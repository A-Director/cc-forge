"""
Hermes cache — freshness-checked read, not a TTL guess (spec §2.7).

The SessionStart hook and the doctor both read the same Layer-2 source
files (state.json, backlog/*.md, RISKS.md, usage.log) and compute a
situational summary. Without a cache, each read recomputes from scratch
on every session — fine for cold cases, expensive when nothing has
changed.

The cache stores:
  - the computed summary
  - the mtime of every source file it derived from

On read, the cache compares stored mtimes against current mtimes for
every source. If all match: cache is warm, summary served directly.
If any source is newer than its stored mtime: cache is stale for that
source, the caller recomputes (the cache does NOT silently serve stale
data — that's the §2.7 contract this module enforces).

Spec §2.7 last paragraph: 'a stale cache is never silently served — any
newer source file forces recomputation of the affected portion. This
makes the cache a freshness-checked read, not a time-to-live guess.'
That's the principle this module codifies. C-2 from the cross-check is
the label on this design.

Module-level invariants:
  - The cache file is JSON; missing or unparseable → treat as cold.
  - Stored mtimes are float seconds-since-epoch for cross-platform safety.
  - A source file that USED TO EXIST but no longer does = cache stale.
  - A source file that DIDN'T EXIST when cache was warmed but DOES NOW =
    cache stale (the summary's preconditions changed).
  - Atomic write: temp-file + rename so a crash mid-write doesn't leave
    a half-written cache.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any


class CacheStaleError(Exception):
    """Raised by read_if_warm() when staleness is detected and the caller
    asked for strict mode. Carries the list of stale source paths."""

    def __init__(self, stale_sources: list[str]):
        self.stale_sources = stale_sources
        super().__init__(f"cache stale for sources: {', '.join(stale_sources)}")


class HermesCache:
    """A freshness-checked summary cache.

    Typical usage:

        cache = HermesCache(Path('.cc-forge/cache.json'))
        summary = cache.read_if_warm(source_files=[
            Path('.cc-forge/state.json'),
            *Path('.cc-forge/backlog').glob('*.md'),
        ])
        if summary is None:
            summary = compute_summary_expensively(...)
            cache.write(summary, source_files=[...])
    """

    def __init__(self, path: Path):
        self.path = Path(path)

    # ─── reads ──────────────────────────────────────────────────────

    def read_if_warm(self, source_files: list[Path], *, strict: bool = False) -> dict[str, Any] | None:
        """
        Return the cached summary if every source file's current mtime matches
        the mtime recorded in the cache. Return None if cold or stale.

        If strict=True, raise CacheStaleError on staleness (so the caller can
        report which sources invalidated the cache).
        """
        record = self._read_record()
        if record is None:
            return None

        stale = self._stale_sources(record, source_files)
        if stale:
            if strict:
                raise CacheStaleError(stale)
            return None

        summary = record.get("summary")
        if not isinstance(summary, dict):
            # Malformed cache — treat as cold.
            return None
        return summary

    def is_warm(self, source_files: list[Path]) -> bool:
        """Boolean version of read_if_warm — for callers that just want the
        verdict without reading the data."""
        record = self._read_record()
        if record is None:
            return False
        return not self._stale_sources(record, source_files)

    def staleness_report(self, source_files: list[Path]) -> dict[str, Any]:
        """Return a structured report of which sources are stale and why.
        Useful for the doctor's drift surface so we can show *what* changed."""
        record = self._read_record()
        if record is None:
            return {"state": "cold", "reason": "no cache file or unreadable"}
        stale = self._stale_sources(record, source_files)
        if not stale:
            return {"state": "warm", "stale_sources": []}
        return {"state": "stale", "stale_sources": stale}

    # ─── writes ─────────────────────────────────────────────────────

    def write(self, summary: dict[str, Any], source_files: list[Path]) -> None:
        """Atomic write: record current mtimes for every source plus the
        summary, in a temp file, then rename. A crash mid-write leaves the
        previous cache file intact (or no cache file at all on first write).
        """
        mtimes: dict[str, float | None] = {}
        for src in source_files:
            try:
                mtimes[str(src)] = src.stat().st_mtime
            except (FileNotFoundError, OSError):
                # Record missing-at-write — future reads will detect a
                # transition (now-missing or now-present) as staleness.
                mtimes[str(src)] = None

        record = {
            "format": "hermes-cache-v1",
            "summary": summary,
            "source_mtimes": mtimes,
        }

        self.path.parent.mkdir(parents=True, exist_ok=True)
        # Atomic: write to tempfile in same dir, then os.replace().
        fd, tmp_path = tempfile.mkstemp(dir=str(self.path.parent),
                                        prefix=".cache.", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(record, fh, indent=2, ensure_ascii=False)
            os.replace(tmp_path, self.path)
        except Exception:
            # Clean up the temp file if something went wrong before rename.
            try:
                os.unlink(tmp_path)
            except FileNotFoundError:
                pass
            raise

    def invalidate(self) -> bool:
        """Delete the cache file. Returns True if a file was removed."""
        try:
            self.path.unlink()
            return True
        except FileNotFoundError:
            return False

    # ─── internals ──────────────────────────────────────────────────

    def _read_record(self) -> dict[str, Any] | None:
        try:
            raw = self.path.read_text(encoding="utf-8")
        except (FileNotFoundError, OSError):
            return None
        try:
            record = json.loads(raw)
        except json.JSONDecodeError:
            return None
        if not isinstance(record, dict):
            return None
        if record.get("format") != "hermes-cache-v1":
            # Unknown cache format — treat as cold, do not try to interpret.
            return None
        return record

    def _stale_sources(self, record: dict[str, Any], source_files: list[Path]) -> list[str]:
        """Return the list of source paths whose current mtime differs from
        the recorded mtime (including the transition cases: now-missing or
        now-present)."""
        stored = record.get("source_mtimes") or {}
        if not isinstance(stored, dict):
            # Malformed mtime map — treat the whole cache as stale.
            return [str(p) for p in source_files]

        stale: list[str] = []

        # 1. Every requested source must match the recorded mtime.
        for src in source_files:
            key = str(src)
            stored_mtime = stored.get(key, "__not_recorded__")
            if stored_mtime == "__not_recorded__":
                # Cache was warmed against a different source set — must
                # recompute to capture the new source.
                stale.append(key)
                continue
            try:
                current_mtime = src.stat().st_mtime
            except (FileNotFoundError, OSError):
                # Source vanished. If the cache recorded it as None
                # (also missing), that's still in sync; otherwise stale.
                if stored_mtime is not None:
                    stale.append(key)
                continue
            if stored_mtime is None:
                # Cache recorded source-as-missing; it now exists.
                stale.append(key)
                continue
            # Float comparison: any difference is stale, no tolerance.
            # mtime granularity differs by filesystem, but we always write
            # what stat() returned — so exact equality is the right test.
            if float(stored_mtime) != float(current_mtime):
                stale.append(key)

        return stale
