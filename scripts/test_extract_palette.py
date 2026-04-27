"""Test palette extraction from .ase format."""
from pathlib import Path

from extract_palette import parse_ase, ase_to_tailwind_tokens

ASE_PATH = Path("/datapool/oracle/reference/hpe-brand/palette/hpe-extended-palette.ase")


def test_parse_ase_returns_swatches():
    swatches = parse_ase(ASE_PATH)
    # Per the reference index: "Primary group: White, HPE Green, Midnight..."
    assert len(swatches) > 0
    names = [s["name"] for s in swatches]
    assert any("HPE Green" in n or "Green" in n for n in names), f"got names: {names}"


def test_swatches_have_hex():
    swatches = parse_ase(ASE_PATH)
    for s in swatches:
        assert "hex" in s
        assert s["hex"].startswith("#")
        assert len(s["hex"]) == 7  # #RRGGBB


def test_tailwind_tokens_has_hpe_green():
    swatches = parse_ase(ASE_PATH)
    tokens = ase_to_tailwind_tokens(swatches)
    # Must produce a token named after HPE Green
    keys = list(tokens.keys())
    assert any("hpe-green" in k.lower() for k in keys), f"got keys: {keys}"
