"""
Opens a GlobalPlatform Secure Channel (SCP02/SCP03) with the card and runs
authenticated commands, by shelling out to GlobalPlatformPro (gp.jar).

pyscard (see java_card_poc/select_card_manager.py) can transmit raw APDUs,
but it doesn't speak the GlobalPlatform secure-channel protocol -- commands
like GET STATUS require an authenticated session first (SW=6982 otherwise).
gp.jar implements that protocol; this module wraps it for scripted use.

Every invocation is a fresh gp.jar process: connect, authenticate SCP,
run the requested command(s), disconnect. There's no persistent Python-side
session to hold open between calls.
"""

import os
import re
import subprocess
import sys

if __name__ == "__main__":
    # Running this file directly (`python gp_client.py`) only puts this
    # file's own directory on sys.path, not the repo root -- so the
    # applet_deployment.* absolute imports below can't resolve without this.
    # Not needed when imported normally (e.g. `from applet_deployment.gp_client
    # import ...`), since the importer already has the repo root on sys.path.
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from applet_deployment.constants.APDU import _APDU_RESPONSE_RE, GET_STATUS_APPLICATIONS
from applet_deployment.constants.constants import GP_JAR_PATH, SMARTCARD_READER, SW_SUCCESS
from applet_deployment.constants.create_bitcoin_address import (
    AID as CREATE_BITCOIN_ADDRESS_AID,
    INS_GENERATE_ENTROPY,
)


def run_gp(*args):
    """Run gp.jar against the configured reader with debug tracing on.
    Returns the completed subprocess (stdout/stderr captured as text)."""
    if not GP_JAR_PATH:
        raise SystemExit(
            "GP_JAR_PATH is not set. Point it at your GlobalPlatformPro jar "
            "(https://github.com/martinpaljak/GlobalPlatformPro/releases)."
        )
    cmd = ["java", "-jar", GP_JAR_PATH, "-r", SMARTCARD_READER, "-d", *args]
    return subprocess.run(cmd, capture_output=True, text=True)


def _apdu_responses(stdout):
    """
    returns: [(data_hex, sw1, sw2), ...] for every APDU exchanged, in order.
    """
    responses = []
    for line in stdout.splitlines():
        m = _APDU_RESPONSE_RE.match(line.strip())
        if m:
            data, sw = m.group(1) or "", m.group(2)
            responses.append((data.upper(), int(sw[:2], 16), int(sw[2:], 16)))
    return responses


def _last_apdu_response(stdout):
    """
    returns: (data_hex, sw1, sw2) for the last APDU exchange, or None.
    """
    responses = _apdu_responses(stdout)
    return responses[-1] if responses else None


def list_card_contents():
    """Open a secure channel (default GlobalPlatform test keys unless gp.jar
    is configured otherwise) and print the card's ISD, packages and applets."""
    result = run_gp("--list")
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr)
    return result


def send_secure_apdu(hex_apdu):
    """
    open a secure channel and send a single APDU over it.
    returns: (data_hex, sw1, sw2)
    """
    result = run_gp("-s", hex_apdu)
    response = _last_apdu_response(result.stdout)
    if response is None:
        raise RuntimeError(f"No APDU response captured:\n{result.stderr}")
    return response


def send_apdu_to_applet(aid_hex, hex_apdu):
    """
    SELECT an already-installed applet and send it one raw APDU -- no
    GlobalPlatform secure channel involved, since talking to a regular
    applet (as opposed to a security domain) doesn't need one.

    Deliberately uses -a (plain), not -s (secure) or --connect. --connect
    makes gp.jar assume it's talking to a security domain and attempt to
    open a secure channel first; confirmed by testing against
    CreateBitcoinAddressApplet that this fails with SW=6D00, since a
    regular applet doesn't implement INITIALIZE UPDATE.

    returns: (data_hex, sw1, sw2) for the command APDU's response (not the
    SELECT's).
    """
    select_apdu = f"00A40400{len(aid_hex) // 2:02X}{aid_hex}"
    result = run_gp("-a", select_apdu, "-a", hex_apdu)
    responses = _apdu_responses(result.stdout)
    if len(responses) < 2:
        raise RuntimeError(
            f"Expected 2 APDU responses (SELECT + command), got {len(responses)}:\n"
            f"{result.stdout}\n{result.stderr}"
        )
    _select_data, select_sw1, select_sw2 = responses[0]
    if (select_sw1, select_sw2) != SW_SUCCESS:
        raise RuntimeError(f"SELECT {aid_hex} failed: {select_sw1:02X}{select_sw2:02X}")
    return responses[1]


def generate_entropy():
    """Calls CreateBitcoinAddressApplet.generate_entropy(): 256 bits
    (32 bytes) straight from the card's hardware TRNG (ALG_TRNG, no DRBG
    conditioning)."""
    data, sw1, sw2 = send_apdu_to_applet(
        CREATE_BITCOIN_ADDRESS_AID, f"00{INS_GENERATE_ENTROPY}000020"
    )
    if (sw1, sw2) != SW_SUCCESS:
        raise RuntimeError(f"generate_entropy failed: {sw1:02X}{sw2:02X}")
    print(f"generate_entropy -> {data} ({len(data) // 2} bytes)")
    return data


def get_status_applications():
    """GET STATUS over a secure channel."""
    data, sw1, sw2 = send_secure_apdu(GET_STATUS_APPLICATIONS)
    print(f"GET STATUS (apps) -> {data} {sw1:02X}{sw2:02X}")
    if (sw1, sw2) == SW_SUCCESS:
        print("Success: no applets installed" if not data else "Success")
    else:
        print("Card returned a non-success status word")
    return data, sw1, sw2


if __name__ == "__main__":
    generate_entropy()