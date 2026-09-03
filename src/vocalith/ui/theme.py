"""Minimal base theme so Gradio's own default styling roughly matches our palette
before design.CSS's overrides apply -- avoids a flash of default-purple on load.
The real design system lives in design.py; this just sets the underlying tokens
Gradio itself reads (spacing/radius/base colors), not a decorative theme pick."""
import gradio as gr

theme = gr.themes.Base(
    # gr.themes.Font (NOT GoogleFont) -- GoogleFont injects a fonts.googleapis.com
    # <link> at runtime, a network call this app promises never to make. Font() wraps
    # a plain family name with no CDN fetch. design.CSS's var(--sans) does the real
    # typography work and overrides this anyway; this just keeps Gradio's own
    # internal theme comparisons (which expect Font objects, not bare strings) happy.
    font=[gr.themes.Font("-apple-system"), gr.themes.Font("system-ui"), gr.themes.Font("sans-serif")],
    font_mono=[gr.themes.Font("SFMono-Regular"), gr.themes.Font("Consolas"), gr.themes.Font("monospace")],
    radius_size=gr.themes.sizes.radius_sm,
).set(
    body_background_fill="#14120F",
    body_text_color="#F2ECE0",
    background_fill_primary="#1B1814",
    background_fill_secondary="#14120F",
    border_color_primary="#2C2822",
    color_accent="#D98A4A",
    color_accent_soft="#2C2822",
    button_primary_background_fill="#D98A4A",
    button_primary_background_fill_hover="#E9A164",
    button_primary_text_color="#1A1108",
    button_secondary_background_fill="transparent",
    button_secondary_border_color="#423C32",
    block_background_fill="transparent",
    block_border_width="0px",
    input_background_fill="#201C17",
    input_border_color="#2C2822",
)
