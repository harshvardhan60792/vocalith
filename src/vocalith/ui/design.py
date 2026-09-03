"""The premium visual layer: design tokens, typography, motion.

Everything here is self-contained -- fonts and anime.js are read from static/ and
inlined as base64/text directly into the page HTML (via head=/css= on gr.Blocks).
No CDN links, no runtime network calls: this app promises nothing leaves the
machine, and that promise extends to its own UI chrome, not just user audio.

Design direction (the brief: "stop looking like a generic AI-generated SaaS site"):
- No purple/blue gradient, no Inter-everywhere, no centered-hero-with-blob-illustration,
  no uniform rounded-card-with-soft-shadow grid, no emoji, no "Unlock the power of..." copy.
- Instead: a warm, confident, editorial palette (near-black + off-white + a single
  copper accent -- audio-equipment coded, not SaaS-dashboard coded), one distinctive
  serif for display moments (Fraunces) against a plain system-ui body face, thin
  1px borders instead of drop shadows, generous asymmetric whitespace, a subtle
  grain texture for depth, and small-caps tracked-out "eyebrow" labels -- a genuine
  editorial-site signature, not a generic AI-site one.
"""
from __future__ import annotations
import base64
from pathlib import Path

_STATIC = Path(__file__).parent / "static"


def _b64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("ascii")


def _font_face_css() -> str:
    serif_600 = _b64(_STATIC / "fonts" / "fraunces-600.woff2")
    serif_italic = _b64(_STATIC / "fonts" / "fraunces-500-italic.woff2")
    return f"""
@font-face {{
    font-family: 'Fraunces';
    font-style: normal;
    font-weight: 600;
    font-display: swap;
    src: url(data:font/woff2;base64,{serif_600}) format('woff2');
}}
@font-face {{
    font-family: 'Fraunces';
    font-style: italic;
    font-weight: 500;
    font-display: swap;
    src: url(data:font/woff2;base64,{serif_italic}) format('woff2');
}}
"""


def head_script() -> str:
    """anime.js (vendored, inlined -- no CDN) plus one small helper it powers:
    a satisfying pulse on the status dot when a generation finishes. Kept as an
    isolated, non-critical flourish -- the hero entrance is CSS-only (see CSS's
    vx-rise keyframes) after a JS-timing bug once left it permanently invisible."""
    anime_src = (_STATIC / "js" / "anime.min.js").read_text(encoding="utf-8")
    helper = """
window.vxPulse = function(selector) {
    if (!window.anime) return;
    var els = document.querySelectorAll(selector);
    if (!els.length) return;
    anime({ targets: els, scale: [1, 1.7, 1], duration: 650, easing: 'easeOutElastic(1, .6)' });
};
"""
    return f"<script>{anime_src}\n{helper}</script>"


def pulse_js(selector: str = ".vx-dot") -> str:
    """js= string for a Gradio .then() hook after a generate button's click resolves."""
    return f"() => {{ window.vxPulse && window.vxPulse('{selector}'); }}"


CSS = _font_face_css() + r"""
:root {
    --bg: #14120F;
    --bg-elevated: #1B1814;
    --bg-input: #201C17;
    --bg-input-focus: #241F19;
    --text: #F2ECE0;
    --text-dim: #A79E8C;
    --text-faint: #6F6656;
    --accent: #D98A4A;
    --accent-hover: #E9A164;
    --accent-ink: #1A1108;
    --border: #2C2822;
    --border-strong: #423C32;
    --serif: 'Fraunces', Georgia, 'Iowan Old Style', serif;
    --sans: -apple-system, 'Segoe UI Variable', 'Segoe UI', system-ui, 'Helvetica Neue', Arial, sans-serif;
    --radius: 8px;
    --radius-lg: 14px;
}

.gradio-container {
    background: var(--bg) !important;
    background-image:
        radial-gradient(ellipse 900px 500px at 15% -10%, rgba(217,138,74,0.10), transparent 60%),
        url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='120' height='120'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2' stitchTiles='stitch'/%3E%3CfeColorMatrix type='saturate' values='0'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.035'/%3E%3C/svg%3E") !important;
    color: var(--text) !important;
    font-family: var(--sans) !important;
    max-width: 980px !important;
}

body, .gradio-container * {
    font-family: var(--sans);
}

/* ---------- Hero ---------- */
@keyframes vx-rise {
    from { opacity: 0; transform: translateY(14px); }
    to   { opacity: 1; transform: translateY(0); }
}
/* CSS-driven entrance, not JS-driven: a JS timing hiccup or a blocked script must
   never be able to leave hero content permanently invisible -- it did, once,
   during development (anime.js ran before Gradio had mounted the DOM). Guaranteed
   animation belongs in CSS; anime.js is reserved below for a non-critical flourish. */
.vx-eyebrow {
    font-family: var(--sans);
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    color: var(--accent);
    margin: 0 0 10px 0;
    animation: vx-rise 0.5s cubic-bezier(.2,.8,.2,1) both;
}
.vx-hero h1 {
    font-family: var(--serif) !important;
    font-weight: 600 !important;
    font-size: 3.1rem !important;
    line-height: 1.05 !important;
    letter-spacing: -0.01em;
    color: var(--text) !important;
    margin: 0 0 14px 0 !important;
    animation: vx-rise 0.65s cubic-bezier(.2,.8,.2,1) 0.12s both;
}
.vx-hero .vx-tagline {
    font-family: var(--serif);
    font-style: italic;
    font-weight: 500;
    font-size: 1.22rem;
    color: var(--text-dim);
    max-width: 46ch;
    line-height: 1.5;
    margin: 0 0 4px 0;
    animation: vx-rise 0.55s cubic-bezier(.2,.8,.2,1) 0.26s both;
}
.vx-hero .vx-tagline em { color: var(--accent); font-style: italic; }

.vx-banner {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    font-family: var(--sans) !important;
    font-size: 0.82rem;
    color: var(--text-faint) !important;
    border: 1px solid var(--border);
    border-radius: 999px;
    padding: 5px 14px 5px 10px;
    margin-top: 18px;
    animation: vx-rise 0.45s cubic-bezier(.2,.8,.2,1) 0.38s both;
}
.vx-banner .vx-dot {
    width: 7px; height: 7px; border-radius: 50%;
    background: var(--accent);
    box-shadow: 0 0 0 3px rgba(217,138,74,0.18);
}
.vx-banner strong { color: var(--text); font-weight: 600; }

/* ---------- Tabs as an editorial nav, not default gradio pills ---------- */
[role="tablist"] {
    border-bottom: 1px solid var(--border) !important;
    gap: 28px !important;
    padding-bottom: 0 !important;
    margin: 40px 0 30px 0 !important;
    background: transparent !important;
}
[role="tab"] {
    font-family: var(--sans) !important;
    font-size: 0.92rem !important;
    font-weight: 500 !important;
    color: var(--text-faint) !important;
    background: transparent !important;
    border: none !important;
    border-bottom: 2px solid transparent !important;
    padding: 0 0 14px 0 !important;
    margin: 0 !important;
    border-radius: 0 !important;
    transition: color 0.2s ease, border-color 0.2s ease;
}
[role="tab"]:hover {
    color: var(--text) !important;
}
[role="tab"][aria-selected="true"] {
    color: var(--text) !important;
    border-bottom-color: var(--accent) !important;
}

/* ---------- Surfaces: thin borders instead of soft-shadow cards ---------- */
.gradio-container .block,
.gradio-container .form {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
}
label.svelte-1gfkn6j, .gr-form label, label {
    font-family: var(--sans) !important;
    font-size: 0.78rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.03em !important;
    text-transform: uppercase;
    color: var(--text-faint) !important;
}

input, textarea, select,
.gradio-container input[type="text"],
.gradio-container input[type="number"] {
    background: var(--bg-input) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius) !important;
    color: var(--text) !important;
    font-family: var(--sans) !important;
    transition: border-color 0.15s ease, background 0.15s ease;
}
input:focus, textarea:focus, select:focus {
    border-color: var(--accent) !important;
    background: var(--bg-input-focus) !important;
    box-shadow: 0 0 0 3px rgba(217,138,74,0.12) !important;
}

/* dropzones (audio/file upload) */
.gradio-container [data-testid="audio"] .wrap,
.gradio-container [data-testid="file"] .wrap {
    background: var(--bg-input) !important;
    border: 1px dashed var(--border-strong) !important;
    border-radius: var(--radius-lg) !important;
}

/* ---------- Buttons ---------- */
button.primary, .gradio-container button.primary {
    background: var(--accent) !important;
    color: var(--accent-ink) !important;
    border: none !important;
    border-radius: var(--radius) !important;
    font-weight: 600 !important;
    letter-spacing: 0.01em;
    box-shadow: none !important;
    transition: transform 0.15s cubic-bezier(.2,.9,.3,1.3), background 0.15s ease, box-shadow 0.15s ease;
}
button.primary:hover {
    background: var(--accent-hover) !important;
    transform: translateY(-1px);
    box-shadow: 0 6px 18px -6px rgba(217,138,74,0.45) !important;
}
button.primary:active { transform: translateY(0); }

button.secondary, .gradio-container button.secondary {
    background: transparent !important;
    color: var(--text) !important;
    border: 1px solid var(--border-strong) !important;
    border-radius: var(--radius) !important;
}
button.secondary:hover { border-color: var(--accent) !important; color: var(--accent) !important; }

/* ---------- Slider accent ---------- */
input[type="range"]::-webkit-slider-thumb { background: var(--accent) !important; }
.gradio-container [data-testid="slider"] .thumb { background: var(--accent) !important; }

/* progress bar accent */
.progress-bar, .meta-text-center, .generating {
    color: var(--accent) !important;
}

/* accordion */
.gradio-container .label-wrap {
    font-family: var(--sans) !important;
    color: var(--text-dim) !important;
}

/* footer note */
.vx-footnote {
    color: var(--text-faint) !important;
    font-size: 0.82rem;
    border-top: 1px solid var(--border);
    margin-top: 48px;
    padding-top: 18px;
}

/* Gradio's own default footer (API/branding links) -- undercuts a custom identity
   on a local, offline app with no meaningful public API surface to advertise. */
.gradio-container footer { display: none !important; }

/* Radio buttons (voice-mode picker etc.) -- default gray boxes read as an
   unstyled default; make the selected state legible against the accent system. */
.gradio-container fieldset [role="radiogroup"] label,
.gradio-container .wrap[role="radiogroup"] label {
    background: var(--bg-input) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius) !important;
    color: var(--text-dim) !important;
    transition: border-color 0.15s ease, color 0.15s ease;
}
.gradio-container fieldset [role="radiogroup"] label:has(input:checked),
.gradio-container .wrap[role="radiogroup"] label:has(input:checked) {
    border-color: var(--accent) !important;
    color: var(--text) !important;
    background: var(--bg-input-focus) !important;
}

::selection { background: rgba(217,138,74,0.35); }
::-webkit-scrollbar { width: 10px; height: 10px; }
::-webkit-scrollbar-track { background: var(--bg); }
::-webkit-scrollbar-thumb { background: var(--border-strong); border-radius: 8px; }
"""


