# Additive + PCF rebuild (2026-09-17)

- CAR Mythic: uses the RSX-exported Apex `__sub_...` feather, fire, and kill-react SMDs as baked delta layers. Only weapon/eye/wing/feather bones are copied; TF2 camera, hands, optics, and aim bones remain untouched.
- Double Take: the current Apex install no longer contains the indexed Huntersafari reactive ASeq assets. The rotating time-machine rings were rebuilt as a proper frame-0-relative delta autoplay layer on the four exact Apex helper bones.
- Particle systems: built from a locally installed Titanfall 2 PCF, uniquely namespaced per mod, declared in `particles_manifest.txt`, and triggered/stopped by QC animation events at valid frames.
- The RUI editor/tool task remains paused.
- These builds passed offline compile, MDL53 conversion, RUI-record, PCF readback, manifest, ZIP and hash checks. They were not launched in game.
