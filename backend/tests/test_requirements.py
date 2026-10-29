from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _pins(path: Path) -> dict[str, str]:
    pins = {}
    for line in path.read_text().splitlines():
        line = line.split("#")[0].strip()
        if line and "==" in line:
            name, version = line.split("==")
            pins[name.split("[")[0].lower()] = version
    return pins


def test_vercel_requirements_match_backend_pins():
    vercel = _pins(ROOT / "requirements.txt")
    backend = _pins(ROOT / "backend" / "requirements.txt")
    assert not (ROOT / "requirements.txt").read_text().count("-r ")
    for name, version in vercel.items():
        assert backend.get(name) == version, f"{name} differs from backend/requirements.txt"
