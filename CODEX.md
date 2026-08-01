# Codex Engineering Guidelines

Use these standards when adding or changing code in this project. Favor clear, maintainable work over cleverness.

## General Code Standards

- Keep changes small, focused, and easy to review.
- Prefer existing project patterns before introducing new abstractions.
- Name files, functions, variables, and components for what they do.
- Write code that is readable without long explanatory comments.
- Add comments only when they explain non-obvious decisions or constraints.
- Avoid unrelated refactors while implementing a feature or fix.
- Keep configuration in environment variables when values differ by environment.
- Validate inputs at API boundaries.
- Handle error states explicitly instead of assuming the happy path.
- Keep dependencies minimal and purposeful.
- Run the relevant checks before considering work complete.

## Backend Standards

- Keep Django apps organized around domain concerns.
- Put request/response behavior in views or viewsets, not models.
- Keep model methods focused on domain behavior.
- Use migrations for schema changes and commit them with the related model change.
- Avoid hard-coded service URLs, secrets, credentials, and environment-specific values.
- Make Celery tasks idempotent when practical.
- Keep background tasks small and observable with clear logging.
- Use database queries intentionally; avoid hidden N+1 query patterns.

## Frontend Standards

- Design mobile-first. Start with the smallest practical viewport, then enhance for larger screens.
- Every screen must be mobile friendly before it is considered complete.
- Use responsive layouts that work well at phone, tablet, and desktop widths.
- Avoid fixed widths that cause horizontal scrolling on small screens.
- Use flexible units, wrapping, and sensible min/max sizes for layout.
- Keep touch targets comfortable on mobile; interactive controls should be easy to tap.
- Make navigation and primary actions usable with one hand on a phone.
- Keep forms simple on mobile: clear labels, stacked fields, appropriate input types, and visible error states.
- Do not rely on hover-only interactions for essential behavior.
- Ensure text remains readable without zooming.
- Avoid dense desktop-style tables on mobile; use stacked, scrollable, or summarized layouts instead.
- Test visual changes at mobile and desktop breakpoints.
- Prefer accessible semantic HTML before custom interaction patterns.
- Use HeroUI when practical for buttons, form fields, validation states, cards, modals, and reusable UI controls.
- Use TanStack Query for client-side backend API fetching and mutations, especially when managing loading, error, and success states.
- Raw `fetch` is acceptable inside Next.js route handlers, server-side utilities, and very small non-reactive server code.
- Keep loading, empty, error, and success states designed, not accidental.
- Preserve performance by avoiding unnecessary client-side JavaScript.

## Styling Standards

- Keep visual design clean, consistent, and restrained.
- Use the existing color, spacing, typography, and component patterns unless there is a reason to extend them.
- Prefer CSS that is predictable and easy to override.
- Do not create page layouts that depend on fragile pixel-perfect positioning.
- Use consistent spacing scales across related UI.
- Keep cards, panels, buttons, and form controls visually consistent.
- Use `var(--panel)` (`#eef6fc`, very light blue) for boxed surfaces: cards, panels, list items, and similar containers.
- Make contrast strong enough for readability. When creating or changing color schemes, verify foreground/background pairs meet WCAG AA contrast: at least 4.5:1 for normal text and 3:1 for large text or non-text UI indicators.
- Check selected, active, hover, disabled, badge, and pill states separately; do not put pale or mid-tone text on tinted backgrounds, even when the hue feels visually related.
- Avoid decorative UI that competes with core workflows.

## Frontend dev

- **Hot reload (daily work):** from `frontend/`, run `npm run dev`.
- **Production smoke test:** `npm run build` then `npm start` (runs standalone output from `next.config.ts`).
- Do not use `npm start` without a fresh build — it runs a frozen `.next` output with no file watching.

## Review Checklist

Before handing off work, confirm:

- The app still builds or the changed area passes its relevant check.
- The UI works on mobile-width screens.
- There is no obvious horizontal overflow on mobile.
- Loading and error states are considered.
- Environment-specific values are not hard-coded.
- The README or docs are updated when setup or behavior changes.
