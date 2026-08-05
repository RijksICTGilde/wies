# Bug report: `nldd-toolbar` flashes at 0×0 when inserted after first paint

**Component:** `nldd-toolbar`
**Version:** `@nldd/design-system` 0.8.78
**Impact:** visible layout flash for any consumer that inserts a toolbar into an
already-painted document — HTMX swap, SPA route change, `v-if`/`v-show` toggle,
`appendChild`, etc. Found in Wies when an assignment panel (containing a
`nldd-toolbar`) is swapped into an open side sheet via HTMX.

## Symptom

An `nldd-toolbar` inserted after first paint renders at **0×0 for one frame**,
then jumps to its measured size. Measured in the consumer app via
`htmx:afterSwap` + `requestAnimationFrame` on the swapped-in toolbar:

```
afterSwap (sync, before paint) — toolbar=0x0    button=0x0
rAF #1                         — toolbar=608x44  button=157x44
rAF #2                         — toolbar=608x44  button=157x44
```

The slotted button/items are fully upgraded the whole time (`:defined`,
`shadowRoot` present) — so this is **not** a custom-element upgrade / FOUCE
issue. It is the toolbar's own layout that is deferred.

## Root cause

`toolbar.js` → `connectedCallback()` defers the first build (and therefore the
first measurement) by a macrotask:

```js
connectedCallback() {
  super.connectedCallback();
  this._observer = new MutationObserver(/* … */);
  setTimeout(() => this._buildChildren(), 0);   // ← deferred a full macrotask
  this._createMenu();
}
```

Until `_buildChildren()` → (via `updated`) `_measureAndUpdate()` runs, the
measurement custom properties stay at their `0px` placeholders:

```css
/* toolbar.styles.js — :host */
--_width: 0px;
--_start-width: 0px;
--_center-width: 0px;
--_end-width: 0px;
--_overflow-button-width: 0px;
```

The spacer flex-bases are computed from those `0px` values, so the toolbar
collapses to 0×0 until the deferred measure fires on the next macrotask.

On an **initial full page load** this is masked by the design system's global
FOUC guard (`css/fouc.css`: `body:has(:not(:defined)) { opacity: 0 }`) — the
body stays hidden until everything settles. That guard is one-shot
(`animation … forwards`), so it does **not** cover a toolbar inserted _after_
the page has revealed — which is exactly when the flash becomes visible.

## Suggested fix (in the component)

Keep the toolbar from being painted at its un-measured 0×0 size until the first
measurement completes. The component already tracks `_hasMeasured`, so:

- Reflect a `[measured]` (or `[data-ready]`) attribute from
  `_measureAndUpdate()` once `_hasMeasured` becomes true, and gate visibility on
  it in the styles:

  ```css
  :host(:not([measured])) {
    visibility: hidden;
  }
  ```

  (Optionally also reserve the intrinsic control height while hidden, e.g.
  `min-height: var(--semantics-controls-<size>-min-size)`, so surrounding
  content doesn't reflow when the toolbar reveals.)

This removes the 0-height frame for every consumer and every insertion path,
without relying on the page-level FOUC guard.

Doing the first build synchronously in `connectedCallback` / `firstUpdated`
instead of `setTimeout(0)` would also remove the gap, but the deferral looks
intentional (presumably to let slotted light-DOM children parse first), so the
visibility-gate approach is the safer change.

## Consumer-side stopgap (what Wies does meanwhile)

Until a fixed version is vendored, Wies reserves the toolbar's settled height
where it inserts toolbars post-paint (see the comment in
`wies/core/static/css/app.css`):

```css
#side-panel-content nldd-toolbar {
  min-height: <settled-height>;
}
```
