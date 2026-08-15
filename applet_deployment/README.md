# applet_deployment

Runs authenticated GlobalPlatform commands against a Java Card — GET STATUS,
listing installed applets, and (eventually) LOAD/INSTALL/DELETE — by opening
a GlobalPlatform Secure Channel (SCP02/SCP03) with it.

## Why this needs gp.jar

[`java_card_poc/select_card_manager.py`](../java_card_poc/select_card_manager.py)
uses `pyscard` to talk to the card directly, but `pyscard` only transmits raw
APDUs — it doesn't implement the GlobalPlatform secure-channel protocol.
Commands like `GET STATUS` are privileged: sent without an authenticated
session, the card correctly refuses with `SW=6982` ("Security status not
satisfied").

Opening that secure channel means authenticating to the Issuer Security
Domain, deriving session keys, and MACing (and often encrypting) every
subsequent APDU — a real sub-protocol, not a single command. Rather than
reimplementing SCP02/SCP03 from the GlobalPlatform spec, this project shells
out to **[GlobalPlatformPro](https://github.com/martinpaljak/GlobalPlatformPro)**
(`gp.jar`), which already implements it correctly. `gp_client.py` wraps that
CLI via `subprocess`.

## Prerequisite: install gp.jar

1. Download the latest `gp.jar` release from
   <https://github.com/martinpaljak/GlobalPlatformPro/releases>.
2. It is **not vendored in this repo** — save it anywhere on disk.
3. Point the `GP_JAR_PATH` environment variable at it:

   **PowerShell (current session):**
   ```powershell
   $env:GP_JAR_PATH = "C:\path\to\gp.jar"
   ```

   **PowerShell (persistent, User scope):**
   ```powershell
   [System.Environment]::SetEnvironmentVariable("GP_JAR_PATH", "C:\path\to\gp.jar", "User")
   ```
   Takes effect in newly launched processes/terminals only — restart VS Code
   (or open a fresh terminal outside it) to pick it up.

   **Git Bash:**
   ```bash
   export GP_JAR_PATH="/c/path/to/gp.jar"
   ```

You'll also need a Java runtime on `PATH` (`java -version`) — `gp.jar` runs
on it directly.

Without `GP_JAR_PATH` set, `gp_client.py` raises `SystemExit` with this same
instruction rather than failing with an opaque error.

## Usage

```bash
python gp_client.py
```

Runs `list_card_contents()` (prints the card's ISD/packages/applets) followed
by `get_status_applications()` (the authenticated GET STATUS — the
counterpart to `select_card_manager.py`'s attempt that fails with `SW=6982`).

Or import the pieces directly:

```python
from gp_client import list_card_contents, send_secure_apdu
from APDU import GET_STATUS_ISD

list_card_contents()
data, sw1, sw2 = send_secure_apdu(GET_STATUS_ISD)
```

## Files

- **`APDU.py`** — raw APDU byte sequences, each documented with a
  byte-by-byte breakdown (CLA/INS/P1/P2/Lc/Data) of what it means.
- **`gp_client.py`** — `subprocess` wrapper around `gp.jar`: opens the secure
  channel, sends a command, parses the result out of `gp.jar`'s debug trace.
- **`constants.py`** — reader name, `GP_JAR_PATH`, shared status-word
  constants.

## Note on keys

`gp.jar` falls back to the well-known GlobalPlatform default test key set
(`40 41 42 ... 4F`) when no `-k`/`--key-enc`/`--key-mac`/`--key-dek` is
given — you'll see `# Warning: no keys given, defaulting to ...` in its
output. That's expected on a test/dev card that hasn't had its keys rotated.
`run_gp()` doesn't currently pass any key arguments through; if you're
working against a card with non-default keys, that needs adding before
these functions will authenticate successfully.
