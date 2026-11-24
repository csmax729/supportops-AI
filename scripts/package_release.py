"""Create a source ZIP from Git-visible project files and validate the distributable."""

import re
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def build():
    raw = subprocess.check_output(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"], cwd=ROOT
    )
    files = sorted({name.decode() for name in raw.split(b"\0") if name})
    output = ROOT.parent / "supportops-ai.zip"
    forbidden = {".venv", ".env", "runtime", ".git", ".uv-cache", "__pycache__"}
    for name in files:
        path = ROOT / name
        if forbidden.intersection(Path(name).parts) or path.is_symlink() or not path.is_file():
            raise ValueError(f"Unexpected release entry: {name}")
        if path.suffix == ".md":
            for target in re.findall(r"\]\(([^)\s]+)\)", path.read_text(encoding="utf-8-sig")):
                if (
                    "://" not in target
                    and not target.startswith("#")
                    and not (path.parent / target.split("#")[0]).is_file()
                ):
                    raise ValueError(f"Broken document link in {name}: {target}")
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in files:
            archive.write(ROOT / name, "supportops-ai/" + name)
    with zipfile.ZipFile(output) as check:
        assert check.testzip() is None and len(check.namelist()) == len(files)
    print(f"{output.name}: {len(files)} files, {output.stat().st_size:,} bytes")


if __name__ == "__main__":
    build()
