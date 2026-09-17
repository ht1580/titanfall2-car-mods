from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import time
import zipfile
import zlib
from collections import defaultdict
from pathlib import Path
from typing import Callable, Iterable

from PIL import Image, ImageEnhance, ImageOps


APP_NAME = "TitanfallModWorkbench"
APP_VERSION = "1.4.0"
APP_HOME = Path(os.environ.get("TITANFALL_WORKBENCH_HOME", r"D:\CodexStorage\TitanfallModWorkbenchData")) if Path("D:/").exists() else Path(os.environ.get("LOCALAPPDATA", Path.home())) / APP_NAME
CONFIG_PATH = APP_HOME / "config.json"
LOG_DIR = APP_HOME / "logs"
BACKUP_DIR = APP_HOME / "backups"
GLOSSARY_PATH = APP_HOME / "script_glossary.json"
BUNDLED_KEYS = {"rsx", "repak12", "repak14", "mdlshit", "texconv", "vtfcmd", "legion", "crowbar", "harmony"}
BUNDLED_DATA = (
    "project-template.json",
    "animated-fx-recipe-template.json",
    "vendor/blender/weapon_pipeline.py",
    "vendor/blender/io_scene_valvesource/__init__.py",
    "vendor/blender/io_scene_valvesource/import_smd.py",
    "vendor/blender/io_scene_valvesource/export_smd.py",
)


def resource_path(relative: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base / relative


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _first_existing(paths: Iterable[Path]) -> str:
    for path in paths:
        if path.exists():
            return str(path)
    return ""


def autodetect() -> dict[str, str]:
    drives = [Path(f"{letter}:\\") for letter in "CDEFG"]
    steam_roots = [drive / "SteamLibrary/steamapps/common" for drive in drives]
    steam_roots += [Path(r"C:\Program Files (x86)\Steam\steamapps\common")]
    titanfall = _first_existing(root / "Titanfall2" for root in steam_roots)
    apex = _first_existing(drive / "Apex" for drive in drives)
    if not apex:
        apex = _first_existing(root / "Apex Legends" for root in steam_roots)
    sfm = _first_existing(root / "SourceFilmmaker" for root in steam_roots)
    blender = _first_existing(
        [root / "Blender/blender.exe" for root in steam_roots]
        + [Path(r"C:\Program Files\Blender Foundation\Blender\blender.exe")]
    )
    bundled = resource_path("vendor")
    return {
        "titanfall": titanfall,
        "r2vanilla": str(Path(titanfall) / "R2Vanilla") if titanfall else "",
        "apex": apex,
        "sfm_game": str(Path(sfm) / "game/usermod") if sfm else "",
        "studiomdl": str(Path(sfm) / "game/bin/studiomdl.exe") if sfm else "",
        "blender": blender,
        "rsx": str(bundled / "rsx/rsx.exe"),
        "repak12": str(bundled / "tools/RePak-1.2.0.exe"),
        "repak14": str(bundled / "tools/RePak-1.4.0.exe"),
        "mdlshit": str(bundled / "tools/mdlshit.exe"),
        "texconv": str(bundled / "tools/texconv.exe"),
        "vtfcmd": str(bundled / "tools/vtfcmd/VTFCmd.exe"),
        "legion": str(bundled / "legion/LegionPlus.exe"),
        "crowbar": str(bundled / "tools/Crowbar.exe"),
        "harmony": str(bundled / "tools/Harmony.VPK.Tool.1.2.1.exe"),
    }


def load_config() -> dict[str, str]:
    detected = autodetect()
    if CONFIG_PATH.is_file():
        try:
            saved = json.loads(CONFIG_PATH.read_text(encoding="utf-8-sig"))
            detected.update({key: str(value) for key, value in saved.items() if key not in BUNDLED_KEYS})
        except (OSError, ValueError):
            pass
    return detected


def save_config(config: dict[str, str]) -> None:
    APP_HOME.mkdir(parents=True, exist_ok=True)
    persistent = {key: value for key, value in config.items() if key not in BUNDLED_KEYS}
    CONFIG_PATH.write_text(json.dumps(persistent, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_process(
    args: list[str],
    log: Callable[[str], None],
    cwd: Path | None = None,
    visible: bool = False,
) -> int:
    log("执行: " + subprocess.list2cmdline(args))
    flags = 0 if visible else getattr(subprocess, "CREATE_NO_WINDOW", 0)
    process = subprocess.Popen(
        args,
        cwd=str(cwd) if cwd else None,
        stdout=None if visible else subprocess.PIPE,
        stderr=None if visible else subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=flags,
    )
    if process.stdout:
        for line in process.stdout:
            log(line.rstrip())
    code = process.wait()
    if code:
        raise RuntimeError(f"命令失败，退出代码 {code}")
    log("完成")
    return code


def apex_pak_chain(apex_dir: Path, base_name: str) -> list[Path]:
    pak_dir = apex_dir / "paks/Win64"
    base = pak_dir / f"{base_name}.rpak"
    if not base.is_file():
        raise FileNotFoundError(base)
    escaped = re.escape(base_name)
    patches = sorted(
        (path for path in pak_dir.glob(f"{base_name}(*).rpak") if re.fullmatch(escaped + r"\(\d+\)\.rpak", path.name)),
        key=lambda path: int(re.search(r"\((\d+)\)", path.name).group(1)),
    )
    return [base, *patches]


def rsx_export(
    config: dict[str, str],
    paks: list[Path],
    output: Path,
    asset_filter: str,
    asset_types: str,
    model_setting: int,
    model_skin: int,
    log: Callable[[str], None],
    material_textures: bool = True,
    full_paths: bool = True,
    skip_postload: bool = True,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    types = {item.strip() for item in asset_types.split(",") if item.strip()}
    whitelist = set(types)
    if "matl" in types:
        whitelist.update({"txtr", "shds", "msnp"})
    if "mdl_" in types and not skip_postload:
        whitelist.update({"arig", "aseq", "asqd", "matl", "txtr"})
    if types.intersection({"arig", "aseq"}) and not skip_postload:
        whitelist.update({"arig", "aseq", "asqd"})
    args = [config["rsx"], "-nogui", "-export"]
    if "matl" in types:
        args += ["--matlsetting", "2"]
    if skip_postload:
        args.append("-skippostload")
    if material_textures:
        args.append("-matltextures")
    if full_paths:
        args.append("-exportfullpaths")
    args += [
        "--loadwhitelist", ",".join(sorted(whitelist)),
        "--exportfilter", asset_filter,
        "--exporttypes", asset_types,
        "--modelsetting", str(model_setting),
        "--modelskin", str(model_skin),
        "--exportdir", str(output),
    ]
    args += [str(path) for path in paks]
    run_process(args, log, cwd=Path(config["rsx"]).parent)


def rsx_list(config: dict[str, str], paks: list[Path], output: Path, log: Callable[[str], None]) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    args = [config["rsx"], "-nogui", "--list", str(output), "--listformat", "csv"]
    args += [str(path) for path in paks]
    run_process(args, log, cwd=Path(config["rsx"]).parent)


def _read_cstr(data: bytes, offset: int) -> tuple[str, int]:
    end = data.index(0, offset)
    return data[offset:end].decode("utf-8"), end + 1


def _parse_vpk_directory(path: Path):
    data = path.read_bytes()
    magic, major, minor, tree_size, data_size = struct.unpack_from("<IHHII", data)
    if (magic, major, minor) != (0x55AA1234, 2, 3):
        raise ValueError(f"不支持的 VPK 版本: {magic:08x} {major}.{minor}")
    if data_size:
        raise ValueError("暂不支持 directory VPK 内嵌 preload data")
    pos, tree_end, files = 16, 16 + tree_size, []
    while True:
        ext, pos = _read_cstr(data, pos)
        if not ext:
            break
        while True:
            folder, pos = _read_cstr(data, pos)
            if not folder:
                break
            while True:
                name, pos = _read_cstr(data, pos)
                if not name:
                    break
                crc, preload, archive = struct.unpack_from("<IHH", data, pos)
                pos += 8
                if preload:
                    raise ValueError(f"暂不支持 preload data: {folder}/{name}.{ext}")
                chunks = []
                while True:
                    flags, texture_flags, offset, compressed, uncompressed = struct.unpack_from("<IHQQQ", data, pos)
                    pos += 30
                    chunks.append((offset, compressed, uncompressed, flags, texture_flags))
                    terminator = struct.unpack_from("<H", data, pos)[0]
                    pos += 2
                    if terminator == 0xFFFF:
                        break
                    if terminator != archive:
                        raise ValueError("VPK chunk terminator 无效")
                rel = f"{name}.{ext}" if folder == " " else f"{folder}/{name}.{ext}"
                files.append((rel, crc, archive, chunks))
    if pos != tree_end:
        raise ValueError(f"VPK 目录树长度不一致: {pos} != {tree_end}")
    return files


def _vpk_block_path(directory_vpk: Path, archive: int) -> Path:
    if archive == 0x7FFF:
        return directory_vpk
    if not directory_vpk.name.endswith("_dir.vpk"):
        raise ValueError("目录 VPK 文件名必须以 _dir.vpk 结尾")
    result = directory_vpk.with_name(directory_vpk.name[:-8] + f"_{archive:03d}.vpk")
    if not result.exists() and result.name.startswith("englishclient_"):
        result = result.with_name(result.name[len("english"):])
    return result


def extract_vpk(directory_vpk: Path, output: Path, log: Callable[[str], None]) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    files = _parse_vpk_directory(directory_vpk)
    total = 0
    for number, (relative, expected_crc, archive, chunks) in enumerate(files, 1):
        source = _vpk_block_path(directory_vpk, archive)
        payload = bytearray()
        with source.open("rb") as handle:
            for offset, compressed, uncompressed, _flags, _texture_flags in chunks:
                if compressed != uncompressed:
                    raise ValueError(f"检测到 LZHAM 压缩，请使用内置 Harmony: {relative}")
                handle.seek(offset)
                payload.extend(handle.read(compressed))
        if zlib.crc32(payload) & 0xFFFFFFFF != expected_crc:
            raise ValueError(f"CRC 不一致: {relative}")
        target = output / Path(relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
        total += len(payload)
        if number % 500 == 0:
            log(f"已解包 {number}/{len(files)}")
    result = {"files": len(files), "bytes": total, "output": str(output)}
    log(json.dumps(result, ensure_ascii=False))
    return result


NODE_RE = re.compile(r'^\s*(-?\d+)\s+"([^"]+)"\s+(-?\d+)\s*$')


def _section(lines: list[str], name: str) -> tuple[int, int]:
    start = lines.index(name)
    return start, lines.index("end", start + 1)


def _nodes(lines: list[str]) -> tuple[int, int, dict[int, tuple[str, int]]]:
    start, end = _section(lines, "nodes")
    table = {}
    for line in lines[start + 1:end]:
        match = NODE_RE.match(line)
        if not match:
            raise ValueError(f"SMD 节点行无效: {line}")
        table[int(match.group(1))] = (match.group(2), int(match.group(3)))
    return start, end, table


def remap_smd_to_reference(
    source: Path,
    reference: Path,
    output: Path,
    material_from: str = "",
    material_to: str = "",
    preserve_reference_material: str = "",
) -> dict:
    current = source.read_text(encoding="utf-8-sig", errors="strict").splitlines()
    ref = reference.read_text(encoding="utf-8-sig", errors="strict").splitlines()
    cur_start, cur_end, cur_nodes = _nodes(current)
    ref_start, ref_end, ref_nodes = _nodes(ref)
    ref_by_name = {name: index for index, (name, _parent) in ref_nodes.items()}
    id_map = {index: ref_by_name[name] for index, (name, _parent) in cur_nodes.items() if name in ref_by_name}

    skeleton_start, skeleton_end = _section(current, "skeleton")
    dropped = 0
    rewritten_skeleton = []
    for line in current[skeleton_start + 1:skeleton_end]:
        tokens = line.split()
        if not tokens or tokens[0] == "time":
            rewritten_skeleton.append(line)
        elif int(tokens[0]) in id_map:
            tokens[0] = str(id_map[int(tokens[0])])
            rewritten_skeleton.append(" ".join(tokens))
        else:
            dropped += 1
    current[skeleton_start + 1:skeleton_end] = rewritten_skeleton

    triangles_start, triangles_end = _section(current, "triangles")
    index = triangles_start + 1
    triangle_count = 0
    while index < triangles_end:
        if material_from and current[index].strip() == material_from:
            current[index] = material_to
        elif material_to and not material_from:
            current[index] = material_to
        for vertex_index in range(index + 1, index + 4):
            tokens = current[vertex_index].split()
            bone_positions = [0]
            if len(tokens) > 9:
                bone_positions += [10 + pair * 2 for pair in range(int(tokens[9]))]
            for token_index in bone_positions:
                old_id = int(tokens[token_index])
                if old_id not in id_map:
                    raise ValueError(f"网格使用了参考骨架不存在的骨骼: {cur_nodes[old_id][0]}")
                tokens[token_index] = str(id_map[old_id])
            current[vertex_index] = " ".join(tokens)
        triangle_count += 1
        index += 4

    preserved = 0
    if preserve_reference_material:
        ref_tri_start, ref_tri_end = _section(ref, "triangles")
        detail = []
        index = ref_tri_start + 1
        while index < ref_tri_end:
            if ref[index].strip() == preserve_reference_material:
                detail.extend(ref[index:index + 4])
                preserved += 1
            index += 4
        current[triangles_end:triangles_end] = detail

    current[cur_start:cur_end + 1] = ref[ref_start:ref_end + 1]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(current) + "\n", encoding="utf-8", newline="\n")
    return {
        "sourceNodes": len(cur_nodes),
        "referenceNodes": len(ref_nodes),
        "droppedPoseRows": dropped,
        "triangles": triangle_count,
        "preservedReferenceFaces": preserved,
        "output": str(output),
    }


def blender_weapon_pipeline(
    config: dict[str, str],
    source: Path,
    reference: Path,
    output_smd: Path,
    blend_path: Path,
    preview_path: Path,
    material_from: str,
    material_to: str,
    preserve_reference_material: str,
    offset: tuple[float, float, float],
    rotation: tuple[float, float, float],
    scale: float,
    mirror: str,
    log: Callable[[str], None],
) -> dict:
    blender = Path(config["blender"])
    if not blender.is_file():
        raise FileNotFoundError(f"Blender 不存在: {blender}")
    work_dir = blend_path.parent / ".workbench"
    work_dir.mkdir(parents=True, exist_ok=True)
    mapped = work_dir / f"{output_smd.stem}.mapped.smd"
    remap = remap_smd_to_reference(
        source, reference, mapped, material_from, material_to, preserve_reference_material,
    )
    script = resource_path("vendor/blender/weapon_pipeline.py")
    report_path = work_dir / f"{output_smd.stem}.blender-report.json"
    args = [
        str(blender), "--factory-startup", "--background", "--python", str(script), "--",
        "--input-smd", str(mapped),
        "--output-smd", str(output_smd),
        "--blend", str(blend_path),
        "--preview", str(preview_path),
        "--offset", *(str(value) for value in offset),
        "--rotation", *(str(value) for value in rotation),
        "--scale", str(scale), "--mirror", mirror,
        "--report", str(report_path),
    ]
    run_process(args, log, cwd=blend_path.parent)
    if not report_path.is_file():
        raise RuntimeError("Blender 未生成流水线报告")
    blender_report = json.loads(report_path.read_text(encoding="utf-8-sig"))
    result = {"status": "passed", "remap": remap, "blender": blender_report}
    result["report"] = str(write_report(result, "blender-pipeline"))
    return result


def run_project_file(project_path: Path) -> dict:
    """Run a repeatable model build from a JSON project without opening the GUI."""
    project_path = project_path.resolve()
    data = json.loads(project_path.read_text(encoding="utf-8-sig"))
    base = project_path.parent
    messages: list[str] = []
    config = load_config()
    config.update({key: str(value) for key, value in data.get("paths", {}).items() if key not in BUNDLED_KEYS})

    def path_value(name: str) -> Path:
        value = str(data.get(name, "")).strip()
        path = Path(value)
        return path if path.is_absolute() else base / path

    def resolve_value(value: str) -> Path:
        path = Path(value)
        return path if path.is_absolute() else base / path

    def log(message: str) -> None:
        messages.append(message)

    result: dict = {"status": "passed", "project": str(project_path), "steps": {}}
    required = ("sourceSmd", "referenceSmd", "outputSmd", "blend", "preview")
    if all(str(data.get(key, "")).strip() for key in required):
        result["steps"]["blender"] = blender_weapon_pipeline(
            config,
            path_value("sourceSmd"), path_value("referenceSmd"), path_value("outputSmd"),
            path_value("blend"), path_value("preview"),
            str(data.get("materialFrom", "")), str(data.get("materialTo", "")),
            str(data.get("preserveReferenceMaterial", "")),
            tuple(float(v) for v in data.get("offset", [0, 0, 0])),
            tuple(float(v) for v in data.get("rotation", [0, 0, 0])),
            float(data.get("scale", 1)), str(data.get("mirror", "none")), log,
        )
    texture = data.get("textures", {})
    if texture.get("enabled"):
        texture_sources = {
            suffix: resolve_value(str(value)) if str(value).strip() else None
            for suffix, value in texture.get("sources", {}).items()
        }
        result["steps"]["textures"] = process_texture_set(
            config, texture_sources, resolve_value(texture["outputRoot"]), texture["materialPath"],
            int(texture.get("size", 1024)), float(texture.get("brightness", 1)),
            float(texture.get("contrast", 1)), float(texture.get("saturation", 1)),
            bool(texture.get("flipNormalGreen", False)), bool(texture.get("generateVtf", True)),
            bool(texture.get("generateDds", True)), log,
        )
    if str(data.get("qc", "")).strip():
        compile_qc(config, path_value("qc"), log)
        result["steps"]["studiomdl"] = str(path_value("qc"))
    if str(data.get("mdl", "")).strip():
        result["steps"]["mdlV53"] = str(convert_mdl(config, path_value("mdl"), log))
    if str(data.get("rpakMap", "")).strip():
        build_rpak(config, path_value("rpakMap"), str(data.get("repakVersion", "1.2")), log)
        result["steps"]["repak"] = str(path_value("rpakMap"))
    if str(data.get("animatedFxRecipe", "")).strip():
        from animated_fx import run_recipe
        result["steps"]["animatedFx"] = run_recipe(path_value("animatedFxRecipe"), log)
    translation = data.get("translateScript", {})
    if translation.get("enabled"):
        source_path = resolve_value(translation["input"])
        output_path = resolve_value(translation["output"])
        source_text = source_path.read_text(encoding="utf-8-sig", errors="replace")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(translate_script_for_editing(source_text), encoding="utf-8")
        result["steps"]["scriptTranslation"] = str(output_path)
    mod = data.get("mod", {})
    if mod.get("enabled"):
        zip_value = str(mod.get("zip", "")).strip()
        result["steps"]["mod"] = assemble_mod(
            resolve_value(mod["staging"]), resolve_value(mod["outputParent"]),
            mod["folderName"], mod.get("name", mod["folderName"]), mod.get("description", ""),
            mod.get("version", "1.0.0"), int(mod.get("loadPriority", 0)),
            resolve_value(zip_value) if zip_value else None,
        )
    if not result["steps"]:
        raise ValueError("Project JSON contains no runnable steps")
    result["log"] = messages
    result["report"] = str(write_report(result, "project-run"))
    return result


def compile_qc(config: dict[str, str], qc: Path, log: Callable[[str], None]) -> None:
    run_process([config["studiomdl"], "-nop4", "-game", config["sfm_game"], str(qc)], log)


def convert_mdl(config: dict[str, str], mdl: Path, log: Callable[[str], None]) -> Path:
    dx90 = mdl.with_suffix(".dx90.vtx")
    vtx = mdl.with_suffix(".vtx")
    if dx90.is_file():
        shutil.copy2(dx90, vtx)
    run_process([config["mdlshit"], "--noui", str(mdl)], log, cwd=mdl.parent)
    output = mdl.with_name(mdl.stem + "_conv.mdl")
    if not output.is_file():
        raise FileNotFoundError(f"MDLShit 未生成 {output}")
    return output


def build_rpak(config: dict[str, str], map_path: Path, version: str, log: Callable[[str], None]) -> None:
    key = "repak12" if version.startswith("1.2") else "repak14"
    run_process([config[key], str(map_path)], log, cwd=map_path.parent)


TEXTURE_SUFFIXES = ("col", "nml", "gls", "spc", "ao", "cav")

DDS_FORMATS = {
    "nml": "BC5_UNORM",
    "gls": "BC4_UNORM",
    "col": "BC7_UNORM_SRGB",
    "spc": "BC7_UNORM_SRGB",
    "msk": "BC7_UNORM_SRGB",
    "opa": "BC7_UNORM_SRGB",
}


def _texture_image(source: Path | None, suffix: str, size: int) -> Image.Image:
    if source and source.is_file():
        image = Image.open(source).convert("RGBA")
        return ImageOps.fit(image, (size, size), method=Image.Resampling.LANCZOS)
    defaults = {
        "nml": (128, 128, 255, 255), "gls": (128, 128, 128, 255),
        "spc": (64, 64, 64, 255), "ao": (255, 255, 255, 255),
        "cav": (255, 255, 255, 255),
    }
    return Image.new("RGBA", (size, size), defaults[suffix])


def process_texture_set(
    config: dict[str, str],
    sources: dict[str, Path | None],
    output_root: Path,
    material_path: str,
    size: int,
    brightness: float,
    contrast: float,
    saturation: float,
    flip_normal_green: bool,
    generate_vtf: bool,
    generate_dds: bool,
    log: Callable[[str], None],
) -> dict:
    color = sources.get("col")
    if not color or not color.is_file():
        raise FileNotFoundError("必须提供颜色贴图")
    if size < 32 or size > 8192 or size & (size - 1):
        raise ValueError("贴图尺寸必须是 32 到 8192 之间的 2 次幂")
    if generate_dds and size < 512:
        raise ValueError("RePak DDS 贴图尺寸至少需要 512；推荐武器贴图使用 1024 或 2048")
    clean_material = material_path.replace("\\", "/").strip("/")
    if clean_material.lower().startswith("materials/"):
        clean_material = clean_material[10:]
    if not clean_material or clean_material.endswith("/"):
        raise ValueError("材质路径必须包含材质名称")
    relative = Path(*clean_material.split("/"))
    work = output_root / ".workbench_textures"
    work.mkdir(parents=True, exist_ok=True)
    processed: dict[str, Path] = {}
    for suffix in TEXTURE_SUFFIXES:
        image = _texture_image(sources.get(suffix), suffix, size)
        if suffix == "col":
            image = ImageEnhance.Brightness(image).enhance(brightness)
            image = ImageEnhance.Contrast(image).enhance(contrast)
            image = ImageEnhance.Color(image).enhance(saturation)
        if suffix == "nml" and flip_normal_green:
            red, green, blue, alpha = image.split()
            green = ImageOps.invert(green)
            image = Image.merge("RGBA", (red, green, blue, alpha))
        path = work / f"{relative.name}_{suffix}.png"
        image.save(path, optimize=True)
        processed[suffix] = path

    outputs: dict[str, list[str] | str] = {"processedPng": [str(p) for p in processed.values()]}
    if generate_vtf:
        vtf_dir = output_root / "mod/materials" / relative.parent
        vtf_dir.mkdir(parents=True, exist_ok=True)
        vtf_files = []
        for suffix, png in processed.items():
            args = [config["vtfcmd"], "-file", str(png), "-output", str(vtf_dir),
                    "-format", "dxt5" if suffix in ("col", "nml") else "dxt1", "-silent"]
            if suffix == "nml":
                args += ["-flag", "normal"]
            run_process(args, log, cwd=Path(config["vtfcmd"]).parent)
            generated = vtf_dir / (png.stem + ".vtf")
            if not generated.is_file():
                raise FileNotFoundError(f"VTFCmd 未生成 {generated}")
            vtf_files.append(str(generated))
        vmt = output_root / "mod/materials" / relative.with_suffix(".vmt")
        vmt.parent.mkdir(parents=True, exist_ok=True)
        base = clean_material
        vmt.write_text(
            'VertexLitGeneric\n{\n'
            f'    "$basetexture" "{base}_col"\n'
            f'    "$bumpmap" "{base}_nml"\n'
            '    "$phong" "1"\n'
            f'    "$phongexponenttexture" "{base}_gls"\n'
            f'    "$phongwarptexture" "{base}_spc"\n'
            '    "$model" "1"\n}\n',
            encoding="utf-8", newline="\n",
        )
        outputs["vtf"] = vtf_files
        outputs["vmt"] = str(vmt)

    if generate_dds:
        dds_dir = output_root / "repak/assets/texture" / relative.parent
        dds_dir.mkdir(parents=True, exist_ok=True)
        dds_files = []
        for suffix, png in processed.items():
            fmt = DDS_FORMATS.get(suffix, "BC7_UNORM")
            run_process([config["texconv"], "-nologo", "-y", "-f", fmt, "-o", str(dds_dir), str(png)], log)
            generated = dds_dir / (png.stem + ".DDS")
            target = dds_dir / (png.stem + ".dds")
            if generated.is_file() and generated != target:
                generated.replace(target)
            if not target.is_file():
                raise FileNotFoundError(f"TexConv 未生成 {target}")
            dds_files.append(str(target))
        map_dir = output_root / "repak/maps"
        map_dir.mkdir(parents=True, exist_ok=True)
        (output_root / "repak/build").mkdir(parents=True, exist_ok=True)
        pak_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", relative.name)
        texture_base = f"texture/{clean_material}"
        textures = [f"{texture_base}_{suffix}" for suffix in TEXTURE_SUFFIXES]
        material = {
            "$type": "matl", "subtype": "viewmodel", "type": "skn",
            "shaderset": "shaderset/uberAoCavEmitEntcolmeSamp2222222_skn.rpak",
            "rasterFlags": 6, "version": 12, "path": clean_material,
            "surface": "weapon", "width": size, "height": size,
            "albedoTint": [1.0, 1.0, 1.0], "emissiveTint": [0.0, 0.0, 0.0],
            "textures": [textures[0], textures[1], textures[2], textures[3], "", "", "", "", "", "", "", textures[4], textures[5]],
            "visibilityflags": "opaque", "faceflags": 6,
        }
        world_material = dict(material)
        world_material.update({
            "subtype": "worldmodel_noglow", "type": "fix",
            "shaderset": "shaderset/uberAoCavEmitEntcolmeSamp2222222_fix.rpak",
        })
        map_data = {
            "name": pak_name, "assetsDir": "../assets", "outputDir": "../build",
            "version": 7, "starpakPath": f"{pak_name}.starpak",
            "files": [{"$type": "txtr", "path": path} for path in textures] + [material, world_material],
        }
        map_path = map_dir / f"{pak_name}.json"
        map_path.write_text(json.dumps(map_data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        outputs["dds"] = dds_files
        outputs["rpakMap"] = str(map_path)
    result = {"status": "passed", "material": clean_material, "size": size, "outputs": outputs}
    result["report"] = str(write_report(result, "texture-build"))
    return result


def assemble_mod(
    staging: Path, output_parent: Path, folder_name: str, mod_name: str,
    description: str, version: str, load_priority: int, zip_output: Path | None,
) -> dict:
    if not staging.is_dir():
        raise FileNotFoundError(staging)
    safe_folder = re.sub(r"[^A-Za-z0-9_. -]+", "_", folder_name).strip(" .")
    if not safe_folder:
        raise ValueError("模组文件夹名称无效")
    output_parent.mkdir(parents=True, exist_ok=True)
    target = (output_parent / safe_folder).resolve()
    if target.parent != output_parent.resolve():
        raise RuntimeError(f"生成目标不安全: {target}")
    if target.exists():
        stamp = time.strftime("%Y%m%d-%H%M%S")
        backup = BACKUP_DIR / "generated" / stamp / safe_folder
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(target, backup)
        shutil.rmtree(target)
    target.mkdir(parents=True)
    allowed_directories = {"mod", "paks", "keyvalues", "scripts", "media"}
    for item in staging.iterdir():
        if item.name.startswith(".workbench") or item.name.lower() == "repak":
            continue
        if item.is_dir() and item.name.lower() not in allowed_directories:
            continue
        item_resolved = item.resolve()
        if target.is_relative_to(item_resolved) or output_parent.resolve() == item_resolved:
            continue
        if zip_output and item_resolved == zip_output.resolve():
            continue
        destination = target / item.name
        if item.is_dir():
            shutil.copytree(item, destination)
        elif item.is_file():
            shutil.copy2(item, destination)
    repak_build = staging / "repak/build"
    package_files = []
    if repak_build.is_dir():
        paks = target / "paks"
        paks.mkdir(parents=True, exist_ok=True)
        for package in repak_build.iterdir():
            if package.is_file() and package.suffix.lower() in (".rpak", ".starpak"):
                shutil.copy2(package, paks / package.name)
                package_files.append(package.name)
        rpak_json = paks / "rpak.json"
        if package_files and not rpak_json.exists():
            registrations = {
                name: "common.rpak" for name in package_files if name.lower().endswith(".rpak")
            }
            rpak_json.write_text(
                json.dumps({"Postload": registrations}, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
    manifest = {
        "Name": mod_name.strip() or safe_folder,
        "Description": description.strip(),
        "Version": version.strip() or "1.0.0",
        "LoadPriority": int(load_priority),
    }
    (target / "mod.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    validation = validate_mod(target)
    result = {"status": validation["status"], "target": str(target), "packagesCopied": package_files, "validation": validation}
    if zip_output:
        result["package"] = package_zip(target, zip_output)
    result["report"] = str(write_report(result, "mod-build"))
    return result


SCRIPT_GLOSSARY = {
    "weapon": "武器", "damage": "伤害", "player": "玩家", "model": "模型",
    "viewmodel": "第一人称模型", "worldmodel": "世界模型", "reload": "换弹",
    "ammo": "弹药", "clip": "弹匣", "fire": "射击", "attack": "攻击",
    "animation": "动画", "bodygroup": "模型组", "material": "材质",
    "texture": "贴图", "enabled": "启用", "disabled": "禁用", "default": "默认",
    "priority": "优先级", "preload": "预加载", "postload": "后加载",
    "server": "服务端", "client": "客户端", "function": "函数", "return": "返回",
    "true": "真", "false": "假", "name": "名称", "description": "说明",
    "version": "版本", "path": "路径", "width": "宽度", "height": "高度",
    "offset": "偏移", "scale": "缩放", "angle": "角度", "origin": "原点",
    "if": "如果", "else": "否则", "while": "当", "for": "循环", "foreach": "遍历",
    "and": "并且", "or": "或者", "not": "非", "local": "局部变量", "global": "全局",
    "entity": "实体", "owner": "持有者", "target": "目标", "event": "事件",
    "array": "数组", "table": "表", "string": "字符串", "integer": "整数",
    "float": "小数", "boolean": "布尔值", "callback": "回调", "register": "注册",
    "create": "创建", "destroy": "销毁", "update": "更新", "initialize": "初始化",
}


def load_script_glossary() -> dict[str, str]:
    APP_HOME.mkdir(parents=True, exist_ok=True)
    glossary = dict(SCRIPT_GLOSSARY)
    if GLOSSARY_PATH.is_file():
        try:
            custom = json.loads(GLOSSARY_PATH.read_text(encoding="utf-8-sig"))
            glossary.update({str(key).lower(): str(value) for key, value in custom.items()})
        except (OSError, ValueError):
            pass
    else:
        GLOSSARY_PATH.write_text(json.dumps(glossary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return glossary


def translate_script_for_editing(text: str) -> str:
    """Create a non-executable Chinese aid view while preserving the original file."""
    output = ["【中文辅助视图：不要直接作为游戏脚本保存】", ""]
    glossary = load_script_glossary()
    token = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*\b")

    def translate_token(match: re.Match) -> str:
        value = match.group(0)
        exact = glossary.get(value.lower())
        if exact:
            return exact
        parts = re.findall(r"[A-Z]+(?=[A-Z][a-z]|\b)|[A-Z]?[a-z]+|\d+", value.replace("_", " "))
        translated = [glossary.get(part.lower(), part) for part in parts]
        if parts and any(left != right for left, right in zip(parts, translated)):
            return f"{value}〔{' '.join(translated)}〕"
        return value
    for number, line in enumerate(text.splitlines(), 1):
        translated = token.sub(translate_token, line)
        output.append(f"{number:04d}  {translated}")
    return "\n".join(output) + "\n"


def save_script_with_backup(path: Path, text: str) -> dict:
    path = path.resolve()
    backup = ""
    if path.exists():
        stamp = time.strftime("%Y%m%d-%H%M%S")
        target = APP_HOME / "script_backups" / stamp / path.name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        backup = str(target)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
    return {"path": str(path), "backup": backup, "bytes": path.stat().st_size}


def launch_tool(config: dict[str, str], key: str, log: Callable[[str], None]) -> None:
    path = Path(config[key])
    if not path.is_file():
        raise FileNotFoundError(path)
    run_process([str(path)], log, cwd=path.parent, visible=True)


def validate_mod(mod_root: Path) -> dict:
    mod_json = mod_root / "mod.json"
    if not mod_json.is_file():
        raise FileNotFoundError(mod_json)
    metadata = json.loads(mod_json.read_text(encoding="utf-8-sig"))
    models, rpaks, starpaks, errors = [], [], [], []
    for path in mod_root.rglob("*.mdl"):
        data = path.read_bytes()
        info = {"path": path.relative_to(mod_root).as_posix(), "bytes": len(data)}
        if len(data) < 8 or data[:4] != b"IDST":
            info["error"] = "invalid magic"
            errors.append(info["path"] + ": invalid MDL")
        else:
            info["version"] = struct.unpack_from("<i", data, 4)[0]
        models.append(info)
    for path in mod_root.rglob("*.rpak"):
        ok = path.read_bytes()[:4] == b"RPak"
        rpaks.append({"path": path.relative_to(mod_root).as_posix(), "bytes": path.stat().st_size, "valid": ok})
        if not ok:
            errors.append(str(path) + ": invalid RPak")
    for path in mod_root.rglob("*.starpak"):
        ok = path.read_bytes()[:4] == b"SRPk"
        starpaks.append({"path": path.relative_to(mod_root).as_posix(), "bytes": path.stat().st_size, "valid": ok})
        if not ok:
            errors.append(str(path) + ": invalid STARPAK")
    return {
        "status": "passed" if not errors else "failed",
        "validationScope": "static_structure_only",
        "runtimeStatus": "NOT_TESTED",
        "releaseAcceptance": "PENDING",
        "workflowReview": workflow_review(mod_root),
        "name": metadata.get("Name"),
        "version": metadata.get("Version"),
        "loadPriority": metadata.get("LoadPriority"),
        "files": sum(1 for path in mod_root.rglob("*") if path.is_file()),
        "models": models,
        "rpaks": rpaks,
        "starpaks": starpaks,
        "errors": errors,
    }


def scan_mods(mods_root: Path) -> dict:
    mods, names, paths = [], defaultdict(list), defaultdict(list)
    for folder in sorted(path for path in mods_root.iterdir() if path.is_dir()):
        manifest = folder / "mod.json"
        if not manifest.is_file():
            continue
        try:
            metadata = json.loads(manifest.read_text(encoding="utf-8-sig"))
        except Exception as exc:
            mods.append({"folder": folder.name, "error": str(exc)})
            continue
        item = {
            "folder": folder.name,
            "name": metadata.get("Name", folder.name),
            "version": metadata.get("Version"),
            "loadPriority": metadata.get("LoadPriority", 0),
        }
        mods.append(item)
        names[item["name"]].append(folder.name)
        for file in folder.rglob("*"):
            if file.is_file():
                relative = file.relative_to(folder).as_posix().lower()
                if relative.startswith(("mod/", "keyvalues/")):
                    paths[relative].append(folder.name)
    return {
        "mods": mods,
        "duplicateNames": {key: value for key, value in names.items() if len(value) > 1},
        "overlappingFiles": {key: value for key, value in paths.items() if len(value) > 1},
    }


def workflow_review(source: Path) -> dict:
    try:
        from .workflow_audit import audit
    except ImportError:
        from workflow_audit import audit
    return audit(source)


def package_zip(source: Path, output: Path) -> dict:
    source, output = source.resolve(), output.resolve()
    if output.is_relative_to(source):
        raise ValueError("ZIP must be outside the mod directory")
    if output.exists():
        raise FileExistsError("Use a new version filename: " + str(output))
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(source.rglob("*")):
            if path.is_file():
                archive.write(path, (Path(source.name) / path.relative_to(source)).as_posix())
    review = workflow_review(output)
    report = output.with_suffix(output.suffix + ".audit.json")
    report.write_text(json.dumps(review, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"path": str(output), "bytes": output.stat().st_size, "sha256": sha256(output),
            "audit": str(report), "runtimeStatus": "NOT_TESTED", "releaseAcceptance": "PENDING"}


def install_mod(source: Path, mods_root: Path) -> dict:
    source = source.resolve()
    mods_root = mods_root.resolve()
    target = (mods_root / source.name).resolve()
    if target.parent != mods_root:
        raise RuntimeError(f"安装目标不安全: {target}")
    stamp = time.strftime("%Y%m%d-%H%M%S")
    backup = BACKUP_DIR / stamp / source.name
    backup.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        shutil.copytree(target, backup)
        shutil.rmtree(target)
    shutil.copytree(source, target)
    source_hashes = {p.relative_to(source).as_posix(): sha256(p) for p in source.rglob("*") if p.is_file()}
    target_hashes = {p.relative_to(target).as_posix(): sha256(p) for p in target.rglob("*") if p.is_file()}
    if source_hashes != target_hashes:
        raise RuntimeError("安装后文件哈希不一致")
    return {"target": str(target), "backup": str(backup) if backup.exists() else "", "files": len(target_hashes)}


def write_report(data: dict, name: str) -> Path:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    output = LOG_DIR / f"{time.strftime('%Y%m%d-%H%M%S')}-{name}.json"
    output.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output


def self_test() -> dict:
    """Check that one-file resources resolve in the current extraction directory."""
    config = load_config()
    bundled: dict[str, dict] = {}
    errors: list[str] = []
    for key in sorted(BUNDLED_KEYS):
        path = Path(config.get(key, ""))
        exists = path.is_file()
        mz = False
        if exists:
            try:
                mz = path.read_bytes()[:2] == b"MZ"
            except OSError:
                pass
        bundled[key] = {"path": str(path), "exists": exists, "windowsExecutable": mz}
        if not exists or not mz:
            errors.append(f"{key}: bundled executable missing or invalid")

    data_files = {}
    for relative in BUNDLED_DATA:
        path = resource_path(relative)
        exists = path.is_file() and path.stat().st_size > 0
        data_files[relative] = {"path": str(path), "exists": exists}
        if not exists:
            errors.append(f"bundled data missing: {relative}")

    APP_HOME.mkdir(parents=True, exist_ok=True)
    save_config(config)
    persisted = json.loads(CONFIG_PATH.read_text(encoding="utf-8-sig"))
    stale_keys = sorted(BUNDLED_KEYS.intersection(persisted))
    if stale_keys:
        errors.append("bundled paths were persisted: " + ", ".join(stale_keys))

    external = {}
    for key in ("titanfall", "r2vanilla", "apex", "sfm_game", "studiomdl", "blender"):
        value = config.get(key, "")
        external[key] = {"path": value, "exists": bool(value) and Path(value).exists()}

    report = {
        "application": APP_NAME,
        "version": APP_VERSION,
        "status": "passed" if not errors else "failed",
        "frozen": bool(getattr(sys, "frozen", False)),
        "resourceRoot": str(resource_path(".")),
        "bundled": bundled,
        "bundledData": data_files,
        "external": external,
        "config": str(CONFIG_PATH),
        "errors": errors,
    }
    report_path = write_report(report, "self-test")
    report["report"] = str(report_path)
    return report
