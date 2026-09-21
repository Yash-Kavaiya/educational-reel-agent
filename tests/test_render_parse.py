from __future__ import annotations

from agent.tools.reel_tools import _parse_render_output


def test_parse_render_output_extracts_metadata():
    stdout = """
TTS engine: sarvam voice: anushka
1080x1920 @ 30fps | 62s | done
Reel ready: /tmp/out.mp4
"""
    info = _parse_render_output(stdout)
    assert info["voice"] == "anushka"
    assert info["resolution"] == "1080x1920"
    assert info["duration"] == "62s"
