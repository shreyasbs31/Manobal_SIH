#!/usr/bin/env python3
"""
Build the caption sidecar from out/narration/cues.json.

The cues carry measured start/end times taken from the synthesized audio, so
captions line up with what is actually being said rather than with an estimate.
Long sentences are split across two cues on a clause boundary so no card holds
more than two comfortable lines.

Outputs:
  out/manobal_demo_captions_en.srt
  out/manobal_demo_captions_en.vtt
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CUES = ROOT / "out" / "narration" / "cues.json"
MAX_CHARS = 84          # above this a cue is split in two
MIN_CUE = 0.9           # never flash a card shorter than this
LINE_WIDTH = 42


def wrap(text: str) -> str:
    words, lines, cur = text.split(), [], ""
    for w in words:
        if cur and len(cur) + 1 + len(w) > LINE_WIDTH:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur:
        lines.append(cur)
    return "\n".join(lines[:2]) if len(lines) <= 2 else "\n".join(
        [" ".join(lines[: len(lines) // 2]), " ".join(lines[len(lines) // 2:])]
    )


def split_cue(cue: dict) -> list[dict]:
    """Split an over-long cue at a clause boundary, proportionally in time."""
    text = cue["text"].strip()
    if len(text) <= MAX_CHARS:
        return [cue]
    # Prefer a comma/colon near the middle; fall back to the middle word.
    mid = len(text) // 2
    candidates = [m.end() for m in re.finditer(r"[,:;]\s+", text)]
    if candidates:
        cut = min(candidates, key=lambda c: abs(c - mid))
    else:
        spaces = [m.start() for m in re.finditer(r"\s+", text)]
        if not spaces:
            return [cue]
        cut = min(spaces, key=lambda c: abs(c - mid))
    first, second = text[:cut].strip(), text[cut:].strip()
    if not first or not second:
        return [cue]
    span = cue["end"] - cue["start"]
    boundary = cue["start"] + span * (len(first) / len(text))
    return [
        {**cue, "text": first, "end": boundary},
        {**cue, "text": second, "start": boundary},
    ]


def ts(seconds: float, sep: str) -> str:
    seconds = max(seconds, 0.0)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    whole = int(s)
    ms = int(round((s - whole) * 1000))
    if ms == 1000:
        whole, ms = whole + 1, 0
    return f"{int(h):02d}:{int(m):02d}:{whole:02d}{sep}{ms:03d}"


def main() -> None:
    cues = json.loads(CUES.read_text())
    out: list[dict] = []
    for cue in cues:
        out.extend(split_cue(cue))

    # Enforce a readable minimum and keep cues strictly ordered and disjoint.
    out.sort(key=lambda c: c["start"])
    for i, cue in enumerate(out):
        if cue["end"] - cue["start"] < MIN_CUE:
            cue["end"] = cue["start"] + MIN_CUE
        nxt = out[i + 1]["start"] if i + 1 < len(out) else None
        if nxt is not None and cue["end"] > nxt - 0.04:
            cue["end"] = max(cue["start"] + 0.35, nxt - 0.04)

    srt, vtt = [], ["WEBVTT", ""]
    for i, cue in enumerate(out, 1):
        body = wrap(cue["text"])
        srt.append(f"{i}\n{ts(cue['start'], ',')} --> {ts(cue['end'], ',')}\n{body}\n")
        vtt.append(f"{ts(cue['start'], '.')} --> {ts(cue['end'], '.')}\n{body}\n")

    srt_path = ROOT / "out" / "manobal_demo_captions_en.srt"
    vtt_path = ROOT / "out" / "manobal_demo_captions_en.vtt"
    srt_path.write_text("\n".join(srt))
    vtt_path.write_text("\n".join(vtt))

    # Sanity: monotonic, in range, non-empty.
    last = 0.0
    for cue in out:
        assert cue["start"] >= last - 1e-6, f"cue order broken at {cue['start']}"
        assert cue["end"] > cue["start"], f"empty cue at {cue['start']}"
        last = cue["start"]
    assert out[-1]["end"] <= 240.5, f"caption runs past the video: {out[-1]['end']}"

    print(f"{len(out)} cues -> {srt_path.name}, {vtt_path.name}")
    print(f"last cue ends at {out[-1]['end']:.2f}s")


if __name__ == "__main__":
    main()
