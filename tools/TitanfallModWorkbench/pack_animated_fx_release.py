from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path


OUT = Path(r"D:\TitanfallMods\22_AnimatedFX")
TOOL = Path(r"D:\CodexStorage\Projects\2026-09-08\w-3\TitanfallModWorkbench")
DOUBLE_SOURCE = Path(r"D:\TitanfallMods\14_DoubleTake_Hunter\materials\source")
WORKSPACE = Path(r"C:\Users\q1551\Documents\Codex\2026-09-08\w-3")

TOOL_SOURCE_FILES = (
    "app.py",
    "core.py",
    "animated_fx.py",
    "workflow_audit.py",
    "animated-fx-recipe-template.json",
    "project-template.json",
    "README.md",
    "CAR_WORKFLOW.md",
    "build.ps1",
    "TitanfallModWorkbench.spec",
    "version_info.txt",
    "THIRD_PARTY_NOTICES.txt",
)

WORKSPACE_FILES = (
    "render_double_fx_preview.py",
    "finish_fx_previews.py",
    "animated-fx-final-audit-recipe.json",
    "doubletake-fx-final-audit-recipe.json",
    "pack_animated_fx_release.py",
)


def add_tree(zf: zipfile.ZipFile, source: Path, prefix: str) -> None:
    for path in sorted(source.rglob("*")):
        if not path.is_file():
            continue
        if path.name.endswith(".blend1") or "__pycache__" in path.parts:
            continue
        zf.write(path, Path(prefix) / path.relative_to(source))


def add_files(zf: zipfile.ZipFile, source: Path, names: tuple[str, ...], prefix: str) -> None:
    for name in names:
        path = source / name
        if path.is_file():
            zf.write(path, Path(prefix) / name)


def digest(path: Path) -> dict[str, object]:
    sha = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            sha.update(chunk)
    return {"name": path.name, "size": path.stat().st_size, "sha256": sha.hexdigest()}


def main() -> None:
    source_zip = OUT / "TitanfallModWorkbench-1.4.0-Source.zip"
    complete_zip = OUT / "AnimatedFX-Complete-Source-2026-09-17.zip"

    for target in (source_zip, complete_zip):
        target.unlink(missing_ok=True)

    with zipfile.ZipFile(source_zip, "w", zipfile.ZIP_DEFLATED, compresslevel=9, allowZip64=True) as zf:
        add_files(zf, TOOL, TOOL_SOURCE_FILES, "TitanfallModWorkbench-1.4.0")

    with zipfile.ZipFile(complete_zip, "w", zipfile.ZIP_DEFLATED, compresslevel=9, allowZip64=True) as zf:
        for path in sorted(OUT.rglob("*")):
            if not path.is_file() or path in (source_zip, complete_zip):
                continue
            if path.name.endswith(".blend1"):
                continue
            zf.write(path, Path("AnimatedFX-2026-09-17") / path.relative_to(OUT))
        add_files(zf, TOOL, TOOL_SOURCE_FILES, "Tool/TitanfallModWorkbench-1.4.0")
        exe = TOOL / "dist" / "TitanfallModWorkbench.exe"
        zf.write(exe, "Tool/TitanfallModWorkbench-1.4.0.exe")
        add_tree(zf, DOUBLE_SOURCE, "OriginalSources/DoubleTake-HunterSafari-materials")
        add_files(zf, WORKSPACE, WORKSPACE_FILES, "Automation")

    manifest = {
        "builtAt": "2026-09-17",
        "assets": [
            digest(OUT / "CAR.Mythic.Allfather-1.2.0-animatedfx.zip"),
            digest(OUT / "Codex.DoubleTake.HunterSafari-1.0.8-animatedfx.zip"),
            digest(TOOL / "dist" / "TitanfallModWorkbench.exe"),
            digest(source_zip),
            digest(complete_zip),
            digest(OUT / "previews" / "CAR-Mythic-Allfather-animatedfx-preview.png"),
            digest(OUT / "previews" / "DoubleTake-HunterSafari-animatedfx-preview.png"),
        ],
    }
    manifest_path = OUT / "RELEASE-MANIFEST-2026-09-17.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(manifest, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
