import json
from pathlib import Path
import argparse
import subprocess
import os
from tempfile import NamedTemporaryFile, TemporaryDirectory
from typing import Any, Collection, List
from datetime import datetime
import xml.etree.ElementTree as ET

profile_dir = Path(os.getenv("APPDATA", default="")).resolve() / "hybrid/profiles/global"
handbrake = Path("HandBrakeCLI.exe").resolve()
hybrid_root = Path(os.getenv("PROGRAMFILES", default="")).resolve() / "Hybrid"
hybrid = (hybrid_root / "Hybrid.exe").resolve()
ffmpeg = (hybrid_root / "64bit" / "ffmpeg.exe").resolve()
mkvmerge = (hybrid_root / "64bit" / "mkvmerge.exe").resolve()

for f in [profile_dir, handbrake, hybrid_root, hybrid, ffmpeg, mkvmerge]:
    if not f.exists():
        raise Exception(f"Unable to access required file or directory: {f}")


def intersperse(lst: Collection[Any], item: Any):
    result = [item] * (len(lst) * 2 - 1)
    result[0::2] = lst
    return result


def run_hybrid(profile: Path, out_dir: Path, *inputs: Path):
    with TemporaryDirectory(dir=out_dir, prefix="hybrid-temp-") as temp_dir:
        with NamedTemporaryFile(dir=profile_dir, prefix="profile-", suffix=".xml", delete=False) as profile_temp:
            try:
                root = ET.parse(profile)
                defaultOutputPath = root.find(".//HybridData[@name='defaultOutputPath']")
                if defaultOutputPath is None:
                    raise Exception("Can't find defaultOutputPath in profile")
                defaultOutputPath.set("value", str(out_dir))
                defaultTempPath = root.find(".//HybridData[@name='defaultTempPath']")
                if defaultTempPath is None:
                    raise Exception("Can't find defaultTempPath in profile")
                defaultTempPath.set("value", str(temp_dir))
                root.write(profile_temp)
                profile_temp.close()
                subprocess.run(
                    [hybrid, "-global", Path(profile_temp.name), *inputs, "-autoAdd", "addAndStart"]
                ).check_returncode()
            finally:
                os.remove(profile_temp.name)


def run_handbrake(preset: Path, output: Path, input: Path):
    with open(preset) as f:
        preset_name = json.load(f)["PresetList"][0]["PresetName"]
    subprocess.run(
        [
            handbrake,
            "-i",
            input,
            "-o",
            output,
            "--preset-import-file",
            preset,
            "--preset",
            preset_name,
        ]
    ).check_returncode()


def run_mkvmerge(output: Path, *inputs: Path):
    subprocess.run(
        [
            mkvmerge,
            "-o",
            output,
            "--generate-chapters",
            "when-appending",
            "--generate-chapters-name-template",
            "<FILE_NAME>",
            *intersperse(inputs, "+"),
        ]
    ).check_returncode()


def should_skip(file: Path, cutoff_size: int) -> bool:
    return file.stat().st_size < cutoff_size * 1024 * 1024


def get_file_from_ts(file: Path, ts: datetime):
    return file.with_stem(f"{ts.year}-{ts.month:02d}-{ts.day:02d} {ts.hour:02d}_{ts.minute:02d}_{ts.second:02d}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Automatic SD video conversion script.", formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    parser.add_argument(
        "inputs",
        metavar="INPUT",
        nargs="+",
        type=str,
        help="File or directory to convert. If a directory, will merge all files inside as chapters of a single file. If you want to glob, use PowerShell: '(Get-Item E:\\*)'.",
    )
    parser.add_argument(
        "-o",
        "--out-dir",
        type=str,
        default=".",
        help="Directory where to save converted files.",
    )
    parser.add_argument(
        "--rename",
        default=False,
        action=argparse.BooleanOptionalAction,
        help="Rename files according to their modification timestamp.",
    )
    parser.add_argument(
        "--encode",
        default=True,
        action=argparse.BooleanOptionalAction,
        help="Encode the video after deinterlacing.",
    )
    parser.add_argument(
        "-c",
        "--cutoff-size",
        default=5,
        type=int,
        help="Skip files smaller than this size in MiB.",
    )
    parser.add_argument(
        "--profile",
        type=str,
        default="profiles/pal.xml",
        help="Hybrid profile to use when deinterlacing.",
    )
    parser.add_argument(
        "--preset",
        type=str,
        default="presets/av1.json",
        help="Handbrake preset to use when encoding.",
    )
    parser.add_argument(
        "--force",
        "-f",
        default=False,
        action=argparse.BooleanOptionalAction,
        help="Force overwrite existing output files.",
    )
    parser.add_argument(
        "--suffix",
        type=str,
        default=".final.mp4",
        help="Suffix to use for output files.",
    )

    args = parser.parse_args()
    inputs: List[Path] = [Path(a).resolve() for a in args.inputs]
    output_dir: Path = Path(args.out_dir).resolve()
    rename: bool = args.rename
    cutoff_size: int = args.cutoff_size
    profile: Path = Path(args.profile)
    preset: Path = Path(args.preset)
    encode: bool = args.encode
    force: bool = args.force
    final_suffix: str = args.suffix

    for input in [*inputs, output_dir, profile, preset]:
        if not input.exists():
            raise Exception(f"Invalid path: {input}")

    print("Launch configuration:")
    print()
    print(f"Queuing {len(inputs)} input files")
    print(f"Output directory: {output_dir}")
    print(f"Renaming: {rename}")
    print(f"Cutoff size: {cutoff_size}")
    print(f"Using profile: {profile}")
    print(f"Using preset: {preset}")
    print(f"Encoding: {encode}")
    print(f"Force overwrite: {force}")
    print(f"Output file suffix: {final_suffix}")
    print()

    for input in inputs:
        print(f"Processing: {input}")
        if input.is_file():
            src_files = [input]
        elif input.is_dir():
            src_files = input.glob("*")
        else:
            raise Exception(f"Unknown input type: {input}")

        src_files = [f for f in src_files if not should_skip(f, cutoff_size)]
        if len(src_files) < 1:
            continue

        src_stem_ts_map = {f.stem: datetime.fromtimestamp(f.stat().st_mtime) for f in src_files}

        with TemporaryDirectory(dir=output_dir, prefix="hybrid-conv-") as converted_dir:
            converted_dir = Path(converted_dir)

            first_file = sorted(src_files)[0]
            final_file = output_dir / first_file.name
            if rename:
                final_file = get_file_from_ts(final_file, src_stem_ts_map[final_file.stem])
            final_file = final_file.with_suffix(final_suffix)

            if final_file.exists() and not force:
                print(f"Skipping existing output: {final_file}")
                continue

            print(f"Running Hybrid...")
            run_hybrid(profile, converted_dir, *src_files)

            if rename:
                print(f"Renaming files...")
                for conv_file in converted_dir.glob("*"):
                    new_file = get_file_from_ts(conv_file, src_stem_ts_map[conv_file.stem])
                    conv_file.rename(new_file)
                    print(f"{conv_file.name} -> {new_file.name}")

            if len(list(converted_dir.glob("*"))) > 1:
                print(f"Merging files...")
                conv_files = sorted(converted_dir.glob("*"))
                merged_file = conv_files[0].with_suffix(".merged.mkv")
                run_mkvmerge(merged_file, *conv_files)
                for f in conv_files:
                    os.remove(f)
            else:
                merged_file = next(converted_dir.glob("*"))

            if encode:
                print(f"Running Handbrake...")
                encoded_file = merged_file.with_suffix(".encoded.mp4")
                run_handbrake(preset, encoded_file, merged_file)
                encoded_file.replace(final_file)
            else:
                merged_file.replace(final_file)

            print(f"Saved to: {final_file}")

    print("Done")
