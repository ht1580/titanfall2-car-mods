# Delta / PCF corrected source package (2026-09-17)

- CAR: Apex feather Delta is composed into the existing `idle_anim_autoplay` and `idle_ads_anim_autoplay`; the fire Delta is composed into existing attack SMDs. No standalone reactive autoplay sequence is created.
- Double Take: frame-0-relative ring Delta is composed into the existing idle and ADS idle autoplay SMDs. No standalone rotor autoplay sequence remains.
- PCF: event names in QC exactly match the reverse-decoded PCF systems. The shipped manifest is the full vanilla frontend manifest with one custom PCF entry appended, preventing loss of map/environment particle registrations.
- RUI: Double Take retains five embedded stock RUI records and stock optics.
- Runtime status: compiled and statically audited only; no game launch was performed.

Run `rebuild_additive_pcf.py` from the original project layout to reproduce the packages.
