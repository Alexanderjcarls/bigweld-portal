"""Extract HPE color tokens from .ase (Adobe Swatch Exchange) -> Tailwind theme JSON.

ASE format: big-endian binary. Magic 'ASEF' + version + block stream.
Block types: 0xC001 (group start), 0xC002 (group end), 0x0001 (color entry).
Color models: RGB (3 floats 0-1), CMYK (4 floats), LAB, Gray.

Reference: http://www.selapa.net/swatches/colors/fileformats.php
"""
import argparse
import json
import struct
from pathlib import Path
from typing import Any


def _read_utf16be(data: bytes, offset: int) -> tuple[str, int]:
    """Read length-prefixed UTF-16BE string. Returns (string, new_offset)."""
    (length,) = struct.unpack(">H", data[offset : offset + 2])
    offset += 2
    raw = data[offset : offset + length * 2]
    offset += length * 2
    s = raw.decode("utf-16-be").rstrip("\x00")
    return s, offset


def _read_block(data: bytes, offset: int) -> tuple[dict[str, Any] | None, int]:
    """Read one block. Returns (block_dict_or_None, new_offset)."""
    (block_type,) = struct.unpack(">H", data[offset : offset + 2])
    offset += 2
    (block_length,) = struct.unpack(">I", data[offset : offset + 4])
    offset += 4
    block_end = offset + block_length

    if block_type == 0x0001:  # Color entry
        name, offset = _read_utf16be(data, offset)
        color_model = data[offset : offset + 4].decode("ascii")
        offset += 4
        if color_model == "RGB ":
            r, g, b = struct.unpack(">fff", data[offset : offset + 12])
            offset += 12
            hex_color = "#{:02X}{:02X}{:02X}".format(
                int(round(r * 255)), int(round(g * 255)), int(round(b * 255))
            )
            return {"name": name, "hex": hex_color, "model": "RGB"}, block_end
        elif color_model == "CMYK":
            c, m, y, k = struct.unpack(">ffff", data[offset : offset + 16])
            offset += 16
            # CMYK -> RGB
            r = (1 - c) * (1 - k) * 255
            g = (1 - m) * (1 - k) * 255
            b = (1 - y) * (1 - k) * 255
            hex_color = "#{:02X}{:02X}{:02X}".format(
                int(round(r)), int(round(g)), int(round(b))
            )
            return {"name": name, "hex": hex_color, "model": "CMYK"}, block_end
        elif color_model == "Gray":
            (gray,) = struct.unpack(">f", data[offset : offset + 4])
            offset += 4
            v = int(round(gray * 255))
            hex_color = "#{:02X}{:02X}{:02X}".format(v, v, v)
            return {"name": name, "hex": hex_color, "model": "Gray"}, block_end
    return None, block_end


def parse_ase(path: Path) -> list[dict[str, Any]]:
    """Parse an .ase file into a list of swatches (RGB-converted)."""
    data = path.read_bytes()
    if data[:4] != b"ASEF":
        raise ValueError("not an ASE file (missing ASEF magic)")
    (block_count,) = struct.unpack(">I", data[8:12])
    swatches = []
    offset = 12
    for _ in range(block_count):
        block, offset = _read_block(data, offset)
        if block is not None:
            swatches.append(block)
    return swatches


def _slugify(name: str) -> str:
    return (
        name.lower()
        .replace(" ", "-")
        .replace("/", "-")
        .replace(".", "")
        .strip("-")
    )


def ase_to_tailwind_tokens(swatches: list[dict[str, Any]]) -> dict[str, str]:
    """Convert swatches to Tailwind theme tokens (slugified key -> hex)."""
    return {f"hpe-{_slugify(s['name'])}": s["hex"] for s in swatches}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--ase", default="/datapool/oracle/reference/hpe-brand/palette/hpe-extended-palette.ase"
    )
    parser.add_argument(
        "--out",
        default="frontend/src/lib/hpe-tokens.json",
        help="Output JSON path (relative to portal repo root)",
    )
    args = parser.parse_args()

    swatches = parse_ase(Path(args.ase))
    tokens = ase_to_tailwind_tokens(swatches)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"tokens": tokens, "swatches": swatches}, indent=2))
    print(f"wrote {len(tokens)} tokens to {out}")


if __name__ == "__main__":
    main()
