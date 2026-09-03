"""Gradio Blocks UI -- the entire user-facing surface. Four tabs, one per feature.
Always bound to 127.0.0.1 with share=False (see launcher/main.py) -- a voice-cloning
server must never be reachable from the LAN by default, and Gradio's share tunnel
would route user audio through a public relay, which this project exists to avoid.
"""
from __future__ import annotations

import traceback

import gradio as gr

from ..device import describe_device
from ..pipelines import clone as clone_mod
from ..pipelines import dub as dub_mod
from ..pipelines import isolate as isolate_mod
from ..pipelines import tts as tts_mod
from . import design
from .theme import theme

LANGUAGES = {
    "Spanish": "es", "French": "fr", "German": "de", "Hindi": "hi",
    "Italian": "it", "Portuguese": "pt", "Japanese": "ja", "Chinese": "zh",
}


def _friendly_error(e: Exception) -> str:
    # Plain-English surface for the UI; full traceback goes to the app log, not the user.
    return f"Something went wrong: {e}"


def build_app() -> gr.Blocks:
    device_info = describe_device()
    if device_info["is_gpu"]:
        device_label = device_info["name"]
        if device_info["vram_gb"]:
            device_label += f" · {device_info['vram_gb']} GB"
    else:
        device_label = "CPU — slower, still works"

    with gr.Blocks(title="Vocalith") as app:
        with gr.Column(elem_classes=["vx-hero"]):
            gr.HTML(
                '<div class="vx-eyebrow">Local · Private · Free Forever</div>'
                '<h1>Your voice,<br>kept off the record.</h1>'
                '<p class="vx-tagline">Text to speech, voice cloning, isolation, and dubbing '
                '— run entirely on <em>this</em> machine. Nothing you speak or upload ever '
                'reaches a server.</p>'
                f'<div class="vx-banner"><span class="vx-dot"></span>'
                f'Running on <strong>{device_label}</strong></div>'
            )

        with gr.Tabs():
            with gr.TabItem("Text to Speech"):
                _tts_tab()
            with gr.TabItem("Voice Cloning"):
                _clone_tab()
            with gr.TabItem("Voice Isolation"):
                _isolate_tab()
            with gr.TabItem("Dubbing"):
                _dub_tab()

        gr.HTML(
            '<div class="vx-footnote">Kokoro · Chatterbox · Demucs · Whisper — '
            'each under a permissive license, each running locally. No account, no API key, '
            'no upload.</div>'
        )

    return app


def _tts_tab():
    with gr.Row():
        with gr.Column():
            text = gr.Textbox(label="Text", lines=6, placeholder="Type what you want spoken…")
            voice = gr.Dropdown(list(tts_mod.VOICES.keys()), value=list(tts_mod.VOICES.keys())[0], label="Voice")
            speed = gr.Slider(0.5, 2.0, value=1.0, step=0.05, label="Speed")
            run = gr.Button("Generate", variant="primary")
        with gr.Column():
            out_audio = gr.Audio(label="Output", type="filepath")
            status = gr.Markdown()

    def _run(text, voice_name, speed, progress=gr.Progress()):
        try:
            path = tts_mod.synthesize(
                text, voice=tts_mod.VOICES[voice_name], speed=speed,
                progress_cb=lambda f, s: progress(f, desc=s),
            )
            return str(path), ""
        except Exception as e:
            traceback.print_exc()
            return None, _friendly_error(e)

    run.click(_run, inputs=[text, voice, speed], outputs=[out_audio, status]).then(fn=None, js=design.pulse_js())


def _clone_tab():
    with gr.Row():
        with gr.Column():
            ref = gr.Audio(label="Reference voice sample (6-20s, clean, single speaker)", type="filepath")
            text = gr.Textbox(label="Text to speak in that voice", lines=6)
            with gr.Accordion("Advanced", open=False):
                exaggeration = gr.Slider(0.0, 1.0, value=0.5, label="Exaggeration")
                cfg_weight = gr.Slider(0.0, 1.0, value=0.5, label="CFG weight")
                denoise = gr.Checkbox(value=True, label="Clean reference audio first (Demucs)")
            run = gr.Button("Generate", variant="primary")
        with gr.Column():
            out_audio = gr.Audio(label="Output", type="filepath")
            status = gr.Markdown()
            gr.Markdown("_Output is watermarked (Resemble AI Perth watermarker), inherited from Chatterbox._")

    def _run(ref, text, exaggeration, cfg_weight, denoise, progress=gr.Progress()):
        if ref is None:
            return None, "Please upload a reference voice sample."
        try:
            path = clone_mod.clone(
                text, ref, exaggeration=exaggeration, cfg_weight=cfg_weight,
                denoise_reference=denoise, progress_cb=lambda f, s: progress(f, desc=s),
            )
            return str(path), ""
        except Exception as e:
            traceback.print_exc()
            return None, _friendly_error(e)

    run.click(
        _run, inputs=[ref, text, exaggeration, cfg_weight, denoise], outputs=[out_audio, status]
    ).then(fn=None, js=design.pulse_js())


def _isolate_tab():
    with gr.Row():
        with gr.Column():
            src = gr.Audio(label="Recording with background noise/music", type="filepath")
            mode = gr.Radio(["vocals", "all"], value="vocals", label="Mode",
                             info="'vocals' = fast two-stem split; 'all' = drums/bass/other/vocals")
            run = gr.Button("Isolate", variant="primary")
        with gr.Column():
            vocals_out = gr.Audio(label="Voice", type="filepath")
            other_out = gr.Audio(label="Background", type="filepath")
            status = gr.Markdown()

    def _run(src, mode, progress=gr.Progress()):
        if src is None:
            return None, None, "Please upload a recording."
        try:
            stems = isolate_mod.isolate(src, mode=mode, progress_cb=lambda f, s: progress(f, desc=s))
            vocals = stems.get("vocals")
            other = stems.get("accompaniment") or stems.get("other")
            return (str(vocals) if vocals else None, str(other) if other else None, "")
        except Exception as e:
            traceback.print_exc()
            return None, None, _friendly_error(e)

    run.click(_run, inputs=[src, mode], outputs=[vocals_out, other_out, status]).then(fn=None, js=design.pulse_js())


def _dub_tab():
    with gr.Row():
        with gr.Column():
            src = gr.File(label="Video or audio clip", file_types=["video", "audio"])
            target_lang = gr.Dropdown(list(LANGUAGES.keys()), value="Spanish", label="Target language")
            voice_mode = gr.Radio(["Clone original speaker", "Preset voice"], value="Clone original speaker",
                                   label="Voice")
            preset_voice = gr.Dropdown(list(tts_mod.VOICES.keys()), value=list(tts_mod.VOICES.keys())[0],
                                        label="Preset voice", visible=False)
            bed_gain = gr.Slider(0.0, 1.0, value=dub_mod.BED_GAIN_DEFAULT, label="Background music/ambience level")
            run = gr.Button("Dub", variant="primary")

            def _toggle(mode):
                return gr.update(visible=(mode == "Preset voice"))
            voice_mode.change(_toggle, inputs=voice_mode, outputs=preset_voice)

        with gr.Column():
            out_video = gr.Video(label="Dubbed video", visible=False)
            out_audio = gr.Audio(label="Dubbed audio", type="filepath", visible=False)
            out_srt = gr.File(label="Subtitles (.srt)")
            status = gr.Markdown()

    def _run(src, target_lang_name, voice_mode, preset_voice_name, bed_gain, progress=gr.Progress()):
        if src is None:
            return gr.update(visible=False), gr.update(visible=False), None, "Please upload a file."
        try:
            result = dub_mod.dub(
                src.name if hasattr(src, "name") else src,
                target_lang=LANGUAGES[target_lang_name],
                voice_mode="clone" if voice_mode.startswith("Clone") else "preset",
                preset_voice=tts_mod.VOICES[preset_voice_name] if preset_voice_name else None,
                bed_gain=bed_gain,
                progress_cb=lambda f, s: progress(f, desc=s),
            )
            msg = "\n".join(f"⚠️ {w}" for w in result.warnings) if result.warnings else "Done."
            if result.video_path:
                return (gr.update(value=str(result.video_path), visible=True),
                        gr.update(visible=False), str(result.srt_path), msg)
            return (gr.update(visible=False),
                    gr.update(value=str(result.audio_path), visible=True), str(result.srt_path), msg)
        except Exception as e:
            traceback.print_exc()
            return gr.update(visible=False), gr.update(visible=False), None, _friendly_error(e)

    run.click(_run, inputs=[src, target_lang, voice_mode, preset_voice, bed_gain],
              outputs=[out_video, out_audio, out_srt, status]).then(fn=None, js=design.pulse_js())


def launch(server_port: int = 7860):
    app = build_app()
    app.launch(server_name="127.0.0.1", server_port=server_port, share=False,
               inbrowser=False, theme=theme, css=design.CSS, head=design.head_script())


if __name__ == "__main__":
    launch()
