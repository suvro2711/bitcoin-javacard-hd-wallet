"""
Pulls raw bytes out of RandomNumberApplet's javacard.security.RandomData
generators, to be run through an entropy analyzer (tools/ent_src/ent.exe) --
empirical evidence about this card's RNG quality, instead of trusting a
datasheet claim.

No secure channel needed here: once an applet is installed, talking to it is
a plain SELECT + APDU exchange (same as select_card_manager.py's ISD SELECT).
The secure channel (see ../gp_client.py) is only required for GlobalPlatform
card-management commands like GET STATUS/LOAD/INSTALL -- installing this
applet in the first place used that path, not this one.

Prerequisite: build and install the applet once --
    (from random_number_generator/, with JDK 11 and ant on PATH)
    ant -f build.xml build
    java -jar <gp.jar> --install out/random_number_generator.cap
"""

import os
import sys

if __name__ == "__main__":
    # Running this file directly only puts this file's own directory on
    # sys.path, not the repo root -- so the applet_deployment.* absolute
    # import below can't resolve without this. Two levels up: applets/ ->
    # applet_deployment/ -> repo root.
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from smartcard.System import readers
from smartcard.util import toHexString

from applet_deployment.constants.constants import SMARTCARD_READER

# RandomNumberApplet AID -- see random_number_generator/build.xml.
APPLET_AID = [0xA0, 0x00, 0x00, 0x00, 0x01, 0x02, 0x01, 0x00, 0x01]

INS_GET_RANDOM = 0x20

# javacard.security.RandomData algorithm constants (confirmed against
# api_classic.jar in the jc305u3_kit SDK -- see RandomNumberApplet.java).
ALG_PSEUDO_RANDOM = 0x01  # software PRNG
ALG_SECURE_RANDOM = 0x02  # hardware-backed, DRBG-conditioned
ALG_TRNG = 0x03           # raw hardware TRNG, no DRBG conditioning (may be unsupported)

ALGORITHM_NAMES = {
    ALG_PSEUDO_RANDOM: "ALG_PSEUDO_RANDOM",
    ALG_SECURE_RANDOM: "ALG_SECURE_RANDOM",
    ALG_TRNG: "ALG_TRNG",
}

# Matches RandomNumberApplet.MAX_CHUNK -- max bytes returned per APDU.
MAX_CHUNK = 250

SW_SUCCESS = (0x90, 0x00)
SW_FUNC_NOT_SUPPORTED = (0x6A, 0x81)


def get_reader():
    available = readers()
    if not available:
        raise SystemExit("No PC/SC readers found")
    for reader in available:
        if str(reader) == SMARTCARD_READER:
            return reader
    raise SystemExit(f"Reader '{SMARTCARD_READER}' not found among {available}")


def select_applet(connection):
    apdu = [0x00, 0xA4, 0x04, 0x00, len(APPLET_AID)] + APPLET_AID
    _data, sw1, sw2 = connection.transmit(apdu)
    if (sw1, sw2) != SW_SUCCESS:
        raise RuntimeError(
            f"SELECT RandomNumberApplet failed: {sw1:02X}{sw2:02X}. "
            "Has it been installed? (gp.jar --install random_number_generator.cap)"
        )


def get_random_chunk(connection, algorithm, length=MAX_CHUNK):
    if not (1 <= length <= MAX_CHUNK):
        raise ValueError(f"length must be 1..{MAX_CHUNK}")
    apdu = [0x00, INS_GET_RANDOM, algorithm, 0x00, length]
    data, sw1, sw2 = connection.transmit(apdu)
    if (sw1, sw2) == SW_FUNC_NOT_SUPPORTED:
        raise RuntimeError(f"{ALGORITHM_NAMES[algorithm]} not supported by this card")
    if (sw1, sw2) != SW_SUCCESS:
        raise RuntimeError(f"GET_RANDOM(alg={algorithm}) failed: {sw1:02X}{sw2:02X}")
    return bytes(data)


def collect_random_bytes(connection, algorithm, total_bytes):
    """Repeatedly call GET_RANDOM to accumulate total_bytes of output."""
    out = bytearray()
    while len(out) < total_bytes:
        chunk_len = min(MAX_CHUNK, total_bytes - len(out))
        out.extend(get_random_chunk(connection, algorithm, chunk_len))
    return bytes(out)


def main():
    reader = get_reader()
    print(f"Using reader: {reader}")
    connection = reader.createConnection()
    connection.connect()
    print("ATR:", toHexString(connection.getATR()))

    select_applet(connection)
    print("Selected RandomNumberApplet")

    total_bytes = 65536  # 64 KiB per algorithm -- enough for a meaningful ent run
    for algorithm in (ALG_PSEUDO_RANDOM, ALG_SECURE_RANDOM, ALG_TRNG):
        name = ALGORITHM_NAMES[algorithm]
        print(f"\nCollecting {total_bytes} bytes via {name}...")
        try:
            data = collect_random_bytes(connection, algorithm, total_bytes)
        except RuntimeError as e:
            print(f"  skipped: {e}")
            continue
        out_path = os.path.join(os.path.dirname(__file__), f"{name.lower()}.bin")
        with open(out_path, "wb") as f:
            f.write(data)
        print(f"  wrote {len(data)} bytes -> {out_path}")
        print("  run: ..\\..\\tools\\ent_src\\ent.exe " + out_path)


if __name__ == "__main__":
    main()
