"""Create unique 30-second vertical clips from videos in raw_vods/."""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RAW_DIR = ROOT / "raw_vods"
OUTPUT_DIR = ROOT / "output"
CLIP_SECONDS = 30
INITIAL_SKIP_SECONDS = 60
BUFFER_SECONDS = 5
MAX_PHONES = 5


@dataclass(frozen=True)
class Clip:
    source: Path
    start: int


def executable(name: str, sibling_name: str | None = None) -> str | None:
    """Find a tool on PATH, or next to its sibling executable."""
    found = shutil.which(name)
    if found:
        return found
    if sibling_name:
        sibling = Path(sibling_name)
        candidate = Path(sibling).with_name(name)
        if candidate.is_file():
            return str(candidate)
    return None


def video_duration(path: Path, ffprobe: str) -> float:
    result = subprocess.run(
        [ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        check=True,
        capture_output=True,
        text=True,
    )
    try:
        return float(result.stdout.strip())
    except ValueError as exc:
        raise RuntimeError(f"Could not read the duration of {path.name!r}.") from exc


def source_clips(videos: list[Path], ffprobe: str, wanted: int) -> list[Clip]:
    clips: list[Clip] = []
    for video in videos:
        try:
            duration = video_duration(video, ffprobe)
        except (OSError, subprocess.CalledProcessError, RuntimeError) as exc:
            print(f"Skipping {video.name}: unable to read duration ({exc})", file=sys.stderr)
            continue

        start = INITIAL_SKIP_SECONDS
        while start + CLIP_SECONDS <= duration and len(clips) < wanted:
            clips.append(Clip(video, start))
            start += CLIP_SECONDS + BUFFER_SECONDS
        if len(clips) >= wanted:
            break
    return clips


def safe_stem(path: Path) -> str:
    return re.sub(r"[^A-Za-z0-9_-]+", "_", path.stem).strip("_") or "video"


def output_path(phone_number: int, slot: int, clip: Clip) -> Path:
    directory = OUTPUT_DIR / f"phone_{phone_number}"
    directory.mkdir(parents=True, exist_ok=True)
    base = f"clip_{slot:03d}_{safe_stem(clip.source)}_t{clip.start:06d}"
    candidate = directory / f"{base}.mp4"
    suffix = 2
    while candidate.exists():
        candidate = directory / f"{base}_{suffix}.mp4"
        suffix += 1
    return candidate


def encode_clip(ffmpeg: str, clip: Clip, destination: Path) -> None:
    video_filter = (
        "crop=w='min(iw,ih*9/16)':h='min(ih,iw*16/9)':"
        "x='(iw-ow)/2':y='(ih-oh)/2',scale=1080:1920"
    )
    command = [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-ss",
        str(clip.start),
        "-i",
        str(clip.source),
        "-t",
        str(CLIP_SECONDS),
        "-map",
        "0:v:0",
        "-map",
        "0:a?",
        "-vf",
        video_filter,
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-crf",
        "23",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-movflags",
        "+faststart",
        str(destination),
    ]
    try:
        subprocess.run(command, check=True)
    except (OSError, subprocess.CalledProcessError):
        destination.unlink(missing_ok=True)
        raise


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phones", type=int, default=3, help="number of phone folders to fill (1-5; default: 3)")
    parser.add_argument("--clips", type=int, default=2, help="number of clips per phone (default: 2)")
    args = parser.parse_args()
    if not 1 <= args.phones <= MAX_PHONES:
        parser.error(f"--phones must be between 1 and {MAX_PHONES}")
    if args.clips < 1:
        parser.error("--clips must be at least 1")
    return args


def main() -> int:
    args = parse_args()
    videos = sorted(path for path in RAW_DIR.glob("*") if path.is_file() and path.suffix.lower() == ".mp4")
    if not videos:
        print(f"No .mp4 files found in {RAW_DIR}", file=sys.stderr)
        return 1

    ffmpeg = shutil.which("ffmpeg") or shutil.which("ffmpeg.exe")
    if not ffmpeg:
        print("FFmpeg was not found on PATH. Install it and add it to PATH.", file=sys.stderr)
        return 1
    ffprobe = shutil.which("ffprobe") or shutil.which("ffprobe.exe")
    if not ffprobe:
        sibling = Path(ffmpeg).with_name("ffprobe.exe" if sys.platform == "win32" else "ffprobe")
        if sibling.is_file():
            ffprobe = str(sibling)
        else:
            print("ffprobe was not found. Install the FFmpeg tools and add them to PATH.", file=sys.stderr)
            return 1

    wanted = args.phones * args.clips
    clips = source_clips(videos, ffprobe, wanted)
    if len(clips) < wanted:
        print(
            f"Found only {len(clips)} usable 30-second clips after the 60-second skip and 5-second gaps; "
            f"{wanted} are needed. Add longer/more source videos or reduce --phones/--clips.",
            file=sys.stderr,
        )
        return 1

    try:
        for index, clip in enumerate(clips):
            phone_number = index // args.clips + 1
            slot = index % args.clips + 1
            destination = output_path(phone_number, slot, clip)
            print(f"Creating {destination.relative_to(ROOT)} from {clip.source.name} at {clip.start}s")
            encode_clip(ffmpeg, clip, destination)
    except (OSError, subprocess.CalledProcessError) as exc:
        print(f"FFmpeg failed: {exc}", file=sys.stderr)
        return 1

    print(f"Created {len(clips)} clips across {args.phones} phone folder(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
