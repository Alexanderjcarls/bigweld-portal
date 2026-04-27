"""Convert HPE Graphik OTFs -> WOFF2. Subsets to Latin if possible to shrink size.

Initial weights to ship: 400 (Regular), 500 (Medium), 600 (Semibold), 700 (Bold)
+ italic variants. ~120 KB total at WOFF2.
"""
import argparse
import subprocess
import sys
from pathlib import Path

WEIGHTS = {
    "Regular": 400,
    "RegularItalic": 400,
    "Medium": 500,
    "MediumItalic": 500,
    "Semibold": 600,
    "SemiboldItalic": 600,
    "Bold": 700,
    "BoldItalic": 700,
}

SOURCE_DIR = Path("/datapool/oracle/reference/hpe-brand/fonts/HPE Graphik/HPE Graphik")

# Basic Latin plus common UI punctuation keeps the Phase 1 payload near 120 KB total.
UNICODES = "U+0020-007E,U+00A0,U+2010-2015,U+2018-201D,U+2022,U+2026,U+20AC"


def convert(otf_path: Path, out_dir: Path) -> Path:
    out_name = otf_path.stem.replace(" ", "-").lower() + ".woff2"
    out_path = out_dir / out_name
    subprocess.run(
        [
            sys.executable,
            "-m",
            "fontTools.subset",
            str(otf_path),
            f"--output-file={out_path}",
            "--flavor=woff2",
            f"--unicodes={UNICODES}",
            "--layout-features=*",
        ],
        check=True,
    )
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--out",
        default="frontend/public/fonts/hpe-graphik",
    )
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    for variant in WEIGHTS:
        src = SOURCE_DIR / f"HPE Graphik-{variant}.otf"
        if not src.exists():
            print(f"skip (missing): {src}")
            continue
        dst = convert(src, out_dir)
        size_kb = dst.stat().st_size / 1024
        print(f"  {dst.name} - {size_kb:.1f} KB")


if __name__ == "__main__":
    main()
