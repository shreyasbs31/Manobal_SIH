#!/usr/bin/env python3
"""
Check the finished demo for the failure modes that ruined the previous cut:
a panel that freezes and stops showing anything, and long stretches where the
screen simply does not change.

Samples a frame per second, then compares consecutive samples over the phone
region and the console region separately. A panel that never changes, or a run
of many identical seconds, is reported.
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MASTER = ROOT / "out" / "manobal_demo_final_4min_1080p30_h264.mp4"
WORK = ROOT / "out" / "verify_frames"

# Regions measured from the stage layout at 1920x1080.
PHONE = (55, 170, 380, 760)      # x, y, w, h - the phone panel on the left
CONSOLE = (480, 60, 1420, 1010)  # the officer console on the right

STATIC_RUN_LIMIT = 12   # seconds of an unchanged region before we complain
DIFF_THRESHOLD = 0.004  # mean abs diff (0-1) above which a second "changed"


def sample(region: tuple[int, int, int, int], tag: str) -> list[Path]:
    out = WORK / tag
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob("*.png"):
        old.unlink()
    x, y, w, h = region
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(MASTER),
         "-vf", f"fps=1,crop={w}:{h}:{x}:{y},scale=160:-1,format=gray",
         str(out / "f_%04d.png")],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    return sorted(out.glob("*.png"))


def mean_diff(a: Path, b: Path) -> float:
    """Mean absolute difference between two greyscale PNGs, 0..1."""
    out = subprocess.run(
        ["ffmpeg", "-i", str(a), "-i", str(b),
         "-filter_complex", "blend=all_mode=difference,signalstats,metadata=print:key=lavfi.signalstats.YAVG",
         "-f", "null", "-"],
        capture_output=True, text=True,
    )
    for line in out.stderr.splitlines():
        if "YAVG" in line:
            try:
                return float(line.split("=")[-1].strip()) / 255.0
            except ValueError:
                pass
    return 0.0


def analyse(region, tag):
    frames = sample(region, tag)
    if len(frames) < 10:
        sys.exit(f"{tag}: only {len(frames)} frames sampled")
    diffs = [mean_diff(frames[i - 1], frames[i]) for i in range(1, len(frames))]
    changed = [i + 1 for i, d in enumerate(diffs) if d > DIFF_THRESHOLD]

    # Longest run of consecutive seconds with no change.
    longest, run, run_start, worst_start = 0, 0, 0, 0
    for i, d in enumerate(diffs):
        if d <= DIFF_THRESHOLD:
            if run == 0:
                run_start = i + 1
            run += 1
            if run > longest:
                longest, worst_start = run, run_start
        else:
            run = 0

    print(f"\n{tag.upper()}  region={region}")
    print(f"  seconds sampled     : {len(frames)}")
    print(f"  seconds that changed: {len(changed)} ({100 * len(changed) / len(diffs):.0f}%)")
    print(f"  longest static run  : {longest}s (starting around t={worst_start}s)")
    return {"changed": len(changed), "total": len(diffs),
            "longest": longest, "at": worst_start}


def main() -> None:
    if not MASTER.exists():
        sys.exit(f"missing {MASTER}")
    WORK.mkdir(parents=True, exist_ok=True)

    phone = analyse(PHONE, "phone")
    console = analyse(CONSOLE, "console")

    print("\n" + "=" * 58)
    problems = []
    for name, r in (("phone", phone), ("console", console)):
        if r["changed"] == 0:
            problems.append(f"{name} panel never changes - it is frozen")
        elif r["changed"] / r["total"] < 0.06:
            problems.append(
                f"{name} panel changes in only {r['changed']}/{r['total']} seconds")
        if r["longest"] > STATIC_RUN_LIMIT:
            problems.append(
                f"{name} panel holds still for {r['longest']}s around t={r['at']}s")

    if problems:
        print("PROBLEMS FOUND:")
        for p in problems:
            print(f"  - {p}")
        sys.exit(1)
    print("No frozen panels and no long static stretches.")


if __name__ == "__main__":
    main()
