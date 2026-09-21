#!/usr/bin/env python3
"""
Build the MANOBAL demo narration from demo/timeline.json.

Per-sentence synthesis so caption timings come from measured audio, not guesses.
Each segment is laid out on its own fixed slot, then padded to exact length, so
the master WAV lands on exactly timeline["total"] seconds and every caption cue
is aligned to the audio that is actually playing.

Outputs:
  out/narration/seg_<id>.wav      per-segment padded audio
  out/manobal_demo_voiceover_48k.wav   master (exactly total seconds)
  out/narration/cues.json         measured caption cues (absolute seconds)
"""

import asyncio
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "services" / "engine"))
from app.config import get_settings  # noqa: E402
from app.providers.endpoints import speech_tts_url  # noqa: E402

OUT = ROOT / "out" / "narration"
CACHE = OUT / "cache"
SR = 48000
LEAD_IN = 0.35          # preferred silence before a segment's first sentence
SENTENCE_GAP = 0.26     # preferred silence between sentences
TAIL_MIN = 0.30         # preferred silence at the end of a segment
LEAD_MIN = 0.15         # floors: pauses tighten this far before speech speeds up
GAP_MIN = 0.12
TAIL_FLOOR = 0.12
MAX_RATE = 14           # cap on prosody speed-up, so segments stay consistent


def sh(cmd: list[str]) -> str:
    return subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode().strip()


def dur_of(path: Path) -> float:
    return float(sh(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                     "-of", "csv=p=0", str(path)]))


def split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p.strip() for p in parts if p.strip()]


async def synth(client: httpx.AsyncClient, text: str, rate_pct: int, voice: str) -> Path:
    """Synthesize one sentence at a given rate; cached on disk by content hash."""
    key = hashlib.sha256(f"{voice}|{rate_pct}|{text}".encode()).hexdigest()[:20]
    path = CACHE / f"{key}.wav"
    if path.exists() and path.stat().st_size > 1000:
        return path

    settings = get_settings()
    speech_key = settings.speech_key.get_secret_value()
    url = speech_tts_url(settings)
    if not speech_key or not url:
        raise RuntimeError("Azure Speech credentials missing")

    rate = f"{rate_pct:+d}%"
    ssml = (
        "<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' "
        "xml:lang='en-IN'>"
        f"<voice name='{voice}'><prosody rate='{rate}'>"
        f"{text}</prosody></voice></speak>"
    )
    res = await client.post(
        url,
        headers={
            "Ocp-Apim-Subscription-Key": speech_key,
            "Content-Type": "application/ssml+xml",
            "X-Microsoft-OutputFormat": "riff-48khz-16bit-mono-pcm",
            "User-Agent": "manobal-demo-builder",
        },
        content=ssml.encode("utf-8"),
    )
    if res.status_code >= 300:
        raise RuntimeError(f"Azure Speech {res.status_code}: {res.text[:300]}")
    path.write_bytes(res.content)
    return path


def silence(seconds: float, path: Path) -> Path:
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", f"anullsrc=r={SR}:cl=mono",
         "-t", f"{max(seconds, 0.001):.3f}", "-c:a", "pcm_s16le", str(path)],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    return path


async def build_segment(client, seg, voice) -> tuple[Path, list[dict]]:
    """Fit a segment's sentences into its slot, speeding up only if needed."""
    seg_id, slot = seg["id"], float(seg["dur"])
    sentences = split_sentences(seg["narration"])
    n_gaps = len(sentences) - 1

    def layout(speech: float) -> tuple[float, float, float] | None:
        """Widest comfortable padding that fits this much speech, else None."""
        for shrink in [1.0, 0.85, 0.7, 0.55, 0.45]:
            lead = max(LEAD_IN * shrink, LEAD_MIN)
            gap = max(SENTENCE_GAP * shrink, GAP_MIN)
            tail = max(TAIL_MIN * shrink, TAIL_FLOOR)
            if speech + lead + gap * n_gaps + tail <= slot:
                return lead, gap, slot - lead - gap * n_gaps - speech
        return None

    rate = 0
    for attempt in range(6):
        paths = [await synth(client, s, rate, voice) for s in sentences]
        speech = sum(dur_of(p) for p in paths)
        plan = layout(speech)
        if plan:
            break
        # Pauses are already at their floor: compress the speech itself.
        room = slot - LEAD_MIN - GAP_MIN * n_gaps - TAIL_FLOOR
        rate = min(int(round((speech / room - 1) * 100)) + rate + 2, MAX_RATE)
        print(f"  [{seg_id}] speech {speech:.2f}s will not fit {slot:.1f}s slot "
              f"-> retry at rate +{rate}% (attempt {attempt + 2})")
    if not plan:
        over = speech + LEAD_MIN + GAP_MIN * n_gaps + TAIL_FLOOR - slot
        raise RuntimeError(
            f"[{seg_id}] narration overflows its {slot:.0f}s slot by {over:.2f}s "
            f"even at +{MAX_RATE}%. Shorten the text or lengthen the segment.")
    lead, gap, tail = plan

    # Lay the segment out and record where each sentence actually lands.
    pieces, cues, cursor = [], [], lead
    pieces.append(silence(lead, OUT / f"_sil_{seg_id}_lead.wav"))
    for i, (sentence, path) in enumerate(zip(sentences, paths)):
        d = dur_of(path)
        cues.append({
            "segment": seg_id,
            "start": seg["start"] + cursor,
            "end": seg["start"] + cursor + d,
            "text": sentence,
        })
        cursor += d
        pieces.append(path)
        if i < n_gaps:
            pieces.append(silence(gap, OUT / f"_sil_{seg_id}_{i}.wav"))
            cursor += gap

    pieces.append(silence(tail, OUT / f"_sil_{seg_id}_tail.wav"))

    listing = OUT / f"list_{seg_id}.txt"
    listing.write_text("".join(f"file '{p.resolve()}'\n" for p in pieces))
    seg_wav = OUT / f"seg_{seg_id}.wav"
    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(listing),
         "-c:a", "pcm_s16le", "-ar", str(SR), "-ac", "1", str(seg_wav)],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    # Hard-trim to the exact slot so rounding can never accumulate.
    exact = OUT / f"seg_{seg_id}_exact.wav"
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(seg_wav), "-t", f"{slot:.3f}",
         "-af", f"apad=whole_dur={slot:.3f}", "-c:a", "pcm_s16le",
         "-ar", str(SR), "-ac", "1", str(exact)],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    print(f"  [{seg_id}] {len(sentences)} sentences, speech {speech:.2f}s, "
          f"slot {slot:.2f}s, rate +{rate}% -> {dur_of(exact):.3f}s")
    return exact, cues


async def main() -> None:
    timeline = json.loads((ROOT / "demo" / "timeline.json").read_text())
    voice = timeline["voice"]
    total = float(timeline["total"])
    OUT.mkdir(parents=True, exist_ok=True)
    CACHE.mkdir(parents=True, exist_ok=True)

    # Verify the timeline is contiguous before spending money on TTS.
    cursor = 0.0
    for seg in timeline["segments"]:
        if abs(seg["start"] - cursor) > 1e-6:
            raise SystemExit(f"timeline gap at {seg['id']}: "
                             f"start {seg['start']} != expected {cursor}")
        cursor += seg["dur"]
    if abs(cursor - total) > 1e-6:
        raise SystemExit(f"segments sum to {cursor}s, expected {total}s")
    print(f"Timeline verified: {len(timeline['segments'])} segments, {total}s contiguous.\n")

    seg_paths, all_cues = [], []
    async with httpx.AsyncClient(timeout=60.0) as client:
        for seg in timeline["segments"]:
            path, cues = await build_segment(client, seg, voice)
            seg_paths.append(path)
            all_cues.extend(cues)

    master_list = OUT / "master_list.txt"
    master_list.write_text("".join(f"file '{p.resolve()}'\n" for p in seg_paths))
    master = ROOT / "out" / "manobal_demo_voiceover_48k.wav"
    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(master_list),
         "-c:a", "pcm_s16le", "-ar", str(SR), "-ac", "1", str(master)],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    (OUT / "cues.json").write_text(json.dumps(all_cues, indent=2))

    measured = dur_of(master)
    print(f"\nMaster: {master} = {measured:.3f}s (target {total:.3f}s)")
    if abs(measured - total) > 0.05:
        raise SystemExit(f"FAIL: master is {measured:.3f}s, expected {total:.3f}s")
    print(f"Cues: {len(all_cues)} -> {OUT / 'cues.json'}")
    print("OK")


if __name__ == "__main__":
    asyncio.run(main())
