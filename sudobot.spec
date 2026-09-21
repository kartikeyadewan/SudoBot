# PyInstaller spec for SudoBot standalone executables.
#
# Usage (local Windows build):
#   python -m pip install pyinstaller rapidfuzz
#   set SUDOBOT_ARTIFACT_NAME=SudoBot-0.1.0-windows-x64
#   python -m PyInstaller sudobot.spec
#
# The artifact name is taken from the SUDOBOT_ARTIFACT_NAME environment
# variable so the same spec works for every platform CI job.
# No absolute development-machine paths are used.

import os

artifact_name = os.environ.get("SUDOBOT_ARTIFACT_NAME", "sudobot")

a = Analysis(
    ["src/sudobot/cli.py"],
    pathex=[],
    binaries=[],
    datas=[
        ("src/sudobot/integrations/bash.sh", "sudobot/integrations"),
        ("src/sudobot/integrations/powershell.ps1", "sudobot/integrations"),
        ("src/sudobot/integrations/bash-frozen.sh", "sudobot/integrations"),
        (
            "src/sudobot/integrations/powershell-frozen.ps1",
            "sudobot/integrations",
        ),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name=artifact_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
