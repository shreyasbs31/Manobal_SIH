from __future__ import annotations

from pathlib import Path


def test_on_device_preview_is_english_only() -> None:
    text = Path("apps/web/src/lib/on-device.ts").read_text(encoding="utf-8")
    assert "On-device preview" in text
    assert "English only" in text
    assert "WebGPU" in text or "webgpu" in text.lower()
    page = Path("apps/web/src/app/(personnel)/app/saathi/page.tsx").read_text(encoding="utf-8")
    assert "onDevice" in page
    assert "ON_DEVICE_LABEL" in page
    assert "sessionLang.startsWith(\"en\")" in page or "lang.startsWith(\"en\")" in page
