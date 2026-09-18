from __future__ import annotations

import hashlib
import json
import re
import shutil
import struct
import subprocess
import sys
import zipfile
from pathlib import Path


ROOT = Path(r"D:\TitanfallMods\23_AdditivePCF_Rebuild")
RELEASE = ROOT / "release"
WORK = ROOT / "work"
PROJECT = Path(r"D:\CodexStorage\Projects\2026-09-08\w-3")
WORKBENCH = PROJECT / "TitanfallModWorkbench"
sys.path.insert(0, str(WORKBENCH.parent))
from TitanfallModWorkbench import core  # noqa: E402

CONFIG = core.load_config()
MYTHIC_PROJECT = PROJECT / "work" / "car_mythic"
MYTHIC_MOD_SOURCE = Path(r"D:\TitanfallMods\17_ReferenceRepair\CAR.Mythic.Allfather")
MYTHIC_GLOW_ZIP = Path(r"D:\TitanfallMods\22_AnimatedFX\CAR.Mythic.Allfather-1.2.0-animatedfx.zip")
NATIVE = MYTHIC_PROJECT / "apex_native/animrig/techart/mshop/weapons/class/smg/car/anims_car_mythic_v25_nogo_level2_v_animRig"
DOUBLE_MOD_SOURCE = Path(r"D:\TitanfallMods\21_DoubleTakeUIRotors\Codex.DoubleTake.HunterSafari")
DOUBLE_VIEW_SOURCE = Path(r"D:\TitanfallMods\22_AnimatedFX\doubletake_view_source")
DOUBLE_WORLD_SOURCE = Path(r"D:\TitanfallMods\22_AnimatedFX\doubletake_world_source")
PARTICLE_SOURCE = MYTHIC_PROJECT / "fx_assets/mod/particles/codex_car_mythic_glow.pcf"
PARTICLE_TEXT = MYTHIC_PROJECT / "fx_assets/source/codex_car_mythic_glow.pcf.txt"
DMX = Path(r"E:\SteamLibrary\steamapps\common\SourceFilmmaker\game\bin\dmxconvert.exe")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def zip_folder(folder: Path, archive: Path) -> None:
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for file in sorted(folder.rglob("*")):
            if file.is_file():
                z.write(file, Path(folder.name) / file.relative_to(folder))
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None


def read_smd(path: Path):
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    na = lines.index("nodes")
    nb = lines.index("end", na)
    nodes = {}
    for line in lines[na + 1 : nb]:
        m = re.match(r'\s*(\d+) "([^"]+)" (-?\d+)', line)
        if m:
            nodes[int(m.group(1))] = (m.group(2), int(m.group(3)))
    sa = lines.index("skeleton")
    sb = lines.index("end", sa)
    frames = []
    for line in lines[sa + 1 : sb]:
        words = line.split()
        if not words:
            continue
        if words[0] == "time":
            frames.append({})
        else:
            frames[-1][int(words[0])] = tuple(float(x) for x in words[1:7])
    return nodes, frames


def write_smd(path: Path, nodes, frames) -> None:
    out = ["version 1", "nodes"]
    out += [f'{i} "{name}" {parent}' for i, (name, parent) in nodes.items()]
    out += ["end", "skeleton"]
    for frame_index, frame in enumerate(frames):
        out.append(f"time {frame_index}")
        for i in nodes:
            values = frame.get(i, (0.0,) * 6)
            out.append(f"{i} " + " ".join(f"{x:.9f}" for x in values))
    out += ["end"]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")


def effect_bone(name: str) -> bool:
    return (
        name.startswith("def_body_feather_")
        or name.startswith("def_wing_")
        or name in {
            "def_upper_body",
            "def_core",
            "def_core_orb",
            "def_iris",
            "def_upper_lid",
            "def_lower_lid",
            "def_eye_lid_cover",
            "def_bifrost_core",
        }
    )


def remap_baked_delta(source: Path, target_reference: Path, output: Path) -> dict:
    target_nodes, _ = read_smd(target_reference)
    source_nodes, source_frames = read_smd(source)
    source_by_name = {name: i for i, (name, _) in source_nodes.items()}
    selected = [name for _, (name, _) in target_nodes.items() if effect_bone(name) and name in source_by_name]
    frames = []
    for source_frame in source_frames:
        frame = {}
        for i, (name, _) in target_nodes.items():
            frame[i] = source_frame[source_by_name[name]] if name in selected else (0.0,) * 6
        frames.append(frame)
    write_smd(output, target_nodes, frames)
    return {"source": str(source), "output": str(output), "frames": len(frames), "bones": selected}


def convert_full_to_delta(source: Path, output: Path, selected_names: set[str] | None = None) -> dict:
    nodes, frames = read_smd(source)
    base = frames[0]
    selected = []
    out_frames = []
    for frame in frames:
        result = {}
        for i, (name, _) in nodes.items():
            allowed = selected_names is None or name in selected_names
            if allowed:
                # SMD Euler values here are continuous authored rotations. The subtraction mirrors
                # the tutorial's subtract(reference, frame 0) result without altering the bind pose.
                result[i] = tuple(frame[i][j] - base[i][j] for j in range(6))
                if name not in selected and any(abs(x) > 1e-7 for x in result[i]):
                    selected.append(name)
            else:
                result[i] = (0.0,) * 6
        out_frames.append(result)
    write_smd(output, nodes, out_frames)
    return {"source": str(source), "output": str(output), "frames": len(frames), "bones": selected}


def add_attachment(qc_text: str, name: str, bone: str) -> str:
    if re.search(rf'^\$attachment\s+"{re.escape(name)}"', qc_text, re.M):
        return qc_text
    marker = '$attachment "MENU_ROTATE"'
    at = qc_text.find(marker)
    if at < 0:
        raise RuntimeError(f"attachment insertion marker absent: {name}")
    return qc_text[:at] + f'$attachment "{name}" "{bone}" 0 0 0 rotate 0 0 0\n' + qc_text[at:]


def add_event_to_sequences(qc_text: str, sequence_names: list[str], event: str) -> tuple[str, list[str]]:
    changed = []
    for name in sequence_names:
        pattern = re.compile(rf'(\$sequence\s+"{re.escape(name)}"\s*\{{)')
        if pattern.search(qc_text):
            qc_text = pattern.sub(rf'\1\n\t{{ event "AE_CL_CREATE_PARTICLE_EFFECT" 0 "{event}" }}', qc_text, count=1)
            changed.append(name)
    return qc_text, changed


def build_pcf(prefix: str, output_dir: Path, color_replacements: list[tuple[str, str]]) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    text = PARTICLE_TEXT.read_text(encoding="utf-8")
    text = text.replace("codex_car_mythic_", prefix)
    for old, new in color_replacements:
        text = text.replace(old, new)
    text_path = output_dir / f"{prefix.rstrip('_')}.pcf.txt"
    pcf_path = output_dir / f"{prefix.rstrip('_')}.pcf"
    text_path.write_text(text, encoding="utf-8", newline="\n")
    subprocess.run([str(DMX), "-i", str(text_path), "-ie", "keyvalues2", "-o", str(pcf_path), "-oe", "binary", "-of", "pcf"], check=True)
    systems = re.findall(r'"name" "string" "(' + re.escape(prefix) + r'[^"]+)"', text)
    text_path.unlink()
    return {"pcf": str(pcf_path), "systems": sorted(set(systems)), "root": prefix + "wpn_muzzleflash_xo_elec_FP"}


def compile_model(qc: Path, log_path: Path) -> Path:
    with log_path.open("w", encoding="utf-8") as log:
        core.compile_qc(CONFIG, qc, lambda line: log.write(str(line) + "\n"))
    model_name = re.search(r'^\$modelname\s+"([^"]+)"', qc.read_text(encoding="utf-8-sig"), re.M).group(1)
    mdl = Path(CONFIG["sfm_game"]) / "models" / model_name
    with log_path.with_name(log_path.stem + "-convert.log").open("w", encoding="utf-8") as log:
        return core.convert_mdl(CONFIG, mdl, lambda line: log.write(str(line) + "\n"))


def model_sequences(data: bytes) -> list[dict]:
    count, offset = struct.unpack_from("<2i", data, 192)
    rows = []
    for index in range(count):
        base = offset + index * 232
        label_start = base + struct.unpack_from("<i", data, base + 4)[0]
        label = data[label_start : data.index(0, label_start)].decode("utf-8", "replace")
        rows.append({"label": label, "flags": struct.unpack_from("<I", data, base + 12)[0]})
    return rows


def bone_names(data: bytes) -> list[str]:
    count, start = struct.unpack_from("<2i", data, 160)
    names = []
    for index in range(count):
        record = start + index * 244
        name_start = record + struct.unpack_from("<i", data, record)[0]
        names.append(data[name_start : data.index(0, name_start)].decode("utf-8", "replace"))
    return names


def append_stock_rui(model: bytes) -> tuple[bytes, int]:
    stock = Path(r"D:\TitanfallMods\14_DoubleTake_Hunter\stock\ptpov_doubletake.mdl").read_bytes()
    old_names, new_names = bone_names(stock), bone_names(model)
    count, start = struct.unpack_from("<2i", stock, 296)
    end = start + count * 8
    for index in range(count):
        header = start + index * 8
        record = header + struct.unpack_from("<i", stock, header + 4)[0]
        pc, vc, fc, po, vo, vmo, fo = struct.unpack_from("<7i", stock, record)
        end = max(end, record + po + pc * 2, record + vo + vc * 16, record + vmo + vc * 2, record + fo + fc * 32)
    block = bytearray(stock[start:end])
    for index in range(count):
        header = index * 8
        record = header + struct.unpack_from("<i", block, header + 4)[0]
        parent_count, _, _, parent_offset, _, _, _ = struct.unpack_from("<7i", block, record)
        for pi in range(parent_count):
            loc = record + parent_offset + pi * 2
            old_index = struct.unpack_from("<h", block, loc)[0]
            struct.pack_into("<h", block, loc, new_names.index(old_names[old_index]))
    output = bytearray(model)
    new_start = (len(output) + 15) & ~15
    output += b"\0" * (new_start - len(output)) + block
    struct.pack_into("<2i", output, 296, count, new_start)
    struct.pack_into("<i", output, 80, len(output))
    return bytes(output), count


def copy_glow_materials(destination: Path) -> None:
    prefix = "CAR.Mythic.Allfather/mod/materials/models/codex_car_mythic_glow/"
    with zipfile.ZipFile(MYTHIC_GLOW_ZIP) as z:
        for name in z.namelist():
            if name.startswith(prefix) and not name.endswith("/"):
                target = destination / "mod/materials/models/codex_car_mythic_glow" / Path(name).name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(z.read(name))


def build_mythic() -> dict:
    work = WORK / "mythic_view"
    destination = RELEASE / "CAR.Mythic.Allfather"
    shutil.copytree(MYTHIC_PROJECT / "source/view", work)
    shutil.copytree(MYTHIC_MOD_SOURCE, destination)
    copy_glow_materials(destination)
    ref = work / "mythic_evolved.smd"
    native_dir = work / "native_additive"
    feather = remap_baked_delta(next(NATIVE.glob("*feather_pose_tweak*")), ref, native_dir / "feather_native_delta.smd")
    killreact = remap_baked_delta(next(NATIVE.glob("*killreact_tier2*")), ref, native_dir / "killreact_native_delta.smd")
    fire = remap_baked_delta(next(NATIVE.glob("*fire_layer_tier2*")), ref, native_dir / "fire_native_delta.smd")
    qc = work / "ptpov_car101.qc"
    text = qc.read_text(encoding="utf-8-sig")
    text = add_attachment(text, "VFX_eye", "def_core_orb")
    text = add_attachment(text, "VFX_base", "def_c_base")
    event = "codex_car_mythic_wpn_muzzleflash_xo_elec_FP follow_attachment VFX_base"
    text, attack_events = add_event_to_sequences(text, ["attack_seq", "attack_seq_regrip", "attack_seq_alt1", "attack_seq_regrip_alt1", "attack_seq_alt2", "attack_seq_regrip_alt2"], event)
    text += (
        '\n// Native Apex additive layers. __sub files are already baked delta; do not subtract again.\n'
        '$sequence "mythic_feather_native" "native_additive\\feather_native_delta.smd" {\n'
        '\tfps 30\n\tloop\n\tdelta\n\tautoplay\n'
        '\t{ event "AE_CL_CREATE_PARTICLE_EFFECT" 0 "codex_car_mythic_mflash_xo_elec_glow follow_attachment VFX_eye" }\n'
        '\t{ event "AE_CL_STOP_PARTICLE_EFFECT" 189 "codex_car_mythic_mflash_xo_elec_glow 0" }\n}\n'
        '$sequence "mythic_fire_native" "native_additive\\fire_native_delta.smd" fps 30 delta\n'
        '$sequence "mythic_killreact_native" "native_additive\\killreact_native_delta.smd" fps 30 delta\n'
    )
    qc.write_text(text, encoding="utf-8", newline="\n")
    pcf = build_pcf("codex_car_mythic_", destination / "mod/particles", [])
    (destination / "mod/particles/particles_manifest.txt").write_text(
        f'particles_manifest\n{{\n\t"file"\t"particles/{Path(pcf["pcf"]).name}"\n}}\n', encoding="utf-8"
    )
    compiled = compile_model(qc, ROOT / "mythic-view-build.log")
    target = destination / "mod/models/weapons/car101/ptpov_car101.mdl"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(compiled.read_bytes())
    metadata_path = destination / "mod.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8-sig"))
    metadata.update(Version="1.3.0-additive-pcf", LoadPriority=0, Description="Native Apex CAR weapon-only delta layers plus namespaced TF2-compatible PCF events; camera, hands and sights remain on TF2 animations.")
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    sequences = model_sequences(target.read_bytes())
    for required in ("mythic_feather_native", "mythic_fire_native", "mythic_killreact_native"):
        row = next(x for x in sequences if x["label"] == required)
        assert row["flags"] & 4
    archive = RELEASE / "CAR.Mythic.Allfather-1.3.0-additive-pcf.zip"
    zip_folder(destination, archive)
    return {"folder": str(destination), "zip": str(archive), "sha256": sha256(archive), "layers": [feather, fire, killreact], "attackEventSequences": attack_events, "pcf": pcf}


def build_double() -> dict:
    work = WORK / "double_view"
    destination = RELEASE / "Codex.DoubleTake.HunterSafari"
    shutil.copytree(DOUBLE_VIEW_SOURCE, work)
    shutil.copytree(DOUBLE_MOD_SOURCE, destination)
    selected = {"def_c_timemachine_core", "def_c_timemachine_ring_01", "def_c_timemachine_ring_02", "def_c_timemachine_ring_03"}
    rotor = convert_full_to_delta(work / "hunter_rotor_spin.smd", work / "hunter_rotor_delta.smd", selected)
    qc = work / "ptpov_doubletake.qc"
    text = qc.read_text(encoding="utf-8-sig")
    text = re.sub(r'^\$sequence\s+"hunter_rotors_autoplay".*$', '$sequence "hunter_rotors_additive" "hunter_rotor_delta.smd" {\n\tfps 30\n\tloop\n\tdelta\n\tautoplay\n\t{ event "AE_CL_CREATE_PARTICLE_EFFECT" 0 "codex_doubletake_hunter_mflash_xo_elec_glow follow_attachment hunter_fx" }\n\t{ event "AE_CL_STOP_PARTICLE_EFFECT" 29 "codex_doubletake_hunter_mflash_xo_elec_glow 0" }\n}', text, flags=re.M)
    text = add_attachment(text, "hunter_fx", "def_c_timemachine_core")
    event = "codex_doubletake_hunter_wpn_muzzleflash_xo_elec_FP follow_attachment muzzle_flash"
    text, attack_events = add_event_to_sequences(text, ["attack_seq", "attack_seq_regrip", "attack_seq_alt1", "attack_seq_regrip_alt1", "attack_seq_alt2", "attack_seq_regrip_alt2"], event)
    qc.write_text(text, encoding="utf-8", newline="\n")
    pcf = build_pcf("codex_doubletake_hunter_", destination / "mod/particles", [("255 190 72 255", "80 210 255 255"), ("174 92 255 255", "210 150 62 255")])
    (destination / "mod/particles/particles_manifest.txt").write_text(
        f'particles_manifest\n{{\n\t"file"\t"particles/{Path(pcf["pcf"]).name}"\n}}\n', encoding="utf-8"
    )
    compiled = compile_model(qc, ROOT / "double-view-build.log")
    view_data, rui_count = append_stock_rui(compiled.read_bytes())
    target = destination / "mod/models/weapons/doubletake/ptpov_doubletake.mdl"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(view_data)
    metadata_path = destination / "mod.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8-sig"))
    metadata.update(Version="1.0.9-additive-pcf", LoadPriority=0, Description="Stock optics and five RUI meshes retained; time-machine rings rebuilt as a proper delta autoplay layer with namespaced TF2-compatible PCF events.")
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    sequences = model_sequences(view_data)
    row = next(x for x in sequences if x["label"] == "hunter_rotors_additive")
    assert row["flags"] & 4 and row["flags"] & 8
    assert rui_count == 5
    for required in (b"doubletake_rui_lower", b"doubletake_rui_upper", b"pro_screen_rui_upper", b"attach_scope_ads_2_crosshair"):
        assert required in view_data
    archive = RELEASE / "Codex.DoubleTake.HunterSafari-1.0.9-additive-pcf.zip"
    zip_folder(destination, archive)
    return {"folder": str(destination), "zip": str(archive), "sha256": sha256(archive), "rotor": rotor, "ruiRecords": rui_count, "attackEventSequences": attack_events, "pcf": pcf}


def main() -> None:
    if WORK.exists():
        shutil.rmtree(WORK)
    if RELEASE.exists():
        shutil.rmtree(RELEASE)
    WORK.mkdir(parents=True)
    RELEASE.mkdir(parents=True)
    report = {"builtAt": "2026-09-17", "runtimeTested": False, "ruiEditorWorkPaused": True, "mythic": build_mythic(), "doubleTake": build_double()}
    (ROOT / "FINAL-AUDIT.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
