# sdconv

> Automatic SD video conversion script

## Usage

1. Install Hybrid 2022.07.01-195722 or later
2. Run Hybrid
   1. Save a dummy global profile to ensure all directories are created
   2. Ensure the job queue is completely empty
3. Use the script

```bash
usage: sdconv.py [-h] [-o OUT_DIR] [--rename | --no-rename] [--encode | --no-encode] [-c CUTOFF_SIZE]
                 [--profile PROFILE] [--preset PRESET] [--force | --no-force | -f] [--suffix SUFFIX]
                 [--keep-raw | --no-keep-raw] [--raw-suffix RAW_SUFFIX] INPUT [INPUT ...]

Automatic SD video conversion script.

positional arguments:
  INPUT                 File or directory to convert. If a directory, will merge all files inside as chapters of a
                        single file. If you want to glob, use PowerShell: '(Get-Item E:\*)'.

options:
  -h, --help            show this help message and exit
  -o OUT_DIR, --out-dir OUT_DIR
                        Directory where to save converted files. (default: .)
  --rename, --no-rename
                        Rename files according to their modification timestamp. (default: False)
  --encode, --no-encode
                        Encode the video after deinterlacing. If disabled, saves the raw video file. (default: True)
  -c CUTOFF_SIZE, --cutoff-size CUTOFF_SIZE
                        Skip files smaller than this size in MiB. (default: 5)
  --profile PROFILE     Hybrid profile to use when deinterlacing. (default: profiles/pal.xml)
  --preset PRESET       Handbrake preset to use when encoding. (default: presets/av1.json)
  --force, --no-force, -f
                        Force overwrite existing output files. (default: False)
  --suffix SUFFIX       Suffix to use for output files. (default: .final.mp4)
  --keep-raw, --no-keep-raw
                        Keep raw video files when encoding. Will be reused to speed up subsequent encodes. (default: False)
  --raw-suffix RAW_SUFFIX
                        Suffix to use for raw files, if applicable. (default: .raw.mkv)
```

## Examples

- Process all videos independently (input directory contains videos)
  ```powershell
  python .\sdconv.py --profile ".\profiles\pal.xml" --preset ".\presets\av1.json" -o "E:\converted" (Get-Item "E:\input\*.avi")
  ```
- Process videos by folder, merging chapters in a single file (input directory contains folders of videos)
  ```powershell
  python .\sdconv.py --rename --profile ".\profiles\pal.xml" --preset ".\presets\av1.json" -o "E:\converted" (Get-Item "E:\input\*")
  ```

## Process

1. Deinterlace video/s using QTGMC in Hybrid. Output as UT Video since it is lossless, widely supported, and fast to encode and decode. Apply PAR and chromaticity hints to output video container (check following sections).
2. If renaming is enabled, rename the output files to their modification time. This will be used to generate chapter names next.
3. If a folder with multiple videos was input, merge the output files into a single video via mkvmerge, generating chapters from each file's name.
4. If encoding is not disabled, encode the video/s using Handbrake.

## Anamorphic dimensions

Pixels on SD video are not square. Instead, they are anamorphic - usually 16:15 for PAL, and 8:9 for NTSC. These dimensions are referred to as PAR (pixel aspect ratio), and when multiplied by the SAR (storage aspect ratio), they give the DAR (display aspect ratio), which for SD is usually 4:3.

Source: https://en.wikipedia.org/wiki/Pixel_aspect_ratio

It is crucual to get these ratios right, otherwise the video dimensions will be skewed. This applies to both encoding and decoding. When decoding, you may need to override these properties if they are missing or incorrect. When encoding, you must explicitly save each of these properties in the video container, otherwise decoders will always assume square pixels.

## Chromaticities

The chromaticities of NTSC and PAL are different, although both follow the ITU BT.601 standard. It is crucial to get them right, otherwise you will get skewed colors. This applies to both encoding and decoding. When decoding, you may need to override these properties if they are missing or incorrect. When encoding, you must explicitly save each of these properties in the video container, otherwise decoders will try to guess them, and that fails badly if the video is resized and/or deinterlaced with frame bobbing (doubling).

- BT.601 Primaries
  - NTSC
    - SMPTE 170M (usually), BT.470M (obsolete)
  - PAL
    - BT.470B/G
- BT.601 Matrix
  - SMPTE 170M, BT.470B/G (all identical)
- BT.601 Transfer
  - BT.470M, SMPTE 170M, BT.470B/G, BT.709 (all identical)

Source: https://forum.doom9.org/showthread.php?p=1681479#post1681479

## Encoder observations

All encoders below were compared at settings with equivalent encoding speed and output size. All latest versions were used as of 09/07/2022.

### x264

Preserves noise and detail better, but causes rapidly shifting, blocky artifacts. Plays everywhere.

### x265

Smoothens noise and detail, but results in significantly less, very evenly distributed, non-blocky artifacts. Plays on Safari and Edge. Requires codec on default Windows player.

### SVT-AV1

30% faster encoding than the rest, while preserving the most noise and detail, has a moderate amount of rapidly shifting, blocky artifacts. Does not play on Safari or QuickTime. Requires codec on default Windows player.
