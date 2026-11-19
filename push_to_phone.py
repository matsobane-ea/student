"""Push one phone's generated clips to the running Android emulator."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT / "output"
DEFAULT_LDPLAYER_ADB = Path(r"C:\LDPlayer\LDPlayer9\adb.exe")
DEVICE_DIRECTORY = "/sdcard/DCIM/Camera/"


def find_adb() -> str | None:
    return shutil.which("adb.exe") or shutil.which("adb") or (str(DEFAULT_LDPLAYER_ADB) if DEFAULT_LDPLAYER_ADB.is_file() else None)


def running_emulator(adb: str) -> str:
    result = subprocess.run([adb, "devices"], check=True, capture_output=True, text=True)
    devices: list[str] = []
    for line in result.stdout.splitlines()[1:]:
        fields = line.strip().split()
        if len(fields) >= 2 and fields[1] == "device" and fields[0].startswith("emulator-"):
            devices.append(fields[0])

    if len(devices) != 1:
        if not devices:
            raise RuntimeError("No running emulator device found. Start the emulator and check `adb devices`.")
        raise RuntimeError(f"Expected exactly one running emulator, found {len(devices)}: {', '.join(devices)}")
    return devices[0]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phone", type=int, help="phone number whose output folder should be transferred (for example: 1)")
    args = parser.parse_args()
    if args.phone < 1:
        parser.error("phone number must be at least 1")

    adb = find_adb()
    if not adb:
        print("adb was not found on PATH or at C:\\LDPlayer\\LDPlayer9\\adb.exe.", file=sys.stderr)
        return 1

    folder = OUTPUT_DIR / f"phone_{args.phone}"
    videos = sorted(path for path in folder.glob("*.mp4") if path.is_file())
    if not videos:
        print(f"No .mp4 files found in {folder}", file=sys.stderr)
        return 1

    try:
        device = running_emulator(adb)
        for video in videos:
            remote_path = f"{DEVICE_DIRECTORY}{video.name}"
            subprocess.run([adb, "-s", device, "push", str(video), remote_path], check=True)
            subprocess.run(
                [
                    adb,
                    "-s",
                    device,
                    "shell",
                    "am",
                    "broadcast",
                    "-a",
                    "android.intent.action.MEDIA_SCANNER_SCANFILE",
                    "-d",
                    f"file://{remote_path}",
                ],
                check=True,
            )
            print(f"Transferred and scanned {video.name} on {device}")
    except (OSError, subprocess.CalledProcessError, RuntimeError) as exc:
        print(f"ADB transfer failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
