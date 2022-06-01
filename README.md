# sdconv

> Automatic SD video conversion script

## Usage

1. Install Hybrid and run it at least once so it creates its directories.
2. Use the script.

```bash
usage: sdconv.py [-h] [-o OUT_DIR] [--rename | --no-rename] [--encode | --no-encode] [-c CUTOFF_SIZE]
                 [--profile PROFILE] [--preset PRESET] [--force | --no-force | -f] [--suffix SUFFIX]
                 INPUT [INPUT ...]

Automatic SD video conversion script.

positional arguments:
  INPUT                 File or directory to convert. If a directory, will merge all files inside as chapters of a
                        single file. If you want to glob, use PowerShell: '(Get-Item E:\*)[0..20]'.

options:
  -h, --help            show this help message and exit
  -o OUT_DIR, --out-dir OUT_DIR
                        Directory where to save converted files. (default: .)
  --rename, --no-rename
                        Rename files according to their modification timestamp. (default: False)
  --encode, --no-encode
                        Encode the video after deinterlacing. (default: True)
  -c CUTOFF_SIZE, --cutoff-size CUTOFF_SIZE
                        Skip files smaller than this size in MB. (default: 5)
  --profile PROFILE     Hybrid profile to use when deinterlacing. (default: profiles/pal.xml)
  --preset PRESET       Handbrake preset to use when encoding. (default: presets/x265.json)
  --force, --no-force, -f
                        Force overwrite existing output files. (default: False)
  --suffix SUFFIX       Suffix to use for output files. (default: .final.mp4)
```

## Process

1. Deinterlace video/s using QTGMC in Hybrid. Output as x265 NVEnc lossless, since it has the smallest size and highest speed, and also allows color space hinting (check caveats section).
2. If renaming is enabled, rename the output files to their modification time. This will be used to generate chapter names next.
3. If a folder with multiple videos was input, merge the output files into a single video via mkvmerge, generating chapters from each file's name.
4. If encoding is not disabled, encode the video/s using Handbrake.

## Caveats

1. QTGMC, at least in Hybrid, always interprets PAR as 1:1, so it produces skewed video dimensions from non-square input PAR videos. To mitigate, convert the video's PAR to 1:1 prior to deinterlacing. Note that with PAL, the width will grow proportionally, while in NTSC, the height.

2. Hybrid, by default, won't output color primaries and transfer hints when rendering. Handbrake then has no choice but to try and guess them from the video's framrate. If you apply frame bobbing when deinterlacing and double the framerate to 50, since it is >25 (PAL), the video will be deemed NTSC, and the wrong color primaries and transfer will be used. To mitigate this, make Hybrid encode to H265, and always output these hints. Alternatively, force Handbrake to use the correct color primaries and transfer via its custom x265 arguments option.

## Encoder observations

All encoders below were compared at settings with equivalent encoding speed and output size.

### x264

Preserves noise and detail better, but causes rapidly shifting, blocky artifacts. Plays everywhere.

### x265

Smoothens noise and detail, but results in significantly less, very evenly distributed, non-blocky artifacts. Plays on Safari and Edge. Requires codec on default Windows player.

### AV1

30% faster encoding than the rest, while preserving the most noise and detail, has a moderate amount of rapidly shifting, blocky artifacts. Does not play on Safari or QuickTime. Requires codec on default Windows player.
