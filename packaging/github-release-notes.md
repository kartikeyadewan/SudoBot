# SudoBot 0.1.2

Offline-first CLI typo correction utility. When you mistype a command,
SudoBot suggests the intended command and asks for confirmation before
executing it. No network, no AI, no background processes.

## Downloads

| File | Platform | Notes |
|---|---|---|
| `SudoBot-0.1.2-windows-x64.exe` | Windows 10/11, x86_64 | Standalone, no Python needed |
| `sudobot-0.1.2-linux-x86_64` | Linux, x86_64 | Standalone, no Python needed |
| `SudoBot-0.1.2-x86_64.AppImage` | Linux, x86_64 | Portable app, no install needed |
| `SHA256SUMS` | All | Checksums for every file above |

Verify after downloading (Linux example):

```bash
sha256sum -c SHA256SUMS
```

## Quick start

Windows (PowerShell):

```powershell
# Place the .exe somewhere on PATH, then optionally:
sudobot --install
```

Linux (binary):

```bash
chmod +x sudobot-0.1.2-linux-x86_64
sudo mv sudobot-0.1.2-linux-x86_64 /usr/local/bin/sudobot
sudobot --install   # Bash integration
```

Linux (AppImage):

```bash
chmod +x SudoBot-0.1.2-x86_64.AppImage
./SudoBot-0.1.2-x86_64.AppImage --version
```

## Notes

- Supported architecture is currently **x86_64/amd64** only.
- The Linux binary is built on Ubuntu and links against the system glibc;
  very old distributions may be incompatible. The AppImage carries its own
  userspace payload and is the more portable Linux option, but it cannot be
  guaranteed to run on every distribution.
- Shell integrations: Bash (`command_not_found_handle`) and PowerShell
  (error trap). `sudobot --install` / `sudobot --uninstall` manage them.
- Fixes the 0.1.0 Windows standalone installer bug where `sudobot
  --install` failed with `PermissionError` on the literal `$PROFILE`
  path; the profile is now resolved natively and non-admin install works.
- Fixes PowerShell command interception: the ineffective profile-scope
  `trap` is replaced by the `CommandNotFoundAction` lookup hook, with
  full argument preservation and visible native command output.
- Alternative Python installation: `pip install sudobot` (requires Python
  3.10+), then `sudobot --install`. PyPI publication status may vary; see
  the project README.
- Debian/RPM/Arch packaging files in the repository are groundwork only and
  are not published to distro repositories.
