from __future__ import annotations

import json
import re
import shutil
import struct
import subprocess
import os
import time
import zipfile
from pathlib import Path
from typing import Callable

import core


CATALOG_PATH = core.APP_HOME / "catalog" / "asset-catalog.json"
STGS_DIR = core.APP_HOME / "catalog" / "apex-settings"


def _rsx_runtime_dir() -> Path:
    # RSX writes its cache and fallback export directory into the process CWD.
    # Keep those mutable files in the D: application-data area, outside source
    # and outside PyInstaller's temporary extraction directory.
    path = core.APP_HOME / "cache" / "rsx-runtime"
    path.mkdir(parents=True, exist_ok=True)
    return path


def respawn_guid(name: str) -> int:
    data = name.encode() + b"\0" * 8
    value = 0
    index = 0
    mask = (1 << 64) - 1
    while True:
        word = int.from_bytes(data[index:index + 4], "little")
        v4 = (~word & (word - 0x1010101) & 0x80808080) & 0xFFFFFFFF
        v5 = (v4 ^ (v4 - 1)) & 0xFFFFFFFF
        v6 = ((v5 & word) ^ 0x5C5C5C5C) & 0xFFFFFFFF
        v7 = (~v6 & (v6 - 0x1010101) & 0x80808080) & 0xFFFFFFFF
        v8 = v7 & -v7
        if v7 != v8:
            for bit in (0xFF000000, 0xFF0000, 0xFF00, 0xFF):
                if bit & v6 == 0:
                    v8 |= bit & 0x80808080
        v11 = (0x633D5F1 * value) & mask
        v12 = ((0xFB8C4D96501 * ((((v5 & word) - 45 * (v8 >> 7)) & 0xFFFFFFFF) & 0xDFDFDFDF)) & mask) >> 24
        if v4:
            break
        total = (v11 + v12) & mask
        value = (total >> 61) ^ total
        index += 4
    return (v12 + v11 - 0xAE502812AA7333 * (index + (v5.bit_length() - 1) // 8)) & mask


def _rsx_cli(config: dict[str, str]) -> Path:
    preferred = core.resource_path("vendor/rsx/rsx_nogui.exe")
    return preferred if preferred.is_file() else Path(config["rsx"])


def _apex_settings(config: dict[str, str], log: Callable[[str], None], refresh: bool) -> Path:
    marker = STGS_DIR / ".complete"
    if marker.is_file() and not refresh:
        return STGS_DIR
    if STGS_DIR.exists():
        shutil.rmtree(STGS_DIR)
    paks = core.apex_pak_chain(Path(config["apex"]), "common")
    args = [str(_rsx_cli(config)), "-export", "-skippostload", "-exportfullpaths",
            "--loadwhitelist", "stgs", "--exporttypes", "stgs", "--exportdir", str(STGS_DIR)]
    args += [str(path) for path in paks]
    core.run_process(args, log, cwd=_rsx_runtime_dir())
    marker.write_text(time.strftime("%Y-%m-%d %H:%M:%S"), encoding="utf-8")
    return STGS_DIR


def _scan_apex(config: dict[str, str], log: Callable[[str], None], refresh: bool) -> list[dict]:
    root = _apex_settings(config, log, refresh) / "settings/itemflav/weapon_skin"
    result = []
    for path in root.rglob("*.json"):
        try:
            settings = json.loads(path.read_text(encoding="utf-8-sig"))["settings"]
        except Exception:
            continue
        view = str(settings.get("viewModel", "")).replace("\\", "/")
        if not view or "/weapons/" not in view:
            continue
        world = str(settings.get("worldModel", "")).replace("\\", "/")
        weapon = path.parent.name
        skin = path.stem
        label = str(settings.get("localizationKey_NAME", "")).lstrip("#") or skin
        skin_name = str(settings.get("skinName", "")).strip()
        # RSX model skin numbers follow the model's texturegroup. These are the
        # stable stock Apex slots; unique legendary/reactive models normally use 0.
        model_skin = {
            "common/rare mask": 1, "blue": 2, "red": 3,
            "green": 4, "aqua": 5, "purple": 6,
        }.get(skin_name.lower(), 0)
        result.append({
            "id": f"{weapon}/{skin}", "display": f"{weapon} | {label} | {skin}",
            "weapon": weapon, "skin": skin, "viewModel": view, "worldModel": world,
            "viewGuid": f"0x{respawn_guid(view):016X}",
            "worldGuid": f"0x{respawn_guid(world):016X}" if world else "",
            "camoIndex": int(settings.get("camoIndex", 0) or 0),
            "skinName": skin_name, "modelSkin": model_skin,
            "reactive": bool(settings.get("featureReactsToKills", False)),
        })
    result.sort(key=lambda row: row["display"].lower())
    log(f"Apex 武器皮肤索引：{len(result)}")
    return result


def _scan_titanfall(config: dict[str, str], log: Callable[[str], None]) -> list[dict]:
    vpk_root = Path(config["titanfall"]) / "vpk"
    found: dict[str, dict] = {}
    all_paths: set[str] = set()
    rows: list[tuple[str, Path]] = []
    for vpk in sorted(vpk_root.glob("*_dir.vpk")):
        try:
            for relative, _crc, _archive, _chunks in core._parse_vpk_directory(vpk):
                normalized = relative.replace("\\", "/")
                all_paths.add(normalized.lower())
                if normalized.lower().startswith("models/weapons/") and normalized.lower().endswith(".mdl"):
                    rows.append((normalized, vpk))
        except (ValueError, OSError):
            continue
    views = [(path, vpk) for path, vpk in rows if Path(path).name.lower().startswith(("ptpov_", "v_", "atpov_")) and "_anims." not in path.lower()]
    worlds = {Path(path).parent.as_posix().lower(): [] for path, _ in rows}
    for path, vpk in rows:
        if Path(path).name.lower().startswith("w_"):
            worlds.setdefault(Path(path).parent.as_posix().lower(), []).append((path, vpk))
    for path, vpk in views:
        folder = Path(path).parent.as_posix().lower()
        world_candidates = worlds.get(folder, [])
        stem = Path(path).stem
        include = f"{Path(path).parent.as_posix()}/{stem}_anims.mdl"
        found.setdefault(path.lower(), {
            "id": path, "display": f"{Path(path).parent.name} | {Path(path).name}",
            "viewModel": path, "viewVpk": str(vpk),
            "worldModel": world_candidates[0][0] if world_candidates else "",
            "worldVpk": str(world_candidates[0][1]) if world_candidates else "",
            "animInclude": include if include.lower() in all_paths else "",
        })
    result = sorted(found.values(), key=lambda row: row["display"].lower())
    log(f"Titanfall 2 第一人称武器索引：{len(result)}")
    return result


def scan_assets(config: dict[str, str], log: Callable[[str], None] = print, refresh: bool = False) -> dict:
    for key in ("apex", "titanfall"):
        if not Path(config.get(key, "")).is_dir():
            raise FileNotFoundError(f"{key} 目录不存在：{config.get(key, '')}")
    catalog = {
        "schema": 1, "generatedAt": time.strftime("%Y-%m-%d %H:%M:%S"),
        "apex": _scan_apex(config, log, refresh),
        "titanfall": _scan_titanfall(config, log),
    }
    CATALOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CATALOG_PATH.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    catalog["catalog"] = str(CATALOG_PATH)
    return catalog


def load_catalog() -> dict:
    if not CATALOG_PATH.is_file():
        return {"apex": [], "titanfall": []}
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8-sig"))


def extract_vpk_members(directory_vpk: Path, wanted: list[str], output: Path) -> list[Path]:
    lookup = {name.replace("\\", "/").lower() for name in wanted if name}
    extracted = []
    for relative, expected_crc, archive, chunks in core._parse_vpk_directory(directory_vpk):
        if relative.replace("\\", "/").lower() not in lookup:
            continue
        source = core._vpk_block_path(directory_vpk, archive)
        payload = bytearray()
        with source.open("rb") as handle:
            for offset, compressed, uncompressed, _flags, _texture_flags in chunks:
                if compressed != uncompressed:
                    return _harmony_extract(directory_vpk, sorted(lookup), output)
                handle.seek(offset)
                payload.extend(handle.read(compressed))
        import zlib
        if zlib.crc32(payload) & 0xFFFFFFFF != expected_crc:
            raise ValueError(f"CRC 不一致：{relative}")
        target = output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
        extracted.append(target)
    missing = lookup - {str(path.relative_to(output)).replace("\\", "/").lower() for path in extracted}
    if missing:
        raise FileNotFoundError("VPK 中未提取到：" + ", ".join(sorted(missing)))
    return extracted


def _harmony_extract(directory_vpk: Path, wanted: list[str], output: Path) -> list[Path]:
    portable = core.resource_path("vendor/tools/Harmony.VPK.Tool.1.2.1.exe")
    helper = core.resource_path("vendor/harmony/extract.js")
    if not portable.is_file() or not helper.is_file():
        raise FileNotFoundError("缺少 Harmony VPK 自动解压组件")
    started = time.time()
    creation = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    launcher = subprocess.Popen([str(portable)], creationflags=creation,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    electron = None
    try:
        temp = Path(os.environ.get("TEMP", ""))
        for _ in range(80):
            choices = [path for path in temp.glob("*/Harmony VPK Tool.exe")
                       if (path.parent / "resources/app.asar").is_file()]
            if choices:
                electron = max(choices, key=lambda path: path.stat().st_mtime)
                break
            time.sleep(0.1)
        if not electron:
            raise RuntimeError("Harmony 后端启动超时")
        env = dict(os.environ)
        env["ELECTRON_RUN_AS_NODE"] = "1"
        args = [str(electron), str(helper), str(directory_vpk), str(output), *wanted]
        subprocess.run(args, check=True, env=env, creationflags=creation)
    finally:
        subprocess.run(["taskkill", "/PID", str(launcher.pid), "/T", "/F"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=creation)
    result = [output / Path(name) for name in wanted]
    missing = [str(path) for path in result if not path.is_file()]
    if missing:
        raise FileNotFoundError("Harmony 未导出：" + ", ".join(missing))
    return result


def mdl_reference_smd(mdl: Path, output: Path) -> dict:
    data = mdl.read_bytes()
    if data[:4] != b"IDST" or struct.unpack_from("<i", data, 4)[0] != 53:
        raise ValueError(f"目标不是 Titanfall 2 v53 MDL：{mdl}")
    count, start = struct.unpack_from("<2i", data, 160)
    if count <= 0 or count > 1024 or start <= 0:
        raise ValueError("目标 MDL 骨架表无效")
    bones = []
    for index in range(count):
        pos = start + index * 244
        name_rel, parent = struct.unpack_from("<2i", data, pos)
        name_start = pos + name_rel
        name_end = data.index(0, name_start)
        name = data[name_start:name_end].decode("utf-8", errors="replace")
        xyz = struct.unpack_from("<3f", data, pos + 32)
        rot = struct.unpack_from("<3f", data, pos + 60)
        bones.append((index, name, parent, xyz, rot))
    lines = ["version 1", "nodes"]
    lines += [f'{index} "{name}" {parent}' for index, name, parent, _xyz, _rot in bones]
    lines += ["end", "skeleton", "time 0"]
    lines += [f"{index} {' '.join(f'{v:.6f}' for v in (*xyz, *rot))}" for index, _name, _parent, xyz, rot in bones]
    lines += ["end", "triangles", "end"]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"bones": count, "path": str(output)}


def _smd_materials(path: Path) -> list[str]:
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    start = lines.index("triangles") + 1
    end = lines.index("end", start)
    return sorted({lines[i].strip() for i in range(start, end, 4) if lines[i].strip()})


def _choose_meshes(export: Path) -> list[Path]:
    qcs = list(export.rglob("*.qc"))
    named = []
    if qcs:
        text = qcs[0].read_text(encoding="utf-8-sig", errors="replace")
        named = re.findall(r'^\s*\$body\s+"[^"]+"\s+"([^"]+\.smd)"', text, re.I | re.M)
        named += [name for name in re.findall(r'^\s*studio\s+"([^"]+\.smd)"', text, re.I | re.M)
                  if re.search(r"magazine|sight_front|iron", name, re.I)]
    meshes = []
    for name in named:
        candidate = qcs[0].parent / name
        if candidate.is_file() and candidate not in meshes:
            meshes.append(candidate)
    if not meshes:
        meshes = [path for path in export.rglob("*.smd") if path.stat().st_size > 9000 and "anim" not in path.name.lower()]
    if not meshes:
        raise FileNotFoundError("RSX 导出中没有可用 SMD 网格")
    return meshes


def _combine_smd(meshes: list[Path], output: Path) -> dict:
    base = meshes[0].read_text(encoding="utf-8-sig").splitlines()
    tri_start = base.index("triangles")
    base = base[:tri_start + 1]
    triangles = []
    for mesh in meshes:
        lines = mesh.read_text(encoding="utf-8-sig").splitlines()
        start = lines.index("triangles") + 1
        end = lines.index("end", start)
        triangles.extend(lines[start:end])
    output.write_text("\n".join(base + triangles + ["end"]) + "\n", encoding="utf-8")
    return {"meshes": len(meshes), "triangles": len(triangles) // 4}


def _remap_fallback(source: Path, reference: Path, output: Path, material_prefix: str) -> dict:
    src = source.read_text(encoding="utf-8-sig").splitlines()
    ref = reference.read_text(encoding="utf-8-sig").splitlines()
    _ss, _se, src_nodes = core._nodes(src)
    rs, re_, ref_nodes = core._nodes(ref)
    by_name = {name: idx for idx, (name, _parent) in ref_nodes.items()}
    fallback = next((by_name[name] for name in ("def_c_base", "weapon_bone", "jx_c_start", "jx_c_delta") if name in by_name), min(ref_nodes))
    mapping = {}
    fallback_names = []
    for old, (name, parent) in src_nodes.items():
        current = old
        while current in src_nodes and src_nodes[current][0] not in by_name and src_nodes[current][1] >= 0:
            current = src_nodes[current][1]
        target = by_name.get(src_nodes[current][0], fallback) if current in src_nodes else fallback
        mapping[old] = target
        if name not in by_name:
            fallback_names.append(name)
    sks, ske = core._section(src, "skeleton")
    rewritten = []
    seen = set()
    for line in src[sks + 1:ske]:
        parts = line.split()
        if not parts or parts[0] == "time":
            rewritten.append(line)
        else:
            parts[0] = str(mapping[int(parts[0])])
            key = (parts[0], tuple(parts[1:]))
            if key not in seen:
                rewritten.append(" ".join(parts)); seen.add(key)
    src[sks + 1:ske] = rewritten
    ts, te = core._section(src, "triangles")
    material_map = {}
    idx = ts + 1
    while idx < te:
        old_material = src[idx].strip()
        safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", old_material).strip("_") or "material"
        material_map[old_material] = f"{material_prefix}/{safe}"
        src[idx] = material_map[old_material]
        for vertex in range(idx + 1, idx + 4):
            parts = src[vertex].split()
            positions = [0]
            if len(parts) > 9:
                positions += [10 + pair * 2 for pair in range(int(parts[9]))]
            for position in positions:
                parts[position] = str(mapping.get(int(parts[position]), fallback))
            src[vertex] = " ".join(parts)
        idx += 4
    src[core._nodes(src)[0]:core._nodes(src)[1] + 1] = ref[rs:re_ + 1]
    output.write_text("\n".join(src) + "\n", encoding="utf-8")
    return {"fallbackBones": sorted(set(fallback_names)), "materials": material_map, "fallbackTarget": fallback}


def _export_model(config: dict[str, str], guid: str, skin: int, output: Path, log: Callable[[str], None]) -> None:
    paks = core.apex_pak_chain(Path(config["apex"]), "common")
    # RSX 2.3 is used for current-game indexing. Its CLI removed the legacy
    # model-format switch, so retain RSX 2.2.1 only for deterministic SMD output.
    exporter = core.resource_path("vendor/rsx/rsx_legacy_smd.exe")
    args = [str(exporter), "-nogui", "-export", "-skippostload", "-exportfullpaths", "-exportdependencies",
            "-matltextures", "--loadwhitelist", "mdl_,matl,txtr", "--exportfilter", guid,
            "--exporttypes", "mdl_,matl,txtr", "--modelsetting", "3", "--modelskin", str(skin),
            "--exportdir", str(output)]
    args += [str(path) for path in paks]
    core.run_process(args, log, cwd=_rsx_runtime_dir())
    current_output = output / "_current_materials"
    current = _rsx_cli(config)
    current_args = [str(current), "-export", "-skippostload", "-exportfullpaths", "-exportdependencies",
                    "-matltextures", "--loadwhitelist", "mdl_,matl,txtr", "--exportfilter", guid,
                    "--exporttypes", "mdl_,matl,txtr", "--exportdir", str(current_output)]
    current_args += [str(path) for path in paks]
    core.run_process(current_args, log, cwd=_rsx_runtime_dir())


def _texture_candidates(export: Path) -> dict[str, list[Path]]:
    result = {suffix: [] for suffix in ("col", "nml", "gls", "spc", "ilm", "ao", "cav")}
    for path in export.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in (".png", ".tga", ".dds", ".bmp"):
            continue
        lower = path.stem.lower()
        for suffix in result:
            if re.search(rf"(?:_|-){suffix}(?:$|[_-])", lower):
                result[suffix].append(path)
    return result


def _build_materials(config: dict[str, str], export: Path, staging: Path, material_map: dict[str, str], log: Callable[[str], None]) -> dict:
    candidates = _texture_candidates(export)
    if not candidates["col"]:
        raise FileNotFoundError("自动材质预检失败：RSX 没有导出颜色贴图；没有生成会呈紫黑格的成品")
    output = []
    for index, (old, target) in enumerate(material_map.items()):
        sources = {}
        for suffix in ("col", "nml", "gls", "spc", "ao", "cav"):
            values = candidates[suffix]
            old_key = re.sub(r"[^a-z0-9]", "", Path(old).name.lower())
            matched = [value for value in values if old_key and old_key in re.sub(r"[^a-z0-9]", "", value.as_posix().lower())]
            use = matched or values
            sources[suffix] = use[min(index, len(use) - 1)] if use else None
        # Loose Source materials are used deliberately: they do not alter global RPak layers.
        built = core.process_texture_set(config, sources, staging, target, 1024, 1.0, 1.0, 1.0,
                                         False, True, False, log)
        output.append(built)
    return {"count": len(output), "materials": [item["material"] for item in output]}


def _write_qc(path: Path, model_name: str, smd: Path, include: str) -> None:
    lines = [f'$modelname "{model_name}"', f'$body "studio" "{smd.name}"', '$surfaceprop "weapon"',
             '$contents "solid"', '$cdmaterials ""', f'$sequence "ref" "{smd.name}" fps 30 loop']
    if include:
        lines.append(f'$includemodel "{include}"')
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _decompile_stock(config: dict[str, str], stock: Path, output: Path, log: Callable[[str], None]) -> Path:
    # Titanfall v53 stores MDL/VTX/VVD sections in one monolithic file. Crowbar expects
    # the same payload through the three conventional names.
    payload = stock.read_bytes()
    # Titanfall 2 studiohdr v53 extension fields.
    vtx_start = struct.unpack_from("<i", payload, 428)[0]
    vvd_start = struct.unpack_from("<i", payload, 432)[0]
    if not (0 < vtx_start < vvd_start < len(payload)):
        raise ValueError("无法定位 v53 MDL 内嵌 VTX/VVD 段")
    stock.with_suffix(".vtx").write_bytes(payload[vtx_start:vvd_start])
    stock.with_suffix(".vvd").write_bytes(payload[vvd_start:])
    script = core.resource_path("vendor/tools/decompile_mdl53.ps1")
    powershell32 = Path(os.environ.get("WINDIR", r"C:\Windows")) / "SysWOW64/WindowsPowerShell/v1.0/powershell.exe"
    args = [str(powershell32), "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script),
            "-Crowbar", config["crowbar"], "-Model", str(stock), "-Output", str(output)]
    core.run_process(args, log, cwd=output.parent)
    qcs = list(output.glob("*.qc"))
    if not qcs:
        raise FileNotFoundError("Crowbar 未生成目标 QC")
    return qcs[0]


def _replace_qc_geometry(qc: Path, mapped: Path, model_name: str) -> None:
    lines = qc.read_text(encoding="utf-8-sig", errors="replace").splitlines()
    result = []
    inserted = False
    index = 0
    while index < len(lines):
        line = lines[index]
        if re.match(r"^\s*\$modelname\b", line, re.I):
            result.append(f'$modelname "{model_name}"')
            result.append(f'$body "studio" "{mapped.name}"')
            inserted = True
            index += 1
            continue
        if re.match(r"^\s*\$(?:bodygroup|lod|shadowlod|collisionmodel|collisionjoints)\b", line, re.I):
            index += 1
            depth = 0
            while index < len(lines):
                depth += lines[index].count("{") - lines[index].count("}")
                index += 1
                if depth <= 0 and index > 0 and "}" in lines[index - 1]:
                    break
            continue
        if re.match(r"^\s*\$body\s+", line, re.I):
            index += 1
            continue
        result.append(line)
        index += 1
    if not inserted:
        result.insert(0, f'$body "studio" "{mapped.name}"')
        result.insert(0, f'$modelname "{model_name}"')
    qc.write_text("\n".join(result) + "\n", encoding="utf-8")


def _compile_role(config: dict[str, str], source: dict, target: dict, role: str, work: Path,
                  staging: Path, slug: str, log: Callable[[str], None]) -> dict:
    model_key, guid_key, vpk_key = ("viewModel", "viewGuid", "viewVpk") if role == "view" else ("worldModel", "worldGuid", "worldVpk")
    if not source.get(model_key) or not target.get(model_key):
        return {"status": "skipped", "reason": f"{role} model unavailable"}
    export = work / f"apex_{role}"
    _export_model(config, source[guid_key], int(source.get("modelSkin", 0)), export, log)
    stock_root = work / "stock"
    stock = extract_vpk_members(Path(target[vpk_key]), [target[model_key]], stock_root)[0]
    decompiled = work / f"stock_{role}_decompiled"
    qc = _decompile_stock(config, stock, decompiled, log)
    references = list(decompiled.rglob("ref.smd")) or list(decompiled.glob("*.smd"))
    if not references:
        raise FileNotFoundError("目标武器反编译后没有参考 SMD")
    reference = references[0]
    combined = work / f"combined_{role}.smd"
    combined_info = _combine_smd(_choose_meshes(export), combined)
    mapped = work / f"mapped_{role}.smd"
    material_prefix = f"models/Weapons_R2/auto_replace/{slug}/{role}"
    remap = _remap_fallback(combined, reference, mapped, material_prefix)
    materials = _build_materials(config, export, staging, remap["materials"], log)
    shutil.copy2(mapped, decompiled / mapped.name)
    temp_model = f"workbench_auto/{slug}/{role}.mdl"
    _replace_qc_geometry(qc, decompiled / mapped.name, temp_model)
    core.compile_qc(config, qc, log)
    compiled = Path(config["sfm_game"]) / "models" / temp_model
    if not compiled.is_file():
        raise FileNotFoundError(f"StudioMDL 未生成：{compiled}")
    converted = core.convert_mdl(config, compiled, log)
    destination = staging / "mod" / target[model_key]
    destination.parent.mkdir(parents=True, exist_ok=True)
    if role == "view":
        from animated_fx import append_rui_from_reference
        rui = append_rui_from_reference(stock, converted, destination)
    else:
        # World models normally have no embedded RUI table.
        shutil.copy2(converted, destination)
        rui = {"count": 0, "status": "not-applicable"}
    # MDLShit v53 output is monolithic; external v49 VVD/VTX files must not be shipped.
    return {"status": "passed", "stock": str(stock), "output": str(destination), "companions": [],
            "combined": combined_info, "remap": remap, "materials": materials, "rui": rui}


def auto_replace(config: dict[str, str], recipe: dict, log: Callable[[str], None] = print) -> dict:
    catalog = load_catalog()
    source = next((row for row in catalog.get("apex", []) if row["id"] == recipe["sourceId"]), None)
    target = next((row for row in catalog.get("titanfall", []) if row["id"] == recipe["targetId"]), None)
    if not source or not target:
        raise KeyError("来源或目标不在当前索引中；请重新扫描")
    output_parent = Path(recipe.get("output", r"D:\TitanfallMods\AutoGenerated"))
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "_", recipe.get("modFolder", f"Auto.{source['weapon']}.{Path(target['viewModel']).parent.name}"))
    job = core.APP_HOME / "auto_jobs" / f"{time.strftime('%Y%m%d-%H%M%S')}-{slug}"
    staging = job / "staging"
    staging.mkdir(parents=True, exist_ok=True)
    steps = {"view": _compile_role(config, source, target, "view", job, staging, slug, log)}
    if recipe.get("includeWorld", True):
        steps["world"] = _compile_role(config, source, target, "world", job, staging, slug, log)
    version = str(recipe.get("version", "1.0.0"))
    package = core.assemble_mod(staging, output_parent, slug, recipe.get("modName", slug),
                                f"Apex {source['display']} -> Titanfall 2 {target['display']}; generated by Workbench",
                                version, 0, output_parent / f"{slug}-{version}.zip")
    report = {"status": package["status"], "source": source, "target": target, "preset": "compatibility",
              "scriptOverrides": 0, "loadPriority": 0, "steps": steps, "package": package,
              "runtimeStatus": "NOT_TESTED"}
    report["report"] = str(core.write_report(report, "auto-replace"))
    (job / "recipe.json").write_text(json.dumps(recipe, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def preflight(recipe: dict) -> dict:
    catalog = load_catalog()
    source = next((x for x in catalog.get("apex", []) if x["id"] == recipe.get("sourceId")), None)
    target = next((x for x in catalog.get("titanfall", []) if x["id"] == recipe.get("targetId")), None)
    checks = {
        "catalog": CATALOG_PATH.is_file(), "sourceSelected": source is not None, "targetSelected": target is not None,
        "sourceView": bool(source and source.get("viewModel")), "targetView": bool(target and target.get("viewModel")),
        "targetVpk": bool(target and Path(target.get("viewVpk", "")).is_file()),
    }
    return {"status": "passed" if all(checks.values()) else "failed", "checks": checks,
            "source": source, "target": target, "plannedLoadPriority": 0,
            "plannedScriptOverrides": 0, "preserveStockRui": True, "preserveStockAnimations": True}
