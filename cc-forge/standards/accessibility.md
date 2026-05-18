# Accessibility Standards

WCAG 2.1 AA is the minimum. These rules are not aspirational — they are
the baseline for any product that respects its users.

---

## Images

Every `<img>` element needs `alt` text:
- Informative images: describe what it shows
- Decorative images: `alt=""`
- Never use `alt="image"` or `alt="photo"` — be specific

```tsx
// Bad
<img src="/hero.jpg" />
<img src="/chart.png" alt="image" />

// Good
<img src="/hero.jpg" alt="Dashboard showing monthly revenue chart" />
<img src="/divider.svg" alt="" role="presentation" />
```

## Forms

Every input must have an associated `<label>`:

```tsx
// Bad — placeholder only
<input placeholder="Email address" />

// Good
<label htmlFor="email">Email address</label>
<input id="email" type="email" placeholder="you@example.com" />

// Good — visually hidden label
<label htmlFor="search" className="sr-only">Search</label>
<input id="search" type="search" />
```

## Colour contrast

- Normal text: minimum 4.5:1 contrast ratio
- Large text (18px+): minimum 3:1
- UI components and focus indicators: minimum 3:1

Use a contrast checker before shipping any new colour combination.
Do not rely solely on colour to convey information (use icons, text, patterns).

## Keyboard navigation

- All interactive elements reachable by Tab
- Logical tab order (matches visual order)
- Visible focus indicator on all interactive elements (never `outline: none`)
- Escape closes modals and dropdowns
- Arrow keys navigate within components (menus, tabs, etc.)

```css
/* Never do this */
:focus { outline: none; }

/* Do this instead */
:focus-visible {
  outline: 2px solid var(--color-focus);
  outline-offset: 2px;
}
```

## Semantic HTML

Use the right element for the job — it provides accessibility for free:

```tsx
// Bad
<div onClick={handleClick}>Submit</div>
<div className="heading">Section Title</div>
<div className="list">
  <div>Item 1</div>
  <div>Item 2</div>
</div>

// Good
<button onClick={handleClick}>Submit</button>
<h2>Section Title</h2>
<ul>
  <li>Item 1</li>
  <li>Item 2</li>
</ul>
```

## ARIA

Use ARIA only when semantic HTML can't express the role or state:

```tsx
// Loading state
<button aria-busy={isLoading} disabled={isLoading}>
  {isLoading ? 'Saving...' : 'Save'}
</button>

// Error message associated with input
<input
  id="email"
  aria-describedby="email-error"
  aria-invalid={!!error}
/>
{error && <p id="email-error" role="alert">{error}</p>}

// Icon-only button
<button aria-label="Close dialog">
  <XIcon aria-hidden="true" />
</button>
```

## Error messages

- Associate error messages with their field using `aria-describedby`
- Use `role="alert"` for dynamically injected errors
- Be specific: "Email is required" not "Field is required"
- Suggest how to fix: "Password must be at least 8 characters"
