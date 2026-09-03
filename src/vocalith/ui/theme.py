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
    body_background_fill="#09090B",
    body_text_color="#EDEEF0",
    background_fill_primary="#131316",
    background_fill_secondary="#09090B",
    border_color_primary="#232327",
    color_accent="#5E6AD2",
    color_accent_soft="#232327",
    button_primary_background_fill="#5E6AD2",
    button_primary_background_fill_hover="#7B85E8",
    button_primary_text_color="#FFFFFF",
    button_secondary_background_fill="#131316",
    button_secondary_border_color="#3A3A40",
    block_background_fill="transparent",
    block_border_width="0px",
    input_background_fill="#17171B",
    input_border_color="#232327",
)
