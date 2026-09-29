from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_growthmcp_package_exists():
    assert (ROOT / "growthmcp").is_dir()
    assert (ROOT / "growthmcp" / "__main__.py").is_file()


def test_original_logo_exists():
    logo = ROOT / "assets" / "growthmcp-logo.svg"
    assert logo.is_file()
    assert "GrowthMCP" in logo.read_text()
