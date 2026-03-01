# Release Notes

## v1.1.0

[RFC 20260301174846](./docs/rfcs/20260301174846.md)

### Bug Fixes

- **[Windows] Registry key not written correctly** — the native messaging host manifest was not being registered in the Windows registry after running the installer, causing the browser to fail to start the API even when running as administrator. Fixed by:
  - Adding the missing `registry_path` for Chromium on Windows.
  - Using a `with` context manager for `winreg.OpenKey()` so the handle is always properly closed.
  - Wrapping each browser's registry write in `try/except` so a failure for one browser does not abort others.
- **[Windows] Manifest file overwritten when installing for multiple browsers** — each browser now gets its own manifest file (`yomitan_api_{browser}.json`) to prevent overwriting.
- **[Windows] Windows Store Python incompatibility** — the generated `.bat` file now detects Windows Store Python app execution aliases and falls back to `"python"` to avoid launch failures.
- **[Server] Crash on missing `Content-Length` header** — the server no longer crashes when a POST request omits this header; it defaults to an empty body.
- **[Server] Crash when extension is not yet ready** — `yomitan_response` is now checked for `None` and missing keys before indexing, returning a `500` response with an explanatory message instead of crashing.
- **[Server] `delete_crowbarfile()` crash on missing file** — wrapped in `try/if exists`.

### Improvements

- **Install all browsers at once** — the installer now defaults to option `0` (all browsers) instead of requiring a specific browser selection.
- **`get_message()` size guard** — rejects native messages larger than 33 MB to prevent memory exhaustion (and the `ValueError` raised by Python 3.9 on Windows for oversized reads).
- **`allow_reuse_address = True`** — prevents "address already in use" errors when restarting the server quickly.
- **`delete_crowbarfile()` in `finally` block** — guarantees cleanup on any exit path.
- **Startup wait reduced** — from 5 s to 2 s.
- **Platform alias matching** — changed from exact match to `startswith()` for better cross-platform compatibility.
- **Type annotations** — added `from typing import Any, Optional` throughout `yomitan_api.py`, `install_yomitan_api.py`, and `request_example.py`.
- **macOS install** — added `os.makedirs` and `chmod 0o755` to the macOS copy step to ensure correct permissions for native messaging.
- **General code quality** — reformatted with `ruff`; long lines split; `os.path.join` used consistently instead of string concatenation.

### Tests

- Added `tests/test_install.py` — unit tests for installer logic (`platform_data_get`, `manifest_get`, `manifest_install_file`).
- Added `tests/test_server.py` — unit tests for server functions (`error_log`, `get_message`, `delete_crowbarfile`).
