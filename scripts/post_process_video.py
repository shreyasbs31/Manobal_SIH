#!/usr/bin/env python3
"""
Assemble the final MANOBAL demo video.

Takes the silent screen capture, the narration master and the caption sidecar
and produces a 1080p30 CFR H.264 master with burned-in captions, plus a smaller
upload copy, a checksum and a verification report.
"""

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "out"
CAPTURE = OUT / "manobal_screen_master.webm"
VOICE = OUT / "manobal_demo_voiceover_48k.wav"
SRT = OUT / "manobal_demo_captions_en.srt"
CAPTIONS = OUT / "captions"
MASTER = OUT / "manobal_demo_final_4min_1080p30_h264.mp4"
UPLOAD = OUT / "manobal_demo_final_4min_upload.mp4"
FRAMES = OUT / "frames"
TOTAL = json.loads((ROOT / "demo" / "timeline.json").read_text())["total"]

# This ffmpeg build has no libass and no drawtext, so captions cannot be burned
# in here. The recorder draws them into the page instead, on the same clock as
# the narration; a selectable soft track is muxed in below as well.

def run(cmd: list[str], label: str) -> None:
    print(f"\n$ {' '.join(cmd[:6])} ...")
    # Run from the output directory so filter arguments can use bare filenames;
    # the project path contains spaces, which the filtergraph parser mishandles.
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=OUT)
    if proc.returncode != 0:
        print(proc.stderr[-2500:])
        sys.exit(f"FAILED: {label}")
    print(f"  [ok] {label}")


def probe(path: Path) -> dict:
    out = subprocess.check_output([
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=codec_name,width,height,r_frame_rate,avg_frame_rate,pix_fmt,nb_frames",
        "-show_entries", "format=duration,bit_rate",
        "-of", "json", str(path),
    ]).decode()
    return json.loads(out)


def main() -> None:
    for path in (CAPTURE, VOICE, SRT):
        if not path.exists():
            sys.exit(f"missing input: {path}")

    cap_dur = float(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "csv=p=0", str(CAPTURE)]).decode().strip())
    print(f"capture duration : {cap_dur:.3f}s (target {TOTAL}s)")
    if cap_dur < TOTAL - 1.0:
        print(f"  ! capture is {TOTAL - cap_dur:.2f}s short; the tail will hold "
              f"the last frame to reach {TOTAL}s")

    # This ffmpeg has neither libass nor drawtext, so captions are pre-rendered
    # to transparent PNGs (by e2e/scripts/render_captions.mjs, which uses
    # Chromium as the type engine) and composited with a plain overlay filter.
    manifest = json.loads((CAPTIONS / "manifest.json").read_text())
    print(f"compositing {len(manifest)} caption images")

    inputs = ["-i", CAPTURE.name, "-i", VOICE.name, "-i", SRT.name]
    for cue in manifest:
        inputs += ["-loop", "1", "-i", f"{CAPTIONS.name}/{cue['file']}"]

    # tpad holds the final frame if the capture ran a touch short, so the video
    # and the narration always end together.
    chain = ["[0:v]tpad=stop_mode=clone:stop_duration=3,fps=30,"
             "scale=1920:1080:flags=lanczos[bg]"]
    label = "bg"
    for i, cue in enumerate(manifest):
        nxt = f"v{i}"
        chain.append(
            f"[{label}][{i + 3}:v]overlay=x=(W-w)/2:y=H-h-52:"
            f"enable='between(t\,{cue['start']:.3f}\,{cue['end']:.3f})'[{nxt}]"
        )
        label = nxt

    run([
        "ffmpeg", "-y", *inputs,
        "-filter_complex", ";".join(chain),
        "-map", f"[{label}]", "-map", "1:a:0", "-map", "2:s:0",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-pix_fmt", "yuv420p", "-r", "30", "-fps_mode", "cfr",
        "-c:a", "aac", "-b:a", "256k", "-ar", "48000",
        "-c:s", "mov_text", "-metadata:s:s:0", "language=eng",
        "-movflags", "+faststart",
        "-t", str(TOTAL),
        MASTER.name,
    ], "master with composited captions")

    run([
        "ffmpeg", "-y", "-i", MASTER.name,
        "-c:v", "libx264", "-preset", "slow", "-crf", "23",
        "-pix_fmt", "yuv420p", "-r", "30", "-fps_mode", "cfr",
        "-c:a", "aac", "-b:a", "192k", "-c:s", "mov_text",
        "-map", "0", "-movflags", "+faststart", UPLOAD.name,
    ], "upload copy")

    digest = hashlib.sha256(MASTER.read_bytes()).hexdigest()
    (OUT / "manobal_demo_final_4min_1080p30_h264_sha256.txt").write_text(
        f"{digest}  {MASTER.name}\n")

    if FRAMES.exists():
        shutil.rmtree(FRAMES)
    FRAMES.mkdir(parents=True)
    run(["ffmpeg", "-y", "-i", MASTER.name, "-vf", "fps=1/10",
         f"{FRAMES.name}/f_%03d.png"], "frame samples")

    info = probe(MASTER)
    stream, fmt = info["streams"][0], info["format"]
    duration = float(fmt["duration"])

    print("\n" + "=" * 58)
    print("VERIFICATION")
    print("=" * 58)
    print(f"  codec / size   : {stream['codec_name']} {stream['width']}x{stream['height']} {stream['pix_fmt']}")
    print(f"  frame rate     : r={stream['r_frame_rate']} avg={stream['avg_frame_rate']}")
    print(f"  frames         : {stream.get('nb_frames')}  (expect {int(TOTAL * 30)})")
    print(f"  duration       : {duration:.3f}s  (expect {TOTAL}s)")
    print(f"  master         : {MASTER.name}  {MASTER.stat().st_size / 1e6:.2f} MB")
    print(f"  upload copy    : {UPLOAD.name}  {UPLOAD.stat().st_size / 1e6:.2f} MB")
    print(f"  sha256         : {digest}")
    print(f"  sample frames  : {len(list(FRAMES.glob('*.png')))} in {FRAMES}")

    problems = []
    if abs(duration - TOTAL) > 0.15:
        problems.append(f"duration {duration:.3f}s != {TOTAL}s")
    if stream["r_frame_rate"] != stream["avg_frame_rate"]:
        problems.append("not constant frame rate")
    if (stream["width"], stream["height"]) != (1920, 1080):
        problems.append("not 1080p")
    if problems:
        print("\n  PROBLEMS: " + "; ".join(problems))
        sys.exit(1)
    print("\n  All checks passed.")


if __name__ == "__main__":
    main()
