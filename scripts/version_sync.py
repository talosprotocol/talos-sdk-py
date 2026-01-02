from __future__ import annotations

import re
from pathlib import Path

PYPROJECT = Path("pyproject.toml")


def bump_patch(v: str) -> str:
    m = re.match(r"^(\d+)\.(\d+)\.(\d+)(.*)?$", v)
    if not m:
        raise ValueError(f"Invalid semver: {v}")
    major, minor, patch = int(m.group(1)), int(m.group(2)), int(m.group(3)) + 1
    suffix = m.group(4) or ""
    return f"{major}.{minor}.{patch}{suffix}"


def main() -> None:
    if not PYPROJECT.exists():
        return

    text = PYPROJECT.read_text(encoding="utf-8")
    m = re.search(r'(?m)^\s*version\s*=\s*"([^"]+)"\s*$', text)
    if not m:
        return
    old = m.group(1)
    new = bump_patch(old)
    updated = text[: m.start(1)] + new + text[m.end(1) :]
    PYPROJECT.write_text(updated, encoding="utf-8")
    print(f"📦 Version bumped: {old} -> {new}")


if __name__ == "__main__":
    main()
