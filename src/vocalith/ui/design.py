"""The premium visual layer: design tokens, typography, motion.

Everything here is self-contained -- anime.js is read from static/ and inlined as
text directly into the page HTML (via head=/css= on gr.Blocks). No CDN links, no
runtime network calls: this app promises nothing leaves the machine, and that
promise extends to its own UI chrome, not just user audio.

Design direction, in order of how it evolved this session:
1. Dark mode, warm copper accent, serif display type -- "stop looking generic AI."
2. Neutral near-black + a single recording-light red -- "copper reads as coffee slop."
3. Light mode modeled on ElevenLabs' actual site -- "use platforms like that as the base."
4. This pass: back to dark, modeled directly on the Linear/Vercel/Raycast school of
   dark developer-tool design -- the most consistently cited "this is what premium
   dark SaaS looks like" reference class. Near-black background (not pure black),
   off-white text (not pure white), ONE indigo-violet accent used sparingly, subtle
   1px low-contrast borders instead of shadows, tight 8-10px rounded-rect shapes (not
   full pills -- that read as ElevenLabs-specific, not the broader dark-SaaS norm),
   generous negative space, small tracked-out uppercase labels. Every structural CSS
   fix found earlier in this session (the body.dark specificity collision, the
   background shorthand+longhand bug that silently dropped background-color, the
   floating file-type badge's own dark default, the dropdown wrap's own dark
   default, targeting Gradio's real `.selected` class on radio labels) carries
   forward unchanged -- those are correctness fixes, not style choices, and apply
   regardless of the palette on top of them.
"""
from __future__ import annotations

from pathlib import Path

_STATIC = Path(__file__).parent / "static"

# Broken into short adjacent string literals (Python auto-concatenates them) purely
# to keep every physical line under ruff's E501 limit -- this is one continuous data
# URI value, not multiple statements.
_NOISE_SVG = (
    "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='90' "
    "height='90'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' "
    "baseFrequency='0.9' numOctaves='2' stitchTiles='stitch'/%3E%3C/filter%3E"
    "%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.035'/%3E"
    "%3C/svg%3E"
)


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


CSS = r"""
:root {
    --vx-bg: #09090B;
    --vx-bg-elevated: #131316;
    --vx-bg-input: #17171B;
    --vx-bg-input-focus: #1B1B20;
    --vx-text: #EDEEF0;
    --vx-text-dim: #8A8F98;
    --vx-text-faint: #5C6066;
    --vx-accent: #5E6AD2;
    --vx-accent-hover: #7B85E8;
    --vx-accent-ink: #FFFFFF;
    --vx-border: #232327;
    --vx-border-strong: #3A3A40;
    --vx-ink: #EDEEF0;
    --vx-ink-hover: #FFFFFF;
    --vx-sans: -apple-system, 'Segoe UI Variable', 'Segoe UI', system-ui, 'Helvetica Neue', Arial, sans-serif;
    --vx-radius: 8px;
    --vx-radius-lg: 14px;
    --vx-pill: 999px;
}

/* Gradio adds a `dark` class to <body> when the OS prefers dark color-scheme, and
   its own dark-mode rule for .gradio-container has the same specificity as a plain
   `.gradio-container` selector -- so on a dark-preference OS, Gradio's rule silently
   won regardless of !important (same specificity ties broken by source order, and
   Gradio's own stylesheet loads first but its rule still matched second-fight-wins
   in testing). Matching `body.dark .gradio-container` explicitly guarantees this
   theme applies regardless of the user's OS light/dark preference -- deliberate:
   Vocalith's design is one fixed look, not an OS-following light/dark pair (yet). */
body.dark .gradio-container,
.gradio-container {
    /* background-color + background-image as separate longhands, NOT the `background`
       shorthand -- shorthand followed by a background-image override in the same rule
       silently dropped background-color from the serialized declaration entirely
       (verified via the live CSSOM, not a guess); this is the fix, not a style choice.
       Three layered radial gradients ("aurora" background, the Linear/Vercel signature
       ambient-glow technique) plus a fine noise/grain SVG overlay -- a single flat
       gradient on pure near-black read as bland; grain specifically is what keeps a
       dark flat surface from reading as an obviously-AI-generated too-clean gradient. */
    background-color: var(--vx-bg) !important;
    background-image:
        radial-gradient(ellipse 900px 500px at 88% -10%, rgba(94,106,210,0.16), transparent 60%),
        radial-gradient(ellipse 700px 460px at -8% 55%, rgba(140,94,210,0.09), transparent 62%),
        radial-gradient(ellipse 600px 380px at 60% 105%, rgba(94,180,210,0.05), transparent 60%),
        url("__VX_NOISE_SVG__") !important;
    background-repeat: no-repeat, no-repeat, no-repeat, repeat !important;
    color: var(--vx-text) !important;
    font-family: var(--vx-sans) !important;
    max-width: 980px !important;
}

body, .gradio-container * {
    font-family: var(--vx-sans);
}

/* ---------- Hero: bold geometric grotesk stand-in (heavy system sans), not serif -- */
@keyframes vx-rise {
    from { opacity: 0; transform: translateY(14px); }
    to   { opacity: 1; transform: translateY(0); }
}
.vx-eyebrow {
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--vx-accent);
    margin: 0 0 12px 0;
    animation: vx-rise 0.5s cubic-bezier(.2,.8,.2,1) both;
}
.vx-hero h1 {
    font-weight: 800 !important;
    font-size: 3.15rem !important;
    line-height: 1.03 !important;
    letter-spacing: -0.02em;
    color: var(--vx-ink) !important;
    margin: 0 0 16px 0 !important;
    animation: vx-rise 0.65s cubic-bezier(.2,.8,.2,1) 0.12s both;
}
.vx-hero .vx-tagline {
    font-weight: 400;
    font-size: 1.12rem;
    color: var(--vx-text-dim);
    max-width: 48ch;
    line-height: 1.55;
    margin: 0 0 4px 0;
    animation: vx-rise 0.55s cubic-bezier(.2,.8,.2,1) 0.26s both;
}
.vx-hero .vx-tagline em { color: var(--vx-text); font-style: normal; font-weight: 600; }

/* Needs !important: this project has repeatedly found Gradio's own CSS wins
   ties/specificity on plain-looking rules like `background` on generic elements
   (same class of bug as the body.dark collision documented above) -- without it,
   background-image silently stayed "none" while -webkit-text-fill-color still
   applied, making the headline's second line render fully invisible. */
.vx-gradient-text {
    background-image: linear-gradient(100deg,
        var(--vx-ink) 30%, var(--vx-accent-hover) 75%, var(--vx-accent) 100%) !important;
    -webkit-background-clip: text !important;
    background-clip: text !important;
    -webkit-text-fill-color: transparent !important;
}

.vx-banner {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    font-size: 0.82rem;
    color: var(--vx-text-dim) !important;
    background: var(--vx-bg-elevated);
    border: 1px solid var(--vx-border);
    border-radius: var(--vx-pill);
    padding: 6px 16px 6px 12px;
    margin-top: 20px;
    animation: vx-rise 0.45s cubic-bezier(.2,.8,.2,1) 0.38s both;
}
.vx-banner .vx-dot {
    width: 7px; height: 7px; border-radius: 50%;
    background: var(--vx-accent);
    box-shadow: 0 0 0 3px rgba(94,106,210,0.25);
}
.vx-banner strong { color: var(--vx-ink); font-weight: 700; }

/* ---------- Tabs: pill-segmented control, ElevenLabs' category-selector pattern --- */
[role="tablist"] {
    display: inline-flex !important;
    background: var(--vx-bg-elevated) !important;
    border: 1px solid var(--vx-border) !important;
    border-radius: 10px !important;
    padding: 4px !important;
    gap: 2px !important;
    margin: 40px 0 30px 0 !important;
    width: fit-content;
}
[role="tab"] {
    font-size: 0.9rem !important;
    font-weight: 600 !important;
    color: var(--vx-text-dim) !important;
    background: transparent !important;
    border: none !important;
    border-radius: 7px !important;
    padding: 8px 18px !important;
    margin: 0 !important;
    transition: color 0.15s ease, background 0.15s ease;
}
[role="tab"]:hover { color: var(--vx-text) !important; }
[role="tab"][aria-selected="true"] {
    color: var(--vx-text) !important;
    background: var(--vx-bg-input) !important;
    box-shadow: inset 0 0 0 1px var(--vx-border-strong);
}

/* ---------- Surfaces ---------- */
.gradio-container .block,
.gradio-container .form {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
}

/* The tab content area previously sat directly on the void background with nothing
   to anchor it -- everything read as loose fields floating in black. A single
   elevated glass panel per tab (subtle border + soft shadow + faint top highlight,
   the standard "raised card" language every dark-SaaS reference site uses) gives the
   working area an actual edge instead of bleeding into the page background. */
[role="tabpanel"] {
    background: linear-gradient(180deg, rgba(255,255,255,0.025), rgba(255,255,255,0) 40%),
        var(--vx-bg-elevated) !important;
    border: 1px solid var(--vx-border) !important;
    border-radius: var(--vx-radius-lg) !important;
    padding: 32px !important;
    box-shadow: 0 24px 60px -30px rgba(0,0,0,0.55), inset 0 1px 0 rgba(255,255,255,0.03) !important;
}
label.svelte-1gfkn6j, .gr-form label, label {
    font-size: 0.78rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.02em !important;
    text-transform: uppercase;
    color: var(--vx-text-dim) !important;
}

input, textarea, select,
.gradio-container input[type="text"],
.gradio-container input[type="number"] {
    background: var(--vx-bg-input) !important;
    border: 1px solid var(--vx-border-strong) !important;
    border-radius: var(--vx-radius) !important;
    color: var(--vx-text) !important;
    transition: border-color 0.15s ease, box-shadow 0.15s ease;
}
input:focus, textarea:focus, select:focus {
    border-color: var(--vx-accent) !important;
    box-shadow: 0 0 0 3px rgba(94,106,210,0.20) !important;
}

/* Floating file-type badge on Audio/File components (the small label with an icon
   pinned over the drop zone's top-left corner) -- a different component from the
   plain <label> above, with its own dark background by default. */
.gradio-container [data-testid="block-label"] {
    background: var(--vx-bg-elevated) !important;
    border: 1px solid var(--vx-border) !important;
    color: var(--vx-text-dim) !important;
}

/* Dropdown/combobox wrapper -- Gradio's own dark-mode default for this element's
   `.wrap` div doesn't get caught by the container-level override above (it's a
   nested component with its own background), so it stayed dark gray. Generic catch
   for any such leftover "wrap" surface; the more specific dropzone rule right after
   wins for audio/file uploads via equal specificity + later source order. */
.gradio-container .wrap {
    background: var(--vx-bg-input) !important;
}

/* dropzones (audio/file upload) */
.gradio-container [data-testid="audio"] .wrap,
.gradio-container [data-testid="file"] .wrap {
    background: var(--vx-bg-elevated) !important;
    border: 1.5px dashed var(--vx-border-strong) !important;
    border-radius: var(--vx-radius-lg) !important;
}

/* ---------- Buttons: gradient primary with a soft ambient glow, not flat fill --- */
button.primary, .gradio-container button.primary {
    background: linear-gradient(135deg, var(--vx-accent-hover), var(--vx-accent) 60%) !important;
    color: var(--vx-accent-ink) !important;
    border: none !important;
    border-radius: var(--vx-radius) !important;
    font-weight: 600 !important;
    letter-spacing: 0.01em;
    box-shadow: 0 8px 24px -10px rgba(94,106,210,0.45) !important;
    transition: transform 0.15s cubic-bezier(.2,.9,.3,1.3), box-shadow 0.15s ease, filter 0.15s ease;
}
button.primary:hover {
    filter: brightness(1.08);
    transform: translateY(-1px);
    box-shadow: 0 10px 28px -8px rgba(94,106,210,0.65) !important;
}
button.primary:active { transform: translateY(0); filter: brightness(0.97); }

button.secondary, .gradio-container button.secondary {
    background: var(--vx-bg-elevated) !important;
    color: var(--vx-text) !important;
    border: 1px solid var(--vx-border-strong) !important;
    border-radius: var(--vx-radius) !important;
}
button.secondary:hover { border-color: var(--vx-text-dim) !important; }

/* ---------- Slider / progress accent (the one functional splash of color) ------ */
input[type="range"]::-webkit-slider-thumb { background: var(--vx-accent) !important; }
.gradio-container [data-testid="slider"] .thumb { background: var(--vx-accent) !important; }
.progress-bar, .meta-text-center, .generating { color: var(--vx-accent) !important; }

.gradio-container .label-wrap { color: var(--vx-text-dim) !important; }

/* footer note */
.vx-footnote {
    color: var(--vx-text-faint) !important;
    font-size: 0.82rem;
    border-top: 1px solid var(--vx-border);
    margin-top: 48px;
    padding-top: 18px;
}

.gradio-container footer { display: none !important; }

/* Radio buttons (voice-mode picker etc.) -- pill-styled to match the button system.
   Gradio itself adds a `.selected` class to the chosen option's <label> (confirmed
   via the live DOM), which is more reliable here than a `role`/`:has()` selector --
   those didn't match this component's actual markup at all. */
.gradio-container fieldset label {
    background: var(--vx-bg-elevated) !important;
    border: 1px solid var(--vx-border-strong) !important;
    border-radius: var(--vx-radius) !important;
    color: var(--vx-text-dim) !important;
    text-transform: none !important;
    font-weight: 500 !important;
    transition: border-color 0.15s ease, color 0.15s ease, background 0.15s ease;
}
.gradio-container fieldset label.selected {
    border-color: var(--vx-accent) !important;
    color: var(--vx-text) !important;
    background: var(--vx-bg-input-focus) !important;
    box-shadow: 0 0 0 1px var(--vx-accent) inset;
}

::selection { background: rgba(94,106,210,0.30); }
::-webkit-scrollbar { width: 10px; height: 10px; }
::-webkit-scrollbar-track { background: var(--vx-bg); }
::-webkit-scrollbar-thumb { background: var(--vx-border-strong); border-radius: 8px; }
"""

CSS = CSS.replace("__VX_NOISE_SVG__", _NOISE_SVG)
