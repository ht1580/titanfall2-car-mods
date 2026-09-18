# 2026-09-18 PCF guide repair candidate

CAR Mythic 1.3.2 / Double Take HunterSafari 1.0.11.

Fixed offline-confirmed issues:
- Replace rounded 31-to-191 frame rotor sampling with 191 analytic samples. All three rings complete integer revolutions and close without a seam jump.
- Restore the original Apex rotor bone local orientations that the earlier importer replaced with zero rotation. Preserve mesh vertices and scale.
- Restore missing Double Take energy.vmt, energy.vtf and flow.vtf used by the emissive mesh overlay.
- Correct SMD Euler XYZ conversion to Rz*Ry*Rx.
- Shorten particle effect identifiers to fit the compiled MDL event's 64-byte options buffer. Maximum used payload is 62 bytes. Final MDL event names and options were read back.
- Ship identical shared PCF and vanilla-plus-custom manifest in both mods so these two mods cannot mask each other's custom PCF registration. This does not establish compatibility with arbitrary third-party manifest replacements.
- Set the persistent glow's view-model flag and limit emission duration. Add stop/create events to ordinary draw, raise and idle sequences as well as the original idle autoplay sequence. Actual runtime dispatch remains unverified.
- Read back the shared binary PCF: 38 named systems; all referenced custom effects resolve. Ten referenced particle VMT files are present in vanilla mp_common VPK.

The supplied PCF guide was followed for resource/manifest/event/compile structure. This build uses text editing and dmxconvert, not an Alien Swarm Particle Editor visual validation. No game was launched. Do not interpret static validation as proof that CAR light effects now render or that every in-game pose is correct.

The additive effect remains baked into original idle and ADS idle channels. No separate reactive autoplay sequence is introduced. LoadPriority remains 0. Original selectable optics and five Double Take RUI records remain.

Outputs are candidates for user evaluation. The latest local log did not expose a particle-specific failure, so absence of CAR FX is not yet traced to a single runtime cause.
