// Global htmx configuration. Loaded right after htmx itself.
htmx.config.historyCacheSize = 0;
// Defense in depth next to the CSP: injected markup must not get htmx to
// request another origin, run swapped-in <script> tags or eval attribute code.
// CSP's script-src 'self' still allows a <script src> to any same-origin
// file, including the startpagina's JS, so allowScriptTags is the only guard
// there. Behaviour for swapped content loads from base.html and binds on
// htmx.onLoad instead.
htmx.config.selfRequestsOnly = true;
htmx.config.allowScriptTags = false;
htmx.config.allowEval = false;
