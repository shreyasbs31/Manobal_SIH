#!/usr/bin/env python3
"""
Generate narration WAV for MANOBAL 4-minute demo recording.
Reads text for each segment from runbook Part 7, calls Azure Speech TTS,
pads each segment to exact duration, and concats to 240.000s master WAV.
"""

import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path
import httpx

# Ensure settings can be loaded
sys.path.insert(0, str(Path(__file__).parent.parent / "services" / "engine"))
from app.config import get_settings
from app.providers.endpoints import speech_tts_url

SEGMENTS = [
    {
        "id": "S1",
        "dur": 20,
        "rate": "+5%",
        "text": (
            "Between 2020 and 2024 the CAPF lost 730 personnel to suicide, "
            "and 55,555 more resigned. Those are MHA's own figures. Everything after this is synthetic. "
            "MANOBAL is built for the weeks before. Support, not surveillance."
        ),
    },
    {
        "id": "TRANS",
        "dur": 3,
        "rate": "0%",
        "text": None,  # Silence
    },
    {
        "id": "S2",
        "dur": 22,
        "rate": "-5%",
        "text": (
            "It begins with twenty seconds. Mood, sleep, and only the context the jawan chooses, "
            "in their language. It writes to the phone first, so an outpost with no signal keeps working, "
            "buffering up to thirty days. Their commander never sees it."
        ),
    },
    {
        "id": "S3",
        "dur": 29,
        "rate": "+6%",
        "text": (
            "No one is compared to anyone else. Each jawan is measured against their own ninety-day norm "
            "across seven domains: duty hours, leave, hardship, sleep, self-report, voice and check-in cadence. "
            "One rough week never flags anyone; two independent domains have to agree. "
            "The officer sees which ones fired and a recommended action. No score, no rank, no diagnosis."
        ),
    },
    {
        "id": "S4",
        "dur": 28,
        "rate": "-4%",
        "text": (
            "The identity stays locked. To reach the person, the officer declares a care purpose and writes a justification, "
            "and the reveal is logged the instant it happens. On their own phone, the jawan sees that their identity was opened, "
            "by which role, and why. A contact note falls due after access."
        ),
    },
    {
        "id": "S5",
        "dur": 24,
        "rate": "-5%",
        "text": (
            "Command sees companies, never people. Any group under ten is blanked, so no one can reason back to an individual. "
            "Ask the assistant who is under strain and it refuses, then answers only in aggregate. "
            "The boundary holds inside the AI too."
        ),
    },
    {
        "id": "S6",
        "dur": 24,
        "rate": "-5%",
        "text": (
            "An acute phrase never reaches a language model. A deterministic filter runs on the device, "
            "ahead of any AI, and hands straight to a fixed, reviewed safety screen: "
            "Tele-MANAS, a welfare callback, SMS, and the jawan's own safety plan."
        ),
    },
    {
        "id": "S7",
        "dur": 15,
        "rate": "-2%",
        "text": (
            "This is what Medical sees. A fifteen-minute clock, the minimum context needed to respond, "
            "no journal text, no assessment answers. The next step is a person."
        ),
    },
    {
        "id": "S8",
        "dur": 20,
        "rate": "0%",
        "text": (
            "Oversight is adversarial by design. We tamper with the audit chain; the system catches the break, "
            "names its sequence, and restores it. Governance can pause Copilot or voice. It cannot switch off the acute path."
        ),
    },
    {
        "id": "S9",
        "dur": 22,
        "rate": "+8%",
        "text": (
            "MANOBAL deliberately does not score suicide risk. The published record on those models is poor and the stigma is worse. "
            "It forecasts operational strain instead, measured for precision, recall, calibration and lead time under distribution shift. "
            "Synthetic validation, not field evidence."
        ),
    },
    {
        "id": "S10",
        "dur": 33,
        "rate": "+15%",
        "text": (
            "Four zones. Analytics holds patterns, no names. Names sit in a separate vault, opened only for a justified care contact. "
            "Zone X, appraisal, promotion, posting, discipline, has no path in. "
            "This demo is hosted so you can reach it; deployment runs on the force's own hardware. "
            "Private self-help, accountable care, aggregate command, independent oversight. "
            "Prediction that earns trust by refusing to become surveillance."
        ),
    },
]

async def synth_azure(text: str, voice_name: str = "en-IN-NeerjaNeural", rate_adj: str = "-8%") -> bytes:
    settings = get_settings()
    key = settings.speech_key.get_secret_value()
    url = speech_tts_url(settings)
    if not key or not url:
        raise RuntimeError("Azure speech credentials missing")

    # Build SSML with breaks and prosody
    # Insert breaks after sentence boundaries
    processed_text = text.replace(". ", ". <break time='500ms'/> ")
    processed_text = processed_text.replace("! ", "! <break time='500ms'/> ")

    ssml = f"""<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xmlns:mstts='https://www.w3.org/2001/mstts' xml:lang='en-IN'>
<voice name='{voice_name}'>
<prosody rate="{rate_adj}">{processed_text}</prosody>
</voice>
</speak>"""

    async with httpx.AsyncClient(timeout=30.0) as client:
        res = await client.post(
            url,
            headers={
                "Ocp-Apim-Subscription-Key": key,
                "Content-Type": "application/ssml+xml",
                "X-Microsoft-OutputFormat": "riff-48khz-16bit-mono-pcm",
                "User-Agent": "manobal-demo-builder",
            },
            content=ssml.encode("utf-8"),
        )
        if res.status_code >= 300:
            raise RuntimeError(f"Azure Speech failed: {res.status_code} {res.text}")
        return bytes(res.content)

async def main():
    out_dir = Path("out")
    out_dir.mkdir(exist_ok=True)

    vo_list_lines = []

    for seg in SEGMENTS:
        seg_id = seg["id"]
        dur = seg["dur"]
        raw_path = out_dir / f"seg_{seg_id}.wav"
        pad_path = out_dir / f"pad_{seg_id}.wav"

        if seg["text"] is None:
            # Generate silence
            print(f"[{seg_id}] Generating {dur}s silence...")
            cmd = [
                "ffmpeg", "-y", "-f", "lavfi",
                "-i", f"anullsrc=r=48000:cl=mono",
                "-t", str(dur), str(pad_path)
            ]
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            rate_target = seg.get("rate", "0%")
            print(f"[{seg_id}] Synthesizing TTS (target {dur}s, rate {rate_target})...")
            raw_audio = await synth_azure(seg["text"], rate_adj=rate_target)
            with open(raw_path, "wb") as f:
                f.write(raw_audio)

            # Probe raw duration
            probe_cmd = [
                "ffprobe", "-v", "error", "-show_entries", "format=duration",
                "-of", "csv=p=0", str(raw_path)
            ]
            raw_dur_str = subprocess.check_output(probe_cmd).decode().strip()
            raw_dur = float(raw_dur_str)
            print(f"[{seg_id}] Raw duration: {raw_dur:.3f}s / allotted {dur}s")

            if raw_dur > dur:
                print(f"WARNING: Segment {seg_id} raw duration {raw_dur:.3f}s exceeds allotted {dur}s! Re-synthesizing at faster rate...")
                raw_audio = await synth_azure(seg["text"], rate_adj="+15%")
                with open(raw_path, "wb") as f:
                    f.write(raw_audio)
                raw_dur = float(subprocess.check_output(probe_cmd).decode().strip())
                print(f"[{seg_id}] Adjusted raw duration: {raw_dur:.3f}s")

            # Pad to exact duration
            pad_cmd = [
                "ffmpeg", "-y", "-i", str(raw_path),
                "-af", f"apad=whole_dur={dur}",
                "-t", str(dur), "-ar", "48000", "-ac", "1",
                str(pad_path)
            ]
            subprocess.run(pad_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        vo_list_lines.append(f"file '{pad_path.name}'")

    list_path = out_dir / "vo_list.txt"
    with open(list_path, "w") as f:
        f.write("\n".join(vo_list_lines) + "\n")

    raw_master = out_dir / "vo_raw.wav"
    concat_cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(list_path), "-c", "copy", str(raw_master)
    ]
    subprocess.run(concat_cmd, check=True)

    final_master = out_dir / "manobal_demo_voiceover_48k.wav"
    norm_cmd = [
        "ffmpeg", "-y", "-i", str(raw_master),
        "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
        "-ar", "48000", str(final_master)
    ]
    subprocess.run(norm_cmd, check=True)

    # Check total duration
    probe_cmd = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "csv=p=0", str(final_master)
    ]
    total_dur = float(subprocess.check_output(probe_cmd).decode().strip())
    print(f"\n==========================================")
    print(f"Master voiceover generated: {final_master}")
    print(f"Total duration: {total_dur:.3f}s (Target: 240.000s)")
    print(f"==========================================")

if __name__ == "__main__":
    asyncio.run(main())
