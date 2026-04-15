var _a;
import { css, nothing, html, LitElement, unsafeCSS, svg } from "lit";
import { property, state, customElement, query } from "lit/decorators.js";
import { unsafeHTML } from "lit/directives/unsafe-html.js";
import { computePosition, offset, flip, shift, size } from "@floating-ui/dom";
import { classMap } from "lit/directives/class-map.js";
import { repeat } from "lit/directives/repeat.js";
import { styleMap } from "lit/directives/style-map.js";
import { ifDefined } from "lit/directives/if-defined.js";
import { unsafeStatic, html as html$1 } from "lit/static-html.js";
const styles$j = css`
	/* # Host */

	:host {
		display: inline-block;
		-webkit-tap-highlight-color: transparent;
	}

	:host([full-width]) {
		display: block;
		width: 100%;
		flex-grow: 1;
	}

	:host([hidden]) {
		display: none;
	}

	:host([disabled]) {
		opacity: var(--primitives-opacity-disabled);
		pointer-events: none;
	}

	/* # Base */

	.button {
		appearance: none;
		border: none;
		margin: 0;
		padding: 0;
		background: none;
		font: inherit;
		box-sizing: border-box;
		text-decoration: none;
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 100%;
		transition:
			background-color 0.15s ease-out,
			color 0.15s ease-out
		;
	}

	@media (prefers-reduced-motion: reduce) {
		.button {
			transition: none;
		}
	}

	/* # Focus */

	.button:focus-visible {
		box-shadow: var(--semantics-focus-ring-box-shadow);
		outline: var(--semantics-focus-ring-outline);
	}

	.button:focus:not(:focus-visible) {
		outline: none;
	}

	/* # Sizes */

	/* ## Size: XS */

	:host([size="xs"]) .button {
		min-height: var(--semantics-controls-xs-min-size);
		min-width: var(--semantics-controls-xs-min-size);
		padding: var(--primitives-space-4) var(--primitives-space-6);
		font: var(--semantics-buttons-xs-font);
		border-radius: var(--semantics-controls-xs-corner-radius);
		gap: var(--primitives-space-3);
	}

	/* ## Size: SM */

	:host([size="sm"]) .button {
		min-height: var(--semantics-controls-sm-min-size);
		min-width: var(--semantics-controls-sm-min-size);
		padding: var(--primitives-space-6) var(--primitives-space-10);
		font: var(--semantics-buttons-sm-font);
		border-radius: var(--semantics-controls-sm-corner-radius);
		gap: var(--primitives-space-4);
	}

	/* ## Size: MD (Default) */

	:host([size="md"]) .button,
	:host(:not([size])) .button {
		min-height: var(--semantics-controls-md-min-size);
		min-width: var(--semantics-controls-md-min-size);
		padding: var(--primitives-space-12);
		font: var(--semantics-buttons-md-font);
		border-radius: var(--semantics-controls-md-corner-radius);
		gap: var(--primitives-space-6);
	}

	/* # Variants */

	/* ## Variant: Neutral Tintend (Secondary, Default) */

	:host([variant="neutral-tinted"]) .button,
	:host([variant="secondary"]) .button,
	:host(:not([variant])) .button {
		background-color: var(--semantics-buttons-neutral-tinted-background-color);
		color: var(--semantics-buttons-neutral-tinted-content-color);
	}

	:host([variant="neutral-tinted"]) .button:hover,
	:host([variant="secondary"]) .button:hover,
	:host(:not([variant])) .button:hover {
		background-color: var(--semantics-buttons-neutral-tinted-is-hovered-background-color);
		color: var(--semantics-buttons-neutral-tinted-is-hovered-content-color);
	}

	:host([variant="neutral-tinted"]) .button:active,
	:host([variant="secondary"]) .button:active,
	:host(:not([variant])) .button:active {
		background-color: var(--semantics-buttons-neutral-tinted-is-active-background-color);
		color: var(--semantics-buttons-neutral-tinted-is-active-content-color);
	}

	/* ## Variant: Neutral Transparent */

	:host([variant="neutral-transparent"]) .button {
		background-color: transparent;
		color: var(--semantics-buttons-neutral-transparent-content-color);
	}

	:host([variant="neutral-transparent"]) .button:hover {
		color: var(--semantics-buttons-neutral-transparent-is-hovered-content-color);
	}

	:host([variant="neutral-transparent"]) .button:active {
		color: var(--semantics-buttons-neutral-transparent-is-active-content-color);
	}

	/* ## Variant: Accent Filled (Primary) */

	:host([variant="accent-filled"]) .button,
	:host([variant="primary"]) .button {
		background-color: var(--semantics-buttons-accent-filled-background-color);
		color: var(--semantics-buttons-accent-filled-content-color);
	}

	:host([variant="accent-filled"]) .button:hover,
	:host([variant="primary"]) .button:hover {
		background-color: var(--semantics-buttons-accent-filled-is-hovered-background-color);
		color: var(--semantics-buttons-accent-filled-is-hovered-content-color);
	}

	:host([variant="accent-filled"]) .button:active,
	:host([variant="primary"]) .button:active {
		background-color: var(--semantics-buttons-accent-filled-is-active-background-color);
		color: var(--semantics-buttons-accent-filled-is-active-content-color);
	}

	/* ## Variant: Accent Outlined */

	:host([variant="accent-outlined"]) .button {
		background-color: transparent;
		padding: calc(var(--primitives-space-12) - var(--semantics-buttons-accent-outlined-border-thickness));
		color: var(--semantics-buttons-accent-outlined-content-color);
		border-width: var(--semantics-buttons-accent-outlined-border-thickness);
		border-style: solid;
		border-color: var(--semantics-buttons-accent-outlined-border-color);
	}

	:host([variant="accent-outlined"][size="md"]) .button {
		padding: calc(var(--primitives-space-12) - var(--semantics-buttons-accent-outlined-border-thickness));
	}

	:host([variant="accent-outlined"][size="sm"]) .button {
		padding:
			calc(var(--primitives-space-6) - var(--semantics-buttons-accent-outlined-border-thickness))
			calc(var(--primitives-space-10) - var(--semantics-buttons-accent-outlined-border-thickness))
		;
	}

	:host([variant="accent-outlined"][size="xs"]) .button {
		padding:
			calc(var(--primitives-space-4) - var(--semantics-buttons-accent-outlined-border-thickness))
			calc(var(--primitives-space-6) - var(--semantics-buttons-accent-outlined-border-thickness))
		;
	}

	:host([variant="accent-outlined"]) .button:hover {
		color: var(--semantics-buttons-accent-outlined-is-hovered-content-color);
		border-color: var(--semantics-buttons-accent-outlined-is-hovered-border-color);
	}

	:host([variant="accent-outlined"]) .button:active {
		color: var(--semantics-buttons-accent-outlined-is-active-content-color);
		border-color: var(--semantics-buttons-accent-outlined-is-active-border-color);
	}

	/* ## Variant: Accent Transparent */

	:host([variant="accent-transparent"]) .button {
		background-color: transparent;
		color: var(--semantics-buttons-accent-transparent-content-color);
	}

	:host([variant="accent-transparent"]) .button:hover {
		color: var(--semantics-buttons-accent-transparent-is-hovered-content-color);
	}

	:host([variant="accent-transparent"]) .button:active {
		color: var(--semantics-buttons-accent-transparent-is-active-content-color);
	}

	/* ## Variant: Danger Tinted */

	:host([variant="danger-tinted"]) .button,
	:host([variant="destructive"]) .button {
		background-color: var(--semantics-buttons-danger-tinted-background-color);
		color: var(--semantics-buttons-danger-tinted-content-color);
	}

	:host([variant="danger-tinted"]) .button:hover,
	:host([variant="destructive"]) .button:hover {
		background-color: var(--semantics-buttons-danger-tinted-is-hovered-background-color);
		color: var(--semantics-buttons-danger-tinted-is-hovered-content-color);
	}

	:host([variant="danger-tinted"]) .button:active,
	:host([variant="destructive"]) .button:active {
		background-color: var(--semantics-buttons-danger-tinted-is-active-background-color);
		color: var(--semantics-buttons-danger-tinted-is-active-content-color);
	}

	/* ## Elements */

	.button__content {
		display: contents;
	}

	::slotted(ndd-icon) {
		display: none;
	}

	.button__start-icon,
	.button__end-icon {
		display: block;
		flex-shrink: 0;
	}

	:host([size="md"]) .button__start-icon,
	:host(:not([size])) .button__start-icon,
	:host([size="md"]) .button__end-icon,
	:host(:not([size])) .button__end-icon {
		width: var(--primitives-space-20);
		height: var(--primitives-space-20);
	}

	:host([size="sm"]) .button__start-icon,
	:host([size="sm"]) .button__end-icon {
		width: var(--primitives-space-18);
		height: var(--primitives-space-18);
	}

	:host([size="xs"]) .button__start-icon,
	:host([size="xs"]) .button__end-icon {
		width: var(--primitives-space-16);
		height: var(--primitives-space-16);
	}

	.button__disclosure-icon {
		display: block;
		flex-shrink: 0;
	}

	:host([size="md"]) .button__disclosure-icon,
	:host(:not([size])) .button__disclosure-icon {
		width: var(--primitives-space-20);
		height: var(--primitives-space-20);
		margin-left: -2px;
		margin-right: -2px;
	}

	:host([size="sm"]) .button__disclosure-icon {
		width: var(--primitives-space-18);
		height: var(--primitives-space-18);
		margin-left: -1px;
		margin-right: -2px;
	}

	:host([size="xs"]) .button__disclosure-icon {
		width: var(--primitives-space-16);
		height: var(--primitives-space-16);
		margin-left: -1px;
		margin-right: -2px;
	}
`;
function renderContent$1(component) {
  return html`
		<span class="button__content">
			${component.startIcon ? html`
				<ndd-icon class="button__start-icon"
					name=${component.startIcon}
				></ndd-icon>
			` : html`<slot name="start-icon"></slot>`}
			${component.text}
			${component.endIcon ? html`
				<ndd-icon class="button__end-icon"
					name=${component.endIcon}
				></ndd-icon>
			` : html`<slot name="end-icon"></slot>`}
			${component.expandable ? html`
				<ndd-icon class="button__disclosure-icon"
					name="chevron-down-small"
				></ndd-icon>
			` : nothing}
		</span>
	`;
}
function template$i(helpers) {
  const content = renderContent$1(this);
  if (this.href) {
    const resolvedRel = this._resolvedRel();
    return html`
			<a class="button"
				href=${this.href}
				target=${this.target || nothing}
				rel=${resolvedRel || nothing}
				aria-disabled=${this.disabled ? "true" : nothing}
				aria-label=${this.accessibleLabel || nothing}
				@click=${helpers.handleClick}
			>
				${content}
			</a>
		`;
  }
  return html`
		<button class="button"
			type=${this.type}
			?disabled=${this.disabled}
			aria-disabled=${this.disabled ? "true" : nothing}
			aria-label=${this.accessibleLabel || nothing}
			popovertarget=${this.popovertarget || nothing}
			@click=${helpers.handleClick}
		>
			${content}
		</button>
	`;
}
const apartmentBuilding = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="M11 16H9v-2h2zM15 16h-2v-2h2zM11 12H9v-2h2zM15 12h-2v-2h2zM11 8H9V6h2zM15 8h-2V6h2z"/>\n	<path fill="currentColor" d="M16 2a3 3 0 0 1 3 3v17h-6v-2h-2v2H5V5a3 3 0 0 1 3-3zM8 4a1 1 0 0 0-1 1v15h2v-2h6v2h2V5a1 1 0 0 0-1-1z"/>\n</svg>\n';
const __vite_glob_0_0 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: apartmentBuilding
}, Symbol.toStringTag, { value: "Module" }));
const arrow2CounterClockwise = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="M4 12a8 8 0 0 0 14.93 4H16v-2h6v6h-2v-2a9.98 9.98 0 0 1-18-6zM12 2a10 10 0 0 1 10 10h-2A8 8 0 0 0 5.07 8H8v2H2V4h2v2a10 10 0 0 1 8-4"/>\n</svg>\n';
const __vite_glob_0_1 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: arrow2CounterClockwise
}, Symbol.toStringTag, { value: "Module" }));
const arrowDownInBucket = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="M13 3v10.586l4.293-4.293 1.414 1.414L12 17.414l-6.707-6.707 1.414-1.414L11 13.586V3zM5 16v3a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-3h2v3a3 3 0 0 1-3 3H6a3 3 0 0 1-3-3v-3z"/>\n</svg>\n';
const __vite_glob_0_2 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: arrowDownInBucket
}, Symbol.toStringTag, { value: "Module" }));
const arrowDown = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="m4 12 8 8 8-8-1.42-1.41L13 16.172V3h-2v13.172L5.42 10.59z"/>\n</svg>\n';
const __vite_glob_0_3 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: arrowDown
}, Symbol.toStringTag, { value: "Module" }));
const arrowLeft = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="m12 4-8 8 8 8 1.41-1.42L7.828 13H21v-2H7.828l5.582-5.58z"/>\n</svg>\n';
const __vite_glob_0_4 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: arrowLeft
}, Symbol.toStringTag, { value: "Module" }));
const arrowRight = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="m12 4 8 8-8 8-1.41-1.42L16.172 13H3v-2h13.172L10.59 5.42z"/>\n</svg>\n';
const __vite_glob_0_5 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: arrowRight
}, Symbol.toStringTag, { value: "Module" }));
const arrowUpArrowDown = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="m7 3.586 5.707 5.707-1.414 1.414L8 7.414V20H6V7.414l-3.293 3.293-1.414-1.414zM18 4v12.586l3.293-3.293 1.414 1.414L17 20.414l-5.707-5.707 1.414-1.414L16 16.586V4z"/>\n</svg>\n';
const __vite_glob_0_6 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: arrowUpArrowDown
}, Symbol.toStringTag, { value: "Module" }));
const arrowUp = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="m4 12 8-8 8 8-1.42 1.41L13 7.828V21h-2V7.828L5.42 13.41z"/>\n</svg>\n';
const __vite_glob_0_7 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: arrowUp
}, Symbol.toStringTag, { value: "Module" }));
const arrowUturnBackward = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="M9.4 5.4 5.82 9H17a5 5 0 0 1 0 10h-2v-2h2a3 3 0 1 0 0-6H5.82l3.58 3.6L8 16l-6-6 6-6z"/>\n</svg>\n';
const __vite_glob_0_8 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: arrowUturnBackward
}, Symbol.toStringTag, { value: "Module" }));
const arrowUturnForward = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="M14.6 5.4 18.18 9H7a5 5 0 0 0 0 10h2v-2H7a3 3 0 1 1 0-6h11.18l-3.58 3.6L16 16l6-6-6-6z"/>\n</svg>\n';
const __vite_glob_0_9 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: arrowUturnForward
}, Symbol.toStringTag, { value: "Module" }));
const bold = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="M5.5 22V2h6.067q3.628 0 5.335 1.311 1.708 1.311 1.708 3.506 0 1.86-.854 3.018a4.35 4.35 0 0 1-2.165 1.586v.091q1.86.366 2.836 1.555 1.006 1.159 1.006 2.896 0 2.867-1.92 4.452Q15.59 21.999 11.81 22zm3.902-3.14h2.257q1.829 0 2.743-.732.915-.762.915-2.134 0-1.311-.915-1.982-.884-.7-3.14-.701h-1.86zm0-8.537h1.769q1.677 0 2.5-.64.823-.67.823-2.043 0-1.25-.762-1.86-.732-.64-2.47-.64h-1.86z"/>\n</svg>\n';
const __vite_glob_0_10 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: bold
}, Symbol.toStringTag, { value: "Module" }));
const bracketsEllipsis = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="M7 6H4v12h3v2H2V4h5zM22 20h-5v-2h3V6h-3V4h5z"/>\n	<path fill="currentColor" d="M7.5 13a1.5 1.5 0 1 1 0 3 1.5 1.5 0 0 1 0-3M12 13a1.5 1.5 0 1 1 0 3 1.5 1.5 0 0 1 0-3M16.5 13a1.5 1.5 0 1 1 0 3 1.5 1.5 0 0 1 0-3"/>\n</svg>\n';
const __vite_glob_0_11 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: bracketsEllipsis
}, Symbol.toStringTag, { value: "Module" }));
const bulletList = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="M4.5 16.5a1.5 1.5 0 1 1 0 3 1.5 1.5 0 0 1 0-3M22 19H9v-2h13zM4.5 10.5a1.5 1.5 0 1 1 0 3 1.5 1.5 0 0 1 0-3M22 13H9v-2h13zM4.5 4.5a1.5 1.5 0 1 1 0 3 1.5 1.5 0 0 1 0-3M22 7H9V5h13z"/>\n</svg>\n';
const __vite_glob_0_12 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: bulletList
}, Symbol.toStringTag, { value: "Module" }));
const businessSuitcase = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="M17 5v1h2a3 3 0 0 1 3 3v9c0 1.66-1.34 3-3 3H5c-1.66 0-3-1.34-3-3V9a3 3 0 0 1 3-3h2V5a3 3 0 0 1 3-3h4c1.66 0 3 1.34 3 3m3 8.464c-.6.336-1.295.536-2 .536H6c-.705 0-1.4-.2-2-.536V18a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1zM5 8a1 1 0 0 0-1 1v1a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9a1 1 0 0 0-1-1zm5-4a1 1 0 0 0-1 1v1h6V5a1 1 0 0 0-1-1z"/>\n</svg>\n';
const __vite_glob_0_13 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: businessSuitcase
}, Symbol.toStringTag, { value: "Module" }));
const calendarEvent = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="M8 2a1 1 0 0 1 1 1v1h6V3a1 1 0 1 1 2 0v1h1a3 3 0 0 1 3 3v12a3 3 0 0 1-3 3H6a3 3 0 0 1-3-3V7a3 3 0 0 1 3-3h1V3a1 1 0 0 1 1-1M7 6H6a1 1 0 0 0-1 1v3h14V7a1 1 0 0 0-1-1h-1v1a1 1 0 1 1-2 0V6H9v1a1 1 0 0 1-2 0zm12 6H5v7a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1zM7 14h4v4H7z"/>\n</svg>\n';
const __vite_glob_0_14 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: calendarEvent
}, Symbol.toStringTag, { value: "Module" }));
const caretDownExtraSmall = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="m6 10 6 6 6-6z"/>\n</svg>\n';
const __vite_glob_0_15 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: caretDownExtraSmall
}, Symbol.toStringTag, { value: "Module" }));
const caretDownSmall = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="m4 9 8 8 8-8z"/>\n</svg>\n';
const __vite_glob_0_16 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: caretDownSmall
}, Symbol.toStringTag, { value: "Module" }));
const caretDown = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="m2 8 10 10L22 8z"/>\n</svg>\n';
const __vite_glob_0_17 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: caretDown
}, Symbol.toStringTag, { value: "Module" }));
const caretLeftExtraSmall = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="m14 18-6-6 6-6z"/>\n</svg>\n';
const __vite_glob_0_18 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: caretLeftExtraSmall
}, Symbol.toStringTag, { value: "Module" }));
const caretLeftSmall = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="m15 20-8-8 8-8z"/>\n</svg>\n';
const __vite_glob_0_19 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: caretLeftSmall
}, Symbol.toStringTag, { value: "Module" }));
const caretLeft = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="m16 21.7-10-10 10-10z"/>\n</svg>\n';
const __vite_glob_0_20 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: caretLeft
}, Symbol.toStringTag, { value: "Module" }));
const caretRightExtraSmall = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="m10 6 6 6-6 6z"/>\n</svg>\n';
const __vite_glob_0_21 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: caretRightExtraSmall
}, Symbol.toStringTag, { value: "Module" }));
const caretRightSmall = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="m9 4 8 8-8 8z"/>\n</svg>\n';
const __vite_glob_0_22 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: caretRightSmall
}, Symbol.toStringTag, { value: "Module" }));
const caretRight = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="m8 1.7 10 10-10 10z"/>\n</svg>\n';
const __vite_glob_0_23 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: caretRight
}, Symbol.toStringTag, { value: "Module" }));
const caretUpExtraSmall = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="m6 14 6-6 6 6z"/>\n</svg>\n';
const __vite_glob_0_24 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: caretUpExtraSmall
}, Symbol.toStringTag, { value: "Module" }));
const caretUpSmall = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="m4 15 8-8 8 8z"/>\n</svg>\n';
const __vite_glob_0_25 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: caretUpSmall
}, Symbol.toStringTag, { value: "Module" }));
const caretUp = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="M2 16 12 6l10 10z"/>\n</svg>\n';
const __vite_glob_0_26 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: caretUp
}, Symbol.toStringTag, { value: "Module" }));
const certificate = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="M15 11a3 3 0 0 1 2 5.23V21l-2-1-2 1v-4.77A2.99 2.99 0 0 1 15 11m0 2a1 1 0 1 0 0 2 1 1 0 0 0 0-2"/>\n	<path fill="currentColor" d="M19 3a3 3 0 0 1 3 3v10c0 1.67-1.33 3-3 3h-1v-2h1a1 1 0 0 0 1-1V6a1 1 0 0 0-1-1H5a1 1 0 0 0-1 1v10a1 1 0 0 0 1 1h7v2H5c-1.67 0-3-1.33-3-3V6a3 3 0 0 1 3-3z"/>\n	<path fill="currentColor" d="M10 13H6v-2h4zM18 9H6V7h12z"/>\n</svg>\n';
const __vite_glob_0_27 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: certificate
}, Symbol.toStringTag, { value: "Module" }));
const chartXYAxisLine = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="M4 19h18v2H2V3h2z"/>\n	<path fill="currentColor" d="M20.7 7.7 14 14.42l-3-3-3.3 3.3-1.4-1.42L11 8.6l3 3 5.3-5.3z"/>\n</svg>\n';
const __vite_glob_0_28 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: chartXYAxisLine
}, Symbol.toStringTag, { value: "Module" }));
const checkMarkCircle = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="M12 4a8 8 0 1 0 0 16 8 8 0 0 0 0-16M2 12C2 6.477 6.477 2 12 2s10 4.477 10 10-4.477 10-10 10S2 17.523 2 12m14.707-2.113L11 15.594l-3.707-3.707 1.414-1.415L11 12.765l4.293-4.293z"/>\n</svg>\n';
const __vite_glob_0_29 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: checkMarkCircle
}, Symbol.toStringTag, { value: "Module" }));
const checkMarkExtraSmall = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="m17.664 8.707-7.707 7.707-3.707-3.707 1.414-1.414 2.293 2.293 6.293-6.293z"/>\n</svg>\n';
const __vite_glob_0_30 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: checkMarkExtraSmall
}, Symbol.toStringTag, { value: "Module" }));
const checkMarkSmall = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="m19.204 7.707-9.707 9.707-4.707-4.707 1.414-1.414 3.293 3.293 8.293-8.293z"/>\n</svg>\n';
const __vite_glob_0_31 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: checkMarkSmall
}, Symbol.toStringTag, { value: "Module" }));
const checkMark = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="M21.707 6.707 10 18.414l-6.707-6.707 1.414-1.414L10 15.586 20.293 5.293z"/>\n</svg>\n';
const __vite_glob_0_32 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: checkMark
}, Symbol.toStringTag, { value: "Module" }));
const chevronDoubleLeftExtraSmall = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="M12 7.4 7.429 12 12 16.6 10.6 18l-6-6.001L10.6 6z"/>\n	<path fill="currentColor" d="M18 7.4 13.429 12 18 16.6 16.6 18l-6-6.001L16.6 6z"/>\n</svg>\n';
const __vite_glob_0_33 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: chevronDoubleLeftExtraSmall
}, Symbol.toStringTag, { value: "Module" }));
const chevronDoubleLeftSmall = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="M14 5.4 7.429 12 14 18.6 12.6 20l-8-8.001L12.6 4z"/>\n	<path fill="currentColor" d="M21 5.4 14.429 12 21 18.6 19.6 20l-8-8.001L19.6 4z"/>\n</svg>\n';
const __vite_glob_0_34 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: chevronDoubleLeftSmall
}, Symbol.toStringTag, { value: "Module" }));
const chevronDoubleLeft = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="M14 3.4 5.429 12 14 20.6 12.6 22l-10-10.001L12.6 2z"/>\n	<path fill="currentColor" d="M22 3.4 13.429 12 22 20.6 20.6 22l-10-10.001L20.6 2z"/>\n</svg>\n';
const __vite_glob_0_35 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: chevronDoubleLeft
}, Symbol.toStringTag, { value: "Module" }));
const chevronDoubleRightExtraSmall = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="M16.172 12 11.6 7.4 13 6l6 6-6 6-1.4-1.4z"/>\n	<path fill="currentColor" d="M10.172 12 5.6 7.4 7 6l6 6-6 6-1.4-1.4z"/>\n</svg>\n';
const __vite_glob_0_36 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: chevronDoubleRightExtraSmall
}, Symbol.toStringTag, { value: "Module" }));
const chevronDoubleRightSmall = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="M18.172 12 11.6 5.4 13 4l8 8-8 8-1.4-1.4z"/>\n	<path fill="currentColor" d="M11.172 12 4.6 5.4 6 4l8 8-8 8-1.4-1.4z"/>\n</svg>\n';
const __vite_glob_0_37 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: chevronDoubleRightSmall
}, Symbol.toStringTag, { value: "Module" }));
const chevronDoubleRight = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="M11.172 11.7 2.6 3.1 4 1.7l10 10-10 10-1.4-1.4z"/>\n	<path fill="currentColor" d="M19.172 11.7 10.6 3.1 12 1.7l10 10-10 10-1.4-1.4z"/>\n</svg>\n';
const __vite_glob_0_38 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: chevronDoubleRight
}, Symbol.toStringTag, { value: "Module" }));
const chevronDownExtraSmall = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="M12 13.172 7.4 8.6 6 10l6 6 6-6-1.4-1.4z"/>\n</svg>\n';
const __vite_glob_0_39 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: chevronDownExtraSmall
}, Symbol.toStringTag, { value: "Module" }));
const chevronDownSmall = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="M12 14.172 5.4 7.6 4 9l8 8 8-8-1.4-1.4z"/>\n</svg>\n';
const __vite_glob_0_40 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: chevronDownSmall
}, Symbol.toStringTag, { value: "Module" }));
const chevronDown = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="M12 15.172 3.4 6.6 2 8l10 10L22 8l-1.4-1.4z"/>\n</svg>\n';
const __vite_glob_0_41 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: chevronDown
}, Symbol.toStringTag, { value: "Module" }));
const chevronLeftExtraSmall = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="m10.828 12 4.572 4.6L14 18l-6-6 6-6 1.4 1.4z"/>\n</svg>\n';
const __vite_glob_0_42 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: chevronLeftExtraSmall
}, Symbol.toStringTag, { value: "Module" }));
const chevronLeftSmall = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="m9.828 12 6.572 6.6L15 20l-8-8 8-8 1.4 1.4z"/>\n</svg>\n';
const __vite_glob_0_43 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: chevronLeftSmall
}, Symbol.toStringTag, { value: "Module" }));
const chevronLeft = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="m8.828 11.7 8.572 8.6-1.4 1.4-10-10 10-10 1.4 1.4z"/>\n</svg>\n';
const __vite_glob_0_44 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: chevronLeft
}, Symbol.toStringTag, { value: "Module" }));
const chevronRightExtraSmall = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="M13.172 12 8.6 7.4 10 6l6 6-6 6-1.4-1.4z"/>\n</svg>\n';
const __vite_glob_0_45 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: chevronRightExtraSmall
}, Symbol.toStringTag, { value: "Module" }));
const chevronRightSmall = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="M14.172 12 7.6 5.4 9 4l8 8-8 8-1.4-1.4z"/>\n</svg>\n';
const __vite_glob_0_46 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: chevronRightSmall
}, Symbol.toStringTag, { value: "Module" }));
const chevronRight = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="M15.172 11.7 6.6 3.1 8 1.7l10 10-10 10-1.4-1.4z"/>\n</svg>\n';
const __vite_glob_0_47 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: chevronRight
}, Symbol.toStringTag, { value: "Module" }));
const chevronUpDown = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="M12 5.828 7.4 10.4 6 9l6-6 6 6-1.4 1.4zm0 12.344L7.4 13.6 6 15l6 6 6-6-1.4-1.4z"/>\n</svg>\n';
const __vite_glob_0_48 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: chevronUpDown
}, Symbol.toStringTag, { value: "Module" }));
const chevronUpExtraSmall = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="M12 10.828 7.4 15.4 6 14l6-6 6 6-1.4 1.4z"/>\n</svg>\n';
const __vite_glob_0_49 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: chevronUpExtraSmall
}, Symbol.toStringTag, { value: "Module" }));
const chevronUpSmall = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="M12 9.828 5.4 16.4 4 15l8-8 8 8-1.4 1.4z"/>\n</svg>\n';
const __vite_glob_0_50 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: chevronUpSmall
}, Symbol.toStringTag, { value: "Module" }));
const chevronUp = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="M12 8.828 3.4 17.4 2 16 12 6l10 10-1.4 1.4z"/>\n</svg>\n';
const __vite_glob_0_51 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: chevronUp
}, Symbol.toStringTag, { value: "Module" }));
const circleDashed = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path\n		fill="currentColor"\n		d="M14.59 21.66a10.05 10.05 0 0 1-5.18 0l.52-1.93a8.05 8.05 0 0 0 4.14 0zM5.07 16A8.05 8.05 0 0 0 8 18.93l-1 1.73A10.05 10.05 0 0 1 3.34 17zm15.59 1A10.04 10.04 0 0 1 17 20.66l-1-1.73A8.05 8.05 0 0 0 18.93 16zM4.27 9.93A8 8 0 0 0 4 12a8 8 0 0 0 .27 2.07l-1.93.52a10 10 0 0 1 0-5.18zm17.39-.52a10 10 0 0 1 0 5.18l-.96-.26-.97-.26a8.06 8.06 0 0 0 0-4.14zM8 5.07A8.05 8.05 0 0 0 5.07 8L3.34 7A10.05 10.05 0 0 1 7 3.34zm9-1.73A10.05 10.05 0 0 1 20.66 7l-1.73 1A8.05 8.05 0 0 0 16 5.07zM12 2c.9 0 1.76.12 2.59.34l-.26.96-.26.97A8 8 0 0 0 12 4a8 8 0 0 0-2.07.27L9.4 2.34C10.24 2.12 11.11 2 12 2"\n	/>\n</svg>\n';
const __vite_glob_0_52 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: circleDashed
}, Symbol.toStringTag, { value: "Module" }));
const circleFilledExtraSmall = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="M8 12c0 2.204 1.796 4 4 4s4-1.796 4-4-1.796-4-4-4-4 1.796-4 4"/>\n</svg>\n';
const __vite_glob_0_53 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: circleFilledExtraSmall
}, Symbol.toStringTag, { value: "Module" }));
const circleFilledSmall = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="M6 12c0 3.306 2.694 6 6 6s6-2.694 6-6-2.694-6-6-6a6.01 6.01 0 0 0-6 6"/>\n</svg>\n';
const __vite_glob_0_54 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: circleFilledSmall
}, Symbol.toStringTag, { value: "Module" }));
const circleFilled = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="M2 12c0 5.51 4.49 10 10 10s10-4.49 10-10S17.51 2 12 2 2 6.49 2 12"/>\n</svg>\n';
const __vite_glob_0_55 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: circleFilled
}, Symbol.toStringTag, { value: "Module" }));
const clockArrowCounterClockwise = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="M5 4.861a10 10 0 0 1 9.686-2.494 10 10 0 0 1 7.312 9.836c-.094 2.22-.815 4.344-2.222 6.084-1.432 1.699-3.306 2.934-5.483 3.446-2.178.514-4.403.242-6.445-.635a10 10 0 0 1-4.703-4.453l1.77-.93a8 8 0 1 0 4.06-11.121c-.823.356-1.588.81-2.264 1.406H9v2H3V2h2z"/>\n	<path fill="currentColor" d="m13 11.586 3.242 3.242-1.414 1.415-3.535-3.536A1 1 0 0 1 11 12V7h2z"/>\n</svg>\n';
const __vite_glob_0_56 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: clockArrowCounterClockwise
}, Symbol.toStringTag, { value: "Module" }));
const cloudArrowDown = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="m13 19.17 1.58-1.58L16 19l-4 4-4-4 1.42-1.41L11 19.17V10h2z"/>\n	<path fill="currentColor" d="M12 2a7 7 0 0 1 6.93 6.02A4.5 4.5 0 0 1 18.5 17H14v-2h4.5a2.5 2.5 0 0 0 .24-4.99l-1.57-.15-.22-1.56a5 5 0 0 0-9.5-1.4l-.44.98-1.06.16A3.5 3.5 0 0 0 6.5 15H10v2H6.5a5.5 5.5 0 0 1-.86-10.93A7 7 0 0 1 12 2"/>\n</svg>\n';
const __vite_glob_0_57 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: cloudArrowDown
}, Symbol.toStringTag, { value: "Module" }));
const cloudArrowUp = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="m16 12-1.42 1.41L13 11.83V21h-2v-9.17L9.42 13.4 8 12l4-4z"/>\n	<path fill="currentColor" d="M12 2a7 7 0 0 1 6.93 6.02A4.5 4.5 0 0 1 18.5 17H14v-2h4.5a2.5 2.5 0 0 0 .24-4.99l-1.57-.15-.22-1.56a5 5 0 0 0-9.5-1.4l-.44.98-1.06.16A3.5 3.5 0 0 0 6.5 15H10v2H6.5a5.5 5.5 0 0 1-.86-10.93A7 7 0 0 1 12 2"/>\n</svg>\n';
const __vite_glob_0_58 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: cloudArrowUp
}, Symbol.toStringTag, { value: "Module" }));
const cloud = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="M1 13.5a5.5 5.5 0 0 1 4.64-5.43 7 7 0 0 1 13.29 1.95A4.5 4.5 0 0 1 18.5 19v-2a2.5 2.5 0 0 0 .24-4.99l-1.57-.15-.22-1.56a5 5 0 0 0-9.5-1.4l-.44.98-1.06.16A3.5 3.5 0 0 0 6.5 17v2A5.5 5.5 0 0 1 1 13.5M18.5 17v2h-12v-2z"/>\n</svg>\n';
const __vite_glob_0_59 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: cloud
}, Symbol.toStringTag, { value: "Module" }));
const cylinderSplitSlash = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="M22 20.59 20.6 22 2 3.41 3.41 2zM6 8.83V12c0 .1.1.2.16.27.18.21.52.5 1.08.77.95.48 2.3.84 3.9.93l1.99 1.99Q12.57 16 12 16c-2.39 0-4.53-.53-6-1.36V18c0 .1.1.2.16.27.18.21.52.5 1.08.77A11 11 0 0 0 12 20c1.76 0 3.28-.32 4.38-.79l1.5 1.5A13 13 0 0 1 12 22c-4.42 0-8-1.8-8-4V6.83zM12 2c4.42 0 8 1.8 8 4v11.17l-2-2v-.53l-.35.19-1.51-1.52q.33-.12.62-.27.82-.44 1.08-.77c.06-.07.16-.18.16-.27V8.64c-1.3.74-3.13 1.23-5.2 1.34l-2.03-2.03Q11.37 8 12 8a11 11 0 0 0 4.76-.96q.82-.44 1.08-.77c.06-.07.16-.18.16-.27s-.1-.2-.16-.27c-.18-.21-.52-.5-1.08-.77A11 11 0 0 0 12 4c-1.76 0-3.28.32-4.38.79l-1.5-1.5A13 13 0 0 1 12 2"/>\n</svg>\n';
const __vite_glob_0_60 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: cylinderSplitSlash
}, Symbol.toStringTag, { value: "Module" }));
const cylinderSplit = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="M20 18c0 2.2-3.58 4-8 4s-8-1.8-8-4V6c0-2.2 3.58-4 8-4s8 1.8 8 4zm-13.84.27c.18.21.52.5 1.08.77A11 11 0 0 0 12 20a11 11 0 0 0 4.76-.96q.82-.44 1.08-.77c.06-.07.16-.18.16-.27v-3.36A12.5 12.5 0 0 1 12 16c-2.39 0-4.53-.53-6-1.36V18c0 .1.1.2.16.27M18 8.64A12.5 12.5 0 0 1 12 10c-2.39 0-4.53-.53-6-1.36V12c0 .1.1.2.16.27.18.21.52.5 1.08.77A11 11 0 0 0 12 14a11 11 0 0 0 4.76-.96q.82-.44 1.08-.77c.06-.07.16-.18.16-.27zM12 4a11 11 0 0 0-4.76.96q-.83.44-1.08.77C6.1 5.8 6 5.91 6 6s.1.2.16.27c.18.21.52.5 1.08.77A11 11 0 0 0 12 8a11 11 0 0 0 4.76-.96q.82-.44 1.08-.77c.06-.07.16-.18.16-.27s-.1-.2-.16-.27c-.18-.21-.52-.5-1.08-.77A11 11 0 0 0 12 4"/>\n</svg>\n';
const __vite_glob_0_61 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: cylinderSplit
}, Symbol.toStringTag, { value: "Module" }));
const dismissCircleFilled = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="M12 2a10 10 0 1 1 0 20 10 10 0 0 1 0-20m0 8.59-3.3-3.3-1.4 1.42L10.58 12l-3.3 3.3 1.42 1.4L12 13.42l3.3 3.3 1.4-1.42L13.42 12l3.3-3.3-1.42-1.4z"/>\n</svg>\n';
const __vite_glob_0_62 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: dismissCircleFilled
}, Symbol.toStringTag, { value: "Module" }));
const dismissCircle = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="m12 10.59 2.8-2.8 1.4 1.42L13.42 12l2.8 2.8-1.42 1.4L12 13.42l-2.8 2.8-1.4-1.42L10.58 12l-2.8-2.79 1.42-1.42z"/>\n	<path fill="currentColor" d="M12 2a10 10 0 1 1 0 20 10 10 0 0 1 0-20m0 2a8 8 0 1 0 0 16 8 8 0 0 0 0-16"/>\n</svg>\n';
const __vite_glob_0_63 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: dismissCircle
}, Symbol.toStringTag, { value: "Module" }));
const dismissExtraSmall = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="m15.3 7.3 1.4 1.4-3.29 3.3 3.3 3.3-1.42 1.4L12 13.42l-3.3 3.3-1.4-1.42L10.58 12l-3.3-3.3 1.42-1.4L12 10.58z"/>\n</svg>\n';
const __vite_glob_0_64 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: dismissExtraSmall
}, Symbol.toStringTag, { value: "Module" }));
const dismissSmall = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="m17.3 5.3 1.4 1.4-5.29 5.3 5.3 5.3-1.42 1.4L12 13.42l-5.3 5.3-1.4-1.42L10.58 12l-5.3-5.3 1.42-1.4L12 10.58z"/>\n</svg>\n';
const __vite_glob_0_65 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: dismissSmall
}, Symbol.toStringTag, { value: "Module" }));
const dismiss = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="m19.3 3.3 1.4 1.4-7.29 7.3 7.3 7.3-1.42 1.4L12 13.42l-7.3 7.3-1.4-1.42L10.58 12l-7.3-7.3 1.42-1.4L12 10.58z"/>\n</svg>\n';
const __vite_glob_0_66 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: dismiss
}, Symbol.toStringTag, { value: "Module" }));
const ellipsis = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="M5 10a2 2 0 1 1 0 4 2 2 0 0 1 0-4m7 0a2 2 0 1 1 0 4 2 2 0 0 1 0-4m7 0a2 2 0 1 1 0 4 2 2 0 0 1 0-4"/>\n</svg>\n';
const __vite_glob_0_67 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: ellipsis
}, Symbol.toStringTag, { value: "Module" }));
const envelope = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="M19 4a3 3 0 0 1 3 3v10c0 1.66-1.34 3-3 3H5c-1.66 0-3-1.34-3-3V7a3 3 0 0 1 3-3zm-5.5 9.562a3 3 0 0 1-3 0L4 9.81V17a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1V9.81zM5 6a1 1 0 0 0-1 1v.5l7.5 4.33a1 1 0 0 0 1 0L20 7.5V7a1 1 0 0 0-1-1z"/>\n</svg>\n';
const __vite_glob_0_68 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: envelope
}, Symbol.toStringTag, { value: "Module" }));
const euro = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="M4.5 10.939V9.055h11.39v1.884zm11.39 2.51v1.884H4.5V13.45zM15.053 22q-2.392 0-4.215-1.076-1.824-1.077-2.87-3.199-1.017-2.122-1.017-5.292 0-2.72.688-4.693.717-1.973 1.913-3.229 1.197-1.286 2.72-1.883A8.5 8.5 0 0 1 15.503 2q.956 0 1.704.09.747.09 1.435.299V4.48q-1.017-.24-1.645-.299-.627-.09-1.614-.09-1.196 0-2.272.479-1.047.478-1.883 1.465-.838.987-1.316 2.511-.478 1.495-.478 3.528 0 2.66.747 4.394.777 1.734 2.123 2.601 1.345.837 3.079.837.867 0 1.674-.09t1.794-.328v2.033q-1.017.24-1.884.358-.837.12-1.913.12"/>\n</svg>\n';
const __vite_glob_0_69 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: euro
}, Symbol.toStringTag, { value: "Module" }));
const exclamationCircle = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="M12 15a1.25 1.25 0 1 1 0 2.5 1.25 1.25 0 0 1 0-2.5m1-1.5h-2v-7h2z"/>\n	<path fill="currentColor" d="M12 2c5.523 0 10 4.477 10 10s-4.477 10-10 10S2 17.523 2 12 6.477 2 12 2m0 2a8 8 0 1 0 0 16 8 8 0 0 0 0-16"/>\n</svg>\n';
const __vite_glob_0_70 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: exclamationCircle
}, Symbol.toStringTag, { value: "Module" }));
const exclamationTriangleFilled = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="M11.99 1.968a3 3 0 0 1 2.62 1.538l7.095 12.242q.035.06.062.126a3 3 0 0 1-2.76 4.125H5a3.02 3.02 0 0 1-2.538-1.387 3 3 0 0 1-.248-2.739 1 1 0 0 1 .06-.125L9.37 3.506a3 3 0 0 1 2.62-1.538M12 14a1.25 1.25 0 1 0 0 2.5 1.25 1.25 0 0 0 0-2.5m-1-7v5h2V7z"/>\n</svg>\n';
const __vite_glob_0_71 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: exclamationTriangleFilled
}, Symbol.toStringTag, { value: "Module" }));
const exclamationTriangle = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="M12 14a1.25 1.25 0 1 1 0 2.5 1.25 1.25 0 0 1 0-2.5m1-1.5h-2v-5h2z"/>\n	<path fill="currentColor" d="M11.99 1.968a3 3 0 0 1 2.62 1.538l7.095 12.242q.035.06.062.126a3 3 0 0 1-2.76 4.125H5a3.02 3.02 0 0 1-2.538-1.387 3 3 0 0 1-.248-2.739 1 1 0 0 1 .06-.125L9.37 3.506a3 3 0 0 1 2.62-1.538m0 2c-.373 0-.705.21-.884.533L4.046 16.68c-.097.286-.06.602.104.86a.99.99 0 0 0 .85.459h13.996a1 1 0 0 0 .938-1.32L12.875 4.502a1.02 1.02 0 0 0-.885-.533"/>\n</svg>\n';
const __vite_glob_0_72 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: exclamationTriangle
}, Symbol.toStringTag, { value: "Module" }));
const eyeSlash = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="m21.004 19.59-1.414 1.414L3 4.414 4.414 3zM5.837 8.665C4.717 9.563 3.843 10.7 3.2 12c1.612 3.261 4.923 5.5 8.801 5.5.82 0 1.617-.102 2.38-.291l1.603 1.604a11.8 11.8 0 0 1-3.983.687C6.989 19.5 2.739 16.392 1 12a11.8 11.8 0 0 1 3.416-4.756zM12 4.5c5.012 0 9.26 3.108 11 7.5a11.8 11.8 0 0 1-3.416 4.756l-1.422-1.422c1.12-.898 1.995-2.034 2.638-3.334-1.613-3.261-4.923-5.5-8.8-5.5-.821 0-1.619.1-2.382.29L8.015 5.187A11.8 11.8 0 0 1 12 4.5"/>\n	<path fill="currentColor" d="M9.527 12.356a2.5 2.5 0 0 0 2.117 2.116l1.791 1.792a4.5 4.5 0 0 1-5.7-5.7zM12 7.5a4.5 4.5 0 0 1 4.264 5.935l-1.792-1.791a2.5 2.5 0 0 0-2.117-2.117l-1.792-1.792A4.5 4.5 0 0 1 12 7.5"/>\n</svg>\n';
const __vite_glob_0_73 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: eyeSlash
}, Symbol.toStringTag, { value: "Module" }));
const eye = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="M12 4.5c5.012 0 9.26 3.108 11 7.5-1.74 4.392-5.988 7.5-10.999 7.5S2.739 16.392 1 12c1.74-4.392 5.988-7.5 11-7.5m0 2c-3.878 0-7.188 2.239-8.8 5.5 1.612 3.261 4.923 5.5 8.801 5.5 3.877 0 7.187-2.239 8.799-5.5-1.613-3.261-4.923-5.5-8.8-5.5m0 1a4.5 4.5 0 1 1 0 9 4.5 4.5 0 0 1 0-9m0 2a2.5 2.5 0 1 0 0 5 2.5 2.5 0 0 0 0-5"/>\n</svg>\n';
const __vite_glob_0_74 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: eye
}, Symbol.toStringTag, { value: "Module" }));
const fileText = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="M7 4a1 1 0 0 0-1 1v14a1 1 0 0 0 1 1h10a1 1 0 0 0 1-1V9h-3a2 2 0 0 1-2-2V4zm8 1.414L16.586 7H15zM4 5a3 3 0 0 1 3-3h7a1 1 0 0 1 .707.293l5 5A1 1 0 0 1 20 8v11a3 3 0 0 1-3 3H7a3 3 0 0 1-3-3zm4 3h3v2H8zm0 4h8v2H8zm0 4h8v2H8z"/>\n</svg>\n';
const __vite_glob_0_75 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: fileText
}, Symbol.toStringTag, { value: "Module" }));
const folderStack = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="M4 18a1 1 0 0 0 1 1h13a2 2 0 0 1-2 2H5a3 3 0 0 1-3-3V9c0-1.11.9-2 2-2z"/>\n	<path fill="currentColor" d="M10.76 3a3 3 0 0 1 2.12.88L15 6h4a3 3 0 0 1 3 3v6a3 3 0 0 1-3 3H8a3 3 0 0 1-3-3V6a3 3 0 0 1 3-3zM8 5a1 1 0 0 0-1 1v9a1 1 0 0 0 1 1h11a1 1 0 0 0 1-1V9a1 1 0 0 0-.9-1h-4.93l-2.7-2.7a1 1 0 0 0-.71-.3z"/>\n</svg>\n';
const __vite_glob_0_76 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: folderStack
}, Symbol.toStringTag, { value: "Module" }));
const folder = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="M2 17V6a3 3 0 0 1 3-3h3.76a3 3 0 0 1 2.12.88L13 6h6a3 3 0 0 1 3 3v8a3 3 0 0 1-3 3v-2a1 1 0 0 0 1-1V9a1 1 0 0 0-.9-1h-6.93l-2.7-2.7a1 1 0 0 0-.71-.3H5a1 1 0 0 0-1 1v11a1 1 0 0 0 1 1v2a3 3 0 0 1-3-3m17 1v2H5v-2z"/>\n</svg>\n';
const __vite_glob_0_77 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: folder
}, Symbol.toStringTag, { value: "Module" }));
const gear = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="M12 8a4 4 0 1 1 0 8 4 4 0 0 1 0-8m0 2a2 2 0 1 0 0 4 2 2 0 0 0 0-4"/>\n	<path fill="currentColor" d="M13.19 2a2 2 0 0 1 1.991 1.8l.09.9a9 9 0 0 1 1.416.818l.824-.372a2 2 0 0 1 2.555.824l1.19 2.06a2 2 0 0 1-.564 2.624l-.734.527c.055.536.056 1.09 0 1.637l.734.528c.833.6 1.078 1.734.564 2.624l-1.294 2.22a2 2 0 0 1-2.274.734l-1.001-.443a8 8 0 0 1-1.416.819l-.118 1.088a2 2 0 0 1-1.772 1.603H10.62a2 2 0 0 1-1.8-1.792l-.09-.9a8 8 0 0 1-1.416-.818l-1.001.443a2 2 0 0 1-2.275-.734l-1.293-2.22a2 2 0 0 1 .415-2.506l.882-.646a8 8 0 0 1 0-1.637l-.732-.527A2 2 0 0 1 2.658 8.2l1.278-2.23a2 2 0 0 1 2.555-.824l.823.372a8 8 0 0 1 1.416-.819l.09-.898a2 2 0 0 1 1.8-1.792zm-2.38 2.002-.207 2.049-1.055.472q-.566.256-1.061.615l-.939.68-1.88-.848-1.191 2.06 1.672 1.201C6.089 10.818 6 11.41 6 12s.088 1.18.148 1.766l-1.671 1.203h-.001l1.19 2.061 1.88-.85.94.681q.37.27.783.48l1.333.607.207 2.05V20h2.38l.206-2.05 1.055-.475a6 6 0 0 0 1.062-.614l.94-.68 1.88.85 1.19-2.061-1.672-1.203c.06-.586.15-1.177.15-1.767s-.09-1.182-.15-1.769l1.673-1.2-1.19-2.061h-.003l-1.88.846-.938-.678a6 6 0 0 0-1.062-.614l-1.055-.474L13.19 4h-2.38z"/>\n</svg>\n';
const __vite_glob_0_78 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: gear
}, Symbol.toStringTag, { value: "Module" }));
const heartFilled = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="M3.716 5.218a5.86 5.86 0 0 1 8.283 0L12 5.215a5.858 5.858 0 0 1 8.284 8.284l-.001.001.001.002L12 21.787l-8.284-8.284a5.86 5.86 0 0 1 0-8.285"/>\n</svg>\n';
const __vite_glob_0_79 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: heartFilled
}, Symbol.toStringTag, { value: "Module" }));
const heart = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="M12 5.216a5.858 5.858 0 1 1 8.284 8.284v.003L12 21.787l-8.284-8.284c-2.297-2.297-2.216-5.979 0-8.284C6 2.916 9.684 3.026 11.999 5.217zm6.87 1.414a3.86 3.86 0 0 0-5.456 0L12 8.045l-1.414-1.413a3.858 3.858 0 0 0-5.455 5.457l6.87 6.87 6.87-6.873a3.86 3.86 0 0 0 0-5.456"/>\n</svg>\n';
const __vite_glob_0_80 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: heart
}, Symbol.toStringTag, { value: "Module" }));
const house = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="m12 2 10.707 10.707-1.414 1.414L20 12.828V21h-7v-6h-2v6H4v-8.172l-1.293 1.293-1.414-1.414zm-6 8.828V19h3v-6h6v6h3v-8.172l-6-6z"/>\n</svg>\n';
const __vite_glob_0_81 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: house
}, Symbol.toStringTag, { value: "Module" }));
const inbox = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="M21 6v12c0 1.66-1.34 3-3 3H6c-1.66 0-3-1.34-3-3V6a3 3 0 0 1 3-3h12c1.66 0 3 1.34 3 3M5 18a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-4h-3.126a4.002 4.002 0 0 1-7.748 0H5zM6 5a1 1 0 0 0-1 1v6h5v1c0 1.083.92 2 2 2s2-.918 2-2v-1h5V6a1 1 0 0 0-1-1z"/>\n</svg>\n';
const __vite_glob_0_82 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: inbox
}, Symbol.toStringTag, { value: "Module" }));
const infoCircle = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="M13 17.5h-2v-7h2zm-1-11A1.25 1.25 0 1 1 12 9a1.25 1.25 0 0 1 0-2.5"/>\n	<path fill="currentColor" d="M12 2c5.523 0 10 4.477 10 10s-4.477 10-10 10S2 17.523 2 12 6.477 2 12 2m0 2a8 8 0 1 0 0 16 8 8 0 0 0 0-16"/>\n</svg>\n';
const __vite_glob_0_83 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: infoCircle
}, Symbol.toStringTag, { value: "Module" }));
const italic = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="M18 4h-2.821l-4.287 16H14v2H6v-2h2.821l4.287-16H10V2h8z"/>\n</svg>\n';
const __vite_glob_0_84 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: italic
}, Symbol.toStringTag, { value: "Module" }));
const listArrowDown = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="M3 5h11v2H3zm16 0v10.586l2.293-2.293 1.414 1.414L18 19.414l-4.707-4.707 1.414-1.414L17 15.586V5zM3 11h9v2H3zm0 6h9v2H3z"/>\n</svg>\n';
const __vite_glob_0_85 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: listArrowDown
}, Symbol.toStringTag, { value: "Module" }));
const listArrowUp = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="M3 5h9v2H3zm15-.414 4.707 4.707-1.414 1.414L19 8.414V19h-2V8.414l-2.293 2.293-1.414-1.414zM3 11h9v2H3zm0 6h11v2H3z"/>\n</svg>\n';
const __vite_glob_0_86 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: listArrowUp
}, Symbol.toStringTag, { value: "Module" }));
const listDecreasingLines = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="M2 5h20v2H2zm6 12h8v2H8zm-3-6h14v2H5z"/>\n</svg>\n';
const __vite_glob_0_87 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: listDecreasingLines
}, Symbol.toStringTag, { value: "Module" }));
const list = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="M2 5h20v2H2zm0 6h20v2H2zm0 6h20v2H2z"/>\n</svg>\n';
const __vite_glob_0_88 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: list
}, Symbol.toStringTag, { value: "Module" }));
const lockClosed = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="M13 17.5h-2v-5h2z"/>\n	<path fill="currentColor" d="M17 9a3 3 0 0 1 3 3v6a3 3 0 0 1-3 3H6.85A3 3 0 0 1 4 18v-6a3 3 0 0 1 3-3V7a5 5 0 0 1 10 0zM9 9h6V7a3 3 0 1 0-6 0zm-2 2a1 1 0 0 0-1 1v6a1 1 0 0 0 1 1h10a1 1 0 0 0 1-1v-6a1 1 0 0 0-1-1z"/>\n</svg>\n';
const __vite_glob_0_89 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: lockClosed
}, Symbol.toStringTag, { value: "Module" }));
const lockOpen = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="M14.5 17h-5v-2h5z"/>\n	<path fill="currentColor" d="M17 7h-2V6a3 3 0 1 0-6 0v4h8a3 3 0 0 1 3 3v6a3 3 0 0 1-3 3H6.85A3 3 0 0 1 4 19v-6a3 3 0 0 1 3-3V6a5 5 0 0 1 10 0zM7 12a1 1 0 0 0-1 1v6a1 1 0 0 0 1 1h10a1 1 0 0 0 1-1v-6a1 1 0 0 0-1-1z"/>\n</svg>\n';
const __vite_glob_0_90 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: lockOpen
}, Symbol.toStringTag, { value: "Module" }));
const magnifier = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="M2 10c0 4.4 3.6 8 8 8a7.95 7.95 0 0 0 4.9-1.7l5.7 5.7 1.4-1.4-5.7-5.7A7.97 7.97 0 0 0 18 10c0-4.4-3.6-8-8-8s-8 3.6-8 8m2 0c0-3.3 2.7-6 6-6s6 2.7 6 6-2.7 6-6 6-6-2.7-6-6"/>\n</svg>\n';
const __vite_glob_0_91 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: magnifier
}, Symbol.toStringTag, { value: "Module" }));
const minusExtraSmall = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="M6 11h12v2H6z"/>\n</svg>\n';
const __vite_glob_0_92 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: minusExtraSmall
}, Symbol.toStringTag, { value: "Module" }));
const minusSmall = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="M4 11h16v2H4z"/>\n</svg>\n';
const __vite_glob_0_93 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: minusSmall
}, Symbol.toStringTag, { value: "Module" }));
const minus = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="M2 11h20v2H2z"/>\n</svg>\n';
const __vite_glob_0_94 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: minus
}, Symbol.toStringTag, { value: "Module" }));
const moon = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="M10.47 2.12a8.99 8.99 0 0 0 11.41 11.4 10 10 0 1 1-11.4-11.4M8 5.07A8 8 0 1 0 18.93 16 11 11 0 0 1 8 5.07"/>\n</svg>\n';
const __vite_glob_0_95 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: moon
}, Symbol.toStringTag, { value: "Module" }));
const numberedList = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="M5.223 14.015c1.003 0 1.634.316 1.944.864.284.491.308 1.154.117 1.684-.153.412-.473.764-1.071 1.142-.481.305-.98.584-1.34 1.035h2.672V20H3.513l-.135-1.053a3.2 3.2 0 0 1 .441-.882q.298-.405.873-.81c.287-.2.614-.382.846-.648.239-.29.371-.824.036-1.098q-.198-.171-.657-.171c-.524 0-.874.034-1.332.162v-1.287a6.8 6.8 0 0 1 1.638-.198M22 19H10v-2h12zm0-6H10v-2h12zM6.483 10H4.935V5.323c-.474 0-.96.041-1.386.126V4.28C4.514 4.021 5.493 4 6.483 4zM22 7H10V5h12z"/>\n</svg>\n';
const __vite_glob_0_96 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: numberedList
}, Symbol.toStringTag, { value: "Module" }));
const pencilOnSquare = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="M10.932 6H5a1 1 0 0 0-1 1v12a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-5.927l2-2V19c0 1.66-1.34 3-3 3H5c-1.66 0-3-1.34-3-3V7a3 3 0 0 1 3-3h7.93z"/>\n	<path fill="currentColor" d="M17.175 2.586a2 2 0 0 1 2.829 0L21.418 4a2 2 0 0 1 0 2.828L11.246 17H7.003v-4.242zm-8.172 11V15h1.414l6.758-6.758-1.414-1.414zm8.172-8.172 1.414 1.414 1.415-1.414L18.589 4z"/>\n</svg>\n';
const __vite_glob_0_97 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: pencilOnSquare
}, Symbol.toStringTag, { value: "Module" }));
const pencil = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="M21.418 4a2 2 0 0 1 0 2.828L7.246 21H3.003v-4.243L17.175 2.586a2 2 0 0 1 2.828 0zM15.76 6.828 5.003 17.586V19h1.414L17.175 8.243zm1.414-1.414 1.414 1.414 1.414-1.414L18.59 4z"/>\n</svg>\n';
const __vite_glob_0_98 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: pencil
}, Symbol.toStringTag, { value: "Module" }));
const person2 = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="M10 14c2.2 0 4 1.8 4 4v3h-2v-3a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v3H2v-3c0-2.2 1.8-4 4-4zM22 17v3h-2v-3a2 2 0 0 0-2-2h-3.93a5 5 0 0 0-1.92-1.55A4 4 0 0 1 14 13h4c2.2 0 4 1.8 4 4"/>\n	<path fill="currentColor" d="M8 4a4 4 0 1 1 0 8 4 4 0 0 1 0-8m0 2a2 2 0 1 0 0 4 2 2 0 0 0 0-4M16 3a4 4 0 1 1-3.2 6.4 5 5 0 0 0-.5-3.94A4 4 0 0 1 16 3m0 2a2 2 0 1 0 0 4 2 2 0 0 0 0-4"/>\n</svg>\n';
const __vite_glob_0_99 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: person2
}, Symbol.toStringTag, { value: "Module" }));
const personCircle = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="M12 6a3.25 3.25 0 1 1 0 6.5A3.25 3.25 0 0 1 12 6"/>\n	<path fill="currentColor" d="M12 2c5.523 0 10 4.477 10 10s-4.477 10-10 10S2 17.523 2 12 6.477 2 12 2m0 2a8 8 0 0 0-5.5 13.807V17a3 3 0 0 1 3-3h5a3 3 0 0 1 3 3v.807A8 8 0 0 0 12 4"/>\n</svg>\n';
const __vite_glob_0_100 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: personCircle
}, Symbol.toStringTag, { value: "Module" }));
const personGearBadge = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="M18.75 13q.23.02.25.25v.68q.01.19.19.25.35.11.67.28c.1.05.23.04.3-.04l.5-.49c.09-.1.25-.1.34 0L22.07 15c.1.1.1.25 0 .35l-.49.48q-.12.14-.04.3.16.33.28.68.06.18.25.19h.68q.23.02.25.25v1.5q-.02.23-.25.25h-.68a.3.3 0 0 0-.25.19q-.11.35-.28.67c-.05.1-.04.23.04.3l.49.5c.1.09.1.25 0 .34L21 22.07c-.1.1-.25.1-.35 0l-.48-.49a.3.3 0 0 0-.3-.04q-.33.16-.68.28a.3.3 0 0 0-.19.25v.68q-.02.23-.25.25h-1.5a.25.25 0 0 1-.25-.25v-.68a.3.3 0 0 0-.19-.25 4 4 0 0 1-.67-.28.3.3 0 0 0-.3.04l-.5.49c-.09.1-.25.1-.34 0L13.93 21a.25.25 0 0 1 0-.35l.49-.48q.13-.13.04-.3-.16-.33-.28-.68a.3.3 0 0 0-.25-.19h-.68a.25.25 0 0 1-.25-.25v-1.5q.02-.23.25-.25h.68q.2-.01.25-.19.11-.35.28-.67a.3.3 0 0 0-.04-.3l-.49-.5a.25.25 0 0 1 0-.34L15 13.93c.1-.1.25-.1.35 0l.48.49q.14.13.3.04.33-.16.68-.28.18-.06.19-.25v-.68q.02-.23.25-.25zM18 16a2 2 0 1 0 0 4 2 2 0 0 0 0-4"/>\n	<path fill="currentColor" d="M13.53 14a6 6 0 0 0-1.19 2H9a3 3 0 0 0-3 3v3H4v-3a5 5 0 0 1 5-5z"/>\n	<path fill="currentColor" d="M12 2a5 5 0 1 1 0 10 5 5 0 0 1 0-10m0 2a3 3 0 1 0 0 6 3 3 0 0 0 0-6"/>\n</svg>\n';
const __vite_glob_0_101 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: personGearBadge
}, Symbol.toStringTag, { value: "Module" }));
const person = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="M12 4a3 3 0 1 0 0 6 3 3 0 0 0 0-6M7 7a5 5 0 1 1 10 0A5 5 0 0 1 7 7m2 9a3 3 0 0 0-3 3v3H4v-3a5 5 0 0 1 5-5h6a5 5 0 0 1 5 5l-.032 3h-2L18 19a3 3 0 0 0-3-3z"/>\n</svg>\n';
const __vite_glob_0_102 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: person
}, Symbol.toStringTag, { value: "Module" }));
const plusSmall = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="M13 11h7v2h-7v7h-2v-7H4v-2h7V4h2z"/>\n</svg>\n';
const __vite_glob_0_103 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: plusSmall
}, Symbol.toStringTag, { value: "Module" }));
const plus = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="M13 11h9v2h-9v9h-2v-9H2v-2h9V2h2z"/>\n</svg>\n';
const __vite_glob_0_104 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: plus
}, Symbol.toStringTag, { value: "Module" }));
const puzzlePieceFilled = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="M11 2a2.5 2.5 0 0 1 2.5 2.5v.75c0 .14.11.25.25.25H18a1 1 0 0 1 1 1v3.75q.02.23.25.25H20a2.5 2.5 0 0 1 0 5h-.75a.25.25 0 0 0-.25.25v4.75a1 1 0 0 1-1 1h-4.25a.25.25 0 0 1-.25-.25V20a2.5 2.5 0 0 0-5 0v1.25q-.02.23-.25.25H4a1 1 0 0 1-1-1v-4.25c0-.14.11-.25.25-.25H4.5a2.5 2.5 0 0 0 0-5H3.25a.25.25 0 0 1-.25-.25V6.5a1 1 0 0 1 1-1h4.25c.14 0 .25-.11.25-.25V4.5A2.5 2.5 0 0 1 11 2"/>\n</svg>\n';
const __vite_glob_0_105 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: puzzlePieceFilled
}, Symbol.toStringTag, { value: "Module" }));
const puzzlePiece = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="M10.5 1.5A3.5 3.5 0 0 1 14 5v.75c0 .14.11.25.25.25h3.25a1 1 0 0 1 1 1v2.75q.02.23.25.25H19a3.5 3.5 0 1 1 0 7h-.25a.25.25 0 0 0-.25.25V21a1 1 0 0 1-1 1h-4.75a.25.25 0 0 1-.25-.25V20.5a1.5 1.5 0 0 0-3 0v1.25q-.02.23-.25.25H3.5a1 1 0 0 1-1-1v-5.75c0-.14.11-.25.25-.25H4a1.5 1.5 0 0 0 0-3H2.75a.25.25 0 0 1-.25-.25V7a1 1 0 0 1 1-1h3.25c.14 0 .25-.11.25-.25V5a3.5 3.5 0 0 1 3.5-3.5m0 2C9.67 3.5 9 4.17 9 5v.75C9 6.99 8 8 6.75 8H4.5v2.04a3.5 3.5 0 0 1 0 6.92V20h3.04a3.5 3.5 0 0 1 6.92 0h2.04v-2.75c0-1.24 1-2.25 2.25-2.25H19a1.5 1.5 0 0 0 0-3h-.25c-1.24 0-2.25-1-2.25-2.25V8h-2.25C13.01 8 12 7 12 5.75V5c0-.83-.67-1.5-1.5-1.5"/>\n</svg>\n';
const __vite_glob_0_106 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: puzzlePiece
}, Symbol.toStringTag, { value: "Module" }));
const questionMarkCircle = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="M11.695 14.47q.564 0 .862.327.311.312.312.906 0 .55-.312.876-.297.327-.862.327-.58 0-.89-.311-.297-.328-.297-.892t.297-.89q.311-.342.89-.342M12.245 7q1.337 0 2.094.624.758.608.758 1.634 0 .907-.402 1.485-.386.564-1.202.95l-.728.372q-.327.162-.475.37a.74.74 0 0 0-.134.431q0 .208.06.43.06.21.163.402l-1.485.075a1.5 1.5 0 0 1-.342-.49 1.6 1.6 0 0 1-.134-.64q0-.519.253-.906.252-.4.876-.742l.787-.445q.46-.252.639-.49a.9.9 0 0 0 .178-.565.66.66 0 0 0-.327-.594q-.313-.222-1.054-.222-.52 0-1.04.118-.52.104-1.04.297V7.476a6 6 0 0 1 1.218-.357Q11.518 7 12.245 7"/>\n	<path fill="currentColor" d="M12 2c5.523 0 10 4.477 10 10s-4.477 10-10 10S2 17.523 2 12 6.477 2 12 2m0 2a8 8 0 1 0 0 16 8 8 0 0 0 0-16"/>\n</svg>\n';
const __vite_glob_0_107 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: questionMarkCircle
}, Symbol.toStringTag, { value: "Module" }));
const shieldCheckMark = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="m16.41 9.41-5.2 5.21L8 11.42 9.41 10l1.8 1.8L15 8z"/>\n	<path fill="currentColor" d="M20.39 4.83A14 14 0 0 1 12 22 14 14 0 0 1 3.62 4.8L12 2zM5.28 6.35A12 12 0 0 0 12 19.83a12 12 0 0 0 6.73-13.45L12 4.1z"/>\n</svg>\n';
const __vite_glob_0_108 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: shieldCheckMark
}, Symbol.toStringTag, { value: "Module" }));
const shipWheel = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="M12 2a1 1 0 0 1 1 1v1.063a7.96 7.96 0 0 1 3.903 1.619l.754-.753a1 1 0 0 1 1.414 1.414l-.754.753A7.96 7.96 0 0 1 19.936 11H21a1 1 0 1 1 0 2h-1.064a7.95 7.95 0 0 1-1.619 3.903l.754.754a1 1 0 0 1-1.414 1.414l-.754-.754A7.95 7.95 0 0 1 13 19.936V21a1 1 0 1 1-2 0v-1.064a7.96 7.96 0 0 1-3.904-1.619l-.753.754a1 1 0 0 1-1.414-1.414l.753-.754A7.96 7.96 0 0 1 4.064 13H3a1 1 0 1 1 0-2h1.064a7.96 7.96 0 0 1 1.618-3.904l-.753-.753a1 1 0 0 1 1.414-1.414l.753.753A7.96 7.96 0 0 1 11 4.063V3a1 1 0 0 1 1-1M8.524 16.889A6 6 0 0 0 11 17.915v-3.09a3 3 0 0 1-.291-.12zm4.766-2.185q-.14.068-.29.121v3.09a6 6 0 0 0 2.475-1.026zM6.085 13c.153.911.51 1.752 1.025 2.475l2.185-2.185a3 3 0 0 1-.121-.29zm8.741 0q-.054.15-.122.29l2.185 2.185A6 6 0 0 0 17.915 13zM12 10.5a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3M7.11 8.524A6 6 0 0 0 6.085 11h3.089q.053-.15.12-.291zm7.594 2.185q.069.142.122.291h3.089a6 6 0 0 0-1.026-2.476zM11 6.084A6 6 0 0 0 8.524 7.11l2.185 2.185A3 3 0 0 1 11 9.174zm2 3.09q.15.053.29.12l2.185-2.184A6 6 0 0 0 13 6.084z"/>\n</svg>\n';
const __vite_glob_0_109 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: shipWheel
}, Symbol.toStringTag, { value: "Module" }));
const slashCircle = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="M12 2a10 10 0 1 1 0 20 10 10 0 0 1 0-20M5.68 7.1A8 8 0 0 0 16.9 18.32zM12 4c-1.85 0-3.55.63-4.9 1.68L18.32 16.9A8 8 0 0 0 12 4"/>\n</svg>\n';
const __vite_glob_0_110 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: slashCircle
}, Symbol.toStringTag, { value: "Module" }));
const squareAndArrowUp = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="M9 11H7a1 1 0 0 0-1 1v7a1 1 0 0 0 1 1h10a1 1 0 0 0 1-1v-7a1 1 0 0 0-1-1h-2V9h2a3 3 0 0 1 3 3v7a3 3 0 0 1-3 3H7c-1.66 0-3-1.34-3-3v-7a3 3 0 0 1 3-3h2z"/>\n	<path fill="currentColor" d="M16.59 5.59 15.17 7 13 4.828V16h-2V4.828L8.83 7 7.41 5.59 12 1z"/>\n</svg>\n';
const __vite_glob_0_111 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: squareAndArrowUp
}, Symbol.toStringTag, { value: "Module" }));
const squareArrowRightTop = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="M11.772 8H5a1 1 0 0 0-1 1v10a1 1 0 0 0 1 1h10a1 1 0 0 0 1-1v-6.765l2-2V19c0 1.66-1.34 3-3 3H5c-1.66 0-3-1.34-3-3V9a3 3 0 0 1 3-3h8.772z"/>\n	<path fill="currentColor" d="M22 11h-2V5.407l-9.296 9.296L9.3 13.3 18.6 4H13V2h9z"/>\n</svg>\n';
const __vite_glob_0_112 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: squareArrowRightTop
}, Symbol.toStringTag, { value: "Module" }));
const squaresStackPlus = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="M15 13h3v2h-3v3h-2v-3h-3v-2h3v-3h2z"/>\n	<path fill="currentColor" d="M18 5v1h1c1.66 0 3 1.34 3 3v10c0 1.658-1.308 3-3 3H9c-1.66 0-3-1.34-3-3v-1H5c-1.66 0-3-1.34-3-3V5a3 3 0 0 1 3-3h10c1.66 0 3 1.34 3 3M9 8a1 1 0 0 0-1 1v10a1 1 0 0 0 1 1h10a1 1 0 0 0 1-1V9a1 1 0 0 0-1-1zM5 4a1 1 0 0 0-1 1v10a1 1 0 0 0 1 1h1V9a3 3 0 0 1 3-3h7V5a1 1 0 0 0-1-1z"/>\n</svg>\n';
const __vite_glob_0_113 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: squaresStackPlus
}, Symbol.toStringTag, { value: "Module" }));
const stack = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="M19 8a3 3 0 0 1 3 3v8a3 3 0 0 1-3 3H5a3 3 0 0 1-3-3v-8a3 3 0 0 1 3-3zM5 10a1 1 0 0 0-1 1v8a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-8a1 1 0 0 0-1-1z"/>\n	<path fill="currentColor" d="M18 5a2 2 0 0 1 2 2H4c0-1.1.9-2 2-2zM16 2a2 2 0 0 1 2 2H6c0-1.1.9-2 2-2z"/>\n</svg>\n';
const __vite_glob_0_114 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: stack
}, Symbol.toStringTag, { value: "Module" }));
const sun = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="M13 22h-2v-3.07c.65.09 1.35.09 2 0zM6.4 16.2q.6.8 1.4 1.4l-2.16 2.18-1.42-1.42zM19.78 18.36l-1.42 1.42-2.17-2.17q.8-.6 1.42-1.42z"/>\n	<path fill="currentColor" d="M12 7a5 5 0 1 1 0 10 5 5 0 0 1 0-10m0 2a3 3 0 1 0 0 6 3 3 0 0 0 0-6"/>\n	<path fill="currentColor" d="M5.07 11c-.1.65-.1 1.35 0 2H2v-2zM22 13h-3.07c.1-.65.1-1.35 0-2H22zM7.8 6.4Q7 7 6.4 7.8L4.21 5.65l1.42-1.42zM19.78 5.64 17.6 7.8a7 7 0 0 0-1.42-1.42l2.17-2.17zM13 5.07c-.65-.1-1.35-.1-2 0V2h2z"/>\n</svg>\n';
const __vite_glob_0_115 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: sun
}, Symbol.toStringTag, { value: "Module" }));
const tableArrowDownBadge = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="M19 14v4.17l1.58-1.58L22 18l-4 4-4-4 1.42-1.41L17 18.17V14z"/>\n	<path fill="currentColor" d="M18 4c1.57 0 3 1.34 3 3v5.8q-.91-.53-2-.72v-1.33h-6v2.5h1.34a6 6 0 0 0-2 6.75H6a3 3 0 0 1-3-3V7a3 3 0 0 1 3-3zM5 17a1 1 0 0 0 1 1h5v-2.75H5zm0-3.75h6v-2.5H5zM6 6a1 1 0 0 0-1 1v1.75h6V6zm7 2.75h6V7a1 1 0 0 0-1-1h-5z"/>\n</svg>\n';
const __vite_glob_0_116 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: tableArrowDownBadge
}, Symbol.toStringTag, { value: "Module" }));
const terminal = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="m11.4 12-4 4L6 14.6 8.57 12 6 9.4 7.4 8zM18 16h-6v-2h6z"/>\n	<path fill="currentColor" d="M19 4a3 3 0 0 1 3 3v10a3 3 0 0 1-3 3H5a3 3 0 0 1-3-3V7a3 3 0 0 1 3-3zM5 6a1 1 0 0 0-1 1v10a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1V7a1 1 0 0 0-1-1z"/>\n</svg>\n';
const __vite_glob_0_117 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: terminal
}, Symbol.toStringTag, { value: "Module" }));
const trash = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" fill-rule="evenodd" d="M8 4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2h5v2h-1.08L19 19.046A3 3 0 0 1 16 22H8a3 3 0 0 1-3-2.954L4.08 8H3V6h5zM6.087 8l.91 10.917L7 19a1 1 0 0 0 1 1h8a1 1 0 0 0 1-1l.003-.083L17.914 8zM14 6h-4V4h4zm-3 4v8H9v-8zm4 0v8h-2v-8z"/>\n</svg>\n';
const __vite_glob_0_118 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: trash
}, Symbol.toStringTag, { value: "Module" }));
const underlined = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">\n	<path fill="currentColor" d="M20 22H4v-2h16zM8.7 12.07q0 1.92.81 2.8.84.87 2.55.87 1.61 0 2.47-.91.89-.94.89-2.67V2h2.37v10.16q0 1.78-.72 3.1a4.7 4.7 0 0 1-2.04 2.02q-1.32.81-3.14.72-2.83.09-4.27-1.44c-.95-.9-1.42-2.36-1.42-4.2V2h2.5z"/>\n</svg>\n';
const __vite_glob_0_119 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: underlined
}, Symbol.toStringTag, { value: "Module" }));
const styles$i = css`
	:host {
		display: inline-block;
		width: 100%;
		height: 100%;
		aspect-ratio: 1 / 1;
		color: inherit;
	}
	.icon__container {
		width: 100%;
		height: 100%;
		display: flex;
		align-items: center;
		justify-content: center;
	}
	svg {
		display: block;
		width: 100%;
		height: 100%;
		object-fit: contain;
	}
`;
function template$h(iconSvg) {
  if (!iconSvg) {
    return html`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"></svg>`;
  }
  return html`
		<div class="icon__container">
			${unsafeHTML(iconSvg)}
		</div>
	`;
}
const aliases = {
  // apartment-building
  "office": "apartment-building",
  // arrow-2-counter-clockwise
  "refresh": "arrow-2-counter-clockwise",
  "reload": "arrow-2-counter-clockwise",
  "sync": "arrow-2-counter-clockwise",
  // arrow-down-in-bucket
  "download": "arrow-down-in-bucket",
  // arrow-up-arrow-down
  "sort": "arrow-up-arrow-down",
  // arrow-uturn-backward
  "undo": "arrow-uturn-backward",
  // arrow-uturn-forward
  "redo": "arrow-uturn-forward",
  // brackets-ellipsis
  "code": "brackets-ellipsis",
  "embed": "brackets-ellipsis",
  // business-suitcase
  "work": "business-suitcase",
  // calendar-event
  "calendar": "calendar-event",
  "event": "calendar-event",
  // certificate
  "license": "certificate",
  // chart-x-y-axis-line
  "analytics": "chart-x-y-axis-line",
  "chart-line": "chart-x-y-axis-line",
  "graph": "chart-x-y-axis-line",
  // check-mark
  "checked": "check-mark",
  // check-mark-circle
  "success": "check-mark-circle",
  "valid": "check-mark-circle",
  // check-mark-extra-small
  "checked-extra-small": "check-mark-extra-small",
  // check-mark-small
  "checked-small": "check-mark-small",
  // chevron-left
  "back": "chevron-left",
  // chevron-right
  "forward": "chevron-right",
  // circle-dashed
  "icon-placeholder": "circle-dashed",
  // clock-arrow-counter-clockwise
  "history": "clock-arrow-counter-clockwise",
  // cloud-arrow-up
  "backup-in-cloud": "cloud-arrow-up",
  "deploy": "cloud-arrow-up",
  "upload-to-cloud": "cloud-arrow-up",
  // cylinder-split
  "database": "cylinder-split",
  // cylinder-split-slash
  "database-disabled": "cylinder-split-slash",
  "database-unavailable": "cylinder-split-slash",
  // ellipsis
  "more": "ellipsis",
  // envelope
  "email": "envelope",
  "mail": "envelope",
  // exclamation-circle
  "error": "exclamation-circle",
  "invalid": "exclamation-circle",
  // exclamation-triangle-filled
  "alert": "exclamation-triangle-filled",
  "warning": "exclamation-triangle-filled",
  // eye
  "show": "eye",
  "visible": "eye",
  // eye-slash
  "hidden": "eye-slash",
  "hide": "eye-slash",
  // file-text
  "document": "file-text",
  "file": "file-text",
  // folder
  "directory": "folder",
  // folder-stack
  "directories": "folder-stack",
  // gear
  "global-settings": "gear",
  // heart-filled
  "favorite": "heart-filled",
  "love": "heart-filled",
  // house
  "home": "house",
  // inbox
  "messages": "inbox",
  // info-circle
  "info": "info-circle",
  "information": "info-circle",
  // list
  "menu": "list",
  // list-arrow-down
  "sort-descending": "list-arrow-down",
  // list-arrow-up
  "sort-ascending": "list-arrow-up",
  // list-decreasing-lines
  "filter": "list-decreasing-lines",
  // lock-closed
  "lock": "lock-closed",
  "locked": "lock-closed",
  "secure": "lock-closed",
  // lock-open
  "unlocked": "lock-open",
  // ship-wheel
  "k8s": "ship-wheel",
  "kubernetes": "ship-wheel",
  // magnifier
  "search": "magnifier",
  // minus
  "delete": "minus",
  // minus-small
  "delete-small": "minus-small",
  // moon
  "dark-mode": "moon",
  "night": "moon",
  // pencil
  "write": "pencil",
  // pencil-on-square
  "edit": "pencil-on-square",
  // person
  "user": "person",
  // person-2
  "group": "person-2",
  "team": "person-2",
  "users": "person-2",
  // person-circle
  "account": "person-circle",
  "profile": "person-circle",
  // person-gear-badge
  "user-admin": "person-gear-badge",
  "user-settings": "person-gear-badge",
  // plus
  "add": "plus",
  // plus-small
  "add-small": "plus-small",
  // puzzle-piece
  "extension": "puzzle-piece",
  "module": "puzzle-piece",
  "plugin": "puzzle-piece",
  // question-mark-circle
  "help": "question-mark-circle",
  "question": "question-mark-circle",
  // shield-check-mark
  "security": "shield-check-mark",
  "verified": "shield-check-mark",
  // slash-circle
  "blocked": "slash-circle",
  "forbidden": "slash-circle",
  // square-and-arrow-up
  "share": "square-and-arrow-up",
  // square-arrow-right-top
  "external-link": "square-arrow-right-top",
  // squares-stack-plus
  "add-stack": "squares-stack-plus",
  // sun
  "day": "sun",
  "light-mode": "sun",
  // table-arrow-down-badge
  "download-table": "table-arrow-down-badge",
  // terminal
  "cli": "terminal",
  "console": "terminal",
  // trash
  "remove": "trash"
};
var __defProp$$ = Object.defineProperty;
var __getOwnPropDesc$13 = Object.getOwnPropertyDescriptor;
var __decorateClass$14 = (decorators, target, key, kind) => {
  var result = kind > 1 ? void 0 : kind ? __getOwnPropDesc$13(target, key) : target;
  for (var i = decorators.length - 1, decorator; i >= 0; i--)
    if (decorator = decorators[i])
      result = (kind ? decorator(target, key, result) : decorator(result)) || result;
  if (kind && result) __defProp$$(target, key, result);
  return result;
};
const iconModules = /* @__PURE__ */ Object.assign({ "./ndd-icons/apartment-building.svg": __vite_glob_0_0, "./ndd-icons/arrow-2-counter-clockwise.svg": __vite_glob_0_1, "./ndd-icons/arrow-down-in-bucket.svg": __vite_glob_0_2, "./ndd-icons/arrow-down.svg": __vite_glob_0_3, "./ndd-icons/arrow-left.svg": __vite_glob_0_4, "./ndd-icons/arrow-right.svg": __vite_glob_0_5, "./ndd-icons/arrow-up-arrow-down.svg": __vite_glob_0_6, "./ndd-icons/arrow-up.svg": __vite_glob_0_7, "./ndd-icons/arrow-uturn-backward.svg": __vite_glob_0_8, "./ndd-icons/arrow-uturn-forward.svg": __vite_glob_0_9, "./ndd-icons/bold.svg": __vite_glob_0_10, "./ndd-icons/brackets-ellipsis.svg": __vite_glob_0_11, "./ndd-icons/bullet-list.svg": __vite_glob_0_12, "./ndd-icons/business-suitcase.svg": __vite_glob_0_13, "./ndd-icons/calendar-event.svg": __vite_glob_0_14, "./ndd-icons/caret-down-extra-small.svg": __vite_glob_0_15, "./ndd-icons/caret-down-small.svg": __vite_glob_0_16, "./ndd-icons/caret-down.svg": __vite_glob_0_17, "./ndd-icons/caret-left-extra-small.svg": __vite_glob_0_18, "./ndd-icons/caret-left-small.svg": __vite_glob_0_19, "./ndd-icons/caret-left.svg": __vite_glob_0_20, "./ndd-icons/caret-right-extra-small.svg": __vite_glob_0_21, "./ndd-icons/caret-right-small.svg": __vite_glob_0_22, "./ndd-icons/caret-right.svg": __vite_glob_0_23, "./ndd-icons/caret-up-extra-small.svg": __vite_glob_0_24, "./ndd-icons/caret-up-small.svg": __vite_glob_0_25, "./ndd-icons/caret-up.svg": __vite_glob_0_26, "./ndd-icons/certificate.svg": __vite_glob_0_27, "./ndd-icons/chart-x-y-axis-line.svg": __vite_glob_0_28, "./ndd-icons/check-mark-circle.svg": __vite_glob_0_29, "./ndd-icons/check-mark-extra-small.svg": __vite_glob_0_30, "./ndd-icons/check-mark-small.svg": __vite_glob_0_31, "./ndd-icons/check-mark.svg": __vite_glob_0_32, "./ndd-icons/chevron-double-left-extra-small.svg": __vite_glob_0_33, "./ndd-icons/chevron-double-left-small.svg": __vite_glob_0_34, "./ndd-icons/chevron-double-left.svg": __vite_glob_0_35, "./ndd-icons/chevron-double-right-extra-small.svg": __vite_glob_0_36, "./ndd-icons/chevron-double-right-small.svg": __vite_glob_0_37, "./ndd-icons/chevron-double-right.svg": __vite_glob_0_38, "./ndd-icons/chevron-down-extra-small.svg": __vite_glob_0_39, "./ndd-icons/chevron-down-small.svg": __vite_glob_0_40, "./ndd-icons/chevron-down.svg": __vite_glob_0_41, "./ndd-icons/chevron-left-extra-small.svg": __vite_glob_0_42, "./ndd-icons/chevron-left-small.svg": __vite_glob_0_43, "./ndd-icons/chevron-left.svg": __vite_glob_0_44, "./ndd-icons/chevron-right-extra-small.svg": __vite_glob_0_45, "./ndd-icons/chevron-right-small.svg": __vite_glob_0_46, "./ndd-icons/chevron-right.svg": __vite_glob_0_47, "./ndd-icons/chevron-up-down.svg": __vite_glob_0_48, "./ndd-icons/chevron-up-extra-small.svg": __vite_glob_0_49, "./ndd-icons/chevron-up-small.svg": __vite_glob_0_50, "./ndd-icons/chevron-up.svg": __vite_glob_0_51, "./ndd-icons/circle-dashed.svg": __vite_glob_0_52, "./ndd-icons/circle-filled-extra-small.svg": __vite_glob_0_53, "./ndd-icons/circle-filled-small.svg": __vite_glob_0_54, "./ndd-icons/circle-filled.svg": __vite_glob_0_55, "./ndd-icons/clock-arrow-counter-clockwise.svg": __vite_glob_0_56, "./ndd-icons/cloud-arrow-down.svg": __vite_glob_0_57, "./ndd-icons/cloud-arrow-up.svg": __vite_glob_0_58, "./ndd-icons/cloud.svg": __vite_glob_0_59, "./ndd-icons/cylinder-split-slash.svg": __vite_glob_0_60, "./ndd-icons/cylinder-split.svg": __vite_glob_0_61, "./ndd-icons/dismiss-circle-filled.svg": __vite_glob_0_62, "./ndd-icons/dismiss-circle.svg": __vite_glob_0_63, "./ndd-icons/dismiss-extra-small.svg": __vite_glob_0_64, "./ndd-icons/dismiss-small.svg": __vite_glob_0_65, "./ndd-icons/dismiss.svg": __vite_glob_0_66, "./ndd-icons/ellipsis.svg": __vite_glob_0_67, "./ndd-icons/envelope.svg": __vite_glob_0_68, "./ndd-icons/euro.svg": __vite_glob_0_69, "./ndd-icons/exclamation-circle.svg": __vite_glob_0_70, "./ndd-icons/exclamation-triangle-filled.svg": __vite_glob_0_71, "./ndd-icons/exclamation-triangle.svg": __vite_glob_0_72, "./ndd-icons/eye-slash.svg": __vite_glob_0_73, "./ndd-icons/eye.svg": __vite_glob_0_74, "./ndd-icons/file-text.svg": __vite_glob_0_75, "./ndd-icons/folder-stack.svg": __vite_glob_0_76, "./ndd-icons/folder.svg": __vite_glob_0_77, "./ndd-icons/gear.svg": __vite_glob_0_78, "./ndd-icons/heart-filled.svg": __vite_glob_0_79, "./ndd-icons/heart.svg": __vite_glob_0_80, "./ndd-icons/house.svg": __vite_glob_0_81, "./ndd-icons/inbox.svg": __vite_glob_0_82, "./ndd-icons/info-circle.svg": __vite_glob_0_83, "./ndd-icons/italic.svg": __vite_glob_0_84, "./ndd-icons/list-arrow-down.svg": __vite_glob_0_85, "./ndd-icons/list-arrow-up.svg": __vite_glob_0_86, "./ndd-icons/list-decreasing-lines.svg": __vite_glob_0_87, "./ndd-icons/list.svg": __vite_glob_0_88, "./ndd-icons/lock-closed.svg": __vite_glob_0_89, "./ndd-icons/lock-open.svg": __vite_glob_0_90, "./ndd-icons/magnifier.svg": __vite_glob_0_91, "./ndd-icons/minus-extra-small.svg": __vite_glob_0_92, "./ndd-icons/minus-small.svg": __vite_glob_0_93, "./ndd-icons/minus.svg": __vite_glob_0_94, "./ndd-icons/moon.svg": __vite_glob_0_95, "./ndd-icons/numbered-list.svg": __vite_glob_0_96, "./ndd-icons/pencil-on-square.svg": __vite_glob_0_97, "./ndd-icons/pencil.svg": __vite_glob_0_98, "./ndd-icons/person-2.svg": __vite_glob_0_99, "./ndd-icons/person-circle.svg": __vite_glob_0_100, "./ndd-icons/person-gear-badge.svg": __vite_glob_0_101, "./ndd-icons/person.svg": __vite_glob_0_102, "./ndd-icons/plus-small.svg": __vite_glob_0_103, "./ndd-icons/plus.svg": __vite_glob_0_104, "./ndd-icons/puzzle-piece-filled.svg": __vite_glob_0_105, "./ndd-icons/puzzle-piece.svg": __vite_glob_0_106, "./ndd-icons/question-mark-circle.svg": __vite_glob_0_107, "./ndd-icons/shield-check-mark.svg": __vite_glob_0_108, "./ndd-icons/ship-wheel.svg": __vite_glob_0_109, "./ndd-icons/slash-circle.svg": __vite_glob_0_110, "./ndd-icons/square-and-arrow-up.svg": __vite_glob_0_111, "./ndd-icons/square-arrow-right-top.svg": __vite_glob_0_112, "./ndd-icons/squares-stack-plus.svg": __vite_glob_0_113, "./ndd-icons/stack.svg": __vite_glob_0_114, "./ndd-icons/sun.svg": __vite_glob_0_115, "./ndd-icons/table-arrow-down-badge.svg": __vite_glob_0_116, "./ndd-icons/terminal.svg": __vite_glob_0_117, "./ndd-icons/trash.svg": __vite_glob_0_118, "./ndd-icons/underlined.svg": __vite_glob_0_119 });
const iconRegistry = /* @__PURE__ */ new Map();
for (const [path, module] of Object.entries(iconModules)) {
  const name = path.replace("./ndd-icons/", "").replace(".svg", "");
  iconRegistry.set(name, module.default);
}
[
  ...iconRegistry.keys(),
  ...Object.keys(aliases)
].sort();
let NDDIcon = class extends LitElement {
  constructor() {
    super(...arguments);
    this.name = "circle-dashed";
    this._iconSvg = null;
  }
  connectedCallback() {
    super.connectedCallback();
    this._iconSvg = this._loadIcon(this.name);
  }
  updated(changedProperties) {
    if (changedProperties.has("name") && this.name) {
      this._iconSvg = this._loadIcon(this.name);
    }
  }
  _loadIcon(name) {
    const resolvedName = aliases[name] ?? name;
    const svg2 = iconRegistry.get(resolvedName);
    if (svg2) {
      return svg2;
    }
    console.warn(`NDDIcon: icon "${resolvedName}" not found`);
    return null;
  }
  render() {
    return template$h(this._iconSvg);
  }
};
NDDIcon.styles = styles$i;
__decorateClass$14([
  property({ type: String })
], NDDIcon.prototype, "name", 2);
__decorateClass$14([
  state()
], NDDIcon.prototype, "_iconSvg", 2);
NDDIcon = __decorateClass$14([
  customElement("ndd-icon")
], NDDIcon);
var __defProp$_ = Object.defineProperty;
var __getOwnPropDesc$12 = Object.getOwnPropertyDescriptor;
var __decorateClass$13 = (decorators, target, key, kind) => {
  var result = kind > 1 ? void 0 : kind ? __getOwnPropDesc$12(target, key) : target;
  for (var i = decorators.length - 1, decorator; i >= 0; i--)
    if (decorator = decorators[i])
      result = (kind ? decorator(target, key, result) : decorator(result)) || result;
  if (kind && result) __defProp$_(target, key, result);
  return result;
};
let NDDButton = class extends LitElement {
  constructor() {
    super(...arguments);
    this.variant = "neutral-tinted";
    this.size = "md";
    this.fullWidth = false;
    this.expandable = false;
    this.type = "button";
    this.popovertarget = void 0;
    this.disabled = false;
    this.text = "";
    this.startIcon = "";
    this.endIcon = "";
    this.accessibleLabel = "";
    this.href = void 0;
    this.target = void 0;
    this.rel = void 0;
    this._warnedA11y = false;
  }
  updated() {
    const isEmpty = !this.text && !this.accessibleLabel;
    if (isEmpty && !this._warnedA11y) {
      this._warnedA11y = true;
      console.warn("<ndd-button>: button has no text or accessible-label. This produces an inaccessible button (WCAG SC 4.1.2).");
    } else if (!isEmpty) {
      this._warnedA11y = false;
    }
  }
  _handleClick(e) {
    if (this.disabled) {
      e.preventDefault();
      e.stopPropagation();
      return;
    }
  }
  /** Resolves the effective rel value for link rendering. */
  _resolvedRel() {
    if (this.rel) return this.rel;
    if (this.target === "_blank") return "noopener noreferrer";
    return "";
  }
  render() {
    return template$i.call(this, {
      handleClick: this._handleClick.bind(this)
    });
  }
};
NDDButton.styles = styles$j;
__decorateClass$13([
  property({ type: String, reflect: true })
], NDDButton.prototype, "variant", 2);
__decorateClass$13([
  property({ type: String, reflect: true })
], NDDButton.prototype, "size", 2);
__decorateClass$13([
  property({ type: Boolean, reflect: true, attribute: "full-width" })
], NDDButton.prototype, "fullWidth", 2);
__decorateClass$13([
  property({ type: Boolean, reflect: true, attribute: "expandable" })
], NDDButton.prototype, "expandable", 2);
__decorateClass$13([
  property({ type: String, reflect: true })
], NDDButton.prototype, "type", 2);
__decorateClass$13([
  property({ type: String })
], NDDButton.prototype, "popovertarget", 2);
__decorateClass$13([
  property({ type: Boolean, reflect: true })
], NDDButton.prototype, "disabled", 2);
__decorateClass$13([
  property({ type: String })
], NDDButton.prototype, "text", 2);
__decorateClass$13([
  property({ type: String, attribute: "start-icon" })
], NDDButton.prototype, "startIcon", 2);
__decorateClass$13([
  property({ type: String, attribute: "end-icon" })
], NDDButton.prototype, "endIcon", 2);
__decorateClass$13([
  property({ type: String, attribute: "accessible-label" })
], NDDButton.prototype, "accessibleLabel", 2);
__decorateClass$13([
  property({ type: String, reflect: true })
], NDDButton.prototype, "href", 2);
__decorateClass$13([
  property({ type: String })
], NDDButton.prototype, "target", 2);
__decorateClass$13([
  property({ type: String })
], NDDButton.prototype, "rel", 2);
NDDButton = __decorateClass$13([
  customElement("ndd-button")
], NDDButton);
const styles$h = css`
	/* # Host */

	:host {
		display: inline-block;
		-webkit-tap-highlight-color: transparent;
	}

	:host([hidden]) {
		display: none;
	}

	:host([disabled]) {
		opacity: var(--primitives-opacity-disabled);
		pointer-events: none;
	}


	/* # Base */

	.icon-button {
		appearance: none;
		border: none;
		margin: 0;
		padding: 0;
		background: none;
		font: inherit;
		box-sizing: border-box;
		display: inline-flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		transition:
			background-color 0.15s ease-out,
			color 0.15s ease-out;
	}

	@media (prefers-reduced-motion: reduce) {
		.icon-button {
			transition: none;
		}
	}


	/* # Focus */

	.icon-button:focus-visible {
		box-shadow: var(--semantics-focus-ring-box-shadow);
		outline: var(--semantics-focus-ring-outline);
	}

	.icon-button:focus:not(:focus-visible) {
		outline: none;
	}


	/* # Sizes */

	/* ## Size: XS */

	:host([size='xs']) .icon-button {
		width: auto;
		height: var(--semantics-controls-xs-min-size);
		min-width: var(--semantics-controls-xs-min-size);
		min-height: var(--semantics-controls-xs-min-size);
		padding: var(--primitives-space-4);
		border-radius: var(--semantics-controls-xs-corner-radius);
	}

	:host([size='xs']) .icon-button__icon {
		width: var(--primitives-space-16);
		height: var(--primitives-space-16);
	}

	:host([size='xs']) .icon-button__disclosure-icon {
		width: var(--primitives-space-16);
		height: var(--primitives-space-16);
	}

	/* ## Size: SM */

	:host([size='sm']) .icon-button {
		width: auto;
		height: var(--semantics-controls-sm-min-size);
		min-width: var(--semantics-controls-sm-min-size);
		min-height: var(--semantics-controls-sm-min-size);
		padding: var(--primitives-space-6);
		border-radius: var(--semantics-controls-sm-corner-radius);
	}

	:host([size='sm']) .icon-button__icon {
		width: var(--primitives-space-20);
		height: var(--primitives-space-20);
	}

	:host([size='sm']) .icon-button__disclosure-icon {
		width: var(--primitives-space-20);
		height: var(--primitives-space-20);
		margin-right: calc(var(--primitives-space-2) * -1);
	}

	/* ## Size: MD (Default) */

	:host([size='md']) .icon-button,
	:host(:not([size])) .icon-button {
		width: auto;
		height: var(--semantics-controls-md-min-size);
		min-width: var(--semantics-controls-md-min-size);
		min-height: var(--semantics-controls-md-min-size);
		padding: var(--primitives-space-8);
		border-radius: var(--semantics-controls-md-corner-radius);
	}

	:host([size='md']) .icon-button__icon,
	:host(:not([size])) .icon-button__icon {
		width: var(--primitives-space-24);
		height: var(--primitives-space-24);
	}

	:host([size='md']) .icon-button__disclosure-icon,
	:host(:not([size])) .icon-button__disclosure-icon {
		width: var(--primitives-space-20);
		height: var(--primitives-space-20);
		margin-right: calc(var(--primitives-space-2) * -1);
	}

	/* ## Size: LG */

	:host([size='lg']) .icon-button {
		width: auto;
		height: var(--semantics-controls-lg-min-size);
		min-width: var(--semantics-controls-lg-min-size);
		min-height: var(--semantics-controls-lg-min-size);
		padding: var(--primitives-space-8);
		border-radius: var(--semantics-controls-lg-corner-radius);
	}

	:host([size='lg']) .icon-button__icon {
		width: var(--primitives-space-24);
		height: var(--primitives-space-24);
	}

	:host([size='lg']) .icon-button__disclosure-icon {
		width: var(--primitives-space-20);
		height: var(--primitives-space-20);
		margin-right: calc(var(--primitives-space-2) * -1);
	}


	/* # Variants */

	/* ## Variant: neutral-tinted (secondary, default) */

	:host([variant='neutral-tinted']) .icon-button,
	:host([variant='secondary']) .icon-button,
	:host(:not([variant])) .icon-button {
		background-color: var(--semantics-buttons-neutral-tinted-background-color);
		color: var(--semantics-buttons-neutral-tinted-content-color);
	}

	:host([variant='neutral-tinted']) .icon-button:hover,
	:host([variant='secondary']) .icon-button:hover,
	:host(:not([variant])) .icon-button:hover {
		background-color: var(--semantics-buttons-neutral-tinted-is-hovered-background-color);
		color: var(--semantics-buttons-neutral-tinted-is-hovered-content-color);
	}

	:host([variant='neutral-tinted']) .icon-button:active,
	:host([variant='secondary']) .icon-button:active,
	:host(:not([variant])) .icon-button:active {
		background-color: var(--semantics-buttons-neutral-tinted-is-active-background-color);
		color: var(--semantics-buttons-neutral-tinted-is-active-content-color);
	}

	/* ## Variant: neutral-transparent */

	:host([variant='neutral-transparent']) .icon-button {
		background-color: transparent;
		color: var(--semantics-buttons-neutral-transparent-content-color);
	}

	:host([variant='neutral-transparent']) .icon-button:hover {
		background-color: transparent;
		color: var(--semantics-buttons-neutral-transparent-is-hovered-content-color);
	}

	:host([variant='neutral-transparent']) .icon-button:active {
		color: var(--semantics-buttons-neutral-transparent-is-active-content-color);
	}

	/* ## Variant: accent-filled (primary) */

	:host([variant='accent-filled']) .icon-button,
	:host([variant='primary']) .icon-button {
		background-color: var(--semantics-buttons-accent-filled-background-color);
		color: var(--semantics-buttons-accent-filled-content-color);
	}

	:host([variant='accent-filled']) .icon-button:hover,
	:host([variant='primary']) .icon-button:hover {
		background-color: var(--semantics-buttons-accent-filled-is-hovered-background-color);
		color: var(--semantics-buttons-accent-filled-is-hovered-content-color);
	}

	:host([variant='accent-filled']) .icon-button:active,
	:host([variant='primary']) .icon-button:active {
		background-color: var(--semantics-buttons-accent-filled-is-active-background-color);
		color: var(--semantics-buttons-accent-filled-is-active-content-color);
	}

	/* ## Variant: accent-outlined */

	:host([variant='accent-outlined']) .icon-button {
		background-color: transparent;
		border-width: var(--semantics-buttons-accent-outlined-border-thickness);
		border-style: solid;
		border-color: var(--semantics-buttons-accent-outlined-border-color);
		color: var(--semantics-buttons-accent-outlined-content-color);
	}

	:host([variant='accent-outlined'][size='lg']) .icon-button {
		padding: calc(var(--primitives-space-8) - var(--semantics-buttons-accent-outlined-border-thickness));
	}

	:host([variant='accent-outlined'][size='md']) .icon-button {
		padding: calc(var(--primitives-space-8) - var(--semantics-buttons-accent-outlined-border-thickness));
	}

	:host([variant='accent-outlined'][size='sm']) .icon-button {
		padding: calc(var(--primitives-space-6) - var(--semantics-buttons-accent-outlined-border-thickness));
	}

	:host([variant='accent-outlined'][size='xs']) .icon-button {
		padding: calc(var(--primitives-space-4) - var(--semantics-buttons-accent-outlined-border-thickness));
	}

	:host([variant='accent-outlined']) .icon-button:hover {
		border-color: var(--semantics-buttons-accent-outlined-is-hovered-border-color);
		color: var(--semantics-buttons-accent-outlined-is-hovered-content-color);
	}

	:host([variant='accent-outlined']) .icon-button:active {
		border-color: var(--semantics-buttons-accent-outlined-is-active-border-color);
		color: var(--semantics-buttons-accent-outlined-is-active-content-color);
	}

	/* ## Variant: accent-transparent */

	:host([variant='accent-transparent']) .icon-button {
		background-color: transparent;
		color: var(--semantics-buttons-accent-transparent-content-color);
	}

	:host([variant='accent-transparent']) .icon-button:hover {
		color: var(--semantics-buttons-accent-transparent-is-hovered-content-color);
	}

	:host([variant='accent-transparent']) .icon-button:active {
		color: var(--semantics-buttons-accent-transparent-is-active-content-color);
	}

	/* ## Variant: danger-tinted (destructive) */

	:host([variant='danger-tinted']) .icon-button,
	:host([variant='destructive']) .icon-button {
		background-color: var(--semantics-buttons-danger-tinted-background-color);
		color: var(--semantics-buttons-danger-tinted-content-color);
	}

	:host([variant='danger-tinted']) .icon-button:hover,
	:host([variant='destructive']) .icon-button:hover {
		background-color: var(--semantics-buttons-danger-tinted-is-hovered-background-color);
		color: var(--semantics-buttons-danger-tinted-is-hovered-content-color);
	}

	:host([variant='danger-tinted']) .icon-button:active,
	:host([variant='destructive']) .icon-button:active {
		background-color: var(--semantics-buttons-danger-tinted-is-active-background-color);
		color: var(--semantics-buttons-danger-tinted-is-active-content-color);
	}


	/* # Elements */

	.icon-button__icon-area {
		display: inline-flex;
		flex-direction: row;
		align-items: center;
		justify-content: center;
	}

	.icon-button__icon {
		display: flex;
		flex-shrink: 0;
		align-items: center;
		justify-content: center;
	}

	.icon-button__disclosure-icon {
		display: flex;
		flex-shrink: 0;
	}

	.icon-button__text {
		display: none;
		text-align: center;
		white-space: nowrap;
		color: inherit;
		font: var(--primitives-font-body-xxs-bold-flat);
	}

	:host([size='lg']) .icon-button__text {
		display: block;
	}
`;
const tooltipStyles = css`


	/* # Host */

	:host {
		display: contents;
		--_z-index: 10000;
		--_show-delay: 700ms;
		--_show-duration: 150ms;
		--_hide-delay: 50; /* unitless ms, read by JavaScript */
		--_hide-duration: 150ms;
		--_offset: 4; /* px, unitless — read by JS */
		--_shift-padding: 8; /* px, unitless — read by JS */
		--_max-width: var(--primitives-area-280);
	}

	:host([hidden]) {
		display: none;
	}


	/* # Tooltip */

	.tooltip {
		position: fixed;
		z-index: var(--_z-index);
		opacity: 0;
		pointer-events: none;
		visibility: hidden;
		transition:
			opacity var(--_hide-duration) ease,
			visibility 0ms linear var(--_hide-duration),
			pointer-events 0ms linear var(--_hide-duration);
	}

	.tooltip.is-visible {
		opacity: 1;
		visibility: visible;
		pointer-events: auto;
		transition:
			opacity var(--_show-duration) ease var(--_show-delay),
			visibility 0ms linear,
			pointer-events 0ms linear var(--_show-delay);
	}

	/* Focus triggers: geen show delay */
	.tooltip.is-focus-visible {
		opacity: 1;
		visibility: visible;
		pointer-events: auto;
		transition:
			opacity var(--_show-duration) ease,
			visibility 0ms linear,
			pointer-events 0ms linear;
	}


	/* ## Tooltip body */

	.tooltip__body {
		background-color: var(--components-tooltip-background-color);
		color: var(--components-tooltip-content-color);
		font: var(--primitives-font-body-xs-regular-tight);
		padding-block: var(--primitives-space-4);
		padding-inline: var(--primitives-space-8);
		width: max-content;
		max-width: var(--_max-width);
		overflow-wrap: break-word;
		box-shadow: var(--components-tooltip-box-shadow);
		border-radius: var(--primitives-corner-radius-xs);
	}


	/* # Toegankelijkheid */

	@media (forced-colors: active) {
		.tooltip__body {
			border: 1px solid CanvasText;
		}
	}

	@media (prefers-reduced-motion: reduce) {
		.tooltip,
		.tooltip.is-visible,
		.tooltip.is-focus-visible {
			transition: none;
		}
	}
`;
function tooltipTemplate(component) {
  return html`
		<slot
			@mouseenter=${component._handleTriggerEnter}
			@mouseleave=${component._handleTriggerLeave}
			@focusin=${component._handleFocusIn}
			@focusout=${component._handleFocusOut}
		></slot>
		<div class=${classMap({ tooltip: true, "is-visible": component._visible && !component._focusVisible, "is-focus-visible": component._visible && component._focusVisible })}
			aria-hidden="true"
			@mouseenter=${component._handleTooltipEnter}
			@mouseleave=${component._handleTooltipLeave}
		>
			<div class="tooltip__body">${component.text}</div>
		</div>
	`;
}
var __defProp$Z = Object.defineProperty;
var __getOwnPropDesc$11 = Object.getOwnPropertyDescriptor;
var __decorateClass$12 = (decorators, target, key, kind) => {
  var result = kind > 1 ? void 0 : kind ? __getOwnPropDesc$11(target, key) : target;
  for (var i = decorators.length - 1, decorator; i >= 0; i--)
    if (decorator = decorators[i])
      result = (kind ? decorator(target, key, result) : decorator(result)) || result;
  if (kind && result) __defProp$Z(target, key, result);
  return result;
};
let tooltipCounter = 0;
const coarsePointerQuery = matchMedia("(pointer: coarse)");
let NDDTooltip = class extends LitElement {
  constructor() {
    super(...arguments);
    this.text = "";
    this.placement = "bottom";
    this._visible = false;
    this._focusVisible = false;
    this._tooltipId = `ndd-tooltip-${++tooltipCounter}`;
    this._hideTimeout = null;
    this._descriptionEl = null;
    this._currentTrigger = null;
    this._boundSlotChange = () => this._syncAriaDescribedBy();
    this._handleKeyDown = (e) => {
      if (e.key === "Escape" && this._visible) {
        this._visible = false;
        this._focusVisible = false;
      }
    };
  }
  get _effectivePlacement() {
    if (this._focusVisible) return this.placement;
    return coarsePointerQuery.matches ? "top" : this.placement;
  }
  connectedCallback() {
    super.connectedCallback();
    this.addEventListener("keydown", this._handleKeyDown);
    if (this.hasUpdated) {
      this.shadowRoot?.querySelector("slot")?.addEventListener("slotchange", this._boundSlotChange);
    }
  }
  firstUpdated() {
    this.shadowRoot?.querySelector("slot")?.addEventListener("slotchange", this._boundSlotChange);
  }
  updated(changed) {
    if (changed.has("_visible") && this._visible) {
      this._updatePosition();
    }
    if (changed.has("text")) {
      this._syncAriaDescribedBy();
    }
  }
  _syncAriaDescribedBy() {
    const trigger = this._getTriggerElement();
    if (this._currentTrigger && this._currentTrigger !== trigger) {
      this._currentTrigger.removeAttribute("aria-describedby");
    }
    this._currentTrigger = trigger;
    if (!trigger) return;
    if (trigger.getRootNode() !== document) {
      return;
    }
    if (this.text) {
      if (!this._descriptionEl) {
        this._descriptionEl = document.createElement("span");
        this._descriptionEl.id = this._tooltipId;
        Object.assign(this._descriptionEl.style, {
          position: "absolute",
          width: "1px",
          height: "1px",
          overflow: "hidden",
          clipPath: "inset(50%)",
          whiteSpace: "nowrap"
        });
        document.body.appendChild(this._descriptionEl);
      }
      this._descriptionEl.textContent = this.text;
      trigger.setAttribute("aria-describedby", this._tooltipId);
    } else {
      trigger.removeAttribute("aria-describedby");
      this._descriptionEl?.remove();
      this._descriptionEl = null;
    }
  }
  _getTriggerElement() {
    const slot = this.shadowRoot?.querySelector("slot");
    const assigned = slot?.assignedElements({ flatten: true });
    return assigned?.[0] ?? null;
  }
  _getTooltipElement() {
    return this.shadowRoot?.querySelector(".tooltip") ?? null;
  }
  _handleTriggerEnter() {
    if (!this.text) return;
    if (this._hideTimeout) {
      clearTimeout(this._hideTimeout);
      this._hideTimeout = null;
    }
    this._focusVisible = false;
    this._visible = true;
  }
  _handleFocusIn() {
    if (!this.text) return;
    if (this._hideTimeout) {
      clearTimeout(this._hideTimeout);
      this._hideTimeout = null;
    }
    this._focusVisible = true;
    this._visible = true;
  }
  _handleTriggerLeave() {
    if (this._hideTimeout) {
      clearTimeout(this._hideTimeout);
    }
    const hideDelay = parseInt(getComputedStyle(this).getPropertyValue("--_hide-delay"), 10);
    this._hideTimeout = setTimeout(() => {
      this._visible = false;
      this._hideTimeout = null;
    }, hideDelay);
  }
  /** Focus guard checks one shadow root level deep for composite triggers. */
  _handleFocusOut(e) {
    const slot = this.shadowRoot?.querySelector("slot");
    const assigned = slot?.assignedElements({ flatten: true }) ?? [];
    const related = e.relatedTarget;
    const stillInside = related && assigned.some(
      (el) => el.contains(related) || el.shadowRoot?.contains(related)
    );
    if (!stillInside) this._handleTriggerLeave();
  }
  _handleTooltipEnter() {
    if (this._hideTimeout) {
      clearTimeout(this._hideTimeout);
      this._hideTimeout = null;
    }
  }
  _handleTooltipLeave() {
    this._handleTriggerLeave();
  }
  async _updatePosition() {
    const trigger = this._getTriggerElement();
    const tooltip = this._getTooltipElement();
    if (!trigger || !tooltip) return;
    const styles2 = getComputedStyle(this);
    const { x, y } = await computePosition(trigger, tooltip, {
      placement: this._effectivePlacement,
      strategy: "fixed",
      middleware: [
        offset(parseInt(styles2.getPropertyValue("--_offset"), 10)),
        flip(),
        shift({ padding: parseInt(styles2.getPropertyValue("--_shift-padding"), 10) })
      ]
    });
    tooltip.style.left = `${x}px`;
    tooltip.style.top = `${y}px`;
  }
  disconnectedCallback() {
    super.disconnectedCallback();
    this.removeEventListener("keydown", this._handleKeyDown);
    this.shadowRoot?.querySelector("slot")?.removeEventListener("slotchange", this._boundSlotChange);
    if (this._hideTimeout) {
      clearTimeout(this._hideTimeout);
      this._hideTimeout = null;
    }
    this._currentTrigger?.removeAttribute("aria-describedby");
    this._currentTrigger = null;
    this._descriptionEl?.remove();
    this._descriptionEl = null;
  }
  render() {
    return tooltipTemplate(this);
  }
};
NDDTooltip.styles = tooltipStyles;
__decorateClass$12([
  property({ type: String, reflect: true })
], NDDTooltip.prototype, "text", 2);
__decorateClass$12([
  property({ type: String, reflect: true })
], NDDTooltip.prototype, "placement", 2);
__decorateClass$12([
  state()
], NDDTooltip.prototype, "_visible", 2);
__decorateClass$12([
  state()
], NDDTooltip.prototype, "_focusVisible", 2);
NDDTooltip = __decorateClass$12([
  customElement("ndd-tooltip")
], NDDTooltip);
function renderContent(component) {
  return html`
		<span class="icon-button__icon-area">
			<span class="icon-button__icon">
				${component.icon ? html`<ndd-icon name=${component.icon}></ndd-icon>` : html`<slot name="icon" @slotchange=${component.requestUpdate}></slot>`}
			</span>
			${component.expandable ? html`
				<span class="icon-button__disclosure-icon">
					<ndd-icon name="chevron-down-small"></ndd-icon>
				</span>
			` : nothing}
		</span>
		${component.text ? html`
			<span class="icon-button__text">${component.text}</span>
		` : ""}
	`;
}
function template$g() {
  const label = this.accessibleLabel || this.text || nothing;
  const content = renderContent(this);
  const tooltipText = this.accessibleLabel || (this.size !== "lg" ? this.text : "");
  const renderButton = () => {
    if (this.href) {
      const resolvedRel = this._resolvedRel();
      return html`
				<a class="icon-button"
					href=${this.href}
					target=${this.target || nothing}
					rel=${resolvedRel || nothing}
					aria-disabled=${this.disabled ? "true" : nothing}
					aria-label=${label}
					@click=${this._handleClick}
				>
					${content}
				</a>
			`;
    }
    return html`
			<button class="icon-button"
				type=${this.type}
				?disabled=${this.disabled}
				aria-disabled=${this.disabled ? "true" : nothing}
				aria-label=${label}
				popovertarget=${this.popovertarget || nothing}
				@click=${this._handleClick}
			>
				${content}
			</button>
		`;
  };
  if (tooltipText) {
    return html`
			<ndd-tooltip text=${tooltipText}>
				${renderButton()}
			</ndd-tooltip>
		`;
  }
  return renderButton();
}
var __defProp$Y = Object.defineProperty;
var __getOwnPropDesc$10 = Object.getOwnPropertyDescriptor;
var __decorateClass$11 = (decorators, target, key, kind) => {
  var result = kind > 1 ? void 0 : kind ? __getOwnPropDesc$10(target, key) : target;
  for (var i = decorators.length - 1, decorator; i >= 0; i--)
    if (decorator = decorators[i])
      result = (kind ? decorator(target, key, result) : decorator(result)) || result;
  if (kind && result) __defProp$Y(target, key, result);
  return result;
};
let NDDIconButton = class extends LitElement {
  constructor() {
    super(...arguments);
    this.variant = "neutral-tinted";
    this.size = "md";
    this.disabled = false;
    this.type = "button";
    this.expandable = false;
    this.popovertarget = void 0;
    this.text = "";
    this.icon = "";
    this.accessibleLabel = "";
    this.href = void 0;
    this.target = void 0;
    this.rel = void 0;
    this._warnedA11y = false;
  }
  /** Whether an icon is present via attribute or slot. */
  get _hasIcon() {
    if (this.icon) return true;
    const slot = this.shadowRoot?.querySelector('slot[name="icon"]');
    return (slot?.assignedElements().length ?? 0) > 0;
  }
  updated() {
    const inaccessible = this._hasIcon && !this.text && !this.accessibleLabel;
    if (inaccessible && !this._warnedA11y) {
      this._warnedA11y = true;
      console.warn("<ndd-icon-button>: icon is set without text or accessible-label. This produces an inaccessible button (WCAG SC 4.1.2). Add a text or accessible-label attribute.");
    } else if (!inaccessible) {
      this._warnedA11y = false;
    }
  }
  /** Resolves the effective rel value for link rendering. */
  _resolvedRel() {
    if (this.rel) return this.rel;
    if (this.target === "_blank") return "noopener noreferrer";
    return "";
  }
  _handleClick(e) {
    if (this.disabled) {
      e.preventDefault();
      e.stopPropagation();
      return;
    }
  }
  render() {
    return template$g.call(this);
  }
};
NDDIconButton.styles = styles$h;
__decorateClass$11([
  property({ type: String, reflect: true })
], NDDIconButton.prototype, "variant", 2);
__decorateClass$11([
  property({ type: String, reflect: true })
], NDDIconButton.prototype, "size", 2);
__decorateClass$11([
  property({ type: Boolean, reflect: true })
], NDDIconButton.prototype, "disabled", 2);
__decorateClass$11([
  property({ type: String, reflect: true })
], NDDIconButton.prototype, "type", 2);
__decorateClass$11([
  property({ type: Boolean, reflect: true, attribute: "expandable" })
], NDDIconButton.prototype, "expandable", 2);
__decorateClass$11([
  property({ type: String })
], NDDIconButton.prototype, "popovertarget", 2);
__decorateClass$11([
  property({ type: String })
], NDDIconButton.prototype, "text", 2);
__decorateClass$11([
  property({ type: String })
], NDDIconButton.prototype, "icon", 2);
__decorateClass$11([
  property({ type: String, attribute: "accessible-label" })
], NDDIconButton.prototype, "accessibleLabel", 2);
__decorateClass$11([
  property({ type: String, reflect: true })
], NDDIconButton.prototype, "href", 2);
__decorateClass$11([
  property({ type: String })
], NDDIconButton.prototype, "target", 2);
__decorateClass$11([
  property({ type: String })
], NDDIconButton.prototype, "rel", 2);
NDDIconButton = __decorateClass$11([
  customElement("ndd-icon-button")
], NDDIconButton);
const styles$g = css`
	/* # Host */

	:host {
		display: inline-flex;
		-webkit-tap-highlight-color: transparent;
	}

	:host([hidden]) {
		display: none;
	}

	:host([disabled]) {
		opacity: var(--primitives-opacity-disabled);
		pointer-events: none;
	}

	:host([disabled]) ndd-button,
	:host([disabled]) ndd-icon-button {
		opacity: 1;
	}

	/* # Base */

	.split-button {
		display: inline-flex;
		flex-direction: row;
		align-items: center;
	}

	/* # Focus */

	ndd-button:focus-within,
	ndd-icon-button:focus-within {
		position: relative;
		z-index: 1;
	}

	/* # Sizes */

	/* ## Size: XS */

	:host([size='xs']) .split-button {
		border-radius: var(--semantics-controls-xs-corner-radius);
	}

	:host([size='xs']) .split-button__divider {
		height: var(--semantics-buttons-xs-divider-length);
	}

	/* ## Size: SM */

	:host([size='sm']) .split-button {
		border-radius: var(--semantics-controls-sm-corner-radius);
	}

	:host([size='sm']) .split-button__divider {
		height: var(--semantics-buttons-sm-divider-length);
	}

	/* ## Size: MD */

	:host([size='md']) .split-button,
	:host(:not([size])) .split-button {
		border-radius: var(--semantics-controls-md-corner-radius);
	}

	:host([size='md']) .split-button__divider,
	:host(:not([size])) .split-button__divider {
		height: var(--semantics-buttons-md-divider-length);
	}

	/* # Variants */

	/* ## Variant: Neutral Tintend (Default) */

	:host([variant="neutral-tinted"]) .split-button,
	:host(:not([variant])) .split-button {
		background-color: var(--semantics-buttons-neutral-tinted-background-color);
	}


	/* # Elements */

	.split-button__divider {
		width: 1px;
		flex-shrink: 0;
		background-color: var(--semantics-buttons-neutral-tinted-divider-color);
	}
`;
function template$f() {
  return html`
		<div class="split-button">
			<ndd-button
				variant=${this.variant}
				size=${this.size}
				text=${this.text}
				start-icon=${this.startIcon || nothing}
				?disabled=${this.disabled}
				@click=${this._handleActionClick}
			></ndd-button>
			<div class="split-button__divider"></div>
			<ndd-icon-button
				variant=${this.variant}
				size=${this.size}
				icon="chevron-down-small"
				text=${this._t("components.split-button.menu-action")}
				?disabled=${this.disabled}
				aria-haspopup="menu"
				@click=${this._handleMenuClick}
			></ndd-icon-button>
		</div>
	`;
}
const nddSplitButtonTranslations = {
  "components.split-button.menu-action": "Meer opties"
};
var __defProp$X = Object.defineProperty;
var __getOwnPropDesc$$ = Object.getOwnPropertyDescriptor;
var __decorateClass$10 = (decorators, target, key, kind) => {
  var result = kind > 1 ? void 0 : kind ? __getOwnPropDesc$$(target, key) : target;
  for (var i = decorators.length - 1, decorator; i >= 0; i--)
    if (decorator = decorators[i])
      result = (kind ? decorator(target, key, result) : decorator(result)) || result;
  if (kind && result) __defProp$X(target, key, result);
  return result;
};
let NDDSplitButton = class extends LitElement {
  constructor() {
    super(...arguments);
    this.size = "md";
    this.variant = "neutral-tinted";
    this.disabled = false;
    this.text = "";
    this.startIcon = "";
    this.translations = {};
  }
  // — i18n —————————————————————————————————————————————————————————————————
  _t(key) {
    return this.translations[key] ?? nddSplitButtonTranslations[key];
  }
  _handleActionClick(e) {
    if (this.disabled) return;
    e.stopPropagation();
    this.dispatchEvent(new CustomEvent("action-click", { bubbles: true, composed: true }));
  }
  _handleMenuClick(e) {
    if (this.disabled) return;
    e.stopPropagation();
    this.dispatchEvent(new CustomEvent("menu-click", { bubbles: true, composed: true }));
  }
  render() {
    return template$f.call(this);
  }
};
NDDSplitButton.styles = styles$g;
__decorateClass$10([
  property({ type: String, reflect: true })
], NDDSplitButton.prototype, "size", 2);
__decorateClass$10([
  property({ type: String, reflect: true })
], NDDSplitButton.prototype, "variant", 2);
__decorateClass$10([
  property({ type: Boolean, reflect: true })
], NDDSplitButton.prototype, "disabled", 2);
__decorateClass$10([
  property({ type: String })
], NDDSplitButton.prototype, "text", 2);
__decorateClass$10([
  property({ type: String, attribute: "start-icon" })
], NDDSplitButton.prototype, "startIcon", 2);
__decorateClass$10([
  property({ type: Object })
], NDDSplitButton.prototype, "translations", 2);
NDDSplitButton = __decorateClass$10([
  customElement("ndd-split-button")
], NDDSplitButton);
const styles$f = css`
	:host {
		display: inline-flex;
	}

	:host([hidden]) {
		display: none;
	}

	::slotted([hidden]) {
		display: none !important;
	}

	.button-group {
		display: flex;
		justify-content: center;
	}

	/* # Orientation: Horizontal */

	:host([orientation="horizontal"]) .button-group {
		flex-direction: row;
		flex-wrap: wrap;
	}

	/* # Orientation: Vertical */

	:host([orientation="vertical"]) {
		display: flex;
		width: 100%;
	}

	:host([orientation="vertical"]) .button-group {
		flex-direction: column;
		width: 100%;
	}

	/* # Size: S */

	:host([size="sm"]) .button-group {
		gap: var(--components-button-group-sm-gap);
	}

	/* # Size: M (default) */

	:host([size="md"]) .button-group,
	:host(:not([size])) .button-group {
		gap: var(--components-button-group-md-gap);
	}
`;
function template$e() {
  return html`
	<div class="button-group">
		<slot @slotchange=${this.handleSlotChange}></slot>
	</div>
	`;
}
var __defProp$W = Object.defineProperty;
var __getOwnPropDesc$_ = Object.getOwnPropertyDescriptor;
var __decorateClass$$ = (decorators, target, key, kind) => {
  var result = kind > 1 ? void 0 : kind ? __getOwnPropDesc$_(target, key) : target;
  for (var i = decorators.length - 1, decorator; i >= 0; i--)
    if (decorator = decorators[i])
      result = (kind ? decorator(target, key, result) : decorator(result)) || result;
  if (kind && result) __defProp$W(target, key, result);
  return result;
};
let NDDButtonGroup = class extends LitElement {
  constructor() {
    super(...arguments);
    this.size = "md";
    this.orientation = "vertical";
  }
  handleSlotChange() {
    const assigned = this._slot.assignedElements({ flatten: true }).filter((el) => el instanceof HTMLElement);
    assigned.forEach((el, index) => {
      if (index >= 3) {
        el.setAttribute("hidden", "");
        console.warn("ndd-button-group: Only 3 buttons are allowed. Extra buttons will be hidden.");
      }
      if (this.orientation === "vertical") {
        el.setAttribute("full-width", "");
      } else {
        el.removeAttribute("full-width");
      }
      el.setAttribute("size", this.size);
    });
  }
  updated(changedProperties) {
    if (changedProperties.has("orientation") || changedProperties.has("size")) {
      this.handleSlotChange();
    }
  }
  render() {
    return template$e.call(this);
  }
};
NDDButtonGroup.styles = styles$f;
__decorateClass$$([
  property({ type: String, reflect: true })
], NDDButtonGroup.prototype, "size", 2);
__decorateClass$$([
  property({ type: String, reflect: true })
], NDDButtonGroup.prototype, "orientation", 2);
__decorateClass$$([
  query("slot")
], NDDButtonGroup.prototype, "_slot", 2);
NDDButtonGroup = __decorateClass$$([
  customElement("ndd-button-group")
], NDDButtonGroup);
const styles$e = css`
	/* # Host */

	:host {
		display: inline-flex;
	}

	:host([hidden]) {
		display: none;
	}

	:host([disabled]) {
		opacity: var(--primitives-opacity-disabled);
		pointer-events: none;
	}

	:host([disabled]) ::slotted(ndd-button),
	:host([disabled]) ::slotted(ndd-icon-button) {
		opacity: 1;
	}

	/* # Base */

	.button-bar {
		display: flex;
		flex-direction: row;
		justify-content: center;
		align-items: center;
		background-color: var(--semantics-buttons-neutral-tinted-background-color);
	}

	/* # Size: XS */

	:host([size="xs"]) .button-bar {
		height: var(--semantics-controls-xs-min-size);
		border-radius: var(--semantics-controls-xs-corner-radius);
	}

	/* # Size: SM */

	:host([size="sm"]) .button-bar {
		height: var(--semantics-controls-sm-min-size);
		border-radius: var(--semantics-controls-sm-corner-radius);
	}

	/* # Size: MD */

	:host([size="md"]) .button-bar,
	:host(:not([size])) .button-bar {
		height: var(--semantics-controls-md-min-size);
		border-radius: var(--semantics-controls-md-corner-radius);
	}

	/* # Divider */

	.button-bar__divider {
		display: flex;
		align-items: center;
		justify-content: center;
		flex-shrink: 0;
	}

	:host([size="xs"]) .button-bar__divider {
		height: var(--semantics-controls-xs-min-size);
	}

	:host([size="sm"]) .button-bar__divider {
		height: var(--semantics-controls-sm-min-size);
	}

	:host([size="md"]) .button-bar__divider,
	:host(:not([size])) .button-bar__divider {
		height: var(--semantics-controls-md-min-size);
	}

	.button-bar__divider-line {
		width: var(--semantics-dividers-thickness);
		background-color: var(--semantics-buttons-neutral-tinted-divider-color);
	}

	:host([size="xs"]) .button-bar__divider-line {
		height: var(--semantics-buttons-xs-divider-length);
	}

	:host([size="sm"]) .button-bar__divider-line {
		height: var(--semantics-buttons-sm-divider-length);
	}

	:host([size="md"]) .button-bar__divider-line,
	:host(:not([size])) .button-bar__divider-line {
		height: var(--semantics-buttons-md-divider-length);
	}

	/* # Focus */

	::slotted([data-focused]) {
		position: relative;
		z-index: 1;
	}
`;
function template$d() {
  return html`
		<div class="button-bar" part="bar" role="group">
			${repeat(this._children, (c) => c.id, (c) => renderChild.call(this, c))}
		</div>
	`;
}
function renderChild(child) {
  if (child.type === "divider") {
    return html`
			<div class="button-bar__divider">
				<div class="button-bar__divider-line"></div>
			</div>
		`;
  }
  return html`<slot name="child-${child.id}"></slot>`;
}
var __defProp$V = Object.defineProperty;
var __getOwnPropDesc$Z = Object.getOwnPropertyDescriptor;
var __decorateClass$_ = (decorators, target, key, kind) => {
  var result = kind > 1 ? void 0 : kind ? __getOwnPropDesc$Z(target, key) : target;
  for (var i = decorators.length - 1, decorator; i >= 0; i--)
    if (decorator = decorators[i])
      result = (kind ? decorator(target, key, result) : decorator(result)) || result;
  if (kind && result) __defProp$V(target, key, result);
  return result;
};
if (!customElements.get("ndd-button-bar-divider")) {
  customElements.define("ndd-button-bar-divider", class extends HTMLElement {
  });
}
const BUTTON_TAGS = ["ndd-button", "ndd-icon-button"];
let NDDButtonBar = class extends LitElement {
  constructor() {
    super(...arguments);
    this.size = "md";
    this.variant = "neutral-tinted";
    this.disabled = false;
    this._children = [];
    this._idCounter = 0;
    this._observer = null;
    this._building = false;
    this._individuallyDisabled = /* @__PURE__ */ new WeakSet();
  }
  connectedCallback() {
    super.connectedCallback();
    this._observer = new MutationObserver(() => this._buildChildren());
    this._observer.observe(this, { childList: true });
    this._buildChildren();
    this.addEventListener("focusin", this._handleFocusIn);
    this.addEventListener("focusout", this._handleFocusOut);
  }
  disconnectedCallback() {
    super.disconnectedCallback();
    this._observer?.disconnect();
    this._observer = null;
    this.removeEventListener("focusin", this._handleFocusIn);
    this.removeEventListener("focusout", this._handleFocusOut);
  }
  updated(changedProperties) {
    if (changedProperties.has("size") || changedProperties.has("_children")) {
      this._propagateSize();
    }
    if (changedProperties.has("variant") || changedProperties.has("_children")) {
      this._propagateVariant();
    }
    if (changedProperties.has("disabled")) {
      this._propagateDisabled();
    } else if (changedProperties.has("_children") && this.disabled) {
      Array.from(this.children).filter((el) => BUTTON_TAGS.includes(el.tagName.toLowerCase())).forEach((el) => el.setAttribute("disabled", ""));
    }
  }
  _handleFocusIn(e) {
    const target = e.target;
    if (BUTTON_TAGS.includes(target.tagName.toLowerCase())) {
      target.setAttribute("data-focused", "");
    }
  }
  _handleFocusOut(e) {
    const target = e.target;
    if (BUTTON_TAGS.includes(target.tagName.toLowerCase())) {
      target.removeAttribute("data-focused");
    }
  }
  _propagateSize() {
    Array.from(this.children).filter((el) => BUTTON_TAGS.includes(el.tagName.toLowerCase())).forEach((el) => el.setAttribute("size", this.size));
  }
  _propagateVariant() {
    Array.from(this.children).filter((el) => BUTTON_TAGS.includes(el.tagName.toLowerCase())).forEach((el) => el.setAttribute("variant", this.variant));
  }
  _propagateDisabled() {
    const buttons = Array.from(this.children).filter(
      (el) => BUTTON_TAGS.includes(el.tagName.toLowerCase())
    );
    if (this.disabled) {
      buttons.forEach((el) => {
        if (el.hasAttribute("disabled")) {
          this._individuallyDisabled.add(el);
        }
      });
      buttons.forEach((el) => el.setAttribute("disabled", ""));
    } else {
      buttons.forEach((el) => {
        if (!this._individuallyDisabled.has(el)) {
          el.removeAttribute("disabled");
        }
      });
      this._individuallyDisabled = /* @__PURE__ */ new WeakSet();
    }
  }
  _buildChildren() {
    if (this._building) return;
    this._building = true;
    this._idCounter = 0;
    this._children = Array.from(this.children).map((el) => {
      const tag = el.tagName.toLowerCase();
      if (tag === "ndd-button-bar-divider") {
        return { type: "divider", id: this._idCounter++ };
      }
      if (BUTTON_TAGS.includes(tag)) {
        el.setAttribute("size", this.size);
        el.setAttribute("variant", this.variant);
      }
      const id = this._idCounter++;
      const slotName = `child-${id}`;
      if (el.getAttribute("slot") !== slotName) {
        el.setAttribute("slot", slotName);
      }
      return { type: "button", element: el, id };
    });
    this._building = false;
  }
  render() {
    return template$d.call(this);
  }
};
NDDButtonBar.styles = styles$e;
__decorateClass$_([
  property({ type: String, reflect: true })
], NDDButtonBar.prototype, "size", 2);
__decorateClass$_([
  property({ type: String, reflect: true })
], NDDButtonBar.prototype, "variant", 2);
__decorateClass$_([
  property({ type: Boolean, reflect: true })
], NDDButtonBar.prototype, "disabled", 2);
__decorateClass$_([
  state()
], NDDButtonBar.prototype, "_children", 2);
NDDButtonBar = __decorateClass$_([
  customElement("ndd-button-bar")
], NDDButtonBar);
const styles$d = css`

	/* # Host */

	:host {
		display: block;
		font-family: var(--ndd-font-family-body);
		box-sizing: border-box;
		--_item-width: auto;
		--_item-min-width: 0px;
		--_title-group-min-width: 200px;
	}

	:host([hidden]) {
		display: none;
	}

	/* # Toolbar */

	.toolbar {
		display: flex;
		flex-direction: row;
		align-items: center;
		width: 100%;
	}

	:host([size="sm"]) .toolbar {
		gap: var(--components-toolbar-sm-gap);
	}

	:host([size="md"]) .toolbar,
	:host(:not([size])) .toolbar {
		gap: var(--components-toolbar-md-gap);
	}

	/* # Items */

	.toolbar__items {
		display: flex;
		flex-direction: row;
		align-items: flex-start;
		flex: 1;
		min-width: 0;
	}

	:host([size="sm"]) .toolbar__items {
		gap: var(--components-toolbar-sm-gap);
	}

	:host([size="md"]) .toolbar__items,
	:host(:not([size])) .toolbar__items {
		gap: var(--components-toolbar-md-gap);
	}

	/* # Spacers */

	.toolbar__flexible-spacer {
		flex-grow: 1;
		flex-shrink: 1;
		margin-left: calc(-1 * var(--components-toolbar-md-gap));
	}

	:host([size="sm"]) .toolbar__flexible-spacer {
		margin-left: calc(-1 * var(--components-toolbar-sm-gap));
	}

	.toolbar__center-fill {
		display: flex;
		flex-direction: row;
		align-items: flex-start;
		flex-grow: 1;
		flex-shrink: 1;
		min-width: 0;
		justify-content: center;
	}

	.toolbar__left-spacer {
		flex-shrink: 1;
		flex-grow: 0;
		min-width: 0;
		margin-right: calc(-1 * var(--components-toolbar-md-gap));
		flex-basis: calc(
			var(--ndd-toolbar-width) / 2
			- var(--ndd-toolbar-start-width)
			- var(--ndd-toolbar-center-width) / 2
			- var(--components-toolbar-md-gap)
		);
	}

	:host([size="sm"]) .toolbar__left-spacer {
		margin-right: calc(-1 * var(--components-toolbar-sm-gap));
		flex-basis: calc(
			var(--ndd-toolbar-width) / 2
			- var(--ndd-toolbar-start-width)
			- var(--ndd-toolbar-center-width) / 2
			- var(--components-toolbar-sm-gap)
		);
	}

	.toolbar__right-spacer {
		flex-shrink: 1;
		flex-grow: 0;
		min-width: 0;
		margin-left: calc(-1 * var(--components-toolbar-md-gap));
		flex-basis: calc(
			var(--ndd-toolbar-width) / 2
			- var(--ndd-toolbar-end-width)
			- var(--ndd-toolbar-center-width) / 2
			- var(--components-toolbar-md-gap)
			- var(--ndd-toolbar-overflow-button-width, 0px)
		);
	}

	:host([size="sm"]) .toolbar__right-spacer {
		margin-left: calc(-1 * var(--components-toolbar-sm-gap));
		flex-basis: calc(
			var(--ndd-toolbar-width) / 2
			- var(--ndd-toolbar-end-width)
			- var(--ndd-toolbar-center-width) / 2
			- var(--components-toolbar-sm-gap)
			- var(--ndd-toolbar-overflow-button-width, 0px)
		);
	}

	/* # Item */

	.toolbar__item {
		display: inline-flex;
		flex-direction: column;
		align-items: center;
		flex-shrink: 0;
		flex-grow: 0;
	}

	.toolbar__item.is-fluid {
		flex-basis: var(--_item-width);
		min-width: var(--_item-min-width);
		flex-shrink: 1;
	}

	.toolbar__item.is-solo-fluid {
		flex-grow: 1;
		flex-shrink: 1;
		flex-basis: 0;
	}

	.toolbar__item.is-hidden {
		display: none;
	}

	.toolbar__item-content {
		display: inline-flex;
		align-items: center;
		width: 100%;
		justify-content: center;
	}

	.toolbar__item.is-fluid .toolbar__item-content ::slotted(*),
	.toolbar__item.is-solo-fluid .toolbar__item-content ::slotted(*) {
		width: 100%;
	}

	.toolbar__item-label {
		display: none;
		margin-top: var(--primitives-space-2);
		font: var(--primitives-font-body-xs-regular-flat);
		color: var(--semantics-content-color);
		white-space: nowrap;
	}

	:host([show-item-labels]) .toolbar__item-label {
		display: block;
	}

	/* # Overflow button */

	.toolbar__overflow-button {
		display: inline-flex;
		flex-direction: column;
		align-items: center;
		flex-shrink: 0;
		flex-grow: 0;
	}

	.toolbar__overflow-button.is-hidden {
		display: none;
	}

	.toolbar__overflow-button .toolbar__item-label {
		display: none;
	}

	:host([show-item-labels]) .toolbar__overflow-button .toolbar__item-label {
		display: block;
	}

	/* # Title group */

	.toolbar__title-group {
		display: inline-flex;
		flex-direction: column;
		justify-content: center;
		min-width: var(--_title-group-min-width);
		overflow: hidden;
		flex-shrink: 1;
	}

	.toolbar__title-group.is-solo-fluid {
		flex-grow: 1;
		flex-shrink: 1;
		flex-basis: 0;
		min-width: 0;
	}

	:host([size="sm"]) .toolbar__title-group {
		height: var(--semantics-controls-sm-min-size);
	}

	:host([size="md"]) .toolbar__title-group,
	:host(:not([size])) .toolbar__title-group {
		height: var(--semantics-controls-md-min-size);
	}

	.toolbar__title-group--center-text-align {
		align-items: center;
		text-align: center;
	}

	.toolbar__title-group--left-text-align {
		align-items: flex-start;
		text-align: left;
	}

	.toolbar__title {
		margin: 0;
		color: var(--semantics-content-color);
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
		max-width: 100%;
	}

	:host([size="md"]) .toolbar__title,
	:host(:not([size])) .toolbar__title {
		font: var(--primitives-font-body-lg-bold-flat);
	}

	:host([size="sm"]) .toolbar__title {
		font: var(--primitives-font-body-sm-bold-flat);
	}

	.toolbar__subtitle {
		margin: 0;
		color: var(--semantics-content-secondary-color);
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
		max-width: 100%;
	}

	:host([size="md"]) .toolbar__subtitle,
	:host(:not([size])) .toolbar__subtitle {
		font: var(--primitives-font-body-xs-regular-flat);
	}

	:host([size="sm"]) .toolbar__subtitle {
		font: var(--primitives-font-body-xxs-regular-flat);
	}
`;
function resolveWidth(width) {
  if (!width) return "";
  if (width.endsWith("%")) {
    const ratio = parseFloat(width) / 100;
    return `calc(var(--ndd-toolbar-width) * ${ratio})`;
  }
  return width;
}
function renderChildren(children, allChildren, overflowIds, suppressSoloFluid = false) {
  return children.map((child) => {
    if (child.type === "title-group") {
      const alignClass = child.align === "center" ? "toolbar__title-group--center-text-align" : "toolbar__title-group--left-text-align";
      const visibleItems = allChildren.filter(
        (c) => !overflowIds.has(c.id) && (c.type === "item" || c.type === "title-group")
      );
      const solo = visibleItems.length === 1 && visibleItems[0].id === child.id;
      return html`
				<div
					class="toolbar__title-group ${alignClass} ${solo ? "is-solo-fluid" : ""}"
					data-child-id=${child.id}
					style=${styleMap({ "--_title-group-min-width": child.minWidth })}
				>
					${child.title ? html`<p class="toolbar__title">${child.title}</p>` : nothing}
					${child.subtitle ? html`<p class="toolbar__subtitle">${child.subtitle}</p>` : nothing}
				</div>
			`;
    }
    if (child.type === "item") {
      const isOverflowed = overflowIds.has(child.id);
      const visibleItems = allChildren.filter(
        (c) => !overflowIds.has(c.id) && (c.type === "item" || c.type === "title-group")
      );
      const soloFluid = !suppressSoloFluid && !isOverflowed && child.isFluid && visibleItems.length === 1 && visibleItems[0].id === child.id;
      const cssVars = {};
      if (!soloFluid && child.isFluid) {
        if (child.minWidth) cssVars["--_item-min-width"] = child.minWidth;
        if (child.width) cssVars["--_item-width"] = resolveWidth(child.width);
      }
      const classes = [
        "toolbar__item",
        soloFluid ? "is-solo-fluid" : child.isFluid ? "is-fluid" : "",
        isOverflowed ? "is-hidden" : ""
      ].filter(Boolean).join(" ");
      return html`
				<div
					class=${classes}
					data-child-id=${child.id}
					aria-hidden=${isOverflowed ? "true" : nothing}
					style=${styleMap(cssVars)}
				>
					<div class="toolbar__item-content">
						<slot name="child-${child.id}"></slot>
					</div>
					${child.label ? html`<span class="toolbar__item-label">${child.label}</span>` : nothing}
				</div>
			`;
    }
    return html`<slot name="child-${child.id}"></slot>`;
  });
}
function template$c(startChildren, centerChildren, endChildren, overflowIds, size2, hasCenterChildren, leftSpacerZero, rightSpacerZero, isSoloFluidItem, hasOverflow, menuOpen, label, menuId, onOverflowClick, centerOnly, t) {
  const allChildren = [...startChildren, ...centerChildren, ...endChildren];
  return html`
		<div class="toolbar"
			role="toolbar"
			aria-label=${label || nothing}
		>
			<div class="toolbar__items">
				${renderChildren(startChildren, allChildren, overflowIds)}
				${hasCenterChildren ? html`
					${centerOnly ? html`
						<div class="toolbar__center-fill">
							${renderChildren(centerChildren, allChildren, overflowIds, true)}
						</div>
					` : html`
						${leftSpacerZero ? nothing : html`<div class="toolbar__left-spacer"></div>`}
						${renderChildren(centerChildren, allChildren, overflowIds)}
						${rightSpacerZero ? nothing : html`<div class="toolbar__right-spacer"></div>`}
					`}
				` : isSoloFluidItem ? nothing : html`
					<div class="toolbar__flexible-spacer"></div>
				`}
				${renderChildren(endChildren, allChildren, overflowIds)}
			</div>
			<div class="toolbar__overflow-button ${hasOverflow ? "" : "is-hidden"}">
				<ndd-icon-button size=${size2}
					icon="ellipsis"
					text=${t("components.toolbar.overflow-action")}
					aria-haspopup="menu"
					aria-expanded=${menuOpen ? "true" : "false"}
					aria-controls=${menuId}
					@click=${onOverflowClick}
				></ndd-icon-button>
				<span class="toolbar__item-label">${t("components.toolbar.overflow-action")}</span>
			</div>
		</div>
	`;
}
const nddToolbarTranslations = {
  "components.toolbar.overflow-action": "Meer"
};
const POPOVER_REOPEN_GUARD_MS = 100;
var __defProp$U = Object.defineProperty;
var __getOwnPropDesc$Y = Object.getOwnPropertyDescriptor;
var __decorateClass$Z = (decorators, target, key, kind) => {
  var result = kind > 1 ? void 0 : kind ? __getOwnPropDesc$Y(target, key) : target;
  for (var i = decorators.length - 1, decorator; i >= 0; i--)
    if (decorator = decorators[i])
      result = (kind ? decorator(target, key, result) : decorator(result)) || result;
  if (kind && result) __defProp$U(target, key, result);
  return result;
};
if (!customElements.get("ndd-toolbar-item")) {
  customElements.define("ndd-toolbar-item", class extends HTMLElement {
    constructor() {
      super();
      this.attachShadow({ mode: "open" }).innerHTML = '<slot></slot><slot name="overflow" style="display:none"></slot>';
    }
  });
}
if (!customElements.get("ndd-toolbar-title-group")) {
  customElements.define("ndd-toolbar-title-group", class extends HTMLElement {
  });
}
let NDDToolbar = class extends LitElement {
  constructor() {
    super(...arguments);
    this.size = "md";
    this.showItemLabels = false;
    this.label = "";
    this.translations = {};
    this._menuOpen = false;
    this._startChildren = [];
    this._centerChildren = [];
    this._endChildren = [];
    this._overflowIds = /* @__PURE__ */ new Set();
    this._leftSpacerZero = false;
    this._rightSpacerZero = false;
    this._pinnedOverflowItems = [];
    this._childIds = /* @__PURE__ */ new WeakMap();
    this._idCounter = 0;
    this._itemWidths = /* @__PURE__ */ new Map();
    this._observer = null;
    this._resizeObserver = null;
    this._menu = null;
    this._isMeasuring = false;
    this._isBuilding = false;
    this._hasMeasured = false;
    this._prioritizedItemsCache = null;
    this._menuClosedAt = 0;
  }
  // — i18n —————————————————————————————————————————————————————————————————
  _t(key) {
    return this.translations[key] ?? nddToolbarTranslations[key];
  }
  _getId(el) {
    if (!this._childIds.has(el)) {
      this._childIds.set(el, this._idCounter++);
    }
    return this._childIds.get(el);
  }
  connectedCallback() {
    super.connectedCallback();
    this._observer = new MutationObserver((mutations) => {
      if (this._isBuilding) return;
      const onlyInternalMoves = mutations.every((m) => {
        if (m.type === "attributes") {
          const tag = m.target.tagName.toLowerCase();
          return tag !== "ndd-toolbar-item" && tag !== "ndd-toolbar-title-group";
        }
        return false;
      });
      if (onlyInternalMoves) return;
      this._buildChildren();
    });
    setTimeout(() => this._buildChildren(), 0);
    this._createMenu();
  }
  disconnectedCallback() {
    super.disconnectedCallback();
    this._observer?.disconnect();
    this._observer = null;
    this._resizeObserver?.disconnect();
    this._resizeObserver = null;
    this._menu?.remove();
    this._menu = null;
  }
  firstUpdated() {
    this._resizeObserver = new ResizeObserver(() => {
      if (this._isMeasuring) return;
      if (this._menuOpen) {
        this._menu?.hidePopover();
      }
      this._measureAndUpdate();
    });
    this._resizeObserver.observe(this);
    this._propagateSize();
  }
  updated(changedProperties) {
    if (changedProperties.has("size")) {
      this._propagateSize();
    }
    if (changedProperties.has("_startChildren") || changedProperties.has("_centerChildren") || changedProperties.has("_endChildren")) {
      this.updateComplete.then(() => this._measureAndUpdate());
    }
    if (changedProperties.has("_overflowIds") || changedProperties.has("_pinnedOverflowItems")) {
      this._syncMenuItems();
      this._syncMenuAnchor();
      if (!this._hasMeasured) {
        this.updateComplete.then(() => this._updateAreaVars());
      }
    }
  }
  _handleOverflowButtonClick() {
    if (!this._menu) return;
    if (this._menuOpen) {
      this._menu.hidePopover();
    } else if (Date.now() - this._menuClosedAt > POPOVER_REOPEN_GUARD_MS) {
      this._menu.showPopover();
    }
  }
  _createMenu() {
    if (this._menu) return;
    const menu = document.createElement("ndd-menu");
    menu.setAttribute("placement", "bottom-end");
    menu.id = `ndd-toolbar-overflow-menu-${this._idCounter++}`;
    menu.addEventListener("toggle", (event) => {
      const open = event.newState === "open";
      this._menuOpen = open;
      if (!open) this._menuClosedAt = Date.now();
    });
    document.body.appendChild(menu);
    this._menu = menu;
  }
  _syncMenuAnchor() {
    if (!this._menu) return;
    const overflowButton = this.shadowRoot?.querySelector(".toolbar__overflow-button ndd-icon-button");
    if (overflowButton) {
      this._menu.anchorElement = overflowButton;
    }
  }
  /**
   * Syncs overflow menu items by cloning the original `ndd-menu-item` elements.
   * Note: `cloneNode` does not copy event listeners added via `addEventListener`.
   * The `select` event works correctly since it is dispatched by `ndd-menu-item` internally.
   * Consumers should avoid adding extra listeners directly on overflow `ndd-menu-item` elements.
   */
  _syncMenuItems() {
    if (!this._menu) return;
    this._menu.innerHTML = "";
    const prioritized = [...this._getPrioritizedItems()].reverse();
    prioritized.forEach((child) => {
      if (!this._overflowIds.has(child.id)) return;
      if (child.overflowItems.length === 0) return;
      child.overflowItems.forEach((el) => {
        const clone = el.cloneNode(true);
        clone.removeAttribute("slot");
        this._menu.appendChild(clone);
      });
    });
    if (this._pinnedOverflowItems.length > 0) {
      this._pinnedOverflowItems.forEach((el) => {
        const clone = el.cloneNode(true);
        this._menu.appendChild(clone);
      });
    }
  }
  _propagateSize() {
    Array.from(this.querySelectorAll("ndd-toolbar-item")).forEach((item) => {
      Array.from(item.children).forEach((child) => {
        if (child.getAttribute("slot") !== "overflow") {
          child.setAttribute("size", this.size);
        }
      });
    });
  }
  _getPrioritizedItems() {
    if (this._prioritizedItemsCache) return this._prioritizedItemsCache;
    const endItems = this._endChildren.filter((c) => c.type === "item");
    const startItems = this._startChildren.filter((c) => c.type === "item");
    const centerItems = this._centerChildren.filter((c) => c.type === "item");
    const result = [
      ...endItems.map((item, index) => ({ item, areaOrder: 0, index })),
      ...centerItems.map((item, index) => ({ item, areaOrder: 1, index })),
      ...startItems.map((item, index) => ({ item, areaOrder: 2, index }))
    ].sort((a, b) => {
      if (a.item.priority !== b.item.priority) return a.item.priority - b.item.priority;
      if (a.areaOrder !== b.areaOrder) return a.areaOrder - b.areaOrder;
      return b.index - a.index;
    }).map(({ item }) => item);
    this._prioritizedItemsCache = result;
    return result;
  }
  _measureItemWidths() {
    const measurableEls = Array.from(
      this.shadowRoot?.querySelectorAll(".toolbar__item[data-child-id], .toolbar__title-group[data-child-id]") ?? []
    );
    measurableEls.forEach((el) => {
      const id = Number(el.dataset.childId);
      this._itemWidths.set(id, el.getBoundingClientRect().width);
    });
  }
  _computeAreaWidth(children, itemGap) {
    const visible = children.filter((c) => !this._overflowIds.has(c.id));
    const gaps = Math.max(0, visible.length - 1) * itemGap;
    const itemsWidth = visible.reduce((sum, child) => {
      if (child.type === "item" || child.type === "title-group") {
        return sum + (this._itemWidths.get(child.id) ?? 0);
      }
      return sum;
    }, 0);
    return gaps + itemsWidth;
  }
  _computeSpacerZeros(hostWidth, itemGap, overflowButtonWidth, startWidth, centerWidth, endWidth) {
    if (startWidth === 0 && endWidth === 0) {
      return { leftZero: true, rightZero: true };
    }
    const leftSpacer = hostWidth / 2 - startWidth - centerWidth / 2 - itemGap;
    const rightSpacer = hostWidth / 2 - endWidth - centerWidth / 2 - itemGap - overflowButtonWidth;
    return {
      leftZero: leftSpacer <= 0,
      rightZero: rightSpacer <= 0
    };
  }
  _updateAreaVars() {
    const itemsEl = this.shadowRoot?.querySelector(".toolbar__items");
    if (!itemsEl) return;
    const hostWidth = this.getBoundingClientRect().width;
    const itemGap = parseFloat(getComputedStyle(itemsEl).gap ?? "0");
    const hostGap = parseFloat(getComputedStyle(this).gap ?? "0");
    const overflowButtonContainerEl = this.shadowRoot?.querySelector(".toolbar__overflow-button");
    const overflowButtonEl = this.shadowRoot?.querySelector(".toolbar__overflow-button ndd-icon-button");
    const overflowButtonWidth = overflowButtonContainerEl && !overflowButtonContainerEl.classList.contains("is-hidden") && overflowButtonEl ? overflowButtonEl.getBoundingClientRect().width + hostGap : 0;
    this.style.setProperty("--ndd-toolbar-overflow-button-width", `${overflowButtonWidth}px`);
    const startWidth = this._computeAreaWidth(this._startChildren, itemGap);
    const centerWidth = this._computeAreaWidth(this._centerChildren, itemGap);
    const endWidth = this._computeAreaWidth(this._endChildren, itemGap);
    this.style.setProperty("--ndd-toolbar-start-width", `${startWidth}px`);
    this.style.setProperty("--ndd-toolbar-center-width", `${centerWidth}px`);
    this.style.setProperty("--ndd-toolbar-end-width", `${endWidth}px`);
    const { leftZero, rightZero } = this._computeSpacerZeros(
      hostWidth,
      itemGap,
      overflowButtonWidth,
      startWidth,
      centerWidth,
      endWidth
    );
    if (leftZero !== this._leftSpacerZero) this._leftSpacerZero = leftZero;
    if (rightZero !== this._rightSpacerZero) this._rightSpacerZero = rightZero;
  }
  _measureAndUpdate() {
    if (this._isMeasuring) return;
    const itemsEl = this.shadowRoot?.querySelector(".toolbar__items");
    if (!itemsEl) return;
    this._isMeasuring = true;
    const hostWidth = this.getBoundingClientRect().width;
    this.style.setProperty("--ndd-toolbar-width", `${hostWidth}px`);
    this._measureOverflow(itemsEl);
    this._hasMeasured = true;
    this._isMeasuring = false;
  }
  _measureOverflow(itemsEl) {
    const overflowButtonEl = this.shadowRoot?.querySelector(".toolbar__overflow-button");
    const allItemEls = Array.from(
      this.shadowRoot?.querySelectorAll(".toolbar__item[data-child-id]") ?? []
    );
    const allTitleGroupEls = Array.from(
      this.shadowRoot?.querySelectorAll(".toolbar__title-group[data-child-id]") ?? []
    );
    const allChildren = [...this._startChildren, ...this._centerChildren, ...this._endChildren];
    allItemEls.forEach((el) => {
      el.classList.remove("is-hidden");
      if (el.classList.contains("is-solo-fluid")) {
        el.classList.replace("is-solo-fluid", "is-fluid");
        const id = Number(el.dataset.childId);
        const child = allChildren.find((c) => c.id === id);
        if (child?.type === "item" && child.minWidth) {
          el.style.setProperty("--_item-min-width", child.minWidth);
        }
      }
    });
    allTitleGroupEls.forEach((el) => {
      if (el.classList.contains("is-solo-fluid")) {
        el.classList.remove("is-solo-fluid");
        el.style.removeProperty("min-width");
      }
    });
    if (this._pinnedOverflowItems.length > 0) {
      overflowButtonEl?.classList.remove("is-hidden");
    } else {
      overflowButtonEl?.classList.add("is-hidden");
    }
    void itemsEl.offsetWidth;
    const isOverflowing = () => itemsEl.scrollWidth > itemsEl.clientWidth + 1;
    if (!isOverflowing()) {
      if (this._overflowIds.size > 0) {
        this._overflowIds = /* @__PURE__ */ new Set();
      }
      this._measureItemWidths();
      this._updateAreaVars();
      return;
    }
    overflowButtonEl?.classList.remove("is-hidden");
    void itemsEl.offsetWidth;
    const prioritized = this._getPrioritizedItems();
    const newOverflowIds = /* @__PURE__ */ new Set();
    for (const child of prioritized) {
      if (!isOverflowing()) break;
      if (child.isFluid) {
        const remainingVisible2 = allItemEls.filter(
          (el2) => !el2.classList.contains("is-hidden") && !el2.classList.contains("is-fluid") && !el2.classList.contains("is-solo-fluid")
        );
        if (remainingVisible2.length === 0) break;
      }
      newOverflowIds.add(child.id);
      const el = this.shadowRoot?.querySelector(
        `.toolbar__item[data-child-id="${child.id}"]`
      );
      el?.classList.add("is-hidden");
      void itemsEl.offsetWidth;
    }
    if (newOverflowIds.size === 0 && this._pinnedOverflowItems.length === 0) {
      overflowButtonEl?.classList.add("is-hidden");
    }
    const remainingVisible = allItemEls.filter((el) => !el.classList.contains("is-hidden"));
    if (remainingVisible.length === 1 && remainingVisible[0].classList.contains("is-fluid")) {
      remainingVisible[0].classList.replace("is-fluid", "is-solo-fluid");
      remainingVisible[0].style.removeProperty("--_item-min-width");
      void itemsEl.offsetWidth;
    }
    const remainingTitleGroups = allTitleGroupEls.filter((el) => !el.classList.contains("is-hidden"));
    if (remainingVisible.length === 0 && remainingTitleGroups.length === 1) {
      remainingTitleGroups[0].classList.add("is-solo-fluid");
      remainingTitleGroups[0].style.setProperty("min-width", "0px");
      void itemsEl.offsetWidth;
    }
    const changed = newOverflowIds.size !== this._overflowIds.size || [...newOverflowIds].some((id) => !this._overflowIds.has(id));
    if (changed) {
      this._overflowIds = newOverflowIds;
    }
    this._measureItemWidths();
    this._updateAreaVars();
  }
  _buildChildrenForSlot(slotName) {
    return Array.from(this.children).filter((el) => el.getAttribute("slot") === slotName).map((el) => {
      const tag = el.tagName.toLowerCase();
      if (tag === "ndd-toolbar-title-group") {
        const id2 = this._getId(el);
        el.dataset.toolbarSlot = slotName;
        el.setAttribute("slot", `child-${id2}`);
        return {
          type: "title-group",
          title: el.getAttribute("text") ?? "",
          subtitle: el.getAttribute("subtext") ?? "",
          align: el.getAttribute("align") ?? "left",
          minWidth: el.getAttribute("min-width") ?? "200px",
          id: id2
        };
      }
      if (tag === "ndd-toolbar-item") {
        const id2 = this._getId(el);
        const label = el.getAttribute("label") ?? "";
        const priority = parseInt(el.getAttribute("priority") ?? "0", 10);
        const minWidth = el.getAttribute("min-width") ?? "";
        const width = el.getAttribute("width") ?? "";
        const isFluid = !!(minWidth || width);
        Array.from(el.children).forEach((child) => {
          if (child.getAttribute("slot") !== "overflow") {
            child.setAttribute("size", this.size);
          }
        });
        el.dataset.toolbarSlot = slotName;
        el.setAttribute("slot", `child-${id2}`);
        const overflowItems = Array.from(el.children).filter((child) => {
          const childTag = child.tagName.toLowerCase();
          return childTag === "ndd-menu-item" || childTag === "ndd-menu-divider";
        });
        overflowItems.forEach((child) => child.setAttribute("slot", "overflow"));
        return { type: "item", element: el, label, id: id2, priority, overflowItems, minWidth, width, isFluid };
      }
      const id = this._getId(el);
      el.dataset.toolbarSlot = slotName;
      el.setAttribute("slot", `child-${id}`);
      return { type: "other", element: el, id };
    });
  }
  _buildPinnedOverflowItems() {
    this._pinnedOverflowItems = Array.from(this.children).filter((el) => {
      const tag = el.tagName.toLowerCase();
      return el.getAttribute("slot") === "overflow" && (tag === "ndd-menu-item" || tag === "ndd-menu-divider");
    });
  }
  _restoreSlots() {
    Array.from(this.children).filter((el) => el instanceof HTMLElement && !!el.dataset.toolbarSlot).forEach((el) => {
      el.setAttribute("slot", el.dataset.toolbarSlot);
      delete el.dataset.toolbarSlot;
    });
  }
  _buildChildren() {
    if (this._isBuilding) return;
    this._isBuilding = true;
    this._observer?.disconnect();
    this._restoreSlots();
    this._startChildren = this._buildChildrenForSlot("start");
    this._centerChildren = this._buildChildrenForSlot("center");
    this._endChildren = this._buildChildrenForSlot("end");
    this._buildPinnedOverflowItems();
    this._prioritizedItemsCache = null;
    const itemAttributeFilter = ["label", "priority", "min-width", "width", "text", "disabled", "selected", "type"];
    this._observer?.observe(this, { childList: true, attributes: true, subtree: true, attributeFilter: itemAttributeFilter });
    this._isBuilding = false;
  }
  render() {
    const allChildren = [...this._startChildren, ...this._centerChildren, ...this._endChildren];
    const visibleNonDivider = allChildren.filter(
      (c) => !this._overflowIds.has(c.id)
    );
    const isSoloFluid = visibleNonDivider.length === 1 && (visibleNonDivider[0].type === "title-group" || visibleNonDivider[0].type === "item" && visibleNonDivider[0].isFluid);
    return template$c(
      this._startChildren,
      this._centerChildren,
      this._endChildren,
      this._overflowIds,
      this.size,
      this._centerChildren.length > 0,
      this._leftSpacerZero,
      this._rightSpacerZero,
      isSoloFluid,
      this._pinnedOverflowItems.length > 0 || this._overflowIds.size > 0,
      this._menuOpen,
      this.label,
      this._menu?.id ?? "",
      () => this._handleOverflowButtonClick(),
      this._startChildren.length === 0 && this._endChildren.length === 0 && this._centerChildren.length > 0,
      (key) => this._t(key)
    );
  }
};
NDDToolbar.styles = styles$d;
__decorateClass$Z([
  property({ type: String, reflect: true })
], NDDToolbar.prototype, "size", 2);
__decorateClass$Z([
  property({ type: Boolean, reflect: true, attribute: "show-item-labels" })
], NDDToolbar.prototype, "showItemLabels", 2);
__decorateClass$Z([
  property({ type: String, reflect: true })
], NDDToolbar.prototype, "label", 2);
__decorateClass$Z([
  property({ type: Object })
], NDDToolbar.prototype, "translations", 2);
__decorateClass$Z([
  state()
], NDDToolbar.prototype, "_menuOpen", 2);
__decorateClass$Z([
  state()
], NDDToolbar.prototype, "_startChildren", 2);
__decorateClass$Z([
  state()
], NDDToolbar.prototype, "_centerChildren", 2);
__decorateClass$Z([
  state()
], NDDToolbar.prototype, "_endChildren", 2);
__decorateClass$Z([
  state()
], NDDToolbar.prototype, "_overflowIds", 2);
__decorateClass$Z([
  state()
], NDDToolbar.prototype, "_leftSpacerZero", 2);
__decorateClass$Z([
  state()
], NDDToolbar.prototype, "_rightSpacerZero", 2);
__decorateClass$Z([
  state()
], NDDToolbar.prototype, "_pinnedOverflowItems", 2);
NDDToolbar = __decorateClass$Z([
  customElement("ndd-toolbar")
], NDDToolbar);
var __defProp$T = Object.defineProperty;
var __getOwnPropDesc$X = Object.getOwnPropertyDescriptor;
var __decorateClass$Y = (decorators, target, key, kind) => {
  var result = kind > 1 ? void 0 : kind ? __getOwnPropDesc$X(target, key) : target;
  for (var i = decorators.length - 1, decorator; i >= 0; i--)
    if (decorator = decorators[i])
      result = (kind ? decorator(target, key, result) : decorator(result)) || result;
  if (kind && result) __defProp$T(target, key, result);
  return result;
};
let NDDRichText = class extends LitElement {
  constructor() {
    super(...arguments);
    this.spacing = "snug";
  }
  createRenderRoot() {
    return this;
  }
};
__decorateClass$Y([
  property({ type: String, reflect: true })
], NDDRichText.prototype, "spacing", 2);
NDDRichText = __decorateClass$Y([
  customElement("ndd-rich-text")
], NDDRichText);
const breakpoints = {
  smMax: "640px",
  mdMin: "641px",
  mdMax: "1007px",
  lgMin: "1008px"
};
const smMax$5 = unsafeCSS(breakpoints.smMax);
const mdMin$5 = unsafeCSS(breakpoints.mdMin);
const mdMax$2 = unsafeCSS(breakpoints.mdMax);
const lgMin$4 = unsafeCSS(breakpoints.lgMin);
const titleStyles = css`
	:host {
		display: flex;
		container-type: inline-size;
	}

	:host([hidden]) {
		display: none;
	}


	/* # Title bar */

	.title {
		display: flex;
		flex-direction: row;
		align-items: center;
		gap: var(--primitives-space-12);
		width: 100%;
	}


	/* # Title group */

	.title__title-group {
		display: flex;
		flex-direction: column;
		flex: 1;
		min-width: 0;
	}


	/* # Overline */

	::slotted([slot='overline']) {
		margin: 0;
		color: var(--semantics-content-secondary-color);
		font: var(--primitives-font-body-sm-regular-tight);
	}


	/* # Title */

	::slotted(:not([slot])) {
		margin: 0;
		padding: 0;
		color: var(--semantics-content-color);
	}


	/* # Subtitle */

	::slotted([slot='subtitle']) {
		margin: 0;
		color: var(--semantics-content-secondary-color);
		font: var(--primitives-font-body-sm-regular-tight);
	}


	/* # Actions */

	.title__actions {
		display: flex;
		flex-direction: row;
		align-items: center;
		flex-shrink: 0;
	}


	/* # Size 1 */

	@container layout-area (max-width: ${smMax$5}) {
		:host([size='1']) ::slotted(:not([slot])) {
			font: var(--primitives-font-display-1-sm);
		}
	}

	@container layout-area (min-width: ${mdMin$5}) and (max-width: ${mdMax$2}) {
		:host([size='1']) ::slotted(:not([slot])) {
			font: var(--primitives-font-display-1-md);
		}
	}

	@container layout-area (min-width: ${lgMin$4}) {
		:host([size='1']) ::slotted(:not([slot])) {
			font: var(--primitives-font-display-1-lg);
		}
	}


	/* # Size 2 */

	@container layout-area (max-width: ${smMax$5}) {
		:host([size='2']) ::slotted(:not([slot])) {
			font: var(--primitives-font-display-2-sm);
		}
	}

	@container layout-area (min-width: ${mdMin$5}) and (max-width: ${mdMax$2}) {
		:host([size='2']) ::slotted(:not([slot])) {
			font: var(--primitives-font-display-2-md);
		}
	}

	@container layout-area (min-width: ${lgMin$4}) {
		:host([size='2']) ::slotted(:not([slot])) {
			font: var(--primitives-font-display-2-lg);
		}
	}


	/* # Size 3 */

	@container layout-area (max-width: ${smMax$5}) {
		:host([size='3']) ::slotted(:not([slot])),
		:host(:not([size])) ::slotted(:not([slot])) {
			font: var(--primitives-font-display-3-sm);
		}
	}

	@container layout-area (min-width: ${mdMin$5}) and (max-width: ${mdMax$2}) {
		:host([size='3']) ::slotted(:not([slot])),
		:host(:not([size])) ::slotted(:not([slot])) {
			font: var(--primitives-font-display-3-md);
		}
	}

	@container layout-area (min-width: ${lgMin$4}) {
		:host([size='3']) ::slotted(:not([slot])),
		:host(:not([size])) ::slotted(:not([slot])) {
			font: var(--primitives-font-display-3-lg);
		}
	}


	/* # Size 4 */

	@container layout-area (max-width: ${smMax$5}) {
		:host([size='4']) ::slotted(:not([slot])) {
			font: var(--primitives-font-display-4-sm);
		}
	}

	@container layout-area (min-width: ${mdMin$5}) and (max-width: ${mdMax$2}) {
		:host([size='4']) ::slotted(:not([slot])) {
			font: var(--primitives-font-display-4-md);
		}
	}

	@container layout-area (min-width: ${lgMin$4}) {
		:host([size='4']) ::slotted(:not([slot])) {
			font: var(--primitives-font-display-4-lg);
		}
	}


	/* # Size 5 */

	@container layout-area (max-width: ${smMax$5}) {
		:host([size='5']) ::slotted(:not([slot])) {
			font: var(--primitives-font-display-5-sm);
		}
	}

	@container layout-area (min-width: ${mdMin$5}) and (max-width: ${mdMax$2}) {
		:host([size='5']) ::slotted(:not([slot])) {
			font: var(--primitives-font-display-5-md);
		}
	}

	@container layout-area (min-width: ${lgMin$4}) {
		:host([size='5']) ::slotted(:not([slot])) {
			font: var(--primitives-font-display-5-lg);
		}
	}


	/* # Size 6 */

	@container layout-area (max-width: ${smMax$5}) {
		:host([size='6']) ::slotted(:not([slot])) {
			font: var(--primitives-font-display-6-sm);
		}
	}

	@container layout-area (min-width: ${mdMin$5}) and (max-width: ${mdMax$2}) {
		:host([size='6']) ::slotted(:not([slot])) {
			font: var(--primitives-font-display-6-md);
		}
	}

	@container layout-area (min-width: ${lgMin$4}) {
		:host([size='6']) ::slotted(:not([slot])) {
			font: var(--primitives-font-display-6-lg);
		}
	}
`;
function titleTemplate() {
  return html`
		<div class="title">
			<div class="title__title-group">
				<slot name="overline"></slot>
				<slot></slot>
				<slot name="subtitle"></slot>
			</div>
			<div class="title__actions">
				<slot name="actions"></slot>
			</div>
		</div>
	`;
}
var __defProp$S = Object.defineProperty;
var __getOwnPropDesc$W = Object.getOwnPropertyDescriptor;
var __decorateClass$X = (decorators, target, key, kind) => {
  var result = kind > 1 ? void 0 : kind ? __getOwnPropDesc$W(target, key) : target;
  for (var i = decorators.length - 1, decorator; i >= 0; i--)
    if (decorator = decorators[i])
      result = (kind ? decorator(target, key, result) : decorator(result)) || result;
  if (kind && result) __defProp$S(target, key, result);
  return result;
};
let NDDTitle = class extends LitElement {
  constructor() {
    super(...arguments);
    this.size = 3;
  }
  render() {
    return titleTemplate();
  }
};
NDDTitle.styles = titleStyles;
__decorateClass$X([
  property({ type: Number, reflect: true })
], NDDTitle.prototype, "size", 2);
NDDTitle = __decorateClass$X([
  customElement("ndd-title")
], NDDTitle);
const formFieldStyles = css`


	/* # Host */

	:host {
		display: block;
		container-type: inline-size;
	}

	:host([hidden]) {
		display: none;
	}


	/* # Form field */

	.form-field {
		display: flex;
		flex-direction: column;
		gap: var(--primitives-space-2);
	}

	@container (min-width: 640px) {
		:host([label-alignment='left']) .form-field,
		:host([label-alignment='right']) .form-field {
			flex-direction: row;
			align-items: start;
			gap: var(--primitives-space-8);
		}
	}


	/* # Header */

	.form-field__header {
		display: flex;
		flex-direction: column;
		box-sizing: border-box;
	}

	.form-field__header.is-empty {
		display: none;
	}

	@container (min-width: 640px) {
		:host([label-alignment='left']) .form-field__header.is-empty,
		:host([label-alignment='right']) .form-field__header.is-empty {
			display: flex;
		}

		:host([label-alignment='left']) .form-field__header,
		:host([label-alignment='right']) .form-field__header {
			flex-grow: 0;
			flex-shrink: 0;
			justify-content: center;
			width: var(--primitives-area-240);
			min-height: var(--semantics-controls-md-min-size);
		}

		:host([label-alignment='right']) .form-field__header {
			align-items: end;
			text-align: right;
		}

		:host([label-alignment='left']) .form-field__header {
			align-items: start;
			text-align: left;
		}
	}


	/* # Label */

	.form-field__label {
		display: inline-flex;
		align-items: baseline;
		gap: var(--primitives-space-4);
		color: var(--semantics-content-color);
		font: var(--primitives-font-body-md-regular-tight);
	}

	@container (min-width: 640px) {
		:host([label-alignment='left']) .form-field__label,
		:host([label-alignment='right']) .form-field__label {
			display: flex;
			flex-direction: column;
			gap: var(--primitives-space-0);
		}

		:host([label-alignment='right']) .form-field__label {
			align-items: end;
		}

		:host([label-alignment='left']) .form-field__label {
			align-items: start;
		}
	}


	/* # Optional indicator */

	.form-field__optional {
		color: var(--semantics-content-secondary-color);
		font: var(--primitives-font-body-xs-regular-tight);
	}


	/* # Supporting label */

	.form-field__supporting-label {
		color: var(--semantics-content-secondary-color);
		font: var(--primitives-font-body-xs-regular-tight);
	}


	/* # Main */

	.form-field__main {
		display: flex;
		flex-direction: column;
		flex-grow: 1;
		flex-shrink: 1;
		flex-basis: 0;
		min-width: 0;
	}


	/* # Errors */

	.form-field__errors {
		display: flex;
		flex-direction: column;
	}

	:host(.has-errors) .form-field__errors {
		margin-top: var(--primitives-space-2);
	}
`;
const formFieldHelpTextStyles = css`


	/* # Host */

	:host {
		display: contents;
	}


	/* # Help text */

	.form-field__help-text {
		margin: var(--primitives-space-2) 0 0;
		color: var(--semantics-content-color);
		font: var(--primitives-font-body-sm-regular-tight);
	}


	/* # Links */

	::slotted(a) {
		color: var(--semantics-links-color);
		text-decoration: underline;
		text-underline-offset: var(--primitives-space-2);
		border-radius: var(--primitives-corner-radius-xxs);
	}

	::slotted(a:hover) {
		color: var(--semantics-links-is-hovered-color);
	}

	::slotted(a:active) {
		color: var(--semantics-links-is-active-color);
	}

	::slotted(a:focus-visible) {
		box-shadow: var(--semantics-focus-ring-box-shadow);
		outline: var(--semantics-focus-ring-outline);
	}

	::slotted(a:focus:not(:focus-visible)) {
		outline: none;
	}
`;
const formFieldErrorTextStyles = css`


	/* # Host */

	:host {
		display: none;
	}

	:host([invalid]) {
		display: block;
	}


	/* # Error text */

	.form-field__error-text {
		margin: 0;
		color: var(--semantics-content-error-color);
		font: var(--primitives-font-body-sm-regular-tight);
	}


	/* # Links */

	::slotted(a) {
		color: var(--semantics-links-color);
		text-decoration: underline;
		text-underline-offset: var(--primitives-space-2);
		border-radius: var(--primitives-corner-radius-xxs);
	}

	::slotted(a:hover) {
		color: var(--semantics-links-is-hovered-color);
	}

	::slotted(a:active) {
		color: var(--semantics-links-is-active-color);
	}

	::slotted(a:focus-visible) {
		box-shadow: var(--semantics-focus-ring-box-shadow);
		outline: var(--semantics-focus-ring-outline);
	}

	::slotted(a:focus:not(:focus-visible)) {
		outline: none;
	}
`;
function renderOptional(label) {
  return html`<span class="form-field__optional">${label}</span>`;
}
function formFieldTemplate(component) {
  const hasLabel = Boolean(component.label);
  const hasSupportingLabel = Boolean(component.supportingLabel);
  const isHeaderEmpty = !hasLabel && !hasSupportingLabel;
  const headerEl = html`
		<div class="form-field__header ${isHeaderEmpty ? "is-empty" : ""}">
			${hasLabel ? html`
				<label class="form-field__label"
					@click=${(e) => component._focusInput(e)}
				>
					${component.label}
					${component.optional ? renderOptional(component.optionalLabel) : nothing}
				</label>
			` : nothing}
			${hasSupportingLabel ? html`
				<span class="form-field__supporting-label">${component.supportingLabel}</span>
			` : nothing}
		</div>
	`;
  return html`
		<div class="form-field">
			${headerEl}
			<div class="form-field__main">
				<slot></slot>
				<div class="form-field__errors"
					aria-live="polite"
				>
					<slot name="errors"></slot>
				</div>
				<slot name="help"></slot>
			</div>
		</div>
	`;
}
function formFieldHelpTextTemplate(_component) {
  return html`
		<p class="form-field__help-text">
			<slot></slot>
		</p>
	`;
}
function formFieldErrorTextTemplate(_component) {
  return html`
		<p class="form-field__error-text">
			<slot></slot>
		</p>
	`;
}
var __defProp$R = Object.defineProperty;
var __getOwnPropDesc$V = Object.getOwnPropertyDescriptor;
var __decorateClass$W = (decorators, target, key, kind) => {
  var result = kind > 1 ? void 0 : kind ? __getOwnPropDesc$V(target, key) : target;
  for (var i = decorators.length - 1, decorator; i >= 0; i--)
    if (decorator = decorators[i])
      result = (kind ? decorator(target, key, result) : decorator(result)) || result;
  if (kind && result) __defProp$R(target, key, result);
  return result;
};
const HELPER_TAGS = ["ndd-form-field-help-text", "ndd-form-field-error-text"];
function generateId() {
  const uuid = crypto.randomUUID?.() ?? Math.random().toString(36).slice(2);
  return `ndd-field-input-${uuid}`;
}
let NDDFormField = class extends LitElement {
  constructor() {
    super(...arguments);
    this.labelAlignment = "top";
    this.label = "";
    this.supportingLabel = "";
    this.optional = false;
    this.optionalLabel = "Optioneel";
    this._childObserver = null;
    this._observer = null;
    this._hasErrors = false;
  }
  render() {
    return formFieldTemplate(this);
  }
  updated(changed) {
    this.classList.toggle("has-errors", this._hasErrors);
    if (changed.has("label")) {
      this._onSlotChange();
    }
  }
  connectedCallback() {
    super.connectedCallback();
    this._childObserver = new MutationObserver(() => this._onSlotChange());
    this._childObserver.observe(this, { childList: true });
  }
  firstUpdated() {
    this._onSlotChange();
  }
  disconnectedCallback() {
    super.disconnectedCallback();
    this._childObserver?.disconnect();
    this._observer?.disconnect();
  }
  /** Called when the label header is clicked — focuses the slotted input. */
  _focusInput(e) {
    const input = this._findInput();
    if (!input) return;
    const tag = input.tagName.toLowerCase();
    const type = input.type?.toLowerCase();
    if (tag !== "input" || type !== "checkbox" && type !== "radio") {
      e.preventDefault();
    }
    input.focus();
  }
  _onSlotChange() {
    this._observer?.disconnect();
    const input = this._findInput();
    if (!input) return;
    const isCustomInput = "inputId" in input;
    if (isCustomInput) {
      const existingId = input.inputId;
      const generatedId = existingId || generateId();
      input.inputId = generatedId;
    } else {
      if (!input.id) input.id = generateId();
    }
    if (this.label) {
      if (isCustomInput) {
        input.setAttribute("accessible-label", this.label);
        input.removeAttribute("aria-label");
      } else {
        input.setAttribute("aria-label", this.label);
        input.removeAttribute("accessible-label");
      }
    } else {
      input.removeAttribute("accessible-label");
      input.removeAttribute("aria-label");
    }
    Array.from(this.children).filter((el) => el.tagName.toLowerCase() === "ndd-form-field-help-text").forEach((el) => {
      if (!el.id) el.id = generateId();
    });
    this._observer = new MutationObserver(() => this._syncErrorText());
    this._observer.observe(input, {
      attributes: true,
      attributeFilter: ["invalid", "error-message"]
    });
    this._syncErrorText();
  }
  /** First child element that is not a form field helper component. */
  _findInput() {
    return Array.from(this.children).find((el) => !HELPER_TAGS.includes(el.tagName.toLowerCase()));
  }
  /**
   * Reads `invalid` and `error-message` from the input and toggles
   * the `invalid` attribute on the referenced ndd-form-field-error-text elements.
   * Also sets `aria-describedby` on the input to reference visible error texts.
   *
   * Note: this mechanism relies on the slotted input reflecting an `invalid`
   * attribute, which ndd-text-field and ndd-password-field do. Plain native
   * `<input>` elements use constraint validation (validity.valid, the `invalid`
   * event) instead — support for native inputs is a known limitation and
   * tracked as a follow-up.
   */
  _syncErrorText() {
    const input = this._findInput();
    if (!input) return;
    const isCustomInput = "inputId" in input;
    const isInvalid = input.hasAttribute("invalid");
    const referencedIds = (input.getAttribute("error-message") ?? "").split(" ").filter(Boolean);
    const allErrorTexts = Array.from(this.children).filter((el) => el.tagName.toLowerCase() === "ndd-form-field-error-text");
    const helpIds = Array.from(this.children).filter((el) => el.tagName.toLowerCase() === "ndd-form-field-help-text" && el.id).map((el) => el.id);
    const visibleErrorIds = [];
    for (const el of allErrorTexts) {
      const shouldShow = isInvalid && referencedIds.includes(el.id);
      el.toggleAttribute("invalid", shouldShow);
      if (shouldShow && el.id) visibleErrorIds.push(el.id);
    }
    const describedByIds = [...helpIds, ...visibleErrorIds];
    const describedByValue = describedByIds.join(" ");
    if (isCustomInput) {
      input.errorMessageIds = describedByValue;
    } else {
      if (describedByIds.length > 0) {
        input.setAttribute("aria-describedby", describedByValue);
      } else {
        input.removeAttribute("aria-describedby");
      }
    }
    this._hasErrors = visibleErrorIds.length > 0;
  }
};
NDDFormField.styles = formFieldStyles;
__decorateClass$W([
  property({ type: String, attribute: "label-alignment", reflect: true })
], NDDFormField.prototype, "labelAlignment", 2);
__decorateClass$W([
  property({ type: String })
], NDDFormField.prototype, "label", 2);
__decorateClass$W([
  property({ type: String, attribute: "supporting-label" })
], NDDFormField.prototype, "supportingLabel", 2);
__decorateClass$W([
  property({ type: Boolean })
], NDDFormField.prototype, "optional", 2);
__decorateClass$W([
  property({ type: String, attribute: "optional-label" })
], NDDFormField.prototype, "optionalLabel", 2);
__decorateClass$W([
  state()
], NDDFormField.prototype, "_hasErrors", 2);
NDDFormField = __decorateClass$W([
  customElement("ndd-form-field")
], NDDFormField);
let NDDFormFieldHelpText = class extends LitElement {
  connectedCallback() {
    super.connectedCallback();
    this.slot = "help";
  }
  render() {
    return formFieldHelpTextTemplate();
  }
};
NDDFormFieldHelpText.styles = formFieldHelpTextStyles;
NDDFormFieldHelpText = __decorateClass$W([
  customElement("ndd-form-field-help-text")
], NDDFormFieldHelpText);
let NDDFormFieldErrorText = class extends LitElement {
  constructor() {
    super(...arguments);
    this.invalid = false;
  }
  connectedCallback() {
    super.connectedCallback();
    this.slot = "errors";
  }
  render() {
    return formFieldErrorTextTemplate();
  }
};
NDDFormFieldErrorText.styles = formFieldErrorTextStyles;
__decorateClass$W([
  property({ type: Boolean, reflect: true })
], NDDFormFieldErrorText.prototype, "invalid", 2);
NDDFormFieldErrorText = __decorateClass$W([
  customElement("ndd-form-field-error-text")
], NDDFormFieldErrorText);
const textFieldStyles = css`


	/* # Host */

	:host {
		display: block;
		--_background-color: var(--semantics-input-fields-background-color);
		-webkit-tap-highlight-color: transparent;
	}

	:host([hidden]) {
		display: none;
	}


	/* # Container */

	.text-field {
		display: flex;
		flex-direction: row;
		align-items: center;
		overflow: hidden;
		box-sizing: border-box;
		padding-left: var(--primitives-space-12);
		min-height: var(--semantics-controls-md-min-size);
		border: var(--semantics-input-fields-border-thickness) solid var(--semantics-input-fields-border-color);
		border-radius: var(--semantics-controls-md-corner-radius);
		background-color: var(--_background-color);
	}

	:host([size='sm']) .text-field {
		padding-left: var(--primitives-space-8);
		min-height: var(--semantics-controls-sm-min-size);
		border-radius: var(--semantics-controls-sm-corner-radius);
	}

	:host([valid]) .text-field {
		border-color: var(--semantics-input-fields-is-valid-border-color);
	}

	:host([invalid]) .text-field {
		border-color: var(--semantics-input-fields-is-invalid-border-color);
	}

	:host([readonly]) .text-field {
		border-color: var(--semantics-input-fields-is-read-only-border-color);
		--_background-color: var(--semantics-input-fields-is-read-only-background-color);
	}

	:host([disabled]) .text-field {
		opacity: var(--primitives-opacity-disabled);
	}

	.text-field:has(input:-webkit-autofill),
	.text-field:has(input:autofill) {
		--_background-color: var(--semantics-input-fields-is-autofill-background-color);
	}

	.text-field:focus-within {
		outline: var(--semantics-focus-ring-outline);
		box-shadow: var(--semantics-focus-ring-box-shadow);
	}


	/* # Input */

	.text-field__input {
		flex-grow: 1;
		min-width: 0;
		overflow: hidden;
		box-sizing: border-box;
		padding: 0;
		margin: 0;
		min-height: calc(var(--semantics-controls-md-min-size) - var(--semantics-input-fields-border-thickness) * 2);
		font: var(--semantics-input-fields-md-text-font);
		color: var(--semantics-content-color);
		background: transparent;
		border: none;
		outline: none;
		appearance: none;
	}

	:host([size='sm']) .text-field__input {
		min-height: calc(var(--semantics-controls-sm-min-size) - var(--semantics-input-fields-border-thickness) * 2);
		font: var(--semantics-input-fields-sm-text-font);
	}

	:host([disabled]) .text-field__input {
		pointer-events: none;
	}

	.text-field__input::placeholder {
		color: var(--semantics-input-fields-placeholder-color);
	}

	.text-field__input:-webkit-autofill,
	.text-field__input:autofill {
		box-shadow: 0 0 0 999px var(--_background-color) inset;
	}


	/* # Fade */

	.text-field__fade {
		position: relative;
		flex-shrink: 0;
		align-self: stretch;
		width: 0;
	}

	.text-field__fade::after {
		content: '';
		position: absolute;
		top: 0;
		bottom: 0;
		right: 0;
		width: var(--primitives-space-8);
		border-radius: var(--semantics-controls-md-corner-radius);
		background: linear-gradient(90deg, color-mix(in oklch, var(--_background-color) 0%, transparent) 0%, var(--_background-color) 100%);
		pointer-events: none;
	}

	:host([size='sm']) .text-field__fade::after {
		border-radius: var(--semantics-controls-sm-corner-radius);
	}


	/* # Validation icon area */

	.text-field__validation-icon-area {
		display: flex;
		align-items: center;
		justify-content: center;
		flex-shrink: 0;
		width: calc(var(--semantics-controls-md-min-size) - var(--semantics-input-fields-border-thickness) * 2);
		height: 100%;
	}

	:host([size='sm']) .text-field__validation-icon-area {
		width: calc(var(--semantics-controls-sm-min-size) - var(--semantics-input-fields-border-thickness) * 2);
	}

	:host([valid]) .text-field__validation-icon-area {
		color: var(--semantics-input-fields-is-valid-icon-color);
	}

	:host([invalid]) .text-field__validation-icon-area {
		color: var(--semantics-input-fields-is-invalid-icon-color);
	}


	/* # Validation icon */

	.text-field__validation-icon {
		width: var(--primitives-space-24);
		height: var(--primitives-space-24);
	}

	:host([size='sm']) .text-field__validation-icon {
		width: var(--primitives-space-20);
		height: var(--primitives-space-20);
	}
`;
function renderValidationIcon$1(component) {
  if (component.valid) {
    return html`
			<div class="text-field__validation-icon-area">
				<ndd-icon class="text-field__validation-icon"
					name="valid"
					aria-hidden="true"
				></ndd-icon>
			</div>
		`;
  }
  if (component.invalid) {
    return html`
			<div class="text-field__validation-icon-area">
				<ndd-icon class="text-field__validation-icon"
					name="invalid"
					aria-hidden="true"
				></ndd-icon>
			</div>
		`;
  }
  return nothing;
}
function textFieldTemplate(component) {
  return html`
		<div class="text-field">
			<input class="text-field__input"
				id=${component.inputId || nothing}
				type=${component.type}
				.value=${component.value}
				placeholder=${component.placeholder || nothing}
				?disabled=${component.disabled}
				?readonly=${component.readonly}
				?required=${component.required}
				name=${component.name || nothing}
				autocomplete=${component.autocomplete || nothing}
				aria-label=${component.accessibleLabel || nothing}
				aria-describedby=${component.errorMessageIds || nothing}
				aria-invalid=${component.invalid ? "true" : nothing}
				@input=${component._handleInput}
				@change=${component._handleChange}
			/>
			<div class="text-field__fade"></div>
			${renderValidationIcon$1(component)}
		</div>
	`;
}
var __defProp$Q = Object.defineProperty;
var __getOwnPropDesc$U = Object.getOwnPropertyDescriptor;
var __decorateClass$V = (decorators, target, key, kind) => {
  var result = kind > 1 ? void 0 : kind ? __getOwnPropDesc$U(target, key) : target;
  for (var i = decorators.length - 1, decorator; i >= 0; i--)
    if (decorator = decorators[i])
      result = (kind ? decorator(target, key, result) : decorator(result)) || result;
  if (kind && result) __defProp$Q(target, key, result);
  return result;
};
let NDDTextField = class extends LitElement {
  constructor() {
    super(...arguments);
    this.size = "md";
    this.value = "";
    this.inputId = "";
    this.placeholder = "";
    this.invalid = false;
    this.valid = false;
    this.disabled = false;
    this.type = "text";
    this.name = "";
    this.readonly = false;
    this.required = false;
    this.autocomplete = "";
    this.accessibleLabel = "";
    this.errorMessageIds = "";
  }
  _handleInput(e) {
    e.stopPropagation();
    const input = e.target;
    this.value = input.value;
    this.dispatchEvent(new CustomEvent("input", {
      detail: { value: this.value },
      bubbles: true,
      composed: true
    }));
  }
  _handleChange(e) {
    e.stopPropagation();
    const input = e.target;
    this.value = input.value;
    this.dispatchEvent(new CustomEvent("change", {
      detail: { value: this.value },
      bubbles: true,
      composed: true
    }));
  }
  focus() {
    this._input?.focus();
  }
  blur() {
    this._input?.blur();
  }
  render() {
    return textFieldTemplate(this);
  }
};
NDDTextField.shadowRootOptions = {
  ...LitElement.shadowRootOptions,
  delegatesFocus: true
};
NDDTextField.styles = textFieldStyles;
__decorateClass$V([
  property({ type: String, reflect: true })
], NDDTextField.prototype, "size", 2);
__decorateClass$V([
  property({ type: String })
], NDDTextField.prototype, "value", 2);
__decorateClass$V([
  property({ type: String, attribute: "input-id" })
], NDDTextField.prototype, "inputId", 2);
__decorateClass$V([
  property({ type: String })
], NDDTextField.prototype, "placeholder", 2);
__decorateClass$V([
  property({ type: Boolean, reflect: true })
], NDDTextField.prototype, "invalid", 2);
__decorateClass$V([
  property({ type: Boolean, reflect: true })
], NDDTextField.prototype, "valid", 2);
__decorateClass$V([
  property({ type: Boolean, reflect: true })
], NDDTextField.prototype, "disabled", 2);
__decorateClass$V([
  property({ type: String })
], NDDTextField.prototype, "type", 2);
__decorateClass$V([
  property({ type: String })
], NDDTextField.prototype, "name", 2);
__decorateClass$V([
  property({ type: Boolean, reflect: true })
], NDDTextField.prototype, "readonly", 2);
__decorateClass$V([
  property({ type: Boolean, reflect: true })
], NDDTextField.prototype, "required", 2);
__decorateClass$V([
  property({ type: String })
], NDDTextField.prototype, "autocomplete", 2);
__decorateClass$V([
  property({ type: String, attribute: "accessible-label" })
], NDDTextField.prototype, "accessibleLabel", 2);
__decorateClass$V([
  property({ type: String, attribute: "error-message-ids" })
], NDDTextField.prototype, "errorMessageIds", 2);
__decorateClass$V([
  query(".text-field__input")
], NDDTextField.prototype, "_input", 2);
NDDTextField = __decorateClass$V([
  customElement("ndd-text-field")
], NDDTextField);
const passwordFieldStyles = css`


	/* # Host */

	:host {
		display: block;
		--_background-color: var(--semantics-input-fields-background-color);
		-webkit-tap-highlight-color: transparent;
	}

	:host([hidden]) {
		display: none;
	}


	/* # Container */

	.password-field {
		display: flex;
		flex-direction: row;
		align-items: center;
		overflow: hidden;
		box-sizing: border-box;
		padding-left: var(--primitives-space-12);
		min-height: var(--semantics-controls-md-min-size);
		border: var(--semantics-input-fields-border-thickness) solid var(--semantics-input-fields-border-color);
		border-radius: var(--semantics-controls-md-corner-radius);
		background-color: var(--_background-color);
	}

	:host([size='sm']) .password-field {
		padding-left: var(--primitives-space-8);
		min-height: var(--semantics-controls-sm-min-size);
		border-radius: var(--semantics-controls-sm-corner-radius);
	}

	:host([valid]) .password-field {
		border-color: var(--semantics-input-fields-is-valid-border-color);
	}

	:host([invalid]) .password-field {
		border-color: var(--semantics-input-fields-is-invalid-border-color);
	}

	:host([readonly]) .password-field {
		border-color: var(--semantics-input-fields-is-read-only-border-color);
		--_background-color: var(--semantics-input-fields-is-read-only-background-color);
	}

	:host([disabled]) .password-field {
		opacity: var(--primitives-opacity-disabled);
	}

	.password-field:has(input:-webkit-autofill),
	.password-field:has(input:autofill) {
		--_background-color: var(--semantics-input-fields-is-autofill-background-color);
	}

	.password-field:focus-within:not(:has(.password-field__visibility-toggle:focus-within)) {
		outline: var(--semantics-focus-ring-outline);
		box-shadow: var(--semantics-focus-ring-box-shadow);
	}

	.password-field:has(.password-field__visibility-toggle:focus-within) {
		overflow: visible;
	}


	/* # Input */

	.password-field__input {
		flex-grow: 1;
		min-width: 0;
		overflow: hidden;
		box-sizing: border-box;
		padding: 0;
		margin: 0;
		min-height: calc(var(--semantics-controls-md-min-size) - var(--semantics-input-fields-border-thickness) * 2);
		font: var(--semantics-input-fields-md-text-font);
		color: var(--semantics-content-color);
		background: transparent;
		border: none;
		outline: none;
		appearance: none;
	}

	.password-field__input.is-masked {
		font: var(--semantics-input-fields-md-mask-font);
	}

	:host([size='sm']) .password-field__input {
		min-height: calc(var(--semantics-controls-sm-min-size) - var(--semantics-input-fields-border-thickness) * 2);
		font: var(--semantics-input-fields-sm-text-font);
	}

	:host([size='sm']) .password-field__input.is-masked {
		font: var(--semantics-input-fields-sm-mask-font);
	}

	:host([disabled]) .password-field__input {
		pointer-events: none;
	}

	.password-field__input::placeholder {
		color: var(--semantics-input-fields-placeholder-color);
		/* Always use text font for placeholder, regardless of masked state */
		font: var(--semantics-input-fields-md-text-font);
	}

	:host([size='sm']) .password-field__input::placeholder {
		font: var(--semantics-input-fields-sm-text-font);
	}

	.password-field__input:-webkit-autofill,
	.password-field__input:autofill {
		box-shadow: 0 0 0 999px var(--_background-color) inset;
	}


	/* # Fade */

	.password-field__fade {
		position: relative;
		flex-shrink: 0;
		align-self: stretch;
		width: 0;
	}

	.password-field__fade::after {
		content: '';
		position: absolute;
		top: 0;
		bottom: 0;
		right: 0;
		width: var(--primitives-space-8);
		border-radius: var(--semantics-controls-md-corner-radius);
		background: linear-gradient(90deg, color-mix(in oklch, var(--_background-color) 0%, transparent) 0%, var(--_background-color) 100%);
		pointer-events: none;
	}


	/* # Validation icon area */

	.password-field__validation-icon-area {
		display: flex;
		align-items: center;
		justify-content: center;
		flex-shrink: 0;
		width: calc(var(--semantics-controls-md-min-size) - var(--semantics-input-fields-border-thickness) * 2);
		height: 100%;
	}

	:host([size='sm']) .password-field__validation-icon-area {
		width: calc(var(--semantics-controls-sm-min-size) - var(--semantics-input-fields-border-thickness) * 2);
	}

	:host([valid]) .password-field__validation-icon-area {
		color: var(--semantics-input-fields-is-valid-icon-color);
	}

	:host([invalid]) .password-field__validation-icon-area {
		color: var(--semantics-input-fields-is-invalid-icon-color);
	}


	/* # Validation icon */

	.password-field__validation-icon {
		width: var(--primitives-space-24);
		height: var(--primitives-space-24);
	}

	:host([size='sm']) .password-field__validation-icon {
		width: var(--primitives-space-20);
		height: var(--primitives-space-20);
	}


	/* # Toggle button */

	.password-field__visibility-toggle {
		display: flex;
		align-items: center;
		justify-content: center;
		flex-shrink: 0;
		height: 100%;
		/* (field height - 2 x border - sm button height) / 2 */
		padding-block: calc((var(--semantics-controls-md-min-size) - var(--semantics-input-fields-border-thickness) * 2 - var(--semantics-controls-sm-min-size)) / 2);
		padding-inline-end: calc((var(--semantics-controls-md-min-size) - var(--semantics-input-fields-border-thickness) * 2 - var(--semantics-controls-sm-min-size)) / 2);
	}

	:host([size='sm']) .password-field__visibility-toggle {
		/* (field height - 2 x border - xs button height) / 2 */
		padding-block: calc((var(--semantics-controls-sm-min-size) - var(--semantics-input-fields-border-thickness) * 2 - var(--semantics-controls-xs-min-size)) / 2);
		padding-inline-end: calc((var(--semantics-controls-sm-min-size) - var(--semantics-input-fields-border-thickness) * 2 - var(--semantics-controls-xs-min-size)) / 2);
	}
`;
function renderValidationIcon(component) {
  if (component.valid) {
    return html`
			<div class="password-field__validation-icon-area">
				<ndd-icon class="password-field__validation-icon"
					name="valid"
					aria-hidden="true"
				></ndd-icon>
			</div>
		`;
  }
  if (component.invalid) {
    return html`
			<div class="password-field__validation-icon-area">
				<ndd-icon class="password-field__validation-icon"
					name="invalid"
					aria-hidden="true"
				></ndd-icon>
			</div>
		`;
  }
  return nothing;
}
function renderVisibilityToggle(component) {
  const buttonSize = component.size === "sm" ? "xs" : "sm";
  const label = component.masked ? component.showText : component.hideText;
  const accessibleLabel = component.masked ? component.showAccessibleLabel : component.hideAccessibleLabel;
  return html`
		<div class="password-field__visibility-toggle">
			<ndd-button
				size=${buttonSize}
				type="button"
				text=${label}
				accessible-label=${accessibleLabel}
				?disabled=${component.disabled}
				@click=${component._handleToggle}
				@mousedown=${(e) => e.preventDefault()}
			></ndd-button>
		</div>
	`;
}
function passwordFieldTemplate(component) {
  return html`
		<div class="password-field">
			<input class="password-field__input ${component.masked ? "is-masked" : ""}"
				id=${component.inputId || nothing}
				type=${component.masked ? "password" : "text"}
				.value=${component.value}
				placeholder=${component.placeholder || nothing}
				?disabled=${component.disabled}
				?readonly=${component.readonly}
				?required=${component.required}
				name=${component.name || nothing}
				autocomplete=${component.autocomplete || nothing}
				aria-label=${component.accessibleLabel || nothing}
				aria-describedby=${component.errorMessageIds || nothing}
				aria-invalid=${component.invalid ? "true" : nothing}
				@input=${component._handleInput}
				@change=${component._handleChange}
			/>
			<div class="password-field__fade"></div>
			${renderValidationIcon(component)}
			${renderVisibilityToggle(component)}
		</div>
	`;
}
var __defProp$P = Object.defineProperty;
var __getOwnPropDesc$T = Object.getOwnPropertyDescriptor;
var __decorateClass$U = (decorators, target, key, kind) => {
  var result = kind > 1 ? void 0 : kind ? __getOwnPropDesc$T(target, key) : target;
  for (var i = decorators.length - 1, decorator; i >= 0; i--)
    if (decorator = decorators[i])
      result = (kind ? decorator(target, key, result) : decorator(result)) || result;
  if (kind && result) __defProp$P(target, key, result);
  return result;
};
let NDDPasswordField = class extends LitElement {
  constructor() {
    super(...arguments);
    this.size = "md";
    this.value = "";
    this.inputId = "";
    this.placeholder = "";
    this.valid = false;
    this.invalid = false;
    this.disabled = false;
    this.masked = true;
    this.showText = "Toon";
    this.hideText = "Verberg";
    this.showAccessibleLabel = "Toon wachtwoord";
    this.hideAccessibleLabel = "Verberg wachtwoord";
    this.readonly = false;
    this.required = false;
    this.name = "";
    this.autocomplete = "";
    this.accessibleLabel = "";
    this.errorMessageIds = "";
  }
  _handleInput(e) {
    e.stopPropagation();
    const input = e.target;
    this.value = input.value;
    this.dispatchEvent(new CustomEvent("input", {
      detail: { value: this.value },
      bubbles: true,
      composed: true
    }));
  }
  _handleChange(e) {
    e.stopPropagation();
    const input = e.target;
    this.value = input.value;
    this.dispatchEvent(new CustomEvent("change", {
      detail: { value: this.value },
      bubbles: true,
      composed: true
    }));
  }
  _handleToggle() {
    this.masked = !this.masked;
    this.updateComplete.then(() => {
      this._input?.focus();
    });
  }
  focus() {
    this._input?.focus();
  }
  blur() {
    this._input?.blur();
  }
  render() {
    return passwordFieldTemplate(this);
  }
};
NDDPasswordField.shadowRootOptions = {
  ...LitElement.shadowRootOptions,
  delegatesFocus: true
};
NDDPasswordField.styles = passwordFieldStyles;
__decorateClass$U([
  property({ type: String, reflect: true })
], NDDPasswordField.prototype, "size", 2);
__decorateClass$U([
  property({ type: String })
], NDDPasswordField.prototype, "value", 2);
__decorateClass$U([
  property({ type: String, attribute: "input-id" })
], NDDPasswordField.prototype, "inputId", 2);
__decorateClass$U([
  property({ type: String })
], NDDPasswordField.prototype, "placeholder", 2);
__decorateClass$U([
  property({ type: Boolean, reflect: true })
], NDDPasswordField.prototype, "valid", 2);
__decorateClass$U([
  property({ type: Boolean, reflect: true })
], NDDPasswordField.prototype, "invalid", 2);
__decorateClass$U([
  property({ type: Boolean, reflect: true })
], NDDPasswordField.prototype, "disabled", 2);
__decorateClass$U([
  property({ type: Boolean, reflect: true })
], NDDPasswordField.prototype, "masked", 2);
__decorateClass$U([
  property({ type: String, attribute: "show-text" })
], NDDPasswordField.prototype, "showText", 2);
__decorateClass$U([
  property({ type: String, attribute: "hide-text" })
], NDDPasswordField.prototype, "hideText", 2);
__decorateClass$U([
  property({ type: String, attribute: "show-accessible-label" })
], NDDPasswordField.prototype, "showAccessibleLabel", 2);
__decorateClass$U([
  property({ type: String, attribute: "hide-accessible-label" })
], NDDPasswordField.prototype, "hideAccessibleLabel", 2);
__decorateClass$U([
  property({ type: Boolean, reflect: true })
], NDDPasswordField.prototype, "readonly", 2);
__decorateClass$U([
  property({ type: Boolean, reflect: true })
], NDDPasswordField.prototype, "required", 2);
__decorateClass$U([
  property({ type: String })
], NDDPasswordField.prototype, "name", 2);
__decorateClass$U([
  property({ type: String })
], NDDPasswordField.prototype, "autocomplete", 2);
__decorateClass$U([
  property({ type: String, attribute: "accessible-label" })
], NDDPasswordField.prototype, "accessibleLabel", 2);
__decorateClass$U([
  property({ type: String, attribute: "error-message-ids" })
], NDDPasswordField.prototype, "errorMessageIds", 2);
__decorateClass$U([
  query(".password-field__input")
], NDDPasswordField.prototype, "_input", 2);
NDDPasswordField = __decorateClass$U([
  customElement("ndd-password-field")
], NDDPasswordField);
const searchFieldStyles = css`
	/* # Host */

	:host {
		display: block;
		--_background-color: var(--semantics-input-fields-background-color);
		-webkit-tap-highlight-color: transparent;
	}

	:host([hidden]) {
		display: none;
	}

	:host([disabled]) {
		opacity: var(--primitives-opacity-disabled);
		pointer-events: none;
	}


	/* # Container */

	.search-field {
		position: relative;
		display: flex;
		flex-direction: row;
		align-items: center;
		box-sizing: border-box;
		width: 100%;
		background-color: var(--_background-color);
		border: var(--semantics-input-fields-border-thickness) solid var(--semantics-input-fields-border-color);
	}

	:host([size='md']) .search-field,
	:host(:not([size])) .search-field {
		min-height: var(--semantics-controls-md-min-size);
		border-radius: var(--semantics-controls-md-corner-radius);
	}

	:host([size='sm']) .search-field {
		min-height: var(--semantics-controls-sm-min-size);
		border-radius: var(--semantics-controls-sm-corner-radius);
	}

	.search-field:has(.search-field__input:focus-visible) {
		box-shadow: var(--semantics-focus-ring-box-shadow);
		outline: var(--semantics-focus-ring-outline);
	}

	.search-field:has(input:-webkit-autofill),
	.search-field:has(input:autofill) {
		--_background-color: var(--semantics-input-fields-is-autofill-background-color);
	}


	/* # Search icon */

	.search-field__search-icon {
		display: flex;
		align-items: center;
		justify-content: center;
		flex-shrink: 0;
		color: var(--semantics-content-secondary-color);
	}

	:host([size='md']) .search-field__search-icon,
	:host(:not([size])) .search-field__search-icon {
		width: var(--primitives-space-24);
		height: var(--primitives-space-24);
		margin-inline: calc((var(--semantics-controls-md-min-size) - var(--primitives-space-24)) / 2 - var(--semantics-input-fields-border-thickness));
	}

	:host([size='sm']) .search-field__search-icon {
		width: var(--primitives-space-20);
		height: var(--primitives-space-20);
		margin-inline: calc((var(--semantics-controls-sm-min-size) - var(--primitives-space-20)) / 2 - var(--semantics-input-fields-border-thickness));
	}


	/* # Input */

	.search-field__input {
		appearance: none;
		border: none;
		background: transparent;
		margin: 0;
		padding: 0;
		outline: none;
		box-sizing: border-box;
		flex: 1;
		min-width: 0;
		color: var(--semantics-content-color);
	}

	:host([size='md']) .search-field__input,
	:host(:not([size])) .search-field__input {
		font: var(--semantics-input-fields-md-text-font);
	}

	:host([size='sm']) .search-field__input {
		font: var(--semantics-input-fields-sm-text-font);
	}

	.search-field__input::placeholder {
		color: var(--semantics-input-fields-placeholder-color);
	}

	.search-field__input:-webkit-autofill,
	.search-field__input:autofill {
		box-shadow: 0 0 0 999px var(--_background-color) inset;
	}

	.search-field__input::-webkit-search-cancel-button {
		-webkit-appearance: none;
	}


	/* # Fade */

	.search-field__fade {
		position: relative;
		flex-shrink: 0;
		align-self: stretch;
		width: 0;
	}

	.search-field__fade::after {
		content: '';
		position: absolute;
		top: 0;
		bottom: 0;
		right: 0;
		width: var(--primitives-space-8);
		border-radius: var(--semantics-controls-md-corner-radius);
		background: linear-gradient(90deg, color-mix(in oklch, var(--_background-color) 0%, transparent) 0%, var(--_background-color) 100%);
		pointer-events: none;
	}


	/* # Actions */

	.search-field__actions {
		display: flex;
		flex-shrink: 0;
		align-items: center;
		position: relative;
		z-index: 1;
	}

	:host([size='md']) .search-field__actions,
	:host(:not([size])) .search-field__actions {
		padding-right: calc((var(--semantics-controls-md-min-size) - var(--semantics-controls-sm-min-size)) / 2 - var(--semantics-input-fields-border-thickness));
		gap: var(--primitives-space-6);
	}

	:host([size='sm']) .search-field__actions {
		padding-right: calc((var(--semantics-controls-sm-min-size) - var(--semantics-controls-xs-min-size)) / 2 - var(--semantics-input-fields-border-thickness));
		gap: var(--primitives-space-4);
	}

	.search-field__dismiss-action:focus-within,
	.search-field__search-action:focus-within {
		position: relative;
		z-index: 1;
	}
`;
function searchFieldTemplate(component) {
  const buttonSize = component.size === "sm" ? "xs" : "sm";
  return html`
		<div class="search-field">
			<div class="search-field__search-icon">
				<ndd-icon name="search"></ndd-icon>
			</div>
			<input class="search-field__input"
				type="search"
				.value=${component.value}
				placeholder=${component.placeholder}
				aria-label=${component.accessibleLabel || component.placeholder || nothing}
				?disabled=${component.disabled}
				name=${component.name || nothing}
				@input=${component._handleInput}
				@change=${component._handleChange}
				@keydown=${component._handleKeydown}
			>
			<div class="search-field__fade"></div>
			<div class="search-field__actions">
				${component.value ? html`
					<div class="search-field__dismiss-action">
						<ndd-icon-button
							variant="neutral-transparent"
							size=${buttonSize}
							icon="dismiss"
							text=${component._t("components.search-field.dismiss-action")}
							@click=${component._handleDismiss}
						></ndd-icon-button>
					</div>
				` : nothing}
				${component.hasSearchButton ? html`
					<div class="search-field__search-action">
						<ndd-button
							variant="neutral-tinted"
							size=${buttonSize}
							text=${component._t("components.search-field.search-action")}
							@click=${component._handleSearch}
						></ndd-button>
					</div>
				` : nothing}
			</div>
		</div>
	`;
}
const nddSearchFieldTranslations = {
  "components.search-field.dismiss-action": "Wis zoekopdracht",
  "components.search-field.search-action": "Zoek"
};
var __defProp$O = Object.defineProperty;
var __getOwnPropDesc$S = Object.getOwnPropertyDescriptor;
var __decorateClass$T = (decorators, target, key, kind) => {
  var result = kind > 1 ? void 0 : kind ? __getOwnPropDesc$S(target, key) : target;
  for (var i = decorators.length - 1, decorator; i >= 0; i--)
    if (decorator = decorators[i])
      result = (kind ? decorator(target, key, result) : decorator(result)) || result;
  if (kind && result) __defProp$O(target, key, result);
  return result;
};
let NDDSearchField = class extends LitElement {
  constructor() {
    super(...arguments);
    this.value = "";
    this.placeholder = "Zoeken";
    this.accessibleLabel = "";
    this.size = "md";
    this.disabled = false;
    this.name = "";
    this.hasSearchButton = false;
    this.translations = {};
  }
  // — i18n ——————————————————————————————————————————————————————————————————
  _t(key) {
    return this.translations[key] ?? nddSearchFieldTranslations[key];
  }
  // — Handlers ————————————————————————————————————————————————————————————
  _handleInput(e) {
    const input = e.target;
    this.value = input.value;
    this.dispatchEvent(new CustomEvent("input", {
      detail: { value: this.value },
      bubbles: true,
      composed: true
    }));
  }
  _handleChange(e) {
    const input = e.target;
    this.value = input.value;
    this.dispatchEvent(new CustomEvent("change", {
      detail: { value: this.value },
      bubbles: true,
      composed: true
    }));
  }
  _handleKeydown(e) {
    if (e.key === "Enter") {
      this._dispatchSearch();
    }
  }
  _handleDismiss() {
    this.value = "";
    this.dispatchEvent(new CustomEvent("change", {
      detail: { value: "" },
      bubbles: true,
      composed: true
    }));
  }
  _handleSearch() {
    this._dispatchSearch();
  }
  _dispatchSearch() {
    this.dispatchEvent(new CustomEvent("search", {
      detail: { value: this.value },
      bubbles: true,
      composed: true
    }));
  }
  render() {
    return searchFieldTemplate(this);
  }
};
NDDSearchField.styles = searchFieldStyles;
__decorateClass$T([
  property({ type: String })
], NDDSearchField.prototype, "value", 2);
__decorateClass$T([
  property({ type: String })
], NDDSearchField.prototype, "placeholder", 2);
__decorateClass$T([
  property({ type: String, attribute: "accessible-label" })
], NDDSearchField.prototype, "accessibleLabel", 2);
__decorateClass$T([
  property({ type: String, reflect: true })
], NDDSearchField.prototype, "size", 2);
__decorateClass$T([
  property({ type: Boolean, reflect: true })
], NDDSearchField.prototype, "disabled", 2);
__decorateClass$T([
  property({ type: String })
], NDDSearchField.prototype, "name", 2);
__decorateClass$T([
  property({ type: Boolean, reflect: true, attribute: "has-search-button" })
], NDDSearchField.prototype, "hasSearchButton", 2);
__decorateClass$T([
  property({ type: Object })
], NDDSearchField.prototype, "translations", 2);
__decorateClass$T([
  query(".search-field__input")
], NDDSearchField.prototype, "_input", 2);
NDDSearchField = __decorateClass$T([
  customElement("ndd-search-field")
], NDDSearchField);
const numberFieldStyles = css`


	/* # Host */

	:host {
		display: inline-block;
		--_width: auto;
		-webkit-tap-highlight-color: transparent;
	}

	:host([hidden]) {
		display: none;
	}

	:host([disabled]) {
		opacity: var(--primitives-opacity-disabled);
		pointer-events: none;
	}

	:host([disabled]) ndd-icon-button {
		opacity: 1;
	}

	:host([full-width]) {
		display: block;
		width: 100%;
	}

	:host([width]) {
		width: var(--_width);
	}


	/* # Container */

	.number-field {
		display: inline-flex;
		flex-direction: row;
		align-items: center;
		height: var(--semantics-controls-md-min-size);
		background-color: var(--semantics-input-fields-background-color);
		border: var(--semantics-input-fields-border-thickness) solid var(--semantics-input-fields-border-color);
		border-radius: var(--semantics-controls-md-corner-radius);
		box-sizing: border-box;
	}

	:host([full-width]) .number-field,
	:host([width]) .number-field {
		width: 100%;
	}

	.number-field:has(.number-field__input:focus-visible) {
		box-shadow: var(--semantics-focus-ring-box-shadow);
		outline: var(--semantics-focus-ring-outline);
	}


	/* # Controls */

	.number-field__decrement-control {
		display: flex;
		align-items: center;
		height: 100%;
		padding-left: calc((var(--semantics-controls-md-min-size) - var(--semantics-controls-sm-min-size)) / 2 - var(--semantics-input-fields-border-thickness));
	}

	.number-field__increment-control {
		display: flex;
		align-items: center;
		height: 100%;
		padding-right: calc((var(--semantics-controls-md-min-size) - var(--semantics-controls-sm-min-size)) / 2 - var(--semantics-input-fields-border-thickness));
	}


	/* # Input */

	.number-field__input {
		appearance: none;
		border: none;
		background: transparent;
		margin: 0;
		padding: 0 var(--primitives-space-6);
		outline: none;
		box-sizing: border-box;
		font: var(--semantics-input-fields-md-text-font);
		color: var(--semantics-content-color);
		text-align: center;
		min-width: var(--semantics-controls-md-min-size);
	}

	.number-field__input[type='number'] {
		-moz-appearance: textfield;
	}

	.number-field__input::-webkit-outer-spin-button,
	.number-field__input::-webkit-inner-spin-button {
		-webkit-appearance: none;
		margin: 0;
	}

	:host([hide-spin-buttons]) .number-field__input {
		min-width: var(--primitives-space-80);
	}

	:host([full-width]) .number-field__input,
	:host([width]) .number-field__input {
		flex: 1;
		min-width: 0;
	}
`;
function numberFieldTemplate(component) {
  const canDecrease = component.value > component.min;
  const canIncrease = component.value < component.max;
  return html`
		<div class="number-field"
			role="group"
			aria-label=${component._t("components.number-field.to-adjust-value-action")}
		>
			${!component.hideSpinButtons ? html`
				<div class="number-field__decrement-control">
					<ndd-icon-button
						variant="neutral-tinted"
						size="sm"
						icon="minus"
						text=${component._t("components.number-field.decrement-action")}
						?disabled=${component.disabled || !canDecrease}
						@click=${component._handleDecrease}
					></ndd-icon-button>
				</div>
			` : nothing}
			<input class="number-field__input"
				type="number"
				aria-label=${component.accessibleLabel || nothing}
				.value=${String(component.value)}
				min=${component.min}
				max=${component.max}
				step=${component.step}
				?disabled=${component.disabled}
				name=${component.name || nothing}
				@input=${component._handleInput}
			>
			${!component.hideSpinButtons ? html`
				<div class="number-field__increment-control">
					<ndd-icon-button
						variant="neutral-tinted"
						size="sm"
						icon="plus"
						text=${component._t("components.number-field.increment-action")}
						?disabled=${component.disabled || !canIncrease}
						@click=${component._handleIncrease}
					></ndd-icon-button>
				</div>
			` : nothing}
		</div>
	`;
}
const nddNumberFieldTranslations = {
  "components.number-field.decrement-action": "Verlaag waarde",
  "components.number-field.increment-action": "Verhoog waarde",
  "components.number-field.to-adjust-value-action": "Waarde aanpassen"
};
var __defProp$N = Object.defineProperty;
var __getOwnPropDesc$R = Object.getOwnPropertyDescriptor;
var __decorateClass$S = (decorators, target, key, kind) => {
  var result = kind > 1 ? void 0 : kind ? __getOwnPropDesc$R(target, key) : target;
  for (var i = decorators.length - 1, decorator; i >= 0; i--)
    if (decorator = decorators[i])
      result = (kind ? decorator(target, key, result) : decorator(result)) || result;
  if (kind && result) __defProp$N(target, key, result);
  return result;
};
let NDDNumberField = class extends LitElement {
  constructor() {
    super(...arguments);
    this.value = 0;
    this.min = -Infinity;
    this.max = Infinity;
    this.step = 1;
    this.disabled = false;
    this.name = "";
    this.fullWidth = false;
    this.width = "";
    this.hideSpinButtons = false;
    this.accessibleLabel = "";
    this.translations = {};
  }
  firstUpdated() {
    if (!this.accessibleLabel) {
      console.warn("<ndd-number-field>: No accessible-label provided. Add an accessible-label attribute so screen readers can announce the input's purpose.");
    }
  }
  updated(changedProperties) {
    if (changedProperties.has("width")) {
      if (this.width) {
        this.style.setProperty("--_width", this.width);
        this.setAttribute("width", this.width);
      } else {
        this.style.removeProperty("--_width");
        this.removeAttribute("width");
      }
    }
  }
  // — i18n —————————————————————————————————————————————————————————————————
  _t(key) {
    return this.translations[key] ?? nddNumberFieldTranslations[key];
  }
  // — Actions ——————————————————————————————————————————————————————————————
  _handleDecrease() {
    if (this.disabled) return;
    this._updateValue(this.value - this.step);
  }
  _handleIncrease() {
    if (this.disabled) return;
    this._updateValue(this.value + this.step);
  }
  _handleInput(e) {
    const input = e.target;
    const newValue = parseFloat(input.value);
    if (!isNaN(newValue)) {
      this._updateValue(newValue);
    }
  }
  _updateValue(newValue) {
    const clampedValue = Math.max(this.min, Math.min(this.max, newValue));
    if (clampedValue !== this.value) {
      this.value = clampedValue;
      this.dispatchEvent(new CustomEvent("input", {
        detail: { value: this.value },
        bubbles: true,
        composed: true
      }));
      this.dispatchEvent(new CustomEvent("change", {
        detail: { value: this.value },
        bubbles: true,
        composed: true
      }));
    }
  }
  render() {
    return numberFieldTemplate(this);
  }
};
NDDNumberField.styles = numberFieldStyles;
__decorateClass$S([
  property({ type: Number })
], NDDNumberField.prototype, "value", 2);
__decorateClass$S([
  property({ type: Number })
], NDDNumberField.prototype, "min", 2);
__decorateClass$S([
  property({ type: Number })
], NDDNumberField.prototype, "max", 2);
__decorateClass$S([
  property({ type: Number })
], NDDNumberField.prototype, "step", 2);
__decorateClass$S([
  property({ type: Boolean, reflect: true })
], NDDNumberField.prototype, "disabled", 2);
__decorateClass$S([
  property({ type: String })
], NDDNumberField.prototype, "name", 2);
__decorateClass$S([
  property({ type: Boolean, reflect: true, attribute: "full-width" })
], NDDNumberField.prototype, "fullWidth", 2);
__decorateClass$S([
  property({ type: String })
], NDDNumberField.prototype, "width", 2);
__decorateClass$S([
  property({ type: Boolean, reflect: true, attribute: "hide-spin-buttons" })
], NDDNumberField.prototype, "hideSpinButtons", 2);
__decorateClass$S([
  property({ type: String, attribute: "accessible-label" })
], NDDNumberField.prototype, "accessibleLabel", 2);
__decorateClass$S([
  property({ type: Object })
], NDDNumberField.prototype, "translations", 2);
NDDNumberField = __decorateClass$S([
  customElement("ndd-number-field")
], NDDNumberField);
const dropdownStyles = css`
	/* # Host */

	:host {
		display: block;
		--_md-icon-size: var(--primitives-space-24);
		--_sm-icon-size: var(--primitives-space-20);
		-webkit-tap-highlight-color: transparent;
	}

	:host([hidden]) {
		display: none;
	}

	:host([disabled]) {
		opacity: var(--primitives-opacity-disabled);
		pointer-events: none;
	}


	/* # Container */

	.dropdown {
		position: relative;
		display: flex;
		flex-direction: row;
		align-items: center;
		box-sizing: border-box;
		width: 100%;
		background-color: var(--semantics-buttons-neutral-tinted-background-color);
		color: var(--semantics-buttons-neutral-tinted-content-color);
	}

	:host([size='md']) .dropdown,
	:host(:not([size])) .dropdown {
		min-height: var(--semantics-controls-md-min-size);
		border-radius: var(--semantics-controls-md-corner-radius);
	}

	:host([size='sm']) .dropdown {
		min-height: var(--semantics-controls-sm-min-size);
		border-radius: var(--semantics-controls-sm-corner-radius);
	}

	.dropdown:focus-within {
		box-shadow: var(--semantics-focus-ring-box-shadow);
		outline: var(--semantics-focus-ring-outline);
	}


	/* # Slotted select */

	::slotted(select) {
		position: absolute;
		inset: 0;
		width: 100%;
		height: 100%;
		opacity: 0;
		appearance: none;
		border: none;
		margin: 0;
		padding: 0;
		background: transparent;
		outline: none;
		box-sizing: border-box;
	}

	:host([size='md']) ::slotted(select),
	:host(:not([size])) ::slotted(select) {
		font: var(--semantics-input-fields-md-text-font);
	}

	:host([size='sm']) ::slotted(select) {
		font: var(--semantics-input-fields-sm-text-font);
	}


	/* # Value */

	.dropdown__value {
		flex: 1;
		min-width: 0;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
		color: inherit;
	}

	:host([size='md']) .dropdown__value,
	:host(:not([size])) .dropdown__value {
		padding: 0 var(--primitives-space-12);
		font: var(--semantics-input-fields-md-text-font);
	}

	:host([size='sm']) .dropdown__value {
		padding: 0 var(--primitives-space-10);
		font: var(--semantics-input-fields-sm-text-font);
	}


	/* # Picker icon */

	.dropdown__picker-icon {
		display: flex;
		align-items: center;
		justify-content: center;
		flex-shrink: 0;
		color: inherit;
	}

	:host([size='md']) .dropdown__picker-icon,
	:host(:not([size])) .dropdown__picker-icon {
		width: var(--_md-icon-size);
		height: var(--_md-icon-size);
		padding-right: calc((var(--semantics-controls-md-min-size) - var(--_md-icon-size)) / 2);
	}

	:host([size='sm']) .dropdown__picker-icon {
		width: var(--_sm-icon-size);
		height: var(--_sm-icon-size);
		padding-right: calc((var(--semantics-controls-sm-min-size) - var(--_sm-icon-size)) / 2);
	}
`;
function dropdownTemplate(component) {
  return html`
		<div class="dropdown">
			<slot @slotchange=${component._onSlotChange}></slot>
			<span class="dropdown__value">${component._displayValue}</span>
			<div class="dropdown__picker-icon">
				<ndd-icon name="chevron-up-down"></ndd-icon>
			</div>
		</div>
	`;
}
var __defProp$M = Object.defineProperty;
var __getOwnPropDesc$Q = Object.getOwnPropertyDescriptor;
var __decorateClass$R = (decorators, target, key, kind) => {
  var result = kind > 1 ? void 0 : kind ? __getOwnPropDesc$Q(target, key) : target;
  for (var i = decorators.length - 1, decorator; i >= 0; i--)
    if (decorator = decorators[i])
      result = (kind ? decorator(target, key, result) : decorator(result)) || result;
  if (kind && result) __defProp$M(target, key, result);
  return result;
};
let NDDDropdown = class extends LitElement {
  constructor() {
    super(...arguments);
    this.size = "md";
    this.disabled = false;
    this._displayValue = "";
    this._select = null;
    this._handleSelectChange = (e) => {
      e.stopPropagation();
      this._syncDisplayValue();
      this.dispatchEvent(new CustomEvent("change", {
        detail: { value: this._select?.value ?? "" },
        bubbles: true,
        composed: true
      }));
    };
  }
  // — Lifecycle ——————————————————————————————————————————————————————————————
  updated(changedProperties) {
    if (changedProperties.has("disabled")) {
      this._syncDisabled();
    }
  }
  // — Slot ——————————————————————————————————————————————————————————————————
  _onSlotChange() {
    const slot = this.shadowRoot?.querySelector("slot");
    const select = slot?.assignedElements({ flatten: true }).find((el) => el.tagName === "SELECT") ?? null;
    if (this._select && this._select !== select) {
      this._select.removeEventListener("change", this._handleSelectChange);
    }
    this._select = select;
    if (!select) {
      this._displayValue = "";
      return;
    }
    if (!select.hasAttribute("aria-label") && !select.hasAttribute("aria-labelledby") && !select.labels?.length) {
      console.warn("<ndd-dropdown>: The slotted <select> has no accessible name. Add an aria-label or aria-labelledby attribute to the <select> element.");
    }
    select.addEventListener("change", this._handleSelectChange);
    this._syncDisabled();
    this._syncDisplayValue();
  }
  // — Internal helpers ——————————————————————————————————————————————————————
  _syncDisabled() {
    if (!this._select) return;
    this._select.disabled = this.disabled;
  }
  _syncDisplayValue() {
    if (!this._select) return;
    this._displayValue = this._select.selectedOptions[0]?.text ?? "";
  }
  render() {
    return dropdownTemplate(this);
  }
};
NDDDropdown.styles = dropdownStyles;
__decorateClass$R([
  property({ type: String, reflect: true })
], NDDDropdown.prototype, "size", 2);
__decorateClass$R([
  property({ type: Boolean, reflect: true })
], NDDDropdown.prototype, "disabled", 2);
__decorateClass$R([
  state()
], NDDDropdown.prototype, "_displayValue", 2);
NDDDropdown = __decorateClass$R([
  customElement("ndd-dropdown")
], NDDDropdown);
const comboBoxStyles = css`


	/* # Host */

	:host {
		display: block;
		-webkit-tap-highlight-color: transparent;
	}

	:host([hidden]) {
		display: none;
	}

	:host([disabled]) {
		opacity: var(--primitives-opacity-disabled);
		pointer-events: none;
	}


	/* # Container */

	.combo-box {
		display: flex;
		flex-direction: row;
		align-items: center;
		box-sizing: border-box;
		width: 100%;
		min-height: var(--semantics-controls-md-min-size);
		background-color: var(--_background-color);
		border: var(--semantics-input-fields-border-thickness) solid var(--semantics-input-fields-border-color);
		border-radius: var(--semantics-controls-md-corner-radius);
		--_background-color: var(--semantics-input-fields-background-color);
	}

	.combo-box:has(input:-webkit-autofill),
	.combo-box:has(input:autofill) {
		--_background-color: var(--semantics-input-fields-is-autofill-background-color);
	}

	.combo-box:has(.combo-box__input:focus-visible) {
		box-shadow: var(--semantics-focus-ring-box-shadow);
		outline: var(--semantics-focus-ring-outline);
	}


	/* # Input */

	.combo-box__input {
		appearance: none;
		border: none;
		background: transparent;
		margin: 0;
		padding: 0 var(--primitives-space-12);
		outline: none;
		box-sizing: border-box;
		flex: 1;
		min-width: 0;
		width: 100%;
		font: var(--semantics-input-fields-md-text-font);
		color: var(--semantics-content-color);
	}

	.combo-box__input::placeholder {
		color: var(--semantics-input-fields-placeholder-color);
	}

	.combo-box__input:-webkit-autofill,
	.combo-box__input:autofill {
		box-shadow: 0 0 0 999px var(--_background-color) inset;
	}


	/* # Picker */

	.combo-box__picker {
		display: flex;
		align-items: center;
		flex-shrink: 0;
		padding-right: calc((var(--semantics-controls-md-min-size) - var(--semantics-controls-sm-min-size)) / 2 - var(--semantics-input-fields-border-thickness));
	}
`;
function comboBoxTemplate(component) {
  return html`
		<div class="combo-box">
			<input class="combo-box__input"
				type="text"
				role="combobox"
				aria-label=${component.accessibleLabel || nothing}
				aria-expanded=${component._isOpen ? "true" : "false"}
				aria-controls=${component._menuId}
				aria-autocomplete="list"
				aria-haspopup="listbox"
				aria-activedescendant=${component._highlightedId || nothing}
				.value=${component._displayValue}
				placeholder=${component.placeholder || nothing}
				?disabled=${component.disabled}
				name=${component.name || nothing}
				@input=${component._handleInput}
				@keydown=${component._handleKeydown}
				@blur=${component._handleBlur}
			>
			<div class="combo-box__picker">
				<ndd-icon-button
					variant="neutral-tinted"
					size="sm"
					icon="chevron-down"
					text=${component._t("components.combo-box.open-picker-action")}
					?disabled=${component.disabled}
					@mousedown=${component._handlePickerMousedown}
					@click=${component._toggleMenu}
				></ndd-icon-button>
			</div>
		</div>
		<slot @slotchange=${component._onSlotChange}></slot>
	`;
}
const nddComboBoxTranslations = {
  "components.combo-box.open-picker-action": "Toon opties"
};
const menuStyles = css`
	/* # Host */

	:host {
		display: block;
		padding: 0;
		border: none;
		background: transparent;
		margin: 0;
		position: absolute;
		overflow: visible;
		--_viewport-margin: 16px;
		--_menu-width: var(--primitives-area-280);
		--_menu-max-height: calc(infinity * 1px);
		--_menu-max-items: 9999;
		--_menu-item-size: var(--semantics-controls-md-min-size);
		--_menu-padding: var(--primitives-space-8);
		@media (pointer: fine) {
			--_menu-item-size: var(--semantics-controls-sm-min-size);
			--_menu-padding: var(--primitives-space-6);
		}
		-webkit-tap-highlight-color: transparent;
	}

	:host(:not(:popover-open)) {
		display: none;
	}


	/* # Menu */

	.menu {
		display: flex;
		flex-direction: column;
		padding: var(--_menu-padding);
		background: var(--semantics-surfaces-background-color);
		border-radius: var(--semantics-overlays-corner-radius);
		box-shadow: var(--components-menu-box-shadow);
		box-sizing: border-box;
		width: var(--_menu-width);
		max-height: min(
			var(--_menu-max-height),
			calc(var(--_menu-max-items) * var(--_menu-item-size) + var(--_menu-padding) * 2)
		);
		overflow-y: auto;
	}

	.menu:focus-visible {
		outline: none;
	}

	.menu.is-keyboard-focus:focus {
		box-shadow: var(--semantics-focus-ring-box-shadow), var(--components-menu-box-shadow);
		outline: var(--semantics-focus-ring-outline);
	}


	/* # Empty text */

	.menu__empty-text {
		padding: var(--primitives-space-8);
		color: var(--semantics-content-secondary-color);
		font: var(--primitives-font-body-md-regular-tight);
		text-align: center;
	}
`;
const menuItemStyles = css`
	/* # Host */

	:host {
		display: block;
		font-family: var(--ndd-font-family-body);
		-webkit-tap-highlight-color: transparent;
	}

	:host([hidden]) {
		display: none;
	}


	/* # Item */

	.menu__item {
		display: flex;
		flex-direction: row;
		align-items: center;
		width: 100%;
		min-height: var(--_menu-item-size);
		padding: var(--primitives-space-8);
		box-sizing: border-box;
		border: none;
		border-radius: var(--semantics-controls-md-corner-radius);
		background: transparent;
		text-align: start;
		appearance: none;
		color: var(--semantics-content-color);
		font: var(--primitives-font-body-md-regular-tight);
		@media (pointer: fine) {
			padding: var(--primitives-space-4) var(--primitives-space-8);
			border-radius: var(--semantics-controls-sm-corner-radius);
		}
	}


	/* # Highlighted */

	:host([highlighted]) .menu__item {
		background-color: var(--components-menu-item-is-highlighted-background-color);
		color: var(--components-menu-item-is-highlighted-content-color);
		--semantics-content-secondary-color: var(--components-menu-item-is-highlighted-content-color);
	}


	/* # Focus */

	.menu__item:focus-visible {
		position: relative;
		z-index: 1;
		box-shadow: var(--semantics-focus-ring-box-shadow);
		outline: var(--semantics-focus-ring-outline);
	}


	/* # Disabled */

	:host([disabled]) .menu__item {
		opacity: var(--primitives-opacity-disabled);
		pointer-events: none;
	}


	/* # Reduced motion */

	@media (prefers-reduced-motion: reduce) {
		.menu__item {
			transition: none;
		}
	}


	/* # Forced colors */

	@media (forced-colors: active) {
		:host([highlighted]) .menu__item {
			background-color: Highlight;
			color: HighlightText;
		}

		.menu__item:focus-visible {
			outline: 2px solid CanvasText;
		}
	}
`;
const menuDividerStyles = css`
	/* # Host */

	:host {
		display: block;
		padding: var(--primitives-space-4) 0;
	}

	:host([hidden]) {
		display: none;
	}


	/* # Divider */

	.menu__divider {
		height: var(--semantics-dividers-thickness);
		background-color: var(--semantics-dividers-color);
	}
`;
const menuRoleMap = {
  menu: "menu",
  listbox: "listbox"
};
const itemRoleMap = {
  button: { menu: "menuitem", listbox: "option" },
  checkbox: { menu: "menuitemcheckbox", listbox: "option" },
  radio: { menu: "menuitemradio", listbox: "option" }
};
function menuTemplate(isEmpty, variant) {
  return html`
		<div class="menu"
			role=${menuRoleMap[variant]}
			tabindex="-1"
		>
			<slot></slot>
			${isEmpty ? html`
				<div class="menu__empty-text">${this._resolvedEmptyText}</div>
			` : nothing}
		</div>
	`;
}
function menuItemTemplate(variant = "menu") {
  const hasCheckState = this.type !== "button" && variant === "menu";
  const role = itemRoleMap[this.type][variant];
  return html`
		<button class="menu__item"
			type="button"
			role=${role}
			?disabled=${this.disabled}
			aria-checked=${hasCheckState ? String(this.selected) : nothing}
			aria-selected=${variant === "listbox" ? String(this.selected) : nothing}
			@click=${this._handleClick}
		>
			${hasCheckState ? html`
				<ndd-icon-cell class="menu__item-check"
					size="24"
					color="inherit"
					horizontal-alignment="center"
				>
					${this.selected ? html`
						<ndd-icon name="check-mark"></ndd-icon>
					` : nothing}
				</ndd-icon-cell>
				<ndd-spacer-cell size="8"></ndd-spacer-cell>
			` : nothing}
			<ndd-text-cell class="menu__item-text" color="inherit" text=${this._displayText || this.text}></ndd-text-cell>
			${this.details ? html`
				<ndd-spacer-cell size="8"></ndd-spacer-cell>
				<ndd-text-cell class="menu__item-details"
					width="fit-content"
					horizontal-alignment="right"
					color="secondary"
					text=${this.details}
				></ndd-text-cell>
			` : nothing}
		</button>
	`;
}
function menuDividerTemplate() {
  return html`<div class="menu__divider" role="separator"></div>`;
}
const nddMenuTranslations = {
  "components.menu.empty-text": "Geen opties beschikbaar"
};
const styles$c = css`
	/* # host */

	:host {
		display: flex;
		flex-direction: column;
		align-items: center;
		color: var(--semantics-content-color);
	}

	:host([hidden]) {
		display: none;
	}

	/* # vertical-alignment */

	/* ## vertical-alignment: center (default) */

	:host([vertical-alignment="center"]),
	:host(:not([vertical-alignment])) {
		justify-content: center;
	}

	/* ## vertical-alignment: top */

	:host([vertical-alignment="top"]) {
		justify-content: flex-start;
	}

	/* # size */

	::slotted(*) {
		display: block;
		flex-shrink: 0;
	}

	/* ## size: 16 */

	:host([size="16"]) {
		width: var(--primitives-space-16);
	}

	:host([size="16"]) ::slotted(*) {
		width: var(--primitives-space-16);
		height: var(--primitives-space-16);
	}

	/* ## size: 20 */

	:host([size="20"]) {
		width: var(--primitives-space-20);
	}

	:host([size="20"]) ::slotted(*) {
		width: var(--primitives-space-20);
		height: var(--primitives-space-20);
	}

	/* ## size: 24 (default) */

	:host([size="24"]) {
		width: var(--primitives-space-24);
	}

	:host([size="24"]) ::slotted(*),
	:host(:not([size])) ::slotted(*) {
		width: var(--primitives-space-24);
		height: var(--primitives-space-24);
	}

	/* ## size: 32 */

	:host([size="32"]) {
		width: var(--primitives-space-32);
	}

	:host([size="32"]) ::slotted(*) {
		width: var(--primitives-space-32);
		height: var(--primitives-space-32);
	}

	/* # selected */

	:host([selected]) {
		color: var(--semantics-controls-is-selected-contrast-color);
	}

	/* # color: inherit */

	:host([color="inherit"]) {
		color: inherit;
	}
`;
function template$b() {
  return html`
		<slot></slot>
	`;
}
var __defProp$L = Object.defineProperty;
var __getOwnPropDesc$P = Object.getOwnPropertyDescriptor;
var __decorateClass$Q = (decorators, target, key, kind) => {
  var result = kind > 1 ? void 0 : kind ? __getOwnPropDesc$P(target, key) : target;
  for (var i = decorators.length - 1, decorator; i >= 0; i--)
    if (decorator = decorators[i])
      result = (kind ? decorator(target, key, result) : decorator(result)) || result;
  if (kind && result) __defProp$L(target, key, result);
  return result;
};
let NDDIconCell = class extends LitElement {
  constructor() {
    super(...arguments);
    this.verticalAlignment = "center";
    this.size = "24";
    this.color = "default";
    this.selected = false;
  }
  render() {
    return template$b.call(this);
  }
};
NDDIconCell.styles = styles$c;
__decorateClass$Q([
  property({ type: String, reflect: true, attribute: "vertical-alignment" })
], NDDIconCell.prototype, "verticalAlignment", 2);
__decorateClass$Q([
  property({ type: String, reflect: true })
], NDDIconCell.prototype, "size", 2);
__decorateClass$Q([
  property({ type: String, reflect: true })
], NDDIconCell.prototype, "color", 2);
__decorateClass$Q([
  property({ type: Boolean, reflect: true })
], NDDIconCell.prototype, "selected", 2);
NDDIconCell = __decorateClass$Q([
  customElement("ndd-icon-cell")
], NDDIconCell);
const styles$b = css`
	/* # host */

	:host {
		display: block;
		flex-shrink: 0;
		flex-grow: 0;
	}

	:host([hidden]) {
		display: none;
	}

	/* # size */

	:host([size="2"])  { width: var(--primitives-space-2); }
	:host([size="4"])  { width: var(--primitives-space-4); }
	:host([size="6"])  { width: var(--primitives-space-6); }
	:host([size="8"])  { width: var(--primitives-space-8); }
	:host([size="10"]) { width: var(--primitives-space-10); }
	:host([size="12"]) { width: var(--primitives-space-12); }

	:host([size="16"]),
	:host(:not([size])) { width: var(--primitives-space-16); }

	:host([size="20"]) { width: var(--primitives-space-20); }
	:host([size="24"]) { width: var(--primitives-space-24); }
	:host([size="28"]) { width: var(--primitives-space-28); }
	:host([size="32"]) { width: var(--primitives-space-32); }
	:host([size="40"]) { width: var(--primitives-space-40); }
	:host([size="44"]) { width: var(--primitives-space-44); }
	:host([size="48"]) { width: var(--primitives-space-48); }
	:host([size="56"]) { width: var(--primitives-space-56); }
	:host([size="64"]) { width: var(--primitives-space-64); }
	:host([size="80"]) { width: var(--primitives-space-80); }
	:host([size="96"]) { width: var(--primitives-space-96); }

	:host([size="flexible"]) {
		flex-grow: 1;
		width: auto;
	}
`;
var __defProp$K = Object.defineProperty;
var __getOwnPropDesc$O = Object.getOwnPropertyDescriptor;
var __decorateClass$P = (decorators, target, key, kind) => {
  var result = kind > 1 ? void 0 : kind ? __getOwnPropDesc$O(target, key) : target;
  for (var i = decorators.length - 1, decorator; i >= 0; i--)
    if (decorator = decorators[i])
      result = (kind ? decorator(target, key, result) : decorator(result)) || result;
  if (kind && result) __defProp$K(target, key, result);
  return result;
};
let NDDSpacerCell = class extends LitElement {
  constructor() {
    super(...arguments);
    this.size = "16";
  }
  render() {
    return null;
  }
};
NDDSpacerCell.styles = styles$b;
__decorateClass$P([
  property({ type: String, reflect: true })
], NDDSpacerCell.prototype, "size", 2);
NDDSpacerCell = __decorateClass$P([
  customElement("ndd-spacer-cell")
], NDDSpacerCell);
const styles$a = css`
	/* # Host */

	:host {
		display: flex;
		flex-direction: column;
		justify-content: center;
		--_width: auto;
		--_min-width: 0;
		--_max-width: none;
		--_min-height: 0;
		width: var(--_width);
		min-width: var(--_min-width);
		max-width: var(--_max-width);
		min-height: var(--_min-height);
	}

	:host([hidden]) {
		display: none;
	}


	/* # Width */

	:host([width='stretch']),
	:host(:not([width])) {
		flex-grow: 1;
		min-width: 0;
	}

	:host([width='fit-content']) {
		flex-grow: 0;
		flex-shrink: 0;
		flex-basis: auto;
		width: fit-content;
	}

	:host([width]:not([width='stretch']):not([width='fit-content'])) {
		flex-shrink: 0;
	}


	/* # Vertical alignment
	 *
	 * 'center' (default): the cell stretches to fill the full row height, then
	 * centers its content within that space. When min-height is set, the cell is
	 * at least that tall and the content sits centered inside it. For strict top
	 * alignment without a minimum height, use vertical-alignment="top".
	 */

	:host([vertical-alignment='center']),
	:host(:not([vertical-alignment])) {
		align-self: stretch;
	}

	:host([vertical-alignment='top']) {
		align-self: flex-start;
	}

	:host([vertical-alignment='bottom']) {
		align-self: flex-end;
	}


	/* # Horizontal alignment */

	:host([horizontal-alignment='left']),
	:host(:not([horizontal-alignment])) {
		align-items: flex-start;
	}

	:host([horizontal-alignment='right']) {
		align-items: flex-end;
	}


	/* # Overline */

	.text-cell__overline {
		margin: 0;
		align-self: stretch;
		min-width: 0;
		color: var(--semantics-content-secondary-color);
	}

	:host([size='md']) .text-cell__overline,
	:host(:not([size])) .text-cell__overline {
		font: var(--primitives-font-body-xs-regular-tight);
	}

	:host([size='sm']) .text-cell__overline {
		font: var(--primitives-font-body-xxs-regular-tight);
	}

	:host([horizontal-alignment='right']) .text-cell__overline {
		text-align: right;
	}


	/* # Text */

	.text-cell__text {
		margin: 0;
		align-self: stretch;
		min-width: 0;
	}

	:host([size='md']) .text-cell__text,
	:host(:not([size])) .text-cell__text {
		font: var(--primitives-font-body-md-regular-tight);
	}

	:host([size='sm']) .text-cell__text {
		font: var(--primitives-font-body-sm-regular-tight);
	}

	:host([horizontal-alignment='right']) .text-cell__text {
		text-align: right;
	}


	/* # Color */

	/* ## Color: default */

	:host([color='default']) .text-cell__text,
	:host(:not([color])) .text-cell__text {
		color: var(--semantics-content-color);
	}

	/* ## Color: secondary */

	:host([color='secondary']) .text-cell__text {
		color: var(--semantics-content-secondary-color);
	}

	/* ## Color: inherit */

	:host([color='inherit']) .text-cell__text,
	:host([color='inherit']) .text-cell__overline,
	:host([color='inherit']) .text-cell__supporting-text {
		color: inherit;
	}


	/* # Supporting text */

	.text-cell__supporting-text {
		margin: 0;
		align-self: stretch;
		min-width: 0;
		color: var(--semantics-content-secondary-color);
	}

	:host([size='md']) .text-cell__supporting-text,
	:host(:not([size])) .text-cell__supporting-text {
		font: var(--primitives-font-body-xs-regular-tight);
	}

	:host([size='sm']) .text-cell__supporting-text {
		font: var(--primitives-font-body-xxs-regular-tight);
	}

	:host([horizontal-alignment='right']) .text-cell__supporting-text {
		text-align: right;
	}


	/* # Selected */

	:host([selected]) .text-cell__text,
	:host([selected]) .text-cell__overline,
	:host([selected]) .text-cell__supporting-text {
		color: var(--semantics-controls-is-selected-contrast-color);
	}


	/* # Forced colors */

	@media (forced-colors: active) {
		.text-cell__text {
			forced-color-adjust: none;
		}
	}
`;
function renderText(text) {
  if (!text.includes("**")) return text;
  const parts = text.split(/\*\*(.+?)\*\*/g);
  return html`${parts.map((part, i) => i % 2 === 1 ? html`<b>${part}</b>` : part)}`;
}
function template$a() {
  return html`
		${this.overline ? html`<p class="text-cell__overline">${this.overline}</p>` : nothing}
		${this.text ? html`<p class="text-cell__text">${renderText(this.text)}</p>` : nothing}
		${this.supportingText ? html`<p class="text-cell__supporting-text">${this.supportingText}</p>` : nothing}
	`;
}
var __defProp$J = Object.defineProperty;
var __getOwnPropDesc$N = Object.getOwnPropertyDescriptor;
var __decorateClass$O = (decorators, target, key, kind) => {
  var result = kind > 1 ? void 0 : kind ? __getOwnPropDesc$N(target, key) : target;
  for (var i = decorators.length - 1, decorator; i >= 0; i--)
    if (decorator = decorators[i])
      result = (kind ? decorator(target, key, result) : decorator(result)) || result;
  if (kind && result) __defProp$J(target, key, result);
  return result;
};
const widthConverter$3 = {
  fromAttribute(value) {
    if (value === null) return "stretch";
    const num = Number(value);
    return Number.isFinite(num) ? num : value;
  },
  toAttribute(value) {
    return String(value);
  }
};
let NDDTextCell = class extends LitElement {
  constructor() {
    super(...arguments);
    this.size = "md";
    this.color = "default";
    this.width = "stretch";
    this.horizontalAlignment = "left";
    this.verticalAlignment = "center";
    this.selected = false;
    this.text = "";
    this.overline = "";
    this.supportingText = "";
  }
  updated(changed) {
    if (changed.has("width") || changed.has("minWidth") || changed.has("maxWidth") || changed.has("minHeight")) {
      this._applyDimensionStyles();
    }
  }
  /* eslint-disable eqeqeq -- != null is intentional: guards both null and undefined */
  _applyDimensionStyles() {
    if (typeof this.width === "number") {
      this.style.setProperty("--_width", `${this.width}px`);
    } else {
      this.style.removeProperty("--_width");
    }
    if (this.minWidth != null) {
      this.style.setProperty("--_min-width", `${this.minWidth}px`);
    } else {
      this.style.removeProperty("--_min-width");
    }
    if (this.maxWidth != null) {
      this.style.setProperty("--_max-width", `${this.maxWidth}px`);
    } else {
      this.style.removeProperty("--_max-width");
    }
    if (this.minHeight != null) {
      this.style.setProperty("--_min-height", `${this.minHeight}px`);
    } else {
      this.style.removeProperty("--_min-height");
    }
  }
  /* eslint-enable eqeqeq */
  render() {
    return template$a.call(this);
  }
};
NDDTextCell.styles = [styles$a];
__decorateClass$O([
  property({ type: String, reflect: true })
], NDDTextCell.prototype, "size", 2);
__decorateClass$O([
  property({ type: String, reflect: true })
], NDDTextCell.prototype, "color", 2);
__decorateClass$O([
  property({ reflect: true, converter: widthConverter$3 })
], NDDTextCell.prototype, "width", 2);
__decorateClass$O([
  property({ type: Number, reflect: true, attribute: "min-width" })
], NDDTextCell.prototype, "minWidth", 2);
__decorateClass$O([
  property({ type: Number, reflect: true, attribute: "max-width" })
], NDDTextCell.prototype, "maxWidth", 2);
__decorateClass$O([
  property({ type: Number, reflect: true, attribute: "min-height" })
], NDDTextCell.prototype, "minHeight", 2);
__decorateClass$O([
  property({ type: String, reflect: true, attribute: "horizontal-alignment" })
], NDDTextCell.prototype, "horizontalAlignment", 2);
__decorateClass$O([
  property({ type: String, reflect: true, attribute: "vertical-alignment" })
], NDDTextCell.prototype, "verticalAlignment", 2);
__decorateClass$O([
  property({ type: Boolean, reflect: true })
], NDDTextCell.prototype, "selected", 2);
__decorateClass$O([
  property({ type: String })
], NDDTextCell.prototype, "text", 2);
__decorateClass$O([
  property({ type: String })
], NDDTextCell.prototype, "overline", 2);
__decorateClass$O([
  property({ type: String, attribute: "supporting-text" })
], NDDTextCell.prototype, "supportingText", 2);
NDDTextCell = __decorateClass$O([
  customElement("ndd-text-cell")
], NDDTextCell);
const nddTextCell = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  get NDDTextCell() {
    return NDDTextCell;
  }
}, Symbol.toStringTag, { value: "Module" }));
let keyboardMode = false;
let initialized = false;
let controller = null;
function init() {
  if (initialized) return;
  initialized = true;
  controller = new AbortController();
  const { signal } = controller;
  document.addEventListener("keydown", (e) => {
    if (["Tab", "ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight", "Enter", " ", "Escape"].includes(e.key)) {
      keyboardMode = true;
    }
  }, { signal });
  document.addEventListener("mousedown", () => {
    keyboardMode = false;
  }, { signal });
  document.addEventListener("touchstart", () => {
    keyboardMode = false;
  }, { passive: true, signal });
}
function isKeyboardMode() {
  init();
  return keyboardMode;
}
var __defProp$I = Object.defineProperty;
var __decorateClass$N = (decorators, target, key, kind) => {
  var result = void 0;
  for (var i = decorators.length - 1, decorator; i >= 0; i--)
    if (decorator = decorators[i])
      result = decorator(target, key, result) || result;
  if (result) __defProp$I(target, key, result);
  return result;
};
const _NDDMenuDivider = class _NDDMenuDivider extends LitElement {
  render() {
    return menuDividerTemplate();
  }
};
_NDDMenuDivider.styles = menuDividerStyles;
let NDDMenuDivider = _NDDMenuDivider;
if (!customElements.get("ndd-menu-divider")) {
  customElements.define("ndd-menu-divider", NDDMenuDivider);
}
const _NDDMenuItem = (_a = class extends LitElement {
  constructor() {
    super(...arguments);
    this.text = "";
    this.value = "";
    this.aliases = "";
    this.details = "";
    this.type = "button";
    this.selected = false;
    this.disabled = false;
    this._displayText = "";
    this.menuVariant = "menu";
  }
  /** Set by ndd-menu during filtering to apply bold markers to matching text. */
  setDisplayText(text) {
    this._displayText = text;
  }
  connectedCallback() {
    super.connectedCallback();
    if (!this.id) {
      this.id = `ndd-menu-item-${_a._counter++}`;
    }
    this.addEventListener("focusin", () => {
      this.setAttribute("data-focused", "");
      this.dispatchEvent(new CustomEvent("menu-item-focused", {
        bubbles: true,
        composed: true
      }));
    });
    this.addEventListener("focusout", () => this.removeAttribute("data-focused"));
  }
  focus(options) {
    const focusable = this.shadowRoot?.querySelector("button, a");
    focusable?.focus(options);
  }
  _handleClick() {
    if (this.disabled) return;
    this.dispatchEvent(new CustomEvent("select", {
      bubbles: true,
      composed: true
    }));
    this.closest("ndd-menu")?.hidePopover?.();
  }
  /** Programmatically select this item. */
  select() {
    this._handleClick();
  }
  render() {
    return menuItemTemplate.call(this, this.menuVariant);
  }
}, _a.styles = menuItemStyles, _a._counter = 0, _a);
__decorateClass$N([
  property({ type: String, reflect: true })
], _NDDMenuItem.prototype, "text");
__decorateClass$N([
  property({ type: String, reflect: true })
], _NDDMenuItem.prototype, "value");
__decorateClass$N([
  property({ type: String, reflect: true })
], _NDDMenuItem.prototype, "aliases");
__decorateClass$N([
  property({ type: String, reflect: true })
], _NDDMenuItem.prototype, "details");
__decorateClass$N([
  property({ type: String, reflect: true })
], _NDDMenuItem.prototype, "type");
__decorateClass$N([
  property({ type: Boolean, reflect: true })
], _NDDMenuItem.prototype, "selected");
__decorateClass$N([
  property({ type: Boolean, reflect: true })
], _NDDMenuItem.prototype, "disabled");
__decorateClass$N([
  state()
], _NDDMenuItem.prototype, "_displayText");
__decorateClass$N([
  state()
], _NDDMenuItem.prototype, "menuVariant");
let NDDMenuItem = _NDDMenuItem;
if (!customElements.get("ndd-menu-item")) {
  customElements.define("ndd-menu-item", NDDMenuItem);
}
const defaultFilterFn = (query2, item) => {
  const q = query2.toLowerCase();
  const textMatch = item.text.toLowerCase().includes(q);
  const valueMatch = item.value !== "" && item.value.toLowerCase().includes(q);
  const aliasesMatch = item.aliases !== "" && item.aliases.split(" ").some((s) => s.toLowerCase().includes(q));
  return textMatch || valueMatch || aliasesMatch;
};
const _NDDMenu = class _NDDMenu extends LitElement {
  constructor() {
    super(...arguments);
    this.anchor = "";
    this.anchorElement = null;
    this.placement = "bottom-start";
    this.variant = "menu";
    this.emptyText = "";
    this.width = "";
    this.maxItems = 0;
    this.translations = {};
    this.filterFn = defaultFilterFn;
    this._isEmpty = false;
    this._isOpen = false;
    this._closedAt = 0;
    this._handleDocumentClick = (event) => {
      if (this.anchorElement) return;
      const anchorEl = this._getAnchorEl();
      if (!anchorEl) return;
      const path = event.composedPath();
      if (!path.includes(anchorEl)) return;
      if (this._isOpen) {
        this.hidePopover();
      } else if (Date.now() - this._closedAt > POPOVER_REOPEN_GUARD_MS) {
        this.showPopover();
      }
    };
    this._handleMenuItemMouseenter = (event) => {
      const item = event.target.closest("ndd-menu-item");
      if (!item || item.disabled || item.hasAttribute("hidden")) return;
      this._setHighlight(item);
    };
    this._handleMouseleave = () => {
      if (this.variant !== "listbox") this._clearHighlight();
    };
    this._handleMenuItemFocused = (event) => {
      const item = event.target.closest("ndd-menu-item");
      if (!item || item.disabled || item.hasAttribute("hidden")) return;
      this._setHighlight(item);
    };
    this._handleKeydown = (event) => {
      const items = this._getVisibleItems();
      if (items.length === 0) return;
      const index = this._getFocusedIndex(items);
      switch (event.key) {
        case "ArrowDown": {
          event.preventDefault();
          const next = index === -1 ? 0 : index < items.length - 1 ? index + 1 : 0;
          items[next].focus();
          break;
        }
        case "ArrowUp": {
          event.preventDefault();
          const prev = index === -1 ? items.length - 1 : index > 0 ? index - 1 : items.length - 1;
          items[prev].focus();
          break;
        }
        case "Home": {
          event.preventDefault();
          items[0].focus();
          break;
        }
        case "End": {
          event.preventDefault();
          items[items.length - 1].focus();
          break;
        }
        case "Escape": {
          event.preventDefault();
          this.hidePopover();
          const anchorEl = this._getAnchorEl();
          anchorEl?.focus();
          break;
        }
      }
    };
    this._handleToggle = async (event) => {
      const toggleEvent = event;
      this._isOpen = toggleEvent.newState === "open";
      if (toggleEvent.newState !== "open") {
        this._closedAt = Date.now();
        return;
      }
      this._updateDividerVisibility();
      this._clearHighlight();
      this._updateEmptyState();
      Array.from(this.querySelectorAll("ndd-menu-item")).forEach((item) => {
        item.menuVariant = this.variant;
      });
      await this.reposition();
      await this.updateComplete;
      if (this.variant !== "listbox") {
        const keyboard = isKeyboardMode();
        const items = this._getVisibleItems();
        if (keyboard && items.length > 0) {
          this._setHighlight(items[0]);
          items[0].focus();
        } else {
          const menu = this.shadowRoot?.querySelector(".menu");
          menu?.classList.toggle("is-keyboard-focus", keyboard);
          menu?.focus();
        }
      }
    };
  }
  // — i18n ——————————————————————————————————————————————————————————————————
  _t(key) {
    return this.translations[key] ?? nddMenuTranslations[key];
  }
  /** Resolved empty text: emptyText attribute takes precedence, then i18n fallback. */
  get _resolvedEmptyText() {
    return this.emptyText || this._t("components.menu.empty-text");
  }
  // — Lifecycle ——————————————————————————————————————————————————————————————
  updated(changedProperties) {
    if (changedProperties.has("width")) {
      if (this.width) {
        this.style.setProperty("--_menu-width", this.width);
      } else {
        this.style.removeProperty("--_menu-width");
      }
    }
    if (changedProperties.has("maxItems")) {
      if (this.maxItems > 0) {
        this.style.setProperty("--_menu-max-items", String(this.maxItems));
      } else {
        this.style.removeProperty("--_menu-max-items");
      }
    }
    if (changedProperties.has("variant")) {
      Array.from(this.querySelectorAll("ndd-menu-item")).forEach((item) => {
        item.menuVariant = this.variant;
      });
    }
  }
  // — Anchor ————————————————————————————————————————————————————————————————
  _getAnchorEl() {
    if (this.anchorElement) return this.anchorElement;
    if (this.anchor) return document.getElementById(this.anchor);
    return null;
  }
  // — Lifecycle callbacks ————————————————————————————————————————————————————
  connectedCallback() {
    super.connectedCallback();
    if (!this.hasAttribute("popover")) {
      this.setAttribute("popover", "");
    }
    this.addEventListener("toggle", this._handleToggle);
    this.addEventListener("keydown", this._handleKeydown);
    this.addEventListener("mouseenter", this._handleMenuItemMouseenter, true);
    this.addEventListener("mouseleave", this._handleMouseleave);
    this.addEventListener("menu-item-focused", this._handleMenuItemFocused);
    document.addEventListener("click", this._handleDocumentClick);
  }
  disconnectedCallback() {
    super.disconnectedCallback();
    this.removeEventListener("toggle", this._handleToggle);
    this.removeEventListener("keydown", this._handleKeydown);
    this.removeEventListener("mouseenter", this._handleMenuItemMouseenter, true);
    this.removeEventListener("mouseleave", this._handleMouseleave);
    this.removeEventListener("menu-item-focused", this._handleMenuItemFocused);
    document.removeEventListener("click", this._handleDocumentClick);
  }
  // — Internal helpers ——————————————————————————————————————————————————————
  _getVisibleItems() {
    return Array.from(
      this.querySelectorAll("ndd-menu-item:not([hidden]):not([disabled])")
    );
  }
  _getFocusedIndex(items) {
    return items.findIndex((item) => item.hasAttribute("data-focused"));
  }
  _clearHighlight() {
    Array.from(this.querySelectorAll("ndd-menu-item")).forEach((item) => {
      item.removeAttribute("highlighted");
    });
  }
  _setHighlight(target) {
    this._clearHighlight();
    const resolved = target ?? this._getVisibleItems()[0] ?? null;
    resolved?.setAttribute("highlighted", "");
  }
  _updateEmptyState() {
    this._isEmpty = this._getVisibleItems().length === 0;
  }
  _updateDividerVisibility() {
    const children = Array.from(this.children);
    children.forEach((el) => {
      if (el.tagName.toLowerCase() === "ndd-menu-divider") {
        el.removeAttribute("hidden");
      }
    });
    const visible = children.filter((el) => !el.hasAttribute("hidden"));
    visible.forEach((el, index) => {
      if (el.tagName.toLowerCase() !== "ndd-menu-divider") return;
      const isFirst = index === 0;
      const isLast = index === visible.length - 1;
      const prevIsDivider = index > 0 && visible[index - 1].tagName.toLowerCase() === "ndd-menu-divider";
      if (isFirst || isLast || prevIsDivider) {
        el.setAttribute("hidden", "");
      }
    });
  }
  // — Public API ————————————————————————————————————————————————————————————
  /**
   * Filter items based on a query string.
   *
   * Matching items are kept visible. Non-matching items are hidden.
   *
   * For visible items, the non-typed portion of the text is marked bold using
   * **markdown** syntax, which the template renders as <b> tags. This follows
   * the principle that the typed characters are already known to the user —
   * emphasising the predictive completion helps users scan the differences
   * between suggestions and identify the new information at a glance.
   *
   * When the query is empty, all items are shown and bold markers are cleared.
   */
  filter(query2) {
    const allItems = Array.from(this.querySelectorAll("ndd-menu-item"));
    allItems.forEach((item) => {
      const matches = !query2 || this.filterFn(query2, item);
      item.toggleAttribute("hidden", !matches);
      if (!query2) {
        item.setDisplayText("");
      } else if (matches) {
        const q = query2.toLowerCase();
        let remaining = item.text;
        let remainingLower = item.text.toLowerCase();
        const parts = [];
        while (remaining.length > 0) {
          const idx = remainingLower.indexOf(q);
          if (idx === -1) {
            parts.push(`**${remaining}**`);
            break;
          }
          if (idx > 0) parts.push(`**${remaining.slice(0, idx)}**`);
          parts.push(remaining.slice(idx, idx + query2.length));
          remaining = remaining.slice(idx + query2.length);
          remainingLower = remaining.toLowerCase();
        }
        item.setDisplayText(parts.join(""));
      }
    });
    this._setHighlight(null);
    this._updateEmptyState();
    this._updateDividerVisibility();
    if (this._isOpen) this.reposition();
  }
  /**
   * Move both focus and highlight to the next, previous, or first visible item.
   */
  focusItem(direction) {
    const items = this._getVisibleItems();
    if (items.length === 0) return;
    let targetIndex;
    if (direction === "first") {
      targetIndex = 0;
    } else {
      const current = items.findIndex(
        (item) => item.hasAttribute("highlighted") || item.hasAttribute("data-focused")
      );
      if (direction === "next") {
        targetIndex = current === -1 ? 0 : current < items.length - 1 ? current + 1 : 0;
      } else {
        targetIndex = current === -1 ? items.length - 1 : current > 0 ? current - 1 : items.length - 1;
      }
    }
    items.forEach((item) => item.removeAttribute("highlighted"));
    items[targetIndex].setAttribute("highlighted", "");
    items[targetIndex].focus();
  }
  /**
   * Move the highlight to the next or previous visible item without moving focus.
   * Useful when keyboard navigation should keep focus on the input.
   */
  moveHighlight(direction) {
    const items = this._getVisibleItems();
    if (items.length === 0) return;
    const current = items.findIndex((item) => item.hasAttribute("highlighted"));
    let next;
    if (direction === "next") {
      next = current === -1 ? 0 : current < items.length - 1 ? current + 1 : 0;
    } else {
      next = current === -1 ? items.length - 1 : current > 0 ? current - 1 : items.length - 1;
    }
    items.forEach((item) => item.removeAttribute("highlighted"));
    items[next].setAttribute("highlighted", "");
  }
  /** Returns the currently highlighted item, or null if none. */
  getHighlighted() {
    return this.querySelector("ndd-menu-item[highlighted]");
  }
  /** Returns the ID of the currently highlighted item, or empty string if none. */
  getHighlightedId() {
    return this.getHighlighted()?.id ?? "";
  }
  /** Recalculate position and size relative to the anchor element. */
  async reposition() {
    const anchorEl = this._getAnchorEl();
    if (!anchorEl || !this._isOpen) return;
    const viewportMargin = parseInt(
      getComputedStyle(this).getPropertyValue("--_viewport-margin")
    );
    const { x, y } = await computePosition(anchorEl, this, {
      placement: this.placement,
      middleware: [
        offset(0),
        flip({ padding: viewportMargin }),
        shift({ padding: viewportMargin }),
        size({
          padding: viewportMargin,
          apply: ({ availableHeight }) => {
            this.style.setProperty("--_menu-max-height", `${availableHeight}px`);
          }
        })
      ]
    });
    Object.assign(this.style, {
      left: `${x}px`,
      top: `${y}px`
    });
  }
  render() {
    return menuTemplate.call(this, this._isEmpty, this.variant);
  }
};
_NDDMenu.styles = menuStyles;
let NDDMenu = _NDDMenu;
__decorateClass$N([
  property({ type: String, reflect: true })
], NDDMenu.prototype, "anchor");
__decorateClass$N([
  property({ attribute: false })
], NDDMenu.prototype, "anchorElement");
__decorateClass$N([
  property({ type: String, reflect: true })
], NDDMenu.prototype, "placement");
__decorateClass$N([
  property({ type: String, reflect: true })
], NDDMenu.prototype, "variant");
__decorateClass$N([
  property({ type: String, attribute: "empty-text" })
], NDDMenu.prototype, "emptyText");
__decorateClass$N([
  property({ type: String, reflect: true })
], NDDMenu.prototype, "width");
__decorateClass$N([
  property({ type: Number, attribute: "max-items" })
], NDDMenu.prototype, "maxItems");
__decorateClass$N([
  property({ type: Object })
], NDDMenu.prototype, "translations");
__decorateClass$N([
  property({ attribute: false })
], NDDMenu.prototype, "filterFn");
__decorateClass$N([
  state()
], NDDMenu.prototype, "_isEmpty");
if (!customElements.get("ndd-menu")) {
  customElements.define("ndd-menu", NDDMenu);
}
var __defProp$H = Object.defineProperty;
var __getOwnPropDesc$M = Object.getOwnPropertyDescriptor;
var __decorateClass$M = (decorators, target, key, kind) => {
  var result = kind > 1 ? void 0 : kind ? __getOwnPropDesc$M(target, key) : target;
  for (var i = decorators.length - 1, decorator; i >= 0; i--)
    if (decorator = decorators[i])
      result = (kind ? decorator(target, key, result) : decorator(result)) || result;
  if (kind && result) __defProp$H(target, key, result);
  return result;
};
let NDDComboBox = class extends LitElement {
  constructor() {
    super(...arguments);
    this.value = "";
    this.placeholder = "";
    this.disabled = false;
    this.name = "";
    this.maxItems = 8;
    this.accessibleLabel = "";
    this.translations = {};
    this._isOpen = false;
    this._displayValue = "";
    this._highlightedId = "";
    this._menuId = `ndd-combo-box-menu-${NDDComboBox._counter++}`;
    this._menu = null;
    this._resizeObserver = null;
    this._handleScrollOrResize = () => {
      if (!this._isOpen) return;
      this._updateMenuWidth();
      this._menu?.reposition();
    };
    this._handleMenuToggle = (e) => {
      this._isOpen = e.newState === "open";
      if (!this._isOpen) {
        this._highlightedId = "";
      } else {
        requestAnimationFrame(() => {
          this._highlightedId = this._menu?.getHighlightedId() ?? "";
        });
      }
    };
    this._handleMenuSelect = (e) => {
      const item = e.target;
      this._displayValue = item.text;
      this.value = item.value || item.text;
      this._highlightedId = "";
      this._closeMenu();
      this._menu?.filter("");
      this.dispatchEvent(new CustomEvent("change", {
        detail: { value: this.value },
        bubbles: true,
        composed: true
      }));
      this._input?.focus();
    };
    this._pickerMousedown = false;
    this._handleMenuKeydown = (e) => {
      if (e.key !== "Tab") return;
      e.preventDefault();
      this._closeMenu();
      this._input?.focus();
    };
  }
  // — i18n ——————————————————————————————————————————————————————————————————
  _t(key) {
    return this.translations[key] ?? nddComboBoxTranslations[key];
  }
  // — Lifecycle ————————————————————————————————————————————————————————————
  firstUpdated() {
    if (!this.accessibleLabel) {
      console.warn("<ndd-combo-box>: No accessible-label provided. Add an accessible-label attribute for screen reader accessibility.");
    }
  }
  updated(changedProperties) {
    if (changedProperties.has("maxItems") && this._menu) {
      this._menu.maxItems = this.maxItems;
    }
  }
  connectedCallback() {
    super.connectedCallback();
    this._resizeObserver = new ResizeObserver(() => this._updateMenuWidth());
    this._resizeObserver.observe(this);
    window.addEventListener("scroll", this._handleScrollOrResize, true);
    window.addEventListener("resize", this._handleScrollOrResize);
  }
  disconnectedCallback() {
    super.disconnectedCallback();
    this._resizeObserver?.disconnect();
    this._resizeObserver = null;
    window.removeEventListener("scroll", this._handleScrollOrResize, true);
    window.removeEventListener("resize", this._handleScrollOrResize);
    if (this._menu) {
      this._menu.removeEventListener("toggle", this._handleMenuToggle);
      this._menu.removeEventListener("select", this._handleMenuSelect);
      this._menu.removeEventListener("keydown", this._handleMenuKeydown);
      this._menu = null;
    }
  }
  // — Slot —————————————————————————————————————————————————————————————————
  _onSlotChange() {
    const slot = this.shadowRoot?.querySelector("slot");
    const menu = slot?.assignedElements({ flatten: true }).find((el) => el.tagName.toLowerCase() === "ndd-menu");
    if (!menu || menu === this._menu) return;
    this._menu = menu;
    menu.id = this._menuId;
    menu.anchorElement = this;
    menu.placement = "bottom-start";
    menu.maxItems = this.maxItems;
    menu.variant = "listbox";
    menu.addEventListener("toggle", this._handleMenuToggle);
    menu.addEventListener("select", this._handleMenuSelect);
    menu.addEventListener("keydown", this._handleMenuKeydown);
    this._updateMenuWidth();
  }
  // — Menu width & position ————————————————————————————————————————————————
  _updateMenuWidth() {
    if (!this._menu) return;
    const rect = this.getBoundingClientRect();
    this._menu.width = `${rect.width}px`;
  }
  _updateActiveDescendant() {
    this._highlightedId = this._menu?.getHighlightedId() ?? "";
  }
  /**
   * Open the menu. Focus always stays on the input — highlight moves via
   * aria-activedescendant rather than by moving focus to items.
   */
  _openMenu() {
    if (!this._menu || this._isOpen) return;
    if (!("showPopover" in this._menu)) {
      console.warn("<ndd-combo-box>: Popover API is not supported in this browser. The dropdown will not open.");
      return;
    }
    this._updateMenuWidth();
    this._menu.showPopover();
  }
  _closeMenu() {
    if (!this._menu || !this._isOpen) return;
    this._menu.hidePopover();
  }
  _toggleMenu() {
    if (this._pickerMousedown) {
      this._pickerMousedown = false;
      return;
    }
    if (this._isOpen) {
      this._closeMenu();
      this._input?.focus();
    } else {
      this._openMenu();
      this._input?.focus();
    }
  }
  _handlePickerMousedown() {
    if (this._isOpen) {
      this._pickerMousedown = true;
    }
  }
  _handleInput(e) {
    const input = e.target;
    this._displayValue = input.value;
    this._menu?.filter(this._displayValue);
    this._updateActiveDescendant();
    if (!this._isOpen) this._openMenu();
    this.dispatchEvent(new CustomEvent("input", {
      detail: { value: this._displayValue },
      bubbles: true,
      composed: true
    }));
  }
  /** Accept a custom typed value and close the menu when focus leaves the input. */
  _handleBlur(e) {
    const relatedTarget = e.relatedTarget;
    if (!relatedTarget || !this._menu?.contains(relatedTarget)) {
      this._closeMenu();
    }
    if (this._displayValue !== "" && this._displayValue !== this.value) {
      this.value = this._displayValue;
      this.dispatchEvent(new CustomEvent("change", {
        detail: { value: this.value },
        bubbles: true,
        composed: true
      }));
    }
  }
  _handleKeydown(e) {
    if (!this._isOpen) {
      if (e.key === "ArrowDown") {
        e.preventDefault();
        this._openMenu();
      }
      return;
    }
    switch (e.key) {
      case "ArrowDown":
        e.preventDefault();
        this._menu?.moveHighlight("next");
        this._updateActiveDescendant();
        break;
      case "ArrowUp":
        e.preventDefault();
        this._menu?.moveHighlight("prev");
        this._updateActiveDescendant();
        break;
      case "Enter": {
        e.preventDefault();
        const highlighted = this._menu?.getHighlighted();
        if (highlighted) {
          highlighted.select();
        } else {
          this.value = this._displayValue;
          this._closeMenu();
          this.dispatchEvent(new CustomEvent("change", {
            detail: { value: this.value },
            bubbles: true,
            composed: true
          }));
        }
        break;
      }
      case "Escape":
        e.preventDefault();
        this._closeMenu();
        break;
    }
  }
  render() {
    return comboBoxTemplate(this);
  }
};
NDDComboBox.styles = comboBoxStyles;
NDDComboBox._counter = 0;
__decorateClass$M([
  property({ type: String })
], NDDComboBox.prototype, "value", 2);
__decorateClass$M([
  property({ type: String })
], NDDComboBox.prototype, "placeholder", 2);
__decorateClass$M([
  property({ type: Boolean, reflect: true })
], NDDComboBox.prototype, "disabled", 2);
__decorateClass$M([
  property({ type: String })
], NDDComboBox.prototype, "name", 2);
__decorateClass$M([
  property({ type: Number, attribute: "max-items" })
], NDDComboBox.prototype, "maxItems", 2);
__decorateClass$M([
  property({ type: String, attribute: "accessible-label" })
], NDDComboBox.prototype, "accessibleLabel", 2);
__decorateClass$M([
  property({ type: Object })
], NDDComboBox.prototype, "translations", 2);
__decorateClass$M([
  state()
], NDDComboBox.prototype, "_isOpen", 2);
__decorateClass$M([
  state()
], NDDComboBox.prototype, "_displayValue", 2);
__decorateClass$M([
  state()
], NDDComboBox.prototype, "_highlightedId", 2);
__decorateClass$M([
  query(".combo-box__input")
], NDDComboBox.prototype, "_input", 2);
NDDComboBox = __decorateClass$M([
  customElement("ndd-combo-box")
], NDDComboBox);
const stepperStyles = css`
	/* # Host */

	:host {
		display: inline-flex;
		-webkit-tap-highlight-color: transparent;
	}

	:host([hidden]) {
		display: none;
	}

	:host([disabled]) {
		opacity: var(--primitives-opacity-disabled);
		pointer-events: none;
	}

	:host([disabled]) ndd-icon-button {
		opacity: 1;
	}


	/* # Container */

	.stepper {
		display: inline-flex;
		flex-direction: row;
		align-items: center;
		background-color: var(--semantics-buttons-neutral-tinted-background-color);
	}

	:host([size='sm']) .stepper {
		border-radius: var(--semantics-controls-sm-corner-radius);
	}

	:host([size='md']) .stepper,
	:host(:not([size])) .stepper {
		border-radius: var(--semantics-controls-md-corner-radius);
	}

	.stepper:focus-visible {
		box-shadow: var(--semantics-focus-ring-box-shadow);
		outline: var(--semantics-focus-ring-outline);
	}


	/* # Divider */

	.stepper__divider {
		width: var(--semantics-dividers-thickness);
		flex-shrink: 0;
		background-color: var(--semantics-buttons-neutral-tinted-divider-color);
	}

	:host([size='sm']) .stepper__divider {
		height: var(--semantics-buttons-sm-divider-length);
	}

	:host([size='md']) .stepper__divider,
	:host(:not([size])) .stepper__divider {
		height: var(--semantics-buttons-md-divider-length);
	}


	/* # Focus */

	ndd-icon-button:focus-within {
		position: relative;
		z-index: 1;
	}
`;
function stepperTemplate(component) {
  const atMin = component.value <= component.min;
  const atMax = component.value >= component.max;
  return html`
		<div class="stepper"
			role="spinbutton"
			tabindex=${component.disabled ? nothing : "0"}
			aria-valuenow=${component.value}
			aria-valuemin=${isFinite(component.min) ? component.min : nothing}
			aria-valuemax=${isFinite(component.max) ? component.max : nothing}
			aria-label=${component._t("components.stepper.to-adjust-value-action")}
			aria-disabled=${component.disabled ? "true" : nothing}
			@keydown=${component._handleKeydown}
		>
			<ndd-icon-button
				variant="neutral-tinted"
				size=${component.size}
				icon="minus"
				text=${component._t("components.stepper.decrement-action")}
				?disabled=${component.disabled || atMin}
				aria-hidden="true"
				tabindex="-1"
				@click=${component._decrement}
			></ndd-icon-button>
			<div class="stepper__divider"
				aria-hidden="true"
			></div>
			<ndd-icon-button
				variant="neutral-tinted"
				size=${component.size}
				icon="plus"
				text=${component._t("components.stepper.increment-action")}
				?disabled=${component.disabled || atMax}
				aria-hidden="true"
				tabindex="-1"
				@click=${component._increment}
			></ndd-icon-button>
		</div>
	`;
}
const nddStepperTranslations = {
  "components.stepper.decrement-action": "Verlaag aantal",
  "components.stepper.increment-action": "Verhoog aantal",
  "components.stepper.to-adjust-value-action": "Aantal aanpassen"
};
var __defProp$G = Object.defineProperty;
var __getOwnPropDesc$L = Object.getOwnPropertyDescriptor;
var __decorateClass$L = (decorators, target, key, kind) => {
  var result = kind > 1 ? void 0 : kind ? __getOwnPropDesc$L(target, key) : target;
  for (var i = decorators.length - 1, decorator; i >= 0; i--)
    if (decorator = decorators[i])
      result = (kind ? decorator(target, key, result) : decorator(result)) || result;
  if (kind && result) __defProp$G(target, key, result);
  return result;
};
let NDDStepper = class extends LitElement {
  constructor() {
    super(...arguments);
    this.value = 0;
    this.min = 0;
    this.max = Infinity;
    this.step = 1;
    this.disabled = false;
    this.size = "md";
    this.translations = {};
  }
  // — i18n —————————————————————————————————————————————————————————————————
  _t(key) {
    return this.translations[key] ?? nddStepperTranslations[key];
  }
  // — Actions ——————————————————————————————————————————————————————————————
  _decrement() {
    if (this.disabled) return;
    const newValue = Math.max(this.min, this.value - this.step);
    if (newValue !== this.value) {
      this.value = newValue;
      this._dispatchChange();
    }
  }
  _increment() {
    if (this.disabled) return;
    const newValue = Math.min(this.max, this.value + this.step);
    if (newValue !== this.value) {
      this.value = newValue;
      this._dispatchChange();
    }
  }
  _handleKeydown(e) {
    switch (e.key) {
      case "ArrowUp":
      case "ArrowRight":
        e.preventDefault();
        this._increment();
        break;
      case "ArrowDown":
      case "ArrowLeft":
        e.preventDefault();
        this._decrement();
        break;
      case "Home":
        e.preventDefault();
        if (isFinite(this.min)) {
          this.value = this.min;
          this._dispatchChange();
        }
        break;
      case "End":
        e.preventDefault();
        if (isFinite(this.max)) {
          this.value = this.max;
          this._dispatchChange();
        }
        break;
    }
  }
  _dispatchChange() {
    this.dispatchEvent(new CustomEvent("change", {
      detail: { value: this.value },
      bubbles: true,
      composed: true
    }));
  }
  render() {
    return stepperTemplate(this);
  }
};
NDDStepper.styles = stepperStyles;
__decorateClass$L([
  property({ type: Number })
], NDDStepper.prototype, "value", 2);
__decorateClass$L([
  property({ type: Number })
], NDDStepper.prototype, "min", 2);
__decorateClass$L([
  property({ type: Number })
], NDDStepper.prototype, "max", 2);
__decorateClass$L([
  property({ type: Number })
], NDDStepper.prototype, "step", 2);
__decorateClass$L([
  property({ type: Boolean, reflect: true })
], NDDStepper.prototype, "disabled", 2);
__decorateClass$L([
  property({ type: String, reflect: true })
], NDDStepper.prototype, "size", 2);
__decorateClass$L([
  property({ type: Object })
], NDDStepper.prototype, "translations", 2);
NDDStepper = __decorateClass$L([
  customElement("ndd-stepper")
], NDDStepper);
const checkboxStyles = css`

	/* # Host */

	:host {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		position: relative;
		width: var(--semantics-controls-xs-min-size);
		height: var(--semantics-controls-xs-min-size);
		-webkit-tap-highlight-color: transparent;
	}

	:host([hidden]) {
		display: none;
	}


	/* # Native input */

	.checkbox__input {
		position: absolute;
		inset: 0;
		width: 100%;
		height: 100%;
		margin: 0;
		opacity: 0;
		z-index: 1;
	}


	/* # Visual box */

	.checkbox__box {
		position: relative;
		box-sizing: border-box;
		width: var(--semantics-controls-xs-min-size);
		height: var(--semantics-controls-xs-min-size);
		border-radius: var(--semantics-controls-xs-corner-radius);
		border: var(--components-checkbox-border-thickness) solid var(--components-checkbox-border-color);
		background-color: var(--components-checkbox-background-color);
		color: transparent;
	}


	/* # Selected */

	.checkbox__input:checked ~ .checkbox__box,
	.checkbox__input:indeterminate ~ .checkbox__box {
		border-color: var(--components-checkbox-is-selected-border-color);
		background-color: var(--components-checkbox-is-selected-background-color);
		color: var(--components-checkbox-is-selected-icon-color);
	}


	/* # Hover */

	.checkbox__input:hover:not(:disabled) ~ .checkbox__box {
		border-color: var(--components-checkbox-is-hovered-border-color);
	}

	.checkbox__input:checked:hover:not(:disabled) ~ .checkbox__box,
	.checkbox__input:indeterminate:hover:not(:disabled) ~ .checkbox__box {
		border-color: var(--components-checkbox-is-selected-is-hovered-border-color);
		background-color: var(--components-checkbox-is-selected-is-hovered-background-color);
		color: var(--components-checkbox-is-selected-is-hovered-icon-color);
	}


	/* # Active */

	.checkbox__input:active:not(:disabled) ~ .checkbox__box {
		border-color: var(--components-checkbox-is-active-border-color);
	}

	.checkbox__input:checked:active:not(:disabled) ~ .checkbox__box,
	.checkbox__input:indeterminate:active:not(:disabled) ~ .checkbox__box {
		border-color: var(--components-checkbox-is-selected-is-active-border-color);
		background-color: var(--components-checkbox-is-selected-is-active-background-color);
		color: var(--components-checkbox-is-selected-is-active-icon-color);
	}


	/* # Focus */

	.checkbox__input:focus-visible ~ .checkbox__box {
		outline: var(--semantics-focus-ring-outline);
		box-shadow: var(--semantics-focus-ring-box-shadow);
	}


	/* # Disabled */

	.checkbox__input:disabled ~ .checkbox__box {
		opacity: var(--primitives-opacity-disabled);
	}


	/* # Icons */

	.checkbox__check-icon,
	.checkbox__indeterminate-icon {
		position: absolute;
		top: 50%;
		left: 50%;
		transform: translate(-50%, -50%);
		width: var(--primitives-space-24);
		height: var(--primitives-space-24);
		display: none;
	}

	.checkbox__input:checked ~ .checkbox__box .checkbox__check-icon {
		display: block;
	}

	.checkbox__input:checked:indeterminate ~ .checkbox__box .checkbox__check-icon {
		display: none;
	}

	.checkbox__input:indeterminate ~ .checkbox__box .checkbox__indeterminate-icon {
		display: block;
	}
`;
function checkboxTemplate(component) {
  return html`
		<input class="checkbox__input"
			type="checkbox"
			.checked=${component.checked}
			.indeterminate=${component.indeterminate}
			?disabled=${component.disabled}
			name=${component.name || ""}
			value=${component.value}
			aria-label=${component.accessibleLabel || nothing}
			@change=${component._handleChange}
		>
		<div class="checkbox__box" aria-hidden="true">
			<ndd-icon class="checkbox__check-icon" name="check-mark-small"></ndd-icon>
			<ndd-icon class="checkbox__indeterminate-icon" name="minus-extra-small"></ndd-icon>
		</div>
	`;
}
var __defProp$F = Object.defineProperty;
var __getOwnPropDesc$K = Object.getOwnPropertyDescriptor;
var __decorateClass$K = (decorators, target, key, kind) => {
  var result = kind > 1 ? void 0 : kind ? __getOwnPropDesc$K(target, key) : target;
  for (var i = decorators.length - 1, decorator; i >= 0; i--)
    if (decorator = decorators[i])
      result = (kind ? decorator(target, key, result) : decorator(result)) || result;
  if (kind && result) __defProp$F(target, key, result);
  return result;
};
let NDDCheckbox = class extends LitElement {
  constructor() {
    super(...arguments);
    this.checked = false;
    this.disabled = false;
    this.indeterminate = false;
    this.value = "on";
    this.name = "";
    this.accessibleLabel = "";
  }
  toggle() {
    if (this.disabled) return;
    this.checked = !this.checked;
    this.indeterminate = false;
    this.dispatchEvent(new CustomEvent("change", {
      detail: { checked: this.checked, value: this.value },
      bubbles: true,
      composed: true
    }));
  }
  _handleChange(e) {
    const input = e.target;
    this.checked = input.checked;
    this.indeterminate = input.indeterminate;
    this.dispatchEvent(new CustomEvent("change", {
      detail: { checked: this.checked, value: this.value },
      bubbles: true,
      composed: true
    }));
  }
  render() {
    return checkboxTemplate(this);
  }
};
NDDCheckbox.styles = checkboxStyles;
__decorateClass$K([
  property({ type: Boolean, reflect: true })
], NDDCheckbox.prototype, "checked", 2);
__decorateClass$K([
  property({ type: Boolean, reflect: true })
], NDDCheckbox.prototype, "disabled", 2);
__decorateClass$K([
  property({ type: Boolean, reflect: true })
], NDDCheckbox.prototype, "indeterminate", 2);
__decorateClass$K([
  property({ type: String })
], NDDCheckbox.prototype, "value", 2);
__decorateClass$K([
  property({ type: String })
], NDDCheckbox.prototype, "name", 2);
__decorateClass$K([
  property({ type: String, attribute: "accessible-label" })
], NDDCheckbox.prototype, "accessibleLabel", 2);
NDDCheckbox = __decorateClass$K([
  customElement("ndd-checkbox")
], NDDCheckbox);
const checkboxFieldStyles = css`
	/* # Host */

	:host {
		display: block;
	}

	:host([hidden]) {
		display: none;
	}


	/* # Container */

	.checkbox-field {
		display: flex;
		flex-direction: row;
		align-items: flex-start;
		gap: var(--primitives-space-8);
		min-height: var(--semantics-controls-md-min-size);
	}


	/* # Control */

	.checkbox-field__control {
		display: flex;
		flex-shrink: 0;
		min-height: var(--semantics-controls-md-min-size);
		align-items: center;
	}


	/* # Label */

	.checkbox-field__label {
		padding-top: calc((var(--semantics-controls-md-min-size) - 1em * var(--primitives-line-height-snug)) / 2);
		display: flex;
		flex-grow: 1;
		font: var(--primitives-font-body-md-regular-snug);
		color: var(--semantics-content-color);
		cursor: default;
	}

	:host([disabled]) .checkbox-field__label {
		opacity: var(--primitives-opacity-disabled);
	}
`;
function checkboxFieldTemplate(component) {
  return html`
		<div class="checkbox-field"
			@click=${component._handleLabelClick}
		>
			<div class="checkbox-field__control">
				<ndd-checkbox
					?checked=${component.checked}
					?indeterminate=${component.indeterminate}
					?disabled=${component.disabled}
					name=${component.name || nothing}
					value=${component.value}
					accessible-label=${component.label || nothing}
					@change=${component._handleChange}
				></ndd-checkbox>
			</div>
			<span class="checkbox-field__label">${component.label}</span>
		</div>
	`;
}
var __defProp$E = Object.defineProperty;
var __getOwnPropDesc$J = Object.getOwnPropertyDescriptor;
var __decorateClass$J = (decorators, target, key, kind) => {
  var result = kind > 1 ? void 0 : kind ? __getOwnPropDesc$J(target, key) : target;
  for (var i = decorators.length - 1, decorator; i >= 0; i--)
    if (decorator = decorators[i])
      result = (kind ? decorator(target, key, result) : decorator(result)) || result;
  if (kind && result) __defProp$E(target, key, result);
  return result;
};
let NDDCheckboxField = class extends LitElement {
  constructor() {
    super(...arguments);
    this.checked = false;
    this.indeterminate = false;
    this.disabled = false;
    this.value = "on";
    this.name = "";
    this.label = "";
  }
  _handleLabelClick(e) {
    if (this.disabled) return;
    if (e.target.closest?.("ndd-checkbox")) return;
    const checkbox = this.shadowRoot?.querySelector("ndd-checkbox");
    checkbox?.toggle();
  }
  _handleChange(e) {
    const { checked } = e.detail;
    this.checked = checked;
    this.indeterminate = false;
    this.dispatchEvent(new CustomEvent("change", {
      detail: { checked: this.checked, value: this.value },
      bubbles: true,
      composed: true
    }));
  }
  render() {
    return checkboxFieldTemplate(this);
  }
};
NDDCheckboxField.styles = checkboxFieldStyles;
__decorateClass$J([
  property({ type: Boolean, reflect: true })
], NDDCheckboxField.prototype, "checked", 2);
__decorateClass$J([
  property({ type: Boolean, reflect: true })
], NDDCheckboxField.prototype, "indeterminate", 2);
__decorateClass$J([
  property({ type: Boolean, reflect: true })
], NDDCheckboxField.prototype, "disabled", 2);
__decorateClass$J([
  property({ type: String })
], NDDCheckboxField.prototype, "value", 2);
__decorateClass$J([
  property({ type: String })
], NDDCheckboxField.prototype, "name", 2);
__decorateClass$J([
  property({ type: String })
], NDDCheckboxField.prototype, "label", 2);
NDDCheckboxField = __decorateClass$J([
  customElement("ndd-checkbox-field")
], NDDCheckboxField);
const radioButtonStyles = css`

	/* # Host */

	:host {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		position: relative;
		width: var(--semantics-controls-xs-min-size);
		height: var(--semantics-controls-xs-min-size);
		-webkit-tap-highlight-color: transparent;
	}

	:host([hidden]) {
		display: none;
	}


	/* # Native input */

	.radio-button__input {
		position: absolute;
		inset: 0;
		width: 100%;
		height: 100%;
		margin: 0;
		opacity: 0;
		z-index: 1;
	}


	/* # Outer shape */

	.radio-button__outer-shape {
		position: relative;
		box-sizing: border-box;
		width: var(--semantics-controls-xs-min-size);
		height: var(--semantics-controls-xs-min-size);
		border-radius: 50%;
		border: var(--components-radio-button-border-thickness) solid var(--components-radio-button-border-color);
		background-color: var(--components-radio-button-background-color);
	}


	/* # Inner shape */

	.radio-button__inner-shape {
		position: absolute;
		top: 50%;
		left: 50%;
		transform: translate(-50%, -50%) scale(0);
		width: var(--primitives-space-20);
		height: var(--primitives-space-20);
		border-radius: 50%;
		border: var(--components-radio-button-is-selected-inner-shape-border-thickness) solid var(--components-radio-button-is-selected-inner-shape-border-color);
		box-sizing: border-box;
	}


	/* # Selected */

	.radio-button__input:checked ~ .radio-button__outer-shape {
		border-color: var(--components-radio-button-is-selected-border-color);
		background-color: var(--components-radio-button-is-selected-background-color);
	}

	.radio-button__input:checked ~ .radio-button__outer-shape .radio-button__inner-shape {
		transform: translate(-50%, -50%) scale(1);
	}


	/* # Hover */

	.radio-button__input:hover:not(:disabled) ~ .radio-button__outer-shape {
		border-color: var(--components-radio-button-is-hovered-border-color);
	}

	.radio-button__input:checked:hover:not(:disabled) ~ .radio-button__outer-shape {
		border-color: var(--components-radio-button-is-selected-is-hovered-border-color);
		background-color: var(--components-radio-button-is-selected-is-hovered-background-color);
	}

	.radio-button__input:checked:hover:not(:disabled) ~ .radio-button__outer-shape .radio-button__inner-shape {
		border-color: var(--components-radio-button-is-selected-is-hovered-inner-shape-border-color);
	}


	/* # Active */

	.radio-button__input:active:not(:disabled) ~ .radio-button__outer-shape {
		border-color: var(--components-radio-button-is-active-border-color);
	}

	.radio-button__input:checked:active:not(:disabled) ~ .radio-button__outer-shape {
		border-color: var(--components-radio-button-is-selected-is-active-border-color);
		background-color: var(--components-radio-button-is-selected-is-active-background-color);
	}

	.radio-button__input:checked:active:not(:disabled) ~ .radio-button__outer-shape .radio-button__inner-shape {
		border-color: var(--components-radio-button-is-selected-is-active-inner-shape-border-color);
	}


	/* # Focus */

	.radio-button__input:focus-visible ~ .radio-button__outer-shape {
		outline: var(--semantics-focus-ring-outline);
		box-shadow: var(--semantics-focus-ring-box-shadow);
	}


	/* # Disabled */

	.radio-button__input:disabled ~ .radio-button__outer-shape {
		opacity: var(--primitives-opacity-disabled);
	}
`;
function radioButtonTemplate(component) {
  return html`
		<input class="radio-button__input"
			type="radio"
			.checked=${component.checked}
			?disabled=${component.disabled}
			?required=${component.required}
			name=${component.name || ""}
			value=${component.value}
			aria-label=${component.accessibleLabel || nothing}
			@change=${component._handleChange}
		>
		<div class="radio-button__outer-shape" aria-hidden="true">
			<div class="radio-button__inner-shape"></div>
		</div>
	`;
}
var __defProp$D = Object.defineProperty;
var __getOwnPropDesc$I = Object.getOwnPropertyDescriptor;
var __decorateClass$I = (decorators, target, key, kind) => {
  var result = kind > 1 ? void 0 : kind ? __getOwnPropDesc$I(target, key) : target;
  for (var i = decorators.length - 1, decorator; i >= 0; i--)
    if (decorator = decorators[i])
      result = (kind ? decorator(target, key, result) : decorator(result)) || result;
  if (kind && result) __defProp$D(target, key, result);
  return result;
};
let NDDRadioButton = class extends LitElement {
  constructor() {
    super(...arguments);
    this.checked = false;
    this.disabled = false;
    this.required = false;
    this.name = "";
    this.value = "";
    this.accessibleLabel = "";
  }
  select() {
    if (this.disabled || this.checked) return;
    const input = this.shadowRoot?.querySelector("input");
    if (!input) return;
    input.checked = true;
    input.dispatchEvent(new Event("change", { bubbles: true }));
  }
  _handleChange(e) {
    const input = e.target;
    this.checked = input.checked;
    this.dispatchEvent(new CustomEvent("change", {
      detail: { checked: this.checked, value: this.value, name: this.name },
      bubbles: true,
      composed: true
    }));
  }
  render() {
    return radioButtonTemplate(this);
  }
};
NDDRadioButton.styles = radioButtonStyles;
__decorateClass$I([
  property({ type: Boolean, reflect: true })
], NDDRadioButton.prototype, "checked", 2);
__decorateClass$I([
  property({ type: Boolean, reflect: true })
], NDDRadioButton.prototype, "disabled", 2);
__decorateClass$I([
  property({ type: Boolean, reflect: true })
], NDDRadioButton.prototype, "required", 2);
__decorateClass$I([
  property({ type: String })
], NDDRadioButton.prototype, "name", 2);
__decorateClass$I([
  property({ type: String })
], NDDRadioButton.prototype, "value", 2);
__decorateClass$I([
  property({ type: String, attribute: "accessible-label" })
], NDDRadioButton.prototype, "accessibleLabel", 2);
NDDRadioButton = __decorateClass$I([
  customElement("ndd-radio-button")
], NDDRadioButton);
const radioButtonFieldStyles = css`
	/* # Host */

	:host {
		display: block;
	}

	:host([hidden]) {
		display: none;
	}


	/* # Container */

	.radio-button-field {
		display: flex;
		flex-direction: row;
		align-items: flex-start;
		gap: var(--primitives-space-8);
		min-height: var(--semantics-controls-md-min-size);
	}


	/* # Control */

	.radio-button-field__control {
		display: flex;
		flex-shrink: 0;
		min-height: var(--semantics-controls-md-min-size);
		align-items: center;
	}


	/* # Label */

	.radio-button-field__label {
		padding-top: calc((var(--semantics-controls-md-min-size) - 1em * var(--primitives-line-height-snug)) / 2);
		display: flex;
		flex-grow: 1;
		font: var(--primitives-font-body-md-regular-snug);
		color: var(--semantics-content-color);
		cursor: default;
	}

	:host([disabled]) .radio-button-field__label {
		opacity: var(--primitives-opacity-disabled);
	}
`;
function radioButtonFieldTemplate(component) {
  return html`
		<div class="radio-button-field"
			@click=${component._handleLabelClick}
		>
			<div class="radio-button-field__control">
				<ndd-radio-button
					?checked=${component.checked}
					?disabled=${component.disabled}
					?required=${component.required}
					name=${component.name || ""}
					value=${component.value}
					accessible-label=${component.label || nothing}
					@change=${component._handleChange}
				></ndd-radio-button>
			</div>
			<span class="radio-button-field__label">${component.label}</span>
		</div>
	`;
}
var __defProp$C = Object.defineProperty;
var __getOwnPropDesc$H = Object.getOwnPropertyDescriptor;
var __decorateClass$H = (decorators, target, key, kind) => {
  var result = kind > 1 ? void 0 : kind ? __getOwnPropDesc$H(target, key) : target;
  for (var i = decorators.length - 1, decorator; i >= 0; i--)
    if (decorator = decorators[i])
      result = (kind ? decorator(target, key, result) : decorator(result)) || result;
  if (kind && result) __defProp$C(target, key, result);
  return result;
};
let NDDRadioButtonField = class extends LitElement {
  constructor() {
    super(...arguments);
    this.checked = false;
    this.disabled = false;
    this.value = "";
    this.name = "";
    this.required = false;
    this.label = "";
  }
  _handleLabelClick(e) {
    if (this.disabled) return;
    if (e.target.closest?.("ndd-radio-button")) return;
    const radioButton = this.shadowRoot?.querySelector("ndd-radio-button");
    radioButton?.select();
  }
  _handleChange(e) {
    this.checked = e.detail.checked;
    this.dispatchEvent(new CustomEvent("change", {
      detail: { checked: this.checked, value: this.value },
      bubbles: true,
      composed: true
    }));
  }
  render() {
    return radioButtonFieldTemplate(this);
  }
};
NDDRadioButtonField.styles = radioButtonFieldStyles;
__decorateClass$H([
  property({ type: Boolean, reflect: true })
], NDDRadioButtonField.prototype, "checked", 2);
__decorateClass$H([
  property({ type: Boolean, reflect: true })
], NDDRadioButtonField.prototype, "disabled", 2);
__decorateClass$H([
  property({ type: String })
], NDDRadioButtonField.prototype, "value", 2);
__decorateClass$H([
  property({ type: String })
], NDDRadioButtonField.prototype, "name", 2);
__decorateClass$H([
  property({ type: Boolean, reflect: true })
], NDDRadioButtonField.prototype, "required", 2);
__decorateClass$H([
  property({ type: String })
], NDDRadioButtonField.prototype, "label", 2);
NDDRadioButtonField = __decorateClass$H([
  customElement("ndd-radio-button-field")
], NDDRadioButtonField);
const radioButtonGroupStyles = css`


	/* # Host */

	:host {
		display: block;
	}

	:host([hidden]) {
		display: none;
	}


	/* # Group */

	.radio-button-group {
		display: flex;
		flex-direction: column;
	}
`;
function radioButtonGroupTemplate(component) {
  return html`
		<div class="radio-button-group">
			<slot @slotchange=${component._onSlotChange}></slot>
		</div>
	`;
}
var __defProp$B = Object.defineProperty;
var __getOwnPropDesc$G = Object.getOwnPropertyDescriptor;
var __decorateClass$G = (decorators, target, key, kind) => {
  var result = kind > 1 ? void 0 : kind ? __getOwnPropDesc$G(target, key) : target;
  for (var i = decorators.length - 1, decorator; i >= 0; i--)
    if (decorator = decorators[i])
      result = (kind ? decorator(target, key, result) : decorator(result)) || result;
  if (kind && result) __defProp$B(target, key, result);
  return result;
};
let NDDRadioButtonGroup = class extends LitElement {
  constructor() {
    super(...arguments);
    this.name = "";
    this.disabled = false;
    this.required = false;
    this.accessibleLabelledBy = "";
    this._handleChange = (e) => {
      const changedField = e.target;
      if (!changedField.checked) return;
      this._getFields().forEach((field) => {
        if (field !== changedField) field.checked = false;
      });
    };
    this._handleKeyDown = (e) => {
      if (e.key !== "ArrowDown" && e.key !== "ArrowUp" && e.key !== "ArrowRight" && e.key !== "ArrowLeft") return;
      const fields = this._getEnabledFields();
      if (fields.length === 0) return;
      const activeField = fields.find((f) => f.checked) ?? fields[0];
      const currentIndex = fields.indexOf(activeField);
      const isNext = e.key === "ArrowDown" || e.key === "ArrowRight";
      const nextIndex = isNext ? (currentIndex + 1) % fields.length : (currentIndex - 1 + fields.length) % fields.length;
      const nextField = fields[nextIndex];
      if (!nextField) return;
      e.preventDefault();
      activeField.checked = false;
      nextField.checked = true;
      const input = nextField.shadowRoot?.querySelector("ndd-radio-button")?.shadowRoot?.querySelector("input");
      input?.focus();
      nextField.dispatchEvent(new CustomEvent("change", {
        detail: { checked: true, value: nextField.value },
        bubbles: true,
        composed: true
      }));
    };
    this._onSlotChange = () => {
      this._syncFields();
    };
  }
  connectedCallback() {
    super.connectedCallback();
    this.setAttribute("role", "radiogroup");
    this.addEventListener("keydown", this._handleKeyDown);
    this.addEventListener("change", this._handleChange);
  }
  disconnectedCallback() {
    super.disconnectedCallback();
    this.removeEventListener("keydown", this._handleKeyDown);
    this.removeEventListener("change", this._handleChange);
  }
  updated(changed) {
    if (changed.has("name") || changed.has("disabled") || changed.has("required")) {
      this._syncFields();
    }
    if (changed.has("accessibleLabelledBy")) {
      if (this.accessibleLabelledBy) {
        this.setAttribute("aria-labelledby", this.accessibleLabelledBy);
      } else {
        this.removeAttribute("aria-labelledby");
      }
    }
    if (changed.has("required")) {
      if (this.required) {
        this.setAttribute("aria-required", "true");
      } else {
        this.removeAttribute("aria-required");
      }
    }
  }
  _getFields() {
    return Array.from(this.querySelectorAll("ndd-radio-button-field"));
  }
  _getEnabledFields() {
    return this._getFields().filter((f) => !f.disabled);
  }
  _syncFields() {
    this._getFields().forEach((field) => {
      field.name = this.name;
      field.required = this.required;
      if (this.disabled) {
        if (!field.hasAttribute("disabled")) {
          field.setAttribute("group-disabled", "");
          field.disabled = true;
        }
      } else if (field.hasAttribute("group-disabled")) {
        field.removeAttribute("group-disabled");
        field.disabled = false;
      }
    });
  }
  render() {
    return radioButtonGroupTemplate(this);
  }
};
NDDRadioButtonGroup.styles = radioButtonGroupStyles;
__decorateClass$G([
  property({ type: String })
], NDDRadioButtonGroup.prototype, "name", 2);
__decorateClass$G([
  property({ type: Boolean, reflect: true })
], NDDRadioButtonGroup.prototype, "disabled", 2);
__decorateClass$G([
  property({ type: Boolean, reflect: true })
], NDDRadioButtonGroup.prototype, "required", 2);
__decorateClass$G([
  property({ type: String, attribute: "accessible-labelledby" })
], NDDRadioButtonGroup.prototype, "accessibleLabelledBy", 2);
NDDRadioButtonGroup = __decorateClass$G([
  customElement("ndd-radio-button-group")
], NDDRadioButtonGroup);
const switchStyles = css`
	/* # Host */

	:host {
		display: inline-block;
		position: relative;
		flex-shrink: 0;
		--_switch-xs-width: var(--semantics-controls-md-min-size);
		--_switch-xs-height: var(--semantics-controls-xs-min-size);
		--_switch-sm-width: var(--semantics-controls-lg-min-size);
		--_switch-sm-height: var(--semantics-controls-sm-min-size);
		--_switch-padding: var(--primitives-space-2);
		--_switch-xs-thumb-size: calc(var(--_switch-xs-height) - var(--_switch-padding) * 2 - var(--components-switch-thumb-border-thickness) * 2);
		--_switch-sm-thumb-size: calc(var(--_switch-sm-height) - var(--_switch-padding) * 2 - var(--components-switch-thumb-border-thickness) * 2);
		--_transition-duration: 150ms;
		-webkit-tap-highlight-color: transparent;
	}

	:host([hidden]) {
		display: none;
	}

	:host([disabled]) {
		opacity: var(--primitives-opacity-disabled);
	}

	:host([size='xs']) {
		width: var(--_switch-xs-width);
		height: var(--_switch-xs-height);
	}

	:host([size='sm']),
	:host(:not([size])) {
		width: var(--_switch-sm-width);
		height: var(--_switch-sm-height);
	}


	/* # Input */

	.switch__input {
		position: absolute;
		inset: 0;
		z-index: 1;
		width: 100%;
		height: 100%;
		margin: 0;
		opacity: 0;
	}


	/* # Track */

	.switch__track {
		position: relative;
		display: flex;
		align-items: center;
		box-sizing: border-box;
		width: 100%;
		height: 100%;
		padding: var(--_switch-padding);
		background-color: var(--components-switch-background-color);
		border: var(--components-switch-border-thickness) solid var(--components-switch-border-color);
		transition: background-color var(--_transition-duration) ease, border-color var(--_transition-duration) ease;
	}

	:host([size='xs']) .switch__track {
		border-radius: calc(var(--semantics-controls-xs-min-size) / 2);
	}

	:host([size='sm']) .switch__track,
	:host(:not([size])) .switch__track {
		border-radius: calc(var(--semantics-controls-sm-min-size) / 2);
	}

	.switch__input:checked ~ .switch__track {
		background-color: var(--components-switch-is-selected-background-color);
		border-color: var(--components-switch-is-selected-background-color);
	}

	.switch__input:focus-visible ~ .switch__track {
		outline: var(--semantics-focus-ring-outline);
		box-shadow: var(--semantics-focus-ring-box-shadow);
	}


	/* # Thumb */

	.switch__thumb {
		position: absolute;
		left: var(--_switch-padding);
		box-sizing: border-box;
		border-radius: 50%;
		background-color: var(--components-switch-thumb-background-color);
		border: var(--components-switch-thumb-border-thickness) solid var(--components-switch-thumb-border-color);
		transition: width var(--_transition-duration) ease, height var(--_transition-duration) ease, left var(--_transition-duration) ease, background-color var(--_transition-duration) ease, border-color var(--_transition-duration) ease;
		will-change: width, height, left;
	}

	:host([size='xs']) .switch__thumb {
		width: var(--_switch-xs-thumb-size);
		height: var(--_switch-xs-thumb-size);
	}

	:host([size='sm']) .switch__thumb,
	:host(:not([size])) .switch__thumb {
		width: var(--_switch-sm-thumb-size);
		height: var(--_switch-sm-thumb-size);
	}

	.switch__input:checked ~ .switch__track .switch__thumb {
		background-color: var(--components-switch-is-selected-thumb-background-color);
		border-color: var(--components-switch-is-selected-thumb-background-color);
	}

	:host([size='xs']) .switch__input:checked ~ .switch__track .switch__thumb {
		left: calc(var(--_switch-xs-width) - var(--components-switch-thumb-border-thickness) * 2 - var(--_switch-xs-thumb-size) - var(--_switch-padding) * 2);
		width: calc(var(--_switch-xs-thumb-size) + var(--_switch-padding) * 2);
		height: calc(var(--_switch-xs-thumb-size) + var(--_switch-padding) * 2);
	}

	:host([size='sm']) .switch__input:checked ~ .switch__track .switch__thumb,
	:host(:not([size])) .switch__input:checked ~ .switch__track .switch__thumb {
		left: calc(var(--_switch-sm-width) - var(--components-switch-thumb-border-thickness) * 2 - var(--_switch-sm-thumb-size) - var(--_switch-padding) * 2);
		width: calc(var(--_switch-sm-thumb-size) + var(--_switch-padding) * 2);
		height: calc(var(--_switch-sm-thumb-size) + var(--_switch-padding) * 2);
	}


	/* # Check */

	.switch__check {
		position: absolute;
		top: 50%;
		left: 50%;
		transform: translate(-50%, -50%);
		display: flex;
		align-items: center;
		justify-content: center;
		width: calc(100% + var(--components-switch-thumb-border-thickness) * 2);
		height: calc(100% + var(--components-switch-thumb-border-thickness) * 2);
		color: var(--components-switch-is-selected-background-color);
		opacity: 0;
		pointer-events: none;
		transition: opacity var(--_transition-duration) ease;
	}

	.switch__input:checked ~ .switch__track .switch__check {
		opacity: 1;
	}
`;
function switchTemplate(component) {
  return html`
		<input class="switch__input"
			type="checkbox"
			role="switch"
			.checked=${component.checked}
			aria-checked=${component.checked}
			?disabled=${component.disabled}
			value=${component.value}
			aria-label=${component.accessibleLabel || nothing}
			@change=${component._handleChange}
		>
		<div class="switch__track"
			aria-hidden="true"
		>
			<div class="switch__thumb">
				<div class="switch__check">
					<ndd-icon name="check-mark-small"></ndd-icon>
				</div>
			</div>
		</div>
	`;
}
var __defProp$A = Object.defineProperty;
var __getOwnPropDesc$F = Object.getOwnPropertyDescriptor;
var __decorateClass$F = (decorators, target, key, kind) => {
  var result = kind > 1 ? void 0 : kind ? __getOwnPropDesc$F(target, key) : target;
  for (var i = decorators.length - 1, decorator; i >= 0; i--)
    if (decorator = decorators[i])
      result = (kind ? decorator(target, key, result) : decorator(result)) || result;
  if (kind && result) __defProp$A(target, key, result);
  return result;
};
let NDDSwitch = class extends LitElement {
  constructor() {
    super(...arguments);
    this.checked = false;
    this.disabled = false;
    this.size = "sm";
    this.accessibleLabel = "";
    this.value = "on";
  }
  firstUpdated() {
    if (!this.accessibleLabel) {
      console.warn("<ndd-switch>: No accessible-label provided. Use ndd-switch-field for labeled usage, or provide an accessible-label attribute for screen reader accessibility.");
    }
  }
  toggle() {
    if (this.disabled) return;
    this.checked = !this.checked;
    this.dispatchEvent(new CustomEvent("change", {
      detail: { checked: this.checked, value: this.value },
      bubbles: true,
      composed: true
    }));
  }
  _handleChange(e) {
    if (this.disabled) return;
    const input = e.target;
    this.checked = input.checked;
    this.dispatchEvent(new CustomEvent("change", {
      detail: { checked: this.checked, value: this.value },
      bubbles: true,
      composed: true
    }));
  }
  render() {
    return switchTemplate(this);
  }
};
NDDSwitch.styles = switchStyles;
__decorateClass$F([
  property({ type: Boolean, reflect: true })
], NDDSwitch.prototype, "checked", 2);
__decorateClass$F([
  property({ type: Boolean, reflect: true })
], NDDSwitch.prototype, "disabled", 2);
__decorateClass$F([
  property({ type: String, reflect: true })
], NDDSwitch.prototype, "size", 2);
__decorateClass$F([
  property({ type: String, attribute: "accessible-label" })
], NDDSwitch.prototype, "accessibleLabel", 2);
__decorateClass$F([
  property({ type: String })
], NDDSwitch.prototype, "value", 2);
NDDSwitch = __decorateClass$F([
  customElement("ndd-switch")
], NDDSwitch);
const switchFieldStyles = css`
	/* # Host */

	:host {
		display: block;
	}

	:host([hidden]) {
		display: none;
	}


	/* # Container */

	.switch-field {
		display: flex;
		flex-direction: row;
		align-items: flex-start;
		gap: var(--primitives-space-8);
		min-height: var(--semantics-controls-md-min-size);
	}


	/* # Control */

	.switch-field__control {
		display: flex;
		flex-shrink: 0;
		min-height: var(--semantics-controls-md-min-size);
		align-items: center;
	}


	/* # Label */

	.switch-field__label {
		padding-top: calc((var(--semantics-controls-md-min-size) - 1em * var(--primitives-line-height-snug)) / 2);
		display: flex;
		flex-grow: 1;
		font: var(--primitives-font-body-md-regular-snug);
		color: var(--semantics-content-color);
		cursor: default;
	}

	:host([disabled]) .switch-field__label {
		opacity: var(--primitives-opacity-disabled);
	}
`;
function switchFieldTemplate(component) {
  return html`
		<div class="switch-field"
			@click=${component._handleLabelClick}
		>
			<div class="switch-field__control">
				<ndd-switch
					size="sm"
					name=${component.name || nothing}
					value=${component.value}
					?checked=${component.checked}
					?disabled=${component.disabled}
					accessible-label=${component.label || nothing}
					@change=${component._handleChange}
				></ndd-switch>
			</div>
			<span class="switch-field__label">${component.label}</span>
		</div>
	`;
}
var __defProp$z = Object.defineProperty;
var __getOwnPropDesc$E = Object.getOwnPropertyDescriptor;
var __decorateClass$E = (decorators, target, key, kind) => {
  var result = kind > 1 ? void 0 : kind ? __getOwnPropDesc$E(target, key) : target;
  for (var i = decorators.length - 1, decorator; i >= 0; i--)
    if (decorator = decorators[i])
      result = (kind ? decorator(target, key, result) : decorator(result)) || result;
  if (kind && result) __defProp$z(target, key, result);
  return result;
};
let NDDSwitchField = class extends LitElement {
  constructor() {
    super(...arguments);
    this.checked = false;
    this.disabled = false;
    this.value = "on";
    this.name = "";
    this.label = "";
  }
  _handleLabelClick(e) {
    if (this.disabled) return;
    if (e.target.closest?.("ndd-switch")) return;
    const switchEl = this.shadowRoot?.querySelector("ndd-switch");
    switchEl?.toggle();
  }
  _handleChange(e) {
    this.checked = e.detail.checked;
    this.dispatchEvent(new CustomEvent("change", {
      detail: { checked: this.checked, value: this.value },
      bubbles: true,
      composed: true
    }));
  }
  render() {
    return switchFieldTemplate(this);
  }
};
NDDSwitchField.styles = switchFieldStyles;
__decorateClass$E([
  property({ type: Boolean, reflect: true })
], NDDSwitchField.prototype, "checked", 2);
__decorateClass$E([
  property({ type: Boolean, reflect: true })
], NDDSwitchField.prototype, "disabled", 2);
__decorateClass$E([
  property({ type: String })
], NDDSwitchField.prototype, "value", 2);
__decorateClass$E([
  property({ type: String })
], NDDSwitchField.prototype, "name", 2);
__decorateClass$E([
  property({ type: String })
], NDDSwitchField.prototype, "label", 2);
NDDSwitchField = __decorateClass$E([
  customElement("ndd-switch-field")
], NDDSwitchField);
const segmentedControlStyles = css`
	/* # Host */

	:host {
		display: inline-grid;
		grid-auto-columns: 1fr;
		grid-auto-flow: column;
		background-color: var(--semantics-buttons-neutral-tinted-background-color);
		-webkit-tap-highlight-color: transparent;
	}

	:host([hidden]) {
		display: none;
	}

	:host([full-width]) {
		display: grid;
		width: 100%;
	}

	:host([disabled]) {
		opacity: var(--primitives-opacity-disabled);
		pointer-events: none;
	}

	:host([size='md']),
	:host(:not([size])) {
		border-radius: var(--semantics-controls-md-corner-radius);
		padding-inline: var(--primitives-space-2);
	}

	:host([size='sm']) {
		border-radius: var(--semantics-controls-sm-corner-radius);
		padding-inline: var(--primitives-space-2);
	}


	/* # Focus */

	::slotted(ndd-segmented-control-item:focus-within) {
		position: relative;
		z-index: 1;
	}
`;
const segmentedControlItemStyles = css`
	/* # Host */

	:host {
		display: flex;
		min-width: 0;
		position: relative;
		--_segmented-control-md-inset-size: var(--primitives-space-4);
		--_segmented-control-md-gap-size: var(--primitives-space-4);
		--_segmented-control-md-item-icon-size: var(--primitives-space-24);
		--_segmented-control-sm-inset-size: var(--primitives-space-3);
		--_segmented-control-sm-gap-size: var(--primitives-space-2);
		--_segmented-control-sm-item-icon-size: var(--primitives-space-20);
		-webkit-tap-highlight-color: transparent;
	}

	:host([hidden]) {
		display: none;
	}


	/* # Input */

	.segmented-control__item-input {
		position: absolute;
		inset: 0;
		width: 100%;
		height: 100%;
		margin: 0;
		opacity: 0;
		z-index: 1;
	}


	/* # Label */

	.segmented-control__item-label {
		position: relative;
		display: flex;
		align-items: center;
		justify-content: center;
		width: 100%;
		box-sizing: border-box;
		color: var(--semantics-buttons-neutral-tinted-content-color);
		cursor: default;
	}

	:host([size='md']) .segmented-control__item-label,
	:host(:not([size])) .segmented-control__item-label {
		height: var(--semantics-controls-md-min-size);
		padding-inline: calc(var(--_segmented-control-md-inset-size) / 2 + var(--primitives-space-12));
		font: var(--semantics-buttons-md-font);
	}

	:host([size='sm']) .segmented-control__item-label {
		height: var(--semantics-controls-sm-min-size);
		padding-inline: calc(var(--_segmented-control-sm-inset-size) / 2 + var(--primitives-space-8));
		font: var(--semantics-buttons-sm-font);
	}

	:host([variant='icon'][size='md']) .segmented-control__item-label,
	:host([variant='icon']:not([size])) .segmented-control__item-label {
		padding-inline: calc((var(--semantics-controls-md-min-size) - var(--_segmented-control-md-item-icon-size) - var(--_segmented-control-md-inset-size) * 2 + var(--_segmented-control-md-gap-size)) / 2);
	}

	:host([variant='icon'][size='sm']) .segmented-control__item-label {
		padding-inline: calc((var(--semantics-controls-sm-min-size) - var(--_segmented-control-sm-item-icon-size) - var(--_segmented-control-sm-inset-size) * 2 + var(--_segmented-control-sm-gap-size)) / 2);
	}

	:host([selected]) .segmented-control__item-label {
		color: var(--semantics-buttons-neutral-tinted-is-selected-content-color);
	}

	:host([disabled]) .segmented-control__item-label {
		opacity: var(--primitives-opacity-disabled);
	}


	/* # Text */

	.segmented-control__item-text {
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
		z-index: 2;
		pointer-events: none;
	}


	/* # Icon slot */

	.segmented-control__item-icon {
		display: flex;
		flex-shrink: 0;
		align-items: center;
		justify-content: center;
		z-index: 2;
		pointer-events: none;
	}

	:host([size='md']) .segmented-control__item-icon,
	:host(:not([size])) .segmented-control__item-icon {
		width: var(--_segmented-control-md-item-icon-size);
		height: var(--_segmented-control-md-item-icon-size);
	}

	:host([size='sm']) .segmented-control__item-icon {
		width: var(--_segmented-control-sm-item-icon-size);
		height: var(--_segmented-control-sm-item-icon-size);
	}

	::slotted(ndd-icon) {
		display: block;
		width: 100%;
		height: 100%;
	}


	/* # Slot visibility */

	:host([variant='text']) .segmented-control__item-icon {
		display: none;
	}

	:host([variant='icon']) .segmented-control__item-text {
		display: none;
	}


	/* # Indicator */

	.segmented-control__item-label::before {
		content: '';
		position: absolute;
		inset: 0;
		pointer-events: none;
		background-color: transparent;
	}

	:host([size='md']) .segmented-control__item-label::before,
	:host(:not([size])) .segmented-control__item-label::before {
		inset-block: var(--_segmented-control-md-inset-size);
		inset-inline: calc(var(--_segmented-control-md-gap-size) / 2);
		border-radius: calc(var(--semantics-controls-md-corner-radius) - (var(--_segmented-control-md-inset-size) / 2));
	}

	:host([size='sm']) .segmented-control__item-label::before {
		inset-block: var(--_segmented-control-sm-inset-size);
		inset-inline: calc(var(--_segmented-control-sm-gap-size) / 2);
		border-radius: calc(var(--semantics-controls-sm-corner-radius) - (var(--_segmented-control-sm-inset-size) / 2));
	}

	:host([selected]) .segmented-control__item-label::before {
		background-color: var(--semantics-buttons-neutral-tinted-is-selected-background-color);
	}

	:host(:not([selected])) .segmented-control__item-label:hover::before {
		background-color: var(--semantics-buttons-neutral-tinted-is-hovered-background-color);
	}


	/* # Focus */

	.segmented-control__item-label:has(:focus-visible)::before {
		box-shadow: var(--semantics-focus-ring-box-shadow);
		outline: var(--semantics-focus-ring-outline);
	}
`;
function segmentedControlTemplate(component) {
  return html`<slot @slotchange=${component._onSlotChange}></slot>`;
}
function segmentedControlItemTemplate(component) {
  const isIcon = component.variant === "icon";
  const labelText = component.text || nothing;
  const label = html`
		<label class="segmented-control__item-label">
			<input class="segmented-control__item-input"
				type=${component.inputType}
				name=${component.groupName || nothing}
				value=${component.value}
				.checked=${component.selected}
				?disabled=${component.disabled}
				aria-label=${isIcon ? labelText : nothing}
				@change=${component._handleChange}
			>
			<span class="segmented-control__item-icon"
				aria-hidden=${component.variant === "icon" ? nothing : "true"}
			>
				${component.icon ? html`<ndd-icon name=${component.icon}></ndd-icon>` : html`<slot name="icon"></slot>`}
			</span>
			<span class="segmented-control__item-text"
				aria-hidden=${component.variant === "text" ? nothing : "true"}
			>
				${component.text}
			</span>
		</label>`;
  if (isIcon && labelText) {
    return html`<ndd-tooltip text=${labelText}>${label}</ndd-tooltip>`;
  }
  return label;
}
var __defProp$y = Object.defineProperty;
var __getOwnPropDesc$D = Object.getOwnPropertyDescriptor;
var __decorateClass$D = (decorators, target, key, kind) => {
  var result = kind > 1 ? void 0 : kind ? __getOwnPropDesc$D(target, key) : target;
  for (var i = decorators.length - 1, decorator; i >= 0; i--)
    if (decorator = decorators[i])
      result = (kind ? decorator(target, key, result) : decorator(result)) || result;
  if (kind && result) __defProp$y(target, key, result);
  return result;
};
let NDDSegmentedControlItem = class extends LitElement {
  constructor() {
    super(...arguments);
    this.value = "";
    this.selected = false;
    this.disabled = false;
    this.size = "md";
    this.variant = "text";
    this.inputType = "radio";
    this.groupName = "";
    this.text = "";
    this.icon = "";
  }
  _handleChange(e) {
    const input = e.target;
    this.dispatchEvent(new CustomEvent("item-change", {
      detail: { value: this.value, checked: input.checked },
      bubbles: true,
      composed: true
    }));
  }
  render() {
    return segmentedControlItemTemplate(this);
  }
};
NDDSegmentedControlItem.styles = segmentedControlItemStyles;
__decorateClass$D([
  property({ type: String })
], NDDSegmentedControlItem.prototype, "value", 2);
__decorateClass$D([
  property({ type: Boolean, reflect: true })
], NDDSegmentedControlItem.prototype, "selected", 2);
__decorateClass$D([
  property({ type: Boolean, reflect: true })
], NDDSegmentedControlItem.prototype, "disabled", 2);
__decorateClass$D([
  property({ type: String, reflect: true })
], NDDSegmentedControlItem.prototype, "size", 2);
__decorateClass$D([
  property({ type: String, reflect: true, attribute: "variant" })
], NDDSegmentedControlItem.prototype, "variant", 2);
__decorateClass$D([
  property({ type: String, reflect: true, attribute: "input-type" })
], NDDSegmentedControlItem.prototype, "inputType", 2);
__decorateClass$D([
  property({ type: String })
], NDDSegmentedControlItem.prototype, "groupName", 2);
__decorateClass$D([
  property({ type: String })
], NDDSegmentedControlItem.prototype, "text", 2);
__decorateClass$D([
  property({ type: String })
], NDDSegmentedControlItem.prototype, "icon", 2);
NDDSegmentedControlItem = __decorateClass$D([
  customElement("ndd-segmented-control-item")
], NDDSegmentedControlItem);
let NDDSegmentedControl = class extends LitElement {
  constructor() {
    super(...arguments);
    this.value = "";
    this.values = [];
    this.size = "md";
    this.type = "radio";
    this.variant = "text";
    this.disabled = false;
    this.fullWidth = false;
    this.name = "";
    this.accessibleLabel = "";
    this.accessibleLabelledBy = "";
    this._generatedName = "";
    this._handleItemChange = (e) => {
      e.stopPropagation();
      if (this.disabled) return;
      if (this.type === "checkbox") {
        const current = this.values;
        const updated = e.detail.checked ? [...current, e.detail.value] : current.filter((v) => v !== e.detail.value);
        this.values = updated;
        this._syncItems();
        this.dispatchEvent(new CustomEvent("change", {
          detail: { values: updated },
          bubbles: true,
          composed: true
        }));
      } else {
        if (e.detail.value === this.value) return;
        this.value = e.detail.value;
        this._syncItems();
        this.dispatchEvent(new CustomEvent("change", {
          detail: { value: this.value },
          bubbles: true,
          composed: true
        }));
      }
    };
    this._handleKeydown = (e) => {
      if (this.disabled || this.type === "checkbox") return;
      const items = this._getItems().filter((item) => !item.disabled);
      if (items.length === 0) return;
      const currentIndex = items.findIndex((item) => item.selected);
      let nextIndex = currentIndex;
      switch (e.key) {
        case "ArrowLeft":
        case "ArrowUp":
          e.preventDefault();
          nextIndex = currentIndex <= 0 ? items.length - 1 : currentIndex - 1;
          break;
        case "ArrowRight":
        case "ArrowDown":
          e.preventDefault();
          nextIndex = currentIndex >= items.length - 1 ? 0 : currentIndex + 1;
          break;
        case "Home":
          e.preventDefault();
          nextIndex = 0;
          break;
        case "End":
          e.preventDefault();
          nextIndex = items.length - 1;
          break;
        default:
          return;
      }
      if (nextIndex !== currentIndex && items[nextIndex]) {
        this.value = items[nextIndex].value;
        this._syncItems();
        items[nextIndex].shadowRoot?.querySelector("input")?.focus();
        this.dispatchEvent(new CustomEvent("change", {
          detail: { value: this.value },
          bubbles: true,
          composed: true
        }));
      }
    };
  }
  // — Lifecycle ——————————————————————————————————————————————————————————————
  connectedCallback() {
    super.connectedCallback();
    this.setAttribute("role", this.type === "checkbox" ? "group" : "radiogroup");
    if (this.accessibleLabel) this.setAttribute("aria-label", this.accessibleLabel);
    if (this.accessibleLabelledBy) this.setAttribute("aria-labelledby", this.accessibleLabelledBy);
    this.addEventListener("item-change", this._handleItemChange);
    this.addEventListener("keydown", this._handleKeydown);
  }
  disconnectedCallback() {
    super.disconnectedCallback();
    this.removeEventListener("item-change", this._handleItemChange);
    this.removeEventListener("keydown", this._handleKeydown);
  }
  firstUpdated() {
    this._syncItems();
    if (!this.accessibleLabel && !this.accessibleLabelledBy) {
      console.warn("<ndd-segmented-control>: No accessible name provided. Add an accessible-label or accessible-labelledby attribute for screen reader accessibility.");
    }
  }
  updated(changedProperties) {
    if (changedProperties.has("value") || changedProperties.has("values") || changedProperties.has("size") || changedProperties.has("disabled") || changedProperties.has("type") || changedProperties.has("variant") || changedProperties.has("name")) {
      this._syncItems();
    }
    if (changedProperties.has("type")) {
      this.setAttribute("role", this.type === "checkbox" ? "group" : "radiogroup");
    }
    if (changedProperties.has("accessibleLabel")) {
      if (this.accessibleLabel) {
        this.setAttribute("aria-label", this.accessibleLabel);
      } else {
        this.removeAttribute("aria-label");
      }
    }
    if (changedProperties.has("accessibleLabelledBy")) {
      if (this.accessibleLabelledBy) {
        this.setAttribute("aria-labelledby", this.accessibleLabelledBy);
      } else {
        this.removeAttribute("aria-labelledby");
      }
    }
  }
  // — Items ——————————————————————————————————————————————————————————————————
  _getItems() {
    const slot = this.shadowRoot?.querySelector("slot");
    if (!slot) return [];
    return slot.assignedElements().filter(
      (el) => el.tagName.toLowerCase() === "ndd-segmented-control-item"
    );
  }
  _getSelectedValues() {
    return this.type === "checkbox" ? this.values : this.value ? [this.value] : [];
  }
  _syncItems() {
    const items = this._getItems();
    const selectedValues = this._getSelectedValues();
    if (this.disabled) {
      items.forEach((item) => {
        if (!item.hasAttribute("disabled")) {
          item.setAttribute("group-disabled", "");
          item.disabled = true;
        }
      });
    } else {
      items.forEach((item) => {
        if (item.hasAttribute("group-disabled")) {
          item.removeAttribute("group-disabled");
          item.disabled = false;
        }
      });
    }
    items.forEach((item) => {
      item.size = this.size;
      item.inputType = this.type;
      item.variant = this.variant;
      item.groupName = this.name || this._autoName;
      item.selected = this.type === "checkbox" ? selectedValues.includes(item.value) : item.value === this.value;
    });
  }
  get _autoName() {
    if (!this._generatedName) {
      this._generatedName = `ndd-segmented-${NDDSegmentedControl._counter++}`;
    }
    return this._generatedName;
  }
  _onSlotChange() {
    this._syncItems();
  }
  render() {
    return segmentedControlTemplate(this);
  }
};
NDDSegmentedControl.styles = segmentedControlStyles;
NDDSegmentedControl._counter = 0;
__decorateClass$D([
  property({ type: String, reflect: true })
], NDDSegmentedControl.prototype, "value", 2);
__decorateClass$D([
  property({ type: Array, attribute: false })
], NDDSegmentedControl.prototype, "values", 2);
__decorateClass$D([
  property({ type: String, reflect: true })
], NDDSegmentedControl.prototype, "size", 2);
__decorateClass$D([
  property({ type: String, reflect: true })
], NDDSegmentedControl.prototype, "type", 2);
__decorateClass$D([
  property({ type: String, reflect: true, attribute: "variant" })
], NDDSegmentedControl.prototype, "variant", 2);
__decorateClass$D([
  property({ type: Boolean, reflect: true })
], NDDSegmentedControl.prototype, "disabled", 2);
__decorateClass$D([
  property({ type: Boolean, reflect: true, attribute: "full-width" })
], NDDSegmentedControl.prototype, "fullWidth", 2);
__decorateClass$D([
  property({ type: String })
], NDDSegmentedControl.prototype, "name", 2);
__decorateClass$D([
  property({ type: String, attribute: "accessible-label" })
], NDDSegmentedControl.prototype, "accessibleLabel", 2);
__decorateClass$D([
  property({ type: String, attribute: "accessible-labelledby" })
], NDDSegmentedControl.prototype, "accessibleLabelledBy", 2);
NDDSegmentedControl = __decorateClass$D([
  customElement("ndd-segmented-control")
], NDDSegmentedControl);
const toggleButtonStyles = css`


	/* # Host */

	:host {
		display: inline-block;
		-webkit-tap-highlight-color: transparent;
	}

	:host([hidden]) {
		display: none;
	}

	:host([disabled]) {
		opacity: var(--primitives-opacity-disabled);
		pointer-events: none;
	}


	/* # Base */

	.toggle-button {
		/* Reset */
		appearance: none;
		border: none;
		margin: 0;
		padding: 0;
		background: none;
		font: inherit;

		/* Layout */
		position: relative;
		box-sizing: border-box;
		display: inline-flex;
		align-items: center;
		justify-content: center;
		white-space: nowrap;
		text-decoration: none;

		/* Appearance */
		background-color: var(--semantics-buttons-neutral-tinted-background-color);
		color: var(--semantics-buttons-neutral-tinted-content-color);
	}

	/* ## Sizes */

	:host([size="xs"]) .toggle-button {
		min-height: var(--semantics-controls-xs-min-size);
		padding: var(--primitives-space-4) var(--primitives-space-6);
		font: var(--semantics-buttons-xs-font);
		border-radius: var(--semantics-controls-xs-corner-radius);
		gap: var(--primitives-space-2);
	}

	:host([size="sm"]) .toggle-button {
		min-height: var(--semantics-controls-sm-min-size);
		padding: var(--primitives-space-6) var(--primitives-space-8);
		font: var(--semantics-buttons-sm-font);
		border-radius: var(--semantics-controls-sm-corner-radius);
		gap: var(--primitives-space-2);
	}

	:host([size="md"]) .toggle-button,
	:host(:not([size])) .toggle-button {
		min-height: var(--semantics-controls-md-min-size);
		padding: var(--primitives-space-8) var(--primitives-space-14);
		font: var(--semantics-buttons-md-font);
		border-radius: var(--semantics-controls-md-corner-radius);
		gap: var(--primitives-space-4);
	}

	/* ## Icon-only sizes */

	:host([icon-only][size="xs"]) .toggle-button {
		width: var(--semantics-controls-xs-min-size);
		padding: 0;
	}

	:host([icon-only][size="sm"]) .toggle-button {
		width: var(--semantics-controls-sm-min-size);
		padding: 0;
	}

	:host([icon-only][size="md"]) .toggle-button,
	:host([icon-only]:not([size])) .toggle-button {
		width: var(--semantics-controls-md-min-size);
		padding: 0;
	}

	/* ## Hover */

	.toggle-button:hover,
	.toggle-button:has(.toggle-button__input:hover) {
		background-color: var(--semantics-buttons-neutral-tinted-is-hovered-background-color);
		color: var(--semantics-buttons-neutral-tinted-is-hovered-content-color);
	}

	/* ## Selected */

	:host([selected]) .toggle-button {
		background-color: var(--semantics-buttons-neutral-tinted-is-selected-background-color);
		color: var(--semantics-buttons-neutral-tinted-is-selected-content-color);
	}

	:host([selected]) .toggle-button:hover,
	:host([selected]) .toggle-button:has(.toggle-button__input:hover) {
		background-color: var(--semantics-buttons-neutral-tinted-is-selected-is-hovered-background-color);
		color: var(--semantics-buttons-neutral-tinted-is-selected-is-hovered-content-color);
	}

	/* ## Focus */

	.toggle-button:focus-visible,
	.toggle-button:has(.toggle-button__input:focus-visible) {
		box-shadow: var(--semantics-focus-ring-box-shadow);
		outline: var(--semantics-focus-ring-outline);
	}

	.toggle-button:focus:not(:focus-visible) {
		outline: none;
	}


	/* # Icon */

	/* Hide the original ndd-icon in the slot — it is re-rendered in the shadow DOM */
	::slotted(ndd-icon) {
		display: none;
	}

	.toggle-button__icon {
		display: block;
		flex-shrink: 0;
	}

	:host([size="md"]) .toggle-button__icon,
	:host(:not([size])) .toggle-button__icon {
		width: var(--primitives-space-20);
		height: var(--primitives-space-20);
	}

	:host([size="sm"]) .toggle-button__icon {
		width: var(--primitives-space-18);
		height: var(--primitives-space-18);
	}

	:host([size="xs"]) .toggle-button__icon {
		width: var(--primitives-space-16);
		height: var(--primitives-space-16);
	}


	/* # Input */

	.toggle-button__input {
		position: absolute;
		inset: 0;
		width: 100%;
		height: 100%;
		margin: 0;
		opacity: 0;
		z-index: 1;
	}
`;
function toggleButtonTemplate(component) {
  const label = component.accessibleLabel || nothing;
  const iconOnly = !!component.icon && !component.text;
  const tooltipText = iconOnly ? component.accessibleLabel || component.text : "";
  const icon = component.icon ? html`<ndd-icon class="toggle-button__icon" name=${component.icon}></ndd-icon>` : html`<slot name="icon" @slotchange=${component.requestUpdate}></slot>`;
  const textContent = component.text ? html`<span class="toggle-button__text">${component.text}</span>` : nothing;
  let result;
  if (component.type === "checkbox" || component.type === "radio") {
    result = html`
			<label class="toggle-button">
				<input
					class="toggle-button__input"
					type=${component.type}
					.checked=${component.selected}
					?disabled=${component.disabled}
					name=${component.name || nothing}
					value=${component.value}
					aria-label=${label}
					@change=${component._handleInputChange}
				>
				${icon}
				${textContent}
			</label>
		`;
  } else {
    result = html`
			<button
				class="toggle-button"
				type="button"
				aria-pressed=${component.selected}
				?disabled=${component.disabled}
				aria-label=${label}
				@click=${component._handleButtonClick}
			>
				${icon}
				${textContent}
			</button>
		`;
  }
  if (tooltipText) {
    return html`<ndd-tooltip text=${tooltipText}>${result}</ndd-tooltip>`;
  }
  return result;
}
var __defProp$x = Object.defineProperty;
var __getOwnPropDesc$C = Object.getOwnPropertyDescriptor;
var __decorateClass$C = (decorators, target, key, kind) => {
  var result = kind > 1 ? void 0 : kind ? __getOwnPropDesc$C(target, key) : target;
  for (var i = decorators.length - 1, decorator; i >= 0; i--)
    if (decorator = decorators[i])
      result = (kind ? decorator(target, key, result) : decorator(result)) || result;
  if (kind && result) __defProp$x(target, key, result);
  return result;
};
let NDDToggleButton = class extends LitElement {
  constructor() {
    super(...arguments);
    this.type = "button";
    this.size = "md";
    this.selected = false;
    this.disabled = false;
    this.value = "on";
    this.name = "";
    this.text = "";
    this.icon = "";
    this.accessibleLabel = "";
    this._warnedA11y = false;
  }
  /** Whether an icon is present via attribute or slot. */
  get _hasIcon() {
    if (this.icon) return true;
    const slot = this.shadowRoot?.querySelector('slot[name="icon"]');
    return (slot?.assignedElements().length ?? 0) > 0;
  }
  updated() {
    const iconOnly = this._hasIcon && !this.text;
    this.toggleAttribute("icon-only", iconOnly);
    const inaccessible = iconOnly && !this.accessibleLabel;
    if (inaccessible && !this._warnedA11y) {
      this._warnedA11y = true;
      console.warn("<ndd-toggle-button>: Icon-only usage requires an accessible-label attribute for accessibility.");
    } else if (!inaccessible) {
      this._warnedA11y = false;
    }
  }
  _handleButtonClick() {
    if (this.disabled) return;
    this._toggle();
  }
  _handleInputChange(e) {
    const input = e.target;
    this.selected = input.checked;
    this._dispatchChange();
  }
  _toggle() {
    this.selected = !this.selected;
    this._dispatchChange();
  }
  _dispatchChange() {
    this.dispatchEvent(new CustomEvent("change", {
      detail: { selected: this.selected, value: this.value },
      bubbles: true,
      composed: true
    }));
  }
  /**
   * Toggle selected state programmatically.
   * For type="radio", the button can only be selected, never deselected (native behavior).
   */
  toggle() {
    if (this.disabled) return;
    if (this.type === "radio" && this.selected) return;
    this._toggle();
  }
  render() {
    return toggleButtonTemplate(this);
  }
};
NDDToggleButton.styles = toggleButtonStyles;
__decorateClass$C([
  property({ type: String, reflect: true })
], NDDToggleButton.prototype, "type", 2);
__decorateClass$C([
  property({ type: String, reflect: true })
], NDDToggleButton.prototype, "size", 2);
__decorateClass$C([
  property({ type: Boolean, reflect: true })
], NDDToggleButton.prototype, "selected", 2);
__decorateClass$C([
  property({ type: Boolean, reflect: true })
], NDDToggleButton.prototype, "disabled", 2);
__decorateClass$C([
  property({ type: String })
], NDDToggleButton.prototype, "value", 2);
__decorateClass$C([
  property({ type: String })
], NDDToggleButton.prototype, "name", 2);
__decorateClass$C([
  property({ type: String })
], NDDToggleButton.prototype, "text", 2);
__decorateClass$C([
  property({ type: String })
], NDDToggleButton.prototype, "icon", 2);
__decorateClass$C([
  property({ type: String, attribute: "accessible-label" })
], NDDToggleButton.prototype, "accessibleLabel", 2);
NDDToggleButton = __decorateClass$C([
  customElement("ndd-toggle-button")
], NDDToggleButton);
const toggleButtonGroupStyles = css`


	/* # Host */

	:host {
		display: block;
	}

	:host([hidden]) {
		display: none;
	}


	/* # Group */

	.toggle-button-group {
		display: flex;
		flex-wrap: wrap;
		gap: var(--components-toggle-button-group-md-gap);
	}

	:host([size="sm"]) .toggle-button-group {
		gap: var(--components-toggle-button-group-sm-gap);
	}

	:host([size="xs"]) .toggle-button-group {
		gap: var(--components-toggle-button-group-xs-gap);
	}
`;
function toggleButtonGroupTemplate(component) {
  return html`
		<div class="toggle-button-group">
			<slot @slotchange=${component._onSlotChange}></slot>
		</div>
	`;
}
var __defProp$w = Object.defineProperty;
var __getOwnPropDesc$B = Object.getOwnPropertyDescriptor;
var __decorateClass$B = (decorators, target, key, kind) => {
  var result = kind > 1 ? void 0 : kind ? __getOwnPropDesc$B(target, key) : target;
  for (var i = decorators.length - 1, decorator; i >= 0; i--)
    if (decorator = decorators[i])
      result = (kind ? decorator(target, key, result) : decorator(result)) || result;
  if (kind && result) __defProp$w(target, key, result);
  return result;
};
let NDDToggleButtonGroup = class extends LitElement {
  constructor() {
    super(...arguments);
    this.type = "checkbox";
    this.name = "";
    this.size = "md";
    this.disabled = false;
    this.accessibleLabel = "";
    this.accessibleLabelledBy = "";
    this._handleChange = (e) => {
      if (this.type !== "radio") return;
      const changedButton = e.target;
      if (!changedButton.selected) return;
      this._getButtons().forEach((button) => {
        if (button !== changedButton) button.selected = false;
      });
    };
    this._handleKeyDown = (e) => {
      if (this.type !== "radio") return;
      if (!["ArrowDown", "ArrowUp", "ArrowRight", "ArrowLeft"].includes(e.key)) return;
      const buttons = this._getEnabledButtons();
      if (buttons.length === 0) return;
      const activeButton = buttons.find((b) => b.selected);
      const currentIndex = activeButton ? buttons.indexOf(activeButton) : -1;
      const isNext = e.key === "ArrowDown" || e.key === "ArrowRight";
      const nextIndex = isNext ? (currentIndex + 1) % buttons.length : currentIndex <= 0 ? buttons.length - 1 : currentIndex - 1;
      const nextButton = buttons[nextIndex];
      if (!nextButton) return;
      e.preventDefault();
      if (activeButton) activeButton.selected = false;
      nextButton.selected = true;
      const input = nextButton.shadowRoot?.querySelector(".toggle-button__input");
      input?.focus();
      nextButton.dispatchEvent(new CustomEvent("change", {
        detail: { selected: true, value: nextButton.value },
        bubbles: true,
        composed: true
      }));
    };
    this._onSlotChange = () => {
      this._syncButtons();
    };
  }
  connectedCallback() {
    super.connectedCallback();
    this._syncRole();
    this.addEventListener("change", this._handleChange);
    this.addEventListener("keydown", this._handleKeyDown);
  }
  disconnectedCallback() {
    super.disconnectedCallback();
    this.removeEventListener("change", this._handleChange);
    this.removeEventListener("keydown", this._handleKeyDown);
  }
  _syncRole() {
    this.setAttribute("role", this.type === "radio" ? "radiogroup" : "group");
  }
  firstUpdated() {
  }
  updated(changed) {
    if (changed.has("type") || changed.has("name") || changed.has("size") || changed.has("disabled")) {
      this._syncButtons();
    }
    if (changed.has("type")) {
      this._syncRole();
    }
    if (changed.has("accessibleLabel")) {
      if (this.accessibleLabel) {
        this.setAttribute("aria-label", this.accessibleLabel);
      } else {
        this.removeAttribute("aria-label");
      }
    }
    if (changed.has("accessibleLabelledBy")) {
      if (this.accessibleLabelledBy) {
        this.setAttribute("aria-labelledby", this.accessibleLabelledBy);
      } else {
        this.removeAttribute("aria-labelledby");
      }
    }
  }
  _getButtons() {
    return Array.from(this.querySelectorAll("ndd-toggle-button"));
  }
  _getEnabledButtons() {
    return this._getButtons().filter((b) => !b.disabled);
  }
  _syncButtons() {
    this._getButtons().forEach((button) => {
      button.type = this.type;
      button.size = this.size;
      if (this.type !== "button") {
        button.name = this.name;
      }
      if (this.disabled) {
        if (!button.hasAttribute("disabled")) {
          button.setAttribute("group-disabled", "");
          button.disabled = true;
        }
      } else if (button.hasAttribute("group-disabled")) {
        button.removeAttribute("group-disabled");
        button.disabled = false;
      }
    });
  }
  render() {
    return toggleButtonGroupTemplate(this);
  }
};
NDDToggleButtonGroup.styles = toggleButtonGroupStyles;
__decorateClass$B([
  property({ type: String, reflect: true })
], NDDToggleButtonGroup.prototype, "type", 2);
__decorateClass$B([
  property({ type: String })
], NDDToggleButtonGroup.prototype, "name", 2);
__decorateClass$B([
  property({ type: String, reflect: true })
], NDDToggleButtonGroup.prototype, "size", 2);
__decorateClass$B([
  property({ type: Boolean, reflect: true })
], NDDToggleButtonGroup.prototype, "disabled", 2);
__decorateClass$B([
  property({ type: String, attribute: "accessible-label" })
], NDDToggleButtonGroup.prototype, "accessibleLabel", 2);
__decorateClass$B([
  property({ type: String, attribute: "accessible-labelledby" })
], NDDToggleButtonGroup.prototype, "accessibleLabelledBy", 2);
NDDToggleButtonGroup = __decorateClass$B([
  customElement("ndd-toggle-button-group")
], NDDToggleButtonGroup);
const tokenStyles = css`


	/* # Host */

	:host {
		display: inline-block;
		-webkit-tap-highlight-color: transparent;
	}

	:host([hidden]) {
		display: none;
	}

	:host([disabled]) {
		opacity: var(--primitives-opacity-disabled);
		pointer-events: none;
	}


	/* # Base */

	.token {
		/* Reset (for menu button) */
		appearance: none;
		border: none;
		margin: 0;
		background: none;
		font: inherit;

		/* Layout */
		display: inline-flex;
		align-items: center;
		box-sizing: border-box;
		height: var(--semantics-controls-sm-min-size);
		padding: 0 var(--primitives-space-6);

		/* Appearance */
		border-radius: var(--semantics-controls-sm-corner-radius);
		background-color: var(--semantics-buttons-neutral-tinted-background-color);
		color: var(--semantics-buttons-neutral-tinted-content-color);
		font: var(--semantics-buttons-sm-font);

		/* Animation */
		transition: background-color 0.15s ease-out;
	}

	@media (prefers-reduced-motion: reduce) {
		.token {
			transition: none;
		}
	}


	/* # Text */

	.token__text {
		display: flex;
		align-items: center;
		padding: 0 var(--primitives-space-2);
	}


	/* # Icon */

	.token__icon {
		display: block;
		flex-shrink: 0;
		width: var(--primitives-space-16);
		height: var(--primitives-space-16);
	}


	/* # States */

	/* ## Hover — menu */

	:host([control="menu"]) .token:hover:not(:disabled) {
		background-color: var(--semantics-buttons-neutral-tinted-is-hovered-background-color);
		color: var(--semantics-buttons-neutral-tinted-is-hovered-content-color);
	}

	/* ## Open — menu */

	:host([open]) .token {
		background-color: var(--semantics-buttons-neutral-tinted-is-active-background-color);
		color: var(--semantics-buttons-neutral-tinted-is-active-content-color);
	}

	:host([open]) .token:hover:not(:disabled) {
		background-color: var(--semantics-buttons-neutral-tinted-is-active-background-color);
		color: var(--semantics-buttons-neutral-tinted-is-active-content-color);
	}

	/* ## Focus — menu */

	:host([control="menu"]) .token:focus-visible {
		box-shadow: var(--semantics-focus-ring-box-shadow);
		outline: var(--semantics-focus-ring-outline);
	}

	:host([control="menu"]) .token:focus:not(:focus-visible) {
		outline: none;
	}


	/* # Dismiss — padding compensation */

	/* Remove right padding so the ndd-icon-button flush-fits the token edge */
	:host([control="dismiss"]) .token {
		padding-right: 0;
	}

	/* # Accessibility */

	@media (forced-colors: active) {
		.token {
			border: 1px solid CanvasText;
		}

		:host([control="menu"]) .token:focus-visible,
		.token__dismiss:focus-visible {
			outline: 2px solid CanvasText;
			outline-offset: 2px;
		}
	}
`;
function tokenTemplate(component) {
  if (component.control === "menu") {
    return html`
			<button
				class="token"
				type="button"
				?disabled=${component.disabled}
				aria-expanded=${component.open}
				aria-controls=${component.controls || nothing}
				@click=${component._handleMenuClick}
			>
				<span class="token__text"><slot></slot></span>
				<ndd-icon class="token__icon" name="chevron-down-small"></ndd-icon>
			</button>
		`;
  }
  return html`
		<div class="token">
			<span class="token__text"><slot></slot></span>
			${component.control === "dismiss" ? html`
				<div class="token__dismiss-action">
					<ndd-icon-button
						size="sm"
						variant="neutral-tinted"
						icon="dismiss-small"
						text=${component.dismissText}
						accessible-label=${component.dismissText}
						?disabled=${component.disabled}
						@click=${component._handleDismiss}
					></ndd-icon-button>
				</div>
			` : nothing}
		</div>
	`;
}
var __defProp$v = Object.defineProperty;
var __getOwnPropDesc$A = Object.getOwnPropertyDescriptor;
var __decorateClass$A = (decorators, target, key, kind) => {
  var result = kind > 1 ? void 0 : kind ? __getOwnPropDesc$A(target, key) : target;
  for (var i = decorators.length - 1, decorator; i >= 0; i--)
    if (decorator = decorators[i])
      result = (kind ? decorator(target, key, result) : decorator(result)) || result;
  if (kind && result) __defProp$v(target, key, result);
  return result;
};
let NDDToken = class extends LitElement {
  constructor() {
    super(...arguments);
    this.control = "none";
    this.open = false;
    this.disabled = false;
    this.dismissText = "Verwijder";
    this.controls = "";
  }
  _handleDismiss(e) {
    e.stopPropagation();
    if (this.disabled) return;
    this.dispatchEvent(new CustomEvent("dismiss", {
      bubbles: true,
      composed: true
    }));
  }
  _handleMenuClick() {
    if (this.disabled) return;
    this.open = !this.open;
    this.dispatchEvent(new CustomEvent("toggle", {
      detail: { open: this.open },
      bubbles: true,
      composed: true
    }));
  }
  render() {
    return tokenTemplate(this);
  }
};
NDDToken.styles = tokenStyles;
__decorateClass$A([
  property({ type: String, reflect: true })
], NDDToken.prototype, "control", 2);
__decorateClass$A([
  property({ type: Boolean, reflect: true })
], NDDToken.prototype, "open", 2);
__decorateClass$A([
  property({ type: Boolean, reflect: true })
], NDDToken.prototype, "disabled", 2);
__decorateClass$A([
  property({ type: String, attribute: "dismiss-text" })
], NDDToken.prototype, "dismissText", 2);
__decorateClass$A([
  property({ type: String, reflect: true })
], NDDToken.prototype, "controls", 2);
NDDToken = __decorateClass$A([
  customElement("ndd-token")
], NDDToken);
const appViewStyles = css`
	:host {
		--context-parent-background-color: var(--semantics-surfaces-background-color);
		--_background-color: var(--context-parent-background-color);

		display: flex;
		width: 100%;
		height: 100%;
		background-color: var(--_background-color);
	}


	:host([background="tinted"]) {
		--context-parent-background-color: var(--semantics-surfaces-tinted-background-color);
		--_background-color: var(--semantics-surfaces-tinted-background-color);
	}

	:host([hidden]) {
		display: none;
	}


	/* # App view */

	.app-view {
		display: flex;
		flex-direction: column;
		flex: 1;
		min-height: 0;
		min-width: 0;
		overflow: hidden;
	}

	::slotted(*) {
		flex: 1;
		min-height: 0;
	}
`;
function appViewTemplate(_component) {
  return html`
		<div class="app-view">
			<slot></slot>
		</div>
	`;
}
var __defProp$u = Object.defineProperty;
var __getOwnPropDesc$z = Object.getOwnPropertyDescriptor;
var __decorateClass$z = (decorators, target, key, kind) => {
  var result = kind > 1 ? void 0 : kind ? __getOwnPropDesc$z(target, key) : target;
  for (var i = decorators.length - 1, decorator; i >= 0; i--)
    if (decorator = decorators[i])
      result = (kind ? decorator(target, key, result) : decorator(result)) || result;
  if (kind && result) __defProp$u(target, key, result);
  return result;
};
let NDDAppView = class extends LitElement {
  constructor() {
    super(...arguments);
    this.background = "default";
  }
  render() {
    return appViewTemplate();
  }
};
NDDAppView.styles = appViewStyles;
__decorateClass$z([
  property({ type: String, reflect: true })
], NDDAppView.prototype, "background", 2);
NDDAppView = __decorateClass$z([
  customElement("ndd-app-view")
], NDDAppView);
const smMax$4 = unsafeCSS(breakpoints.smMax);
const barSplitViewStyles = css`
	:host {
		display: flex;
		flex-direction: column;
		width: 100%;
		height: 100%;
		background-color: var(--_background-color);

		--_background-color: var(--context-parent-background-color, var(--semantics-surfaces-background-color));
		--context-bar-split-view-top-bars-height: 0px;
		--context-bar-split-view-bottom-bars-height: 0px;
	}

	:host([background="default"]) {
		--context-parent-background-color: var(--semantics-surfaces-background-color);
		--_background-color: var(--context-parent-background-color);
	}

	:host([background="tinted"]) {
		--context-parent-background-color: var(--semantics-surfaces-tinted-background-color);
		--_background-color: var(--context-parent-background-color);
	}

	:host([hidden]) {
		display: none;
	}


	/* # Bar split view */

	.bar-split-view {
		display: flex;
		flex-direction: column;
		flex: 1;
		min-height: 0;
		min-width: 0;
		position: relative;
	}


	/* # Bar */

	.bar-split-view__bar {
		display: flex;
		flex-direction: column;
		flex-shrink: 0;
		min-width: 0;
		overflow: hidden;
		container-type: inline-size;
		container-name: layout-area;

		@media (max-width: ${smMax$4}) {
			position: absolute;
			left: 0;
			right: 0;
			z-index: 2;
		}
	}


	/* # Divider */

	.bar-split-view__divider {
		flex-shrink: 0;
	}


	/* # Main */

	.bar-split-view__main {
		display: flex;
		flex-direction: column;
		flex: 1;
		min-height: 0;
		min-width: 0;
		overflow: hidden;
		container-type: inline-size;
		container-name: layout-area;

		@media (max-width: ${smMax$4}) {
			&::before {
				content: '';
				position: absolute;
				top: 0;
				left: 0;
				right: 0;
				z-index: 1;
				height: calc(var(--context-bar-split-view-top-bars-height) + var(--primitives-space-32));
				background: linear-gradient(
					to bottom,
					color-mix(in srgb, var(--_background-color) 95%, transparent) var(--context-bar-split-view-top-bars-height),
					transparent);
				pointer-events: none;
			}

			&::after {
				content: '';
				position: absolute;
				bottom: 0;
				left: 0;
				right: 0;
				z-index: 1;
				height: calc(var(--context-bar-split-view-bottom-bars-height) + var(--primitives-space-32));
				background: linear-gradient(
					to top,
					color-mix(in srgb, var(--_background-color) 95%, transparent) var(--context-bar-split-view-bottom-bars-height),
					transparent);
				pointer-events: none;
			}
		}
	}


	/* # Slotted */

	::slotted(*) {
		flex: 1;
		min-height: 0;
	}
`;
const splitViewDividerStyles = css`
	:host {
		display: flex;
		flex-shrink: 0;
		align-self: stretch;
	}

	:host([hidden]) {
		display: none;
	}


	/* # Divider */

	.split-view-divider {
		display: flex;
		justify-content: center;
		align-items: center;
		position: relative;
		background-color: var(--semantics-dividers-color);
	}


	/* # Drag handle */

	.split-view-divider__drag-handle {
		background-color: var(--semantics-content-secondary-color);
		border-radius: 9999px;
		position: absolute;
	}


	/* # Vertical */

	:host([orientation='vertical']) .split-view-divider {
		width: var(--semantics-dividers-thickness);
		height: 100%;
	}

	:host([orientation='vertical'][has-drag-handle]) .split-view-divider {
		width: 12px;
	}

	:host([orientation='vertical']) .split-view-divider__drag-handle {
		width: 4px;
		height: 40px;
	}


	/* # Horizontal */

	:host([orientation='horizontal']) .split-view-divider,
	:host(:not([orientation])) .split-view-divider {
		width: 100%;
		height: var(--semantics-dividers-thickness);
	}

	:host([orientation='horizontal'][has-drag-handle]) .split-view-divider,
	:host(:not([orientation])[has-drag-handle]) .split-view-divider {
		height: 12px;
	}

	:host([orientation='horizontal']) .split-view-divider__drag-handle,
	:host(:not([orientation])) .split-view-divider__drag-handle {
		width: 40px;
		height: 4px;
	}


	/* # High contrast */

	@media (forced-colors: active) {
		.split-view-divider {
			background-color: CanvasText;
		}
	}
`;
function splitViewDividerTemplate(component) {
  return html`
		<div
			class="split-view-divider"
			role="separator"
			aria-orientation=${component.orientation}
		>
			${component.hasDragHandle ? html`<div class="split-view-divider__drag-handle"></div>` : nothing}
		</div>
	`;
}
var __defProp$t = Object.defineProperty;
var __getOwnPropDesc$y = Object.getOwnPropertyDescriptor;
var __decorateClass$y = (decorators, target, key, kind) => {
  var result = kind > 1 ? void 0 : kind ? __getOwnPropDesc$y(target, key) : target;
  for (var i = decorators.length - 1, decorator; i >= 0; i--)
    if (decorator = decorators[i])
      result = (kind ? decorator(target, key, result) : decorator(result)) || result;
  if (kind && result) __defProp$t(target, key, result);
  return result;
};
let NDDSplitViewDivider = class extends LitElement {
  constructor() {
    super(...arguments);
    this.orientation = "vertical";
    this.hasDragHandle = false;
  }
  render() {
    return splitViewDividerTemplate(this);
  }
};
NDDSplitViewDivider.styles = splitViewDividerStyles;
__decorateClass$y([
  property({ type: String, reflect: true })
], NDDSplitViewDivider.prototype, "orientation", 2);
__decorateClass$y([
  property({ type: Boolean, reflect: true, attribute: "has-drag-handle" })
], NDDSplitViewDivider.prototype, "hasDragHandle", 2);
NDDSplitViewDivider = __decorateClass$y([
  customElement("ndd-split-view-divider")
], NDDSplitViewDivider);
function barSplitViewTemplate(component) {
  const sorted = component._getSortedChildren();
  const isSm = component._currentBreakpoint === "sm";
  return html`
		<div class="bar-split-view">
			${sorted.map((el, index) => {
    const isMain = el.slot === "main";
    const isLast = index === sorted.length - 1;
    const barStyles = !isMain && isSm ? component._smTopBars.has(el) ? { top: `${component._smOffsets.get(el) ?? 0}px` } : { bottom: `${component._smOffsets.get(el) ?? 0}px` } : {};
    return html`
					<div class=${classMap({ "bar-split-view__main": isMain, "bar-split-view__bar": !isMain })}
						style=${styleMap(barStyles)}>
						<slot name=${el.slot}></slot>
					</div>
					${!isSm && !isLast ? html`
						<div class="bar-split-view__divider">
							<ndd-split-view-divider orientation="horizontal"></ndd-split-view-divider>
						</div>
					` : nothing}
				`;
  })}
			${!sorted.some((el) => el.slot === "main") ? html`
				<div class="bar-split-view__main">
					<slot name="main"></slot>
				</div>
			` : nothing}
		</div>
	`;
}
var __defProp$s = Object.defineProperty;
var __getOwnPropDesc$x = Object.getOwnPropertyDescriptor;
var __decorateClass$x = (decorators, target, key, kind) => {
  var result = kind > 1 ? void 0 : kind ? __getOwnPropDesc$x(target, key) : target;
  for (var i = decorators.length - 1, decorator; i >= 0; i--)
    if (decorator = decorators[i])
      result = (kind ? decorator(target, key, result) : decorator(result)) || result;
  if (kind && result) __defProp$s(target, key, result);
  return result;
};
const smMaxPx = parseInt(breakpoints.smMax);
const mdMaxPx = parseInt(breakpoints.mdMax);
let NDDBarSplitView = class extends LitElement {
  constructor() {
    super(...arguments);
    this.background = "inherit";
    this._currentBreakpoint = null;
    this._smTopBars = /* @__PURE__ */ new Set();
    this._smOffsets = /* @__PURE__ */ new Map();
    this._observer = null;
    this._resizeObserver = null;
    this._childResizeObserver = null;
  }
  connectedCallback() {
    super.connectedCallback();
    this._currentBreakpoint = this._getBreakpoint(this.getBoundingClientRect().width);
    this._observer = new MutationObserver(() => {
      this._observeChildren();
      this._updateLayout();
      this.requestUpdate();
    });
    this._observer.observe(this, { childList: true, attributes: true, attributeFilter: ["above", "below", "only", "sm-order", "md-order", "lg-order"], subtree: false });
    this._resizeObserver = new ResizeObserver(() => {
      const bp = this._getBreakpoint(this.getBoundingClientRect().width);
      if (bp !== this._currentBreakpoint) {
        this._currentBreakpoint = bp;
        this.requestUpdate();
      }
      this._updateLayout();
    });
    this._resizeObserver.observe(this);
    this._childResizeObserver = new ResizeObserver(() => this._updateLayout());
    this._observeChildren();
  }
  disconnectedCallback() {
    super.disconnectedCallback();
    this._observer?.disconnect();
    this._observer = null;
    this._resizeObserver?.disconnect();
    this._resizeObserver = null;
    this._childResizeObserver?.disconnect();
    this._childResizeObserver = null;
  }
  _getBreakpoint(width) {
    if (width <= smMaxPx) return "sm";
    if (width <= mdMaxPx) return "md";
    return "lg";
  }
  _isChildVisible(el) {
    if (this._currentBreakpoint === null) return true;
    const bp = this._currentBreakpoint;
    const order = ["sm", "md", "lg"];
    const bpIndex = order.indexOf(bp);
    const only = el.getAttribute("only");
    if (only) return bp === only;
    const above = el.getAttribute("above");
    if (above) return bpIndex >= order.indexOf(above);
    const below = el.getAttribute("below");
    if (below) return bpIndex <= order.indexOf(below);
    return true;
  }
  _getSortedChildren() {
    const all = Array.from(this.children).filter((el) => {
      if (!el.slot) {
        console.warn('<ndd-bar-split-view>: every child must have a slot attribute (e.g. slot="toolbar", slot="status-bar", or slot="bar-1" if no meaningful name applies). Child without slot attribute is ignored:', el);
        return false;
      }
      return this._isChildVisible(el);
    });
    if (this._currentBreakpoint === null) return all;
    const attr = `${this._currentBreakpoint}-order`;
    return [...all].sort((a, b) => {
      const aVal = a.hasAttribute(attr) ? parseInt(a.getAttribute(attr)) : all.indexOf(a);
      const bVal = b.hasAttribute(attr) ? parseInt(b.getAttribute(attr)) : all.indexOf(b);
      return aVal - bVal;
    });
  }
  _observeChildren() {
    this._childResizeObserver?.disconnect();
    for (const child of Array.from(this.children)) {
      this._childResizeObserver?.observe(child);
    }
  }
  _updateLayout() {
    const width = this.getBoundingClientRect().width;
    if (width > smMaxPx) {
      this.style.removeProperty("--context-bar-split-view-top-bars-height");
      this.style.removeProperty("--context-bar-split-view-bottom-bars-height");
      this._smTopBars = /* @__PURE__ */ new Set();
      this._smOffsets = /* @__PURE__ */ new Map();
      return;
    }
    const sorted = this._getSortedChildren();
    const mainIndex = sorted.findIndex((el) => el.slot === "main");
    const topBars = mainIndex > 0 ? sorted.slice(0, mainIndex) : [];
    const bottomBars = mainIndex >= 0 ? sorted.slice(mainIndex + 1) : sorted;
    this._smTopBars = new Set(topBars);
    const newOffsets = /* @__PURE__ */ new Map();
    let topOffset = 0;
    for (const el of topBars) {
      newOffsets.set(el, topOffset);
      topOffset += el.getBoundingClientRect().height;
    }
    let bottomOffset = 0;
    for (const el of [...bottomBars].reverse()) {
      newOffsets.set(el, bottomOffset);
      bottomOffset += el.getBoundingClientRect().height;
    }
    this._smOffsets = newOffsets;
    const prevTop = this.style.getPropertyValue("--context-bar-split-view-top-bars-height");
    const prevBottom = this.style.getPropertyValue("--context-bar-split-view-bottom-bars-height");
    const nextTop = `${topOffset}px`;
    const nextBottom = `${bottomOffset}px`;
    if (prevTop !== nextTop || prevBottom !== nextBottom) {
      this.style.setProperty("--context-bar-split-view-top-bars-height", nextTop);
      this.style.setProperty("--context-bar-split-view-bottom-bars-height", nextBottom);
      this.requestUpdate();
    }
  }
  render() {
    return barSplitViewTemplate(this);
  }
};
NDDBarSplitView.styles = barSplitViewStyles;
__decorateClass$x([
  property({ type: String, reflect: true })
], NDDBarSplitView.prototype, "background", 2);
__decorateClass$x([
  state()
], NDDBarSplitView.prototype, "_currentBreakpoint", 2);
NDDBarSplitView = __decorateClass$x([
  customElement("ndd-bar-split-view")
], NDDBarSplitView);
const smMax$3 = unsafeCSS(breakpoints.smMax);
const lgMin$3 = unsafeCSS(breakpoints.lgMin);
const navigationSplitViewStyles = css`
	:host {
		display: flex;
		width: 100%;
		height: 100%;
		background-color: var(--_background-color);

		--_sidebar-min-width: var(--primitives-area-320); /* Pane min-width — read by JS via getComputedStyle in firstUpdated */
		--_secondary-sidebar-min-width: var(--primitives-area-320); /* Pane min-width — read by JS via getComputedStyle in firstUpdated */
		--_main-min-width: var(--primitives-area-480); /* Pane min-width — read by JS via getComputedStyle in firstUpdated */
		--_inspector-min-width: var(--primitives-area-320); /* Pane min-width — read by JS via getComputedStyle in firstUpdated */
		--_background-color: var(--context-parent-background-color, var(--semantics-surfaces-background-color));
	}

	:host([background="default"]) {
		--context-parent-background-color: var(--semantics-surfaces-background-color);
		--_background-color: var(--context-parent-background-color);
	}

	:host([background="tinted"]) {
		--context-parent-background-color: var(--semantics-surfaces-tinted-background-color);
		--_background-color: var(--context-parent-background-color);
	}


	/* # Split view */

	.navigation-split-view {
		display: flex;
		flex-direction: row;
		flex: 1;
		min-height: 0;
		min-width: 0;
		overflow: hidden;
	}


	/* # Sidebar */

	.navigation-split-view__sidebar-pane {
		display: flex;
		flex-direction: column;
		flex-shrink: 0;
		min-height: 0;
		min-width: var(--_sidebar-min-width);
		overflow: hidden;
		container-type: inline-size;
		container-name: layout-area;
	}


	/* # Secondary sidebar */

	.navigation-split-view__secondary-sidebar-pane {
		display: flex;
		flex-direction: column;
		flex-shrink: 0;
		min-height: 0;
		min-width: var(--_secondary-sidebar-min-width);
		overflow: hidden;
		container-type: inline-size;
		container-name: layout-area;
	}


	/* # Main */

	.navigation-split-view__main-pane {
		display: flex;
		flex-direction: column;
		flex: 1;
		min-height: 0;
		min-width: var(--_main-min-width);
		overflow: hidden;
		container-type: inline-size;
		container-name: layout-area;
	}


	/* # Full-stack: single pane fills available space, no minimum */

	:host(.full-stack) .navigation-split-view__sidebar-pane,
	:host(.full-stack) .navigation-split-view__secondary-sidebar-pane,
	:host(.full-stack) .navigation-split-view__main-pane {
		min-width: 0;
	}

	/* # Sidebar — inline pane suppresses dismiss button */

	.navigation-split-view__sidebar-pane,
	.navigation-split-view__secondary-sidebar-pane {
		--context-dismiss-button-display: none;
	}

	.navigation-split-view__inspector-pane {
		display: flex;
		flex-direction: column;
		flex-shrink: 0;
		min-height: 0;
		min-width: var(--_inspector-min-width);
		overflow: hidden;
		container-type: inline-size;
		container-name: layout-area;

		/* Suppress dismiss button — inspector is always dismissable as a sheet, not inline */
		--context-dismiss-button-display: none;
	}


	/* # Inspector — sheet (dialog) */

	@keyframes navigation-split-view-inspector-slide-in {
		from { transform: translateX(100%); }
		to { transform: translateX(0); }
	}

	@keyframes navigation-split-view-inspector-slide-out {
		from { transform: translateX(0); }
		to { transform: translateX(100%); }
	}

	.navigation-split-view__inspector-sheet {
		display: flex;
		flex-direction: column;
		border: none;
		padding: 0;
		margin: 0;
		background: var(--semantics-surfaces-background-color);
		box-shadow: var(--components-sheet-box-shadow);
		overflow: hidden;
		position: fixed;
		inset: var(--components-sheet-side-inset) var(--components-sheet-side-inset) var(--components-sheet-side-inset) auto;
		width: var(--components-sheet-side-md-width);
		height: calc(100dvh - var(--components-sheet-side-inset) * 2);
		border-radius: var(--semantics-overlays-corner-radius);

		@media (min-width: ${lgMin$3}) {
			width: var(--components-sheet-side-lg-width);
		}

		&:focus-visible {
			box-shadow: var(--semantics-focus-ring-box-shadow), var(--components-sheet-box-shadow);
			outline: var(--semantics-focus-ring-outline);
		}

		&:not([open]) {
			display: none;
		}

		&::backdrop {
			background: var(--semantics-overlays-backdrop-color);
		}

		&[open] {
			animation: navigation-split-view-inspector-slide-in var(--components-sheet-side-animation-duration) ease both;
		}

		&.is-closing {
			animation: navigation-split-view-inspector-slide-out var(--components-sheet-side-animation-duration) ease both;
		}
	}

	.navigation-split-view__inspector-sheet-body {
		display: flex;
		flex-direction: column;
		flex-grow: 1;
		min-height: 0;
		width: 100%;
	}


	/* # Sidebar — sheet (dialog) */

	@keyframes navigation-split-view-sidebar-slide-in {
		from { transform: translateX(-100%); }
		to { transform: translateX(0); }
	}

	@keyframes navigation-split-view-sidebar-slide-out {
		from { transform: translateX(0); }
		to { transform: translateX(-100%); }
	}

	.navigation-split-view__sidebar-sheet {
		display: flex;
		flex-direction: column;
		border: none;
		padding: 0;
		margin: 0;
		background: var(--semantics-surfaces-background-color);
		box-shadow: var(--components-sheet-box-shadow);
		overflow: hidden;
		position: fixed;
		inset: var(--components-sheet-side-inset) auto var(--components-sheet-side-inset) var(--components-sheet-side-inset);
		width: var(--components-sheet-side-md-width);
		height: calc(100dvh - var(--components-sheet-side-inset) * 2);
		border-radius: var(--semantics-overlays-corner-radius);

		@media (min-width: ${lgMin$3}) {
			width: var(--components-sheet-side-lg-width);
		}

		&:focus-visible {
			box-shadow: var(--semantics-focus-ring-box-shadow), var(--components-sheet-box-shadow);
			outline: var(--semantics-focus-ring-outline);
		}

		&:not([open]) {
			display: none;
		}

		&::backdrop {
			background: var(--semantics-overlays-backdrop-color);
		}

		&[open] {
			animation: navigation-split-view-sidebar-slide-in var(--components-sheet-side-animation-duration) ease both;
		}

		&.is-closing {
			animation: navigation-split-view-sidebar-slide-out var(--components-sheet-side-animation-duration) ease both;
		}
	}

	.navigation-split-view__sidebar-sheet-body {
		display: flex;
		flex-direction: column;
		flex-grow: 1;
		min-height: 0;
		width: 100%;

		/* Show dismiss button inside sidebar sheet */
		--context-dismiss-button-display: block;
	}


	/* # Responsive: sm viewport — sheets become bottom sheets */

	@keyframes navigation-split-view-slide-in-bottom {
		from { transform: translateY(100%); }
		to { transform: translateY(0); }
	}

	@keyframes navigation-split-view-slide-out-bottom {
		from { transform: translateY(0); }
		to { transform: translateY(100%); }
	}

	@media (max-width: ${smMax$3}) {
		.navigation-split-view__inspector-sheet {
			inset: auto 0 0 0;
			width: 100%;
			max-width: 100%;
			height: auto;
			max-height: calc(100dvh - var(--components-sheet-bottom-top-inset));
			border-radius: var(--semantics-overlays-corner-radius) var(--semantics-overlays-corner-radius) 0 0;

			&[open] {
				animation: navigation-split-view-slide-in-bottom var(--components-sheet-bottom-animation-duration) ease both;
			}

			&.is-closing {
				animation: navigation-split-view-slide-out-bottom var(--components-sheet-bottom-animation-duration) ease both;
			}
		}

		.navigation-split-view__sidebar-sheet {
			inset: auto 0 0 0;
			width: 100%;
			max-width: 100%;
			height: auto;
			max-height: calc(100dvh - var(--components-sheet-bottom-top-inset));
			border-radius: var(--semantics-overlays-corner-radius) var(--semantics-overlays-corner-radius) 0 0;

			&[open] {
				animation: navigation-split-view-slide-in-bottom var(--components-sheet-bottom-animation-duration) ease both;
			}

			&.is-closing {
				animation: navigation-split-view-slide-out-bottom var(--components-sheet-bottom-animation-duration) ease both;
			}
		}
	}


	/* # Reduced motion */

	@media (prefers-reduced-motion: reduce) {
		.navigation-split-view__inspector-sheet[open],
		.navigation-split-view__inspector-sheet.is-closing,
		.navigation-split-view__sidebar-sheet[open],
		.navigation-split-view__sidebar-sheet.is-closing {
			animation: none;
		}
	}


	/* # Slotted */

	::slotted(*) {
		flex: 1;
		min-height: 0;
	}
`;
function navigationSplitViewTemplate(component) {
  return html`
		<div class="navigation-split-view">
			${component._showSidebar ? html`
				<div class="navigation-split-view__sidebar-pane">
					<slot name="sidebar"></slot>
				</div>
				<ndd-split-view-divider orientation="vertical"></ndd-split-view-divider>
			` : nothing}
			${component._showSecondarySidebar ? html`
				<div class="navigation-split-view__secondary-sidebar-pane">
					<slot name="secondary-sidebar"></slot>
				</div>
				<ndd-split-view-divider orientation="vertical"></ndd-split-view-divider>
			` : nothing}
			${component._showMain ? html`
				<div class="navigation-split-view__main-pane">
					<slot name="main"></slot>
				</div>
			` : nothing}
			${component._showInspector ? html`
				<ndd-split-view-divider orientation="vertical"></ndd-split-view-divider>
				<div class="navigation-split-view__inspector-pane">
					<slot name="inspector"></slot>
				</div>
			` : component.inspectorAutoHidden || component.inspectorAsSheet ? html`
				<dialog class="navigation-split-view__inspector-sheet"
					aria-label=${component.inspectorAccessibleLabel}
					aria-modal="true"
					@click=${component._handleInspectorSheetClick}
					@cancel=${component._handleInspectorSheetCancel}
				>
					<div class="navigation-split-view__inspector-sheet-body">
						<slot name="inspector"></slot>
					</div>
				</dialog>
			` : nothing}
			${component.sidebarAsSheet ? html`
				<dialog class="navigation-split-view__sidebar-sheet"
					aria-label=${component.sidebarAccessibleLabel}
					aria-modal="true"
					@click=${component._handleSidebarSheetClick}
					@cancel=${component._handleSidebarSheetCancel}
				>
					<div class="navigation-split-view__sidebar-sheet-body">
						${component._hasSecondarySidebar && component._paneHasContent("secondary-sidebar") ? html`
							<slot name="secondary-sidebar"></slot>
						` : html`
							<slot name="sidebar"></slot>
						`}
					</div>
				</dialog>
			` : nothing}
		</div>
	`;
}
var __defProp$r = Object.defineProperty;
var __getOwnPropDesc$w = Object.getOwnPropertyDescriptor;
var __decorateClass$w = (decorators, target, key, kind) => {
  var result = kind > 1 ? void 0 : kind ? __getOwnPropDesc$w(target, key) : target;
  for (var i = decorators.length - 1, decorator; i >= 0; i--)
    if (decorator = decorators[i])
      result = (kind ? decorator(target, key, result) : decorator(result)) || result;
  if (kind && result) __defProp$r(target, key, result);
  return result;
};
let NDDNavigationSplitView = class extends LitElement {
  constructor() {
    super(...arguments);
    this.inspectorAutoHidden = false;
    this.inspectorAsSheet = false;
    this.sidebarAsSheet = false;
    this.inspectorAccessibleLabel = "Details";
    this.sidebarAccessibleLabel = "Navigatie";
    this._showSidebar = false;
    this._showSecondarySidebar = false;
    this._showMain = true;
    this._showInspector = true;
    this._mode = "spatial";
    this._resizeObserver = null;
    this._paneObserver = null;
    this._hostObserver = null;
    this._paneMinWidths = { sidebar: 320, secondarySidebar: 320, main: 480, inspector: 320 };
    this._handleDismiss = (e) => {
      const path = e.composedPath();
      if (path.some((el) => el === this._sidebarSheet)) {
        this.hideSidebarSheet();
      } else if (this.inspectorAutoHidden || this.inspectorAsSheet) {
        this.hideInspectorSheet();
      }
    };
  }
  get _inspectorSheet() {
    return this.shadowRoot?.querySelector(".navigation-split-view__inspector-sheet") ?? null;
  }
  get _sidebarSheet() {
    return this.shadowRoot?.querySelector(".navigation-split-view__sidebar-sheet") ?? null;
  }
  get _hasSidebar() {
    return this.querySelector(':scope > [slot="sidebar"]') !== null;
  }
  get _hasSecondarySidebar() {
    return this.querySelector(':scope > [slot="secondary-sidebar"]') !== null;
  }
  get _hasInspector() {
    return this.querySelector(':scope > [slot="inspector"]') !== null;
  }
  _paneHasContent(slot) {
    return this.querySelector(`:scope > ndd-split-view-pane[slot="${slot}"]`)?.hasAttribute("has-content") ?? false;
  }
  connectedCallback() {
    super.connectedCallback();
    this._resizeObserver = new ResizeObserver(() => this._updateLayout());
    this._resizeObserver.observe(this);
    this.addEventListener("dismiss", this._handleDismiss);
    this._paneObserver = new MutationObserver(() => this._updateLayout());
    this._hostObserver = new MutationObserver(() => {
      this._observePanes();
      this._updateLayout();
    });
    this._hostObserver.observe(this, { childList: true });
    this._observePanes();
  }
  disconnectedCallback() {
    super.disconnectedCallback();
    this._resizeObserver?.disconnect();
    this._resizeObserver = null;
    this._paneObserver?.disconnect();
    this._paneObserver = null;
    this._hostObserver?.disconnect();
    this._hostObserver = null;
    this.removeEventListener("dismiss", this._handleDismiss);
  }
  _observePanes() {
    this._paneObserver?.disconnect();
    this.querySelectorAll(":scope > ndd-split-view-pane").forEach((pane) => {
      this._paneObserver.observe(pane, {
        attributes: true,
        attributeFilter: ["has-content"]
      });
    });
  }
  firstUpdated() {
    const style = getComputedStyle(this);
    const read = (prop) => parseFloat(style.getPropertyValue(prop));
    this._paneMinWidths = {
      sidebar: read("--_sidebar-min-width") || this._paneMinWidths.sidebar,
      secondarySidebar: read("--_secondary-sidebar-min-width") || this._paneMinWidths.secondarySidebar,
      main: read("--_main-min-width") || this._paneMinWidths.main,
      inspector: read("--_inspector-min-width") || this._paneMinWidths.inspector
    };
    this._updateLayout();
  }
  updated(changed) {
    if (changed.has("inspectorAsSheet") || changed.has("sidebarAsSheet")) {
      this._updateLayout();
    }
    if (changed.has("inspectorAutoHidden") && !this.inspectorAutoHidden && !this.inspectorAsSheet) {
      this._closeSheetImmediate(this._inspectorSheet);
    }
  }
  _updateLayout() {
    const width = this.getBoundingClientRect().width;
    const { sidebar: sidebarMin, secondarySidebar: secondarySidebarMin, main: mainMin, inspector: inspectorMin } = this._paneMinWidths;
    let sidebar = this.sidebarAsSheet ? false : this._hasSidebar;
    let secondarySidebar = this.sidebarAsSheet ? false : this._hasSecondarySidebar;
    let main = true;
    let inspector = this._hasInspector;
    const requestedWidth = () => [
      sidebar && sidebarMin,
      secondarySidebar && secondarySidebarMin,
      main && mainMin,
      inspector && inspectorMin
    ].reduce((sum, v) => sum + (v || 0), 0);
    if (inspector && requestedWidth() > width) inspector = false;
    if (sidebar && secondarySidebar && requestedWidth() > width) sidebar = false;
    const sidebarCollapsed = this._hasSidebar && this._hasSecondarySidebar && !sidebar && secondarySidebar;
    const fits = requestedWidth() <= width;
    let mode;
    if (sidebarCollapsed && fits) {
      mode = "sidebar-stack";
    } else if (!sidebarCollapsed && fits) {
      mode = "spatial";
    } else {
      mode = "full-stack";
    }
    if (mode === "full-stack") {
      sidebar = false;
      secondarySidebar = false;
      main = false;
      inspector = false;
      if (this._paneHasContent("main")) {
        main = true;
      } else if (this._hasSecondarySidebar && this._paneHasContent("secondary-sidebar")) {
        secondarySidebar = true;
      } else if (this._hasSidebar && this._paneHasContent("sidebar")) {
        sidebar = true;
      } else {
        main = true;
      }
    }
    if (!sidebar && !secondarySidebar && inspector && !this._paneHasContent("main")) {
      inspector = false;
    }
    this._showSidebar = sidebar;
    this._showSecondarySidebar = secondarySidebar;
    this._showMain = main;
    this._showInspector = inspector && !this.inspectorAsSheet;
    this.inspectorAutoHidden = this._hasInspector && !inspector;
    this._mode = mode;
    this.classList.toggle("full-stack", mode === "full-stack");
    this._updatePaneBackButtons();
  }
  _updatePaneBackButtons() {
    const panes = {
      sidebar: this.querySelector(':scope > ndd-split-view-pane[slot="sidebar"]'),
      secondarySidebar: this.querySelector(':scope > ndd-split-view-pane[slot="secondary-sidebar"]'),
      main: this.querySelector(':scope > ndd-split-view-pane[slot="main"]')
    };
    if (this.sidebarAsSheet) {
      panes.secondarySidebar?.removeAttribute("hide-back");
      panes.main?.setAttribute("hide-back", "");
      return;
    }
    if (this._mode === "spatial") {
      panes.secondarySidebar?.setAttribute("hide-back", "");
      panes.main?.setAttribute("hide-back", "");
      return;
    }
    if (this._mode === "sidebar-stack") {
      panes.secondarySidebar?.removeAttribute("hide-back");
      panes.main?.setAttribute("hide-back", "");
      return;
    }
    if (this._mode === "full-stack") {
      panes.secondarySidebar?.removeAttribute("hide-back");
      panes.main?.removeAttribute("hide-back");
      return;
    }
  }
  // ----------------------------------------------------------------
  // Sidebar sheet
  // ----------------------------------------------------------------
  /** Opens the sidebar as a sheet. Awaitable — resolves once the dialog is open. */
  async showSidebarSheet() {
    if (!this.sidebarAsSheet) return;
    await this.updateComplete;
    this._sidebarSheet?.showModal();
    this._manageSidebarSheetFocus();
  }
  hideSidebarSheet() {
    this._hideSheet(this._sidebarSheet);
  }
  _manageSidebarSheetFocus() {
    const activeSlotName = this._hasSecondarySidebar && this._paneHasContent("secondary-sidebar") ? "secondary-sidebar" : "sidebar";
    const slot = this.shadowRoot?.querySelector(`slot[name="${activeSlotName}"]`);
    const assigned = slot?.assignedElements({ flatten: true }) ?? [];
    this._manageFocusForSlot(assigned, this._sidebarSheet);
  }
  _handleSidebarSheetClick(e) {
    if (e.target === this._sidebarSheet) this.hideSidebarSheet();
  }
  _handleSidebarSheetCancel(e) {
    e.preventDefault();
    this.hideSidebarSheet();
  }
  // ----------------------------------------------------------------
  // Inspector sheet
  // ----------------------------------------------------------------
  /** Opens the inspector as a sheet. Awaitable — resolves once the dialog is open. */
  async showInspectorSheet() {
    if (!this.inspectorAutoHidden && !this.inspectorAsSheet) return;
    await this.updateComplete;
    this._inspectorSheet?.showModal();
    this._manageInspectorSheetFocus();
  }
  hideInspectorSheet() {
    this._hideSheet(this._inspectorSheet);
  }
  _manageInspectorSheetFocus() {
    const slot = this.shadowRoot?.querySelector('slot[name="inspector"]');
    const assigned = slot?.assignedElements({ flatten: true }) ?? [];
    this._manageFocusForSlot(assigned, this._inspectorSheet);
  }
  _handleInspectorSheetClick(e) {
    if (e.target === this._inspectorSheet) this.hideInspectorSheet();
  }
  _handleInspectorSheetCancel(e) {
    e.preventDefault();
    this.hideInspectorSheet();
  }
  // ----------------------------------------------------------------
  // Shared focus helper
  // ----------------------------------------------------------------
  _manageFocusForSlot(assigned, fallback) {
    if (assigned.some((el) => el.querySelector("[autofocus]"))) return;
    const topTitleBar = assigned.flatMap((el) => [
      el.tagName === "NDD-TOP-TITLE-BAR" ? el : null,
      el.querySelector("ndd-top-title-bar")
    ]).find(Boolean);
    const heading = topTitleBar?.shadowRoot?.querySelector("h1,h2,h3,h4,h5,h6") ?? assigned.map((el) => el.querySelector("h1,h2,h3,h4,h5,h6")).find(Boolean);
    if (heading) {
      const hadTabindex = heading.hasAttribute("tabindex");
      if (!hadTabindex) heading.setAttribute("tabindex", "-1");
      heading.focus();
      if (!hadTabindex) {
        heading.addEventListener("blur", () => heading.removeAttribute("tabindex"), { once: true });
      }
      return;
    }
    fallback?.focus();
  }
  _hideSheet(dialog) {
    if (!dialog?.open) return;
    if (dialog.dataset["closing"] === "true") return;
    dialog.dataset["closing"] = "true";
    dialog.classList.add("is-closing");
    dialog.addEventListener("animationend", () => {
      dialog.classList.remove("is-closing");
      delete dialog.dataset["closing"];
      dialog.close();
    }, { once: true });
    requestAnimationFrame(() => {
      if (dialog.dataset["closing"] === "true" && getComputedStyle(dialog).animationName === "none") {
        dialog.classList.remove("is-closing");
        delete dialog.dataset["closing"];
        dialog.close();
      }
    });
  }
  _closeSheetImmediate(dialog) {
    if (!dialog?.open) return;
    dialog.classList.remove("is-closing");
    dialog.close();
  }
  render() {
    return navigationSplitViewTemplate(this);
  }
};
NDDNavigationSplitView.styles = navigationSplitViewStyles;
__decorateClass$w([
  property({ type: Boolean, reflect: true, attribute: "inspector-auto-hidden" })
], NDDNavigationSplitView.prototype, "inspectorAutoHidden", 2);
__decorateClass$w([
  property({ type: Boolean, reflect: true, attribute: "inspector-as-sheet" })
], NDDNavigationSplitView.prototype, "inspectorAsSheet", 2);
__decorateClass$w([
  property({ type: Boolean, reflect: true, attribute: "sidebar-as-sheet" })
], NDDNavigationSplitView.prototype, "sidebarAsSheet", 2);
__decorateClass$w([
  property({ type: String, attribute: "inspector-accessible-label" })
], NDDNavigationSplitView.prototype, "inspectorAccessibleLabel", 2);
__decorateClass$w([
  property({ type: String, attribute: "sidebar-accessible-label" })
], NDDNavigationSplitView.prototype, "sidebarAccessibleLabel", 2);
__decorateClass$w([
  state()
], NDDNavigationSplitView.prototype, "_showSidebar", 2);
__decorateClass$w([
  state()
], NDDNavigationSplitView.prototype, "_showSecondarySidebar", 2);
__decorateClass$w([
  state()
], NDDNavigationSplitView.prototype, "_showMain", 2);
__decorateClass$w([
  state()
], NDDNavigationSplitView.prototype, "_showInspector", 2);
NDDNavigationSplitView = __decorateClass$w([
  customElement("ndd-navigation-split-view")
], NDDNavigationSplitView);
const sideBySideSplitViewStyles = css`
	:host {
		display: flex;
		width: 100%;
		height: 100%;
		background-color: var(--_background-color);

		--_pane-min-width: var(--primitives-area-320); /* Pane min-width — read by JS via getComputedStyle in firstUpdated */
		--_background-color: var(--context-parent-background-color, var(--semantics-surfaces-background-color));
	}

	:host([background="default"]) {
		--context-parent-background-color: var(--semantics-surfaces-background-color);
		--_background-color: var(--context-parent-background-color);
	}

	:host([background="tinted"]) {
		--context-parent-background-color: var(--semantics-surfaces-tinted-background-color);
		--_background-color: var(--context-parent-background-color);
	}

	:host([hidden]) {
		display: none;
	}


	/* # Split view */

	.side-by-side-split-view {
		display: flex;
		flex-direction: row;
		flex: 1;
		min-height: 0;
		min-width: 0;
		overflow: hidden;
	}


	/* # Pane */

	.side-by-side-split-view__pane {
		display: flex;
		flex-direction: column;
		flex: 1;
		min-height: 0;
		min-width: var(--_pane-min-width);
		overflow: hidden;
		container-type: inline-size;
		container-name: layout-area;
	}

	.side-by-side-split-view__pane[hidden] {
		display: none;
	}

	::slotted(*) {
		flex: 1;
		min-height: 0;
	}
`;
function sideBySideSplitViewTemplate(component) {
  const panes = Array.from({ length: component.panes }, (_, i) => i + 1);
  return html`
		<div class="side-by-side-split-view">
			${panes.map((n, i) => html`
				${i > 0 && i < component._visiblePanes ? html`
					<ndd-split-view-divider orientation="vertical"></ndd-split-view-divider>
				` : nothing}
				<div
					class="side-by-side-split-view__pane"
					?hidden=${i >= component._visiblePanes}
				>
					<slot name="pane-${n}"></slot>
				</div>
			`)}
		</div>
	`;
}
var __defProp$q = Object.defineProperty;
var __getOwnPropDesc$v = Object.getOwnPropertyDescriptor;
var __decorateClass$v = (decorators, target, key, kind) => {
  var result = kind > 1 ? void 0 : kind ? __getOwnPropDesc$v(target, key) : target;
  for (var i = decorators.length - 1, decorator; i >= 0; i--)
    if (decorator = decorators[i])
      result = (kind ? decorator(target, key, result) : decorator(result)) || result;
  if (kind && result) __defProp$q(target, key, result);
  return result;
};
let NDDSideBySideSplitView = class extends LitElement {
  constructor() {
    super(...arguments);
    this.background = "inherit";
    this.panes = 2;
    this._visiblePanes = Infinity;
    this._paneMinWidth = 0;
    this._resizeObserver = null;
  }
  connectedCallback() {
    super.connectedCallback();
    this._resizeObserver = new ResizeObserver(() => this._updateVisiblePanes());
    this._resizeObserver.observe(this);
  }
  disconnectedCallback() {
    super.disconnectedCallback();
    this._resizeObserver?.disconnect();
    this._resizeObserver = null;
  }
  firstUpdated() {
    this._paneMinWidth = parseFloat(getComputedStyle(this).getPropertyValue("--_pane-min-width"));
    this._updateVisiblePanes();
  }
  updated(changed) {
    if (changed.has("panes")) {
      this._updateVisiblePanes();
    }
  }
  _updateVisiblePanes() {
    if (!this._paneMinWidth) return;
    const width = this.getBoundingClientRect().width;
    const fitting = Math.floor(width / this._paneMinWidth);
    this._visiblePanes = Math.min(this.panes, Math.max(1, fitting));
  }
  render() {
    return sideBySideSplitViewTemplate(this);
  }
};
NDDSideBySideSplitView.styles = sideBySideSplitViewStyles;
__decorateClass$v([
  property({ type: String, reflect: true })
], NDDSideBySideSplitView.prototype, "background", 2);
__decorateClass$v([
  property({ type: Number, reflect: true })
], NDDSideBySideSplitView.prototype, "panes", 2);
__decorateClass$v([
  state()
], NDDSideBySideSplitView.prototype, "_visiblePanes", 2);
NDDSideBySideSplitView = __decorateClass$v([
  customElement("ndd-side-by-side-split-view")
], NDDSideBySideSplitView);
const stackedSplitViewStyles = css`
	:host {
		display: flex;
		flex-direction: column;
		width: 100%;
		height: 100%;
		background-color: var(--_background-color);

		--_pane-min-height: var(--primitives-area-200); /* Pane min-height — read by JS via getComputedStyle in firstUpdated */
		--_background-color: var(--context-parent-background-color, var(--semantics-surfaces-background-color));
	}

	:host([background="default"]) {
		--context-parent-background-color: var(--semantics-surfaces-background-color);
		--_background-color: var(--context-parent-background-color);
	}

	:host([background="tinted"]) {
		--context-parent-background-color: var(--semantics-surfaces-tinted-background-color);
		--_background-color: var(--context-parent-background-color);
	}

	:host([hidden]) {
		display: none;
	}


	/* # Split view */

	.stacked-split-view {
		display: flex;
		flex-direction: column;
		flex: 1;
		min-height: 0;
		min-width: 0;
		overflow: hidden;
	}


	/* # Pane */

	.stacked-split-view__pane {
		display: flex;
		flex-direction: column;
		flex: 1;
		min-height: var(--_pane-min-height);
		min-width: 0;
		overflow: hidden;
		container-type: inline-size;
		container-name: layout-area;
	}

	.stacked-split-view__pane[hidden] {
		display: none;
	}

	::slotted(*) {
		flex: 1;
		min-height: 0;
	}
`;
function stackedSplitViewTemplate(component) {
  const panes = Array.from({ length: component.panes }, (_, i) => i + 1);
  return html`
		<div class="stacked-split-view">
			${panes.map((n, i) => html`
				${i > 0 && i < component._visiblePanes ? html`
					<ndd-split-view-divider orientation="horizontal"></ndd-split-view-divider>
				` : nothing}
				<div
					class="stacked-split-view__pane"
					?hidden=${i >= component._visiblePanes}
				>
					<slot name="pane-${n}"></slot>
				</div>
			`)}
		</div>
	`;
}
var __defProp$p = Object.defineProperty;
var __getOwnPropDesc$u = Object.getOwnPropertyDescriptor;
var __decorateClass$u = (decorators, target, key, kind) => {
  var result = kind > 1 ? void 0 : kind ? __getOwnPropDesc$u(target, key) : target;
  for (var i = decorators.length - 1, decorator; i >= 0; i--)
    if (decorator = decorators[i])
      result = (kind ? decorator(target, key, result) : decorator(result)) || result;
  if (kind && result) __defProp$p(target, key, result);
  return result;
};
let NDDStackedSplitView = class extends LitElement {
  constructor() {
    super(...arguments);
    this.background = "inherit";
    this.panes = 2;
    this._visiblePanes = Infinity;
    this._paneMinHeight = 0;
    this._resizeObserver = null;
  }
  connectedCallback() {
    super.connectedCallback();
    this._resizeObserver = new ResizeObserver(() => this._updateVisiblePanes());
    this._resizeObserver.observe(this);
  }
  disconnectedCallback() {
    super.disconnectedCallback();
    this._resizeObserver?.disconnect();
    this._resizeObserver = null;
  }
  firstUpdated() {
    this._paneMinHeight = parseFloat(getComputedStyle(this).getPropertyValue("--_pane-min-height"));
    this._updateVisiblePanes();
  }
  updated(changed) {
    if (changed.has("panes")) {
      this._updateVisiblePanes();
    }
  }
  _updateVisiblePanes() {
    if (!this._paneMinHeight) return;
    const height = this.getBoundingClientRect().height;
    const fitting = Math.floor(height / this._paneMinHeight);
    this._visiblePanes = Math.min(this.panes, Math.max(1, fitting));
  }
  render() {
    return stackedSplitViewTemplate(this);
  }
};
NDDStackedSplitView.styles = stackedSplitViewStyles;
__decorateClass$u([
  property({ type: String, reflect: true })
], NDDStackedSplitView.prototype, "background", 2);
__decorateClass$u([
  property({ type: Number, reflect: true })
], NDDStackedSplitView.prototype, "panes", 2);
__decorateClass$u([
  state()
], NDDStackedSplitView.prototype, "_visiblePanes", 2);
NDDStackedSplitView = __decorateClass$u([
  customElement("ndd-stacked-split-view")
], NDDStackedSplitView);
const mdMin$4 = unsafeCSS(breakpoints.mdMin);
const splitViewPaneStyles = css`
	:host {
		--_background-color: var(--context-parent-background-color, var(--semantics-surfaces-background-color));

		display: flex;
		width: 100%;
		height: 100%;

		@media (min-width: ${mdMin$4}) {
			background-color: var(--_background-color);
		}
	}

	:host([background="default"]) {
		--context-parent-background-color: var(--semantics-surfaces-background-color);
		--_background-color: var(--context-parent-background-color);
	}

	:host([background="tinted"]) {
		--context-parent-background-color: var(--semantics-surfaces-tinted-background-color);
		--_background-color: var(--context-parent-background-color);
	}

	:host([hidden]) {
		display: none;
	}

	:host([hide-back]) {
		--context-back-button-display: none;
	}


	/* # Pane */

	.split-view-pane {
		display: flex;
		flex-direction: column;
		flex: 1;
		min-height: 0;
		min-width: 0;
		overflow: hidden;
	}

	::slotted(*) {
		flex: 1;
		min-height: 0;
	}
`;
function splitViewPaneTemplate(_component) {
  return html`
		<div class="split-view-pane">
			<slot></slot>
		</div>
	`;
}
var __defProp$o = Object.defineProperty;
var __getOwnPropDesc$t = Object.getOwnPropertyDescriptor;
var __decorateClass$t = (decorators, target, key, kind) => {
  var result = kind > 1 ? void 0 : kind ? __getOwnPropDesc$t(target, key) : target;
  for (var i = decorators.length - 1, decorator; i >= 0; i--)
    if (decorator = decorators[i])
      result = (kind ? decorator(target, key, result) : decorator(result)) || result;
  if (kind && result) __defProp$o(target, key, result);
  return result;
};
let NDDSplitViewPane = class extends LitElement {
  constructor() {
    super(...arguments);
    this.hasContent = false;
    this.hideBack = false;
    this.background = "inherit";
  }
  render() {
    return splitViewPaneTemplate();
  }
};
NDDSplitViewPane.styles = splitViewPaneStyles;
__decorateClass$t([
  property({ type: Boolean, reflect: true, attribute: "has-content" })
], NDDSplitViewPane.prototype, "hasContent", 2);
__decorateClass$t([
  property({ type: Boolean, reflect: true, attribute: "hide-back" })
], NDDSplitViewPane.prototype, "hideBack", 2);
__decorateClass$t([
  property({ type: String, reflect: true })
], NDDSplitViewPane.prototype, "background", 2);
NDDSplitViewPane = __decorateClass$t([
  customElement("ndd-split-view-pane")
], NDDSplitViewPane);
const pageStyles = css`
	:host {
		--_background-color: var(--context-parent-background-color, var(--semantics-surfaces-background-color));

		display: flex;
		flex-direction: column;
		width: 100%;
		height: 100%;
		overflow-y: auto;
		overflow-x: hidden;
		background-color: var(--_background-color);
		padding-top: var(--context-bar-split-view-top-bars-height, 0px);
		padding-bottom: var(--context-bar-split-view-bottom-bars-height, 0px);
	}

	/* Overflow hidden prevents content from escaping the scroll wrapper.
	   Overlays inside slotted content should use popover, dialog, or
	   position: fixed to render in the top layer. */
	:host([sticky-header]) {
		position: relative;
		overflow: hidden;
	}

	:host([background="default"]) {
		--context-parent-background-color: var(--semantics-surfaces-background-color);
		--_background-color: var(--context-parent-background-color);
	}

	:host([background="tinted"]) {
		--context-parent-background-color: var(--semantics-surfaces-tinted-background-color);
		--_background-color: var(--context-parent-background-color);
	}

	:host([hidden]) {
		display: none;
	}


	/* # Header */

	.page__header {
		flex-shrink: 0;
		position: relative;
		container-type: inline-size;
		container-name: layout-area;
	}

	:host([sticky-header]) .page__header {
		position: absolute;
		top: 0;
		left: 0;
		right: 0;
		z-index: 1;
		background-color: color-mix(in srgb, var(--_background-color) 95%, transparent);
	}

	:host([sticky-header]) .page__header::after {
		content: '';
		position: absolute;
		top: 100%;
		left: 0;
		right: 0;
		height: var(--primitives-space-32);
		background: linear-gradient(to bottom, color-mix(in srgb, var(--_background-color) 95%, transparent), transparent);
		pointer-events: none;
		opacity: 0;
		transition: opacity 200ms ease;
	}

	:host([sticky-header]) .page__header.is-scrolled::after {
		opacity: 1;
	}


	/* # Scroll */

	.page__scroll {
		display: flex;
		flex-direction: column;
		flex-grow: 1;
		min-height: 0;
	}

	:host([sticky-header]) .page__scroll {
		overflow-y: auto;
		overflow-x: hidden;
	}


	/* # Main */

	.page__main {
		display: flex;
		flex-direction: column;
		flex-grow: 1;
		container-type: inline-size;
		container-name: layout-area;
	}


	/* # Footer */

	.page__footer {
		flex-shrink: 0;
		position: relative;
		container-type: inline-size;
		container-name: layout-area;
	}

	:host([sticky-footer]) .page__footer {
		position: sticky;
		bottom: 0;
		z-index: 1;
		background-color: color-mix(in srgb, var(--_background-color) 95%, transparent);
	}

	:host([sticky-footer]) .page__footer::before {
		content: '';
		position: absolute;
		bottom: 100%;
		left: 0;
		right: 0;
		height: var(--primitives-space-32);
		background: linear-gradient(to top, color-mix(in srgb, var(--_background-color) 95%, transparent), transparent);
		pointer-events: none;
	}
`;
function pageTemplate(component) {
  return html`
		<header class="page__header ${component._scrolled ? "is-scrolled" : ""}">
			<slot name="header"></slot>
		</header>
		<div class="page__scroll">
			<main class="page__main">
				<slot></slot>
			</main>
			<footer class="page__footer">
				<slot name="footer"></slot>
			</footer>
		</div>
	`;
}
var __defProp$n = Object.defineProperty;
var __getOwnPropDesc$s = Object.getOwnPropertyDescriptor;
var __decorateClass$s = (decorators, target, key, kind) => {
  var result = kind > 1 ? void 0 : kind ? __getOwnPropDesc$s(target, key) : target;
  for (var i = decorators.length - 1, decorator; i >= 0; i--)
    if (decorator = decorators[i])
      result = (kind ? decorator(target, key, result) : decorator(result)) || result;
  if (kind && result) __defProp$n(target, key, result);
  return result;
};
let NDDPage = class extends LitElement {
  constructor() {
    super(...arguments);
    this.stickyHeader = false;
    this.stickyFooter = false;
    this.background = "inherit";
    this._scrolled = false;
    this._scrollTarget = null;
    this._headerObserver = null;
    this._onScroll = () => {
      const target = this.stickyHeader ? this._scrollEl : this;
      this._scrolled = target.scrollTop > 0;
    };
  }
  get scrollTarget() {
    return this.stickyHeader ? this._scrollEl ?? this : this;
  }
  get _headerEl() {
    return this.shadowRoot?.querySelector(".page__header") ?? null;
  }
  get _scrollEl() {
    return this.shadowRoot?.querySelector(".page__scroll") ?? null;
  }
  connectedCallback() {
    super.connectedCallback();
    if (this.hasUpdated) {
      this._setupScrollListener();
      if (this.stickyHeader) this._setupHeaderObserver();
    }
  }
  disconnectedCallback() {
    super.disconnectedCallback();
    this._teardownScrollListener();
    this._teardownHeaderObserver();
  }
  firstUpdated() {
    this._setupScrollListener();
    if (this.stickyHeader) this._setupHeaderObserver();
  }
  updated(changed) {
    if (changed.has("stickyHeader")) {
      this._teardownScrollListener();
      this._setupScrollListener();
      if (this.stickyHeader) {
        this._setupHeaderObserver();
      } else {
        this._teardownHeaderObserver();
        if (this._scrollEl) this._scrollEl.style.paddingTop = "";
      }
    }
  }
  _setupScrollListener() {
    const target = this.stickyHeader ? this._scrollEl : this;
    if (!target) return;
    target.addEventListener("scroll", this._onScroll);
    this._scrollTarget = target;
  }
  _teardownScrollListener() {
    if (this._scrollTarget) {
      this._scrollTarget.removeEventListener("scroll", this._onScroll);
      this._scrollTarget = null;
    }
  }
  _setupHeaderObserver() {
    this._teardownHeaderObserver();
    const header = this._headerEl;
    const scroll = this._scrollEl;
    if (!header || !scroll) return;
    this._headerObserver = new ResizeObserver(() => {
      if (scroll.scrollTop > 0) return;
      scroll.style.paddingTop = `${header.offsetHeight}px`;
    });
    this._headerObserver.observe(header);
  }
  _teardownHeaderObserver() {
    if (this._headerObserver) {
      this._headerObserver.disconnect();
      this._headerObserver = null;
    }
  }
  render() {
    return pageTemplate(this);
  }
};
NDDPage.styles = pageStyles;
__decorateClass$s([
  property({ type: Boolean, reflect: true, attribute: "sticky-header" })
], NDDPage.prototype, "stickyHeader", 2);
__decorateClass$s([
  property({ type: Boolean, reflect: true, attribute: "sticky-footer" })
], NDDPage.prototype, "stickyFooter", 2);
__decorateClass$s([
  property({ type: String, reflect: true })
], NDDPage.prototype, "background", 2);
__decorateClass$s([
  state()
], NDDPage.prototype, "_scrolled", 2);
NDDPage = __decorateClass$s([
  customElement("ndd-page")
], NDDPage);
const nddPage = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  get NDDPage() {
    return NDDPage;
  }
}, Symbol.toStringTag, { value: "Module" }));
const simpleSectionStyles = css`
	:host {
		display: flex;
		flex-direction: column;
		align-items: center;
		width: 100%;
		container-type: inline-size;
	}

	:host([hidden]) {
		display: none;
	}

	:host([align="center"]) {
		flex-grow: 1;
	}


	/* # Section */

	.simple-section {
		display: flex;
		flex-direction: column;
		flex-grow: 1;
		align-items: center;
		width: 100%;
		box-sizing: border-box;

		@container (max-width: ${unsafeCSS(breakpoints.smMax)}) {
			padding-inline: var(--semantics-page-sections-sm-margin-inline);
			padding-block: var(--semantics-page-sections-sm-margin-block);
		}

		@container (min-width: ${unsafeCSS(breakpoints.mdMin)}) and (max-width: ${unsafeCSS(breakpoints.mdMax)}) {
			padding-inline: var(--semantics-page-sections-md-margin-inline);
			padding-block: var(--semantics-page-sections-md-margin-block);
		}

		@container (min-width: ${unsafeCSS(breakpoints.lgMin)}) {
			padding-inline: var(--semantics-page-sections-lg-margin-inline);
			padding-block: var(--semantics-page-sections-lg-margin-block);
		}
	}



	/* # Header */

	.simple-section__header[hidden] {
		display: none;
	}


	/* # Body */

	.simple-section__body {
		display: flex;
		flex-direction: column;
		flex-grow: 1;
		width: 100%;
		max-width: var(--semantics-page-sections-body-max-width);

		@container (max-width: ${unsafeCSS(breakpoints.smMax)}) {
			gap: var(--semantics-page-sections-sm-gap);
		}

		@container (min-width: ${unsafeCSS(breakpoints.mdMin)}) and (max-width: ${unsafeCSS(breakpoints.mdMax)}) {
			gap: var(--semantics-page-sections-md-gap);
		}

		@container (min-width: ${unsafeCSS(breakpoints.lgMin)}) {
			gap: var(--semantics-page-sections-lg-gap);
		}
	}



	/* # Footer */

	.simple-section__footer[hidden] {
		display: none;
	}


	/* # Main */

	.simple-section__main {
		display: flex;
		flex-direction: column;
		flex-grow: 1;
	}

	:host([align="center"]) .simple-section__main {
		justify-content: center;
	}
`;
function simpleSectionTemplate(component) {
  return html`
		<section class="simple-section">
			<div class="simple-section__body">
				<header class="simple-section__header" hidden>
					<slot name="header" @slotchange=${component._onSlotChange}></slot>
				</header>
				<div class="simple-section__main">
					<slot></slot>
				</div>
				<footer class="simple-section__footer" hidden>
					<slot name="footer" @slotchange=${component._onSlotChange}></slot>
				</footer>
			</div>
		</section>
	`;
}
var __defProp$m = Object.defineProperty;
var __getOwnPropDesc$r = Object.getOwnPropertyDescriptor;
var __decorateClass$r = (decorators, target, key, kind) => {
  var result = kind > 1 ? void 0 : kind ? __getOwnPropDesc$r(target, key) : target;
  for (var i = decorators.length - 1, decorator; i >= 0; i--)
    if (decorator = decorators[i])
      result = (kind ? decorator(target, key, result) : decorator(result)) || result;
  if (kind && result) __defProp$m(target, key, result);
  return result;
};
let NDDSimpleSection = class extends LitElement {
  _onSlotChange(e) {
    const slot = e.target;
    const wrapper = slot.parentElement;
    wrapper.hidden = slot.assignedElements().length === 0;
  }
  render() {
    return simpleSectionTemplate(this);
  }
};
NDDSimpleSection.styles = simpleSectionStyles;
__decorateClass$r([
  property({ type: String, reflect: true })
], NDDSimpleSection.prototype, "align", 2);
NDDSimpleSection = __decorateClass$r([
  customElement("ndd-simple-section")
], NDDSimpleSection);
const nddSimpleSection = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  get NDDSimpleSection() {
    return NDDSimpleSection;
  }
}, Symbol.toStringTag, { value: "Module" }));
const fullBleedSectionStyles = css`
	:host {
		display: flex;
		flex-direction: column;
		align-items: center;
		width: 100%;
		container-type: inline-size;
	}

	:host([hidden]) {
		display: none;
	}

	:host([align="center"]) {
		flex-grow: 1;
	}


	/* # Section */

	.full-bleed-section {
		display: flex;
		flex-direction: column;
		flex-grow: 1;
		width: 100%;
		box-sizing: border-box;

		@container (max-width: ${unsafeCSS(breakpoints.smMax)}) {
			padding-block: var(--semantics-page-sections-sm-margin-block);
		}

		@container (min-width: ${unsafeCSS(breakpoints.mdMin)}) and (max-width: ${unsafeCSS(breakpoints.mdMax)}) {
			padding-block: var(--semantics-page-sections-md-margin-block);
		}

		@container (min-width: ${unsafeCSS(breakpoints.lgMin)}) {
			padding-block: var(--semantics-page-sections-lg-margin-block);
		}
	}



	/* # Header */

	.full-bleed-section__header[hidden] {
		display: none;
	}


	/* # Body */

	.full-bleed-section__body {
		display: flex;
		flex-direction: column;
		flex-grow: 1;
		width: 100%;

		@container (max-width: ${unsafeCSS(breakpoints.smMax)}) {
			gap: var(--semantics-page-sections-sm-gap);
		}

		@container (min-width: ${unsafeCSS(breakpoints.mdMin)}) and (max-width: ${unsafeCSS(breakpoints.mdMax)}) {
			gap: var(--semantics-page-sections-md-gap);
		}

		@container (min-width: ${unsafeCSS(breakpoints.lgMin)}) {
			gap: var(--semantics-page-sections-lg-gap);
		}
	}



	/* # Footer */

	.full-bleed-section__footer[hidden] {
		display: none;
	}


	/* # Main */

	.full-bleed-section__main {
		display: flex;
		flex-direction: column;
		flex-grow: 1;
	}

	:host([align="center"]) .full-bleed-section__main {
		justify-content: center;
	}

`;
function fullBleedSectionTemplate(component) {
  return html`
		<section class="full-bleed-section">
			<div class="full-bleed-section__body">
				<header class="full-bleed-section__header" hidden>
					<slot name="header" @slotchange=${component._onSlotChange}></slot>
				</header>
				<div class="full-bleed-section__main">
					<slot></slot>
				</div>
				<footer class="full-bleed-section__footer" hidden>
					<slot name="footer" @slotchange=${component._onSlotChange}></slot>
				</footer>
			</div>
		</section>
	`;
}
var __defProp$l = Object.defineProperty;
var __getOwnPropDesc$q = Object.getOwnPropertyDescriptor;
var __decorateClass$q = (decorators, target, key, kind) => {
  var result = kind > 1 ? void 0 : kind ? __getOwnPropDesc$q(target, key) : target;
  for (var i = decorators.length - 1, decorator; i >= 0; i--)
    if (decorator = decorators[i])
      result = (kind ? decorator(target, key, result) : decorator(result)) || result;
  if (kind && result) __defProp$l(target, key, result);
  return result;
};
let NDDFullBleedSection = class extends LitElement {
  _onSlotChange(e) {
    const slot = e.target;
    const wrapper = slot.parentElement;
    wrapper.hidden = slot.assignedElements().length === 0;
  }
  render() {
    return fullBleedSectionTemplate(this);
  }
};
NDDFullBleedSection.styles = fullBleedSectionStyles;
__decorateClass$q([
  property({ type: String, reflect: true })
], NDDFullBleedSection.prototype, "align", 2);
NDDFullBleedSection = __decorateClass$q([
  customElement("ndd-full-bleed-section")
], NDDFullBleedSection);
const oneThirdTwoThirdsSectionStyles = css`
	:host {
		display: flex;
		flex-direction: column;
		align-items: center;
		width: 100%;
		container-type: inline-size;
	}

	:host([hidden]) {
		display: none;
	}



	/* # Section */

	.one-third-two-thirds-section {
		display: flex;
		flex-direction: column;
		align-items: center;
		width: 100%;
		box-sizing: border-box;

		@container (max-width: ${unsafeCSS(breakpoints.smMax)}) {
			padding-inline: var(--semantics-page-sections-sm-margin-inline);
			padding-block: var(--semantics-page-sections-sm-margin-block);
		}

		@container (min-width: ${unsafeCSS(breakpoints.mdMin)}) and (max-width: ${unsafeCSS(breakpoints.mdMax)}) {
			padding-inline: var(--semantics-page-sections-md-margin-inline);
			padding-block: var(--semantics-page-sections-md-margin-block);
		}

		@container (min-width: ${unsafeCSS(breakpoints.lgMin)}) {
			padding-inline: var(--semantics-page-sections-lg-margin-inline);
			padding-block: var(--semantics-page-sections-lg-margin-block);
		}
	}


	/* # Body */

	.one-third-two-thirds-section__body {
		display: flex;
		flex-direction: column;
		width: 100%;
		max-width: var(--semantics-page-sections-body-max-width);

		@container (max-width: ${unsafeCSS(breakpoints.smMax)}) {
			gap: var(--semantics-page-sections-sm-gap);
		}

		@container (min-width: ${unsafeCSS(breakpoints.mdMin)}) and (max-width: ${unsafeCSS(breakpoints.mdMax)}) {
			gap: var(--semantics-page-sections-md-gap);
		}

		@container (min-width: ${unsafeCSS(breakpoints.lgMin)}) {
			gap: var(--semantics-page-sections-lg-gap);
		}
	}


	/* # Columns */

	.one-third-two-thirds-section__columns {
		display: flex;
		flex-wrap: wrap;

		@container (max-width: ${unsafeCSS(breakpoints.smMax)}) {
			gap: var(--semantics-page-sections-sm-gap);
		}

		@container (min-width: ${unsafeCSS(breakpoints.mdMin)}) and (max-width: ${unsafeCSS(breakpoints.mdMax)}) {
			gap: var(--semantics-page-sections-md-gap);
		}

		@container (min-width: ${unsafeCSS(breakpoints.lgMin)}) {
			gap: var(--semantics-page-sections-lg-gap);
		}
	}

	.one-third-two-thirds-section__left-column {
		flex: 1;
		min-width: var(--primitives-area-280);
	}

	.one-third-two-thirds-section__right-column {
		flex: 2;
		min-width: var(--primitives-area-280);
	}
`;
function oneThirdTwoThirdsSectionTemplate(_component) {
  return html`
		<section class="one-third-two-thirds-section">
			<div class="one-third-two-thirds-section__body">
				<slot name="header"></slot>
				<div class="one-third-two-thirds-section__columns">
					<div class="one-third-two-thirds-section__left-column">
						<slot name="left"></slot>
					</div>
					<div class="one-third-two-thirds-section__right-column">
						<slot></slot>
						<slot name="right"></slot>
					</div>
				</div>
				<slot name="footer"></slot>
			</div>
		</section>
	`;
}
var __getOwnPropDesc$p = Object.getOwnPropertyDescriptor;
var __decorateClass$p = (decorators, target, key, kind) => {
  var result = kind > 1 ? void 0 : kind ? __getOwnPropDesc$p(target, key) : target;
  for (var i = decorators.length - 1, decorator; i >= 0; i--)
    if (decorator = decorators[i])
      result = decorator(result) || result;
  return result;
};
let NDDOneThirdTwoThirdsSection = class extends LitElement {
  render() {
    return oneThirdTwoThirdsSectionTemplate();
  }
};
NDDOneThirdTwoThirdsSection.styles = oneThirdTwoThirdsSectionStyles;
NDDOneThirdTwoThirdsSection = __decorateClass$p([
  customElement("ndd-one-third-two-thirds-section")
], NDDOneThirdTwoThirdsSection);
const twoThirdsOneThirdSectionStyles = css`
	:host {
		display: flex;
		flex-direction: column;
		align-items: center;
		width: 100%;
		container-type: inline-size;
	}

	:host([hidden]) {
		display: none;
	}



	/* # Section */

	.two-thirds-one-third-section {
		display: flex;
		flex-direction: column;
		align-items: center;
		width: 100%;
		box-sizing: border-box;

		@container (max-width: ${unsafeCSS(breakpoints.smMax)}) {
			padding-inline: var(--semantics-page-sections-sm-margin-inline);
			padding-block: var(--semantics-page-sections-sm-margin-block);
		}

		@container (min-width: ${unsafeCSS(breakpoints.mdMin)}) and (max-width: ${unsafeCSS(breakpoints.mdMax)}) {
			padding-inline: var(--semantics-page-sections-md-margin-inline);
			padding-block: var(--semantics-page-sections-md-margin-block);
		}

		@container (min-width: ${unsafeCSS(breakpoints.lgMin)}) {
			padding-inline: var(--semantics-page-sections-lg-margin-inline);
			padding-block: var(--semantics-page-sections-lg-margin-block);
		}
	}


	/* # Body */

	.two-thirds-one-third-section__body {
		display: flex;
		flex-direction: column;
		width: 100%;
		max-width: var(--semantics-page-sections-body-max-width);

		@container (max-width: ${unsafeCSS(breakpoints.smMax)}) {
			gap: var(--semantics-page-sections-sm-gap);
		}

		@container (min-width: ${unsafeCSS(breakpoints.mdMin)}) and (max-width: ${unsafeCSS(breakpoints.mdMax)}) {
			gap: var(--semantics-page-sections-md-gap);
		}

		@container (min-width: ${unsafeCSS(breakpoints.lgMin)}) {
			gap: var(--semantics-page-sections-lg-gap);
		}
	}


	/* # Columns */

	.two-thirds-one-third-section__columns {
		display: flex;
		flex-wrap: wrap;

		@container (max-width: ${unsafeCSS(breakpoints.smMax)}) {
			gap: var(--semantics-page-sections-sm-gap);
		}

		@container (min-width: ${unsafeCSS(breakpoints.mdMin)}) and (max-width: ${unsafeCSS(breakpoints.mdMax)}) {
			gap: var(--semantics-page-sections-md-gap);
		}

		@container (min-width: ${unsafeCSS(breakpoints.lgMin)}) {
			gap: var(--semantics-page-sections-lg-gap);
		}
	}

	.two-thirds-one-third-section__left-column {
		flex: 2;
		min-width: var(--primitives-area-280);
	}

	.two-thirds-one-third-section__right-column {
		flex: 1;
		min-width: var(--primitives-area-280);
	}

`;
function twoThirdsOneThirdSectionTemplate(_component) {
  return html`
		<section class="two-thirds-one-third-section">
			<div class="two-thirds-one-third-section__body">
				<slot name="header"></slot>
				<div class="two-thirds-one-third-section__columns">
					<div class="two-thirds-one-third-section__left-column">
						<slot></slot>
						<slot name="left"></slot>
					</div>
					<div class="two-thirds-one-third-section__right-column">
						<slot name="right"></slot>
					</div>
				</div>
				<slot name="footer"></slot>
			</div>
		</section>
	`;
}
var __getOwnPropDesc$o = Object.getOwnPropertyDescriptor;
var __decorateClass$o = (decorators, target, key, kind) => {
  var result = kind > 1 ? void 0 : kind ? __getOwnPropDesc$o(target, key) : target;
  for (var i = decorators.length - 1, decorator; i >= 0; i--)
    if (decorator = decorators[i])
      result = decorator(result) || result;
  return result;
};
let NDDTwoThirdsOneThirdSection = class extends LitElement {
  render() {
    return twoThirdsOneThirdSectionTemplate();
  }
};
NDDTwoThirdsOneThirdSection.styles = twoThirdsOneThirdSectionStyles;
NDDTwoThirdsOneThirdSection = __decorateClass$o([
  customElement("ndd-two-thirds-one-third-section")
], NDDTwoThirdsOneThirdSection);
const oneHalfOneHalfSectionStyles = css`
	:host {
		display: flex;
		flex-direction: column;
		align-items: center;
		width: 100%;
		container-type: inline-size;
	}

	:host([hidden]) {
		display: none;
	}



	/* # Section */

	.one-half-one-half-section {
		display: flex;
		flex-direction: column;
		align-items: center;
		width: 100%;
		box-sizing: border-box;

		@container (max-width: ${unsafeCSS(breakpoints.smMax)}) {
			padding-inline: var(--semantics-page-sections-sm-margin-inline);
			padding-block: var(--semantics-page-sections-sm-margin-block);
		}

		@container (min-width: ${unsafeCSS(breakpoints.mdMin)}) and (max-width: ${unsafeCSS(breakpoints.mdMax)}) {
			padding-inline: var(--semantics-page-sections-md-margin-inline);
			padding-block: var(--semantics-page-sections-md-margin-block);
		}

		@container (min-width: ${unsafeCSS(breakpoints.lgMin)}) {
			padding-inline: var(--semantics-page-sections-lg-margin-inline);
			padding-block: var(--semantics-page-sections-lg-margin-block);
		}
	}


	/* # Body */

	.one-half-one-half-section__body {
		display: flex;
		flex-direction: column;
		width: 100%;
		max-width: var(--semantics-page-sections-body-max-width);

		@container (max-width: ${unsafeCSS(breakpoints.smMax)}) {
			gap: var(--semantics-page-sections-sm-gap);
		}

		@container (min-width: ${unsafeCSS(breakpoints.mdMin)}) and (max-width: ${unsafeCSS(breakpoints.mdMax)}) {
			gap: var(--semantics-page-sections-md-gap);
		}

		@container (min-width: ${unsafeCSS(breakpoints.lgMin)}) {
			gap: var(--semantics-page-sections-lg-gap);
		}
	}


	/* # Columns */

	.one-half-one-half-section__columns {
		display: flex;
		flex-wrap: wrap;

		@container (max-width: ${unsafeCSS(breakpoints.smMax)}) {
			gap: var(--semantics-page-sections-sm-gap);
		}

		@container (min-width: ${unsafeCSS(breakpoints.mdMin)}) and (max-width: ${unsafeCSS(breakpoints.mdMax)}) {
			gap: var(--semantics-page-sections-md-gap);
		}

		@container (min-width: ${unsafeCSS(breakpoints.lgMin)}) {
			gap: var(--semantics-page-sections-lg-gap);
		}
	}

	.one-half-one-half-section__left-column {
		flex: 1;
		min-width: var(--primitives-area-280);
	}

	.one-half-one-half-section__right-column {
		flex: 1;
		min-width: var(--primitives-area-280);
	}
`;
function oneHalfOneHalfSectionTemplate(_component) {
  return html`
		<section class="one-half-one-half-section">
			<div class="one-half-one-half-section__body">
				<slot name="header"></slot>
				<div class="one-half-one-half-section__columns">
					<div class="one-half-one-half-section__left-column">
						<slot></slot>
						<slot name="left"></slot>
					</div>
					<div class="one-half-one-half-section__right-column">
						<slot name="right"></slot>
					</div>
				</div>
				<slot name="footer"></slot>
			</div>
		</section>
	`;
}
var __getOwnPropDesc$n = Object.getOwnPropertyDescriptor;
var __decorateClass$n = (decorators, target, key, kind) => {
  var result = kind > 1 ? void 0 : kind ? __getOwnPropDesc$n(target, key) : target;
  for (var i = decorators.length - 1, decorator; i >= 0; i--)
    if (decorator = decorators[i])
      result = decorator(result) || result;
  return result;
};
let NDDOneHalfOneHalfSection = class extends LitElement {
  render() {
    return oneHalfOneHalfSectionTemplate();
  }
};
NDDOneHalfOneHalfSection.styles = oneHalfOneHalfSectionStyles;
NDDOneHalfOneHalfSection = __decorateClass$n([
  customElement("ndd-one-half-one-half-section")
], NDDOneHalfOneHalfSection);
const boxStyles = css`
	:host {
		display: block;
	}

	:host([hidden]) {
		display: none;
	}

	.box {
		background-color: var(--components-box-background-color);
		border-radius: var(--components-box-corner-radius);
		padding: var(--components-box-padding);
		box-sizing: border-box;
	}
`;
function boxTemplate(_component) {
  return html`
		<div class="box">
			<slot></slot>
		</div>
	`;
}
var __getOwnPropDesc$m = Object.getOwnPropertyDescriptor;
var __decorateClass$m = (decorators, target, key, kind) => {
  var result = kind > 1 ? void 0 : kind ? __getOwnPropDesc$m(target, key) : target;
  for (var i = decorators.length - 1, decorator; i >= 0; i--)
    if (decorator = decorators[i])
      result = decorator(result) || result;
  return result;
};
let NDDBox = class extends LitElement {
  render() {
    return boxTemplate();
  }
};
NDDBox.styles = boxStyles;
NDDBox = __decorateClass$m([
  customElement("ndd-box")
], NDDBox);
const collectionStyles = css`
	:host {
		display: flex;
		flex-direction: column;
		width: 100%;
		min-width: 0;
		gap: 16px;
	}

	:host([hidden]) {
		display: none;
	}


	/* # Items */

	.collection__items {
		display: flex;
		width: 100%;
		gap: 16px;
	}


	/* # Grid */

	:host([layout='grid']) .collection__items,
	:host(:not([layout])) .collection__items {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(var(--primitives-area-280), 1fr));
	}


	/* # List */

	:host([layout='list']) .collection__items {
		flex-direction: column;
	}


	/* # Horizontal scroll */

	:host([layout='horizontal-scroll']) .collection__items {
		flex-direction: row;
		flex-wrap: nowrap;
		overflow-x: auto;
		scroll-snap-type: x mandatory;
		scroll-behavior: smooth;
		-webkit-overflow-scrolling: touch;
		scrollbar-width: none;
		gap: var(--primitives-space-16);
		margin-inline-start: -16px;
		padding-inline-start: 16px;
		scroll-padding-inline-start: 16px;
		mask-image: linear-gradient(
			to right,
			transparent 0,
			black 16px,
			black calc(100% - 48px),
			transparent 100%
		);
	}

	:host([layout='horizontal-scroll']) .collection__items::after {
		content: '';
		flex: 0 0 48px;
	}

	:host([layout='horizontal-scroll']) .collection__items::-webkit-scrollbar {
		display: none;
	}

	:host([layout='horizontal-scroll']) .collection__items ::slotted(*) {
		flex-grow: 1;
		flex-shrink: 0;
		flex-basis: var(--primitives-area-280);
		scroll-snap-align: start;
	}


	/* # Footer */

	.collection__footer {
		display: flex;
		width: 100%;
	}


	/* # Load more (grid/list) */

	:host([layout='grid']) .collection__footer,
	:host([layout='list']) .collection__footer,
	:host(:not([layout])) .collection__footer {
		justify-content: stretch;
	}

	:host([layout='grid']) .collection__footer ndd-button,
	:host([layout='list']) .collection__footer ndd-button,
	:host(:not([layout])) .collection__footer ndd-button {
		width: 100%;
	}

	:host([layout='grid']) .collection__footer ndd-button::part(button),
	:host([layout='list']) .collection__footer ndd-button::part(button),
	:host(:not([layout])) .collection__footer ndd-button::part(button) {
		width: 100%;
	}


	/* # Scroll navigation (horizontal scroll) */

	:host([layout='horizontal-scroll']) .collection__footer {
		justify-content: flex-end;
		gap: var(--primitives-space-16);
	}
`;
function collectionTemplate(component) {
  const isHorizontal = component.layout === "horizontal-scroll";
  const showLoadMore = !isHorizontal && component.showLoadMore && component._hasMore;
  return html`
		<div class="collection__items">
			<slot @slotchange=${(e) => component._onSlotChange(e)}></slot>
		</div>
		<footer class="collection__footer">
			<slot name="footer">
				${isHorizontal ? html`
					<ndd-button-bar>
						<ndd-icon-button
							icon="chevron-left"
							text=${component._t("components.collection.previous-action")}
							?disabled=${component._atStart}
							@click=${() => component._scrollBy(-1)}
						></ndd-icon-button>
						<ndd-button-bar-divider></ndd-button-bar-divider>
						<ndd-icon-button
							icon="chevron-right"
							text=${component._t("components.collection.next-action")}
							?disabled=${component._atEnd}
							@click=${() => component._scrollBy(1)}
						></ndd-icon-button>
					</ndd-button-bar>
				` : nothing}
				${showLoadMore ? html`
					<ndd-button
						variant="neutral-tinted"
						text=${component._t("components.collection.load-more-action")}
						@click=${() => component._loadMore()}
					></ndd-button>
				` : nothing}
			</slot>
		</footer>
	`;
}
const nddCollectionTranslations = {
  "components.collection.previous-action": "Vorige",
  "components.collection.next-action": "Volgende",
  "components.collection.load-more-action": "Toon meer"
};
var __defProp$k = Object.defineProperty;
var __getOwnPropDesc$l = Object.getOwnPropertyDescriptor;
var __decorateClass$l = (decorators, target, key, kind) => {
  var result = kind > 1 ? void 0 : kind ? __getOwnPropDesc$l(target, key) : target;
  for (var i = decorators.length - 1, decorator; i >= 0; i--)
    if (decorator = decorators[i])
      result = (kind ? decorator(target, key, result) : decorator(result)) || result;
  if (kind && result) __defProp$k(target, key, result);
  return result;
};
let NDDCollection = class extends LitElement {
  constructor() {
    super(...arguments);
    this.layout = "grid";
    this.showLoadMore = false;
    this.maxItems = 24;
    this.lazyLoad = false;
    this.translations = {};
    this._visibleCount = 0;
    this._totalCount = 0;
    this._atStart = true;
    this._atEnd = false;
    this._scrollListener = () => {
      const el = this._itemsEl;
      if (!el) return;
      this._atStart = el.scrollLeft < 1;
      this._atEnd = el.scrollLeft + el.clientWidth >= el.scrollWidth - 1;
    };
    this._scrollListenerAttached = false;
  }
  // — i18n —————————————————————————————————————————————————————————————————
  _t(key) {
    return this.translations[key] ?? nddCollectionTranslations[key];
  }
  connectedCallback() {
    super.connectedCallback();
    this._visibleCount = this.maxItems;
  }
  disconnectedCallback() {
    super.disconnectedCallback();
    this._intersectionObserver?.disconnect();
    this._teardownScrollListeners();
  }
  updated(changedProperties) {
    if (changedProperties.has("layout")) {
      this._setupScrollListeners();
    }
    if (this.lazyLoad && this._loadMoreBtn && !this._intersectionObserver) {
      this._intersectionObserver = new IntersectionObserver(
        ([entry]) => {
          if (entry.isIntersecting) this._loadMore();
        },
        { threshold: 0.1 }
      );
      this._intersectionObserver.observe(this._loadMoreBtn);
    } else if (!this._loadMoreBtn) {
      this._intersectionObserver?.disconnect();
      this._intersectionObserver = void 0;
    }
  }
  _setupScrollListeners() {
    this._teardownScrollListeners();
    if (this.layout === "horizontal-scroll" && this._itemsEl) {
      this._itemsEl.addEventListener("scroll", this._scrollListener, { passive: true });
      this._resizeObserver = new ResizeObserver(() => this._scrollListener());
      this._resizeObserver.observe(this._itemsEl);
      this._scrollListenerAttached = true;
    }
  }
  _teardownScrollListeners() {
    this._itemsEl?.removeEventListener("scroll", this._scrollListener);
    this._resizeObserver?.disconnect();
    this._resizeObserver = void 0;
    this._scrollListenerAttached = false;
  }
  _onSlotChange(e) {
    const slot = e.target;
    const items = slot.assignedElements();
    this._totalCount = items.length;
    if (this.layout !== "horizontal-scroll") {
      this._applyVisibility(items);
    }
  }
  _applyVisibility(items) {
    const slot = this._itemsEl?.querySelector("slot");
    const elements = items ?? (slot?.assignedElements() ?? []);
    elements.forEach((el, i) => {
      el.hidden = i >= this._visibleCount;
    });
  }
  _loadMore() {
    this._visibleCount = Math.min(this._visibleCount + this.maxItems, this._totalCount);
    this._applyVisibility();
    this.dispatchEvent(new CustomEvent("load-more", { bubbles: true, composed: true }));
  }
  get _hasMore() {
    return this._visibleCount < this._totalCount;
  }
  _scrollBy(direction) {
    const slot = this._itemsEl?.querySelector("slot");
    const firstItem = slot?.assignedElements()[0];
    const itemWidth = firstItem?.offsetWidth ?? 280;
    this._itemsEl?.scrollBy({ left: direction * (itemWidth + 16), behavior: "smooth" });
  }
  render() {
    return collectionTemplate(this);
  }
};
NDDCollection.styles = collectionStyles;
__decorateClass$l([
  property({ type: String, reflect: true })
], NDDCollection.prototype, "layout", 2);
__decorateClass$l([
  property({ type: Boolean, reflect: true, attribute: "show-load-more" })
], NDDCollection.prototype, "showLoadMore", 2);
__decorateClass$l([
  property({ type: Number, attribute: "max-items" })
], NDDCollection.prototype, "maxItems", 2);
__decorateClass$l([
  property({ type: Boolean, reflect: true, attribute: "lazy-load" })
], NDDCollection.prototype, "lazyLoad", 2);
__decorateClass$l([
  property({ type: Object })
], NDDCollection.prototype, "translations", 2);
__decorateClass$l([
  state()
], NDDCollection.prototype, "_visibleCount", 2);
__decorateClass$l([
  state()
], NDDCollection.prototype, "_totalCount", 2);
__decorateClass$l([
  state()
], NDDCollection.prototype, "_atStart", 2);
__decorateClass$l([
  state()
], NDDCollection.prototype, "_atEnd", 2);
__decorateClass$l([
  query(".collection__items")
], NDDCollection.prototype, "_itemsEl", 2);
__decorateClass$l([
  query("ndd-button.load-more")
], NDDCollection.prototype, "_loadMoreBtn", 2);
NDDCollection = __decorateClass$l([
  customElement("ndd-collection")
], NDDCollection);
const spacerStyles = css`
	:host {
		display: block;
		flex-shrink: 0;
	}

	:host([hidden]) {
		display: none;
	}


	/* # Flexible and responsive */

	:host([size='flexible']) {
		flex: 1;
		min-width: 0;
		min-height: 0;
	}

	:host([size='md']) {
		width: var(--primitives-space-16);
		height: var(--primitives-space-16);

		@media (min-width: ${unsafeCSS(breakpoints.smMax)}) {
			width: var(--primitives-space-24);
			height: var(--primitives-space-24);
		}
	}


	/* # Fixed sizes */

	:host([size='2']) {
		width: var(--primitives-space-2);
		height: var(--primitives-space-2);
	}

	:host([size='4']) {
		width: var(--primitives-space-4);
		height: var(--primitives-space-4);
	}

	:host([size='6']) {
		width: var(--primitives-space-6);
		height: var(--primitives-space-6);
	}

	:host([size='16']),
	:host(:not([size])) {
		width: var(--primitives-space-16);
		height: var(--primitives-space-16);
	}

	:host([size='8']) {
		width: var(--primitives-space-8);
		height: var(--primitives-space-8);
	}

	:host([size='10']) {
		width: var(--primitives-space-10);
		height: var(--primitives-space-10);
	}

	:host([size='12']) {
		width: var(--primitives-space-12);
		height: var(--primitives-space-12);
	}

	:host([size='16']) {
		width: var(--primitives-space-16);
		height: var(--primitives-space-16);
	}

	:host([size='20']) {
		width: var(--primitives-space-20);
		height: var(--primitives-space-20);
	}

	:host([size='24']) {
		width: var(--primitives-space-24);
		height: var(--primitives-space-24);
	}

	:host([size='28']) {
		width: var(--primitives-space-28);
		height: var(--primitives-space-28);
	}

	:host([size='32']) {
		width: var(--primitives-space-32);
		height: var(--primitives-space-32);
	}

	:host([size='40']) {
		width: var(--primitives-space-40);
		height: var(--primitives-space-40);
	}

	:host([size='44']) {
		width: var(--primitives-space-44);
		height: var(--primitives-space-44);
	}

	:host([size='48']) {
		width: var(--primitives-space-48);
		height: var(--primitives-space-48);
	}

	:host([size='56']) {
		width: var(--primitives-space-56);
		height: var(--primitives-space-56);
	}

	:host([size='64']) {
		width: var(--primitives-space-64);
		height: var(--primitives-space-64);
	}

	:host([size='80']) {
		width: var(--primitives-space-80);
		height: var(--primitives-space-80);
	}

	:host([size='96']) {
		width: var(--primitives-space-96);
		height: var(--primitives-space-96);
	}


	/* # Direction modifiers */

	:host([direction='horizontal']) {
		height: auto;
	}

	:host([direction='vertical']) {
		width: auto;
	}

	:host([size='flexible'][direction='horizontal']) {
		height: auto;
		min-height: auto;
	}

	:host([size='flexible'][direction='vertical']) {
		width: auto;
		min-width: auto;
	}
`;
var __defProp$j = Object.defineProperty;
var __getOwnPropDesc$k = Object.getOwnPropertyDescriptor;
var __decorateClass$k = (decorators, target, key, kind) => {
  var result = kind > 1 ? void 0 : kind ? __getOwnPropDesc$k(target, key) : target;
  for (var i = decorators.length - 1, decorator; i >= 0; i--)
    if (decorator = decorators[i])
      result = (kind ? decorator(target, key, result) : decorator(result)) || result;
  if (kind && result) __defProp$j(target, key, result);
  return result;
};
let NDDSpacer = class extends LitElement {
  constructor() {
    super(...arguments);
    this.size = "16";
    this.direction = "both";
  }
};
NDDSpacer.styles = spacerStyles;
__decorateClass$k([
  property({ type: String, reflect: true })
], NDDSpacer.prototype, "size", 2);
__decorateClass$k([
  property({ type: String, reflect: true })
], NDDSpacer.prototype, "direction", 2);
NDDSpacer = __decorateClass$k([
  customElement("ndd-spacer")
], NDDSpacer);
const smMax$2 = unsafeCSS(breakpoints.smMax);
const mdMin$3 = unsafeCSS(breakpoints.mdMin);
const mdMax$1 = unsafeCSS(breakpoints.mdMax);
const lgMin$2 = unsafeCSS(breakpoints.lgMin);
const containerStyles = css`
	:host {
		display: block;
	}

	:host([hidden]) {
		display: none;
	}

	.container {
		height: 100%;
	}

	/* # Padding — base */

	:host([padding="0"]) .container { padding: 0; }
	:host([padding="2"]) .container { padding: var(--primitives-space-2); }
	:host([padding="4"]) .container { padding: var(--primitives-space-4); }
	:host([padding="6"]) .container { padding: var(--primitives-space-6); }
	:host([padding="8"]) .container { padding: var(--primitives-space-8); }
	:host([padding="10"]) .container { padding: var(--primitives-space-10); }
	:host([padding="12"]) .container { padding: var(--primitives-space-12); }
	:host([padding="16"]) .container { padding: var(--primitives-space-16); }
	:host([padding="20"]) .container { padding: var(--primitives-space-20); }
	:host([padding="24"]) .container { padding: var(--primitives-space-24); }
	:host([padding="28"]) .container { padding: var(--primitives-space-28); }
	:host([padding="32"]) .container { padding: var(--primitives-space-32); }
	:host([padding="40"]) .container { padding: var(--primitives-space-40); }
	:host([padding="44"]) .container { padding: var(--primitives-space-44); }
	:host([padding="48"]) .container { padding: var(--primitives-space-48); }
	:host([padding="56"]) .container { padding: var(--primitives-space-56); }
	:host([padding="64"]) .container { padding: var(--primitives-space-64); }
	:host([padding="80"]) .container { padding: var(--primitives-space-80); }
	:host([padding="96"]) .container { padding: var(--primitives-space-96); }

	/* # Padding — sm viewport */

	:host([sm-padding="0"]) .container { @media (max-width: ${smMax$2}) { padding: 0; } }
	:host([sm-padding="2"]) .container { @media (max-width: ${smMax$2}) { padding: var(--primitives-space-2); } }
	:host([sm-padding="4"]) .container { @media (max-width: ${smMax$2}) { padding: var(--primitives-space-4); } }
	:host([sm-padding="6"]) .container { @media (max-width: ${smMax$2}) { padding: var(--primitives-space-6); } }
	:host([sm-padding="8"]) .container { @media (max-width: ${smMax$2}) { padding: var(--primitives-space-8); } }
	:host([sm-padding="10"]) .container { @media (max-width: ${smMax$2}) { padding: var(--primitives-space-10); } }
	:host([sm-padding="12"]) .container { @media (max-width: ${smMax$2}) { padding: var(--primitives-space-12); } }
	:host([sm-padding="16"]) .container { @media (max-width: ${smMax$2}) { padding: var(--primitives-space-16); } }
	:host([sm-padding="20"]) .container { @media (max-width: ${smMax$2}) { padding: var(--primitives-space-20); } }
	:host([sm-padding="24"]) .container { @media (max-width: ${smMax$2}) { padding: var(--primitives-space-24); } }
	:host([sm-padding="28"]) .container { @media (max-width: ${smMax$2}) { padding: var(--primitives-space-28); } }
	:host([sm-padding="32"]) .container { @media (max-width: ${smMax$2}) { padding: var(--primitives-space-32); } }
	:host([sm-padding="40"]) .container { @media (max-width: ${smMax$2}) { padding: var(--primitives-space-40); } }
	:host([sm-padding="44"]) .container { @media (max-width: ${smMax$2}) { padding: var(--primitives-space-44); } }
	:host([sm-padding="48"]) .container { @media (max-width: ${smMax$2}) { padding: var(--primitives-space-48); } }
	:host([sm-padding="56"]) .container { @media (max-width: ${smMax$2}) { padding: var(--primitives-space-56); } }
	:host([sm-padding="64"]) .container { @media (max-width: ${smMax$2}) { padding: var(--primitives-space-64); } }
	:host([sm-padding="80"]) .container { @media (max-width: ${smMax$2}) { padding: var(--primitives-space-80); } }
	:host([sm-padding="96"]) .container { @media (max-width: ${smMax$2}) { padding: var(--primitives-space-96); } }

	/* # Padding — md viewport */

	:host([md-padding="0"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding: 0; } }
	:host([md-padding="2"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding: var(--primitives-space-2); } }
	:host([md-padding="4"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding: var(--primitives-space-4); } }
	:host([md-padding="6"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding: var(--primitives-space-6); } }
	:host([md-padding="8"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding: var(--primitives-space-8); } }
	:host([md-padding="10"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding: var(--primitives-space-10); } }
	:host([md-padding="12"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding: var(--primitives-space-12); } }
	:host([md-padding="16"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding: var(--primitives-space-16); } }
	:host([md-padding="20"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding: var(--primitives-space-20); } }
	:host([md-padding="24"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding: var(--primitives-space-24); } }
	:host([md-padding="28"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding: var(--primitives-space-28); } }
	:host([md-padding="32"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding: var(--primitives-space-32); } }
	:host([md-padding="40"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding: var(--primitives-space-40); } }
	:host([md-padding="44"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding: var(--primitives-space-44); } }
	:host([md-padding="48"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding: var(--primitives-space-48); } }
	:host([md-padding="56"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding: var(--primitives-space-56); } }
	:host([md-padding="64"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding: var(--primitives-space-64); } }
	:host([md-padding="80"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding: var(--primitives-space-80); } }
	:host([md-padding="96"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding: var(--primitives-space-96); } }

	/* # Padding — lg viewport */

	:host([lg-padding="0"]) .container { @media (min-width: ${lgMin$2}) { padding: 0; } }
	:host([lg-padding="2"]) .container { @media (min-width: ${lgMin$2}) { padding: var(--primitives-space-2); } }
	:host([lg-padding="4"]) .container { @media (min-width: ${lgMin$2}) { padding: var(--primitives-space-4); } }
	:host([lg-padding="6"]) .container { @media (min-width: ${lgMin$2}) { padding: var(--primitives-space-6); } }
	:host([lg-padding="8"]) .container { @media (min-width: ${lgMin$2}) { padding: var(--primitives-space-8); } }
	:host([lg-padding="10"]) .container { @media (min-width: ${lgMin$2}) { padding: var(--primitives-space-10); } }
	:host([lg-padding="12"]) .container { @media (min-width: ${lgMin$2}) { padding: var(--primitives-space-12); } }
	:host([lg-padding="16"]) .container { @media (min-width: ${lgMin$2}) { padding: var(--primitives-space-16); } }
	:host([lg-padding="20"]) .container { @media (min-width: ${lgMin$2}) { padding: var(--primitives-space-20); } }
	:host([lg-padding="24"]) .container { @media (min-width: ${lgMin$2}) { padding: var(--primitives-space-24); } }
	:host([lg-padding="28"]) .container { @media (min-width: ${lgMin$2}) { padding: var(--primitives-space-28); } }
	:host([lg-padding="32"]) .container { @media (min-width: ${lgMin$2}) { padding: var(--primitives-space-32); } }
	:host([lg-padding="40"]) .container { @media (min-width: ${lgMin$2}) { padding: var(--primitives-space-40); } }
	:host([lg-padding="44"]) .container { @media (min-width: ${lgMin$2}) { padding: var(--primitives-space-44); } }
	:host([lg-padding="48"]) .container { @media (min-width: ${lgMin$2}) { padding: var(--primitives-space-48); } }
	:host([lg-padding="56"]) .container { @media (min-width: ${lgMin$2}) { padding: var(--primitives-space-56); } }
	:host([lg-padding="64"]) .container { @media (min-width: ${lgMin$2}) { padding: var(--primitives-space-64); } }
	:host([lg-padding="80"]) .container { @media (min-width: ${lgMin$2}) { padding: var(--primitives-space-80); } }
	:host([lg-padding="96"]) .container { @media (min-width: ${lgMin$2}) { padding: var(--primitives-space-96); } }

	/* # Padding — sm container */

	:host([layout-area-sm-padding="0"]) .container { @container layout-area (max-width: ${smMax$2}) { padding: 0; } }
	:host([layout-area-sm-padding="2"]) .container { @container layout-area (max-width: ${smMax$2}) { padding: var(--primitives-space-2); } }
	:host([layout-area-sm-padding="4"]) .container { @container layout-area (max-width: ${smMax$2}) { padding: var(--primitives-space-4); } }
	:host([layout-area-sm-padding="6"]) .container { @container layout-area (max-width: ${smMax$2}) { padding: var(--primitives-space-6); } }
	:host([layout-area-sm-padding="8"]) .container { @container layout-area (max-width: ${smMax$2}) { padding: var(--primitives-space-8); } }
	:host([layout-area-sm-padding="10"]) .container { @container layout-area (max-width: ${smMax$2}) { padding: var(--primitives-space-10); } }
	:host([layout-area-sm-padding="12"]) .container { @container layout-area (max-width: ${smMax$2}) { padding: var(--primitives-space-12); } }
	:host([layout-area-sm-padding="16"]) .container { @container layout-area (max-width: ${smMax$2}) { padding: var(--primitives-space-16); } }
	:host([layout-area-sm-padding="20"]) .container { @container layout-area (max-width: ${smMax$2}) { padding: var(--primitives-space-20); } }
	:host([layout-area-sm-padding="24"]) .container { @container layout-area (max-width: ${smMax$2}) { padding: var(--primitives-space-24); } }
	:host([layout-area-sm-padding="28"]) .container { @container layout-area (max-width: ${smMax$2}) { padding: var(--primitives-space-28); } }
	:host([layout-area-sm-padding="32"]) .container { @container layout-area (max-width: ${smMax$2}) { padding: var(--primitives-space-32); } }
	:host([layout-area-sm-padding="40"]) .container { @container layout-area (max-width: ${smMax$2}) { padding: var(--primitives-space-40); } }
	:host([layout-area-sm-padding="44"]) .container { @container layout-area (max-width: ${smMax$2}) { padding: var(--primitives-space-44); } }
	:host([layout-area-sm-padding="48"]) .container { @container layout-area (max-width: ${smMax$2}) { padding: var(--primitives-space-48); } }
	:host([layout-area-sm-padding="56"]) .container { @container layout-area (max-width: ${smMax$2}) { padding: var(--primitives-space-56); } }
	:host([layout-area-sm-padding="64"]) .container { @container layout-area (max-width: ${smMax$2}) { padding: var(--primitives-space-64); } }
	:host([layout-area-sm-padding="80"]) .container { @container layout-area (max-width: ${smMax$2}) { padding: var(--primitives-space-80); } }
	:host([layout-area-sm-padding="96"]) .container { @container layout-area (max-width: ${smMax$2}) { padding: var(--primitives-space-96); } }

	/* # Padding — md container */

	:host([layout-area-md-padding="0"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding: 0; } }
	:host([layout-area-md-padding="2"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding: var(--primitives-space-2); } }
	:host([layout-area-md-padding="4"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding: var(--primitives-space-4); } }
	:host([layout-area-md-padding="6"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding: var(--primitives-space-6); } }
	:host([layout-area-md-padding="8"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding: var(--primitives-space-8); } }
	:host([layout-area-md-padding="10"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding: var(--primitives-space-10); } }
	:host([layout-area-md-padding="12"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding: var(--primitives-space-12); } }
	:host([layout-area-md-padding="16"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding: var(--primitives-space-16); } }
	:host([layout-area-md-padding="20"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding: var(--primitives-space-20); } }
	:host([layout-area-md-padding="24"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding: var(--primitives-space-24); } }
	:host([layout-area-md-padding="28"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding: var(--primitives-space-28); } }
	:host([layout-area-md-padding="32"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding: var(--primitives-space-32); } }
	:host([layout-area-md-padding="40"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding: var(--primitives-space-40); } }
	:host([layout-area-md-padding="44"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding: var(--primitives-space-44); } }
	:host([layout-area-md-padding="48"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding: var(--primitives-space-48); } }
	:host([layout-area-md-padding="56"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding: var(--primitives-space-56); } }
	:host([layout-area-md-padding="64"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding: var(--primitives-space-64); } }
	:host([layout-area-md-padding="80"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding: var(--primitives-space-80); } }
	:host([layout-area-md-padding="96"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding: var(--primitives-space-96); } }

	/* # Padding — lg container */

	:host([layout-area-lg-padding="0"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding: 0; } }
	:host([layout-area-lg-padding="2"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding: var(--primitives-space-2); } }
	:host([layout-area-lg-padding="4"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding: var(--primitives-space-4); } }
	:host([layout-area-lg-padding="6"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding: var(--primitives-space-6); } }
	:host([layout-area-lg-padding="8"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding: var(--primitives-space-8); } }
	:host([layout-area-lg-padding="10"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding: var(--primitives-space-10); } }
	:host([layout-area-lg-padding="12"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding: var(--primitives-space-12); } }
	:host([layout-area-lg-padding="16"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding: var(--primitives-space-16); } }
	:host([layout-area-lg-padding="20"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding: var(--primitives-space-20); } }
	:host([layout-area-lg-padding="24"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding: var(--primitives-space-24); } }
	:host([layout-area-lg-padding="28"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding: var(--primitives-space-28); } }
	:host([layout-area-lg-padding="32"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding: var(--primitives-space-32); } }
	:host([layout-area-lg-padding="40"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding: var(--primitives-space-40); } }
	:host([layout-area-lg-padding="44"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding: var(--primitives-space-44); } }
	:host([layout-area-lg-padding="48"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding: var(--primitives-space-48); } }
	:host([layout-area-lg-padding="56"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding: var(--primitives-space-56); } }
	:host([layout-area-lg-padding="64"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding: var(--primitives-space-64); } }
	:host([layout-area-lg-padding="80"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding: var(--primitives-space-80); } }
	:host([layout-area-lg-padding="96"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding: var(--primitives-space-96); } }

	/* # Padding Inline — base */

	:host([padding-inline="0"]) .container { padding-inline: 0; }
	:host([padding-inline="2"]) .container { padding-inline: var(--primitives-space-2); }
	:host([padding-inline="4"]) .container { padding-inline: var(--primitives-space-4); }
	:host([padding-inline="6"]) .container { padding-inline: var(--primitives-space-6); }
	:host([padding-inline="8"]) .container { padding-inline: var(--primitives-space-8); }
	:host([padding-inline="10"]) .container { padding-inline: var(--primitives-space-10); }
	:host([padding-inline="12"]) .container { padding-inline: var(--primitives-space-12); }
	:host([padding-inline="16"]) .container { padding-inline: var(--primitives-space-16); }
	:host([padding-inline="20"]) .container { padding-inline: var(--primitives-space-20); }
	:host([padding-inline="24"]) .container { padding-inline: var(--primitives-space-24); }
	:host([padding-inline="28"]) .container { padding-inline: var(--primitives-space-28); }
	:host([padding-inline="32"]) .container { padding-inline: var(--primitives-space-32); }
	:host([padding-inline="40"]) .container { padding-inline: var(--primitives-space-40); }
	:host([padding-inline="44"]) .container { padding-inline: var(--primitives-space-44); }
	:host([padding-inline="48"]) .container { padding-inline: var(--primitives-space-48); }
	:host([padding-inline="56"]) .container { padding-inline: var(--primitives-space-56); }
	:host([padding-inline="64"]) .container { padding-inline: var(--primitives-space-64); }
	:host([padding-inline="80"]) .container { padding-inline: var(--primitives-space-80); }
	:host([padding-inline="96"]) .container { padding-inline: var(--primitives-space-96); }

	/* # Padding Inline — sm viewport */

	:host([sm-padding-inline="0"]) .container { @media (max-width: ${smMax$2}) { padding-inline: 0; } }
	:host([sm-padding-inline="2"]) .container { @media (max-width: ${smMax$2}) { padding-inline: var(--primitives-space-2); } }
	:host([sm-padding-inline="4"]) .container { @media (max-width: ${smMax$2}) { padding-inline: var(--primitives-space-4); } }
	:host([sm-padding-inline="6"]) .container { @media (max-width: ${smMax$2}) { padding-inline: var(--primitives-space-6); } }
	:host([sm-padding-inline="8"]) .container { @media (max-width: ${smMax$2}) { padding-inline: var(--primitives-space-8); } }
	:host([sm-padding-inline="10"]) .container { @media (max-width: ${smMax$2}) { padding-inline: var(--primitives-space-10); } }
	:host([sm-padding-inline="12"]) .container { @media (max-width: ${smMax$2}) { padding-inline: var(--primitives-space-12); } }
	:host([sm-padding-inline="16"]) .container { @media (max-width: ${smMax$2}) { padding-inline: var(--primitives-space-16); } }
	:host([sm-padding-inline="20"]) .container { @media (max-width: ${smMax$2}) { padding-inline: var(--primitives-space-20); } }
	:host([sm-padding-inline="24"]) .container { @media (max-width: ${smMax$2}) { padding-inline: var(--primitives-space-24); } }
	:host([sm-padding-inline="28"]) .container { @media (max-width: ${smMax$2}) { padding-inline: var(--primitives-space-28); } }
	:host([sm-padding-inline="32"]) .container { @media (max-width: ${smMax$2}) { padding-inline: var(--primitives-space-32); } }
	:host([sm-padding-inline="40"]) .container { @media (max-width: ${smMax$2}) { padding-inline: var(--primitives-space-40); } }
	:host([sm-padding-inline="44"]) .container { @media (max-width: ${smMax$2}) { padding-inline: var(--primitives-space-44); } }
	:host([sm-padding-inline="48"]) .container { @media (max-width: ${smMax$2}) { padding-inline: var(--primitives-space-48); } }
	:host([sm-padding-inline="56"]) .container { @media (max-width: ${smMax$2}) { padding-inline: var(--primitives-space-56); } }
	:host([sm-padding-inline="64"]) .container { @media (max-width: ${smMax$2}) { padding-inline: var(--primitives-space-64); } }
	:host([sm-padding-inline="80"]) .container { @media (max-width: ${smMax$2}) { padding-inline: var(--primitives-space-80); } }
	:host([sm-padding-inline="96"]) .container { @media (max-width: ${smMax$2}) { padding-inline: var(--primitives-space-96); } }

	/* # Padding Inline — md viewport */

	:host([md-padding-inline="0"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-inline: 0; } }
	:host([md-padding-inline="2"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-inline: var(--primitives-space-2); } }
	:host([md-padding-inline="4"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-inline: var(--primitives-space-4); } }
	:host([md-padding-inline="6"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-inline: var(--primitives-space-6); } }
	:host([md-padding-inline="8"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-inline: var(--primitives-space-8); } }
	:host([md-padding-inline="10"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-inline: var(--primitives-space-10); } }
	:host([md-padding-inline="12"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-inline: var(--primitives-space-12); } }
	:host([md-padding-inline="16"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-inline: var(--primitives-space-16); } }
	:host([md-padding-inline="20"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-inline: var(--primitives-space-20); } }
	:host([md-padding-inline="24"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-inline: var(--primitives-space-24); } }
	:host([md-padding-inline="28"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-inline: var(--primitives-space-28); } }
	:host([md-padding-inline="32"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-inline: var(--primitives-space-32); } }
	:host([md-padding-inline="40"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-inline: var(--primitives-space-40); } }
	:host([md-padding-inline="44"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-inline: var(--primitives-space-44); } }
	:host([md-padding-inline="48"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-inline: var(--primitives-space-48); } }
	:host([md-padding-inline="56"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-inline: var(--primitives-space-56); } }
	:host([md-padding-inline="64"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-inline: var(--primitives-space-64); } }
	:host([md-padding-inline="80"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-inline: var(--primitives-space-80); } }
	:host([md-padding-inline="96"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-inline: var(--primitives-space-96); } }

	/* # Padding Inline — lg viewport */

	:host([lg-padding-inline="0"]) .container { @media (min-width: ${lgMin$2}) { padding-inline: 0; } }
	:host([lg-padding-inline="2"]) .container { @media (min-width: ${lgMin$2}) { padding-inline: var(--primitives-space-2); } }
	:host([lg-padding-inline="4"]) .container { @media (min-width: ${lgMin$2}) { padding-inline: var(--primitives-space-4); } }
	:host([lg-padding-inline="6"]) .container { @media (min-width: ${lgMin$2}) { padding-inline: var(--primitives-space-6); } }
	:host([lg-padding-inline="8"]) .container { @media (min-width: ${lgMin$2}) { padding-inline: var(--primitives-space-8); } }
	:host([lg-padding-inline="10"]) .container { @media (min-width: ${lgMin$2}) { padding-inline: var(--primitives-space-10); } }
	:host([lg-padding-inline="12"]) .container { @media (min-width: ${lgMin$2}) { padding-inline: var(--primitives-space-12); } }
	:host([lg-padding-inline="16"]) .container { @media (min-width: ${lgMin$2}) { padding-inline: var(--primitives-space-16); } }
	:host([lg-padding-inline="20"]) .container { @media (min-width: ${lgMin$2}) { padding-inline: var(--primitives-space-20); } }
	:host([lg-padding-inline="24"]) .container { @media (min-width: ${lgMin$2}) { padding-inline: var(--primitives-space-24); } }
	:host([lg-padding-inline="28"]) .container { @media (min-width: ${lgMin$2}) { padding-inline: var(--primitives-space-28); } }
	:host([lg-padding-inline="32"]) .container { @media (min-width: ${lgMin$2}) { padding-inline: var(--primitives-space-32); } }
	:host([lg-padding-inline="40"]) .container { @media (min-width: ${lgMin$2}) { padding-inline: var(--primitives-space-40); } }
	:host([lg-padding-inline="44"]) .container { @media (min-width: ${lgMin$2}) { padding-inline: var(--primitives-space-44); } }
	:host([lg-padding-inline="48"]) .container { @media (min-width: ${lgMin$2}) { padding-inline: var(--primitives-space-48); } }
	:host([lg-padding-inline="56"]) .container { @media (min-width: ${lgMin$2}) { padding-inline: var(--primitives-space-56); } }
	:host([lg-padding-inline="64"]) .container { @media (min-width: ${lgMin$2}) { padding-inline: var(--primitives-space-64); } }
	:host([lg-padding-inline="80"]) .container { @media (min-width: ${lgMin$2}) { padding-inline: var(--primitives-space-80); } }
	:host([lg-padding-inline="96"]) .container { @media (min-width: ${lgMin$2}) { padding-inline: var(--primitives-space-96); } }

	/* # Padding Inline — sm container */

	:host([layout-area-sm-padding-inline="0"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-inline: 0; } }
	:host([layout-area-sm-padding-inline="2"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-inline: var(--primitives-space-2); } }
	:host([layout-area-sm-padding-inline="4"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-inline: var(--primitives-space-4); } }
	:host([layout-area-sm-padding-inline="6"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-inline: var(--primitives-space-6); } }
	:host([layout-area-sm-padding-inline="8"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-inline: var(--primitives-space-8); } }
	:host([layout-area-sm-padding-inline="10"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-inline: var(--primitives-space-10); } }
	:host([layout-area-sm-padding-inline="12"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-inline: var(--primitives-space-12); } }
	:host([layout-area-sm-padding-inline="16"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-inline: var(--primitives-space-16); } }
	:host([layout-area-sm-padding-inline="20"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-inline: var(--primitives-space-20); } }
	:host([layout-area-sm-padding-inline="24"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-inline: var(--primitives-space-24); } }
	:host([layout-area-sm-padding-inline="28"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-inline: var(--primitives-space-28); } }
	:host([layout-area-sm-padding-inline="32"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-inline: var(--primitives-space-32); } }
	:host([layout-area-sm-padding-inline="40"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-inline: var(--primitives-space-40); } }
	:host([layout-area-sm-padding-inline="44"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-inline: var(--primitives-space-44); } }
	:host([layout-area-sm-padding-inline="48"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-inline: var(--primitives-space-48); } }
	:host([layout-area-sm-padding-inline="56"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-inline: var(--primitives-space-56); } }
	:host([layout-area-sm-padding-inline="64"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-inline: var(--primitives-space-64); } }
	:host([layout-area-sm-padding-inline="80"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-inline: var(--primitives-space-80); } }
	:host([layout-area-sm-padding-inline="96"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-inline: var(--primitives-space-96); } }

	/* # Padding Inline — md container */

	:host([layout-area-md-padding-inline="0"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-inline: 0; } }
	:host([layout-area-md-padding-inline="2"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-inline: var(--primitives-space-2); } }
	:host([layout-area-md-padding-inline="4"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-inline: var(--primitives-space-4); } }
	:host([layout-area-md-padding-inline="6"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-inline: var(--primitives-space-6); } }
	:host([layout-area-md-padding-inline="8"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-inline: var(--primitives-space-8); } }
	:host([layout-area-md-padding-inline="10"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-inline: var(--primitives-space-10); } }
	:host([layout-area-md-padding-inline="12"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-inline: var(--primitives-space-12); } }
	:host([layout-area-md-padding-inline="16"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-inline: var(--primitives-space-16); } }
	:host([layout-area-md-padding-inline="20"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-inline: var(--primitives-space-20); } }
	:host([layout-area-md-padding-inline="24"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-inline: var(--primitives-space-24); } }
	:host([layout-area-md-padding-inline="28"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-inline: var(--primitives-space-28); } }
	:host([layout-area-md-padding-inline="32"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-inline: var(--primitives-space-32); } }
	:host([layout-area-md-padding-inline="40"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-inline: var(--primitives-space-40); } }
	:host([layout-area-md-padding-inline="44"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-inline: var(--primitives-space-44); } }
	:host([layout-area-md-padding-inline="48"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-inline: var(--primitives-space-48); } }
	:host([layout-area-md-padding-inline="56"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-inline: var(--primitives-space-56); } }
	:host([layout-area-md-padding-inline="64"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-inline: var(--primitives-space-64); } }
	:host([layout-area-md-padding-inline="80"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-inline: var(--primitives-space-80); } }
	:host([layout-area-md-padding-inline="96"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-inline: var(--primitives-space-96); } }

	/* # Padding Inline — lg container */

	:host([layout-area-lg-padding-inline="0"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-inline: 0; } }
	:host([layout-area-lg-padding-inline="2"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-inline: var(--primitives-space-2); } }
	:host([layout-area-lg-padding-inline="4"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-inline: var(--primitives-space-4); } }
	:host([layout-area-lg-padding-inline="6"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-inline: var(--primitives-space-6); } }
	:host([layout-area-lg-padding-inline="8"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-inline: var(--primitives-space-8); } }
	:host([layout-area-lg-padding-inline="10"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-inline: var(--primitives-space-10); } }
	:host([layout-area-lg-padding-inline="12"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-inline: var(--primitives-space-12); } }
	:host([layout-area-lg-padding-inline="16"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-inline: var(--primitives-space-16); } }
	:host([layout-area-lg-padding-inline="20"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-inline: var(--primitives-space-20); } }
	:host([layout-area-lg-padding-inline="24"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-inline: var(--primitives-space-24); } }
	:host([layout-area-lg-padding-inline="28"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-inline: var(--primitives-space-28); } }
	:host([layout-area-lg-padding-inline="32"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-inline: var(--primitives-space-32); } }
	:host([layout-area-lg-padding-inline="40"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-inline: var(--primitives-space-40); } }
	:host([layout-area-lg-padding-inline="44"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-inline: var(--primitives-space-44); } }
	:host([layout-area-lg-padding-inline="48"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-inline: var(--primitives-space-48); } }
	:host([layout-area-lg-padding-inline="56"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-inline: var(--primitives-space-56); } }
	:host([layout-area-lg-padding-inline="64"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-inline: var(--primitives-space-64); } }
	:host([layout-area-lg-padding-inline="80"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-inline: var(--primitives-space-80); } }
	:host([layout-area-lg-padding-inline="96"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-inline: var(--primitives-space-96); } }

	/* # Padding Block — base */

	:host([padding-block="0"]) .container { padding-block: 0; }
	:host([padding-block="2"]) .container { padding-block: var(--primitives-space-2); }
	:host([padding-block="4"]) .container { padding-block: var(--primitives-space-4); }
	:host([padding-block="6"]) .container { padding-block: var(--primitives-space-6); }
	:host([padding-block="8"]) .container { padding-block: var(--primitives-space-8); }
	:host([padding-block="10"]) .container { padding-block: var(--primitives-space-10); }
	:host([padding-block="12"]) .container { padding-block: var(--primitives-space-12); }
	:host([padding-block="16"]) .container { padding-block: var(--primitives-space-16); }
	:host([padding-block="20"]) .container { padding-block: var(--primitives-space-20); }
	:host([padding-block="24"]) .container { padding-block: var(--primitives-space-24); }
	:host([padding-block="28"]) .container { padding-block: var(--primitives-space-28); }
	:host([padding-block="32"]) .container { padding-block: var(--primitives-space-32); }
	:host([padding-block="40"]) .container { padding-block: var(--primitives-space-40); }
	:host([padding-block="44"]) .container { padding-block: var(--primitives-space-44); }
	:host([padding-block="48"]) .container { padding-block: var(--primitives-space-48); }
	:host([padding-block="56"]) .container { padding-block: var(--primitives-space-56); }
	:host([padding-block="64"]) .container { padding-block: var(--primitives-space-64); }
	:host([padding-block="80"]) .container { padding-block: var(--primitives-space-80); }
	:host([padding-block="96"]) .container { padding-block: var(--primitives-space-96); }

	/* # Padding Block — sm viewport */

	:host([sm-padding-block="0"]) .container { @media (max-width: ${smMax$2}) { padding-block: 0; } }
	:host([sm-padding-block="2"]) .container { @media (max-width: ${smMax$2}) { padding-block: var(--primitives-space-2); } }
	:host([sm-padding-block="4"]) .container { @media (max-width: ${smMax$2}) { padding-block: var(--primitives-space-4); } }
	:host([sm-padding-block="6"]) .container { @media (max-width: ${smMax$2}) { padding-block: var(--primitives-space-6); } }
	:host([sm-padding-block="8"]) .container { @media (max-width: ${smMax$2}) { padding-block: var(--primitives-space-8); } }
	:host([sm-padding-block="10"]) .container { @media (max-width: ${smMax$2}) { padding-block: var(--primitives-space-10); } }
	:host([sm-padding-block="12"]) .container { @media (max-width: ${smMax$2}) { padding-block: var(--primitives-space-12); } }
	:host([sm-padding-block="16"]) .container { @media (max-width: ${smMax$2}) { padding-block: var(--primitives-space-16); } }
	:host([sm-padding-block="20"]) .container { @media (max-width: ${smMax$2}) { padding-block: var(--primitives-space-20); } }
	:host([sm-padding-block="24"]) .container { @media (max-width: ${smMax$2}) { padding-block: var(--primitives-space-24); } }
	:host([sm-padding-block="28"]) .container { @media (max-width: ${smMax$2}) { padding-block: var(--primitives-space-28); } }
	:host([sm-padding-block="32"]) .container { @media (max-width: ${smMax$2}) { padding-block: var(--primitives-space-32); } }
	:host([sm-padding-block="40"]) .container { @media (max-width: ${smMax$2}) { padding-block: var(--primitives-space-40); } }
	:host([sm-padding-block="44"]) .container { @media (max-width: ${smMax$2}) { padding-block: var(--primitives-space-44); } }
	:host([sm-padding-block="48"]) .container { @media (max-width: ${smMax$2}) { padding-block: var(--primitives-space-48); } }
	:host([sm-padding-block="56"]) .container { @media (max-width: ${smMax$2}) { padding-block: var(--primitives-space-56); } }
	:host([sm-padding-block="64"]) .container { @media (max-width: ${smMax$2}) { padding-block: var(--primitives-space-64); } }
	:host([sm-padding-block="80"]) .container { @media (max-width: ${smMax$2}) { padding-block: var(--primitives-space-80); } }
	:host([sm-padding-block="96"]) .container { @media (max-width: ${smMax$2}) { padding-block: var(--primitives-space-96); } }

	/* # Padding Block — md viewport */

	:host([md-padding-block="0"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-block: 0; } }
	:host([md-padding-block="2"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-block: var(--primitives-space-2); } }
	:host([md-padding-block="4"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-block: var(--primitives-space-4); } }
	:host([md-padding-block="6"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-block: var(--primitives-space-6); } }
	:host([md-padding-block="8"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-block: var(--primitives-space-8); } }
	:host([md-padding-block="10"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-block: var(--primitives-space-10); } }
	:host([md-padding-block="12"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-block: var(--primitives-space-12); } }
	:host([md-padding-block="16"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-block: var(--primitives-space-16); } }
	:host([md-padding-block="20"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-block: var(--primitives-space-20); } }
	:host([md-padding-block="24"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-block: var(--primitives-space-24); } }
	:host([md-padding-block="28"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-block: var(--primitives-space-28); } }
	:host([md-padding-block="32"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-block: var(--primitives-space-32); } }
	:host([md-padding-block="40"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-block: var(--primitives-space-40); } }
	:host([md-padding-block="44"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-block: var(--primitives-space-44); } }
	:host([md-padding-block="48"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-block: var(--primitives-space-48); } }
	:host([md-padding-block="56"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-block: var(--primitives-space-56); } }
	:host([md-padding-block="64"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-block: var(--primitives-space-64); } }
	:host([md-padding-block="80"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-block: var(--primitives-space-80); } }
	:host([md-padding-block="96"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-block: var(--primitives-space-96); } }

	/* # Padding Block — lg viewport */

	:host([lg-padding-block="0"]) .container { @media (min-width: ${lgMin$2}) { padding-block: 0; } }
	:host([lg-padding-block="2"]) .container { @media (min-width: ${lgMin$2}) { padding-block: var(--primitives-space-2); } }
	:host([lg-padding-block="4"]) .container { @media (min-width: ${lgMin$2}) { padding-block: var(--primitives-space-4); } }
	:host([lg-padding-block="6"]) .container { @media (min-width: ${lgMin$2}) { padding-block: var(--primitives-space-6); } }
	:host([lg-padding-block="8"]) .container { @media (min-width: ${lgMin$2}) { padding-block: var(--primitives-space-8); } }
	:host([lg-padding-block="10"]) .container { @media (min-width: ${lgMin$2}) { padding-block: var(--primitives-space-10); } }
	:host([lg-padding-block="12"]) .container { @media (min-width: ${lgMin$2}) { padding-block: var(--primitives-space-12); } }
	:host([lg-padding-block="16"]) .container { @media (min-width: ${lgMin$2}) { padding-block: var(--primitives-space-16); } }
	:host([lg-padding-block="20"]) .container { @media (min-width: ${lgMin$2}) { padding-block: var(--primitives-space-20); } }
	:host([lg-padding-block="24"]) .container { @media (min-width: ${lgMin$2}) { padding-block: var(--primitives-space-24); } }
	:host([lg-padding-block="28"]) .container { @media (min-width: ${lgMin$2}) { padding-block: var(--primitives-space-28); } }
	:host([lg-padding-block="32"]) .container { @media (min-width: ${lgMin$2}) { padding-block: var(--primitives-space-32); } }
	:host([lg-padding-block="40"]) .container { @media (min-width: ${lgMin$2}) { padding-block: var(--primitives-space-40); } }
	:host([lg-padding-block="44"]) .container { @media (min-width: ${lgMin$2}) { padding-block: var(--primitives-space-44); } }
	:host([lg-padding-block="48"]) .container { @media (min-width: ${lgMin$2}) { padding-block: var(--primitives-space-48); } }
	:host([lg-padding-block="56"]) .container { @media (min-width: ${lgMin$2}) { padding-block: var(--primitives-space-56); } }
	:host([lg-padding-block="64"]) .container { @media (min-width: ${lgMin$2}) { padding-block: var(--primitives-space-64); } }
	:host([lg-padding-block="80"]) .container { @media (min-width: ${lgMin$2}) { padding-block: var(--primitives-space-80); } }
	:host([lg-padding-block="96"]) .container { @media (min-width: ${lgMin$2}) { padding-block: var(--primitives-space-96); } }

	/* # Padding Block — sm container */

	:host([layout-area-sm-padding-block="0"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-block: 0; } }
	:host([layout-area-sm-padding-block="2"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-block: var(--primitives-space-2); } }
	:host([layout-area-sm-padding-block="4"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-block: var(--primitives-space-4); } }
	:host([layout-area-sm-padding-block="6"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-block: var(--primitives-space-6); } }
	:host([layout-area-sm-padding-block="8"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-block: var(--primitives-space-8); } }
	:host([layout-area-sm-padding-block="10"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-block: var(--primitives-space-10); } }
	:host([layout-area-sm-padding-block="12"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-block: var(--primitives-space-12); } }
	:host([layout-area-sm-padding-block="16"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-block: var(--primitives-space-16); } }
	:host([layout-area-sm-padding-block="20"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-block: var(--primitives-space-20); } }
	:host([layout-area-sm-padding-block="24"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-block: var(--primitives-space-24); } }
	:host([layout-area-sm-padding-block="28"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-block: var(--primitives-space-28); } }
	:host([layout-area-sm-padding-block="32"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-block: var(--primitives-space-32); } }
	:host([layout-area-sm-padding-block="40"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-block: var(--primitives-space-40); } }
	:host([layout-area-sm-padding-block="44"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-block: var(--primitives-space-44); } }
	:host([layout-area-sm-padding-block="48"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-block: var(--primitives-space-48); } }
	:host([layout-area-sm-padding-block="56"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-block: var(--primitives-space-56); } }
	:host([layout-area-sm-padding-block="64"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-block: var(--primitives-space-64); } }
	:host([layout-area-sm-padding-block="80"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-block: var(--primitives-space-80); } }
	:host([layout-area-sm-padding-block="96"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-block: var(--primitives-space-96); } }

	/* # Padding Block — md container */

	:host([layout-area-md-padding-block="0"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-block: 0; } }
	:host([layout-area-md-padding-block="2"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-block: var(--primitives-space-2); } }
	:host([layout-area-md-padding-block="4"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-block: var(--primitives-space-4); } }
	:host([layout-area-md-padding-block="6"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-block: var(--primitives-space-6); } }
	:host([layout-area-md-padding-block="8"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-block: var(--primitives-space-8); } }
	:host([layout-area-md-padding-block="10"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-block: var(--primitives-space-10); } }
	:host([layout-area-md-padding-block="12"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-block: var(--primitives-space-12); } }
	:host([layout-area-md-padding-block="16"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-block: var(--primitives-space-16); } }
	:host([layout-area-md-padding-block="20"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-block: var(--primitives-space-20); } }
	:host([layout-area-md-padding-block="24"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-block: var(--primitives-space-24); } }
	:host([layout-area-md-padding-block="28"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-block: var(--primitives-space-28); } }
	:host([layout-area-md-padding-block="32"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-block: var(--primitives-space-32); } }
	:host([layout-area-md-padding-block="40"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-block: var(--primitives-space-40); } }
	:host([layout-area-md-padding-block="44"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-block: var(--primitives-space-44); } }
	:host([layout-area-md-padding-block="48"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-block: var(--primitives-space-48); } }
	:host([layout-area-md-padding-block="56"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-block: var(--primitives-space-56); } }
	:host([layout-area-md-padding-block="64"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-block: var(--primitives-space-64); } }
	:host([layout-area-md-padding-block="80"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-block: var(--primitives-space-80); } }
	:host([layout-area-md-padding-block="96"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-block: var(--primitives-space-96); } }

	/* # Padding Block — lg container */

	:host([layout-area-lg-padding-block="0"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-block: 0; } }
	:host([layout-area-lg-padding-block="2"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-block: var(--primitives-space-2); } }
	:host([layout-area-lg-padding-block="4"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-block: var(--primitives-space-4); } }
	:host([layout-area-lg-padding-block="6"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-block: var(--primitives-space-6); } }
	:host([layout-area-lg-padding-block="8"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-block: var(--primitives-space-8); } }
	:host([layout-area-lg-padding-block="10"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-block: var(--primitives-space-10); } }
	:host([layout-area-lg-padding-block="12"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-block: var(--primitives-space-12); } }
	:host([layout-area-lg-padding-block="16"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-block: var(--primitives-space-16); } }
	:host([layout-area-lg-padding-block="20"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-block: var(--primitives-space-20); } }
	:host([layout-area-lg-padding-block="24"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-block: var(--primitives-space-24); } }
	:host([layout-area-lg-padding-block="28"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-block: var(--primitives-space-28); } }
	:host([layout-area-lg-padding-block="32"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-block: var(--primitives-space-32); } }
	:host([layout-area-lg-padding-block="40"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-block: var(--primitives-space-40); } }
	:host([layout-area-lg-padding-block="44"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-block: var(--primitives-space-44); } }
	:host([layout-area-lg-padding-block="48"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-block: var(--primitives-space-48); } }
	:host([layout-area-lg-padding-block="56"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-block: var(--primitives-space-56); } }
	:host([layout-area-lg-padding-block="64"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-block: var(--primitives-space-64); } }
	:host([layout-area-lg-padding-block="80"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-block: var(--primitives-space-80); } }
	:host([layout-area-lg-padding-block="96"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-block: var(--primitives-space-96); } }

	/* # Padding Top — base */

	:host([padding-top="0"]) .container { padding-top: 0; }
	:host([padding-top="2"]) .container { padding-top: var(--primitives-space-2); }
	:host([padding-top="4"]) .container { padding-top: var(--primitives-space-4); }
	:host([padding-top="6"]) .container { padding-top: var(--primitives-space-6); }
	:host([padding-top="8"]) .container { padding-top: var(--primitives-space-8); }
	:host([padding-top="10"]) .container { padding-top: var(--primitives-space-10); }
	:host([padding-top="12"]) .container { padding-top: var(--primitives-space-12); }
	:host([padding-top="16"]) .container { padding-top: var(--primitives-space-16); }
	:host([padding-top="20"]) .container { padding-top: var(--primitives-space-20); }
	:host([padding-top="24"]) .container { padding-top: var(--primitives-space-24); }
	:host([padding-top="28"]) .container { padding-top: var(--primitives-space-28); }
	:host([padding-top="32"]) .container { padding-top: var(--primitives-space-32); }
	:host([padding-top="40"]) .container { padding-top: var(--primitives-space-40); }
	:host([padding-top="44"]) .container { padding-top: var(--primitives-space-44); }
	:host([padding-top="48"]) .container { padding-top: var(--primitives-space-48); }
	:host([padding-top="56"]) .container { padding-top: var(--primitives-space-56); }
	:host([padding-top="64"]) .container { padding-top: var(--primitives-space-64); }
	:host([padding-top="80"]) .container { padding-top: var(--primitives-space-80); }
	:host([padding-top="96"]) .container { padding-top: var(--primitives-space-96); }

	/* # Padding Top — sm viewport */

	:host([sm-padding-top="0"]) .container { @media (max-width: ${smMax$2}) { padding-top: 0; } }
	:host([sm-padding-top="2"]) .container { @media (max-width: ${smMax$2}) { padding-top: var(--primitives-space-2); } }
	:host([sm-padding-top="4"]) .container { @media (max-width: ${smMax$2}) { padding-top: var(--primitives-space-4); } }
	:host([sm-padding-top="6"]) .container { @media (max-width: ${smMax$2}) { padding-top: var(--primitives-space-6); } }
	:host([sm-padding-top="8"]) .container { @media (max-width: ${smMax$2}) { padding-top: var(--primitives-space-8); } }
	:host([sm-padding-top="10"]) .container { @media (max-width: ${smMax$2}) { padding-top: var(--primitives-space-10); } }
	:host([sm-padding-top="12"]) .container { @media (max-width: ${smMax$2}) { padding-top: var(--primitives-space-12); } }
	:host([sm-padding-top="16"]) .container { @media (max-width: ${smMax$2}) { padding-top: var(--primitives-space-16); } }
	:host([sm-padding-top="20"]) .container { @media (max-width: ${smMax$2}) { padding-top: var(--primitives-space-20); } }
	:host([sm-padding-top="24"]) .container { @media (max-width: ${smMax$2}) { padding-top: var(--primitives-space-24); } }
	:host([sm-padding-top="28"]) .container { @media (max-width: ${smMax$2}) { padding-top: var(--primitives-space-28); } }
	:host([sm-padding-top="32"]) .container { @media (max-width: ${smMax$2}) { padding-top: var(--primitives-space-32); } }
	:host([sm-padding-top="40"]) .container { @media (max-width: ${smMax$2}) { padding-top: var(--primitives-space-40); } }
	:host([sm-padding-top="44"]) .container { @media (max-width: ${smMax$2}) { padding-top: var(--primitives-space-44); } }
	:host([sm-padding-top="48"]) .container { @media (max-width: ${smMax$2}) { padding-top: var(--primitives-space-48); } }
	:host([sm-padding-top="56"]) .container { @media (max-width: ${smMax$2}) { padding-top: var(--primitives-space-56); } }
	:host([sm-padding-top="64"]) .container { @media (max-width: ${smMax$2}) { padding-top: var(--primitives-space-64); } }
	:host([sm-padding-top="80"]) .container { @media (max-width: ${smMax$2}) { padding-top: var(--primitives-space-80); } }
	:host([sm-padding-top="96"]) .container { @media (max-width: ${smMax$2}) { padding-top: var(--primitives-space-96); } }

	/* # Padding Top — md viewport */

	:host([md-padding-top="0"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-top: 0; } }
	:host([md-padding-top="2"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-top: var(--primitives-space-2); } }
	:host([md-padding-top="4"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-top: var(--primitives-space-4); } }
	:host([md-padding-top="6"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-top: var(--primitives-space-6); } }
	:host([md-padding-top="8"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-top: var(--primitives-space-8); } }
	:host([md-padding-top="10"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-top: var(--primitives-space-10); } }
	:host([md-padding-top="12"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-top: var(--primitives-space-12); } }
	:host([md-padding-top="16"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-top: var(--primitives-space-16); } }
	:host([md-padding-top="20"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-top: var(--primitives-space-20); } }
	:host([md-padding-top="24"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-top: var(--primitives-space-24); } }
	:host([md-padding-top="28"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-top: var(--primitives-space-28); } }
	:host([md-padding-top="32"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-top: var(--primitives-space-32); } }
	:host([md-padding-top="40"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-top: var(--primitives-space-40); } }
	:host([md-padding-top="44"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-top: var(--primitives-space-44); } }
	:host([md-padding-top="48"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-top: var(--primitives-space-48); } }
	:host([md-padding-top="56"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-top: var(--primitives-space-56); } }
	:host([md-padding-top="64"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-top: var(--primitives-space-64); } }
	:host([md-padding-top="80"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-top: var(--primitives-space-80); } }
	:host([md-padding-top="96"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-top: var(--primitives-space-96); } }

	/* # Padding Top — lg viewport */

	:host([lg-padding-top="0"]) .container { @media (min-width: ${lgMin$2}) { padding-top: 0; } }
	:host([lg-padding-top="2"]) .container { @media (min-width: ${lgMin$2}) { padding-top: var(--primitives-space-2); } }
	:host([lg-padding-top="4"]) .container { @media (min-width: ${lgMin$2}) { padding-top: var(--primitives-space-4); } }
	:host([lg-padding-top="6"]) .container { @media (min-width: ${lgMin$2}) { padding-top: var(--primitives-space-6); } }
	:host([lg-padding-top="8"]) .container { @media (min-width: ${lgMin$2}) { padding-top: var(--primitives-space-8); } }
	:host([lg-padding-top="10"]) .container { @media (min-width: ${lgMin$2}) { padding-top: var(--primitives-space-10); } }
	:host([lg-padding-top="12"]) .container { @media (min-width: ${lgMin$2}) { padding-top: var(--primitives-space-12); } }
	:host([lg-padding-top="16"]) .container { @media (min-width: ${lgMin$2}) { padding-top: var(--primitives-space-16); } }
	:host([lg-padding-top="20"]) .container { @media (min-width: ${lgMin$2}) { padding-top: var(--primitives-space-20); } }
	:host([lg-padding-top="24"]) .container { @media (min-width: ${lgMin$2}) { padding-top: var(--primitives-space-24); } }
	:host([lg-padding-top="28"]) .container { @media (min-width: ${lgMin$2}) { padding-top: var(--primitives-space-28); } }
	:host([lg-padding-top="32"]) .container { @media (min-width: ${lgMin$2}) { padding-top: var(--primitives-space-32); } }
	:host([lg-padding-top="40"]) .container { @media (min-width: ${lgMin$2}) { padding-top: var(--primitives-space-40); } }
	:host([lg-padding-top="44"]) .container { @media (min-width: ${lgMin$2}) { padding-top: var(--primitives-space-44); } }
	:host([lg-padding-top="48"]) .container { @media (min-width: ${lgMin$2}) { padding-top: var(--primitives-space-48); } }
	:host([lg-padding-top="56"]) .container { @media (min-width: ${lgMin$2}) { padding-top: var(--primitives-space-56); } }
	:host([lg-padding-top="64"]) .container { @media (min-width: ${lgMin$2}) { padding-top: var(--primitives-space-64); } }
	:host([lg-padding-top="80"]) .container { @media (min-width: ${lgMin$2}) { padding-top: var(--primitives-space-80); } }
	:host([lg-padding-top="96"]) .container { @media (min-width: ${lgMin$2}) { padding-top: var(--primitives-space-96); } }

	/* # Padding Top — sm container */

	:host([layout-area-sm-padding-top="0"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-top: 0; } }
	:host([layout-area-sm-padding-top="2"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-top: var(--primitives-space-2); } }
	:host([layout-area-sm-padding-top="4"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-top: var(--primitives-space-4); } }
	:host([layout-area-sm-padding-top="6"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-top: var(--primitives-space-6); } }
	:host([layout-area-sm-padding-top="8"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-top: var(--primitives-space-8); } }
	:host([layout-area-sm-padding-top="10"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-top: var(--primitives-space-10); } }
	:host([layout-area-sm-padding-top="12"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-top: var(--primitives-space-12); } }
	:host([layout-area-sm-padding-top="16"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-top: var(--primitives-space-16); } }
	:host([layout-area-sm-padding-top="20"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-top: var(--primitives-space-20); } }
	:host([layout-area-sm-padding-top="24"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-top: var(--primitives-space-24); } }
	:host([layout-area-sm-padding-top="28"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-top: var(--primitives-space-28); } }
	:host([layout-area-sm-padding-top="32"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-top: var(--primitives-space-32); } }
	:host([layout-area-sm-padding-top="40"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-top: var(--primitives-space-40); } }
	:host([layout-area-sm-padding-top="44"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-top: var(--primitives-space-44); } }
	:host([layout-area-sm-padding-top="48"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-top: var(--primitives-space-48); } }
	:host([layout-area-sm-padding-top="56"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-top: var(--primitives-space-56); } }
	:host([layout-area-sm-padding-top="64"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-top: var(--primitives-space-64); } }
	:host([layout-area-sm-padding-top="80"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-top: var(--primitives-space-80); } }
	:host([layout-area-sm-padding-top="96"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-top: var(--primitives-space-96); } }

	/* # Padding Top — md container */

	:host([layout-area-md-padding-top="0"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-top: 0; } }
	:host([layout-area-md-padding-top="2"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-top: var(--primitives-space-2); } }
	:host([layout-area-md-padding-top="4"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-top: var(--primitives-space-4); } }
	:host([layout-area-md-padding-top="6"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-top: var(--primitives-space-6); } }
	:host([layout-area-md-padding-top="8"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-top: var(--primitives-space-8); } }
	:host([layout-area-md-padding-top="10"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-top: var(--primitives-space-10); } }
	:host([layout-area-md-padding-top="12"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-top: var(--primitives-space-12); } }
	:host([layout-area-md-padding-top="16"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-top: var(--primitives-space-16); } }
	:host([layout-area-md-padding-top="20"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-top: var(--primitives-space-20); } }
	:host([layout-area-md-padding-top="24"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-top: var(--primitives-space-24); } }
	:host([layout-area-md-padding-top="28"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-top: var(--primitives-space-28); } }
	:host([layout-area-md-padding-top="32"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-top: var(--primitives-space-32); } }
	:host([layout-area-md-padding-top="40"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-top: var(--primitives-space-40); } }
	:host([layout-area-md-padding-top="44"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-top: var(--primitives-space-44); } }
	:host([layout-area-md-padding-top="48"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-top: var(--primitives-space-48); } }
	:host([layout-area-md-padding-top="56"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-top: var(--primitives-space-56); } }
	:host([layout-area-md-padding-top="64"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-top: var(--primitives-space-64); } }
	:host([layout-area-md-padding-top="80"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-top: var(--primitives-space-80); } }
	:host([layout-area-md-padding-top="96"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-top: var(--primitives-space-96); } }

	/* # Padding Top — lg container */

	:host([layout-area-lg-padding-top="0"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-top: 0; } }
	:host([layout-area-lg-padding-top="2"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-top: var(--primitives-space-2); } }
	:host([layout-area-lg-padding-top="4"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-top: var(--primitives-space-4); } }
	:host([layout-area-lg-padding-top="6"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-top: var(--primitives-space-6); } }
	:host([layout-area-lg-padding-top="8"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-top: var(--primitives-space-8); } }
	:host([layout-area-lg-padding-top="10"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-top: var(--primitives-space-10); } }
	:host([layout-area-lg-padding-top="12"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-top: var(--primitives-space-12); } }
	:host([layout-area-lg-padding-top="16"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-top: var(--primitives-space-16); } }
	:host([layout-area-lg-padding-top="20"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-top: var(--primitives-space-20); } }
	:host([layout-area-lg-padding-top="24"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-top: var(--primitives-space-24); } }
	:host([layout-area-lg-padding-top="28"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-top: var(--primitives-space-28); } }
	:host([layout-area-lg-padding-top="32"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-top: var(--primitives-space-32); } }
	:host([layout-area-lg-padding-top="40"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-top: var(--primitives-space-40); } }
	:host([layout-area-lg-padding-top="44"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-top: var(--primitives-space-44); } }
	:host([layout-area-lg-padding-top="48"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-top: var(--primitives-space-48); } }
	:host([layout-area-lg-padding-top="56"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-top: var(--primitives-space-56); } }
	:host([layout-area-lg-padding-top="64"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-top: var(--primitives-space-64); } }
	:host([layout-area-lg-padding-top="80"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-top: var(--primitives-space-80); } }
	:host([layout-area-lg-padding-top="96"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-top: var(--primitives-space-96); } }

	/* # Padding Right — base */

	:host([padding-right="0"]) .container { padding-right: 0; }
	:host([padding-right="2"]) .container { padding-right: var(--primitives-space-2); }
	:host([padding-right="4"]) .container { padding-right: var(--primitives-space-4); }
	:host([padding-right="6"]) .container { padding-right: var(--primitives-space-6); }
	:host([padding-right="8"]) .container { padding-right: var(--primitives-space-8); }
	:host([padding-right="10"]) .container { padding-right: var(--primitives-space-10); }
	:host([padding-right="12"]) .container { padding-right: var(--primitives-space-12); }
	:host([padding-right="16"]) .container { padding-right: var(--primitives-space-16); }
	:host([padding-right="20"]) .container { padding-right: var(--primitives-space-20); }
	:host([padding-right="24"]) .container { padding-right: var(--primitives-space-24); }
	:host([padding-right="28"]) .container { padding-right: var(--primitives-space-28); }
	:host([padding-right="32"]) .container { padding-right: var(--primitives-space-32); }
	:host([padding-right="40"]) .container { padding-right: var(--primitives-space-40); }
	:host([padding-right="44"]) .container { padding-right: var(--primitives-space-44); }
	:host([padding-right="48"]) .container { padding-right: var(--primitives-space-48); }
	:host([padding-right="56"]) .container { padding-right: var(--primitives-space-56); }
	:host([padding-right="64"]) .container { padding-right: var(--primitives-space-64); }
	:host([padding-right="80"]) .container { padding-right: var(--primitives-space-80); }
	:host([padding-right="96"]) .container { padding-right: var(--primitives-space-96); }

	/* # Padding Right — sm viewport */

	:host([sm-padding-right="0"]) .container { @media (max-width: ${smMax$2}) { padding-right: 0; } }
	:host([sm-padding-right="2"]) .container { @media (max-width: ${smMax$2}) { padding-right: var(--primitives-space-2); } }
	:host([sm-padding-right="4"]) .container { @media (max-width: ${smMax$2}) { padding-right: var(--primitives-space-4); } }
	:host([sm-padding-right="6"]) .container { @media (max-width: ${smMax$2}) { padding-right: var(--primitives-space-6); } }
	:host([sm-padding-right="8"]) .container { @media (max-width: ${smMax$2}) { padding-right: var(--primitives-space-8); } }
	:host([sm-padding-right="10"]) .container { @media (max-width: ${smMax$2}) { padding-right: var(--primitives-space-10); } }
	:host([sm-padding-right="12"]) .container { @media (max-width: ${smMax$2}) { padding-right: var(--primitives-space-12); } }
	:host([sm-padding-right="16"]) .container { @media (max-width: ${smMax$2}) { padding-right: var(--primitives-space-16); } }
	:host([sm-padding-right="20"]) .container { @media (max-width: ${smMax$2}) { padding-right: var(--primitives-space-20); } }
	:host([sm-padding-right="24"]) .container { @media (max-width: ${smMax$2}) { padding-right: var(--primitives-space-24); } }
	:host([sm-padding-right="28"]) .container { @media (max-width: ${smMax$2}) { padding-right: var(--primitives-space-28); } }
	:host([sm-padding-right="32"]) .container { @media (max-width: ${smMax$2}) { padding-right: var(--primitives-space-32); } }
	:host([sm-padding-right="40"]) .container { @media (max-width: ${smMax$2}) { padding-right: var(--primitives-space-40); } }
	:host([sm-padding-right="44"]) .container { @media (max-width: ${smMax$2}) { padding-right: var(--primitives-space-44); } }
	:host([sm-padding-right="48"]) .container { @media (max-width: ${smMax$2}) { padding-right: var(--primitives-space-48); } }
	:host([sm-padding-right="56"]) .container { @media (max-width: ${smMax$2}) { padding-right: var(--primitives-space-56); } }
	:host([sm-padding-right="64"]) .container { @media (max-width: ${smMax$2}) { padding-right: var(--primitives-space-64); } }
	:host([sm-padding-right="80"]) .container { @media (max-width: ${smMax$2}) { padding-right: var(--primitives-space-80); } }
	:host([sm-padding-right="96"]) .container { @media (max-width: ${smMax$2}) { padding-right: var(--primitives-space-96); } }

	/* # Padding Right — md viewport */

	:host([md-padding-right="0"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-right: 0; } }
	:host([md-padding-right="2"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-right: var(--primitives-space-2); } }
	:host([md-padding-right="4"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-right: var(--primitives-space-4); } }
	:host([md-padding-right="6"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-right: var(--primitives-space-6); } }
	:host([md-padding-right="8"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-right: var(--primitives-space-8); } }
	:host([md-padding-right="10"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-right: var(--primitives-space-10); } }
	:host([md-padding-right="12"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-right: var(--primitives-space-12); } }
	:host([md-padding-right="16"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-right: var(--primitives-space-16); } }
	:host([md-padding-right="20"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-right: var(--primitives-space-20); } }
	:host([md-padding-right="24"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-right: var(--primitives-space-24); } }
	:host([md-padding-right="28"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-right: var(--primitives-space-28); } }
	:host([md-padding-right="32"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-right: var(--primitives-space-32); } }
	:host([md-padding-right="40"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-right: var(--primitives-space-40); } }
	:host([md-padding-right="44"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-right: var(--primitives-space-44); } }
	:host([md-padding-right="48"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-right: var(--primitives-space-48); } }
	:host([md-padding-right="56"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-right: var(--primitives-space-56); } }
	:host([md-padding-right="64"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-right: var(--primitives-space-64); } }
	:host([md-padding-right="80"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-right: var(--primitives-space-80); } }
	:host([md-padding-right="96"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-right: var(--primitives-space-96); } }

	/* # Padding Right — lg viewport */

	:host([lg-padding-right="0"]) .container { @media (min-width: ${lgMin$2}) { padding-right: 0; } }
	:host([lg-padding-right="2"]) .container { @media (min-width: ${lgMin$2}) { padding-right: var(--primitives-space-2); } }
	:host([lg-padding-right="4"]) .container { @media (min-width: ${lgMin$2}) { padding-right: var(--primitives-space-4); } }
	:host([lg-padding-right="6"]) .container { @media (min-width: ${lgMin$2}) { padding-right: var(--primitives-space-6); } }
	:host([lg-padding-right="8"]) .container { @media (min-width: ${lgMin$2}) { padding-right: var(--primitives-space-8); } }
	:host([lg-padding-right="10"]) .container { @media (min-width: ${lgMin$2}) { padding-right: var(--primitives-space-10); } }
	:host([lg-padding-right="12"]) .container { @media (min-width: ${lgMin$2}) { padding-right: var(--primitives-space-12); } }
	:host([lg-padding-right="16"]) .container { @media (min-width: ${lgMin$2}) { padding-right: var(--primitives-space-16); } }
	:host([lg-padding-right="20"]) .container { @media (min-width: ${lgMin$2}) { padding-right: var(--primitives-space-20); } }
	:host([lg-padding-right="24"]) .container { @media (min-width: ${lgMin$2}) { padding-right: var(--primitives-space-24); } }
	:host([lg-padding-right="28"]) .container { @media (min-width: ${lgMin$2}) { padding-right: var(--primitives-space-28); } }
	:host([lg-padding-right="32"]) .container { @media (min-width: ${lgMin$2}) { padding-right: var(--primitives-space-32); } }
	:host([lg-padding-right="40"]) .container { @media (min-width: ${lgMin$2}) { padding-right: var(--primitives-space-40); } }
	:host([lg-padding-right="44"]) .container { @media (min-width: ${lgMin$2}) { padding-right: var(--primitives-space-44); } }
	:host([lg-padding-right="48"]) .container { @media (min-width: ${lgMin$2}) { padding-right: var(--primitives-space-48); } }
	:host([lg-padding-right="56"]) .container { @media (min-width: ${lgMin$2}) { padding-right: var(--primitives-space-56); } }
	:host([lg-padding-right="64"]) .container { @media (min-width: ${lgMin$2}) { padding-right: var(--primitives-space-64); } }
	:host([lg-padding-right="80"]) .container { @media (min-width: ${lgMin$2}) { padding-right: var(--primitives-space-80); } }
	:host([lg-padding-right="96"]) .container { @media (min-width: ${lgMin$2}) { padding-right: var(--primitives-space-96); } }

	/* # Padding Right — sm container */

	:host([layout-area-sm-padding-right="0"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-right: 0; } }
	:host([layout-area-sm-padding-right="2"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-right: var(--primitives-space-2); } }
	:host([layout-area-sm-padding-right="4"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-right: var(--primitives-space-4); } }
	:host([layout-area-sm-padding-right="6"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-right: var(--primitives-space-6); } }
	:host([layout-area-sm-padding-right="8"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-right: var(--primitives-space-8); } }
	:host([layout-area-sm-padding-right="10"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-right: var(--primitives-space-10); } }
	:host([layout-area-sm-padding-right="12"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-right: var(--primitives-space-12); } }
	:host([layout-area-sm-padding-right="16"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-right: var(--primitives-space-16); } }
	:host([layout-area-sm-padding-right="20"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-right: var(--primitives-space-20); } }
	:host([layout-area-sm-padding-right="24"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-right: var(--primitives-space-24); } }
	:host([layout-area-sm-padding-right="28"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-right: var(--primitives-space-28); } }
	:host([layout-area-sm-padding-right="32"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-right: var(--primitives-space-32); } }
	:host([layout-area-sm-padding-right="40"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-right: var(--primitives-space-40); } }
	:host([layout-area-sm-padding-right="44"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-right: var(--primitives-space-44); } }
	:host([layout-area-sm-padding-right="48"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-right: var(--primitives-space-48); } }
	:host([layout-area-sm-padding-right="56"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-right: var(--primitives-space-56); } }
	:host([layout-area-sm-padding-right="64"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-right: var(--primitives-space-64); } }
	:host([layout-area-sm-padding-right="80"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-right: var(--primitives-space-80); } }
	:host([layout-area-sm-padding-right="96"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-right: var(--primitives-space-96); } }

	/* # Padding Right — md container */

	:host([layout-area-md-padding-right="0"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-right: 0; } }
	:host([layout-area-md-padding-right="2"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-right: var(--primitives-space-2); } }
	:host([layout-area-md-padding-right="4"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-right: var(--primitives-space-4); } }
	:host([layout-area-md-padding-right="6"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-right: var(--primitives-space-6); } }
	:host([layout-area-md-padding-right="8"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-right: var(--primitives-space-8); } }
	:host([layout-area-md-padding-right="10"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-right: var(--primitives-space-10); } }
	:host([layout-area-md-padding-right="12"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-right: var(--primitives-space-12); } }
	:host([layout-area-md-padding-right="16"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-right: var(--primitives-space-16); } }
	:host([layout-area-md-padding-right="20"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-right: var(--primitives-space-20); } }
	:host([layout-area-md-padding-right="24"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-right: var(--primitives-space-24); } }
	:host([layout-area-md-padding-right="28"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-right: var(--primitives-space-28); } }
	:host([layout-area-md-padding-right="32"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-right: var(--primitives-space-32); } }
	:host([layout-area-md-padding-right="40"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-right: var(--primitives-space-40); } }
	:host([layout-area-md-padding-right="44"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-right: var(--primitives-space-44); } }
	:host([layout-area-md-padding-right="48"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-right: var(--primitives-space-48); } }
	:host([layout-area-md-padding-right="56"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-right: var(--primitives-space-56); } }
	:host([layout-area-md-padding-right="64"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-right: var(--primitives-space-64); } }
	:host([layout-area-md-padding-right="80"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-right: var(--primitives-space-80); } }
	:host([layout-area-md-padding-right="96"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-right: var(--primitives-space-96); } }

	/* # Padding Right — lg container */

	:host([layout-area-lg-padding-right="0"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-right: 0; } }
	:host([layout-area-lg-padding-right="2"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-right: var(--primitives-space-2); } }
	:host([layout-area-lg-padding-right="4"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-right: var(--primitives-space-4); } }
	:host([layout-area-lg-padding-right="6"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-right: var(--primitives-space-6); } }
	:host([layout-area-lg-padding-right="8"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-right: var(--primitives-space-8); } }
	:host([layout-area-lg-padding-right="10"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-right: var(--primitives-space-10); } }
	:host([layout-area-lg-padding-right="12"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-right: var(--primitives-space-12); } }
	:host([layout-area-lg-padding-right="16"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-right: var(--primitives-space-16); } }
	:host([layout-area-lg-padding-right="20"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-right: var(--primitives-space-20); } }
	:host([layout-area-lg-padding-right="24"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-right: var(--primitives-space-24); } }
	:host([layout-area-lg-padding-right="28"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-right: var(--primitives-space-28); } }
	:host([layout-area-lg-padding-right="32"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-right: var(--primitives-space-32); } }
	:host([layout-area-lg-padding-right="40"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-right: var(--primitives-space-40); } }
	:host([layout-area-lg-padding-right="44"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-right: var(--primitives-space-44); } }
	:host([layout-area-lg-padding-right="48"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-right: var(--primitives-space-48); } }
	:host([layout-area-lg-padding-right="56"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-right: var(--primitives-space-56); } }
	:host([layout-area-lg-padding-right="64"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-right: var(--primitives-space-64); } }
	:host([layout-area-lg-padding-right="80"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-right: var(--primitives-space-80); } }
	:host([layout-area-lg-padding-right="96"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-right: var(--primitives-space-96); } }

	/* # Padding Bottom — base */

	:host([padding-bottom="0"]) .container { padding-bottom: 0; }
	:host([padding-bottom="2"]) .container { padding-bottom: var(--primitives-space-2); }
	:host([padding-bottom="4"]) .container { padding-bottom: var(--primitives-space-4); }
	:host([padding-bottom="6"]) .container { padding-bottom: var(--primitives-space-6); }
	:host([padding-bottom="8"]) .container { padding-bottom: var(--primitives-space-8); }
	:host([padding-bottom="10"]) .container { padding-bottom: var(--primitives-space-10); }
	:host([padding-bottom="12"]) .container { padding-bottom: var(--primitives-space-12); }
	:host([padding-bottom="16"]) .container { padding-bottom: var(--primitives-space-16); }
	:host([padding-bottom="20"]) .container { padding-bottom: var(--primitives-space-20); }
	:host([padding-bottom="24"]) .container { padding-bottom: var(--primitives-space-24); }
	:host([padding-bottom="28"]) .container { padding-bottom: var(--primitives-space-28); }
	:host([padding-bottom="32"]) .container { padding-bottom: var(--primitives-space-32); }
	:host([padding-bottom="40"]) .container { padding-bottom: var(--primitives-space-40); }
	:host([padding-bottom="44"]) .container { padding-bottom: var(--primitives-space-44); }
	:host([padding-bottom="48"]) .container { padding-bottom: var(--primitives-space-48); }
	:host([padding-bottom="56"]) .container { padding-bottom: var(--primitives-space-56); }
	:host([padding-bottom="64"]) .container { padding-bottom: var(--primitives-space-64); }
	:host([padding-bottom="80"]) .container { padding-bottom: var(--primitives-space-80); }
	:host([padding-bottom="96"]) .container { padding-bottom: var(--primitives-space-96); }

	/* # Padding Bottom — sm viewport */

	:host([sm-padding-bottom="0"]) .container { @media (max-width: ${smMax$2}) { padding-bottom: 0; } }
	:host([sm-padding-bottom="2"]) .container { @media (max-width: ${smMax$2}) { padding-bottom: var(--primitives-space-2); } }
	:host([sm-padding-bottom="4"]) .container { @media (max-width: ${smMax$2}) { padding-bottom: var(--primitives-space-4); } }
	:host([sm-padding-bottom="6"]) .container { @media (max-width: ${smMax$2}) { padding-bottom: var(--primitives-space-6); } }
	:host([sm-padding-bottom="8"]) .container { @media (max-width: ${smMax$2}) { padding-bottom: var(--primitives-space-8); } }
	:host([sm-padding-bottom="10"]) .container { @media (max-width: ${smMax$2}) { padding-bottom: var(--primitives-space-10); } }
	:host([sm-padding-bottom="12"]) .container { @media (max-width: ${smMax$2}) { padding-bottom: var(--primitives-space-12); } }
	:host([sm-padding-bottom="16"]) .container { @media (max-width: ${smMax$2}) { padding-bottom: var(--primitives-space-16); } }
	:host([sm-padding-bottom="20"]) .container { @media (max-width: ${smMax$2}) { padding-bottom: var(--primitives-space-20); } }
	:host([sm-padding-bottom="24"]) .container { @media (max-width: ${smMax$2}) { padding-bottom: var(--primitives-space-24); } }
	:host([sm-padding-bottom="28"]) .container { @media (max-width: ${smMax$2}) { padding-bottom: var(--primitives-space-28); } }
	:host([sm-padding-bottom="32"]) .container { @media (max-width: ${smMax$2}) { padding-bottom: var(--primitives-space-32); } }
	:host([sm-padding-bottom="40"]) .container { @media (max-width: ${smMax$2}) { padding-bottom: var(--primitives-space-40); } }
	:host([sm-padding-bottom="44"]) .container { @media (max-width: ${smMax$2}) { padding-bottom: var(--primitives-space-44); } }
	:host([sm-padding-bottom="48"]) .container { @media (max-width: ${smMax$2}) { padding-bottom: var(--primitives-space-48); } }
	:host([sm-padding-bottom="56"]) .container { @media (max-width: ${smMax$2}) { padding-bottom: var(--primitives-space-56); } }
	:host([sm-padding-bottom="64"]) .container { @media (max-width: ${smMax$2}) { padding-bottom: var(--primitives-space-64); } }
	:host([sm-padding-bottom="80"]) .container { @media (max-width: ${smMax$2}) { padding-bottom: var(--primitives-space-80); } }
	:host([sm-padding-bottom="96"]) .container { @media (max-width: ${smMax$2}) { padding-bottom: var(--primitives-space-96); } }

	/* # Padding Bottom — md viewport */

	:host([md-padding-bottom="0"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-bottom: 0; } }
	:host([md-padding-bottom="2"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-bottom: var(--primitives-space-2); } }
	:host([md-padding-bottom="4"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-bottom: var(--primitives-space-4); } }
	:host([md-padding-bottom="6"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-bottom: var(--primitives-space-6); } }
	:host([md-padding-bottom="8"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-bottom: var(--primitives-space-8); } }
	:host([md-padding-bottom="10"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-bottom: var(--primitives-space-10); } }
	:host([md-padding-bottom="12"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-bottom: var(--primitives-space-12); } }
	:host([md-padding-bottom="16"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-bottom: var(--primitives-space-16); } }
	:host([md-padding-bottom="20"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-bottom: var(--primitives-space-20); } }
	:host([md-padding-bottom="24"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-bottom: var(--primitives-space-24); } }
	:host([md-padding-bottom="28"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-bottom: var(--primitives-space-28); } }
	:host([md-padding-bottom="32"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-bottom: var(--primitives-space-32); } }
	:host([md-padding-bottom="40"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-bottom: var(--primitives-space-40); } }
	:host([md-padding-bottom="44"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-bottom: var(--primitives-space-44); } }
	:host([md-padding-bottom="48"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-bottom: var(--primitives-space-48); } }
	:host([md-padding-bottom="56"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-bottom: var(--primitives-space-56); } }
	:host([md-padding-bottom="64"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-bottom: var(--primitives-space-64); } }
	:host([md-padding-bottom="80"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-bottom: var(--primitives-space-80); } }
	:host([md-padding-bottom="96"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-bottom: var(--primitives-space-96); } }

	/* # Padding Bottom — lg viewport */

	:host([lg-padding-bottom="0"]) .container { @media (min-width: ${lgMin$2}) { padding-bottom: 0; } }
	:host([lg-padding-bottom="2"]) .container { @media (min-width: ${lgMin$2}) { padding-bottom: var(--primitives-space-2); } }
	:host([lg-padding-bottom="4"]) .container { @media (min-width: ${lgMin$2}) { padding-bottom: var(--primitives-space-4); } }
	:host([lg-padding-bottom="6"]) .container { @media (min-width: ${lgMin$2}) { padding-bottom: var(--primitives-space-6); } }
	:host([lg-padding-bottom="8"]) .container { @media (min-width: ${lgMin$2}) { padding-bottom: var(--primitives-space-8); } }
	:host([lg-padding-bottom="10"]) .container { @media (min-width: ${lgMin$2}) { padding-bottom: var(--primitives-space-10); } }
	:host([lg-padding-bottom="12"]) .container { @media (min-width: ${lgMin$2}) { padding-bottom: var(--primitives-space-12); } }
	:host([lg-padding-bottom="16"]) .container { @media (min-width: ${lgMin$2}) { padding-bottom: var(--primitives-space-16); } }
	:host([lg-padding-bottom="20"]) .container { @media (min-width: ${lgMin$2}) { padding-bottom: var(--primitives-space-20); } }
	:host([lg-padding-bottom="24"]) .container { @media (min-width: ${lgMin$2}) { padding-bottom: var(--primitives-space-24); } }
	:host([lg-padding-bottom="28"]) .container { @media (min-width: ${lgMin$2}) { padding-bottom: var(--primitives-space-28); } }
	:host([lg-padding-bottom="32"]) .container { @media (min-width: ${lgMin$2}) { padding-bottom: var(--primitives-space-32); } }
	:host([lg-padding-bottom="40"]) .container { @media (min-width: ${lgMin$2}) { padding-bottom: var(--primitives-space-40); } }
	:host([lg-padding-bottom="44"]) .container { @media (min-width: ${lgMin$2}) { padding-bottom: var(--primitives-space-44); } }
	:host([lg-padding-bottom="48"]) .container { @media (min-width: ${lgMin$2}) { padding-bottom: var(--primitives-space-48); } }
	:host([lg-padding-bottom="56"]) .container { @media (min-width: ${lgMin$2}) { padding-bottom: var(--primitives-space-56); } }
	:host([lg-padding-bottom="64"]) .container { @media (min-width: ${lgMin$2}) { padding-bottom: var(--primitives-space-64); } }
	:host([lg-padding-bottom="80"]) .container { @media (min-width: ${lgMin$2}) { padding-bottom: var(--primitives-space-80); } }
	:host([lg-padding-bottom="96"]) .container { @media (min-width: ${lgMin$2}) { padding-bottom: var(--primitives-space-96); } }

	/* # Padding Bottom — sm container */

	:host([layout-area-sm-padding-bottom="0"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-bottom: 0; } }
	:host([layout-area-sm-padding-bottom="2"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-bottom: var(--primitives-space-2); } }
	:host([layout-area-sm-padding-bottom="4"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-bottom: var(--primitives-space-4); } }
	:host([layout-area-sm-padding-bottom="6"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-bottom: var(--primitives-space-6); } }
	:host([layout-area-sm-padding-bottom="8"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-bottom: var(--primitives-space-8); } }
	:host([layout-area-sm-padding-bottom="10"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-bottom: var(--primitives-space-10); } }
	:host([layout-area-sm-padding-bottom="12"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-bottom: var(--primitives-space-12); } }
	:host([layout-area-sm-padding-bottom="16"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-bottom: var(--primitives-space-16); } }
	:host([layout-area-sm-padding-bottom="20"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-bottom: var(--primitives-space-20); } }
	:host([layout-area-sm-padding-bottom="24"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-bottom: var(--primitives-space-24); } }
	:host([layout-area-sm-padding-bottom="28"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-bottom: var(--primitives-space-28); } }
	:host([layout-area-sm-padding-bottom="32"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-bottom: var(--primitives-space-32); } }
	:host([layout-area-sm-padding-bottom="40"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-bottom: var(--primitives-space-40); } }
	:host([layout-area-sm-padding-bottom="44"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-bottom: var(--primitives-space-44); } }
	:host([layout-area-sm-padding-bottom="48"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-bottom: var(--primitives-space-48); } }
	:host([layout-area-sm-padding-bottom="56"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-bottom: var(--primitives-space-56); } }
	:host([layout-area-sm-padding-bottom="64"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-bottom: var(--primitives-space-64); } }
	:host([layout-area-sm-padding-bottom="80"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-bottom: var(--primitives-space-80); } }
	:host([layout-area-sm-padding-bottom="96"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-bottom: var(--primitives-space-96); } }

	/* # Padding Bottom — md container */

	:host([layout-area-md-padding-bottom="0"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-bottom: 0; } }
	:host([layout-area-md-padding-bottom="2"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-bottom: var(--primitives-space-2); } }
	:host([layout-area-md-padding-bottom="4"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-bottom: var(--primitives-space-4); } }
	:host([layout-area-md-padding-bottom="6"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-bottom: var(--primitives-space-6); } }
	:host([layout-area-md-padding-bottom="8"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-bottom: var(--primitives-space-8); } }
	:host([layout-area-md-padding-bottom="10"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-bottom: var(--primitives-space-10); } }
	:host([layout-area-md-padding-bottom="12"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-bottom: var(--primitives-space-12); } }
	:host([layout-area-md-padding-bottom="16"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-bottom: var(--primitives-space-16); } }
	:host([layout-area-md-padding-bottom="20"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-bottom: var(--primitives-space-20); } }
	:host([layout-area-md-padding-bottom="24"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-bottom: var(--primitives-space-24); } }
	:host([layout-area-md-padding-bottom="28"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-bottom: var(--primitives-space-28); } }
	:host([layout-area-md-padding-bottom="32"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-bottom: var(--primitives-space-32); } }
	:host([layout-area-md-padding-bottom="40"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-bottom: var(--primitives-space-40); } }
	:host([layout-area-md-padding-bottom="44"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-bottom: var(--primitives-space-44); } }
	:host([layout-area-md-padding-bottom="48"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-bottom: var(--primitives-space-48); } }
	:host([layout-area-md-padding-bottom="56"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-bottom: var(--primitives-space-56); } }
	:host([layout-area-md-padding-bottom="64"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-bottom: var(--primitives-space-64); } }
	:host([layout-area-md-padding-bottom="80"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-bottom: var(--primitives-space-80); } }
	:host([layout-area-md-padding-bottom="96"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-bottom: var(--primitives-space-96); } }

	/* # Padding Bottom — lg container */

	:host([layout-area-lg-padding-bottom="0"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-bottom: 0; } }
	:host([layout-area-lg-padding-bottom="2"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-bottom: var(--primitives-space-2); } }
	:host([layout-area-lg-padding-bottom="4"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-bottom: var(--primitives-space-4); } }
	:host([layout-area-lg-padding-bottom="6"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-bottom: var(--primitives-space-6); } }
	:host([layout-area-lg-padding-bottom="8"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-bottom: var(--primitives-space-8); } }
	:host([layout-area-lg-padding-bottom="10"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-bottom: var(--primitives-space-10); } }
	:host([layout-area-lg-padding-bottom="12"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-bottom: var(--primitives-space-12); } }
	:host([layout-area-lg-padding-bottom="16"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-bottom: var(--primitives-space-16); } }
	:host([layout-area-lg-padding-bottom="20"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-bottom: var(--primitives-space-20); } }
	:host([layout-area-lg-padding-bottom="24"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-bottom: var(--primitives-space-24); } }
	:host([layout-area-lg-padding-bottom="28"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-bottom: var(--primitives-space-28); } }
	:host([layout-area-lg-padding-bottom="32"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-bottom: var(--primitives-space-32); } }
	:host([layout-area-lg-padding-bottom="40"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-bottom: var(--primitives-space-40); } }
	:host([layout-area-lg-padding-bottom="44"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-bottom: var(--primitives-space-44); } }
	:host([layout-area-lg-padding-bottom="48"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-bottom: var(--primitives-space-48); } }
	:host([layout-area-lg-padding-bottom="56"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-bottom: var(--primitives-space-56); } }
	:host([layout-area-lg-padding-bottom="64"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-bottom: var(--primitives-space-64); } }
	:host([layout-area-lg-padding-bottom="80"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-bottom: var(--primitives-space-80); } }
	:host([layout-area-lg-padding-bottom="96"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-bottom: var(--primitives-space-96); } }

	/* # Padding Left — base */

	:host([padding-left="0"]) .container { padding-left: 0; }
	:host([padding-left="2"]) .container { padding-left: var(--primitives-space-2); }
	:host([padding-left="4"]) .container { padding-left: var(--primitives-space-4); }
	:host([padding-left="6"]) .container { padding-left: var(--primitives-space-6); }
	:host([padding-left="8"]) .container { padding-left: var(--primitives-space-8); }
	:host([padding-left="10"]) .container { padding-left: var(--primitives-space-10); }
	:host([padding-left="12"]) .container { padding-left: var(--primitives-space-12); }
	:host([padding-left="16"]) .container { padding-left: var(--primitives-space-16); }
	:host([padding-left="20"]) .container { padding-left: var(--primitives-space-20); }
	:host([padding-left="24"]) .container { padding-left: var(--primitives-space-24); }
	:host([padding-left="28"]) .container { padding-left: var(--primitives-space-28); }
	:host([padding-left="32"]) .container { padding-left: var(--primitives-space-32); }
	:host([padding-left="40"]) .container { padding-left: var(--primitives-space-40); }
	:host([padding-left="44"]) .container { padding-left: var(--primitives-space-44); }
	:host([padding-left="48"]) .container { padding-left: var(--primitives-space-48); }
	:host([padding-left="56"]) .container { padding-left: var(--primitives-space-56); }
	:host([padding-left="64"]) .container { padding-left: var(--primitives-space-64); }
	:host([padding-left="80"]) .container { padding-left: var(--primitives-space-80); }
	:host([padding-left="96"]) .container { padding-left: var(--primitives-space-96); }

	/* # Padding Left — sm viewport */

	:host([sm-padding-left="0"]) .container { @media (max-width: ${smMax$2}) { padding-left: 0; } }
	:host([sm-padding-left="2"]) .container { @media (max-width: ${smMax$2}) { padding-left: var(--primitives-space-2); } }
	:host([sm-padding-left="4"]) .container { @media (max-width: ${smMax$2}) { padding-left: var(--primitives-space-4); } }
	:host([sm-padding-left="6"]) .container { @media (max-width: ${smMax$2}) { padding-left: var(--primitives-space-6); } }
	:host([sm-padding-left="8"]) .container { @media (max-width: ${smMax$2}) { padding-left: var(--primitives-space-8); } }
	:host([sm-padding-left="10"]) .container { @media (max-width: ${smMax$2}) { padding-left: var(--primitives-space-10); } }
	:host([sm-padding-left="12"]) .container { @media (max-width: ${smMax$2}) { padding-left: var(--primitives-space-12); } }
	:host([sm-padding-left="16"]) .container { @media (max-width: ${smMax$2}) { padding-left: var(--primitives-space-16); } }
	:host([sm-padding-left="20"]) .container { @media (max-width: ${smMax$2}) { padding-left: var(--primitives-space-20); } }
	:host([sm-padding-left="24"]) .container { @media (max-width: ${smMax$2}) { padding-left: var(--primitives-space-24); } }
	:host([sm-padding-left="28"]) .container { @media (max-width: ${smMax$2}) { padding-left: var(--primitives-space-28); } }
	:host([sm-padding-left="32"]) .container { @media (max-width: ${smMax$2}) { padding-left: var(--primitives-space-32); } }
	:host([sm-padding-left="40"]) .container { @media (max-width: ${smMax$2}) { padding-left: var(--primitives-space-40); } }
	:host([sm-padding-left="44"]) .container { @media (max-width: ${smMax$2}) { padding-left: var(--primitives-space-44); } }
	:host([sm-padding-left="48"]) .container { @media (max-width: ${smMax$2}) { padding-left: var(--primitives-space-48); } }
	:host([sm-padding-left="56"]) .container { @media (max-width: ${smMax$2}) { padding-left: var(--primitives-space-56); } }
	:host([sm-padding-left="64"]) .container { @media (max-width: ${smMax$2}) { padding-left: var(--primitives-space-64); } }
	:host([sm-padding-left="80"]) .container { @media (max-width: ${smMax$2}) { padding-left: var(--primitives-space-80); } }
	:host([sm-padding-left="96"]) .container { @media (max-width: ${smMax$2}) { padding-left: var(--primitives-space-96); } }

	/* # Padding Left — md viewport */

	:host([md-padding-left="0"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-left: 0; } }
	:host([md-padding-left="2"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-left: var(--primitives-space-2); } }
	:host([md-padding-left="4"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-left: var(--primitives-space-4); } }
	:host([md-padding-left="6"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-left: var(--primitives-space-6); } }
	:host([md-padding-left="8"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-left: var(--primitives-space-8); } }
	:host([md-padding-left="10"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-left: var(--primitives-space-10); } }
	:host([md-padding-left="12"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-left: var(--primitives-space-12); } }
	:host([md-padding-left="16"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-left: var(--primitives-space-16); } }
	:host([md-padding-left="20"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-left: var(--primitives-space-20); } }
	:host([md-padding-left="24"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-left: var(--primitives-space-24); } }
	:host([md-padding-left="28"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-left: var(--primitives-space-28); } }
	:host([md-padding-left="32"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-left: var(--primitives-space-32); } }
	:host([md-padding-left="40"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-left: var(--primitives-space-40); } }
	:host([md-padding-left="44"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-left: var(--primitives-space-44); } }
	:host([md-padding-left="48"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-left: var(--primitives-space-48); } }
	:host([md-padding-left="56"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-left: var(--primitives-space-56); } }
	:host([md-padding-left="64"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-left: var(--primitives-space-64); } }
	:host([md-padding-left="80"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-left: var(--primitives-space-80); } }
	:host([md-padding-left="96"]) .container { @media (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-left: var(--primitives-space-96); } }

	/* # Padding Left — lg viewport */

	:host([lg-padding-left="0"]) .container { @media (min-width: ${lgMin$2}) { padding-left: 0; } }
	:host([lg-padding-left="2"]) .container { @media (min-width: ${lgMin$2}) { padding-left: var(--primitives-space-2); } }
	:host([lg-padding-left="4"]) .container { @media (min-width: ${lgMin$2}) { padding-left: var(--primitives-space-4); } }
	:host([lg-padding-left="6"]) .container { @media (min-width: ${lgMin$2}) { padding-left: var(--primitives-space-6); } }
	:host([lg-padding-left="8"]) .container { @media (min-width: ${lgMin$2}) { padding-left: var(--primitives-space-8); } }
	:host([lg-padding-left="10"]) .container { @media (min-width: ${lgMin$2}) { padding-left: var(--primitives-space-10); } }
	:host([lg-padding-left="12"]) .container { @media (min-width: ${lgMin$2}) { padding-left: var(--primitives-space-12); } }
	:host([lg-padding-left="16"]) .container { @media (min-width: ${lgMin$2}) { padding-left: var(--primitives-space-16); } }
	:host([lg-padding-left="20"]) .container { @media (min-width: ${lgMin$2}) { padding-left: var(--primitives-space-20); } }
	:host([lg-padding-left="24"]) .container { @media (min-width: ${lgMin$2}) { padding-left: var(--primitives-space-24); } }
	:host([lg-padding-left="28"]) .container { @media (min-width: ${lgMin$2}) { padding-left: var(--primitives-space-28); } }
	:host([lg-padding-left="32"]) .container { @media (min-width: ${lgMin$2}) { padding-left: var(--primitives-space-32); } }
	:host([lg-padding-left="40"]) .container { @media (min-width: ${lgMin$2}) { padding-left: var(--primitives-space-40); } }
	:host([lg-padding-left="44"]) .container { @media (min-width: ${lgMin$2}) { padding-left: var(--primitives-space-44); } }
	:host([lg-padding-left="48"]) .container { @media (min-width: ${lgMin$2}) { padding-left: var(--primitives-space-48); } }
	:host([lg-padding-left="56"]) .container { @media (min-width: ${lgMin$2}) { padding-left: var(--primitives-space-56); } }
	:host([lg-padding-left="64"]) .container { @media (min-width: ${lgMin$2}) { padding-left: var(--primitives-space-64); } }
	:host([lg-padding-left="80"]) .container { @media (min-width: ${lgMin$2}) { padding-left: var(--primitives-space-80); } }
	:host([lg-padding-left="96"]) .container { @media (min-width: ${lgMin$2}) { padding-left: var(--primitives-space-96); } }

	/* # Padding Left — sm container */

	:host([layout-area-sm-padding-left="0"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-left: 0; } }
	:host([layout-area-sm-padding-left="2"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-left: var(--primitives-space-2); } }
	:host([layout-area-sm-padding-left="4"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-left: var(--primitives-space-4); } }
	:host([layout-area-sm-padding-left="6"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-left: var(--primitives-space-6); } }
	:host([layout-area-sm-padding-left="8"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-left: var(--primitives-space-8); } }
	:host([layout-area-sm-padding-left="10"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-left: var(--primitives-space-10); } }
	:host([layout-area-sm-padding-left="12"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-left: var(--primitives-space-12); } }
	:host([layout-area-sm-padding-left="16"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-left: var(--primitives-space-16); } }
	:host([layout-area-sm-padding-left="20"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-left: var(--primitives-space-20); } }
	:host([layout-area-sm-padding-left="24"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-left: var(--primitives-space-24); } }
	:host([layout-area-sm-padding-left="28"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-left: var(--primitives-space-28); } }
	:host([layout-area-sm-padding-left="32"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-left: var(--primitives-space-32); } }
	:host([layout-area-sm-padding-left="40"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-left: var(--primitives-space-40); } }
	:host([layout-area-sm-padding-left="44"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-left: var(--primitives-space-44); } }
	:host([layout-area-sm-padding-left="48"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-left: var(--primitives-space-48); } }
	:host([layout-area-sm-padding-left="56"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-left: var(--primitives-space-56); } }
	:host([layout-area-sm-padding-left="64"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-left: var(--primitives-space-64); } }
	:host([layout-area-sm-padding-left="80"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-left: var(--primitives-space-80); } }
	:host([layout-area-sm-padding-left="96"]) .container { @container layout-area (max-width: ${smMax$2}) { padding-left: var(--primitives-space-96); } }

	/* # Padding Left — md container */

	:host([layout-area-md-padding-left="0"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-left: 0; } }
	:host([layout-area-md-padding-left="2"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-left: var(--primitives-space-2); } }
	:host([layout-area-md-padding-left="4"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-left: var(--primitives-space-4); } }
	:host([layout-area-md-padding-left="6"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-left: var(--primitives-space-6); } }
	:host([layout-area-md-padding-left="8"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-left: var(--primitives-space-8); } }
	:host([layout-area-md-padding-left="10"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-left: var(--primitives-space-10); } }
	:host([layout-area-md-padding-left="12"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-left: var(--primitives-space-12); } }
	:host([layout-area-md-padding-left="16"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-left: var(--primitives-space-16); } }
	:host([layout-area-md-padding-left="20"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-left: var(--primitives-space-20); } }
	:host([layout-area-md-padding-left="24"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-left: var(--primitives-space-24); } }
	:host([layout-area-md-padding-left="28"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-left: var(--primitives-space-28); } }
	:host([layout-area-md-padding-left="32"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-left: var(--primitives-space-32); } }
	:host([layout-area-md-padding-left="40"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-left: var(--primitives-space-40); } }
	:host([layout-area-md-padding-left="44"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-left: var(--primitives-space-44); } }
	:host([layout-area-md-padding-left="48"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-left: var(--primitives-space-48); } }
	:host([layout-area-md-padding-left="56"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-left: var(--primitives-space-56); } }
	:host([layout-area-md-padding-left="64"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-left: var(--primitives-space-64); } }
	:host([layout-area-md-padding-left="80"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-left: var(--primitives-space-80); } }
	:host([layout-area-md-padding-left="96"]) .container { @container layout-area (min-width: ${mdMin$3}) and (max-width: ${mdMax$1}) { padding-left: var(--primitives-space-96); } }

	/* # Padding Left — lg container */

	:host([layout-area-lg-padding-left="0"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-left: 0; } }
	:host([layout-area-lg-padding-left="2"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-left: var(--primitives-space-2); } }
	:host([layout-area-lg-padding-left="4"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-left: var(--primitives-space-4); } }
	:host([layout-area-lg-padding-left="6"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-left: var(--primitives-space-6); } }
	:host([layout-area-lg-padding-left="8"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-left: var(--primitives-space-8); } }
	:host([layout-area-lg-padding-left="10"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-left: var(--primitives-space-10); } }
	:host([layout-area-lg-padding-left="12"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-left: var(--primitives-space-12); } }
	:host([layout-area-lg-padding-left="16"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-left: var(--primitives-space-16); } }
	:host([layout-area-lg-padding-left="20"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-left: var(--primitives-space-20); } }
	:host([layout-area-lg-padding-left="24"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-left: var(--primitives-space-24); } }
	:host([layout-area-lg-padding-left="28"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-left: var(--primitives-space-28); } }
	:host([layout-area-lg-padding-left="32"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-left: var(--primitives-space-32); } }
	:host([layout-area-lg-padding-left="40"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-left: var(--primitives-space-40); } }
	:host([layout-area-lg-padding-left="44"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-left: var(--primitives-space-44); } }
	:host([layout-area-lg-padding-left="48"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-left: var(--primitives-space-48); } }
	:host([layout-area-lg-padding-left="56"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-left: var(--primitives-space-56); } }
	:host([layout-area-lg-padding-left="64"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-left: var(--primitives-space-64); } }
	:host([layout-area-lg-padding-left="80"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-left: var(--primitives-space-80); } }
	:host([layout-area-lg-padding-left="96"]) .container { @container layout-area (min-width: ${lgMin$2}) { padding-left: var(--primitives-space-96); } }

`;
function containerTemplate(_component) {
  return html`
		<div class="container">
			<slot></slot>
		</div>
	`;
}
var __defProp$i = Object.defineProperty;
var __getOwnPropDesc$j = Object.getOwnPropertyDescriptor;
var __decorateClass$j = (decorators, target, key, kind) => {
  var result = kind > 1 ? void 0 : kind ? __getOwnPropDesc$j(target, key) : target;
  for (var i = decorators.length - 1, decorator; i >= 0; i--)
    if (decorator = decorators[i])
      result = (kind ? decorator(target, key, result) : decorator(result)) || result;
  if (kind && result) __defProp$i(target, key, result);
  return result;
};
let NDDContainer = class extends LitElement {
  constructor() {
    super(...arguments);
    this.padding = void 0;
    this.paddingInline = void 0;
    this.paddingBlock = void 0;
    this.paddingTop = void 0;
    this.paddingRight = void 0;
    this.paddingBottom = void 0;
    this.paddingLeft = void 0;
    this.smPadding = void 0;
    this.smPaddingInline = void 0;
    this.smPaddingBlock = void 0;
    this.smPaddingTop = void 0;
    this.smPaddingRight = void 0;
    this.smPaddingBottom = void 0;
    this.smPaddingLeft = void 0;
    this.mdPadding = void 0;
    this.mdPaddingInline = void 0;
    this.mdPaddingBlock = void 0;
    this.mdPaddingTop = void 0;
    this.mdPaddingRight = void 0;
    this.mdPaddingBottom = void 0;
    this.mdPaddingLeft = void 0;
    this.lgPadding = void 0;
    this.lgPaddingInline = void 0;
    this.lgPaddingBlock = void 0;
    this.lgPaddingTop = void 0;
    this.lgPaddingRight = void 0;
    this.lgPaddingBottom = void 0;
    this.lgPaddingLeft = void 0;
    this.layoutAreaSmPadding = void 0;
    this.layoutAreaSmPaddingInline = void 0;
    this.layoutAreaSmPaddingBlock = void 0;
    this.layoutAreaSmPaddingTop = void 0;
    this.layoutAreaSmPaddingRight = void 0;
    this.layoutAreaSmPaddingBottom = void 0;
    this.layoutAreaSmPaddingLeft = void 0;
    this.layoutAreaMdPadding = void 0;
    this.layoutAreaMdPaddingInline = void 0;
    this.layoutAreaMdPaddingBlock = void 0;
    this.layoutAreaMdPaddingTop = void 0;
    this.layoutAreaMdPaddingRight = void 0;
    this.layoutAreaMdPaddingBottom = void 0;
    this.layoutAreaMdPaddingLeft = void 0;
    this.layoutAreaLgPadding = void 0;
    this.layoutAreaLgPaddingInline = void 0;
    this.layoutAreaLgPaddingBlock = void 0;
    this.layoutAreaLgPaddingTop = void 0;
    this.layoutAreaLgPaddingRight = void 0;
    this.layoutAreaLgPaddingBottom = void 0;
    this.layoutAreaLgPaddingLeft = void 0;
  }
  render() {
    return containerTemplate();
  }
};
NDDContainer.styles = containerStyles;
__decorateClass$j([
  property({ type: String, reflect: true })
], NDDContainer.prototype, "padding", 2);
__decorateClass$j([
  property({ type: String, reflect: true })
], NDDContainer.prototype, "paddingInline", 2);
__decorateClass$j([
  property({ type: String, reflect: true })
], NDDContainer.prototype, "paddingBlock", 2);
__decorateClass$j([
  property({ type: String, reflect: true })
], NDDContainer.prototype, "paddingTop", 2);
__decorateClass$j([
  property({ type: String, reflect: true })
], NDDContainer.prototype, "paddingRight", 2);
__decorateClass$j([
  property({ type: String, reflect: true })
], NDDContainer.prototype, "paddingBottom", 2);
__decorateClass$j([
  property({ type: String, reflect: true })
], NDDContainer.prototype, "paddingLeft", 2);
__decorateClass$j([
  property({ type: String, reflect: true })
], NDDContainer.prototype, "smPadding", 2);
__decorateClass$j([
  property({ type: String, reflect: true })
], NDDContainer.prototype, "smPaddingInline", 2);
__decorateClass$j([
  property({ type: String, reflect: true })
], NDDContainer.prototype, "smPaddingBlock", 2);
__decorateClass$j([
  property({ type: String, reflect: true })
], NDDContainer.prototype, "smPaddingTop", 2);
__decorateClass$j([
  property({ type: String, reflect: true })
], NDDContainer.prototype, "smPaddingRight", 2);
__decorateClass$j([
  property({ type: String, reflect: true })
], NDDContainer.prototype, "smPaddingBottom", 2);
__decorateClass$j([
  property({ type: String, reflect: true })
], NDDContainer.prototype, "smPaddingLeft", 2);
__decorateClass$j([
  property({ type: String, reflect: true })
], NDDContainer.prototype, "mdPadding", 2);
__decorateClass$j([
  property({ type: String, reflect: true })
], NDDContainer.prototype, "mdPaddingInline", 2);
__decorateClass$j([
  property({ type: String, reflect: true })
], NDDContainer.prototype, "mdPaddingBlock", 2);
__decorateClass$j([
  property({ type: String, reflect: true })
], NDDContainer.prototype, "mdPaddingTop", 2);
__decorateClass$j([
  property({ type: String, reflect: true })
], NDDContainer.prototype, "mdPaddingRight", 2);
__decorateClass$j([
  property({ type: String, reflect: true })
], NDDContainer.prototype, "mdPaddingBottom", 2);
__decorateClass$j([
  property({ type: String, reflect: true })
], NDDContainer.prototype, "mdPaddingLeft", 2);
__decorateClass$j([
  property({ type: String, reflect: true })
], NDDContainer.prototype, "lgPadding", 2);
__decorateClass$j([
  property({ type: String, reflect: true })
], NDDContainer.prototype, "lgPaddingInline", 2);
__decorateClass$j([
  property({ type: String, reflect: true })
], NDDContainer.prototype, "lgPaddingBlock", 2);
__decorateClass$j([
  property({ type: String, reflect: true })
], NDDContainer.prototype, "lgPaddingTop", 2);
__decorateClass$j([
  property({ type: String, reflect: true })
], NDDContainer.prototype, "lgPaddingRight", 2);
__decorateClass$j([
  property({ type: String, reflect: true })
], NDDContainer.prototype, "lgPaddingBottom", 2);
__decorateClass$j([
  property({ type: String, reflect: true })
], NDDContainer.prototype, "lgPaddingLeft", 2);
__decorateClass$j([
  property({ type: String, reflect: true })
], NDDContainer.prototype, "layoutAreaSmPadding", 2);
__decorateClass$j([
  property({ type: String, reflect: true })
], NDDContainer.prototype, "layoutAreaSmPaddingInline", 2);
__decorateClass$j([
  property({ type: String, reflect: true })
], NDDContainer.prototype, "layoutAreaSmPaddingBlock", 2);
__decorateClass$j([
  property({ type: String, reflect: true })
], NDDContainer.prototype, "layoutAreaSmPaddingTop", 2);
__decorateClass$j([
  property({ type: String, reflect: true })
], NDDContainer.prototype, "layoutAreaSmPaddingRight", 2);
__decorateClass$j([
  property({ type: String, reflect: true })
], NDDContainer.prototype, "layoutAreaSmPaddingBottom", 2);
__decorateClass$j([
  property({ type: String, reflect: true })
], NDDContainer.prototype, "layoutAreaSmPaddingLeft", 2);
__decorateClass$j([
  property({ type: String, reflect: true })
], NDDContainer.prototype, "layoutAreaMdPadding", 2);
__decorateClass$j([
  property({ type: String, reflect: true })
], NDDContainer.prototype, "layoutAreaMdPaddingInline", 2);
__decorateClass$j([
  property({ type: String, reflect: true })
], NDDContainer.prototype, "layoutAreaMdPaddingBlock", 2);
__decorateClass$j([
  property({ type: String, reflect: true })
], NDDContainer.prototype, "layoutAreaMdPaddingTop", 2);
__decorateClass$j([
  property({ type: String, reflect: true })
], NDDContainer.prototype, "layoutAreaMdPaddingRight", 2);
__decorateClass$j([
  property({ type: String, reflect: true })
], NDDContainer.prototype, "layoutAreaMdPaddingBottom", 2);
__decorateClass$j([
  property({ type: String, reflect: true })
], NDDContainer.prototype, "layoutAreaMdPaddingLeft", 2);
__decorateClass$j([
  property({ type: String, reflect: true })
], NDDContainer.prototype, "layoutAreaLgPadding", 2);
__decorateClass$j([
  property({ type: String, reflect: true })
], NDDContainer.prototype, "layoutAreaLgPaddingInline", 2);
__decorateClass$j([
  property({ type: String, reflect: true })
], NDDContainer.prototype, "layoutAreaLgPaddingBlock", 2);
__decorateClass$j([
  property({ type: String, reflect: true })
], NDDContainer.prototype, "layoutAreaLgPaddingTop", 2);
__decorateClass$j([
  property({ type: String, reflect: true })
], NDDContainer.prototype, "layoutAreaLgPaddingRight", 2);
__decorateClass$j([
  property({ type: String, reflect: true })
], NDDContainer.prototype, "layoutAreaLgPaddingBottom", 2);
__decorateClass$j([
  property({ type: String, reflect: true })
], NDDContainer.prototype, "layoutAreaLgPaddingLeft", 2);
NDDContainer = __decorateClass$j([
  customElement("ndd-container")
], NDDContainer);
const dividerStyles = css`
	:host {
		display: block;
		flex-shrink: 0;
	}

	:host([hidden]) {
		display: none;
	}

	.divider {
		display: block;
		width: 100%;
		height: var(--semantics-dividers-thickness);
		margin: 0;
		border: none;
		background-color: var(--semantics-dividers-color);

		@media (forced-colors: active) {
			background-color: CanvasText;
		}
	}
`;
function dividerTemplate(_component) {
  return html`
		<hr class="divider">
	`;
}
var __getOwnPropDesc$i = Object.getOwnPropertyDescriptor;
var __decorateClass$i = (decorators, target, key, kind) => {
  var result = kind > 1 ? void 0 : kind ? __getOwnPropDesc$i(target, key) : target;
  for (var i = decorators.length - 1, decorator; i >= 0; i--)
    if (decorator = decorators[i])
      result = decorator(result) || result;
  return result;
};
let NDDDivider = class extends LitElement {
  render() {
    return dividerTemplate();
  }
};
NDDDivider.styles = dividerStyles;
NDDDivider = __decorateClass$i([
  customElement("ndd-divider")
], NDDDivider);
const smMax$1 = unsafeCSS(breakpoints.smMax);
const mdMin$2 = unsafeCSS(breakpoints.mdMin);
const lgMin$1 = unsafeCSS(breakpoints.lgMin);
const sheetStyles = css`

	/* # Host */

	:host {
		display: block;
	}


	/* # Keyframes — right */

	@keyframes sheet-slide-in-right {
		from { transform: translateX(100%); }
		to { transform: translateX(0); }
	}

	@keyframes sheet-slide-out-right {
		from { transform: translateX(0); }
		to { transform: translateX(100%); }
	}


	/* # Keyframes — left */

	@keyframes sheet-slide-in-left {
		from { transform: translateX(-100%); }
		to { transform: translateX(0); }
	}

	@keyframes sheet-slide-out-left {
		from { transform: translateX(0); }
		to { transform: translateX(-100%); }
	}


	/* # Keyframes — bottom */

	@keyframes sheet-slide-in-bottom {
		from { transform: translateY(100%); }
		to { transform: translateY(0); }
	}

	@keyframes sheet-slide-out-bottom {
		from { transform: translateY(0); }
		to { transform: translateY(100%); }
	}


	/* # Sheet base */

	.sheet {
		display: flex;
		flex-direction: column;
		border: none;
		padding: 0;
		margin: 0;
		background: var(--semantics-surfaces-background-color);
		box-shadow: var(--components-sheet-box-shadow);
		overflow: hidden;
		position: fixed;
	}

	.sheet:focus-visible {
		outline: none;
	}

	.sheet.is-keyboard-focus:focus {
		box-shadow: var(--semantics-focus-ring-box-shadow), var(--components-sheet-box-shadow);
		outline: var(--semantics-focus-ring-outline);
	}

	.sheet:not([open]) {
		display: none;
	}

	.sheet::backdrop {
		background: var(--semantics-overlays-backdrop-color);
	}

	:host([modeless]) .sheet::backdrop {
		background: transparent;
	}


	/* # Placement: right (default) */

	:host([placement='right']) .sheet,
	:host(:not([placement])) .sheet {
		inset: var(--components-sheet-side-inset) var(--components-sheet-side-inset) var(--components-sheet-side-inset) auto;
		width: var(--components-sheet-side-md-width);
		height: calc(100dvh - var(--components-sheet-side-inset) * 2);
		border-radius: var(--semantics-overlays-corner-radius);

		@media (min-width: ${lgMin$1}) {
			width: var(--components-sheet-side-lg-width);
		}

		&[open] {
			animation: sheet-slide-in-right var(--components-sheet-side-animation-duration) ease both;
		}

		&.is-closing {
			animation: sheet-slide-out-right var(--components-sheet-side-animation-duration) ease both;
		}
	}


	/* # Placement: left */

	:host([placement='left']) .sheet {
		inset: var(--components-sheet-side-inset) auto var(--components-sheet-side-inset) var(--components-sheet-side-inset);
		width: var(--components-sheet-side-md-width);
		height: calc(100dvh - var(--components-sheet-side-inset) * 2);
		border-radius: var(--semantics-overlays-corner-radius);

		@media (min-width: ${lgMin$1}) {
			width: var(--components-sheet-side-lg-width);
		}

		&[open] {
			animation: sheet-slide-in-left var(--components-sheet-side-animation-duration) ease both;
		}

		&.is-closing {
			animation: sheet-slide-out-left var(--components-sheet-side-animation-duration) ease both;
		}
	}


	/* # Placement: bottom */

	:host([placement='bottom']) .sheet {
		inset: auto 0 0 0;
		max-width: var(--semantics-page-sections-body-max-width);
		max-height: calc(100dvh - var(--components-sheet-bottom-top-inset));
		height: auto;
		margin-inline: auto;
		border-radius: var(--semantics-overlays-corner-radius) var(--semantics-overlays-corner-radius) 0 0;

		@media (max-width: ${smMax$1}) {
			width: 100%;
			max-width: 100%;
		}

		@media (min-width: ${mdMin$2}) {
			width: calc(100% - var(--components-sheet-bottom-md-inline-inset));
		}

		@media (min-width: ${lgMin$1}) {
			width: calc(100% - var(--components-sheet-bottom-lg-inline-inset));
		}

		&[open] {
			animation: sheet-slide-in-bottom var(--components-sheet-bottom-animation-duration) ease both;
		}

		&.is-closing {
			animation: sheet-slide-out-bottom var(--components-sheet-bottom-animation-duration) ease both;
		}
	}


	/* # Responsive: sm viewport — all placements become bottom sheet */

	@media (max-width: ${smMax$1}) {
		:host([placement='right']) .sheet,
		:host(:not([placement])) .sheet,
		:host([placement='left']) .sheet {
			inset: auto 0 0 0;
			width: 100%;
			max-width: 100%;
			height: auto;
			max-height: calc(100dvh - var(--components-sheet-bottom-top-inset));
			border-radius: var(--semantics-overlays-corner-radius) var(--semantics-overlays-corner-radius) 0 0;

			&[open] {
				animation: sheet-slide-in-bottom var(--components-sheet-bottom-animation-duration) ease both;
			}

			&.is-closing {
				animation: sheet-slide-out-bottom var(--components-sheet-bottom-animation-duration) ease both;
			}
		}
	}


	/* # Reduced motion */

	@media (prefers-reduced-motion: reduce) {
		.sheet[open],
		.sheet.is-closing {
			animation: none;
		}
	}


	/* # Sheet body */

	.sheet__body {
		display: flex;
		flex-direction: column;
		flex-grow: 1;
		min-height: 0;
		width: 100%;
	}

	::slotted(*) {
		flex: 1;
		min-height: 0;
	}
`;
function sheetTemplate(component) {
  return html`
		<dialog class="sheet"
			aria-label=${component.accessibleLabel}
			aria-modal=${component.modeless ? nothing : "true"}
			@click=${component._handleDialogClick}
			@cancel=${component._handleCancel}
		>
			<div class="sheet__body">
				<slot></slot>
			</div>
		</dialog>
	`;
}
var __defProp$h = Object.defineProperty;
var __getOwnPropDesc$h = Object.getOwnPropertyDescriptor;
var __decorateClass$h = (decorators, target, key, kind) => {
  var result = kind > 1 ? void 0 : kind ? __getOwnPropDesc$h(target, key) : target;
  for (var i = decorators.length - 1, decorator; i >= 0; i--)
    if (decorator = decorators[i])
      result = (kind ? decorator(target, key, result) : decorator(result)) || result;
  if (kind && result) __defProp$h(target, key, result);
  return result;
};
let NDDSheet = class extends LitElement {
  constructor() {
    super(...arguments);
    this.placement = "right";
    this.modeless = false;
    this.accessibleLabel = "Dialoogvenster";
    this._hasWarnedLabel = false;
    this._closing = false;
    this._handleDismiss = () => {
      this.hide();
    };
  }
  get _dialog() {
    return this.shadowRoot?.querySelector("dialog") ?? null;
  }
  connectedCallback() {
    super.connectedCallback();
    this.addEventListener("dismiss", this._handleDismiss);
  }
  disconnectedCallback() {
    super.disconnectedCallback();
    this.removeEventListener("dismiss", this._handleDismiss);
  }
  show() {
    const dialog = this._dialog;
    if (!dialog) return;
    if (this.accessibleLabel === "Dialoogvenster" && !this._hasWarnedLabel) {
      this._hasWarnedLabel = true;
      console.warn('<ndd-sheet>: No accessible-label provided. Screen readers will announce this dialog as "Dialoogvenster". Set accessible-label to a descriptive name matching the dialog title.');
    }
    if (this.modeless) {
      dialog.show();
    } else {
      dialog.showModal();
    }
    this._manageFocus();
    this.dispatchEvent(new CustomEvent("open", { bubbles: true, composed: true }));
  }
  _manageFocus() {
    if (this.querySelector("[autofocus]")) return;
    const dialog = this._dialog;
    if (!dialog) return;
    dialog.classList.toggle("is-keyboard-focus", isKeyboardMode());
    dialog.focus();
  }
  hide() {
    const dialog = this._dialog;
    if (!dialog || !dialog.open || this._closing) return;
    this._closing = true;
    dialog.classList.add("is-closing");
    dialog.addEventListener("animationend", () => {
      dialog.classList.remove("is-closing");
      this._closing = false;
      dialog.close();
      this.dispatchEvent(new CustomEvent("close", { bubbles: true, composed: true }));
    }, { once: true });
    requestAnimationFrame(() => {
      if (this._closing && getComputedStyle(dialog).animationName === "none") {
        dialog.classList.remove("is-closing");
        this._closing = false;
        dialog.close();
        this.dispatchEvent(new CustomEvent("close", { bubbles: true, composed: true }));
      }
    });
  }
  _handleDialogClick(e) {
    if (this.modeless) return;
    if (e.target === this._dialog) {
      this.hide();
    }
  }
  _handleCancel(e) {
    e.preventDefault();
    this.hide();
  }
  render() {
    return sheetTemplate(this);
  }
};
NDDSheet.styles = sheetStyles;
__decorateClass$h([
  property({ type: String, reflect: true })
], NDDSheet.prototype, "placement", 2);
__decorateClass$h([
  property({ type: Boolean, reflect: true })
], NDDSheet.prototype, "modeless", 2);
__decorateClass$h([
  property({ type: String, attribute: "accessible-label" })
], NDDSheet.prototype, "accessibleLabel", 2);
NDDSheet = __decorateClass$h([
  customElement("ndd-sheet")
], NDDSheet);
const nddSheet = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  get NDDSheet() {
    return NDDSheet;
  }
}, Symbol.toStringTag, { value: "Module" }));
const styles$9 = css`
	/* # Host */

	:host {
		display: block;
		position: relative;
		--_drag-clone-top: 0px;
		--_drag-clone-left: 0px;
		--_drag-clone-width: 0px;
		--_drag-clone-height: 0px;
		--_drag-clone-opacity: 0.95;
		--_drag-clone-z-index: 100;
	}


	/* # Body */

	.list__body {
		display: flex;
		flex-direction: column;
		gap: var(--primitives-space-8);
	}


	/* # Header & footer */

	.list__header,
	.list__footer {
		display: contents;
	}


	/* # Items */

	.list__items {
		display: flex;
		flex-direction: column;
	}


	/* # No dividers */

	:host([no-dividers]) {
		--context-list-divider-display: none;
	}


	/* # Variant: simple */

	:host([variant='simple']) .list__items {
		border-top: var(--semantics-dividers-thickness) solid var(--semantics-dividers-color);
	}

	:host([variant='simple'][no-dividers]) .list__items {
		border-top: none;
	}


	/* # Variant: box */

	:host([variant='box']) .list__items {
		background-color: var(--semantics-surfaces-tinted-background-color);
		border-radius: var(--components-list-corner-radius);
		overflow: hidden;
	}


	/* # Variant: inset */

	:host([variant='inset']) .list__items {
		background-color: var(--semantics-surfaces-background-color);
		border-radius: var(--components-list-corner-radius);
		overflow: hidden;
	}


	/* # Drag placeholder */

	::slotted(.ndd-list-drag-placeholder) {
		box-sizing: border-box;
		background-color: var(--components-list-drag-placeholder-background-color);
		pointer-events: none;
		border-radius: var(--components-list-item-indicator-corner-radius);
	}


	/* # Drag clone */

	.list__drag-clone {
		position: absolute;
		top: var(--_drag-clone-top);
		left: var(--_drag-clone-left);
		width: var(--_drag-clone-width);
		height: var(--_drag-clone-height);
		display: flex;
		flex-direction: row;
		align-items: stretch;
		pointer-events: none;
		opacity: var(--_drag-clone-opacity);
		border-radius: var(--components-list-item-indicator-corner-radius);
		background: var(--semantics-surfaces-background-color);
		z-index: var(--_drag-clone-z-index);
		overflow: hidden;
	}


	/* # Announcer */

	.list__polite-announcer,
	.list__assertive-announcer {
		position: absolute;
		width: 1px;
		height: 1px;
		padding: 0;
		margin: -1px;
		overflow: hidden;
		clip-path: inset(50%);
		white-space: nowrap;
		border: 0;
	}
`;
const template$9 = (itemsLabel, hasHeader) => html`
	<div class="list__body">
		<div class="list__header">
			<slot name="header"></slot>
		</div>
		<div class="list__items"
			role="list"
			aria-label=${ifDefined(hasHeader ? void 0 : itemsLabel)}
		>
			<slot></slot>
		</div>
		<div class="list__footer">
			<slot name="footer"></slot>
		</div>
	</div>
	<div class="list__polite-announcer"
		role="status"
		aria-live="polite"
		aria-atomic="true"
	></div>
	<div class="list__assertive-announcer"
		role="alert"
		aria-live="assertive"
		aria-atomic="true"
	></div>
`;
const nddListTranslations = {
  "components.list.items-label-text": "Lijst",
  "components.list.drag-grabbed-text": "Item opgepakt. Gebruik de pijltjestoetsen om te verplaatsen, Spatie of Enter om neer te zetten, Escape om te annuleren.",
  "components.list.drag-dropped-text": "Item neergezet op positie {position}.",
  "components.list.drag-no-change-text": "Item neergezet. Positie ongewijzigd.",
  "components.list.drag-cancelled-text": "Slepen geannuleerd.",
  "components.list.drag-position-text": "Positie {position} van {total}.",
  "components.list.drag-handle-active-label-text": "Positie {position} van {total} — druk Enter om te bevestigen, Escape om te annuleren."
};
var __defProp$g = Object.defineProperty;
var __getOwnPropDesc$g = Object.getOwnPropertyDescriptor;
var __decorateClass$g = (decorators, target, key, kind) => {
  var result = kind > 1 ? void 0 : kind ? __getOwnPropDesc$g(target, key) : target;
  for (var i = decorators.length - 1, decorator; i >= 0; i--)
    if (decorator = decorators[i])
      result = (kind ? decorator(target, key, result) : decorator(result)) || result;
  if (kind && result) __defProp$g(target, key, result);
  return result;
};
let NDDList = class extends LitElement {
  constructor() {
    super(...arguments);
    this.variant = "simple";
    this.reorderable = false;
    this.noDividers = false;
    this.translations = {};
    this._mergedTranslations = { ...nddListTranslations };
    this._hasHeader = false;
    this._draggingEl = null;
    this._draggingFromIndex = -1;
    this._placeholder = null;
    this._currentDropIndex = -1;
    this._keyboardDragging = false;
    this._pointerId = null;
    this._clone = null;
    this._cloneOffsetY = 0;
    this._listRect = null;
    this._onPointerDown = (event) => {
      if (!this.reorderable) return;
      const path = event.composedPath();
      const hasDragHandle = path.some(
        (el) => el instanceof Element && el.hasAttribute("draggable-only")
      );
      if (!hasDragHandle) return;
      const item = path.find(
        (el) => el instanceof Element && el.tagName.toLowerCase() === "ndd-list-item"
      );
      if (!item) return;
      event.preventDefault();
      this._lastPointerY = event.clientY;
      this._startDrag(item, event.clientY);
      const handle = path.find(
        (el) => el instanceof HTMLButtonElement
      );
      handle?.focus();
      this._pointerId = event.pointerId;
      this.setPointerCapture(event.pointerId);
      this.addEventListener("pointermove", this._onPointerMove);
      this.addEventListener("pointerup", this._onPointerUp);
      this.addEventListener("pointercancel", this._onPointerCancel);
    };
    this._lastPointerY = 0;
    this._onPointerMove = (event) => {
      if (!this._draggingEl || !this._placeholder) return;
      if (this._clone) {
        this._listRect = this.getBoundingClientRect();
        this._clone.style.setProperty("--_drag-clone-top", `${event.clientY - this._listRect.top - this._cloneOffsetY}px`);
      }
      const draggingDown = event.clientY >= this._lastPointerY;
      this._lastPointerY = event.clientY;
      const items = this._getItems();
      const nonDragging = items.filter((i) => i !== this._draggingEl);
      const pointerY = event.clientY;
      let toIndex = nonDragging.length;
      for (let i = 0; i < nonDragging.length; i++) {
        const inner = nonDragging[i].shadowRoot?.querySelector(".list-item") ?? nonDragging[i];
        const rect = inner.getBoundingClientRect();
        const threshold = draggingDown ? rect.top : rect.bottom;
        if (pointerY < threshold) {
          toIndex = i;
          break;
        }
      }
      this._setDropIndex(toIndex);
    };
    this._onPointerUp = (_event) => {
      this._endDrag();
    };
    this._onPointerCancel = () => {
      this._cancelDrag();
    };
    this._onKeyDown = (event) => {
      if (!this.reorderable) return;
      if (this._keyboardDragging) {
        switch (event.key) {
          case "ArrowUp": {
            event.preventDefault();
            const current = this._getDropIndex();
            this._setDropIndex(Math.max(0, current - 1));
            this._announce(this._dragPositionAnnouncement());
            if (this._draggingEl) this._setDragHandleLabel(this._draggingEl, this._dragPositionLabel());
            break;
          }
          case "ArrowDown": {
            event.preventDefault();
            const items = this._getItems();
            const current = this._getDropIndex();
            this._setDropIndex(Math.min(items.length - 1, current + 1));
            this._announce(this._dragPositionAnnouncement());
            if (this._draggingEl) this._setDragHandleLabel(this._draggingEl, this._dragPositionLabel());
            break;
          }
          case "Enter":
          case " ":
            event.preventDefault();
            this._endDrag();
            break;
          case "Escape":
            event.preventDefault();
            this._cancelDrag();
            break;
        }
        return;
      }
      if (event.key !== " " && event.key !== "Enter") return;
      const path = event.composedPath();
      const hasDragHandle = path.some(
        (el) => el instanceof Element && el.hasAttribute("draggable-only")
      );
      if (!hasDragHandle) return;
      const item = path.find(
        (el) => el instanceof Element && el.tagName.toLowerCase() === "ndd-list-item"
      );
      if (!item) return;
      event.preventDefault();
      this._keyboardDragging = true;
      this._startDrag(item);
      this._announce(this._t("components.list.drag-grabbed-text"), true);
      this._setDragHandleLabel(item, this._dragPositionLabel());
    };
  }
  // — Lifecycle ————————————————————————————————————————————————————————————
  firstUpdated() {
    const slot = this.shadowRoot?.querySelector("slot:not([name])");
    slot?.addEventListener("slotchange", () => this._updateItems());
    this._updateItems();
    const headerSlot = this.shadowRoot?.querySelector('slot[name="header"]');
    headerSlot?.addEventListener("slotchange", () => {
      this._hasHeader = headerSlot.assignedElements().length > 0;
    });
  }
  connectedCallback() {
    super.connectedCallback();
    this.addEventListener("pointerdown", this._onPointerDown);
    this.addEventListener("keydown", this._onKeyDown);
  }
  disconnectedCallback() {
    super.disconnectedCallback();
    this.removeEventListener("pointerdown", this._onPointerDown);
    this.removeEventListener("keydown", this._onKeyDown);
    this._cancelDrag();
  }
  updated(changed) {
    if (changed.has("reorderable")) {
      this._updateItems();
    }
    if (changed.has("translations")) {
      this._mergedTranslations = { ...nddListTranslations, ...this.translations };
    }
  }
  // — Items ————————————————————————————————————————————————————————————————
  _getItems() {
    const slot = this.shadowRoot?.querySelector("slot:not([name])");
    return (slot?.assignedElements() ?? []).filter(
      (el) => el.tagName.toLowerCase() === "ndd-list-item" && !el.hasAttribute("data-ndd-placeholder")
    );
  }
  _updateItems() {
    const items = this._getItems();
    items.forEach((item, index) => {
      item.classList.toggle("is-last", index === items.length - 1);
      if (this.reorderable) {
        item.setAttribute("reorderable", "");
      } else {
        item.removeAttribute("reorderable");
      }
    });
  }
  // — Drag: core ———————————————————————————————————————————————————————————
  _startDrag(item, clientY = 0) {
    const items = this._getItems();
    const fromIndex = items.indexOf(item);
    if (fromIndex === -1) return;
    this._draggingEl = item;
    this._draggingFromIndex = fromIndex;
    this._currentDropIndex = fromIndex;
    const inner = item.shadowRoot?.querySelector(".list-item") ?? item;
    const rect = inner.getBoundingClientRect();
    this._placeholder = document.createElement("div");
    this._placeholder.className = "ndd-list-drag-placeholder";
    this._placeholder.setAttribute("aria-hidden", "true");
    this._placeholder.setAttribute("data-ndd-placeholder", "");
    this._placeholder.style.height = `${rect.height}px`;
    item.after(this._placeholder);
    item.classList.add("is-dragging");
    if (!this._keyboardDragging) {
      item.classList.add("is-dragging-pointer");
      this._listRect = this.getBoundingClientRect();
      this._cloneOffsetY = clientY - rect.top;
      const hostClone = item.cloneNode(true);
      hostClone.classList.remove("is-dragging");
      hostClone.classList.remove("is-dragging-pointer");
      hostClone.setAttribute("data-ndd-clone", "");
      this._clone = document.createElement("div");
      this._clone.className = "list__drag-clone";
      this._clone.style.setProperty("--_drag-clone-top", `${clientY - this._listRect.top - this._cloneOffsetY}px`);
      this._clone.style.setProperty("--_drag-clone-left", `${rect.left - this._listRect.left}px`);
      this._clone.style.setProperty("--_drag-clone-width", `${rect.width}px`);
      this._clone.style.setProperty("--_drag-clone-height", `${rect.height}px`);
      this._clone.appendChild(hostClone);
      this.renderRoot.appendChild(this._clone);
    }
  }
  /**
   * Places the placeholder so the dragged item will land at position `toIndex`
   * among the non-dragging items (0 = before first, nonDragging.length = after last).
   */
  _setDropIndex(toIndex) {
    if (!this._placeholder || !this._draggingEl) return;
    const nonDragging = this._getItems().filter((i) => i !== this._draggingEl);
    const clamped = Math.max(0, Math.min(nonDragging.length, toIndex));
    this._currentDropIndex = clamped;
    this._placeholder.remove();
    if (nonDragging.length === 0) {
      this._draggingEl.after(this._placeholder);
      return;
    }
    if (clamped === 0) {
      nonDragging[0].before(this._placeholder);
    } else {
      nonDragging[clamped - 1].after(this._placeholder);
    }
  }
  _getDropIndex() {
    return this._currentDropIndex;
  }
  _endDrag() {
    if (!this._draggingEl) return;
    const fromIndex = this._draggingFromIndex;
    const toIndex = this._getDropIndex();
    const movedItem = this._draggingEl;
    this._cleanupDrag();
    if (fromIndex !== toIndex) {
      this.dispatchEvent(
        new CustomEvent("ndd-reorder", {
          detail: { fromIndex, toIndex },
          bubbles: true,
          composed: true
        })
      );
      this._announce(this._t("components.list.drag-dropped-text", { position: toIndex + 1 }));
      requestAnimationFrame(() => {
        const handle = movedItem.querySelector("[draggable-only]")?.shadowRoot?.querySelector("button");
        handle?.focus();
      });
    } else {
      this._announce(this._t("components.list.drag-no-change-text"));
    }
  }
  _cancelDrag() {
    if (!this._draggingEl) return;
    this._cleanupDrag();
    this._announce(this._t("components.list.drag-cancelled-text"));
  }
  _cleanupDrag() {
    if (this._draggingEl) this._setDragHandleLabel(this._draggingEl);
    this._draggingEl?.classList.remove("is-dragging");
    this._draggingEl?.classList.remove("is-dragging-pointer");
    this._placeholder?.remove();
    this._clone?.remove();
    if (this._pointerId !== null) {
      try {
        this.releasePointerCapture(this._pointerId);
      } catch (e) {
        if (!(e instanceof DOMException)) throw e;
      }
      this._pointerId = null;
    }
    this.removeEventListener("pointermove", this._onPointerMove);
    this.removeEventListener("pointerup", this._onPointerUp);
    this.removeEventListener("pointercancel", this._onPointerCancel);
    this._draggingEl = null;
    this._draggingFromIndex = -1;
    this._placeholder = null;
    this._clone = null;
    this._cloneOffsetY = 0;
    this._listRect = null;
    this._currentDropIndex = -1;
    this._keyboardDragging = false;
  }
  // — i18n ————————————————————————————————————————————————————————————————
  _t(key, vars) {
    let str = this._mergedTranslations[key];
    if (vars) {
      for (const [k, v] of Object.entries(vars)) {
        str = str.replace(`{${k}}`, String(v));
      }
    }
    return str;
  }
  // Sets or clears the aria-label on the active keyboard drag handle button directly
  _setDragHandleLabel(item, label) {
    const handle = item.querySelector("[draggable-only]")?.shadowRoot?.querySelector("button");
    if (!handle) return;
    if (label) {
      handle.setAttribute("aria-label", label);
    } else {
      handle.removeAttribute("aria-label");
    }
  }
  // — Accessibility ————————————————————————————————————————————————————————
  _dragPositionLabel() {
    const items = this._getItems();
    const pos = this._getDropIndex() + 1;
    return this._t("components.list.drag-handle-active-label-text", { position: pos, total: items.length });
  }
  _dragPositionAnnouncement() {
    const items = this._getItems();
    const pos = this._getDropIndex() + 1;
    return this._t("components.list.drag-position-text", { position: pos, total: items.length });
  }
  _announce(message, assertive = false) {
    const selector = assertive ? ".list__assertive-announcer" : ".list__polite-announcer";
    const region = this.shadowRoot?.querySelector(selector);
    if (!region) return;
    region.textContent = "";
    requestAnimationFrame(() => requestAnimationFrame(() => {
      region.textContent = message;
    }));
  }
  render() {
    return template$9(this._t("components.list.items-label-text"), this._hasHeader);
  }
};
NDDList.styles = [styles$9];
__decorateClass$g([
  property({ reflect: true })
], NDDList.prototype, "variant", 2);
__decorateClass$g([
  property({ type: Boolean, reflect: true })
], NDDList.prototype, "reorderable", 2);
__decorateClass$g([
  property({ type: Boolean, reflect: true, attribute: "no-dividers" })
], NDDList.prototype, "noDividers", 2);
__decorateClass$g([
  property({ type: Object })
], NDDList.prototype, "translations", 2);
__decorateClass$g([
  state()
], NDDList.prototype, "_mergedTranslations", 2);
__decorateClass$g([
  state()
], NDDList.prototype, "_hasHeader", 2);
NDDList = __decorateClass$g([
  customElement("ndd-list")
], NDDList);
const nddList = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  get NDDList() {
    return NDDList;
  }
}, Symbol.toStringTag, { value: "Module" }));
const styles$8 = css`
	/* # Host */

	:host {
		display: block;
		width: 100%;
		--_z-index-content: 1;
		--_z-index-indicator: calc(var(--_z-index-content) - 1);
		--_focus-outline-offset: 6px;
		-webkit-tap-highlight-color: transparent;
	}

	:host([hidden]) {
		display: none;
	}


	/* ## Dragging */

	:host(.is-dragging) {
		opacity: var(--components-list-item-is-dragging-opacity);
	}

	:host(.is-dragging-pointer) {
		display: none;
	}

	:host(:not([reorderable])) ::slotted([draggable-only]) {
		display: none;
	}

	:host([reorderable]) ::slotted([draggable-only]) {
		cursor: grab;
		touch-action: none;
	}

	:host(.is-dragging) ::slotted([draggable-only]) {
		cursor: grabbing;
	}


	/* # List item */

	.list-item {
		box-sizing: border-box;
		display: flex;
		min-height: var(--semantics-controls-md-min-size);
		flex-direction: row;
		align-items: stretch;
		position: relative;
		isolation: isolate;
		width: 100%;
	}

	:host([size='sm']) .list-item {
		min-height: var(--semantics-controls-sm-min-size);
	}


	/* # Action */

	.list-item__action {
		display: flex;
		flex-direction: row;
		align-items: stretch;
		width: 100%;
		background: none;
		border: none;
		padding: 0;
		margin: 0;
		text-align: start;
		text-decoration: none;
		color: inherit;
	}

	.list-item__action:focus-visible {
		outline: var(--semantics-focus-ring-outline);
		box-shadow: var(--semantics-focus-ring-box-shadow);
		border-radius: var(--primitives-corner-radius-xxs);
	}

	:host(.is-boxed) .list-item__action:focus-visible {
		outline: none;
		box-shadow: none;
	}

	:host(.is-boxed) .list-item__action:focus-visible:after {
		content: '';
		display: block;
		position: absolute;
		left: var(--_focus-outline-offset);
		top: var(--_focus-outline-offset);
		right: var(--_focus-outline-offset);
		bottom: var(--_focus-outline-offset);
		border-radius: calc(var(--components-list-corner-radius) - var(--_focus-outline-offset));
		outline: var(--semantics-focus-ring-outline);
		box-shadow: var(--semantics-focus-ring-box-shadow);
	}


	/* # Start & end area */

	.list-item__start-area,
	.list-item__end-area {
		display: none;
		flex-direction: row;
		align-items: center;
		flex-shrink: 0;
		position: relative;
		z-index: var(--_z-index-content);
		padding-block: var(--components-list-item-md-padding-block);
	}

	.list-item__start-area.is-visible,
	.list-item__end-area.is-visible {
		display: flex;
	}

	:host([size='sm']) .list-item__start-area,
	:host([size='sm']) .list-item__end-area {
		padding-block: var(--components-list-item-sm-padding-block);
	}


	/* # Main area */

	.list-item__main-area {
		display: flex;
		flex-direction: row;
		align-items: center;
		flex-grow: 1;
		min-width: 0;
		position: relative;
		z-index: var(--_z-index-content);
		padding-block: var(--components-list-item-md-padding-block);
	}

	:host([size='sm']) .list-item__main-area {
		padding-block: var(--components-list-item-sm-padding-block);
	}


	/* # Divider */

	.list-item__divider {
		display: var(--context-list-divider-display, block);
		position: absolute;
		inset-block-end: 0;
		inset-inline: 0;
		height: var(--semantics-dividers-thickness);
		background-color: var(--semantics-dividers-color);
	}

	:host([selected]) .list-item__divider,
	:host(.is-boxed.is-last) .list-item__divider {
		display: none;
	}


	/* # Indicator */

	.list-item::before {
		content: '';
		display: none;
		position: absolute;
		inset-block: 0;
		inset-inline: min(calc(var(--primitives-space-8) * -1), calc(var(--components-list-item-indicator-corner-radius) * -1));
		border-radius: var(--components-list-item-indicator-corner-radius);
		z-index: var(--_z-index-indicator);
	}

	:host([selected]) .list-item::before {
		display: block;
		background-color: var(--components-list-item-is-selected-background-color);
	}

	.list-item:has(.list-item__action:hover)::before {
		display: block;
		background-color: var(--components-list-item-is-hovered-background-color);
	}

	:host([selected]) .list-item:has(.list-item__action:hover)::before {
		background-color: var(--components-list-item-is-selected-background-color);
	}
`;
const areas = (showStart, showEnd) => html`
	<div class=${classMap({ "list-item__start-area": true, "is-visible": showStart })}>
		<slot name="start">
			<ndd-spacer-cell size="12"></ndd-spacer-cell>
		</slot>
	</div>
	<div class="list-item__main-area">
		<slot></slot>
		<div class="list-item__divider"></div>
	</div>
	<div class=${classMap({ "list-item__end-area": true, "is-visible": showEnd })}>
		<slot name="end">
			<ndd-spacer-cell size="12"></ndd-spacer-cell>
		</slot>
	</div>
`;
const template$8 = (type, href, showStart, showEnd) => {
  if (type === "link") {
    return html`<div class="list-item">
			<a class="list-item__action"
				href=${ifDefined(href)}
			>${areas(showStart, showEnd)}</a>
		</div>`;
  }
  if (type === "button") {
    return html`<div class="list-item">
			<button class="list-item__action"
				type="button"
			>${areas(showStart, showEnd)}</button>
		</div>`;
  }
  return html`<div class="list-item">${areas(showStart, showEnd)}</div>`;
};
var __defProp$f = Object.defineProperty;
var __getOwnPropDesc$f = Object.getOwnPropertyDescriptor;
var __decorateClass$f = (decorators, target, key, kind) => {
  var result = kind > 1 ? void 0 : kind ? __getOwnPropDesc$f(target, key) : target;
  for (var i = decorators.length - 1, decorator; i >= 0; i--)
    if (decorator = decorators[i])
      result = (kind ? decorator(target, key, result) : decorator(result)) || result;
  if (kind && result) __defProp$f(target, key, result);
  return result;
};
let NDDListItem = class extends LitElement {
  constructor() {
    super(...arguments);
    this.size = "md";
    this.selected = false;
    this.reorderable = false;
    this._showStart = false;
    this._showEnd = false;
    this._isBoxOrInset = false;
    this._listObserver = null;
  }
  connectedCallback() {
    super.connectedCallback();
    if (this.hasAttribute("data-ndd-clone")) return;
    this.setAttribute("role", "listitem");
  }
  disconnectedCallback() {
    super.disconnectedCallback();
    this._listObserver?.disconnect();
    this._listObserver = null;
  }
  firstUpdated() {
    if (this.hasAttribute("data-ndd-clone")) {
      this._observeStartSlot();
      this._observeEndSlot();
      return;
    }
    this._syncWithList();
    this._observeStartSlot();
    this._observeEndSlot();
  }
  updated(changed) {
    if (changed.has("selected")) {
      this._propagateSelected();
    }
  }
  /**
   * Syncs the item with the closest parent ndd-list variant.
   * Called once in firstUpdated. If the item is moved to a different ndd-list
   * after first render, the MutationObserver will still watch the original list.
   * This is acceptable as moving items between lists is not a supported use case.
   */
  _syncWithList() {
    const list2 = this.closest("ndd-list");
    if (!list2) {
      return;
    }
    this._applyVariant(list2.variant);
    this._listObserver = new MutationObserver(() => {
      this._applyVariant(list2.variant);
    });
    this._listObserver.observe(list2, {
      attributes: true,
      attributeFilter: ["variant"]
    });
  }
  _applyVariant(variant) {
    this._isBoxOrInset = variant === "box" || variant === "inset";
    this.classList.toggle("is-boxed", this._isBoxOrInset);
    this._updateVisibility();
  }
  _updateVisibility() {
    const startSlot = this.shadowRoot?.querySelector('slot[name="start"]');
    const endSlot = this.shadowRoot?.querySelector('slot[name="end"]');
    this._showStart = this._isBoxOrInset || (startSlot?.assignedElements().length ?? 0) > 0;
    this._showEnd = this._isBoxOrInset || (endSlot?.assignedElements().length ?? 0) > 0;
  }
  _observeStartSlot() {
    const slot = this.shadowRoot?.querySelector('slot[name="start"]');
    slot?.addEventListener("slotchange", () => this._updateVisibility());
  }
  _observeEndSlot() {
    const slot = this.shadowRoot?.querySelector('slot[name="end"]');
    slot?.addEventListener("slotchange", () => this._updateVisibility());
  }
  _propagateSelected() {
    const slots = this.shadowRoot?.querySelectorAll("slot");
    slots?.forEach((slot) => {
      slot.assignedElements({ flatten: true }).forEach((el) => {
        if (this.selected) {
          el.setAttribute("selected", "");
        } else {
          el.removeAttribute("selected");
        }
      });
    });
  }
  render() {
    return template$8(this.type, this.href, this._showStart, this._showEnd);
  }
};
NDDListItem.styles = [styles$8];
__decorateClass$f([
  property({ reflect: true })
], NDDListItem.prototype, "size", 2);
__decorateClass$f([
  property({ type: Boolean, reflect: true })
], NDDListItem.prototype, "selected", 2);
__decorateClass$f([
  property({ reflect: true })
], NDDListItem.prototype, "type", 2);
__decorateClass$f([
  property({ reflect: true })
], NDDListItem.prototype, "href", 2);
__decorateClass$f([
  property({ type: Boolean, reflect: true })
], NDDListItem.prototype, "reorderable", 2);
__decorateClass$f([
  state()
], NDDListItem.prototype, "_showStart", 2);
__decorateClass$f([
  state()
], NDDListItem.prototype, "_showEnd", 2);
NDDListItem = __decorateClass$f([
  customElement("ndd-list-item")
], NDDListItem);
const nddListItem = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  get NDDListItem() {
    return NDDListItem;
  }
}, Symbol.toStringTag, { value: "Module" }));
const styles$7 = css`
	/* # Host */

	:host {
		display: flex;
		flex-direction: column;
		align-items: stretch;
		flex-shrink: 0;
		justify-content: center;
		--_width: auto;
		--_min-width: 0;
		--_max-width: none;
		--_min-height: 0;
		width: var(--_width);
		min-width: var(--_min-width);
		max-width: var(--_max-width);
		min-height: var(--_min-height);
	}

	:host([hidden]) {
		display: none;
	}


	/* # Width */

	:host([width='stretch']) {
		flex-grow: 1;
		flex-shrink: 1;
		min-width: 0;
	}

	:host([width='fit-content']),
	:host(:not([width])) {
		flex-grow: 0;
		width: fit-content;
	}

	:host([width]:not([width='stretch']):not([width='fit-content'])) {
		flex-shrink: 0;
	}


	/* # Vertical alignment
	 *
	 * 'center' (default): the cell stretches to fill the full row height, then
	 * centers its content within that space. When min-height is set, the cell is
	 * at least that tall and the content sits centered inside it. For strict top
	 * alignment without a minimum height, use vertical-alignment="top".
	 */

	:host([vertical-alignment='center']),
	:host(:not([vertical-alignment])) {
		align-self: stretch;
	}

	:host([vertical-alignment='top']) {
		align-self: flex-start;
	}

	:host([vertical-alignment='bottom']) {
		align-self: flex-end;
	}


	/* # Slotted content */

	::slotted(*) {
		flex-shrink: 0;
	}
`;
const template$7 = () => html`<slot></slot>`;
var __defProp$e = Object.defineProperty;
var __getOwnPropDesc$e = Object.getOwnPropertyDescriptor;
var __decorateClass$e = (decorators, target, key, kind) => {
  var result = kind > 1 ? void 0 : kind ? __getOwnPropDesc$e(target, key) : target;
  for (var i = decorators.length - 1, decorator; i >= 0; i--)
    if (decorator = decorators[i])
      result = (kind ? decorator(target, key, result) : decorator(result)) || result;
  if (kind && result) __defProp$e(target, key, result);
  return result;
};
const widthConverter$2 = {
  fromAttribute(value) {
    if (value === null) return "fit-content";
    const num = Number(value);
    return Number.isFinite(num) ? num : value;
  },
  toAttribute(value) {
    return String(value);
  }
};
let NDDCell = class extends LitElement {
  constructor() {
    super(...arguments);
    this.width = "fit-content";
    this.verticalAlignment = "center";
  }
  updated(changed) {
    if (changed.has("width") || changed.has("minWidth") || changed.has("maxWidth") || changed.has("minHeight")) {
      this._applyDimensionStyles();
    }
  }
  /* eslint-disable eqeqeq -- != null is intentional: guards both null and undefined */
  _applyDimensionStyles() {
    if (typeof this.width === "number") {
      this.style.setProperty("--_width", `${this.width}px`);
    } else {
      this.style.removeProperty("--_width");
    }
    if (this.minWidth != null) {
      this.style.setProperty("--_min-width", `${this.minWidth}px`);
    } else {
      this.style.removeProperty("--_min-width");
    }
    if (this.maxWidth != null) {
      this.style.setProperty("--_max-width", `${this.maxWidth}px`);
    } else {
      this.style.removeProperty("--_max-width");
    }
    if (this.minHeight != null) {
      this.style.setProperty("--_min-height", `${this.minHeight}px`);
    } else {
      this.style.removeProperty("--_min-height");
    }
  }
  /* eslint-enable eqeqeq */
  render() {
    return template$7();
  }
};
NDDCell.styles = [styles$7];
__decorateClass$e([
  property({ reflect: true, converter: widthConverter$2 })
], NDDCell.prototype, "width", 2);
__decorateClass$e([
  property({ type: Number, reflect: true, attribute: "min-width" })
], NDDCell.prototype, "minWidth", 2);
__decorateClass$e([
  property({ type: Number, reflect: true, attribute: "max-width" })
], NDDCell.prototype, "maxWidth", 2);
__decorateClass$e([
  property({ type: Number, reflect: true, attribute: "min-height" })
], NDDCell.prototype, "minHeight", 2);
__decorateClass$e([
  property({ reflect: true, attribute: "vertical-alignment" })
], NDDCell.prototype, "verticalAlignment", 2);
NDDCell = __decorateClass$e([
  customElement("ndd-cell")
], NDDCell);
const styles$6 = css`
	/* # Host */

	:host {
		display: flex;
		flex-direction: column;
		justify-content: center;
		--_width: auto;
		--_min-width: 0;
		--_max-width: none;
		--_min-height: 0;
		width: var(--_width);
		min-width: var(--_min-width);
		max-width: var(--_max-width);
		min-height: var(--_min-height);
	}

	:host([hidden]) {
		display: none;
	}


	/* # Width */

	:host([width='stretch']),
	:host(:not([width])) {
		flex-grow: 1;
		min-width: 0;
	}

	:host([width='fit-content']) {
		flex-grow: 0;
		flex-shrink: 0;
		flex-basis: auto;
		width: fit-content;
	}

	:host([width]:not([width='stretch']):not([width='fit-content'])) {
		flex-shrink: 0;
	}


	/* # Vertical alignment
	 *
	 * 'center' (default): the cell stretches to fill the full row height, then
	 * centers its content within that space. When min-height is set, the cell is
	 * at least that tall and the content sits centered inside it. For strict top
	 * alignment without a minimum height, use vertical-alignment="top".
	 */

	:host([vertical-alignment='center']),
	:host(:not([vertical-alignment])) {
		align-self: stretch;
	}

	:host([vertical-alignment='top']) {
		align-self: flex-start;
	}

	:host([vertical-alignment='bottom']) {
		align-self: flex-end;
	}


	/* # Horizontal alignment */

	:host([horizontal-alignment='left']),
	:host(:not([horizontal-alignment])) {
		align-items: flex-start;
	}

	:host([horizontal-alignment='right']) {
		align-items: flex-end;
	}


	/* # Overline */

	.title-cell__overline {
		margin: 0;
		align-self: stretch;
		min-width: 0;
		font: var(--primitives-font-body-xs-regular-tight);
		color: var(--semantics-content-secondary-color);
	}

	:host([horizontal-alignment='right']) .title-cell__overline {
		text-align: right;
	}


	/* # Title */

	.title-cell__title {
		margin: 0;
		align-self: stretch;
		min-width: 0;
		color: var(--semantics-content-color);
	}

	:host([horizontal-alignment='right']) .title-cell__title {
		text-align: right;
	}

	/* ## Size 1 */

	:host([size='1']) .title-cell__title {
		font: var(--primitives-font-display-1-sm);
	}

	/* ## Size 2 */

	:host([size='2']) .title-cell__title {
		font: var(--primitives-font-display-2-sm);
	}

	/* ## Size 3 */

	:host([size='3']) .title-cell__title {
		font: var(--primitives-font-display-3-sm);
	}

	/* ## Size 4 */

	:host([size='4']) .title-cell__title {
		font: var(--primitives-font-display-4-sm);
	}

	/* ## Size 5 */

	:host([size='5']) .title-cell__title,
	:host(:not([size])) .title-cell__title {
		font: var(--primitives-font-display-5-sm);
	}

	/* ## Size 6 */

	:host([size='6']) .title-cell__title {
		font: var(--primitives-font-display-6-sm);
	}


	/* # Subtitle */

	.title-cell__supporting-text {
		margin: 0;
		align-self: stretch;
		min-width: 0;
		font: var(--primitives-font-body-sm-regular-tight);
		color: var(--semantics-content-secondary-color);
	}

	:host([horizontal-alignment='right']) .title-cell__supporting-text {
		text-align: right;
	}


	/* # Color: inherit */

	:host([color='inherit']) .title-cell__title,
	:host([color='inherit']) .title-cell__overline,
	:host([color='inherit']) .title-cell__supporting-text {
		color: inherit;
	}


	/* # Selected */

	:host([selected]) .title-cell__title,
	:host([selected]) .title-cell__overline,
	:host([selected]) .title-cell__supporting-text {
		color: var(--semantics-controls-is-selected-contrast-color);
	}


	/* # Forced colors */

	@media (forced-colors: active) {
		.title-cell__title {
			forced-color-adjust: none;
		}
	}
`;
const HEADING_TAGS = {
  1: unsafeStatic("h1"),
  2: unsafeStatic("h2"),
  3: unsafeStatic("h3"),
  4: unsafeStatic("h4"),
  5: unsafeStatic("h5"),
  6: unsafeStatic("h6")
};
function renderTitle(component) {
  if (!component.text) return nothing;
  const tag = HEADING_TAGS[component.headingLevel];
  if (tag) {
    return html$1`<${tag} class="title-cell__title">${component.text}</${tag}>`;
  }
  return html`<p class="title-cell__title">${component.text}</p>`;
}
const template$6 = function() {
  return html`
		${this.overline ? html`<p class="title-cell__overline">${this.overline}</p>` : nothing}
		${renderTitle(this)}
		${this.supportingText ? html`<p class="title-cell__supporting-text">${this.supportingText}</p>` : nothing}
	`;
};
var __defProp$d = Object.defineProperty;
var __getOwnPropDesc$d = Object.getOwnPropertyDescriptor;
var __decorateClass$d = (decorators, target, key, kind) => {
  var result = kind > 1 ? void 0 : kind ? __getOwnPropDesc$d(target, key) : target;
  for (var i = decorators.length - 1, decorator; i >= 0; i--)
    if (decorator = decorators[i])
      result = (kind ? decorator(target, key, result) : decorator(result)) || result;
  if (kind && result) __defProp$d(target, key, result);
  return result;
};
const widthConverter$1 = {
  fromAttribute(value) {
    if (value === null) return "stretch";
    const num = Number(value);
    return Number.isFinite(num) ? num : value;
  },
  toAttribute(value) {
    return String(value);
  }
};
let NDDTitleCell = class extends LitElement {
  constructor() {
    super(...arguments);
    this.size = 5;
    this.color = "default";
    this.width = "stretch";
    this.horizontalAlignment = "left";
    this.verticalAlignment = "center";
    this.selected = false;
    this.text = "";
    this.overline = "";
    this.supportingText = "";
    this.headingLevel = void 0;
  }
  updated(changed) {
    if (changed.has("width") || changed.has("minWidth") || changed.has("maxWidth") || changed.has("minHeight")) {
      this._applyDimensionStyles();
    }
  }
  /* eslint-disable eqeqeq -- != null is intentional: guards both null and undefined */
  _applyDimensionStyles() {
    if (typeof this.width === "number") {
      this.style.setProperty("--_width", `${this.width}px`);
    } else {
      this.style.removeProperty("--_width");
    }
    if (this.minWidth != null) {
      this.style.setProperty("--_min-width", `${this.minWidth}px`);
    } else {
      this.style.removeProperty("--_min-width");
    }
    if (this.maxWidth != null) {
      this.style.setProperty("--_max-width", `${this.maxWidth}px`);
    } else {
      this.style.removeProperty("--_max-width");
    }
    if (this.minHeight != null) {
      this.style.setProperty("--_min-height", `${this.minHeight}px`);
    } else {
      this.style.removeProperty("--_min-height");
    }
  }
  /* eslint-enable eqeqeq */
  render() {
    return template$6.call(this);
  }
};
NDDTitleCell.styles = [styles$6];
__decorateClass$d([
  property({ type: Number, reflect: true })
], NDDTitleCell.prototype, "size", 2);
__decorateClass$d([
  property({ type: String, reflect: true })
], NDDTitleCell.prototype, "color", 2);
__decorateClass$d([
  property({ reflect: true, converter: widthConverter$1 })
], NDDTitleCell.prototype, "width", 2);
__decorateClass$d([
  property({ type: Number, reflect: true, attribute: "min-width" })
], NDDTitleCell.prototype, "minWidth", 2);
__decorateClass$d([
  property({ type: Number, reflect: true, attribute: "max-width" })
], NDDTitleCell.prototype, "maxWidth", 2);
__decorateClass$d([
  property({ type: Number, reflect: true, attribute: "min-height" })
], NDDTitleCell.prototype, "minHeight", 2);
__decorateClass$d([
  property({ type: String, reflect: true, attribute: "horizontal-alignment" })
], NDDTitleCell.prototype, "horizontalAlignment", 2);
__decorateClass$d([
  property({ type: String, reflect: true, attribute: "vertical-alignment" })
], NDDTitleCell.prototype, "verticalAlignment", 2);
__decorateClass$d([
  property({ type: Boolean, reflect: true })
], NDDTitleCell.prototype, "selected", 2);
__decorateClass$d([
  property({ type: String })
], NDDTitleCell.prototype, "text", 2);
__decorateClass$d([
  property({ type: String })
], NDDTitleCell.prototype, "overline", 2);
__decorateClass$d([
  property({ type: String, attribute: "supporting-text" })
], NDDTitleCell.prototype, "supportingText", 2);
__decorateClass$d([
  property({ type: Number, attribute: "heading-level" })
], NDDTitleCell.prototype, "headingLevel", 2);
NDDTitleCell = __decorateClass$d([
  customElement("ndd-title-cell")
], NDDTitleCell);
const styles$5 = css`
	/* # Host */

	:host {
		display: flex;
		flex-direction: column;
		justify-content: center;
		--_width: auto;
		--_min-width: 0;
		--_max-width: none;
		--_min-height: 0;
		width: var(--_width);
		min-width: var(--_min-width);
		max-width: var(--_max-width);
		min-height: var(--_min-height);
	}

	:host([hidden]) {
		display: none;
	}


	/* # Width */

	:host([width='stretch']),
	:host(:not([width])) {
		flex-grow: 1;
		min-width: 0;
	}

	:host([width='fit-content']) {
		flex-grow: 0;
		flex-shrink: 0;
		flex-basis: auto;
		width: fit-content;
	}

	:host([width]:not([width='stretch']):not([width='fit-content'])) {
		flex-shrink: 0;
	}


	/* # Vertical alignment
	 *
	 * 'center' (default): the cell stretches to fill the full row height, then
	 * centers its content within that space. When min-height is set, the cell is
	 * at least that tall and the content sits centered inside it. For strict top
	 * alignment without a minimum height, use vertical-alignment="top".
	 */

	:host([vertical-alignment='center']),
	:host(:not([vertical-alignment])) {
		align-self: stretch;
	}

	:host([vertical-alignment='top']) {
		align-self: flex-start;
	}

	:host([vertical-alignment='bottom']) {
		align-self: flex-end;
	}


	/* # Title */

	::slotted([slot='title']) {
		margin: 0;
		align-self: stretch;
		min-width: 0;
		font: var(--primitives-font-body-sm-regular-flat);
		color: var(--semantics-content-secondary-color);
	}


	/* # Description */

	::slotted([slot='description']) {
		margin: 0;
		align-self: stretch;
		min-width: 0;
		font: var(--primitives-font-body-md-regular-tight);
		color: var(--semantics-content-color);
	}


	/* # Selected */

	:host([selected]) ::slotted([slot='title']),
	:host([selected]) ::slotted([slot='description']) {
		color: var(--semantics-controls-is-selected-contrast-color);
	}


	/* # Forced colors */

	@media (forced-colors: active) {
		::slotted([slot='title']),
		::slotted([slot='description']) {
			forced-color-adjust: none;
		}
	}
`;
const template$5 = () => html`
	<slot name="title"></slot>
	<slot name="description"></slot>
`;
var __defProp$c = Object.defineProperty;
var __getOwnPropDesc$c = Object.getOwnPropertyDescriptor;
var __decorateClass$c = (decorators, target, key, kind) => {
  var result = kind > 1 ? void 0 : kind ? __getOwnPropDesc$c(target, key) : target;
  for (var i = decorators.length - 1, decorator; i >= 0; i--)
    if (decorator = decorators[i])
      result = (kind ? decorator(target, key, result) : decorator(result)) || result;
  if (kind && result) __defProp$c(target, key, result);
  return result;
};
const widthConverter = {
  fromAttribute(value) {
    if (value === null) return "stretch";
    const num = Number(value);
    return Number.isFinite(num) ? num : value;
  },
  toAttribute(value) {
    return String(value);
  }
};
let NDDDescriptionCell = class extends LitElement {
  constructor() {
    super(...arguments);
    this.width = "stretch";
    this.verticalAlignment = "center";
    this.selected = false;
  }
  updated(changed) {
    if (changed.has("width") || changed.has("minWidth") || changed.has("maxWidth") || changed.has("minHeight")) {
      this._applyDimensionStyles();
    }
  }
  /* eslint-disable eqeqeq -- != null is intentional: guards both null and undefined */
  _applyDimensionStyles() {
    if (typeof this.width === "number") {
      this.style.setProperty("--_width", `${this.width}px`);
    } else {
      this.style.removeProperty("--_width");
    }
    if (this.minWidth != null) {
      this.style.setProperty("--_min-width", `${this.minWidth}px`);
    } else {
      this.style.removeProperty("--_min-width");
    }
    if (this.maxWidth != null) {
      this.style.setProperty("--_max-width", `${this.maxWidth}px`);
    } else {
      this.style.removeProperty("--_max-width");
    }
    if (this.minHeight != null) {
      this.style.setProperty("--_min-height", `${this.minHeight}px`);
    } else {
      this.style.removeProperty("--_min-height");
    }
  }
  /* eslint-enable eqeqeq */
  render() {
    return template$5();
  }
};
NDDDescriptionCell.styles = [styles$5];
__decorateClass$c([
  property({ reflect: true, converter: widthConverter })
], NDDDescriptionCell.prototype, "width", 2);
__decorateClass$c([
  property({ type: Number, reflect: true, attribute: "min-width" })
], NDDDescriptionCell.prototype, "minWidth", 2);
__decorateClass$c([
  property({ type: Number, reflect: true, attribute: "max-width" })
], NDDDescriptionCell.prototype, "maxWidth", 2);
__decorateClass$c([
  property({ type: Number, reflect: true, attribute: "min-height" })
], NDDDescriptionCell.prototype, "minHeight", 2);
__decorateClass$c([
  property({ reflect: true, attribute: "vertical-alignment" })
], NDDDescriptionCell.prototype, "verticalAlignment", 2);
__decorateClass$c([
  property({ type: Boolean, reflect: true })
], NDDDescriptionCell.prototype, "selected", 2);
NDDDescriptionCell = __decorateClass$c([
  customElement("ndd-description-cell")
], NDDDescriptionCell);
const styles$4 = css`
	/* # Host */

	:host {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: fit-content;
		cursor: grab;
	}

	:host([hidden]) {
		display: none;
	}

	:host(:active) {
		cursor: grabbing;
	}


	/* # Control */

	.drag-handle-cell__control {
		display: flex;
		align-items: center;
		justify-content: center;
		background-color: var(--semantics-grab-handles-background-color);
		border: none;
		padding: 0;
		margin: 0;
		cursor: inherit;
		-webkit-appearance: none;
		appearance: none;
	}

	.drag-handle-cell__control:focus-visible {
		outline: var(--semantics-focus-ring-outline);
		box-shadow: var(--semantics-focus-ring-box-shadow);
	}


	/* ## Size: MD (default) */

	:host([size="md"]) .drag-handle-cell__control,
	:host(:not([size])) .drag-handle-cell__control {
		width: var(--semantics-controls-sm-min-size);
		height: var(--semantics-controls-md-min-size);
		border-radius: var(--semantics-controls-md-corner-radius);
	}


	/* ## Size: SM */

	:host([size="sm"]) .drag-handle-cell__control {
		width: var(--semantics-controls-xs-min-size);
		height: var(--semantics-controls-sm-min-size);
		border-radius: var(--semantics-controls-sm-corner-radius);
	}


	/* # Grip */

	.drag-handle-cell__control-grip {
		display: block;
		color: var(--semantics-grab-handles-grip-color);
	}
`;
const gripMd = svg`
	<svg aria-hidden="true" class="drag-handle-cell__control-grip"
		width="10"
		height="22"
		viewBox="0 0 10 22"
		xmlns="http://www.w3.org/2000/svg"
	>
		<circle cx="2" cy="2"  r="2" fill="currentColor"/>
		<circle cx="8" cy="2"  r="2" fill="currentColor"/>
		<circle cx="2" cy="8"  r="2" fill="currentColor"/>
		<circle cx="8" cy="8"  r="2" fill="currentColor"/>
		<circle cx="2" cy="14" r="2" fill="currentColor"/>
		<circle cx="8" cy="14" r="2" fill="currentColor"/>
		<circle cx="2" cy="20" r="2" fill="currentColor"/>
		<circle cx="8" cy="20" r="2" fill="currentColor"/>
	</svg>
`;
const gripSm = svg`
	<svg aria-hidden="true" class="drag-handle-cell__control-grip"
		width="10"
		height="16"
		viewBox="0 0 10 16"
		xmlns="http://www.w3.org/2000/svg"
	>
		<circle cx="2" cy="2"  r="2" fill="currentColor"/>
		<circle cx="8" cy="2"  r="2" fill="currentColor"/>
		<circle cx="2" cy="8"  r="2" fill="currentColor"/>
		<circle cx="8" cy="8"  r="2" fill="currentColor"/>
		<circle cx="2" cy="14" r="2" fill="currentColor"/>
		<circle cx="8" cy="14" r="2" fill="currentColor"/>
	</svg>
`;
function template$4(size2, label) {
  return html`
		<button class="drag-handle-cell__control"
			type="button"
			aria-label=${label}
		>
			${size2 === "sm" ? gripSm : gripMd}
		</button>
	`;
}
const nddDragHandleCellTranslations = {
  "components.drag-handle-cell.label-text": "Sleepgreep, druk spatie of enter om te verplaatsen"
};
var __defProp$b = Object.defineProperty;
var __getOwnPropDesc$b = Object.getOwnPropertyDescriptor;
var __decorateClass$b = (decorators, target, key, kind) => {
  var result = kind > 1 ? void 0 : kind ? __getOwnPropDesc$b(target, key) : target;
  for (var i = decorators.length - 1, decorator; i >= 0; i--)
    if (decorator = decorators[i])
      result = (kind ? decorator(target, key, result) : decorator(result)) || result;
  if (kind && result) __defProp$b(target, key, result);
  return result;
};
let NDDDragHandleCell = class extends LitElement {
  constructor() {
    super(...arguments);
    this.size = "md";
    this.translations = {};
  }
  // — i18n ————————————————————————————————————————————————————————————————
  _t(key) {
    return this.translations[key] ?? nddDragHandleCellTranslations[key];
  }
  render() {
    const label = this._t("components.drag-handle-cell.label-text");
    return template$4(this.size, label);
  }
};
NDDDragHandleCell.styles = styles$4;
__decorateClass$b([
  property({ type: String, reflect: true })
], NDDDragHandleCell.prototype, "size", 2);
__decorateClass$b([
  property({ type: Object })
], NDDDragHandleCell.prototype, "translations", 2);
NDDDragHandleCell = __decorateClass$b([
  customElement("ndd-drag-handle-cell")
], NDDDragHandleCell);
var __defProp$a = Object.defineProperty;
var __getOwnPropDesc$a = Object.getOwnPropertyDescriptor;
var __decorateClass$a = (decorators, target, key, kind) => {
  var result = kind > 1 ? void 0 : kind ? __getOwnPropDesc$a(target, key) : target;
  for (var i = decorators.length - 1, decorator; i >= 0; i--)
    if (decorator = decorators[i])
      result = (kind ? decorator(target, key, result) : decorator(result)) || result;
  if (kind && result) __defProp$a(target, key, result);
  return result;
};
let NDDTimelineTrackCell = class extends LitElement {
  constructor() {
    super(...arguments);
    this.step = "past";
    this.child = "between";
  }
  render() {
    if (this.step === "none") {
      return html`
				<div class="timeline-track" part="track">
					<div class="timeline-track__line-full"></div>
				</div>
			`;
    }
    const showTopLine = this.child === "between" || this.child === "last";
    const showBottomLine = this.child === "between" || this.child === "first";
    return html`
			<div class="timeline-track" part="track">
				${showTopLine ? html`<div class="timeline-track__line-top"></div>` : ""}
				<div class="timeline-track__dot"></div>
				${showBottomLine ? html`<div class="timeline-track__line-bottom"></div>` : ""}
			</div>
		`;
  }
};
NDDTimelineTrackCell.styles = css`
		:host {
			display: flex;
			flex-direction: column;
			align-items: center;
			width: 18px;
		}

		:host([hidden]) {
			display: none;
		}

		.timeline-track {
			position: relative;
			width: 18px;
			height: 100%;
			min-height: 50px;
		}

		/* Vertical lines */
		.timeline-track__line-top,
		.timeline-track__line-bottom {
			position: absolute;
			left: 50%;
			width: 2px;
			margin-left: -1px;
			background-color: var(--semantics-buttons-accent-filled-background-color);
		}

		.timeline-track__line-top {
			bottom: 50%;
			height: 59px;
		}

		.timeline-track__line-bottom {
			top: 50%;
			height: 59px;
		}

		/* Dot indicator */
		.timeline-track__dot {
			position: absolute;
			top: 50%;
			left: 0;
			width: 18px;
			height: 18px;
			margin-top: -9px;
			border-radius: 50%;
			box-sizing: border-box;
			border: 2px solid var(--semantics-buttons-accent-filled-background-color);
		}

		/* Step: past (filled dot) */
		:host([step="past"]) .timeline-track__dot,
		:host(:not([step])) .timeline-track__dot {
			background-color: var(--semantics-buttons-accent-filled-background-color);
		}

		/* Step: future (hollow dot with white fill) */
		:host([step="future"]) .timeline-track__dot {
			background-color: var(--semantics-surfaces-background-color);
		}

		/* Step: none - continuous line, no dot */
		.timeline-track__line-full {
			position: absolute;
			left: 50%;
			width: 2px;
			margin-left: -1px;
			top: -34px;
			bottom: -34px;
			background-color: var(--semantics-buttons-accent-filled-background-color);
		}

		/* Accessibility: High Contrast Mode */
		@media (forced-colors: active) {
			.timeline-track__dot,
			.timeline-track__line-top,
			.timeline-track__line-bottom,
			.timeline-track__line-full {
				forced-color-adjust: none;
			}
		}
	`;
__decorateClass$a([
  property({ type: String, reflect: true })
], NDDTimelineTrackCell.prototype, "step", 2);
__decorateClass$a([
  property({ type: String, reflect: true })
], NDDTimelineTrackCell.prototype, "child", 2);
NDDTimelineTrackCell = __decorateClass$a([
  customElement("ndd-timeline-track-cell")
], NDDTimelineTrackCell);
const styles$3 = css`


	/* # Host */

	:host {
		display: flex;
		flex-grow: 1;
		flex-shrink: 1;
		min-width: 0;
	}

	:host([hidden]),
	:host([empty]) {
		display: none;
	}


	/* # Block */

	.menu-bar {
		display: flex;
		flex-direction: row;
		align-items: center;
		flex-grow: 1;
		flex-shrink: 1;
		min-width: 0;
	}

	/* ## Overflow button */

	.menu-bar__overflow-button {
		display: none;
	}
`;
function template$3(component) {
  return html`
		<nav class="menu-bar"
			aria-label=${component.accessibleLabel || nothing}
		>
			<slot></slot>
			<div class="menu-bar__overflow-button">
				<ndd-menu-bar-item
					text="${component._overflowText}"
					icon="ellipsis"
					icon-only
					haspopup="menu"
					@click=${component._onOverflowClick}
				></ndd-menu-bar-item>
			</div>
		</nav>
	`;
}
const nddMenuBarTranslations = {
  "components.menu-bar.overflow-action": "Meer opties"
};
const styles$2 = css`


	/* # Host */

	:host {
		--_indicator-z-index: 0;
		--_content-z-index: 1;
		--_focus-z-index: 1;
		display: inline-block;
		position: relative;
		flex-grow: 0;
		flex-shrink: 0;
		flex-basis: auto;
		-webkit-tap-highlight-color: transparent;
	}

	:host([hidden]) {
		display: none;
	}


	/* # Item */

	.menu-bar-item {
		appearance: none;
		border: none;
		margin: 0;
		background: none;
		text-decoration: none;
		display: flex;
		position: relative;
		height: var(--semantics-controls-md-min-size);
		min-width: var(--semantics-controls-md-min-size);
		box-sizing: border-box;
		justify-content: center;
		align-items: center;
		gap: var(--primitives-space-4);
		font: var(--components-menu-bar-item-font);
		color: var(--components-menu-bar-item-content-color);
		text-align: center;
		padding: 0 var(--primitives-space-8);
		white-space: nowrap;
	}

	/* ## Hover indicator (::before) */

	.menu-bar-item::before {
		content: '';
		position: absolute;
		top: var(--primitives-space-6);
		bottom: var(--primitives-space-6);
		left: 0;
		right: 0;
		border-radius: var(--semantics-controls-sm-corner-radius);
		pointer-events: none;
		z-index: var(--_indicator-z-index);
	}

	.menu-bar-item:hover::before {
		background-color: var(--components-menu-bar-item-is-hovered-indicator-background-color);
	}

	:host([open]) .menu-bar-item::before {
		background-color: var(--components-menu-bar-item-is-open-indicator-background-color);
	}

	:host([open]) .menu-bar-item:hover::before {
		background-color: var(--components-menu-bar-item-is-hovered-indicator-background-color);
	}

	/* ## Current indicator (::after) */

	:host([current]) .menu-bar-item::after {
		content: '';
		position: absolute;
		bottom: 0;
		left: var(--primitives-space-8);
		right: var(--primitives-space-8);
		height: var(--components-menu-bar-item-is-current-indicator-height);
		background-color: var(--components-menu-bar-item-is-current-indicator-background-color);
		pointer-events: none;
		z-index: var(--_indicator-z-index);
	}

	/* ## Text */

	.menu-bar-item__text {
		position: relative;
		z-index: var(--_content-z-index);
	}

	/* ## Icon */

	.menu-bar-item__icon {
		width: var(--primitives-space-20);
		height: var(--primitives-space-20);
		flex-shrink: 0;
		z-index: var(--_content-z-index);
	}

	/* ## Disclosure icon */

	.menu-bar-item__disclosure-icon {
		width: var(--primitives-space-16);
		height: var(--primitives-space-16);
		z-index: var(--_content-z-index);
	}


	/* # Focus */

	:host(:focus-within) {
		z-index: var(--_focus-z-index);
	}

	.menu-bar-item:focus-visible {
		outline: none;
	}

	.menu-bar-item:focus-visible::before {
		box-shadow: var(--semantics-focus-ring-box-shadow);
		outline: var(--semantics-focus-ring-outline);
	}


	/* # Slotted */

	::slotted(ndd-menu-item),
	::slotted(ndd-menu-divider) {
		display: none;
	}


	/* # Disabled */

	:host([disabled]) .menu-bar-item {
		opacity: var(--primitives-opacity-disabled);
		pointer-events: none;
	}


	/* # Icon-only */

	:host([icon-only]) .menu-bar-item,
	:host([content-priority="icon"][compact][icon]:not([icon=""])) .menu-bar-item {
		padding: var(--primitives-space-8);
	}

	:host([icon-only]) .menu-bar-item__text,
	:host([content-priority="icon"][compact][icon]:not([icon=""])) .menu-bar-item__text {
		position: absolute;
		width: 1px;
		height: 1px;
		padding: 0;
		margin: -1px;
		overflow: hidden;
		clip-path: inset(50%);
		white-space: nowrap;
		border: 0;
	}

	/* ## Text-only when compact */

	:host([content-priority="text"][compact]) .menu-bar-item__icon {
		display: none;
	}
`;
function sanitizeUrl(url) {
  if (!url) return null;
  const trimmed = url.replace(/^[\s\u00A0\u200B\u2028\u2029]+|[\s\u00A0\u200B\u2028\u2029]+$/g, "").replace(/[\0\t\n\r]/g, "");
  const lower = trimmed.toLowerCase();
  if (lower.startsWith("javascript:") || lower.startsWith("data:") || lower.startsWith("vbscript:") || lower.startsWith("blob:")) {
    return null;
  }
  return trimmed;
}
function template$2(component) {
  const safeHref = sanitizeUrl(component.href);
  const isLink = Boolean(safeHref);
  const isIconOnly = Boolean((component.iconOnly || component.contentPriority === "icon" && component.compact) && component.text);
  const ariaLabel = component.accessibleLabel || (isIconOnly ? component.text : nothing);
  const ariaCurrent = component.current ? component.currentType : nothing;
  const ariaHaspopup = component.expandable ? "menu" : component.haspopup || nothing;
  const ariaExpanded = component.expandable || component.haspopup ? String(component.open) : nothing;
  if (isLink) {
    return html`
			<a class="menu-bar-item"
				href=${safeHref}
				aria-disabled=${component.disabled || nothing}
				tabindex=${component.disabled ? "-1" : nothing}
				aria-current=${ariaCurrent}
				aria-label=${ariaLabel}
				aria-haspopup=${ariaHaspopup}
				aria-expanded=${ariaExpanded}
			>
				${component.icon ? html`
					<span class="menu-bar-item__icon">
						<ndd-icon name=${component.icon}></ndd-icon>
					</span>
				` : nothing}
				<span class="menu-bar-item__text">
					${component.text}
				</span>
				${component.expandable ? html`
					<span class="menu-bar-item__disclosure-icon">
						<ndd-icon name="chevron-down-small"></ndd-icon>
					</span>
				` : nothing}
			</a>
			<slot></slot>
		`;
  }
  return html`
		<button class="menu-bar-item"
			type="button"
			?disabled=${component.disabled}
			aria-current=${ariaCurrent}
			aria-label=${ariaLabel}
			aria-haspopup=${ariaHaspopup}
			aria-expanded=${ariaExpanded}
		>
			${component.icon ? html`
				<span class="menu-bar-item__icon">
					<ndd-icon name=${component.icon}></ndd-icon>
				</span>
			` : nothing}
			<span class="menu-bar-item__text">
				${component.text}
			</span>
			${component.expandable ? html`
				<span class="menu-bar-item__disclosure-icon">
					<ndd-icon name="chevron-down-small"></ndd-icon>
				</span>
			` : nothing}
		</button>
		<slot></slot>
	`;
}
var __defProp$9 = Object.defineProperty;
var __getOwnPropDesc$9 = Object.getOwnPropertyDescriptor;
var __decorateClass$9 = (decorators, target, key, kind) => {
  var result = kind > 1 ? void 0 : kind ? __getOwnPropDesc$9(target, key) : target;
  for (var i = decorators.length - 1, decorator; i >= 0; i--)
    if (decorator = decorators[i])
      result = (kind ? decorator(target, key, result) : decorator(result)) || result;
  if (kind && result) __defProp$9(target, key, result);
  return result;
};
let NDDMenuBarItem = class extends LitElement {
  constructor() {
    super(...arguments);
    this.text = "";
    this.current = false;
    this.currentType = "page";
    this.href = "";
    this.icon = "";
    this.expandable = false;
    this.iconOnly = false;
    this.contentPriority = "";
    this.compact = false;
    this.disabled = false;
    this.accessibleLabel = "";
    this.haspopup = "";
    this.open = false;
    this._menu = null;
    this._menuOpen = false;
    this._menuClosedAt = 0;
    this._handleClick = (event) => {
      if (this.disabled) {
        event.preventDefault();
        event.stopPropagation();
        return;
      }
      if (this.expandable && this._hasMenuItems()) {
        event.preventDefault();
        this._toggleMenu();
        return;
      }
      if (!this.href) {
        event.preventDefault();
        this.dispatchEvent(new CustomEvent("select", {
          bubbles: true,
          composed: true,
          detail: { item: this }
        }));
      }
    };
  }
  // ## Lifecycle
  connectedCallback() {
    super.connectedCallback();
    this.addEventListener("click", this._handleClick);
  }
  disconnectedCallback() {
    super.disconnectedCallback();
    this.removeEventListener("click", this._handleClick);
    this._menu?.remove();
    this._menu = null;
  }
  updated(changed) {
    if (changed.has("expandable") && !this.expandable && this._menu) {
      this._menu.remove();
      this._menu = null;
    }
  }
  focus(options) {
    const focusable = this.shadowRoot?.querySelector("button, a");
    focusable?.focus(options);
  }
  // ## Helpers
  _hasMenuItems() {
    return this.querySelector("ndd-menu-item, ndd-menu-divider") !== null;
  }
  // ## Menu popover
  _createMenu() {
    if (this._menu || !this._hasMenuItems()) return;
    if (typeof document === "undefined") return;
    const menu = document.createElement("ndd-menu");
    menu.setAttribute("placement", "bottom-start");
    menu.addEventListener("toggle", (event) => {
      const open = event.newState === "open";
      this._menuOpen = open;
      this.open = open;
      if (!open) this._menuClosedAt = Date.now();
    });
    document.body.appendChild(menu);
    this._menu = menu;
  }
  /**
   * Clone slotted menu items into the popover menu.
   * Note: cloneNode(true) copies DOM structure and attributes but not JS event
   * listeners. Custom click handlers on slotted ndd-menu-item elements won't
   * fire in the popover. Use event delegation on a parent element instead.
   */
  _syncMenuItems() {
    if (!this._menu) return;
    this._menu.replaceChildren();
    const items = this.querySelectorAll("ndd-menu-item, ndd-menu-divider");
    items.forEach((item) => {
      const clone = item.cloneNode(true);
      this._menu.appendChild(clone);
    });
  }
  _toggleMenu() {
    if (!this._menu) this._createMenu();
    if (!this._menu) return;
    this._menu.anchorElement = this;
    if (this._menuOpen) {
      this._menu.hidePopover();
    } else if (Date.now() - this._menuClosedAt > POPOVER_REOPEN_GUARD_MS) {
      this._syncMenuItems();
      this._menu.showPopover();
    }
  }
  render() {
    return template$2(this);
  }
};
NDDMenuBarItem.styles = styles$2;
__decorateClass$9([
  property({ type: String, reflect: true })
], NDDMenuBarItem.prototype, "text", 2);
__decorateClass$9([
  property({ type: Boolean, reflect: true })
], NDDMenuBarItem.prototype, "current", 2);
__decorateClass$9([
  property({ type: String, attribute: "current-type", reflect: true })
], NDDMenuBarItem.prototype, "currentType", 2);
__decorateClass$9([
  property({ type: String })
], NDDMenuBarItem.prototype, "href", 2);
__decorateClass$9([
  property({ type: String, reflect: true })
], NDDMenuBarItem.prototype, "icon", 2);
__decorateClass$9([
  property({ type: Boolean, reflect: true })
], NDDMenuBarItem.prototype, "expandable", 2);
__decorateClass$9([
  property({ type: Boolean, attribute: "icon-only", reflect: true })
], NDDMenuBarItem.prototype, "iconOnly", 2);
__decorateClass$9([
  property({ type: String, attribute: "content-priority", reflect: true })
], NDDMenuBarItem.prototype, "contentPriority", 2);
__decorateClass$9([
  property({ type: Boolean, reflect: true })
], NDDMenuBarItem.prototype, "compact", 2);
__decorateClass$9([
  property({ type: Boolean, reflect: true })
], NDDMenuBarItem.prototype, "disabled", 2);
__decorateClass$9([
  property({ type: String, attribute: "accessible-label" })
], NDDMenuBarItem.prototype, "accessibleLabel", 2);
__decorateClass$9([
  property({ type: String })
], NDDMenuBarItem.prototype, "haspopup", 2);
__decorateClass$9([
  property({ type: Boolean, reflect: true })
], NDDMenuBarItem.prototype, "open", 2);
NDDMenuBarItem = __decorateClass$9([
  customElement("ndd-menu-bar-item")
], NDDMenuBarItem);
var __defProp$8 = Object.defineProperty;
var __getOwnPropDesc$8 = Object.getOwnPropertyDescriptor;
var __decorateClass$8 = (decorators, target, key, kind) => {
  var result = kind > 1 ? void 0 : kind ? __getOwnPropDesc$8(target, key) : target;
  for (var i = decorators.length - 1, decorator; i >= 0; i--)
    if (decorator = decorators[i])
      result = (kind ? decorator(target, key, result) : decorator(result)) || result;
  if (kind && result) __defProp$8(target, key, result);
  return result;
};
let NDDMenuBar = class extends LitElement {
  constructor() {
    super(...arguments);
    this.overflowText = "";
    this.accessibleLabel = "";
    this.compact = false;
    this.translations = {};
    this._overflowMenu = null;
    this._overflowMenuOpen = false;
    this._overflowMenuClosedAt = 0;
    this._resizeObserver = null;
    this._overflowRAF = null;
    this._setupRAF = null;
    this._mergedTranslations = { ...nddMenuBarTranslations };
    this._onSlotChange = () => {
      this._syncCompactAttribute();
      this._scheduleOverflowUpdate();
      this._syncEmpty();
    };
    this._scheduleOverflowUpdate = () => {
      if (this._overflowRAF) cancelAnimationFrame(this._overflowRAF);
      this._overflowRAF = requestAnimationFrame(() => {
        this._overflowRAF = null;
        this._updateOverflow();
      });
    };
    this._onOverflowClick = () => {
      if (!this._overflowMenu) {
        this._overflowMenu = this._createOverflowMenu();
      }
      this._populateOverflowMenu();
      this._overflowMenu.anchorElement = this._overflowButton;
      if (this._overflowMenuOpen) {
        this._overflowMenu.hidePopover();
      } else if (Date.now() - this._overflowMenuClosedAt > POPOVER_REOPEN_GUARD_MS) {
        this._overflowMenu.showPopover();
      }
    };
  }
  _t(key) {
    return this._mergedTranslations[key] ?? key;
  }
  willUpdate(changed) {
    if (changed.has("translations")) {
      this._mergedTranslations = { ...nddMenuBarTranslations, ...this.translations };
    }
    if (changed.has("compact")) {
      this._syncCompactAttribute();
    }
  }
  // ## Computed properties
  /** @internal Used by template */
  get _overflowText() {
    return this.overflowText || this._t("components.menu-bar.overflow-action");
  }
  // ## Lifecycle
  disconnectedCallback() {
    super.disconnectedCallback();
    this._cleanupOverflowDetection();
    this._overflowMenu?.remove();
    this._overflowMenu = null;
  }
  firstUpdated() {
    this._setupOverflowDetection();
    this._syncCompactAttribute();
    this._syncEmpty();
  }
  /** Request a recalculation of overflow state. Call from parent when layout changes. */
  requestOverflowUpdate() {
    this._scheduleOverflowUpdate();
  }
  /** Hide the component when no items are slotted to avoid empty nav landmarks. */
  _syncEmpty() {
    const items = this._defaultSlot?.assignedElements({ flatten: true }) ?? [];
    const hasItems = items.some((el) => el.tagName === "NDD-MENU-BAR-ITEM");
    this.toggleAttribute("empty", !hasItems);
  }
  /** Propagate compact attribute to slotted items and internal overflow button. */
  _syncCompactAttribute() {
    const items = this._defaultSlot?.assignedElements({ flatten: true }) ?? [];
    for (const item of items) {
      item.toggleAttribute("compact", this.compact);
    }
    const overflowItem = this._overflowButton?.querySelector("ndd-menu-bar-item");
    if (overflowItem) {
      overflowItem.toggleAttribute("compact", this.compact);
    }
  }
  // ## Overflow detection
  _setupOverflowDetection() {
    this._cleanupOverflowDetection();
    this._setupRAF = requestAnimationFrame(() => {
      this._setupRAF = null;
      if (!this.isConnected) return;
      this._resizeObserver = new ResizeObserver(() => {
        this._scheduleOverflowUpdate();
      });
      this._resizeObserver.observe(this);
      if (this._defaultSlot) {
        this._defaultSlot.addEventListener("slotchange", this._onSlotChange);
      }
      this._scheduleOverflowUpdate();
    });
  }
  _cleanupOverflowDetection() {
    if (this._setupRAF) {
      cancelAnimationFrame(this._setupRAF);
      this._setupRAF = null;
    }
    if (this._overflowRAF) {
      cancelAnimationFrame(this._overflowRAF);
      this._overflowRAF = null;
    }
    if (this._resizeObserver) {
      this._resizeObserver.disconnect();
      this._resizeObserver = null;
    }
    if (this._defaultSlot) {
      this._defaultSlot.removeEventListener("slotchange", this._onSlotChange);
    }
  }
  /**
   * Calculate which slotted items overflow and hide them behind an overflow button.
   * Note: not unit-tested — JSDOM lacks layout support (offsetWidth, clientWidth).
   * Covered by visual/E2E testing via Storybook stories.
   */
  _updateOverflow() {
    const overflowButton = this._overflowButton;
    if (!overflowButton) return;
    const slottedElements = this._defaultSlot?.assignedElements({ flatten: true }) ?? [];
    const items = slottedElements.filter((el) => el.tagName === "NDD-MENU-BAR-ITEM");
    if (items.length === 0) {
      overflowButton.style.display = "none";
      return;
    }
    items.forEach((item) => {
      item.style.display = "";
      item.removeAttribute("data-overflow");
    });
    overflowButton.style.display = "inline-block";
    const containerWidth = this.clientWidth;
    const overflowButtonWidth = overflowButton.offsetWidth;
    let usedWidth = 0;
    let overflowStartIndex = -1;
    for (let i = 0; i < items.length; i++) {
      const itemWidth = items[i].offsetWidth;
      const availableWidth = containerWidth - overflowButtonWidth;
      if (usedWidth + itemWidth > availableWidth && overflowStartIndex < 0) {
        overflowStartIndex = i;
        break;
      }
      usedWidth += itemWidth;
    }
    if (overflowStartIndex >= 0) {
      for (let i = overflowStartIndex; i < items.length; i++) {
        items[i].style.display = "none";
        items[i].setAttribute("data-overflow", "true");
      }
    } else {
      overflowButton.style.display = "none";
    }
  }
  // ## Overflow popover menu
  _createOverflowMenu() {
    const menu = document.createElement("ndd-menu");
    menu.setAttribute("placement", "bottom-end");
    menu.addEventListener("toggle", (event) => {
      const open = event.newState === "open";
      this._overflowMenuOpen = open;
      if (!open) this._overflowMenuClosedAt = Date.now();
      const item = this._overflowButton?.querySelector("ndd-menu-bar-item");
      if (item) item.open = open;
    });
    document.body.appendChild(menu);
    return menu;
  }
  _populateOverflowMenu() {
    if (!this._overflowMenu) return;
    this._overflowMenu.replaceChildren();
    const slottedElements = this._defaultSlot?.assignedElements({ flatten: true }) ?? [];
    const overflowItems = slottedElements.filter(
      (el) => el.tagName === "NDD-MENU-BAR-ITEM" && el.hasAttribute("data-overflow")
    );
    for (const item of overflowItems) {
      const menuItem = document.createElement("ndd-menu-item");
      menuItem.setAttribute("text", item.text);
      if (item.icon) menuItem.setAttribute("icon", item.icon);
      if (item.current) menuItem.setAttribute("selected", "");
      if (item.disabled) menuItem.setAttribute("disabled", "");
      if (item.expandable) {
        const children = item.querySelectorAll("ndd-menu-item, ndd-menu-divider");
        if (children.length > 0) {
          const divider = document.createElement("ndd-menu-divider");
          this._overflowMenu.appendChild(menuItem);
          this._overflowMenu.appendChild(divider);
          children.forEach((child) => {
            const clone = child.cloneNode(true);
            clone.addEventListener("click", () => {
              child.click();
            });
            this._overflowMenu.appendChild(clone);
          });
          continue;
        }
      }
      menuItem.addEventListener("click", () => {
        item.click();
      });
      this._overflowMenu.appendChild(menuItem);
    }
  }
  // ## Render
  render() {
    return template$3(this);
  }
};
NDDMenuBar.styles = styles$3;
__decorateClass$8([
  property({ type: String, attribute: "overflow-text" })
], NDDMenuBar.prototype, "overflowText", 2);
__decorateClass$8([
  property({ type: String, attribute: "accessible-label" })
], NDDMenuBar.prototype, "accessibleLabel", 2);
__decorateClass$8([
  property({ type: Boolean, reflect: true })
], NDDMenuBar.prototype, "compact", 2);
__decorateClass$8([
  property({ type: Object })
], NDDMenuBar.prototype, "translations", 2);
__decorateClass$8([
  query("slot:not([name])")
], NDDMenuBar.prototype, "_defaultSlot", 2);
__decorateClass$8([
  query(".menu-bar__overflow-button")
], NDDMenuBar.prototype, "_overflowButton", 2);
NDDMenuBar = __decorateClass$8([
  customElement("ndd-menu-bar")
], NDDMenuBar);
const styles$1 = css`


	/* # Host */

	:host {
		--_z-index: 1000;
		--_box-shadow: var(--primitives-box-shadows-level-3);
		--_focus-box-shadow: inset var(--semantics-focus-ring-box-shadow);
		--_focus-outline-offset: -6px;
		display: block;
		position: relative;
	}

	:host([hidden]) {
		display: none;
	}


	/* # Block */

	.skip-link {
		position: absolute;
		top: 0;
		left: 0;
		z-index: var(--_z-index);
		display: flex;
		justify-content: center;
		background-color: var(--semantics-surfaces-background-color);
		box-shadow: var(--_box-shadow);
		border-radius: var(--semantics-controls-md-corner-radius);
		opacity: 0;
		pointer-events: none;
	}

	.skip-link:has(:focus-visible) {
		opacity: 1;
		pointer-events: auto;
	}


	/* # Control */

	.skip-link__control {
		display: inline-flex;
		align-items: center;
		min-height: var(--semantics-controls-md-min-size);
		appearance: none;
		border: none;
		background: none;
		color: var(--semantics-links-color);
		font: var(--primitives-font-body-md-bold-flat);
		text-decoration: underline;
		white-space: nowrap;
		border-radius: var(--semantics-controls-sm-corner-radius);
		padding: var(--primitives-space-4) var(--primitives-space-16);
	}

	.skip-link__control:focus-visible {
		box-shadow: var(--_focus-box-shadow);
		outline: var(--semantics-focus-ring-outline);
		outline-offset: var(--_focus-outline-offset);
	}
`;
function template$1(component) {
  const safeHref = sanitizeUrl(component.href);
  return html`
		<div class="skip-link">
			${safeHref ? html`
				<a class="skip-link__control"
					href=${safeHref}
				>
					${component._text}
				</a>
			` : html`
				<button class="skip-link__control"
					type="button"
					@click=${component._handleClick}
				>
					${component._text}
				</button>
			`}
		</div>
		<slot></slot>
	`;
}
const nddSkipLinkTranslations = {
  "components.skip-link.action": "Sla over"
};
var __defProp$7 = Object.defineProperty;
var __getOwnPropDesc$7 = Object.getOwnPropertyDescriptor;
var __decorateClass$7 = (decorators, target, key, kind) => {
  var result = kind > 1 ? void 0 : kind ? __getOwnPropDesc$7(target, key) : target;
  for (var i = decorators.length - 1, decorator; i >= 0; i--)
    if (decorator = decorators[i])
      result = (kind ? decorator(target, key, result) : decorator(result)) || result;
  if (kind && result) __defProp$7(target, key, result);
  return result;
};
let NDDSkipLink = class extends LitElement {
  constructor() {
    super(...arguments);
    this.text = "";
    this.href = "";
    this.translations = {};
    this._mergedTranslations = { ...nddSkipLinkTranslations };
    this._handleClick = () => {
      const next = this.nextElementSibling;
      if (next) {
        const hadTabindex = next.hasAttribute("tabindex");
        if (!hadTabindex) {
          next.setAttribute("tabindex", "-1");
          next.addEventListener("blur", () => {
            next.removeAttribute("tabindex");
          }, { once: true });
        }
        next.focus();
      }
    };
  }
  _t(key) {
    return this._mergedTranslations[key] ?? key;
  }
  willUpdate(changed) {
    if (changed.has("translations")) {
      this._mergedTranslations = { ...nddSkipLinkTranslations, ...this.translations };
    }
  }
  get _text() {
    return this.text || this._t("components.skip-link.action");
  }
  render() {
    return template$1(this);
  }
};
NDDSkipLink.styles = styles$1;
__decorateClass$7([
  property({ type: String })
], NDDSkipLink.prototype, "text", 2);
__decorateClass$7([
  property({ type: String })
], NDDSkipLink.prototype, "href", 2);
__decorateClass$7([
  property({ type: Object })
], NDDSkipLink.prototype, "translations", 2);
NDDSkipLink = __decorateClass$7([
  customElement("ndd-skip-link")
], NDDSkipLink);
const mdMin$1 = unsafeCSS(breakpoints.mdMin);
const mdMax = unsafeCSS(breakpoints.mdMax);
const lgMin = unsafeCSS(breakpoints.lgMin);
const styles = css`


	/* # Host */

	:host {
		--_logo-width: var(--primitives-space-40);
		--_wordmark-content-color: light-dark(var(--primitives-color-reference-lintblauw), var(--primitives-color-neutral-1000));
		display: block;
		width: 100%;

		@container layout-area (min-width: ${mdMin$1}) {
			--_logo-width: var(--primitives-space-44);
		}

		@container layout-area (min-width: ${lgMin}) {
			--_logo-width: var(--primitives-space-48);
		}
	}

	:host([hidden]) {
		display: none;
	}


	/* # Container */

	.top-navigation-bar {
		display: flex;
		flex-direction: column;
		width: 100%;
		margin: 0 auto;
		box-sizing: border-box;
		container-type: inline-size;
		container-name: top-navigation-bar;
	}


	/* # Logo bar */

	.top-navigation-bar__logo-bar {
		display: grid;
		grid-template-columns: 1fr auto 1fr;
		gap: var(--primitives-space-8);
		align-items: center;
		padding-inline: var(--semantics-page-sections-sm-margin-inline);

		@container layout-area (min-width: ${mdMin$1}) {
			padding-inline: var(--semantics-page-sections-md-margin-inline);
		}

		@container layout-area (min-width: ${lgMin}) {
			padding-inline: var(--semantics-page-sections-lg-margin-inline);
		}
	}

	/* ## Logo */

	.top-navigation-bar__logo {
		grid-column: 2;
		align-self: start;
		display: flex;
		align-items: center;
		justify-content: center;
		width: var(--_logo-width);
		height: calc(var(--_logo-width) * 2);
	}

	.top-navigation-bar__logo svg {
		width: 100%;
		height: 100%;
	}

	/* ## Wordmark */

	.top-navigation-bar__wordmark {
		grid-column: 3;
		display: flex;
		flex-direction: column;
		height: calc(var(--_logo-width) * 2);
		color: var(--_wordmark-content-color);
	}

	.top-navigation-bar__wordmark-spacer {
		flex-grow: 1;
		flex-shrink: 1;
		flex-basis: 50%;
	}

	.top-navigation-bar__wordmark-content {
		display: flex;
		flex-direction: column;
		flex-grow: 1;
		flex-shrink: 1;
		flex-basis: 50%;
	}

	.top-navigation-bar__wordmark-title {
		font: var(--primitives-font-body-md-bold-flat);
		margin: 0;
	}

	.top-navigation-bar__wordmark-subtitle {
		font: var(--primitives-font-body-xs-regular-flat);
		margin: 0;
	}

	.top-navigation-bar__wordmark-supporting-text {
		font: var(--primitives-font-body-xxs-regular-flat);
		margin: 0;
	}


	/* # Main bar */

	.top-navigation-bar__main-bar {
		display: flex;
		flex-direction: column;
		padding-inline: var(--semantics-page-sections-sm-margin-inline);

		@container layout-area (min-width: ${mdMin$1}) {
			padding-inline: var(--semantics-page-sections-md-margin-inline);
		}

		@container layout-area (min-width: ${lgMin}) {
			padding-inline: var(--semantics-page-sections-lg-margin-inline);
		}

		@container top-navigation-bar (min-width: ${mdMin$1}) {
			flex-direction: row;
			align-items: center;
		}
	}

	/* ## Title bar */

	.top-navigation-bar__title-bar {
		display: flex;
		align-items: center;
		justify-content: center;
		padding: var(--primitives-space-4) var(--primitives-space-8);

		@container top-navigation-bar (min-width: ${mdMin$1}) {
			justify-content: flex-start;
			padding: 0;
		}
	}

	/* ## Title */

	.top-navigation-bar__title {
		font: var(--components-top-navigation-bar-title-sm-font);
		color: var(--semantics-content-color);
		padding: 0 var(--primitives-space-8);
		white-space: nowrap;

		@container top-navigation-bar (min-width: ${mdMin$1}) {
			font: var(--components-top-navigation-bar-title-md-font);
		}

		@container top-navigation-bar (min-width: ${lgMin}) {
			font: var(--components-top-navigation-bar-title-lg-font);
		}
	}

	/* ## Menu bar */

	.top-navigation-bar__menu-bar {
		display: flex;
		align-items: center;
		flex-grow: 1;
		min-width: 0;
	}

	/* ## Menu bar start */

	.top-navigation-bar__menu-bar-start {
		display: flex;
		align-items: center;
		flex-grow: 1;
		min-width: 0;
	}

	/* ## Menu bar end */

	.top-navigation-bar__menu-bar-end {
		display: flex;
		align-items: center;

		@container top-navigation-bar (max-width: ${mdMax}) {
			min-width: 0;
		}
	}

	/* ## Global bar */

	.top-navigation-bar__global-menu-bar {
		display: none;
		flex-grow: 1;
		flex-shrink: 1;
		min-width: 0;
		@container top-navigation-bar (min-width: ${lgMin}) {
			:host(.has-global-items) & {
				display: flex;
			}
		}
	}

	/* ## Menu button */

	.top-navigation-bar__menu-button {
		display: none;

		@container top-navigation-bar (max-width: ${mdMax}) {
			:host(.has-global-items) & {
				display: inline-block;
			}
		}
	}

	/* ## Utility menu bar */

	.top-navigation-bar__utility-menu-bar {
		display: flex;
		flex-grow: 1;
		flex-shrink: 1;
		min-width: 0;
	}
`;
const logoSvg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 50 100" aria-hidden="true" focusable="false"><path d="M0 0h50v100H0z" fill="#154273"/><path d="M25.9 77.36h-.87v-2.41h.87zm3.93-10.64h-.87v-2.41h.87zM13.7 62.56c-.06 0-.51 0-.51.1 0 .09.2.04.51.1.7.11.97.46 1.46.46.45 0 .9-.3.72-.94q-.06-.13-.1-.01c-.07.29-.42.45-.8.45-.46 0-.55-.16-1.28-.16m-4.79 2.41c.08.11.9 1.17-.36 1.58q-.1.04 0 .11c.94.39 1.39-.33 1.39-.33.47 1.08-.25 1.67-.25 1.67.1.2.54.52 1.22.67.26-.14.62-.4.77-.8 0 0 .18.46.01.91 1.9.17 2.58-1.35 4.04-1.07q.06 0 .06-.07c0-.94-.57-2.65-2.38-3s-1.33-1.09-1.33-1.09c.77-.03 1.2.3 1.2.3.15-.23-.05-.48-.05-.48.07-.08.11-.4.11-.4-.86 0-1.08-.18-1.08-.18-.13-.5.22-1.23 1.5-.46.32-.28.3-.72.3-.72.09-.04.15-.2.15-.26 0-.2-1.02-.78-1.28-.85-.07-.3-.46-.75-1.66-.6-.57.08-.98-.07-.79-.4.03-.06-.07-.07-.12-.01-.13.13-.31.5.18.75.55.28.59.83.6.9 0 .12-.14.14-.17.02-.25-.93-1.53-1.13-2.28-.64.04.5.58.83.87.83.17 0 .4-.17.4-.4 0-.11.06-.1.1-.01.12.33-.37 1.01-1.1.6-.74.74-.44 1.65-.37 1.99.14.6-.16 1.2-.7.92q-.05-.05-.06.04c0 .38.5.81 1.08.48M13 61.24c-.34.38-.9.3-1.04-.34.7-.04 1.01.03 1.04.34m22.07 1.48c-.37 0-.72-.16-.79-.45-.01-.07-.08-.1-.1 0-.18.65.27.95.72.95.48 0 .76-.35 1.45-.47.31-.05.52 0 .52-.1 0-.09-.45-.09-.52-.09-.72 0-.82.16-1.28.16m7.16 1.77q0-.09-.06-.04c-.54.27-.84-.31-.7-.92.07-.34.36-1.25-.38-2-.73.42-1.22-.26-1.1-.6.04-.08.1-.1.1.02 0 .23.23.4.4.4.3 0 .83-.33.88-.83-.76-.5-2.03-.3-2.28.64-.03.12-.17.1-.16-.01 0-.08.03-.63.58-.91.5-.25.32-.62.19-.75-.06-.06-.16-.05-.13 0 .2.34-.21.49-.78.42-1.2-.16-1.6.28-1.66.6-.26.06-1.28.63-1.28.84 0 .07.06.22.16.26 0 0-.03.44.29.72 1.27-.77 1.63-.05 1.5.46 0 0-.23.18-1.09.19 0 0 .04.3.12.4 0 0-.2.24-.06.47 0 0 .44-.33 1.2-.3 0 0 .49.74-1.32 1.1-1.81.34-2.39 2.05-2.39 3q0 .06.06.06c1.47-.28 2.14 1.24 4.04 1.07-.16-.45.02-.91.02-.91.15.4.51.66.77.8.67-.15 1.12-.48 1.22-.67 0 0-.72-.6-.25-1.67 0 0 .45.72 1.38.33q.11-.07.01-.1c-1.26-.42-.44-1.48-.36-1.59.58.33 1.08-.1 1.08-.48m-4.12-3.6c-.14.64-.7.73-1.05.35.03-.31.34-.38 1.05-.34M24.7 50.22c0 .16.07.3.12.38.12.16.1.25.04.3-.05.05-.14.07-.3-.04a1 1 0 0 0-.37-.12c-.28 0-.41.18-.41.33s.13.33.4.33q.26-.01.38-.12.23-.15.3-.04c.06.05-.02.6-.08 1.04-.46.1-.67.45-.67.67 0 .54.58.86.92 1.04.35-.18.93-.5.93-1.04 0-.22-.22-.58-.67-.67a4 4 0 0 1-.09-1.04c.05-.05.14-.07.3.04q.13.1.38.12c.28 0 .41-.18.41-.33s-.13-.33-.41-.33q-.25.01-.38.12-.23.15-.3.04c-.05-.05-.07-.14.04-.3a1 1 0 0 0 .13-.38c0-.27-.18-.4-.34-.4-.15 0-.33.13-.33.4m.33 4.06a.67.67 0 1 0 0 1.33.67.67 0 0 0 0-1.33m0 6.41c2.67 0 4.18.51 4.18.51.01-1.34 0-2.1.78-1.98-.43-1.14 1.4-1.58 1.4-3.06 0-.97-.7-1.08-.9-1.08-.6 0-.5.4-1.02.4-.06 0-.13-.02-.13.02 0 .17.14.46.38.46.32 0 .32-.31.56-.31.1 0 .24.08.24.4 0 .63-.4 1.33-.9 1.87a.6.6 0 0 0-.44-.25c-.28 0-.54.3-.54.67q0 .18.08.35a1 1 0 0 1-.42.14c-.22 0-.55-.09-.55-.57 0-1.07 1.44-2.01 1.44-3.37 0-.64-.44-1.29-1.34-1.29-.97 0-.79.89-1.63.89q-.06-.01-.07.04c0 .06.15.55.58.55.47 0 .6-.8 1-.8.16 0 .4.09.4.63 0 .42-.22 1.1-.52 1.76a.6.6 0 0 0-.42-.19c-.36 0-.62.35-.62.77q0 .4.28.68c-.2.27-.42.49-.72.49-.58 0-.83-.33-.83-.69 0-.38.7-.53.7-1.13 0-.41-.26-.64-.52-.64-.28 0-.42.18-.45.18s-.17-.18-.44-.18c-.26 0-.53.23-.53.64 0 .6.7.75.7 1.13 0 .36-.25.69-.83.69-.29 0-.5-.22-.72-.5a1 1 0 0 0 .28-.67c0-.42-.25-.77-.61-.77a.6.6 0 0 0-.43.2 5 5 0 0 1-.5-1.77c0-.54.22-.63.38-.63.4 0 .54.8 1 .8.44 0 .58-.5.58-.55q0-.04-.07-.04c-.84 0-.65-.89-1.62-.89-.9 0-1.34.65-1.34 1.3 0 1.35 1.43 2.3 1.43 3.36 0 .48-.33.57-.54.57a1 1 0 0 1-.42-.14 1 1 0 0 0 .07-.35c0-.37-.25-.67-.54-.67q-.27.01-.44.25c-.49-.54-.9-1.24-.9-1.87 0-.32.15-.4.25-.4.23 0 .24.31.56.31.23 0 .38-.29.38-.46 0-.04-.07-.03-.13-.03-.52 0-.42-.39-1.03-.39-.2 0-.89.11-.89 1.08 0 1.48 1.82 1.92 1.4 3.06.77-.12.76.64.78 1.98 0 0 1.5-.5 4.17-.5m-4.89 2q-1.11.24-1.48.38c.01-.33.13-.62.42-.69.04 0 .05-.06.01-.08-.65-.43-1 .4-1 .42-.23-.02-.58.05-.58.37 0 .92-2.12 1.44-2.61 1.51.86.34 1.22 1.43 1.22 1.43a5 5 0 0 1 1.53-1.18c.17 0 .23.2.24.33q.02.06.07.02c.33-.5.17-.6.15-.75-.03-.11 0-.54.49-.5v6.2l-.25.05c-.11.02-1.02-.75-2.05-1.47-1.04-.72-1.6-.29-2.78.35-1.54.84-3.1.08-3.1.08-1.34.95-1.8 3.7-1.8 3.7-.26.12-.7.24-1.12.24-1.01 0-1.2-.62-1.2-.99 0-1.57 1.97-2.24 1.97-3.79 0-.37-.18-1.9-2.07-1.9H4.51c-.7 0-.88-.51-.98-.7-.04-.08-.11-.04-.08.02.05.13-.09.33-.09.72 0 .63.37 1 1.06 1 .31 0 .6-.08.7-.14.07-.04.1.02.07.06-.3.35-.32 1-.2 1.16q.05.05.08 0a1.7 1.7 0 0 1 1.62-1.3c1.03 0 1.02.88 1.02 1.1 0 1.25-2.21 2.18-2.21 3.9 0 1.77 1.85 2.14 2.93 1.86-.06 1.76-2.08 2.36-2.14 1.1q-.02-.1-.08 0c-.25.63-.15 1.18.63 1.35q.06.03-.02.08c-.78.5-.36 2.43-.32 3 .06.82-.76.72-.82.7q-.08-.02-.02.07c.58.71 1.3.06 1.3.06.54.17.2.63-.16.87q-.08.07.01.08c.08 0 .92.08 1.07-.59.37.44.92.28 1.03.22.16-.08.95-.36 1.02.52 0 .06.05.02.07-.01.6-.75-.04-1.2-.4-1.26a.6.6 0 0 1 .94.11q.04.08.06-.03c.05-.95-.72-1.03-1.22-.62-.02-.1-.19-.63.56-.61.02 0 .06-.03.02-.06-.58-.62-1.06-.06-1.18.07-.26.31-.9.19-.96.18.2-3.29 3.1-2.12 3.5-3.72.01-.08.05-.05.06-.02.1.39 1.1.44 1.27-.32q.02-.1-.03-.05c-.84.83-2.73-1.78-.15-3.91a3.74 3.74 0 0 1 4.92-.2c.04.26-.12.34-.22.37q-.05.03.01.07c.21.08.5.05.65-.14.47.33.07.74-.13.86q-.05.05.02.07c.43.08.79-.37.8-.62l.08.04v1.87c0 2.66 3.07 3.03 6.43 5.28 3.37-2.25 6.44-2.62 6.44-5.28v-1.87l.07-.04c.02.25.38.7.81.62q.07-.01.01-.07c-.19-.12-.6-.53-.12-.86.14.2.43.22.64.14q.08-.04.01-.07c-.1-.03-.25-.11-.21-.38.75-.6 2.72-1.6 4.92.2 2.57 2.14.68 4.75-.15 3.92q-.05-.04-.03.05c.18.76 1.16.7 1.27.32 0-.03.04-.06.06.02.4 1.6 3.3.43 3.5 3.72-.06 0-.7.13-.97-.18-.1-.13-.59-.7-1.17-.07-.04.03 0 .06.01.06.76-.02.59.51.57.61-.5-.41-1.27-.33-1.22.62q0 .1.06.03a.6.6 0 0 1 .93-.11c-.35.05-.99.51-.4 1.26.03.03.07.07.07 0 .08-.87.86-.59 1.03-.5.11.05.66.21 1.03-.23.15.67.98.6 1.06.6q.1-.02.01-.09c-.36-.24-.7-.7-.15-.87 0 0 .72.65 1.3-.06.05-.07.01-.08-.02-.07-.07.02-.89.12-.83-.7.04-.57.46-2.5-.31-3q-.1-.06-.02-.08c.78-.17.88-.72.63-1.34q-.07-.11-.09 0c-.06 1.25-2.07.65-2.13-1.1 1.07.27 2.93-.1 2.93-1.86 0-1.73-2.21-2.66-2.21-3.92 0-.2-.01-1.08 1.02-1.08.83 0 1.46.63 1.62 1.3 0 .02.05.03.07 0 .13-.17.1-.82-.2-1.17-.03-.04 0-.1.07-.06.1.06.4.15.7.15.7 0 1.06-.38 1.06-1.01 0-.4-.13-.59-.08-.72.03-.06-.05-.1-.08-.03-.1.2-.28.7-.99.7h-1.69c-1.89 0-2.06 1.54-2.06 1.91 0 1.55 1.97 2.22 1.97 3.8 0 .36-.19.98-1.2.98-.42 0-.87-.12-1.13-.23 0 0-.45-2.76-1.79-3.71 0 0-1.56.76-3.1-.08-1.19-.64-1.74-1.07-2.78-.35s-1.94 1.49-2.05 1.47l-.25-.05v-6.2c.48-.04.51.39.5.5-.04.15-.2.26.14.75q.05.04.06-.02c.02-.12.08-.33.25-.33s.9.55 1.52 1.18c0 0 .36-1.1 1.23-1.43-.5-.07-2.61-.59-2.61-1.51 0-.32-.35-.39-.58-.37-.01-.03-.36-.85-1-.42a.04.04 0 0 0 0 .08c.3.07.42.36.43.69-.62-.2-3.25-.93-6.38-.93-1.51 0-2.9.17-4.02.37v2.15h-.87zm-5.76 21.98c-.23-.1-.38-.24-.38-.55v-1.33c-.38-.13-1.43-.53-3.5-.53-1.74 0-2.28.39-2.3.53l-.47 2.53s.7-.64 3.21-.47c3.02.19 6.16 1.97 6.16.07v-1.12c-2.37 0-2.72.76-2.72.87m18.6-.87v1.12c0 1.9 3.12.12 6.14-.07 2.51-.17 3.21.47 3.21.47l-.46-2.53c-.02-.14-.56-.53-2.3-.53-2.07 0-3.12.4-3.5.53v1.33q-.02.43-.38.55c0-.11-.35-.87-2.72-.87m-7.95-1.15c4.87 0 9.81.26 10.46.99.05.06.07 0 .07-.05V81c0-.76-5.1-1.2-10.53-1.2s-10.52.44-10.52 1.2v2.57c0 .05.02.1.07.05.65-.73 5.59-.99 10.45-.99M20.7 70.47l-.49-.12-.04.06-.57-.25h.51q.07-.02.03-.06l-.44-.43.56.21q.06.01.04-.04l-.38-.55.55.37q.05.02.05-.03l-.27-.65.5.48q.05.02.05-.02l-.14-.65.37.54q.04.04.05-.01l.01-.6.24.55q.02.06.06-.01l.2-.46.01.62-.08.01-.1.74c.73-.17 1.65-1.43 2.35-1.43.84 0 1.14.98 2.68.49.4.57.53 1.08.68 1.77.6.56 1.43.37 1.43-.22 0-.8-.87-.95-.87-1.79 0-.37.26-.9.98-.9.37 0 .93.16 1.24.16.38 0 .46-.28.5-.39.04-.08.14-.06.13 0-.01.09.04.2.04.38 0 .52-.76.6-.86.53-.04-.03-.07.01-.04.03.12.1.09.41-.05.61q-.02.03-.04 0c-.08-.38-.53-.85-.92-.85-.14 0-.43.09-.43.42 0 .47.96.9.96 1.9 0 1.01-1.02 1.26-2.04 1 .04.97 1.48 1.55 1.52.86 0-.05.03-.02.04 0 .22.3.12.52-.16.63.26.12.3.62.38.93.1.45.59.2.61.19q.05-.02.03.03c-.19.47-.67.3-.67.3-.26.17.05.33.28.4q.06.01 0 .04c-.16.07-.53.18-.7-.12-.13.31-.4.3-.5.3-.2 0-.32.2-.27.45q0 .03-.03.01c-.45-.3-.2-.64-.01-.72-.03-.02-.34-.15-.47.2q-.01.06-.04.01c-.19-.51.23-.66.54-.53-.02-.08-.18-.33-.58-.25q-.03 0-.02-.03c.06-.15.26-.39.63-.15.18.11.5-.05.53-.07-.65-1.29-1.9-.2-2.18-1.22 0-.02-.03-.04-.05.02-.07.21-.62.23-.72-.2q0-.04.03-.01c.08.08.25.15.48-.18.15-.21.17-.5.17-.7 0-.78-.78-2.1-2-2.1-.78 0-1.6.3-2.22.75l.57.14a.9.9 0 0 1-1.12.77l.09-.66a1 1 0 0 0-.44.28l-.03-.01c-.1-.38.2-.57.3-.61q.03-.02 0-.02a.6.6 0 0 0-.48.26q-.01.02-.02 0c-.03-.07-.08-.26.05-.4m1.7 4.48c-.21.27-.4.01-.7.01-.27 0-.31.23-.32.32q0 .03-.02 0c-.3-.41.04-.64.24-.67-.03-.03-.33-.23-.53.04q-.02.02-.03 0c0-.53.4-.57.68-.34.05-.2-.08-.33-.3-.34q-.04 0-.02-.03.14-.14.27-.14c.29 0 .33.36.51.36.29 0 .69-.38.73-.42 0-.02-.28-.75-.23-1.2q0-.02-.02 0c-.13.07-.48.07-.48-.36q0-.06.03-.01c.15.2.4-.03.52-.17.13-.15.85-1.19 1.8-1.19.21 0 .48.12.7.27-.33.4 0 .78.24.74q.05 0 0 .03c-1.25.47-1.82.66-1.82 1.71 0 .55.2.86.52.79q.04 0 .01.02a.5.5 0 0 1-.36.19c-.27 0-.31-.15-.45-.15s-.62.28-.62.51q-.01.14.22.31v.02c-.1.02-.48.05-.56-.3m3.32-10.25c-.4-.03-.64.06-.63.19.19.2.44.18.63-.2m-1.45.97c.28-.07.58-.04.62-.03s.04.09-.01.1c-.58.07-.6.33-.98.33-.24 0-.5-.24-.4-.6q.02-.08.05 0c.04.15.27.32.72.2m-7.53 12.86c.38.5.75.03 1.26.03.24 0 .54.08.6.58q0 .04.05 0c.55-.76-.08-1.18-.44-1.23.08-.07.61-.4.96.08q.03.04.05-.01c0-.95-.71-1.02-1.23-.6-.1-.38.19-.62.55-.62q.06 0 .03-.06c-.64-.68-1.11.18-1.22.31-.25.34-1.16-.3-1.52-.67 0 0 .8-.84.8-1.61v-.14q0-.03.03-.02.12.08.3.08c.17 0 .52-.06.52-.71q0-.07-.04-.02-.16.19-.28.17c-.65 0-2-2.16-3.6-2.16-.42 0-1.2.3-1.6.73.19.11.22.35.2.52-.03.27-.24.4-.47.47q-.06.02 0 .06c.81.3 2.28.86 2.61 1.15.4.34.32.98.09 1.87-.22.85-.7.73-.87.7q-.03 0-.02.04c.21.26.47.35.68.35.42 0 .58-.26.8-.26.36 0 1.12.52 1.12.92 0 .22-.17.42-.4.57q-.01.02.01.03c.18.03.9.1 1.03-.55m17.63.55q.04 0 .01-.03c-.22-.15-.4-.35-.4-.57 0-.4.77-.92 1.13-.92.22 0 .38.26.8.26q.34.02.67-.35.02-.04-.02-.03c-.17.02-.64.14-.86-.71-.23-.89-.3-1.53.09-1.87.33-.3 1.8-.85 2.6-1.15q.07-.04 0-.06c-.22-.06-.44-.2-.47-.47-.02-.17.02-.4.21-.52a2.7 2.7 0 0 0-1.6-.73c-1.6 0-2.95 2.16-3.6 2.16q-.13.02-.28-.17-.04-.05-.04.02c0 .65.34.7.53.7q.16.01.3-.07.02-.01.02.02v.14c0 .77.8 1.6.8 1.6-.36.39-1.27 1.02-1.52.68-.11-.13-.59-.99-1.22-.3q-.04.04.03.05c.36 0 .64.24.54.61-.51-.41-1.22-.34-1.22.6q.01.06.05.02c.34-.48.88-.15.96-.08-.36.05-.99.47-.44 1.23q.03.04.05 0c.05-.5.36-.58.6-.58.5 0 .87.46 1.26-.03.14.64.85.58 1.02.55M21.45 66.61c-.05.07-.22 0-.28-.03h-.02c.04.1.2.37.45.37.1 0 .26-.07.3-.14l1.41.43q-.27.37-.31.85c-.38-.23-1.88-1.04-1.88-1.04l-.46.64c-.08.1-.45-.17-.37-.27l.35-.49c-.12-.12-.4-.05-.48-.02q-.02 0 0-.02c.04-.1.22-.4.66-.26 0-.27-.4-.18-.5-.15q-.03 0-.01-.02c.1-.12.43-.38.8-.16l.16-.22-.33-.34.2-.28.23.3 1.73-2.37c.05-.05.39-.15.52-.18.01.13.03.49-.02.55l-1.7 2.39.36.12-.2.27-.42-.2zm6.07-.39c0 .22.13.54.42.44q.03 0 .03.02c-.05.24-.48.46-.68.17-.17.37-.13.72.25.93q.03.01 0 .05a.5.5 0 0 1-.74-.19c-.31.24-.27.73-.08.9 0 0-.86.52-1.64.15-.52-.25-.94-.56-1.6-.51.09-.94.56-1.18 1.42-1.32.68-.1.77-.42.67-.66-.23-.07-.66.15-.66.15-.08-.13.04-.26.04-.26-.05-.06-.07-.23-.07-.23.48 0 .57-.1.57-.1.08-.5-.43-.56-.81-.29-.18-.16-.16-.37-.16-.37q-.08-.06-.08-.15c0-.11.57-.43.71-.47.04-.17.25-.4.85-.34.07-.16-.04-.75-.12-.9q-.02-.08.07-.05c.2.14.42.63.56.64 0 0 .68-.36.72-.34s.12.78.12.78c.1.11.62 0 .85.1q.08.06 0 .08c-.17.03-.72.26-.8.41.3.48.16 1.17.16 1.36" fill="#fff"/></svg>';
function template(component) {
  return html`
		<div class="top-navigation-bar">
			${!component.noLogo ? html`<div class="top-navigation-bar__logo-bar">
				<div class="top-navigation-bar__logo"
					role="img"
					aria-label="${component._t("components.top-navigation-bar.logo-label")}"
				>
					${/* xss-safe: logoSvg is a bundled static asset (logo.svg?raw), never user input.
  If the source changes to dynamic/user-supplied, replace unsafeHTML with a safe alternative. */
  ""}
					${unsafeHTML(logoSvg)}
				</div>
				${component.logoTitle ? html`
					<div class="top-navigation-bar__wordmark">
						<div class="top-navigation-bar__wordmark-spacer"></div>
						<div class="top-navigation-bar__wordmark-content">
							<p class="top-navigation-bar__wordmark-title">
								${component.logoTitle}
							</p>
							${component.logoSubtitle ? html`
								<p class="top-navigation-bar__wordmark-subtitle">
									${component.logoSubtitle}
								</p>
							` : nothing}
							${component.logoSupportingText1 ? html`
								<p class="top-navigation-bar__wordmark-supporting-text">
									${component.logoSupportingText1}
								</p>
							` : nothing}
							${component.logoSupportingText2 ? html`
								<p class="top-navigation-bar__wordmark-supporting-text">
									${component.logoSupportingText2}
								</p>
							` : nothing}
						</div>
					</div>
				` : nothing}
			</div>` : nothing}
			<div class="top-navigation-bar__main-bar">
				${component.websiteTitle ? html`
					<div class="top-navigation-bar__title-bar">
						<span class="top-navigation-bar__title">
							${component.websiteTitle}
						</span>
					</div>
				` : nothing}
				<div class="top-navigation-bar__menu-bar">
					<div class="top-navigation-bar__menu-bar-start">
						${component._hasBackButton ? html`
							<div class="top-navigation-bar__back-button">
								<ndd-menu-bar-item
									icon="arrow-left"
									text="${component._backText}"
									href=${component.backHref || nothing}
									accessible-label="${component._backText}"
									@click=${component._handleBackClick}
								></ndd-menu-bar-item>
							</div>
						` : nothing}
						<div class="top-navigation-bar__menu-button">
							<ndd-menu-bar-item
								icon="menu"
								text="${component._menuText}"
								haspopup="dialog"
								@click=${component._onMenuButtonClick}
							></ndd-menu-bar-item>
						</div>
						<div class="top-navigation-bar__global-menu-bar">
							<ndd-menu-bar
								accessible-label="${component._t("components.top-navigation-bar.global-menu-bar-label")}"
							>
								<slot name="global"></slot>
							</ndd-menu-bar>
						</div>
					</div>
					<div class="top-navigation-bar__menu-bar-end">
						<div class="top-navigation-bar__utility-menu-bar">
							<ndd-menu-bar
								accessible-label="${component._t("components.top-navigation-bar.utility-menu-bar-label")}"
							>
								<slot name="utility"></slot>
							</ndd-menu-bar>
						</div>
					</div>
				</div>
			</div>
		</div>
	`;
}
const nddTopNavigationBarTranslations = {
  "components.top-navigation-bar.global-menu-bar-label": "Hoofdnavigatie",
  "components.top-navigation-bar.back-action": "Terug",
  "components.top-navigation-bar.menu-action": "Menu",
  "components.top-navigation-bar.logo-label": "Rijkswapen - Rijksoverheid",
  "components.top-navigation-bar.utility-menu-bar-label": "Hulplinks",
  "components.top-navigation-bar.menu-sheet-dismiss-action": "Sluit"
};
var __defProp$6 = Object.defineProperty;
var __getOwnPropDesc$6 = Object.getOwnPropertyDescriptor;
var __decorateClass$6 = (decorators, target, key, kind) => {
  var result = kind > 1 ? void 0 : kind ? __getOwnPropDesc$6(target, key) : target;
  for (var i = decorators.length - 1, decorator; i >= 0; i--)
    if (decorator = decorators[i])
      result = (kind ? decorator(target, key, result) : decorator(result)) || result;
  if (kind && result) __defProp$6(target, key, result);
  return result;
};
let NDDTopNavigationBar = class extends LitElement {
  constructor() {
    super(...arguments);
    this.websiteTitle = "";
    this.noLogo = false;
    this.logoTitle = "";
    this.logoSubtitle = "";
    this.logoSupportingText1 = "";
    this.logoSupportingText2 = "";
    this.backHref = "";
    this.backText = "";
    this.translations = {};
    this._globalMenuSheet = null;
    this._globalMenuSheetList = null;
    this._resizeObserver = null;
    this._compactRAF = null;
    this._setupRAF = null;
    this._mergedTranslations = { ...nddTopNavigationBarTranslations };
    this._handleItemSelect = (event) => {
      const detail = event.detail;
      if (!detail?.item) return;
      const slottedItems = this._globalSlot?.assignedElements({ flatten: true }) ?? [];
      if (!slottedItems.includes(detail.item)) return;
      const selectEvent = new CustomEvent("itemselect", {
        bubbles: true,
        composed: true,
        cancelable: true,
        detail
      });
      this.dispatchEvent(selectEvent);
      if (!selectEvent.defaultPrevented) {
        detail.item.current = true;
        slottedItems.forEach((item) => {
          if (item !== detail.item) {
            item.removeAttribute("current");
          }
        });
      }
    };
    this._onGlobalSlotChange = () => {
      this._syncHasGlobalItems();
    };
    this._scheduleCompactUpdate = () => {
      if (this._compactRAF) cancelAnimationFrame(this._compactRAF);
      this._compactRAF = requestAnimationFrame(() => {
        this._syncCompactAttribute();
      });
    };
    this._onMenuButtonClick = async () => {
      if (!this._globalMenuSheet) {
        try {
          await this._loadGlobalMenuSheetDependencies();
        } catch (error) {
          return;
        }
        if (!this.isConnected) return;
        if (this._globalMenuSheet) return;
        this._globalMenuSheet = this._createGlobalMenuSheet();
        const menuButtonItem = this._menuButton?.querySelector("ndd-menu-bar-item");
        this._globalMenuSheet.addEventListener("open", () => {
          if (menuButtonItem) menuButtonItem.open = true;
        });
        this._globalMenuSheet.addEventListener("close", () => {
          if (menuButtonItem) menuButtonItem.open = false;
        });
      }
      this._syncGlobalMenuSheetItems();
      requestAnimationFrame(() => {
        this._globalMenuSheet?.show();
      });
    };
    this._handleBackClick = (e) => {
      if (!this.backHref) {
        e.preventDefault();
        this.dispatchEvent(
          new CustomEvent("back-click", {
            bubbles: true,
            composed: true
          })
        );
      }
    };
  }
  /** @internal Used by template */
  _t(key) {
    return this._mergedTranslations[key] ?? key;
  }
  willUpdate(changed) {
    if (changed.has("translations")) {
      this._mergedTranslations = { ...nddTopNavigationBarTranslations, ...this.translations };
      this._globalMenuSheet?.setAttribute("accessible-label", this._t("components.top-navigation-bar.menu-action"));
      this._globalMenuSheet?.querySelector("ndd-top-title-bar")?.setAttribute("text", this._menuText);
      this._globalMenuSheet?.querySelector("ndd-top-title-bar")?.setAttribute("dismiss-text", this._t("components.top-navigation-bar.menu-sheet-dismiss-action"));
    }
  }
  // ## Computed properties
  /** @internal Used by template */
  get _hasBackButton() {
    return Boolean(this.backHref || this.backText);
  }
  /** @internal Used by template */
  get _backText() {
    return this.backText || this._t("components.top-navigation-bar.back-action");
  }
  /** @internal Used by template */
  get _menuText() {
    return this._t("components.top-navigation-bar.menu-action");
  }
  // ## Lifecycle
  connectedCallback() {
    super.connectedCallback();
    this.addEventListener("select", this._handleItemSelect);
  }
  disconnectedCallback() {
    super.disconnectedCallback();
    this.removeEventListener("select", this._handleItemSelect);
    this._cleanupCompactDetection();
    this._globalMenuSheet?.remove();
    this._globalMenuSheet = null;
    this._globalMenuSheetList = null;
  }
  firstUpdated() {
    this._syncHasGlobalItems();
    this._setupCompactDetection();
  }
  // ## Compact attribute propagation
  _setupCompactDetection() {
    this._cleanupCompactDetection();
    this._setupRAF = requestAnimationFrame(() => {
      this._setupRAF = null;
      if (!this.isConnected) return;
      this._resizeObserver = new ResizeObserver(() => {
        this._scheduleCompactUpdate();
      });
      this._resizeObserver.observe(this);
      if (this._globalSlot) {
        this._globalSlot.addEventListener("slotchange", this._onGlobalSlotChange);
      }
      this._scheduleCompactUpdate();
    });
  }
  _cleanupCompactDetection() {
    if (this._setupRAF) {
      cancelAnimationFrame(this._setupRAF);
      this._setupRAF = null;
    }
    if (this._compactRAF) {
      cancelAnimationFrame(this._compactRAF);
      this._compactRAF = null;
    }
    if (this._resizeObserver) {
      this._resizeObserver.disconnect();
      this._resizeObserver = null;
    }
    if (this._globalSlot) {
      this._globalSlot.removeEventListener("slotchange", this._onGlobalSlotChange);
    }
  }
  /** Update has-global-items class on host based on global slot content. */
  _syncHasGlobalItems() {
    const globalItems = this._globalSlot?.assignedElements({ flatten: true }) ?? [];
    const hasGlobalItems = globalItems.some((el) => el.tagName === "NDD-MENU-BAR-ITEM");
    this.classList.toggle("has-global-items", hasGlobalItems);
  }
  /** Propagate compact to menu-bars and internal items when container is sm. */
  _syncCompactAttribute() {
    const isCompact = this._isSmBreakpoint();
    const menuBars = this.shadowRoot?.querySelectorAll("ndd-menu-bar") ?? [];
    for (const menuBar of menuBars) {
      menuBar.toggleAttribute("compact", isCompact);
      menuBar.requestOverflowUpdate();
    }
    const internalItems = this.shadowRoot?.querySelectorAll("ndd-menu-bar-item") ?? [];
    for (const item of internalItems) {
      item.toggleAttribute("compact", isCompact);
    }
    this._syncHasGlobalItems();
  }
  /** Check if the container is at the sm breakpoint (<= smMax). */
  _isSmBreakpoint() {
    const container = this.shadowRoot?.querySelector(".top-navigation-bar");
    if (!container) return false;
    return container.clientWidth <= parseInt(breakpoints.smMax);
  }
  // ## Menu sheet
  async _loadGlobalMenuSheetDependencies() {
    await Promise.all([
      Promise.resolve().then(() => nddSheet),
      Promise.resolve().then(() => nddPage),
      Promise.resolve().then(() => nddSimpleSection),
      Promise.resolve().then(() => nddTopTitleBar),
      Promise.resolve().then(() => nddList),
      Promise.resolve().then(() => nddListItem),
      Promise.resolve().then(() => nddTextCell)
    ]);
  }
  _createGlobalMenuSheet() {
    const sheet = document.createElement("ndd-sheet");
    sheet.setAttribute("placement", "left");
    sheet.setAttribute("accessible-label", this._t("components.top-navigation-bar.menu-action"));
    const page = document.createElement("ndd-page");
    page.setAttribute("sticky-header", "");
    const titleBar = document.createElement("ndd-top-title-bar");
    titleBar.setAttribute("slot", "header");
    titleBar.setAttribute("text", this._menuText);
    titleBar.setAttribute("dismiss-text", this._t("components.top-navigation-bar.menu-sheet-dismiss-action"));
    page.appendChild(titleBar);
    const section = document.createElement("ndd-simple-section");
    this._globalMenuSheetList = document.createElement("ndd-list");
    this._globalMenuSheetList.setAttribute("variant", "simple");
    this._globalMenuSheetList.setAttribute("no-dividers", "");
    section.appendChild(this._globalMenuSheetList);
    page.appendChild(section);
    sheet.appendChild(page);
    document.body.appendChild(sheet);
    return sheet;
  }
  _syncGlobalMenuSheetItems() {
    if (!this._globalMenuSheetList) return;
    this._globalMenuSheetList.replaceChildren();
    const slottedElements = this._globalSlot?.assignedElements({ flatten: true }) ?? [];
    const items = slottedElements.filter((el) => el.tagName === "NDD-MENU-BAR-ITEM");
    for (const item of items) {
      const listItem = document.createElement("ndd-list-item");
      const safeHref = sanitizeUrl(item.href);
      if (safeHref) {
        listItem.setAttribute("type", "link");
        listItem.setAttribute("href", safeHref);
      } else {
        listItem.setAttribute("type", "button");
      }
      if (item.current) listItem.setAttribute("selected", "");
      const textCell = document.createElement("ndd-text-cell");
      textCell.setAttribute("text", item.text);
      listItem.appendChild(textCell);
      listItem.addEventListener("click", () => {
        if (!safeHref) item.click();
        this._globalMenuSheet?.hide();
      });
      this._globalMenuSheetList.appendChild(listItem);
    }
  }
  // ## Render
  render() {
    return template(this);
  }
};
NDDTopNavigationBar.styles = styles;
__decorateClass$6([
  property({ type: String, attribute: "website-title" })
], NDDTopNavigationBar.prototype, "websiteTitle", 2);
__decorateClass$6([
  property({ type: Boolean, attribute: "no-logo", reflect: true })
], NDDTopNavigationBar.prototype, "noLogo", 2);
__decorateClass$6([
  property({ type: String, attribute: "logo-title" })
], NDDTopNavigationBar.prototype, "logoTitle", 2);
__decorateClass$6([
  property({ type: String, attribute: "logo-subtitle" })
], NDDTopNavigationBar.prototype, "logoSubtitle", 2);
__decorateClass$6([
  property({ type: String, attribute: "logo-supporting-text-1" })
], NDDTopNavigationBar.prototype, "logoSupportingText1", 2);
__decorateClass$6([
  property({ type: String, attribute: "logo-supporting-text-2" })
], NDDTopNavigationBar.prototype, "logoSupportingText2", 2);
__decorateClass$6([
  property({ type: String, attribute: "back-href" })
], NDDTopNavigationBar.prototype, "backHref", 2);
__decorateClass$6([
  property({ type: String, attribute: "back-text" })
], NDDTopNavigationBar.prototype, "backText", 2);
__decorateClass$6([
  property({ type: Object })
], NDDTopNavigationBar.prototype, "translations", 2);
__decorateClass$6([
  query(".top-navigation-bar__menu-button")
], NDDTopNavigationBar.prototype, "_menuButton", 2);
__decorateClass$6([
  query('slot[name="global"]')
], NDDTopNavigationBar.prototype, "_globalSlot", 2);
__decorateClass$6([
  query('slot[name="utility"]')
], NDDTopNavigationBar.prototype, "_utilitySlot", 2);
NDDTopNavigationBar = __decorateClass$6([
  customElement("ndd-top-navigation-bar")
], NDDTopNavigationBar);
const topTitleBarStyles = css`

	/* # Host */

	:host {
		display: block;
		width: 100%;
	}

	:host([hidden]) {
		display: none;
	}


	/* # Top title bar */

	.top-title-bar {
		display: flex;
		flex-direction: row;
		align-items: center;
		width: 100%;
		box-sizing: border-box;
		padding-inline: var(--primitives-space-6);
	}


	/* # Start */

	.top-title-bar__start {
		display: flex;
		flex-direction: row;
		align-items: center;
		flex-grow: 1;
		flex-shrink: 1;
		flex-basis: 0;
		min-width: 0;
	}


	/* # End */

	.top-title-bar__end {
		display: flex;
		flex-direction: row;
		align-items: center;
		flex-grow: 0;
		flex-shrink: 0;
		margin-top: var(--primitives-space-6);
	}

	.top-title-bar__end[hidden] {
		display: none;
	}


	/* # Back button — text variant (default state) */

	.top-title-bar__back-button {
		display: var(--context-back-button-display, flex);
		flex-direction: row;
		align-items: center;
		margin-top: var(--primitives-space-6);
	}

	.top-title-bar__text-back-button {
		display: flex;
	}

	:host(.is-compact) .top-title-bar__text-back-button {
		display: none;
	}


	/* # Back button — icon variant (compact state) */

	.top-title-bar__icon-back-button {
		display: none;
	}

	:host(.is-compact) .top-title-bar__icon-back-button {
		display: flex;
	}


	/* # Divider */

	.top-title-bar__divider {
		display: none;
		width: var(--semantics-dividers-thickness);
		height: var(--primitives-space-24);
		background-color: var(--components-top-title-bar-divider-color);
		flex-shrink: 0;
	}

	:host(.is-compact) .top-title-bar__divider {
		display: block;
	}


	/* # Title group */

	.top-title-bar__title-group {
		display: none;
		flex-direction: column;
		justify-content: center;
		flex-grow: 1;
		flex-shrink: 1;
		min-width: 0;
		min-height: var(--semantics-controls-md-min-size);
		margin-top: var(--primitives-space-6);
		padding-inline: var(--primitives-space-10);
		overflow: hidden;
	}

	:host(.is-compact) .top-title-bar__title-group {
		display: flex;
	}

	.top-title-bar__title {
		margin: 0;
		font: var(--primitives-font-body-lg-bold-flat);
		color: var(--semantics-content-color);
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.top-title-bar__title:has(+ .top-title-bar__subtitle) {
		font: var(--primitives-font-body-md-bold-flat);
	}

	.top-title-bar__subtitle {
		margin: 0;
		font: var(--primitives-font-body-xxs-regular-flat);
		color: var(--semantics-content-secondary-color);
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}


	/* # Dismiss button */

	.top-title-bar__dismiss-button {
		display: var(--context-dismiss-button-display, block);
	}


	/* # Accessibility: High Contrast Mode */

	@media (forced-colors: active) {
		.top-title-bar__title {
			color: CanvasText;
		}
	}
`;
function topTitleBarTemplate(component) {
  const showBack = !!component.backText;
  return html`
		<div class="top-title-bar">
			<div class="top-title-bar__start">
				${showBack ? html`
					<div class="top-title-bar__back-button">
						<div class="top-title-bar__text-back-button">
							<ndd-button
								variant="accent-transparent"
								start-icon="chevron-left"
								text=${component.backText}
								href=${component.backHref || nothing}
								@click=${component._handleBack}
							></ndd-button>
						</div>
						<div class="top-title-bar__icon-back-button">
							<ndd-icon-button
								variant="accent-transparent"
								icon="chevron-left"
								text=${component.backText}
								accessible-label=${component.backText || nothing}
								href=${component.backHref || nothing}
								@click=${component._handleBack}
							></ndd-icon-button>
						</div>
						<div class="top-title-bar__divider"></div>
					</div>
				` : nothing}
				<div class="top-title-bar__title-group">
					<h1 class="top-title-bar__title">${component.text}</h1>
					${component.supportingText ? html`
						<p class="top-title-bar__subtitle">${component.supportingText}</p>
					` : nothing}
				</div>
			</div>
			<div class="top-title-bar__end" ?hidden=${!component.dismissText && !component._hasToolbarItems}>
				<slot name="toolbar" @slotchange=${component._onToolbarSlotChange}></slot>
				${component.dismissText ? html`
					<div class="top-title-bar__dismiss-button">
						<ndd-button
							variant="accent-transparent"
							text=${component.dismissText}
							@click=${component._handleDismiss}
						></ndd-button>
					</div>
				` : nothing}
			</div>
		</div>
	`;
}
var __defProp$5 = Object.defineProperty;
var __getOwnPropDesc$5 = Object.getOwnPropertyDescriptor;
var __decorateClass$5 = (decorators, target, key, kind) => {
  var result = kind > 1 ? void 0 : kind ? __getOwnPropDesc$5(target, key) : target;
  for (var i = decorators.length - 1, decorator; i >= 0; i--)
    if (decorator = decorators[i])
      result = (kind ? decorator(target, key, result) : decorator(result)) || result;
  if (kind && result) __defProp$5(target, key, result);
  return result;
};
let NDDTopTitleBar = class extends LitElement {
  constructor() {
    super(...arguments);
    this.text = "";
    this.supportingText = "";
    this.collapseAnchor = "";
    this.backText = "";
    this.backHref = "";
    this.dismissText = "";
    this._hasToolbarItems = false;
    this._pageElement = null;
    this._anchorElement = null;
    this._activeScrollTarget = null;
    this._boundOnScroll = this._onScroll.bind(this);
    this._onToolbarSlotChange = (e) => {
      const slot = e.target;
      this._hasToolbarItems = slot.assignedElements().length > 0;
    };
  }
  connectedCallback() {
    super.connectedCallback();
    this._connectPage();
    this._connectAnchor();
    if (!this.collapseAnchor) {
      this.classList.add("is-compact");
    }
  }
  disconnectedCallback() {
    super.disconnectedCallback();
    this._teardownAnchor();
  }
  updated(changed) {
    if (changed.has("collapseAnchor")) {
      this._teardownAnchor();
      if (this.collapseAnchor) {
        this._connectAnchor();
      } else {
        this.classList.add("is-compact");
      }
    }
  }
  _connectPage() {
    let el = this;
    while (el) {
      if (el.tagName.toLowerCase() === "ndd-page") {
        this._pageElement = el;
        return;
      }
      el = el.parentElement ?? (el.getRootNode() instanceof ShadowRoot ? el.getRootNode().host : null);
    }
  }
  _connectAnchor() {
    if (!this.collapseAnchor) return;
    const root = this.getRootNode();
    this._anchorElement = root.getElementById?.(this.collapseAnchor) ?? root.querySelector(`#${this.collapseAnchor}`);
    if (!this._anchorElement) return;
    const page = this._pageElement;
    this._activeScrollTarget = page ? page.scrollTarget : window;
    this._activeScrollTarget.addEventListener("scroll", this._boundOnScroll, { passive: true });
    this.updateComplete.then(() => this._onScroll());
  }
  _teardownAnchor() {
    this._activeScrollTarget?.removeEventListener("scroll", this._boundOnScroll);
    this._activeScrollTarget = null;
    this._anchorElement = null;
  }
  _onScroll() {
    if (!this._anchorElement || !this._pageElement) return;
    const pageTop = this._pageElement.getBoundingClientRect().top;
    const anchorTop = this._anchorElement.getBoundingClientRect().top;
    this.classList.toggle("is-compact", anchorTop <= pageTop);
  }
  _handleBack() {
    if (this.backHref) return;
    this.dispatchEvent(new CustomEvent("back", { bubbles: true, composed: true }));
  }
  _handleDismiss() {
    this.dispatchEvent(new CustomEvent("dismiss", { bubbles: true, composed: true }));
  }
  render() {
    return topTitleBarTemplate(this);
  }
};
NDDTopTitleBar.styles = topTitleBarStyles;
__decorateClass$5([
  property({ type: String })
], NDDTopTitleBar.prototype, "text", 2);
__decorateClass$5([
  property({ type: String, attribute: "supporting-text" })
], NDDTopTitleBar.prototype, "supportingText", 2);
__decorateClass$5([
  property({ type: String, attribute: "collapse-anchor" })
], NDDTopTitleBar.prototype, "collapseAnchor", 2);
__decorateClass$5([
  property({ type: String, attribute: "back-text" })
], NDDTopTitleBar.prototype, "backText", 2);
__decorateClass$5([
  property({ type: String, attribute: "back-href" })
], NDDTopTitleBar.prototype, "backHref", 2);
__decorateClass$5([
  property({ type: String, attribute: "dismiss-text" })
], NDDTopTitleBar.prototype, "dismissText", 2);
__decorateClass$5([
  state()
], NDDTopTitleBar.prototype, "_hasToolbarItems", 2);
NDDTopTitleBar = __decorateClass$5([
  customElement("ndd-top-title-bar")
], NDDTopTitleBar);
const nddTopTitleBar = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  get NDDTopTitleBar() {
    return NDDTopTitleBar;
  }
}, Symbol.toStringTag, { value: "Module" }));
const smMax = unsafeCSS(breakpoints.smMax);
const tabBarStyles = css`

	/* # Host */

	:host {
		display: inline-block;
		position: relative;
		-webkit-tap-highlight-color: transparent;
	}

	:host([hidden]) {
		display: none;
	}

	:host([full-width]) {
		display: block;
		width: 100%;
	}


	/* # Tab bar */

	.tab-bar {
		display: flex;
		flex-direction: row;
		justify-content: center;
		align-items: center;
	}

	.tab-bar__items {
		display: flex;
		flex-direction: row;
		justify-content: center;
		align-items: center;
		background-color: var(--semantics-buttons-neutral-tinted-background-color);
		border-radius: var(--semantics-controls-md-corner-radius);
		padding: 0 var(--primitives-space-2);
	}

	:host([compact]) .tab-bar__items {
		border-radius: var(--semantics-controls-lg-corner-radius);
	}


	/* # Focus */

	::slotted(ndd-tab-bar-item:focus-within) {
		position: relative;
		z-index: 1;
	}

`;
const tabBarItemStyles = css`

	/* # Host */

	:host {
		display: inline-block;
		position: relative;
		-webkit-tap-highlight-color: transparent;
	}

	:host([hidden]) {
		display: none;
	}


	/* # Item */

	.tab-bar__item {
		appearance: none;
		border: none;
		margin: 0;
		padding: 0;
		background: none;
		text-decoration: none;
		box-sizing: border-box;
		display: flex;
		position: relative;
		justify-content: center;
		align-items: center;
		font: var(--semantics-buttons-md-font);
		color: var(--semantics-buttons-neutral-tinted-content-color);
	}

	:host([variant='icon-and-text']) .tab-bar__item {
		flex-direction: row;
		gap: var(--primitives-space-4);
		padding: var(--primitives-space-8) var(--primitives-space-12);
		height: var(--semantics-controls-md-min-size);
	}

	:host([variant='text']) .tab-bar__item {
		flex-direction: row;
		padding: var(--primitives-space-8) var(--primitives-space-12);
		height: var(--semantics-controls-md-min-size);
	}

	:host([variant='icon']) .tab-bar__item {
		flex-direction: row;
		padding: var(--primitives-space-8);
		height: var(--semantics-controls-md-min-size);
	}

	:host([variant='compact']) .tab-bar__item {
		flex-direction: column;
		padding: var(--primitives-space-8);
		height: var(--semantics-controls-lg-min-size);
	}

	:host([responsive]) .tab-bar__item {
		@container layout-area (max-width: ${smMax}) {
			flex-direction: column;
			gap: 0;
			padding: var(--primitives-space-8);
			height: var(--semantics-controls-lg-min-size);
		}
	}

	:host([selected]) .tab-bar__item {
		color: var(--semantics-buttons-neutral-tinted-is-selected-content-color);
	}

	.tab-bar__item:focus-visible {
		outline: none;
	}


	/* # Indicator */

	.tab-bar__item::before {
		content: '';
		position: absolute;
		inset: var(--primitives-space-4) var(--primitives-space-2);
		border-radius: var(--primitives-corner-radius-sm);
		background-color: transparent;
		z-index: 0;
		pointer-events: none;
	}

	.tab-bar__item:hover::before {
		background-color: var(--semantics-buttons-neutral-tinted-is-hovered-background-color);
	}

	:host([selected]) .tab-bar__item::before {
		background-color: var(--semantics-buttons-neutral-tinted-is-selected-background-color);

		@media (forced-colors: active) {
			background-color: Highlight;
		}
	}


	/* # Focus */

	.tab-bar__item:focus-visible::before {
		box-shadow: var(--semantics-focus-ring-box-shadow);
		outline: var(--semantics-focus-ring-outline);
	}


	/* # Icon */

	.tab-bar__item-icon {
		display: flex;
		align-items: center;
		justify-content: center;
		position: relative;
		z-index: 1;
		flex-shrink: 0;
		width: var(--primitives-space-24);
		height: var(--primitives-space-24);
	}

	:host([variant='text']) .tab-bar__item-icon {
		display: none;
	}

	::slotted([slot='icon']) {
		display: block;
		width: 100%;
		height: 100%;
	}


	/* # Label */

	.tab-bar__item-text {
		position: relative;
		z-index: 1;
	}

	:host([variant='compact']) .tab-bar__item-text {
		font: var(--primitives-font-body-xxs-bold-flat);
	}

	:host([variant='icon']) .tab-bar__item-text {
		display: none;
	}

	:host([responsive]) .tab-bar__item-text {
		@container layout-area (max-width: ${smMax}) {
			font: var(--primitives-font-body-xxs-bold-flat);
		}
	}

`;
function tabBarTemplate(component) {
  const label = component.accessibleLabel || "Tabs";
  const isNavigation = component.navigation;
  const itemsContainer = html`
		<div class="tab-bar__items"
			role=${isNavigation ? nothing : "tablist"}
			aria-label=${isNavigation ? nothing : label}
		>
			<slot @slotchange=${component._onSlotChange}></slot>
		</div>
	`;
  if (isNavigation) {
    return html`
			<nav class="tab-bar" aria-label=${label}>
				${itemsContainer}
			</nav>
		`;
  }
  return html`
		<div class="tab-bar">
			${itemsContainer}
		</div>
	`;
}
function tabBarItemTemplate(component) {
  const safeHref = sanitizeUrl(component.href);
  const isLink = Boolean(safeHref);
  const isNavigation = component._navigation;
  const tabindex = component.selected || component._isFallbackFocusable ? "0" : "-1";
  const isIconVariant = component._effectiveVariant === "icon";
  const iconLabel = isIconVariant ? component.text || nothing : nothing;
  const content = html`
		<span class="tab-bar__item-icon" aria-hidden="true">
			<slot name="icon" @slotchange=${component._onIconSlotChange}></slot>
		</span>
		<span class="tab-bar__item-text">
			${component.text}
		</span>
	`;
  let result;
  if (isLink) {
    result = html`
			<a class="tab-bar__item"
				href=${safeHref}
				role=${isNavigation ? nothing : "tab"}
				aria-current=${isNavigation && component.selected ? "page" : nothing}
				aria-selected=${!isNavigation ? component.selected ? "true" : "false" : nothing}
				aria-label=${iconLabel}
				tabindex=${tabindex}
				@click=${component._handleClick}
			>${content}</a>
		`;
  } else {
    result = html`
			<button class="tab-bar__item"
				type="button"
				role="tab"
				aria-selected=${component.selected ? "true" : "false"}
				aria-label=${iconLabel}
				tabindex=${tabindex}
				@click=${component._handleClick}
			>${content}</button>
		`;
  }
  if (isIconVariant && component.text) {
    return html`<ndd-tooltip text=${component.text}>${result}</ndd-tooltip>`;
  }
  return result;
}
var __defProp$4 = Object.defineProperty;
var __getOwnPropDesc$4 = Object.getOwnPropertyDescriptor;
var __decorateClass$4 = (decorators, target, key, kind) => {
  var result = kind > 1 ? void 0 : kind ? __getOwnPropDesc$4(target, key) : target;
  for (var i = decorators.length - 1, decorator; i >= 0; i--)
    if (decorator = decorators[i])
      result = (kind ? decorator(target, key, result) : decorator(result)) || result;
  if (kind && result) __defProp$4(target, key, result);
  return result;
};
let NDDTabBarItem = class extends LitElement {
  constructor() {
    super(...arguments);
    this.selected = false;
    this.href = "";
    this.compact = false;
    this.responsive = false;
    this._groupVariant = "";
    this._authorVariant = "";
    this.text = "";
    this._hasIcon = false;
    this._navigation = false;
    this._isFallbackFocusable = false;
  }
  get _effectiveVariant() {
    if (this.compact) return "compact";
    if (this._authorVariant) return this._authorVariant;
    if (this._groupVariant) return this._groupVariant;
    if (this.text && this._hasIcon) return "icon-and-text";
    if (this.text) return "text";
    return "icon";
  }
  connectedCallback() {
    super.connectedCallback();
    this.setAttribute("role", "none");
    const attr = this.getAttribute("variant");
    if (attr === "text" || attr === "icon" || attr === "icon-and-text") {
      this._authorVariant = attr;
    }
  }
  updated() {
    this.setAttribute("variant", this._effectiveVariant);
  }
  focus(options) {
    this.shadowRoot?.querySelector(".tab-bar__item")?.focus(options);
  }
  _onIconSlotChange(e) {
    const slot = e.target;
    this._hasIcon = slot.assignedElements({ flatten: true }).length > 0;
  }
  _handleClick(event) {
    if (!sanitizeUrl(this.href)) {
      event.preventDefault();
    }
    this.dispatchEvent(new CustomEvent("select", {
      bubbles: true,
      composed: true,
      detail: { item: this }
    }));
  }
  render() {
    return tabBarItemTemplate(this);
  }
};
NDDTabBarItem.styles = tabBarItemStyles;
__decorateClass$4([
  property({ type: Boolean, reflect: true })
], NDDTabBarItem.prototype, "selected", 2);
__decorateClass$4([
  property({ type: String })
], NDDTabBarItem.prototype, "href", 2);
__decorateClass$4([
  property({ type: Boolean, reflect: true })
], NDDTabBarItem.prototype, "compact", 2);
__decorateClass$4([
  property({ type: Boolean, reflect: true })
], NDDTabBarItem.prototype, "responsive", 2);
__decorateClass$4([
  property({ type: String })
], NDDTabBarItem.prototype, "_groupVariant", 2);
__decorateClass$4([
  property({ type: String })
], NDDTabBarItem.prototype, "text", 2);
__decorateClass$4([
  state()
], NDDTabBarItem.prototype, "_hasIcon", 2);
__decorateClass$4([
  state()
], NDDTabBarItem.prototype, "_navigation", 2);
__decorateClass$4([
  state()
], NDDTabBarItem.prototype, "_isFallbackFocusable", 2);
NDDTabBarItem = __decorateClass$4([
  customElement("ndd-tab-bar-item")
], NDDTabBarItem);
let NDDTabBar = class extends LitElement {
  constructor() {
    super(...arguments);
    this.compact = false;
    this.responsive = false;
    this.fullWidth = false;
    this.variant = "";
    this.navigation = false;
    this.accessibleLabel = "";
    this._hasCustomLabel = false;
    this._handleItemSelect = (event) => {
      event.stopPropagation();
      const items = this._getItems();
      items.forEach((item) => {
        item.selected = item === event.detail.item;
      });
      this.dispatchEvent(new CustomEvent("tabchange", {
        bubbles: true,
        composed: true,
        detail: event.detail
      }));
    };
    this._handleKeyDown = (event) => {
      const items = this._getItems();
      if (items.length === 0) return;
      const currentIndex = items.findIndex(
        (item) => item === event.target || item.contains(event.target)
      );
      let newIndex = -1;
      switch (event.key) {
        case "ArrowLeft":
          event.preventDefault();
          newIndex = currentIndex > 0 ? currentIndex - 1 : items.length - 1;
          break;
        case "ArrowRight":
          event.preventDefault();
          newIndex = currentIndex < items.length - 1 ? currentIndex + 1 : 0;
          break;
        case "Home":
          event.preventDefault();
          newIndex = 0;
          break;
        case "End":
          event.preventDefault();
          newIndex = items.length - 1;
          break;
        default:
          return;
      }
      if (newIndex >= 0 && newIndex < items.length) {
        items[newIndex].focus();
        if (!this.navigation) {
          items.forEach((item) => {
            item.selected = item === items[newIndex];
          });
          this.dispatchEvent(new CustomEvent("tabchange", {
            bubbles: true,
            composed: true,
            detail: { item: items[newIndex] }
          }));
        }
      }
    };
  }
  connectedCallback() {
    super.connectedCallback();
    this.addEventListener("select", this._handleItemSelect);
    this.addEventListener("keydown", this._handleKeyDown);
  }
  disconnectedCallback() {
    super.disconnectedCallback();
    this.removeEventListener("select", this._handleItemSelect);
    this.removeEventListener("keydown", this._handleKeyDown);
  }
  firstUpdated() {
    this._hasCustomLabel = Boolean(this.accessibleLabel);
    this._syncItems();
  }
  updated(changedProperties) {
    if (changedProperties.has("compact") || changedProperties.has("responsive") || changedProperties.has("variant") || changedProperties.has("navigation")) {
      this._syncItems();
    }
  }
  _getItems() {
    const slot = this.shadowRoot?.querySelector("slot");
    if (!slot) return [];
    return slot.assignedElements().filter(
      (el) => el.tagName.toLowerCase() === "ndd-tab-bar-item"
    );
  }
  _syncItems() {
    const items = this._getItems();
    items.forEach((item) => {
      item.compact = this.compact;
      item.responsive = this.responsive;
      item._groupVariant = this.variant;
      item._navigation = this.navigation;
    });
    const hasSelected = items.some((item) => item.selected);
    const firstItem = items[0] ?? null;
    items.forEach((item) => {
      item._isFallbackFocusable = !hasSelected && item === firstItem;
    });
  }
  _onSlotChange() {
    this._syncItems();
  }
  render() {
    return tabBarTemplate(this);
  }
};
NDDTabBar.styles = tabBarStyles;
__decorateClass$4([
  property({ type: Boolean, reflect: true })
], NDDTabBar.prototype, "compact", 2);
__decorateClass$4([
  property({ type: Boolean, reflect: true })
], NDDTabBar.prototype, "responsive", 2);
__decorateClass$4([
  property({ type: Boolean, reflect: true, attribute: "full-width" })
], NDDTabBar.prototype, "fullWidth", 2);
__decorateClass$4([
  property({ type: String, reflect: true })
], NDDTabBar.prototype, "variant", 2);
__decorateClass$4([
  property({ type: Boolean, reflect: true })
], NDDTabBar.prototype, "navigation", 2);
__decorateClass$4([
  property({ type: String, attribute: "accessible-label" })
], NDDTabBar.prototype, "accessibleLabel", 2);
NDDTabBar = __decorateClass$4([
  customElement("ndd-tab-bar")
], NDDTabBar);
const documentTabBarStyles = css`

	/* # Host */

	:host {
		display: block;
		position: relative;
		--_drag-clone-top: 0px;
		--_drag-clone-left: 0px;
		--_drag-clone-width: 0px;
		--_drag-clone-height: 0px;
		--_drag-clone-opacity: 0.95;
		--_drag-clone-z-index: 100;
		--_short-text-threshold: 200px;
		--_item-min-width: 100px;
		--_overflow-button-reserve: 52px; /* Used for overflowButtonReserve. Overflow button width + spacing */
		-webkit-tap-highlight-color: transparent;
	}

	:host([hidden]) {
		display: none;
	}


	/* # Document tab bar */

	.document-tab-bar {
		display: flex;
		flex-direction: row;
		align-items: center;
		gap: var(--primitives-space-8);
	}

	.document-tab-bar__items {
		display: flex;
		flex-direction: row;
		align-items: center;
		gap: var(--primitives-space-8);
		flex-grow: 1;
		flex-shrink: 1;
		flex-basis: 0;
		min-width: 0;
	}

	::slotted(ndd-document-tab-bar-item) {
		flex-grow: 1;
		flex-shrink: 1;
		flex-basis: 0;
		min-width: var(--_item-min-width);
	}

	::slotted(ndd-document-tab-bar-item[hidden]) {
		display: none;
	}

	.document-tab-bar__items.is-measuring slot {
		flex-grow: 0;
	}

	.document-tab-bar__overflow {
		flex-grow: 0;
		flex-shrink: 0;
	}

	.document-tab-bar__overflow.is-hidden {
		display: none;
	}

	.document-tab-bar__end {
		display: flex;
		flex-direction: row;
		align-items: center;
		gap: var(--primitives-space-8);
		flex-grow: 0;
		flex-shrink: 0;
	}

	.document-tab-bar__end[hidden] {
		display: none;
	}


	/* # Focus */

	::slotted(ndd-document-tab-bar-item:focus-within) {
		position: relative;
		z-index: 4;
	}


	/* # Drag states */

	::slotted(ndd-document-tab-bar-item.is-dragging) {
		display: none;
	}


	/* # Drag placeholder */

	::slotted(.ndd-document-tab-bar-drag-placeholder) {
		box-sizing: border-box;
		background-color: var(--semantics-buttons-neutral-tinted-background-color);
		pointer-events: none;
		border-radius: var(--semantics-controls-md-corner-radius);
		height: var(--semantics-controls-md-min-size);
		flex-grow: 1;
		flex-shrink: 1;
		flex-basis: 0;
		min-width: var(--_item-min-width);
		opacity: var(--primitives-opacity-dragging);
	}


	/* # Drag clone */

	.document-tab-bar__drag-clone {
		position: absolute;
		top: var(--_drag-clone-top);
		left: var(--_drag-clone-left);
		width: var(--_drag-clone-width);
		height: var(--_drag-clone-height);
		display: flex;
		flex-direction: row;
		align-items: stretch;
		pointer-events: none;
		opacity: var(--_drag-clone-opacity);
		border-radius: var(--semantics-controls-md-corner-radius);
		background: var(--semantics-buttons-neutral-tinted-background-color);
		z-index: var(--_drag-clone-z-index);
		overflow: hidden;
		cursor: grabbing;
	}

	.document-tab-bar__drag-clone .document-tab-bar__item {
		width: 100%;
		height: 100%;
		box-sizing: border-box;
		position: relative;
	}

	.document-tab-bar__drag-clone .document-tab-bar__item-tab {
		display: flex;
		flex-direction: column;
		justify-content: center;
		width: 100%;
		height: 100%;
		min-width: 0;
		border-radius: var(--semantics-controls-md-corner-radius);
		padding-block: var(--primitives-space-6);
		padding-inline-start: var(--primitives-space-10);
		padding-inline-end: calc(var(--semantics-controls-sm-min-size) + var(--primitives-space-6) * 2);
		box-sizing: border-box;
		overflow: hidden;
	}

	.document-tab-bar__drag-clone .document-tab-bar__item-text {
		font: var(--components-document-tab-bar-tab-title-font);
		color: var(--semantics-buttons-neutral-tinted-content-color);
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.document-tab-bar__drag-clone.is-selected .document-tab-bar__item-tab {
		background-color: var(--semantics-buttons-neutral-tinted-is-selected-background-color);
	}

	.document-tab-bar__drag-clone.is-selected .document-tab-bar__item-text,
	.document-tab-bar__drag-clone.is-selected .document-tab-bar__item-supporting-text {
		color: var(--semantics-buttons-neutral-tinted-is-selected-content-color);
	}

	.document-tab-bar__drag-clone .document-tab-bar__item-supporting-text {
		font: var(--primitives-font-body-xs-regular-flat);
		color: var(--semantics-content-secondary-color);
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}


	/* # Announcers */

	.document-tab-bar__polite-announcer,
	.document-tab-bar__assertive-announcer {
		position: absolute;
		width: 1px;
		height: 1px;
		padding: 0;
		margin: -1px;
		overflow: hidden;
		clip-path: inset(50%);
		white-space: nowrap;
		border: 0;
	}

`;
const documentTabBarItemStyles = css`

	/* # Host */

	:host {
		display: block;
		min-width: 0;
		container-name: document-tab-bar;
		container-type: inline-size;
		touch-action: pan-y;
		-webkit-tap-highlight-color: transparent;
	}

	:host([hidden]) {
		display: none;
	}


	/* # Item */

	.document-tab-bar__item {
		position: relative;
		height: var(--semantics-controls-md-min-size);
		width: 100%;
		box-sizing: border-box;
	}


	/* # Item tab */

	.document-tab-bar__item-tab {
		appearance: none;
		border: none;
		margin: 0;
		text-align: left;
		display: flex;
		flex-direction: column;
		justify-content: center;
		width: 100%;
		height: 100%;
		min-width: 0;
		border-radius: var(--semantics-controls-md-corner-radius);
		padding-block: var(--primitives-space-6);
		padding-inline-start: var(--primitives-space-10);
		padding-inline-end: calc(var(--semantics-controls-sm-min-size) + var(--primitives-space-6));
		background-color: var(--semantics-buttons-neutral-tinted-background-color);
		box-sizing: border-box;
		overflow: hidden;
		text-decoration: none;
	}

	.document-tab-bar__item-tab:hover {
		background-color: var(--semantics-buttons-neutral-tinted-is-hovered-background-color);
	}

	.document-tab-bar__item-tab:active {
		background-color: var(--semantics-buttons-neutral-tinted-is-active-background-color);
	}

	:host([selected]) .document-tab-bar__item-tab {
		background-color: var(--semantics-buttons-neutral-tinted-is-selected-background-color);
	}

	:host([selected]) .document-tab-bar__item-tab:hover {
		background-color: var(--semantics-buttons-neutral-tinted-is-selected-background-color);
	}

	/* ## Focus */

	.document-tab-bar__item-tab:focus-visible {
		box-shadow: var(--semantics-focus-ring-box-shadow);
		outline: var(--semantics-focus-ring-outline);
	}


	/* # Item text wrappers */

	.document-tab-bar__item-normal {
		display: contents;

		@container document-tab-bar (max-width: 200px) {
			display: none;
		}
	}

	.document-tab-bar__item-short {
		display: none;

		@container document-tab-bar (max-width: 200px) {
			display: contents;
		}
	}


	/* # Item label */

	.document-tab-bar__item-text {
		padding-inline-end: var(--primitives-space-6);
		font: var(--components-document-tab-bar-tab-title-font);
		color: var(--semantics-buttons-neutral-tinted-content-color);
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	:host([selected]) .document-tab-bar__item-text {
		color: var(--semantics-buttons-neutral-tinted-is-selected-content-color);
	}

	.document-tab-bar__item-short-text {
		padding-inline-end: var(--primitives-space-6);
		font: var(--components-document-tab-bar-tab-title-font);
		color: var(--semantics-buttons-neutral-tinted-content-color);
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	:host([selected]) .document-tab-bar__item-short-text {
		color: var(--semantics-buttons-neutral-tinted-is-selected-content-color);
	}


	/* # Item supporting label */

	.document-tab-bar__item-supporting-text {
		padding-inline-end: var(--primitives-space-6);
		font: var(--primitives-font-body-xs-regular-flat);
		color: var(--semantics-content-secondary-color);
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	:host([selected]) .document-tab-bar__item-supporting-text {
		color: var(--semantics-buttons-neutral-tinted-is-selected-content-color);
	}

	.document-tab-bar__item-short-supporting-text {
		padding-inline-end: var(--primitives-space-6);
		font: var(--primitives-font-body-xs-regular-flat);
		color: var(--semantics-content-secondary-color);
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	:host([selected]) .document-tab-bar__item-short-supporting-text {
		color: var(--semantics-buttons-neutral-tinted-is-selected-content-color);
	}


	/* # Item dismiss button */

	.document-tab-bar__item-dismiss-button {
		position: absolute;
		right: var(--primitives-space-6);
		top: 50%;
		transform: translateY(-50%);
		appearance: none;
		border: none;
		background: none;
		margin: 0;
		padding: var(--primitives-space-4);
		display: flex;
		align-items: center;
		justify-content: center;
		width: var(--semantics-controls-sm-min-size);
		height: var(--semantics-controls-sm-min-size);
		border-radius: var(--semantics-controls-sm-corner-radius);
		color: var(--semantics-buttons-neutral-tinted-content-color);
	}

	.document-tab-bar__item-dismiss-button:hover {
		background-color: var(--primitives-color-neutral-150);
	}

	.document-tab-bar__item-dismiss-button:active {
		background-color: var(--primitives-color-neutral-200);
	}

	:host([selected]) .document-tab-bar__item-dismiss-button {
		color: var(--semantics-buttons-neutral-tinted-is-selected-content-color);
	}

	:host([selected]) .document-tab-bar__item-dismiss-button:hover {
		background-color: var(--primitives-color-accent-650);
	}

	:host([selected]) .document-tab-bar__item-dismiss-button:active {
		background-color: var(--primitives-color-accent-600);
	}

	.document-tab-bar__item-dismiss-button:focus-visible {
		box-shadow: var(--semantics-focus-ring-box-shadow);
		outline: var(--semantics-focus-ring-outline);
	}


	/* # Item dismiss icon */

	.document-tab-bar__item-dismiss-icon {
		display: flex;
		width: var(--primitives-space-16);
		height: var(--primitives-space-16);
	}

`;
function documentTabBarTemplate(component) {
  const hasOverflow = component._overflowCount > 0;
  const label = component.accessibleLabel || "Tabbladen";
  const isNavigation = component.navigation;
  const inner = html`
		<div class="document-tab-bar__items"
			role=${isNavigation ? nothing : "tablist"}
			aria-label=${isNavigation ? nothing : label}
		>
			<slot @slotchange=${component._onSlotChange}></slot>
		</div>
		<div class=${classMap({ "document-tab-bar__overflow": true, "is-hidden": !hasOverflow })}>
			<ndd-icon-button
				text=${component._t("components.document-tab-bar.overflow-action")}
				variant="neutral-tinted"
				icon="ellipsis"
				aria-haspopup="menu"
				aria-expanded=${component._menuOpen ? "true" : "false"}
				@click=${component._onOverflowButtonClick}
			>
				<!-- aria-controls omitted: ARIA IDREF attributes cannot cross shadow DOM boundaries.
					 aria-haspopup + aria-expanded provide sufficient AT context for WCAG 2.1 AA.
					 Restore aria-controls once ndd-menu moves into the shadow root or CSS Anchor
					 Positioning allows the menu to escape stacking context without document.body. -->
			</ndd-icon-button>
		</div>
		<div class="document-tab-bar__end" hidden>
			<slot name="end" @slotchange=${component._onEndSlotChange}></slot>
		</div>
	`;
  return html`
		${isNavigation ? html`<nav class="document-tab-bar" aria-label=${label}>${inner}</nav>` : html`<div class="document-tab-bar">${inner}</div>`}
		<div class="document-tab-bar__polite-announcer"
			role="status"
			aria-live="polite"
			aria-atomic="true"
		></div>
		<div class="document-tab-bar__assertive-announcer"
			role="alert"
			aria-live="assertive"
			aria-atomic="true"
		></div>
	`;
}
function documentTabBarItemTemplate(component) {
  const shortTextValue = component.shortText || component.text;
  const shortSupportingTextValue = component.shortSupportingText || component.supportingText;
  const isNavigation = component._navigation;
  const safeHref = sanitizeUrl(component.href);
  const isLink = Boolean(safeHref);
  const tabindex = component.selected || component._isFallbackFocusable ? "0" : "-1";
  const tooltipText = component.supportingText ? `${component.text} · ${component.supportingText}` : component.text;
  const tabContent = html`
		<span class="document-tab-bar__item-normal" aria-hidden="true">
			<span class="document-tab-bar__item-text">${component.text}</span>
			${component.supportingText ? html`<span class="document-tab-bar__item-supporting-text">${component.supportingText}</span>` : nothing}
		</span>
		<span class="document-tab-bar__item-short">
			<ndd-tooltip text=${tooltipText}>
				<span class="document-tab-bar__item-short-text">${shortTextValue}</span>
				${shortSupportingTextValue ? html`<span class="document-tab-bar__item-short-supporting-text">${shortSupportingTextValue}</span>` : nothing}
			</ndd-tooltip>
		</span>
	`;
  const tab = isLink ? html`<a class="document-tab-bar__item-tab"
				href=${safeHref}
				role=${isNavigation ? nothing : "tab"}
				aria-current=${isNavigation && component.selected ? "page" : nothing}
				aria-selected=${!isNavigation ? component.selected ? "true" : "false" : nothing}
				aria-label=${tooltipText}
				tabindex=${tabindex}
				@click=${component._handleClick}
			>${tabContent}</a>` : html`<button class="document-tab-bar__item-tab"
				type="button"
				role="tab"
				aria-selected=${component.selected ? "true" : "false"}
				aria-label=${tooltipText}
				tabindex=${tabindex}
				@click=${component._handleClick}
			>${tabContent}</button>`;
  return html`
		<div class="document-tab-bar__item">
			${tab}
			<button class="document-tab-bar__item-dismiss-button"
				aria-label=${component._dismissButtonAccessibilityLabel}
				tabindex=${component.selected || component._isFallbackFocusable ? "0" : "-1"}
				@click=${component._handleDismiss}
			>
				<span class="document-tab-bar__item-dismiss-icon">
					<ndd-icon name="dismiss"></ndd-icon>
				</span>
			</button>
		</div>
	`;
}
const nddDocumentTabBarTranslations = {
  "components.document-tab-bar.dismiss-action": "Sluit",
  "components.document-tab-bar.overflow-action": "Toon meer tabbladen",
  "components.document-tab-bar.drag-dropped-text": "Tabblad verplaatst naar positie {position}.",
  "components.document-tab-bar.drag-no-change-text": "Tabblad verplaatst. Positie ongewijzigd.",
  "components.document-tab-bar.drag-cancelled-text": "Slepen geannuleerd."
};
var __defProp$3 = Object.defineProperty;
var __getOwnPropDesc$3 = Object.getOwnPropertyDescriptor;
var __decorateClass$3 = (decorators, target, key, kind) => {
  var result = kind > 1 ? void 0 : kind ? __getOwnPropDesc$3(target, key) : target;
  for (var i = decorators.length - 1, decorator; i >= 0; i--)
    if (decorator = decorators[i])
      result = (kind ? decorator(target, key, result) : decorator(result)) || result;
  if (kind && result) __defProp$3(target, key, result);
  return result;
};
const DRAG_THRESHOLD = 5;
let NDDDocumentTabBarItem = class extends LitElement {
  constructor() {
    super(...arguments);
    this._id = `ndd-document-tab-bar-item-${NDDDocumentTabBarItem._counter++}`;
    this.selected = false;
    this.text = "";
    this.supportingText = "";
    this.shortText = "";
    this.shortSupportingText = "";
    this.href = "";
    this._dismissButtonAccessibilityLabel = "Sluit";
    this._isFallbackFocusable = false;
    this._navigation = false;
  }
  connectedCallback() {
    super.connectedCallback();
    this.setAttribute("role", "none");
  }
  focus(options) {
    this.shadowRoot?.querySelector(".document-tab-bar__item-tab")?.focus(options);
  }
  _handleClick() {
    this.dispatchEvent(new CustomEvent("select", {
      bubbles: true,
      composed: true,
      detail: { item: this }
    }));
  }
  _handleDismiss(event) {
    event.stopPropagation();
    this.dispatchEvent(new CustomEvent("dismiss", {
      bubbles: true,
      composed: true,
      detail: { item: this }
    }));
  }
  render() {
    return documentTabBarItemTemplate(this);
  }
};
NDDDocumentTabBarItem.styles = documentTabBarItemStyles;
NDDDocumentTabBarItem._counter = 0;
__decorateClass$3([
  property({ type: Boolean, reflect: true })
], NDDDocumentTabBarItem.prototype, "selected", 2);
__decorateClass$3([
  property({ type: String, attribute: "text" })
], NDDDocumentTabBarItem.prototype, "text", 2);
__decorateClass$3([
  property({ type: String, attribute: "supporting-text" })
], NDDDocumentTabBarItem.prototype, "supportingText", 2);
__decorateClass$3([
  property({ type: String, attribute: "short-text" })
], NDDDocumentTabBarItem.prototype, "shortText", 2);
__decorateClass$3([
  property({ type: String, attribute: "short-supporting-text" })
], NDDDocumentTabBarItem.prototype, "shortSupportingText", 2);
__decorateClass$3([
  property({ type: String })
], NDDDocumentTabBarItem.prototype, "href", 2);
__decorateClass$3([
  state()
], NDDDocumentTabBarItem.prototype, "_dismissButtonAccessibilityLabel", 2);
__decorateClass$3([
  state()
], NDDDocumentTabBarItem.prototype, "_isFallbackFocusable", 2);
__decorateClass$3([
  state()
], NDDDocumentTabBarItem.prototype, "_navigation", 2);
NDDDocumentTabBarItem = __decorateClass$3([
  customElement("ndd-document-tab-bar-item")
], NDDDocumentTabBarItem);
let NDDDocumentTabBar = class extends LitElement {
  constructor() {
    super(...arguments);
    this._id = `ndd-document-tab-bar-${NDDDocumentTabBar._counter++}`;
    this.accessibleLabel = "";
    this.navigation = false;
    this.translations = {};
    this._overflowCount = 0;
    this._menuOpen = false;
    this._menu = null;
    this._menuClosedAt = 0;
    this._resizeObserver = null;
    this._hasCustomLabel = false;
    this._mergedTranslations = { ...nddDocumentTabBarTranslations };
    this._draggingEl = null;
    this._placeholder = null;
    this._currentDropIndex = -1;
    this._pointerId = null;
    this._clone = null;
    this._cloneOffsetX = 0;
    this._tabBarRect = null;
    this._pendingDragItem = null;
    this._pendingDragStartX = 0;
    this._pendingPointerId = null;
    this._onPointerDown = (event) => {
      const path = event.composedPath();
      const onDismiss = path.some(
        (el) => el instanceof Element && el.classList?.contains("document-tab-bar__item-dismiss-button")
      );
      if (onDismiss) return;
      const item = path.find(
        (el) => el instanceof Element && el.tagName.toLowerCase() === "ndd-document-tab-bar-item"
      );
      if (!item || item.hidden) return;
      this._pendingDragItem = item;
      this._pendingDragStartX = event.clientX;
      this._pendingPointerId = event.pointerId;
      this.addEventListener("pointermove", this._onPointerMovePending);
      this.addEventListener("pointerup", this._onPointerUpPending);
      this.addEventListener("pointercancel", this._onPointerCancelPending);
    };
    this._onPointerMovePending = (event) => {
      if (event.pointerId !== this._pendingPointerId) return;
      if (!this._pendingDragItem) return;
      event.preventDefault();
      if (Math.abs(event.clientX - this._pendingDragStartX) < DRAG_THRESHOLD) return;
      const item = this._pendingDragItem;
      this._clearPendingDrag();
      event.preventDefault();
      this._startDrag(item, event.clientX);
      this._pointerId = event.pointerId;
      this.setPointerCapture(event.pointerId);
      this.addEventListener("pointermove", this._onPointerMove);
      this.addEventListener("pointerup", this._onPointerUp);
      this.addEventListener("pointercancel", this._onPointerCancel);
    };
    this._onPointerUpPending = () => {
      this._clearPendingDrag();
    };
    this._onPointerCancelPending = () => {
      this._clearPendingDrag();
    };
    this._lastPointerX = 0;
    this._onPointerMove = (event) => {
      if (!this._draggingEl || !this._placeholder) return;
      if (this._clone) {
        this._tabBarRect = this.getBoundingClientRect();
        this._clone.style.setProperty(
          "--_drag-clone-left",
          `${event.clientX - this._tabBarRect.left - this._cloneOffsetX}px`
        );
      }
      const draggingRight = event.clientX >= this._lastPointerX;
      this._lastPointerX = event.clientX;
      const visibleItems = this._getVisibleItems().filter((i) => i !== this._draggingEl);
      const pointerX = event.clientX;
      let toIndex = visibleItems.length;
      for (let i = 0; i < visibleItems.length; i++) {
        const inner = visibleItems[i].shadowRoot?.querySelector(".document-tab-bar__item") ?? visibleItems[i];
        const rect = inner.getBoundingClientRect();
        const threshold = draggingRight ? rect.left : rect.right;
        if (pointerX < threshold) {
          toIndex = i;
          break;
        }
      }
      this._setDropIndex(toIndex);
    };
    this._onPointerUp = () => {
      try {
        this._endDrag();
      } finally {
        document.documentElement.style.cursor = "";
      }
    };
    this._onPointerCancel = () => {
      try {
        this._cancelDrag();
      } finally {
        document.documentElement.style.cursor = "";
      }
    };
    this._handleItemSelect = (event) => {
      event.stopPropagation();
      const selectedItem = event.detail.item;
      this._getItems().forEach((item) => {
        item.selected = item === selectedItem;
      });
      this._syncFallbackFocusable();
      this.dispatchEvent(new CustomEvent("tabchange", {
        bubbles: true,
        composed: true,
        detail: event.detail
      }));
    };
    this._handleItemDismiss = (event) => {
      event.stopPropagation();
      const dismissedItem = event.detail.item;
      const items = this._getItems();
      let nextItem = null;
      if (dismissedItem.selected) {
        const index = items.indexOf(dismissedItem);
        for (let i = index + 1; i < items.length; i++) {
          if (!items[i].hidden) {
            nextItem = items[i];
            break;
          }
        }
        if (!nextItem) {
          for (let i = index - 1; i >= 0; i--) {
            if (!items[i].hidden) {
              nextItem = items[i];
              break;
            }
          }
        }
        if (nextItem) {
          nextItem.selected = true;
          nextItem.focus();
        }
        dismissedItem.selected = false;
      }
      const isLastItem = items.length === 1;
      this.dispatchEvent(new CustomEvent("tabdismiss", {
        bubbles: true,
        composed: true,
        detail: { item: dismissedItem, nextItem }
      }));
      if (isLastItem) {
        this.dispatchEvent(new CustomEvent("tabempty", { bubbles: true, composed: true }));
      }
      this._syncFallbackFocusable();
    };
    this._handleKeyDown = (event) => {
      const path = event.composedPath();
      const item = path.find(
        (el) => el instanceof Element && el.tagName.toLowerCase() === "ndd-document-tab-bar-item"
      );
      if (!item || item.hidden) return;
      const onDismiss = path.some(
        (el) => el instanceof Element && el.classList?.contains("document-tab-bar__item-dismiss-button")
      );
      if (onDismiss) return;
      if (event.shiftKey && (event.key === "ArrowLeft" || event.key === "ArrowRight")) {
        event.preventDefault();
        const visibleItems = this._getVisibleItems();
        const allItems = this._getItems();
        const currentIndex2 = visibleItems.indexOf(item);
        if (currentIndex2 === -1) return;
        const targetIndex = event.key === "ArrowLeft" ? currentIndex2 - 1 : currentIndex2 + 1;
        if (targetIndex < 0 || targetIndex >= visibleItems.length) return;
        const sibling = visibleItems[targetIndex];
        if (event.key === "ArrowLeft") {
          sibling.before(item);
        } else {
          sibling.after(item);
        }
        const fromIndex = allItems.indexOf(item);
        const newAllItems = this._getItems();
        const toIndex = newAllItems.indexOf(item);
        this.dispatchEvent(new CustomEvent("ndd-reorder", {
          detail: { fromIndex, toIndex },
          bubbles: true,
          composed: true
        }));
        this._announce(this._t("components.document-tab-bar.drag-dropped-text", { position: toIndex + 1 }));
        requestAnimationFrame(() => {
          item.shadowRoot?.querySelector(".document-tab-bar__item-tab")?.focus();
        });
        return;
      }
      const items = this._getVisibleItems();
      if (items.length === 0) return;
      const currentIndex = items.findIndex(
        (i) => i === event.target || i.contains(event.target)
      );
      let newIndex = -1;
      switch (event.key) {
        case "ArrowLeft":
          event.preventDefault();
          newIndex = currentIndex > 0 ? currentIndex - 1 : items.length - 1;
          break;
        case "ArrowRight":
          event.preventDefault();
          newIndex = currentIndex < items.length - 1 ? currentIndex + 1 : 0;
          break;
        case "Home":
          event.preventDefault();
          newIndex = 0;
          break;
        case "End":
          event.preventDefault();
          newIndex = items.length - 1;
          break;
        default:
          return;
      }
      if (newIndex >= 0) {
        items[newIndex].focus();
        if (!this.navigation) {
          this._getItems().forEach((item2) => {
            item2.selected = item2 === items[newIndex];
          });
          this.dispatchEvent(new CustomEvent("tabchange", {
            bubbles: true,
            composed: true,
            detail: { item: items[newIndex] }
          }));
        }
      }
    };
  }
  connectedCallback() {
    super.connectedCallback();
    this.addEventListener("select", this._handleItemSelect);
    this.addEventListener("dismiss", this._handleItemDismiss);
    this.addEventListener("keydown", this._handleKeyDown);
    this.addEventListener("pointerdown", this._onPointerDown);
    this._createMenu();
  }
  disconnectedCallback() {
    super.disconnectedCallback();
    this.removeEventListener("select", this._handleItemSelect);
    this.removeEventListener("dismiss", this._handleItemDismiss);
    this.removeEventListener("keydown", this._handleKeyDown);
    this.removeEventListener("pointerdown", this._onPointerDown);
    this._menu?.remove();
    this._menu = null;
    this._resizeObserver?.disconnect();
    this._resizeObserver = null;
    this._cancelDrag();
  }
  firstUpdated() {
    this._hasCustomLabel = Boolean(this.accessibleLabel);
    if (!this._hasCustomLabel) ;
    const container = this.shadowRoot?.querySelector(".document-tab-bar__items");
    if (container) {
      this._resizeObserver = new ResizeObserver(() => this._calculateOverflow());
      this._resizeObserver.observe(container);
    }
    this._syncMenuAnchor();
    requestAnimationFrame(() => this._calculateOverflow());
  }
  updated(changedProperties) {
    if (changedProperties.has("_overflowCount")) {
      this._applyItemVisibility();
      this._updateMenu();
    }
    if (changedProperties.has("translations")) {
      this._mergedTranslations = { ...nddDocumentTabBarTranslations, ...this.translations };
      this._propagateDismissLabel();
    }
    if (changedProperties.has("navigation")) {
      this._propagateNavigation();
    }
  }
  // — Items ——————————————————————————————————————————————————————————————————
  _getItems() {
    const slot = this.shadowRoot?.querySelector("slot:not([name])");
    if (!slot) return [];
    return slot.assignedElements().filter(
      (el) => el.tagName.toLowerCase() === "ndd-document-tab-bar-item" && !el.hasAttribute("data-ndd-placeholder")
    );
  }
  _getVisibleItems() {
    return this._getItems().filter((item) => !item.hidden);
  }
  _propagateNavigation() {
    this._getItems().forEach((item) => {
      item._navigation = this.navigation;
    });
  }
  _propagateDismissLabel() {
    const label = this._mergedTranslations["components.document-tab-bar.dismiss-action"];
    this._getItems().forEach((item) => {
      item._dismissButtonAccessibilityLabel = label;
    });
  }
  _syncFallbackFocusable() {
    const items = this._getVisibleItems();
    const hasSelected = items.some((item) => item.selected);
    const firstEnabled = items.find((item) => !item.hidden) ?? null;
    items.forEach((item) => {
      item._isFallbackFocusable = !hasSelected && item === firstEnabled;
    });
  }
  _onEndSlotChange(e) {
    const slot = e.target;
    const wrapper = slot.parentElement;
    wrapper.hidden = slot.assignedElements().length === 0;
  }
  _onSlotChange() {
    this._calculateOverflow();
    this._propagateDismissLabel();
    this._syncFallbackFocusable();
    this._propagateNavigation();
  }
  _applyItemVisibility() {
    const items = this._getItems();
    const visibleCount = items.length - this._overflowCount;
    items.forEach((item, index) => {
      item.hidden = index >= visibleCount;
    });
  }
  _clearPendingDrag() {
    this._pendingDragItem = null;
    this._pendingDragStartX = 0;
    this._pendingPointerId = null;
    this.removeEventListener("pointermove", this._onPointerMovePending);
    this.removeEventListener("pointerup", this._onPointerUpPending);
    this.removeEventListener("pointercancel", this._onPointerCancelPending);
  }
  // — Drag: keyboard ————————————————————————————————————————————————————————
  // — Drag: core ————————————————————————————————————————————————————————————
  _startDrag(item, clientX = 0) {
    const visibleItems = this._getVisibleItems();
    const visibleIndex = visibleItems.indexOf(item);
    if (visibleIndex === -1) return;
    this._draggingEl = item;
    this._currentDropIndex = visibleIndex;
    this._lastPointerX = clientX;
    const inner = item.shadowRoot?.querySelector(".document-tab-bar__item-tab") ?? item;
    const rect = inner.getBoundingClientRect();
    this._placeholder = document.createElement("div");
    this._placeholder.className = "ndd-document-tab-bar-drag-placeholder";
    this._placeholder.setAttribute("aria-hidden", "true");
    this._placeholder.setAttribute("data-ndd-placeholder", "");
    item.after(this._placeholder);
    item.classList.add("is-dragging");
    this._tabBarRect = this.getBoundingClientRect();
    this._cloneOffsetX = clientX - rect.left;
    document.documentElement.style.cursor = "grabbing";
    const threshold = parseFloat(getComputedStyle(item).getPropertyValue("--_short-text-threshold"));
    const useShort = rect.width < threshold;
    const displayTitle = useShort ? item.shortText || item.text : item.text;
    const displaySubtitle = useShort ? item.shortSupportingText || item.supportingText : item.supportingText;
    const cloneInner = document.createElement("div");
    cloneInner.className = "document-tab-bar__item";
    const cloneTab = document.createElement("div");
    cloneTab.className = "document-tab-bar__item-tab";
    const titleEl = document.createElement("span");
    titleEl.className = "document-tab-bar__item-text";
    titleEl.textContent = displayTitle;
    cloneTab.appendChild(titleEl);
    if (displaySubtitle) {
      const subtitleEl = document.createElement("span");
      subtitleEl.className = "document-tab-bar__item-supporting-text";
      subtitleEl.textContent = displaySubtitle;
      cloneTab.appendChild(subtitleEl);
    }
    cloneInner.appendChild(cloneTab);
    this._clone = document.createElement("div");
    this._clone.className = `document-tab-bar__drag-clone${item.selected ? " is-selected" : ""}`;
    this._clone.style.setProperty("--_drag-clone-left", `${clientX - this._tabBarRect.left - this._cloneOffsetX}px`);
    this._clone.style.setProperty("--_drag-clone-top", `${rect.top - this._tabBarRect.top}px`);
    this._clone.style.setProperty("--_drag-clone-width", `${rect.width}px`);
    this._clone.style.setProperty("--_drag-clone-height", `${rect.height}px`);
    this._clone.appendChild(cloneInner);
    this.renderRoot.appendChild(this._clone);
  }
  _setDropIndex(toIndex) {
    if (!this._placeholder || !this._draggingEl) return;
    const nonDragging = this._getVisibleItems().filter((i) => i !== this._draggingEl);
    const clamped = Math.max(0, Math.min(nonDragging.length, toIndex));
    this._currentDropIndex = clamped;
    this._placeholder.remove();
    if (nonDragging.length === 0) {
      this._draggingEl.after(this._placeholder);
      return;
    }
    if (clamped === 0) {
      nonDragging[0].before(this._placeholder);
    } else {
      nonDragging[clamped - 1].after(this._placeholder);
    }
  }
  _getDropIndex() {
    return this._currentDropIndex;
  }
  _endDrag() {
    if (!this._draggingEl || !this._placeholder) return;
    const allItems = this._getItems();
    const movedItem = this._draggingEl;
    const fromIndex = allItems.indexOf(movedItem);
    this._placeholder.replaceWith(movedItem);
    const newAllItems = this._getItems();
    const toIndex = newAllItems.indexOf(movedItem);
    this._cleanupDrag();
    if (fromIndex !== toIndex) {
      this.dispatchEvent(new CustomEvent("ndd-reorder", {
        detail: { fromIndex, toIndex },
        bubbles: true,
        composed: true
      }));
      this._announce(this._t("components.document-tab-bar.drag-dropped-text", { position: toIndex + 1 }));
      requestAnimationFrame(() => {
        const inner = movedItem.shadowRoot?.querySelector(".document-tab-bar__item-tab");
        inner?.focus();
      });
    } else {
      this._announce(this._t("components.document-tab-bar.drag-no-change-text"));
    }
  }
  _cancelDrag() {
    if (!this._draggingEl) return;
    this._cleanupDrag();
    this._announce(this._t("components.document-tab-bar.drag-cancelled-text"));
  }
  _cleanupDrag() {
    this._clearPendingDrag();
    this._draggingEl?.classList.remove("is-dragging");
    this._placeholder?.remove();
    this._clone?.remove();
    document.documentElement.style.cursor = "";
    if (this._pointerId !== null) {
      try {
        this.releasePointerCapture(this._pointerId);
      } catch (e) {
        if (!(e instanceof DOMException)) throw e;
      }
      this._pointerId = null;
    }
    this.removeEventListener("pointermove", this._onPointerMove);
    this.removeEventListener("pointerup", this._onPointerUp);
    this.removeEventListener("pointercancel", this._onPointerCancel);
    this._draggingEl = null;
    this._placeholder = null;
    this._clone = null;
    this._cloneOffsetX = 0;
    this._tabBarRect = null;
    this._lastPointerX = 0;
    this._currentDropIndex = -1;
  }
  // — i18n ——————————————————————————————————————————————————————————————————
  _t(key, vars) {
    let str = this._mergedTranslations[key];
    if (vars) {
      for (const [k, v] of Object.entries(vars)) {
        str = str.replace(`{${k}}`, String(v));
      }
    }
    return str;
  }
  // — Accessibility ——————————————————————————————————————————————————————————
  _announce(message, assertive = false) {
    const selector = assertive ? ".document-tab-bar__assertive-announcer" : ".document-tab-bar__polite-announcer";
    const region = this.shadowRoot?.querySelector(selector);
    if (!region) return;
    region.textContent = "";
    requestAnimationFrame(() => requestAnimationFrame(() => {
      region.textContent = message;
    }));
  }
  _calculateOverflow() {
    const items = this._getItems();
    const totalItems = items.length;
    if (totalItems === 0) {
      this._overflowCount = 0;
      return;
    }
    const container = this.shadowRoot?.querySelector(".document-tab-bar__items");
    if (!container) return;
    const containerWidth = container.offsetWidth;
    if (containerWidth === 0) return;
    const gap = parseFloat(getComputedStyle(container).gap) || 8;
    const firstItem = this._getItems()[0];
    const minItemWidth = firstItem ? parseFloat(getComputedStyle(firstItem).minWidth) || parseFloat(getComputedStyle(this).getPropertyValue("--_item-min-width")) : parseFloat(getComputedStyle(this).getPropertyValue("--_item-min-width"));
    const overflowButtonReserve = parseFloat(getComputedStyle(this).getPropertyValue("--_overflow-button-reserve"));
    const visible = Math.floor((containerWidth - overflowButtonReserve + gap) / (minItemWidth + gap));
    const newOverflowCount = Math.max(0, totalItems - Math.max(1, visible));
    if (newOverflowCount !== this._overflowCount) {
      this._overflowCount = newOverflowCount;
      this._ensureSelectedVisible();
    }
  }
  _ensureSelectedVisible() {
    const items = this._getItems();
    const visibleCount = items.length - this._overflowCount;
    const selectedIndex = items.findIndex((i) => i.selected);
    if (selectedIndex >= visibleCount && visibleCount > 0) {
      const lastVisible = items[visibleCount - 1];
      const selected = items[selectedIndex];
      this.insertBefore(selected, lastVisible);
    }
  }
  // — Overflow menu ——————————————————————————————————————————————————————————
  _updateMenu() {
    if (!this._menu) return;
    this._menu.innerHTML = "";
    const items = this._getItems();
    const visibleCount = items.length - this._overflowCount;
    items.slice(visibleCount).forEach((item) => {
      const menuItemText = item.supportingText ? `${item.text || "–"} · ${item.supportingText}` : item.text || "–";
      const menuItem = document.createElement("ndd-menu-item");
      menuItem.setAttribute("text", menuItemText);
      menuItem.addEventListener("click", () => {
        this._selectAndPromote(item);
        this._closeMenu();
      });
      this._menu.appendChild(menuItem);
    });
  }
  _selectAndPromote(targetItem) {
    const items = this._getItems();
    const visibleCount = items.length - this._overflowCount;
    items.forEach((item) => {
      item.selected = item === targetItem;
    });
    if (visibleCount > 0 && visibleCount < items.length) {
      const lastVisible = items[visibleCount - 1];
      this.insertBefore(targetItem, lastVisible);
    }
    this._applyItemVisibility();
    this._updateMenu();
    this.dispatchEvent(new CustomEvent("tabchange", {
      bubbles: true,
      composed: true,
      detail: { item: targetItem }
    }));
  }
  _createMenu() {
    if (this._menu) return;
    if (typeof document === "undefined") return;
    const menu = document.createElement("ndd-menu");
    menu.setAttribute("placement", "bottom-end");
    menu.id = `${this._id}-menu`;
    menu.addEventListener("toggle", (event) => {
      const open = event.newState === "open";
      this._menuOpen = open;
      if (!open) this._menuClosedAt = Date.now();
    });
    document.body.appendChild(menu);
    this._menu = menu;
  }
  _syncMenuAnchor() {
    if (!this._menu) return;
    const button = this.shadowRoot?.querySelector(".document-tab-bar__overflow ndd-icon-button");
    if (button) {
      this._menu.anchorElement = button;
    }
  }
  _closeMenu() {
    this._menu?.hidePopover?.();
  }
  _onOverflowButtonClick() {
    if (!this._menu) return;
    this._syncMenuAnchor();
    this._updateMenu();
    if (this._menuOpen) {
      this._menu.hidePopover?.();
    } else if (Date.now() - this._menuClosedAt > POPOVER_REOPEN_GUARD_MS) {
      this._menu.showPopover?.();
    }
  }
  render() {
    return documentTabBarTemplate(this);
  }
};
NDDDocumentTabBar.styles = documentTabBarStyles;
NDDDocumentTabBar._counter = 0;
__decorateClass$3([
  property({ type: String, attribute: "accessible-label" })
], NDDDocumentTabBar.prototype, "accessibleLabel", 2);
__decorateClass$3([
  property({ type: Boolean, reflect: true })
], NDDDocumentTabBar.prototype, "navigation", 2);
__decorateClass$3([
  property({ type: Object })
], NDDDocumentTabBar.prototype, "translations", 2);
__decorateClass$3([
  state()
], NDDDocumentTabBar.prototype, "_overflowCount", 2);
__decorateClass$3([
  state()
], NDDDocumentTabBar.prototype, "_menuOpen", 2);
NDDDocumentTabBar = __decorateClass$3([
  customElement("ndd-document-tab-bar")
], NDDDocumentTabBar);
const paginationStyles = css`


	/* # Host */

	:host {
		display: block;
		container-type: inline-size;
		-webkit-tap-highlight-color: transparent;
	}

	:host([hidden]) {
		display: none;
	}

	:host([full-width]) {
		display: flex;
		justify-content: center;
	}

	:host([disabled]) {
		opacity: var(--primitives-opacity-disabled);
		pointer-events: none;
	}


	/* # Container */

	.pagination {
		display: inline-flex;
		align-items: center;
		background-color: var(--semantics-buttons-neutral-tinted-background-color);
		border-radius: var(--semantics-controls-md-corner-radius);
	}


	/* # Page button */

	.pagination__page-button {
		appearance: none;
		border: none;
		background: transparent;
		display: inline-flex;
		align-items: center;
		justify-content: center;
		height: var(--semantics-controls-md-min-size);
		min-width: var(--semantics-controls-md-min-size);
		padding-block: var(--primitives-space-8);
		padding-inline: var(--primitives-space-12);
		font: var(--semantics-buttons-md-font);
		color: inherit;
		box-sizing: border-box;
		position: relative;
		margin: 0;
	}

	a.pagination__page-button {
		text-decoration: none;
	}

	.pagination__page-button:hover,
	.pagination__page-button:focus-visible {
		z-index: 1;
	}

	.pagination__page-button:focus-visible {
		outline: none;
	}

	.pagination__page-button.is-current {
		color: var(--semantics-buttons-neutral-tinted-is-selected-content-color);
	}


	/* ## Page button indicator */

	.pagination__page-button::before {
		content: '';
		position: absolute;
		inset: var(--primitives-space-4);
		border-radius: calc(var(--semantics-controls-md-corner-radius) - var(--primitives-space-4) / 2);
		background-color: transparent;
		pointer-events: none;
	}

	.pagination__page-button:hover:not(.is-current)::before {
		background-color: var(--semantics-buttons-neutral-tinted-is-hovered-background-color);
	}

	.pagination__page-button.is-current::before {
		background-color: var(--semantics-buttons-neutral-tinted-is-selected-background-color);
	}

	.pagination__page-button:focus-visible::before {
		box-shadow: var(--semantics-focus-ring-box-shadow);
		outline: var(--semantics-focus-ring-outline);
	}


	/* ## Page button text */

	.pagination__page-button-text {
		position: relative;
		z-index: 1;
		pointer-events: none;
	}


	/* # Ellipsis */

	.pagination__ellipsis {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		height: var(--semantics-controls-md-min-size);
		min-width: var(--semantics-controls-md-min-size);
		padding-block: var(--primitives-space-8);
		padding-inline: var(--primitives-space-12);
		font: var(--semantics-buttons-md-font);
		color: inherit;
		box-sizing: border-box;
		pointer-events: none;
	}


	/* # Divider */

	.pagination__divider {
		display: flex;
		align-items: center;
		justify-content: center;
		height: var(--semantics-controls-md-min-size);
		flex-shrink: 0;
	}

	.pagination__divider-line {
		width: var(--semantics-dividers-thickness);
		height: var(--semantics-buttons-md-divider-length);
		background-color: var(--semantics-buttons-neutral-tinted-divider-color);
	}


	/* # Select (compact fallback) */

	.pagination__select-wrapper {
		position: relative;
		display: inline-flex;
		align-items: center;
	}

	.pagination__select {
		appearance: none;
		border: none;
		background: transparent;
		height: var(--semantics-controls-md-min-size);
		padding-block: var(--primitives-space-8);
		padding-inline-start: var(--primitives-space-12);
		padding-inline-end: calc(var(--primitives-space-24) + var(--primitives-space-12));
		font: var(--semantics-buttons-md-font);
		color: inherit;
		box-sizing: border-box;
		margin: 0;
		position: relative;
		z-index: 1;
	}

	.pagination__select:focus-visible {
		box-shadow: var(--semantics-focus-ring-box-shadow);
		outline: var(--semantics-focus-ring-outline);
		border-radius: calc(var(--semantics-controls-md-corner-radius) - var(--primitives-space-4) / 2);
	}

	.pagination__select-picker-icon {
		position: absolute;
		inset-inline-end: var(--primitives-space-8);
		pointer-events: none;
		width: var(--primitives-space-24);
		height: var(--primitives-space-24);
	}


	/* # Responsive */

	.pagination__page-buttons {
		display: contents;
	}

	.pagination__compact {
		display: none;
	}

	@container (max-width: 400px) {
		.pagination__page-buttons {
			display: none;
		}

		.pagination__compact {
			display: contents;
		}
	}


	/* # High contrast */

	@media (forced-colors: active) {
		.pagination {
			border: 1px solid CanvasText;
		}

		.pagination__page-button.is-current {
			color: HighlightText;
		}

		.pagination__page-button.is-current::before {
			background-color: Highlight;
		}

		.pagination__page-button:focus-visible::before {
			outline: 2px solid CanvasText;
		}
	}
`;
function paginationTemplate(component) {
  const pages = component._getVisiblePages();
  const atFirst = component.current <= 1;
  const atLast = component.current >= component.total;
  const t = component._t.bind(component);
  const hasHref = !!component.hrefPattern;
  const isDisabled = component.disabled;
  const renderPageButton = (page) => {
    const isCurrent = page === component.current;
    const label = t("components.pagination.page-action", { page });
    if (hasHref) {
      return html`
				<a class="pagination__page-button ${isCurrent ? "is-current" : ""}"
					href=${!isDisabled ? component._hrefForPage(page) : nothing}
					aria-label=${label}
					aria-current=${isCurrent ? "page" : nothing}
					tabindex=${isDisabled ? -1 : nothing}
					aria-disabled=${isDisabled ? "true" : nothing}
					@click=${(e) => {
        e.preventDefault();
        component._goToPage(page);
      }}
				>
					<span class="pagination__page-button-text">${page}</span>
				</a>
			`;
    }
    return html`
			<button class="pagination__page-button ${isCurrent ? "is-current" : ""}"
				type="button"
				aria-label=${label}
				aria-current=${isCurrent ? "page" : nothing}
				?disabled=${isDisabled}
				@click=${() => component._goToPage(page)}
			>
				<span class="pagination__page-button-text">${page}</span>
			</button>
		`;
  };
  return html`
		<nav class="pagination"
			aria-label=${t("components.pagination.accessibility-label")}
		>
			<ndd-icon-button
				icon="chevron-left-small"
				text=${t("components.pagination.previous-action")}
				variant="neutral-tinted"
				?disabled=${isDisabled || atFirst}
				href=${hasHref && !isDisabled && !atFirst ? component._hrefForPage(component.current - 1) : nothing}
				@click=${(e) => {
    if (hasHref) e.preventDefault();
    component._goToPage(component.current - 1);
  }}
			></ndd-icon-button>
			<div class="pagination__divider" aria-hidden="true">
				<div class="pagination__divider-line"></div>
			</div>
			<div class="pagination__page-buttons">
				${pages.map(
    (page) => page === "ellipsis" ? html`<div class="pagination__ellipsis" aria-hidden="true">&hellip;</div>` : renderPageButton(page)
  )}
			</div>
			<div class="pagination__compact">
				<div class="pagination__select-wrapper">
					<select class="pagination__select"
						aria-label=${t("components.pagination.go-to-page-label")}
						?disabled=${isDisabled}
						@change=${(e) => component._goToPage(Number(e.target.value))}
					>
						${Array.from({ length: component.total }, (_, i) => i + 1).map((page) => html`
							<option value=${page} ?selected=${page === component.current}>${page} / ${component.total}</option>
						`)}
					</select>
					<div class="pagination__select-picker-icon">
						<ndd-icon name="chevron-up-down"></ndd-icon>
					</div>
				</div>
			</div>
			<div class="pagination__divider" aria-hidden="true">
				<div class="pagination__divider-line"></div>
			</div>
			<ndd-icon-button
				icon="chevron-right-small"
				text=${t("components.pagination.next-action")}
				variant="neutral-tinted"
				?disabled=${isDisabled || atLast}
				href=${hasHref && !isDisabled && !atLast ? component._hrefForPage(component.current + 1) : nothing}
				@click=${(e) => {
    if (hasHref) e.preventDefault();
    component._goToPage(component.current + 1);
  }}
			></ndd-icon-button>
		</nav>
	`;
}
const nddPaginationTranslations = {
  "components.pagination.accessibility-label": "Paginering",
  "components.pagination.previous-action": "Ga naar vorige pagina",
  "components.pagination.next-action": "Ga naar volgende pagina",
  "components.pagination.page-action": "Ga naar pagina {page}",
  "components.pagination.go-to-page-label": "Ga naar pagina"
};
var __defProp$2 = Object.defineProperty;
var __getOwnPropDesc$2 = Object.getOwnPropertyDescriptor;
var __decorateClass$2 = (decorators, target, key, kind) => {
  var result = kind > 1 ? void 0 : kind ? __getOwnPropDesc$2(target, key) : target;
  for (var i = decorators.length - 1, decorator; i >= 0; i--)
    if (decorator = decorators[i])
      result = (kind ? decorator(target, key, result) : decorator(result)) || result;
  if (kind && result) __defProp$2(target, key, result);
  return result;
};
let NDDPagination = class extends LitElement {
  constructor() {
    super(...arguments);
    this.current = 1;
    this.total = 1;
    this.disabled = false;
    this.fullWidth = false;
    this.hrefPattern = "";
    this.translations = {};
    this._mergedTranslations = { ...nddPaginationTranslations };
  }
  willUpdate(changed) {
    if (changed.has("translations")) {
      this._mergedTranslations = { ...nddPaginationTranslations, ...this.translations };
    }
  }
  _t(key, params) {
    let text = this._mergedTranslations[key] ?? key;
    if (params) {
      for (const [k, v] of Object.entries(params)) {
        text = text.replace(`{${k}}`, String(v));
      }
    }
    return text;
  }
  _getVisiblePages() {
    if (this.total <= 7) {
      return Array.from({ length: this.total }, (_, i) => i + 1);
    }
    if (this.current <= 3) {
      return [1, 2, 3, 4, "ellipsis", this.total - 1, this.total];
    }
    if (this.current === 4) {
      return [1, 2, 3, 4, 5, "ellipsis", this.total];
    }
    if (this.current >= this.total - 3) {
      return [1, "ellipsis", this.total - 4, this.total - 3, this.total - 2, this.total - 1, this.total];
    }
    return [1, "ellipsis", this.current - 1, this.current, this.current + 1, "ellipsis", this.total];
  }
  _hrefForPage(page) {
    const href = this.hrefPattern.replace("{page}", String(page));
    if (/^(https?:\/\/|[^:]+$)/.test(href)) return href;
    return "";
  }
  _goToPage(page) {
    if (this.disabled || page < 1 || page > this.total || page === this.current) {
      return;
    }
    const detail = { page };
    if (this.hrefPattern) {
      detail.href = this._hrefForPage(page);
    }
    const cancelable = !!this.hrefPattern;
    const event = new CustomEvent("page-change", {
      detail,
      bubbles: true,
      composed: true,
      cancelable
    });
    const proceeded = this.dispatchEvent(event);
    this.current = page;
    if (this.hrefPattern && proceeded && detail.href) {
      window.location.href = detail.href;
    }
  }
  render() {
    return paginationTemplate(this);
  }
};
NDDPagination.styles = paginationStyles;
__decorateClass$2([
  property({ type: Number, reflect: true })
], NDDPagination.prototype, "current", 2);
__decorateClass$2([
  property({ type: Number, reflect: true })
], NDDPagination.prototype, "total", 2);
__decorateClass$2([
  property({ type: Boolean, reflect: true })
], NDDPagination.prototype, "disabled", 2);
__decorateClass$2([
  property({ type: Boolean, reflect: true, attribute: "full-width" })
], NDDPagination.prototype, "fullWidth", 2);
__decorateClass$2([
  property({ type: String, attribute: "href-pattern" })
], NDDPagination.prototype, "hrefPattern", 2);
__decorateClass$2([
  property({ type: Object })
], NDDPagination.prototype, "translations", 2);
NDDPagination = __decorateClass$2([
  customElement("ndd-pagination")
], NDDPagination);
const mdMin = unsafeCSS(breakpoints.mdMin);
const modalDialogStyles = css`

	/* # Host */

	:host {
		display: contents;
		--_max-height: 90vh;
		--_animation-duration: 150ms;
		--_animation-easing: ease;
	}

	:host([hidden]) {
		display: none;
	}


	/* # Modal dialog */

	.modal-dialog {
		border: none;
		max-width: var(--primitives-area-480);
		width: calc(100% - var(--primitives-space-16) * 2);
		max-height: var(--_max-height);
		overflow-y: auto;
		background-color: var(--semantics-surfaces-background-color);
		border-radius: var(--semantics-overlays-corner-radius);
		box-shadow: var(--components-modal-dialog-box-shadow);
		box-sizing: border-box;

		padding: var(--primitives-space-16);

		@media (min-width: ${mdMin}) {
			padding: var(--primitives-space-24);
		}
	}

	.modal-dialog:not([open]) {
		display: none;
	}

	.modal-dialog:focus-visible {
		outline: none;
	}

	.modal-dialog.is-keyboard-focus:focus {
		box-shadow: var(--semantics-focus-ring-box-shadow), var(--components-modal-dialog-box-shadow);
		outline: var(--semantics-focus-ring-outline);
	}

	.modal-dialog::backdrop {
		background: var(--semantics-overlays-backdrop-color);
	}


	/* # Keyframes */

	@keyframes modal-dialog-in {
		from {
			opacity: 0;
			transform: scale(0.95);
		}
		to {
			opacity: 1;
			transform: scale(1);
		}
	}

	@keyframes modal-dialog-out {
		from {
			opacity: 1;
			transform: scale(1);
		}
		to {
			opacity: 0;
			transform: scale(0.95);
		}
	}

	.modal-dialog[open] {
		animation: modal-dialog-in var(--_animation-duration) var(--_animation-easing) both;
	}

	.modal-dialog.is-closing {
		animation: modal-dialog-out var(--_animation-duration) var(--_animation-easing) both;
	}


	/* # Reduced motion */

	@media (prefers-reduced-motion: reduce) {
		.modal-dialog[open],
		.modal-dialog.is-closing {
			animation: none;
		}
	}
`;
function modalDialogTemplate(component) {
  return html`
		<dialog class="modal-dialog"
			role=${component.variant === "alert" ? "alertdialog" : nothing}
			aria-label=${component.accessibleLabel || component.text || nothing}
			aria-modal="true"
			@click=${component._handleBackdropClick}
			@cancel=${component._handleCancel}
		>
			<ndd-inline-dialog
				variant=${component.variant || nothing}
				icon-name=${component.iconName || nothing}
				text=${component.text || nothing}
				supporting-text=${component.supportingText || nothing}
				heading-level="2"
			>
				<slot></slot>
				<slot slot="actions" name="actions"></slot>
			</ndd-inline-dialog>
		</dialog>
	`;
}
const inlineDialogStyles = css`

	/* # Host */

	:host {
		display: flex;
		justify-content: center;

		--_icon-color: var(--semantics-content-color);
	}

	:host([hidden]) {
		display: none;
	}

	:host([variant='alert']) {
		--_icon-color: var(--primitives-color-warning-350);
	}


	/* # Body */

	.inline-dialog__body {
		display: flex;
		flex-direction: column;
		align-items: center;
		flex-grow: 1;
		box-sizing: border-box;
		max-width: var(--primitives-area-480);
	}


	/* # Icon */

	.inline-dialog__icon {
		display: flex;
		align-items: center;
		justify-content: center;
		width: var(--primitives-space-48);
		height: var(--primitives-space-48);
		color: var(--_icon-color);
		flex-shrink: 0;
	}


	/* # Text */

	.inline-dialog__text {
		margin: 0;
		font: var(--primitives-font-body-md-bold-tight);
		color: var(--semantics-content-color);
		text-align: center;
	}

	.inline-dialog__text:focus-visible {
		box-shadow: none;
		outline: none;
	}


	/* # Supporting text */

	.inline-dialog__supporting-text {
		margin: 0;
		font: var(--primitives-font-body-sm-regular-tight);
		color: var(--semantics-content-color);
		text-align: center;
	}


	/* # Content */

	.inline-dialog__content {
		width: 100%;
	}

	.inline-dialog__content:not(:has(*)) {
		display: none;
	}


	/* # Actions */

	.inline-dialog__actions {
		width: 100%;
		padding-top: var(--primitives-space-16);
	}

	.inline-dialog__actions:not(:has(*)) {
		display: none;
	}
`;
function inlineDialogTemplate(component) {
  return html`
		<div class="inline-dialog__body">
			${component._resolvedIconName ? html`
				<div class="inline-dialog__icon">
					<ndd-icon name=${component._resolvedIconName}></ndd-icon>
				</div>
			` : nothing}
			${component.text ? html`
				${component.headingLevel === 1 ? html`<h1 class="inline-dialog__text">${component.text}</h1>` : component.headingLevel === 2 ? html`<h2 class="inline-dialog__text">${component.text}</h2>` : component.headingLevel === 3 ? html`<h3 class="inline-dialog__text">${component.text}</h3>` : component.headingLevel === 4 ? html`<h4 class="inline-dialog__text">${component.text}</h4>` : component.headingLevel === 5 ? html`<h5 class="inline-dialog__text">${component.text}</h5>` : component.headingLevel === 6 ? html`<h6 class="inline-dialog__text">${component.text}</h6>` : html`<p class="inline-dialog__text">${component.text}</p>`}
			` : nothing}
			${component.supportingText ? html`
				<p class="inline-dialog__supporting-text">${component.supportingText}</p>
			` : nothing}
			<div class="inline-dialog__content">
				<slot></slot>
			</div>
			<div class="inline-dialog__actions">
				<ndd-button-group orientation="vertical">
					<slot name="actions"></slot>
				</ndd-button-group>
			</div>
		</div>
	`;
}
var __defProp$1 = Object.defineProperty;
var __getOwnPropDesc$1 = Object.getOwnPropertyDescriptor;
var __decorateClass$1 = (decorators, target, key, kind) => {
  var result = kind > 1 ? void 0 : kind ? __getOwnPropDesc$1(target, key) : target;
  for (var i = decorators.length - 1, decorator; i >= 0; i--)
    if (decorator = decorators[i])
      result = (kind ? decorator(target, key, result) : decorator(result)) || result;
  if (kind && result) __defProp$1(target, key, result);
  return result;
};
let NDDInlineDialog = class extends LitElement {
  constructor() {
    super(...arguments);
    this.variant = "";
    this.iconName = "";
    this.text = "";
    this.supportingText = "";
    this.headingLevel = null;
  }
  get _resolvedIconName() {
    if (this.variant === "alert") return "alert";
    if (this.iconName) return this.iconName;
    return "";
  }
  render() {
    return inlineDialogTemplate(this);
  }
};
NDDInlineDialog.styles = inlineDialogStyles;
__decorateClass$1([
  property({ type: String, reflect: true })
], NDDInlineDialog.prototype, "variant", 2);
__decorateClass$1([
  property({ type: String, reflect: true, attribute: "icon-name" })
], NDDInlineDialog.prototype, "iconName", 2);
__decorateClass$1([
  property({ type: String, reflect: true })
], NDDInlineDialog.prototype, "text", 2);
__decorateClass$1([
  property({ type: String, reflect: true, attribute: "supporting-text" })
], NDDInlineDialog.prototype, "supportingText", 2);
__decorateClass$1([
  property({ type: Number, reflect: true, attribute: "heading-level" })
], NDDInlineDialog.prototype, "headingLevel", 2);
NDDInlineDialog = __decorateClass$1([
  customElement("ndd-inline-dialog")
], NDDInlineDialog);
var __defProp = Object.defineProperty;
var __getOwnPropDesc = Object.getOwnPropertyDescriptor;
var __decorateClass = (decorators, target, key, kind) => {
  var result = kind > 1 ? void 0 : kind ? __getOwnPropDesc(target, key) : target;
  for (var i = decorators.length - 1, decorator; i >= 0; i--)
    if (decorator = decorators[i])
      result = (kind ? decorator(target, key, result) : decorator(result)) || result;
  if (kind && result) __defProp(target, key, result);
  return result;
};
let NDDModalDialog = class extends LitElement {
  constructor() {
    super(...arguments);
    this.variant = "";
    this.iconName = "";
    this.text = "";
    this.supportingText = "";
    this.accessibleLabel = "";
    this._closing = false;
  }
  get _dialog() {
    return this.shadowRoot?.querySelector("dialog") ?? null;
  }
  show() {
    const dialog = this._dialog;
    if (!dialog || dialog.open) return;
    dialog.showModal();
    this._manageFocus();
    this.dispatchEvent(new CustomEvent("open", { bubbles: true, composed: true }));
  }
  _manageFocus() {
    if (this.querySelector("[autofocus]")) return;
    const dialog = this._dialog;
    if (!dialog) return;
    dialog.classList.toggle("is-keyboard-focus", isKeyboardMode());
    dialog.focus();
  }
  hide() {
    const dialog = this._dialog;
    if (!dialog || !dialog.open || this._closing) return;
    this._closing = true;
    dialog.classList.add("is-closing");
    dialog.addEventListener("animationend", () => {
      dialog.classList.remove("is-closing");
      this._closing = false;
      dialog.close();
      this.dispatchEvent(new CustomEvent("close", { bubbles: true, composed: true }));
    }, { once: true });
    requestAnimationFrame(() => {
      if (this._closing && getComputedStyle(dialog).animationName === "none") {
        dialog.classList.remove("is-closing");
        this._closing = false;
        dialog.close();
        this.dispatchEvent(new CustomEvent("close", { bubbles: true, composed: true }));
      }
    });
  }
  _handleBackdropClick(e) {
    if (e.target === this._dialog) this.hide();
  }
  _handleCancel(e) {
    e.preventDefault();
    this.hide();
  }
  render() {
    return modalDialogTemplate(this);
  }
};
NDDModalDialog.styles = modalDialogStyles;
__decorateClass([
  property({ type: String, reflect: true })
], NDDModalDialog.prototype, "variant", 2);
__decorateClass([
  property({ type: String, reflect: true, attribute: "icon-name" })
], NDDModalDialog.prototype, "iconName", 2);
__decorateClass([
  property({ type: String, reflect: true })
], NDDModalDialog.prototype, "text", 2);
__decorateClass([
  property({ type: String, reflect: true, attribute: "supporting-text" })
], NDDModalDialog.prototype, "supportingText", 2);
__decorateClass([
  property({ type: String, attribute: "accessible-label" })
], NDDModalDialog.prototype, "accessibleLabel", 2);
NDDModalDialog = __decorateClass([
  customElement("ndd-modal-dialog")
], NDDModalDialog);
export {
  NDDAppView,
  NDDBarSplitView,
  NDDBox,
  NDDButton,
  NDDButtonBar,
  NDDButtonGroup,
  NDDCell,
  NDDCheckbox,
  NDDCheckboxField,
  NDDCollection,
  NDDComboBox,
  NDDContainer,
  NDDDescriptionCell,
  NDDDivider,
  NDDDocumentTabBar,
  NDDDragHandleCell,
  NDDDropdown,
  NDDFormField,
  NDDFullBleedSection,
  NDDIcon,
  NDDIconButton,
  NDDIconCell,
  NDDInlineDialog,
  NDDList,
  NDDListItem,
  NDDMenu,
  NDDMenuBar,
  NDDMenuBarItem,
  NDDModalDialog,
  NDDNavigationSplitView,
  NDDNumberField,
  NDDOneHalfOneHalfSection,
  NDDOneThirdTwoThirdsSection,
  NDDPage,
  NDDPagination,
  NDDPasswordField,
  NDDRadioButton,
  NDDRadioButtonField,
  NDDRadioButtonGroup,
  NDDRichText,
  NDDSearchField,
  NDDSegmentedControl,
  NDDSheet,
  NDDSideBySideSplitView,
  NDDSimpleSection,
  NDDSkipLink,
  NDDSpacer,
  NDDSpacerCell,
  NDDSplitButton,
  NDDSplitViewPane,
  NDDStackedSplitView,
  NDDStepper,
  NDDSwitch,
  NDDSwitchField,
  NDDTabBar,
  NDDTextCell,
  NDDTextField,
  NDDTimelineTrackCell,
  NDDTitle,
  NDDTitleCell,
  NDDToggleButton,
  NDDToggleButtonGroup,
  NDDToken,
  NDDToolbar,
  NDDTooltip,
  NDDTopNavigationBar,
  NDDTopTitleBar,
  NDDTwoThirdsOneThirdSection
};
