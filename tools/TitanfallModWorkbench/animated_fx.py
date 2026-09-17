"""Repeatable Titanfall 2 model animation, emissive-overlay and RUI helpers.

The module deliberately separates four asset systems which are easy to mix up:
SMD/QC animation, MDL-embedded RUI, VMT/VTF rendering, and Northstar scripts/PCF.
Recipes are data-only JSON and never launch the game or install a mod.
"""
from __future__ import annotations

import hashlib
import json
import re
import struct
from pathlib import Path
from typing import Callable

from PIL import Image
from PIL import ImageDraw, ImageFilter, ImageFont


def _resolve(base: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else base / path


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _luminance(image: Image.Image, u: float, v: float) -> int:
    x = min(image.width - 1, max(0, int((u % 1.0) * image.width)))
    y = min(image.height - 1, max(0, int(((1.0 - v) % 1.0) * image.height)))
    return max(image.getpixel((x, y))[:3])


def add_ilm_overlay(
    input_smd: Path,
    output_smd: Path,
    ilm_path: Path,
    material: str,
    threshold: int = 18,
    normal_offset: float = 0.012,
) -> dict:
    """Duplicate only triangles touching bright ILM pixels.

    Vertex bone weights and UVs are copied exactly. A small normal offset keeps
    the additive layer from z-fighting without detaching it from animation.
    """
    if not 0 <= threshold <= 255:
        raise ValueError("ILM threshold must be 0..255")
    if not 0 <= normal_offset <= 0.25:
        raise ValueError("Normal offset must be 0..0.25 model units")
    lines = input_smd.read_text(encoding="utf-8-sig").splitlines()
    start = lines.index("triangles") + 1
    end = lines.index("end", start)
    source = lines[start:end]
    ilm = Image.open(ilm_path).convert("RGBA")
    overlay: list[str] = []
    selected = 0
    for offset in range(0, len(source), 4):
        if offset + 3 >= len(source):
            break
        vertices = [source[offset + index].split() for index in (1, 2, 3)]
        uvs = [(float(row[7]), float(row[8])) for row in vertices]
        samples = [_luminance(ilm, u, v) for u, v in uvs]
        samples.append(_luminance(ilm, sum(u for u, _ in uvs) / 3, sum(v for _, v in uvs) / 3))
        if max(samples) < threshold:
            continue
        overlay.append(material.replace("\\", "/"))
        for row in vertices:
            values = row[:]
            normal = [float(value) for value in values[4:7]]
            for axis in range(3):
                values[1 + axis] = f"{float(values[1 + axis]) + normal[axis] * normal_offset:.8f}"
            overlay.append(" ".join(values))
        selected += 1
    if selected == 0:
        raise RuntimeError("ILM mask selected no triangles; lower the threshold after checking the source image")
    output_smd.parent.mkdir(parents=True, exist_ok=True)
    output_smd.write_text("\n".join(lines[:end] + overlay + ["end"]) + "\n", encoding="utf-8", newline="\n")
    return {
        "input": str(input_smd),
        "output": str(output_smd),
        "material": material,
        "threshold": threshold,
        "normalOffset": normal_offset,
        "overlayTriangles": selected,
        "overlayVertices": selected * 3,
        "sha256": _sha256(output_smd),
    }


def write_animated_vmt(
    output: Path,
    base_texture: str,
    flow_texture: str,
    color: tuple[float, float, float] = (1.0, 1.0, 1.0),
    alpha_min: float = 0.55,
    alpha_max: float = 0.90,
    period: float = 3.0,
    scroll_rate: float = 0.06,
    scroll_angle: float = 180.0,
) -> dict:
    if alpha_min < 0 or alpha_max < alpha_min:
        raise ValueError("Invalid alpha range")
    output.parent.mkdir(parents=True, exist_ok=True)
    text = (
        "UnlitTwoTexture\n{\n"
        f' "$basetexture" "{base_texture}"\n'
        f' "$texture2" "{flow_texture}"\n'
        ' "$model" "1"\n "$additive" "1"\n "$allowoverbright" "1"\n'
        f' "$translucent" "1"\n "$color2" "[{color[0]} {color[1]} {color[2]}]"\n'
        f' "$alpha" "{alpha_max}"\n "$nofog" "1"\n "$nocull" "1"\n "$nodecal" "1"\n'
        " Proxies\n {\n"
        f'  TextureScroll {{ texturescrollvar "$texture2transform" texturescrollrate "{scroll_rate}" texturescrollangle "{scroll_angle}" }}\n'
        f'  Sine {{ sineperiod "{period}" sinemin "{alpha_min}" sinemax "{alpha_max}" resultVar "$alpha" }}\n'
        " }\n}\n"
    )
    if "_rt_Camera" in text:
        raise RuntimeError("Global render-target materials are intentionally blocked for weapon overlays")
    output.write_text(text, encoding="utf-8", newline="\n")
    return {"output": str(output), "sha256": _sha256(output), "shader": "UnlitTwoTexture"}


def add_autoplay_sequence(
    input_qc: Path,
    output_qc: Path,
    name: str,
    animation_smd: str,
    fps: float = 30.0,
    delta: bool = False,
    weightlist: str = "",
) -> dict:
    if not re.fullmatch(r"[A-Za-z0-9_@.-]+", name):
        raise ValueError("Unsafe sequence name")
    text = input_qc.read_text(encoding="utf-8-sig")
    begin = f"// WORKBENCH_AUTOPLAY_BEGIN {name}"
    end = f"// WORKBENCH_AUTOPLAY_END {name}"
    if begin in text:
        pattern = re.escape(begin) + r".*?" + re.escape(end)
        text = re.sub(pattern, "", text, flags=re.S)
    options = [f"fps {fps:g}", "loop", "autoplay"]
    if delta:
        options.append("delta")
    if weightlist:
        options.append(f'weightlist "{weightlist}"')
    block = f'{begin}\n$sequence "{name}" "{animation_smd}" {" ".join(options)}\n{end}'
    output_qc.parent.mkdir(parents=True, exist_ok=True)
    output_qc.write_text(text.rstrip() + "\n\n" + block + "\n", encoding="utf-8", newline="\n")
    return {"output": str(output_qc), "name": name, "delta": delta, "fps": fps, "sha256": _sha256(output_qc)}


def render_preview_card(
    source: Path,
    output: Path,
    title: str,
    subtitle: str,
    accent: tuple[int, int, int] = (50, 200, 255),
    mask_mode: str = "bright",
) -> dict:
    """Add a restrained bloom preview to an existing Blender PNG render."""
    image = Image.open(source).convert("RGB")
    mask = Image.new("L", image.size)
    source_pixels, mask_pixels = image.load(), mask.load()
    for y in range(image.height):
        for x in range(image.width):
            r, g, b = source_pixels[x, y]
            if mask_mode == "cyan":
                value = (b - r) + (g - r)
                mask_pixels[x, y] = max(0, min(255, value * 2)) if b - r > 24 and g - r > 16 else 0
            else:
                mask_pixels[x, y] = max(0, min(255, (max(r, g, b) - 175) * 2))
    result = image.convert("RGBA")
    for radius, scale in ((7, 1.2), (20, 0.6), (42, 0.25)):
        alpha = mask.filter(ImageFilter.GaussianBlur(radius)).point(lambda value: min(255, int(value * scale)))
        glow = Image.new("RGBA", image.size, (*accent, 0))
        glow.putalpha(alpha)
        result = Image.alpha_composite(result, glow)
    draw = ImageDraw.Draw(result)
    font_root = Path(r"C:\Windows\Fonts")
    font = ImageFont.truetype(str(font_root / "segoeuib.ttf"), 44) if (font_root / "segoeuib.ttf").is_file() else ImageFont.load_default()
    small = ImageFont.truetype(str(font_root / "segoeui.ttf"), 18) if (font_root / "segoeui.ttf").is_file() else ImageFont.load_default()
    draw.rounded_rectangle((36, 36, min(image.width - 36, 1150), 136), radius=16, fill=(5, 8, 14, 225), outline=accent, width=2)
    draw.text((60, 49), title, font=font, fill=(242, 247, 255))
    draw.text((62, 108), subtitle, font=small, fill=accent)
    output.parent.mkdir(parents=True, exist_ok=True)
    result.convert("RGB").save(output, optimize=True)
    return {"output": str(output), "maskMode": mask_mode, "sha256": _sha256(output)}


def audit_squirrel_text(text: str) -> dict:
    """Cheap structural checks; this is not a replacement for the game compiler."""
    without_comments = re.sub(r"/\*.*?\*/|//[^\n]*", "", text, flags=re.S)
    issues = []
    for opening, closing, label in (("{", "}", "braces"), ("(", ")", "parentheses"), ("[", "]", "brackets")):
        depth = 0
        for character in without_comments:
            if character == opening:
                depth += 1
            elif character == closing:
                depth -= 1
                if depth < 0:
                    break
        if depth != 0:
            issues.append(f"Unbalanced {label}")
    functions = sorted(set(re.findall(r"\b(?:void|function|entity|int|float|bool|string|var|table|array)\s+([A-Za-z_]\w*)\s*\(", without_comments)))
    if "GetParticleSystemIndex" in without_comments and "PrecacheParticleSystem" not in without_comments:
        issues.append("Particle index lookup exists without an obvious PrecacheParticleSystem call")
    return {"status": "passed" if not issues else "failed", "functions": functions, "issues": issues}


def _bone_names(data: bytes) -> list[str]:
    count, start = struct.unpack_from("<2i", data, 160)
    names = []
    for index in range(count):
        record = start + index * 244
        name_start = record + struct.unpack_from("<i", data, record)[0]
        names.append(data[name_start:data.index(0, name_start)].decode("utf-8", "replace"))
    return names


def append_rui_from_reference(reference_mdl: Path, rebuilt_mdl: Path, output_mdl: Path) -> dict:
    """Copy embedded RUI records while remapping parent bone indices by name."""
    reference = reference_mdl.read_bytes()
    rebuilt = rebuilt_mdl.read_bytes()
    if reference[:4] != b"IDST" or rebuilt[:4] != b"IDST":
        raise ValueError("Both inputs must be MDL files")
    old_names, new_names = _bone_names(reference), _bone_names(rebuilt)
    count, start = struct.unpack_from("<2i", reference, 296)
    if count <= 0:
        raise ValueError("Reference model has no embedded RUI records")
    end = start + count * 8
    for index in range(count):
        header = start + index * 8
        record = header + struct.unpack_from("<i", reference, header + 4)[0]
        parent_count, vertex_count, face_count, parent_offset, vertex_offset, vertex_map_offset, face_offset = struct.unpack_from("<7i", reference, record)
        end = max(end, record + parent_offset + parent_count * 2,
                  record + vertex_offset + vertex_count * 16,
                  record + vertex_map_offset + vertex_count * 2,
                  record + face_offset + face_count * 32)
    block = bytearray(reference[start:end])
    for index in range(count):
        header = index * 8
        record = header + struct.unpack_from("<i", block, header + 4)[0]
        parent_count, _, _, parent_offset, _, _, _ = struct.unpack_from("<7i", block, record)
        for parent_index in range(parent_count):
            location = record + parent_offset + parent_index * 2
            old_index = struct.unpack_from("<h", block, location)[0]
            name = old_names[old_index]
            if name not in new_names:
                raise RuntimeError(f"RUI parent bone is missing after rebuild: {name}")
            struct.pack_into("<h", block, location, new_names.index(name))
    output = bytearray(rebuilt)
    new_start = (len(output) + 15) & ~15
    output += b"\0" * (new_start - len(output)) + block
    struct.pack_into("<2i", output, 296, count, new_start)
    struct.pack_into("<i", output, 80, len(output))
    output_mdl.parent.mkdir(parents=True, exist_ok=True)
    output_mdl.write_bytes(output)
    return {"output": str(output_mdl), "ruiRecords": count, "sha256": _sha256(output_mdl)}


def _mdl_sequences(data: bytes) -> list[dict]:
    count, start = struct.unpack_from("<2i", data, 192)
    result = []
    for index in range(count):
        record = start + index * 232
        label_start = record + struct.unpack_from("<i", data, record + 4)[0]
        label = data[label_start:data.index(0, label_start)].decode("utf-8", "replace")
        result.append({"label": label, "flags": struct.unpack_from("<I", data, record + 12)[0]})
    return result


def audit_mod(mod_root: Path, expected_sequences: list[str] | None = None, min_rui_records: int = 0) -> dict:
    mod_root = Path(mod_root)
    expected_sequences = expected_sequences or []
    manifest_path = mod_root / "mod.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    issues: list[str] = []
    warnings: list[str] = []
    if manifest.get("LoadPriority") != 0:
        warnings.append("LoadPriority is not 0")
    scripts = manifest.get("Scripts", [])
    for entry in scripts:
        path, run_on = entry.get("Path"), entry.get("RunOn")
        if not path or not run_on:
            issues.append("Every script entry needs Path and RunOn")
            continue
        script_path = mod_root / "mod/scripts/vscripts" / path
        if not script_path.is_file():
            issues.append(f"Declared script is missing: {path}")
            continue
        if not re.search(r"\b(CLIENT|SERVER|UI)\b", run_on):
            issues.append(f"Script RunOn has no VM context: {path}")
        script_audit = audit_squirrel_text(script_path.read_text(encoding="utf-8-sig", errors="replace"))
        issues.extend(f"{path}: {issue}" for issue in script_audit["issues"])
        declared_functions = set(script_audit["functions"])
        for callback_group in (entry.get("ClientCallback", {}), entry.get("ServerCallback", {})):
            for callback in callback_group.values():
                if callback not in declared_functions:
                    warnings.append(f"Callback function was not found in the declared file: {callback}")
    pcfs = list(mod_root.rglob("*.pcf"))
    particle_manifests = list(mod_root.rglob("particles_manifest.txt"))
    if pcfs and not particle_manifests:
        issues.append("PCF files exist without particles_manifest.txt")
    vmts = list(mod_root.rglob("*.vmt"))
    camera_vmts = [path for path in vmts if "_rt_Camera" in path.read_text(encoding="utf-8-sig", errors="ignore")]
    if camera_vmts:
        warnings.append("Weapon materials reference _rt_Camera and may affect screen layers")
    models = []
    found_sequences: set[str] = set()
    max_rui = 0
    for path in mod_root.rglob("*.mdl"):
        data = path.read_bytes()
        valid = data[:4] == b"IDST" and len(data) >= 304
        version = struct.unpack_from("<i", data, 4)[0] if valid else None
        rui = struct.unpack_from("<i", data, 296)[0] if valid else 0
        sequences = _mdl_sequences(data) if valid else []
        found_sequences.update(item["label"] for item in sequences)
        max_rui = max(max_rui, rui)
        models.append({"path": path.relative_to(mod_root).as_posix(), "valid": valid, "version": version, "ruiRecords": rui})
    missing_sequences = sorted(set(expected_sequences) - found_sequences)
    if missing_sequences:
        issues.append("Missing model sequences: " + ", ".join(missing_sequences))
    if max_rui < min_rui_records:
        issues.append(f"Expected at least {min_rui_records} RUI records, found {max_rui}")
    return {
        "status": "passed" if not issues else "failed",
        "mod": str(mod_root),
        "name": manifest.get("Name"),
        "version": manifest.get("Version"),
        "scripts": scripts,
        "pcfFiles": [path.relative_to(mod_root).as_posix() for path in pcfs],
        "particleManifests": [path.relative_to(mod_root).as_posix() for path in particle_manifests],
        "cameraRenderTargetMaterials": [path.relative_to(mod_root).as_posix() for path in camera_vmts],
        "models": models,
        "foundExpectedSequences": sorted(set(expected_sequences) & found_sequences),
        "issues": issues,
        "warnings": warnings,
        "runtimeTested": False,
    }


def run_recipe(recipe_path: Path, log: Callable[[str], None] | None = None) -> dict:
    recipe_path = Path(recipe_path).resolve()
    base = recipe_path.parent
    data = json.loads(recipe_path.read_text(encoding="utf-8-sig"))
    result: dict = {"recipe": str(recipe_path), "steps": {}, "runtimeTested": False}
    overlay = data.get("ilmOverlay")
    if overlay:
        result["steps"]["ilmOverlay"] = add_ilm_overlay(
            _resolve(base, overlay["inputSmd"]), _resolve(base, overlay["outputSmd"]),
            _resolve(base, overlay["ilm"]), overlay["material"],
            int(overlay.get("threshold", 18)), float(overlay.get("normalOffset", 0.012)),
        )
    vmt = data.get("animatedVmt")
    if vmt:
        color = tuple(float(value) for value in vmt.get("color", [1, 1, 1]))
        result["steps"]["animatedVmt"] = write_animated_vmt(
            _resolve(base, vmt["output"]), vmt["baseTexture"], vmt["flowTexture"], color,
            float(vmt.get("alphaMin", 0.55)), float(vmt.get("alphaMax", 0.90)),
            float(vmt.get("period", 3)), float(vmt.get("scrollRate", 0.06)),
            float(vmt.get("scrollAngle", 180)),
        )
    sequence = data.get("autoplaySequence")
    if sequence:
        result["steps"]["autoplaySequence"] = add_autoplay_sequence(
            _resolve(base, sequence["inputQc"]), _resolve(base, sequence["outputQc"]),
            sequence["name"], sequence["animationSmd"], float(sequence.get("fps", 30)),
            bool(sequence.get("delta", False)), sequence.get("weightlist", ""),
        )
    rui = data.get("preserveRui")
    if rui:
        result["steps"]["preserveRui"] = append_rui_from_reference(
            _resolve(base, rui["referenceMdl"]), _resolve(base, rui["rebuiltMdl"]),
            _resolve(base, rui["outputMdl"]),
        )
    audit = data.get("auditMod")
    if audit:
        report = audit_mod(
            _resolve(base, audit["path"]), list(audit.get("expectedSequences", [])),
            int(audit.get("minRuiRecords", 0)),
        )
        result["steps"]["auditMod"] = report
        if report["status"] != "passed":
            result["status"] = "failed"
    preview = data.get("previewCard")
    if preview:
        result["steps"]["previewCard"] = render_preview_card(
            _resolve(base, preview["source"]), _resolve(base, preview["output"]),
            preview["title"], preview.get("subtitle", ""),
            tuple(int(value) for value in preview.get("accent", [50, 200, 255])),
            preview.get("maskMode", "bright"),
        )
    result.setdefault("status", "passed")
    output = data.get("report")
    if output:
        report_path = _resolve(base, output)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        result["report"] = str(report_path)
    if log:
        log(json.dumps(result, ensure_ascii=False, indent=2))
    return result
