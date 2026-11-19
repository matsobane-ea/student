# Video slicing and Android transfer

A small local pipeline for turning videos in `raw_vods/` into unique 30-second vertical clips, then copying each phone's clips to an attached Android emulator with ADB.

## Windows PowerShell setup

1. Install Python 3 and FFmpeg (including `ffmpeg.exe` and `ffprobe.exe`) and make them available on `PATH`. Alternatively, ADB can be on `PATH`; `push_to_phone.py` also checks `C:\LDPlayer\LDPlayer9\adb.exe`.
2. Put one or more `.mp4` source videos in `raw_vods\`. The slicer skips the first 60 seconds of each source and leaves a 5-second gap between clips.
3. Connect/start the Android emulator and confirm it is listed as the only running emulator in `adb devices`.

## Usage

From the repository directory, generate two clips per phone for three phones (defaults):

```powershell
python .\batch_slice.py
```

Choose a phone count (up to 5) and clips per phone:

```powershell
python .\batch_slice.py --phones 5 --clips 3
```

Clips are written to `output\phone_1\`, `output\phone_2\`, etc. Transfer a phone's clips to the connected emulator's gallery:

```powershell
python .\push_to_phone.py 1
```

Repeat with `2`, `3`, etc. for the other output folders. Generated videos and working folders are ignored by Git.

## Existing site preview

<div class="mt-12 mb-16 glass p-2 rounded-2xl border border-white/10 overflow-hidden max-w-3xl mx-auto shadow-2xl">
    <video 
        class="w-full rounded-xl" 
        controls 
        preload="metadata">
        <source src="assets/video%202%20prod.mp4" type="video/mp4">
        
    </video>
    <div class="p-4 text-left">
        <p class="text-xs font-mono text-cyan-500 uppercase tracking-tighter">Live Demo: Detecting R4000.90 balance manipulation</p>
    </div>
</div>
