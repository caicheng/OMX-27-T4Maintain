# patch_e2end.py - PlatformIO pre-build script (teensy40 env only)
#
# Raises the Teensy 4.0 emulated EEPROM size from the core default
# (E2END = 0x437, 1080 bytes) to 0xEF0 (3825 bytes = 15 sectors x 255,
# the official T4.0 maximum). The EEPROM fallback storage layout of this
# firmware is designed for 2048+ bytes, so the patch is required on T4.
#
# The patch edits the platform core header in-place (idempotent). It is
# applied automatically on every `pio run -e teensy40`, so a Teensy
# platform update that restores the original file is re-patched.
# NOTE: this affects every Teensy 4.0 build made with this PlatformIO
# installation on this machine.

Import("env")
from pathlib import Path

REL_PATHS = (
    "cores/teensy4/avr/eeprom.h",
    "hardware/teensy/avr/cores/teensy4/avr/eeprom.h",
)
PACKAGES = ("framework-arduinoteensy", "framework-arduino-teensy4", "framework-arduino-teensy")

targets = []
for pkg in PACKAGES:
    try:
        pkg_dir = Path(env.PioPlatform().get_package_dir(pkg))
    except Exception:
        continue
    for rel in REL_PATHS:
        p = pkg_dir / rel
        if p.exists() and p not in targets:
            targets.append(p)

# fallback: glob the whole packages folder (platform layouts vary by version)
if not targets:
    try:
        pkgs_root = Path(env.PioPlatform().get_packages_dir())
        for p in pkgs_root.glob("*/cores/teensy4/avr/eeprom.h"):
            if p not in targets:
                targets.append(p)
        for p in pkgs_root.glob("*/hardware/teensy/avr/cores/teensy4/avr/eeprom.h"):
            if p not in targets:
                targets.append(p)
    except Exception:
        pass

if not targets:
    print("[patch_e2end] WARNING: teensy4 core eeprom.h not found - "
          "E2END stays at the core default (1080B). "
          "Build will run with reduced EEPROM layout safety valve.")
else:
    for hdr in targets:
        txt = hdr.read_text(encoding="utf-8")
        if "#define E2END 0xEF0" in txt:
            continue  # already patched
        new = txt.replace("#define E2END 0x437", "#define E2END 0xEF0")
        assert new != txt, (
            "[patch_e2end] anchor '#define E2END 0x437' not found in %s - "
            "the core changed, verify the E2END section manually" % hdr
        )
        hdr.write_text(new, encoding="utf-8")
        print("[patch_e2end] patched %s : E2END 0x437 -> 0xEF0 (1080B -> 3825B)" % hdr)
