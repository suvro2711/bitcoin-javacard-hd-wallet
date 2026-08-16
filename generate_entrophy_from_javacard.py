from smartcard.System import readers
from smartcard.util import toHexString

from javacard_applet_deployment.constants.APDU import to_int_list
from javacard_applet_deployment.constants.constants import SMARTCARD_READER, SW_SUCCESS
from javacard_applet_deployment.constants.create_bitcoin_address import AID, INS_GENERATE_ENTROPY

# Matches CreateBitcoinAddressApplet.ENTROPY_LENGTH -- 256 bits.
ENTROPY_LENGTH = 32


def get_reader():
    available = readers()
    if not available:
        raise SystemExit("No PC/SC readers found")
    for reader in available:
        if str(reader) == SMARTCARD_READER:
            return reader
    raise SystemExit(f"Reader '{SMARTCARD_READER}' not found among {available}")


def select_applet(connection):
    aid_bytes = to_int_list(AID)
    apdu = [0x00, 0xA4, 0x04, 0x00, len(aid_bytes)] + aid_bytes
    _data, sw1, sw2 = connection.transmit(apdu)
    if (sw1, sw2) != SW_SUCCESS:
        raise RuntimeError(
            f"SELECT CreateBitcoinAddressApplet failed: {sw1:02X}{sw2:02X}. "
            "Has it been installed? (gp.jar --install create_bitcoin_address.cap)"
        )


def generate_entropy(connection):
    """Calls CreateBitcoinAddressApplet.generate_entropy().
    returns: raw TRNG output, ENTROPY_LENGTH bytes."""
    apdu = [0x00, int(INS_GENERATE_ENTROPY, 16), 0x00, 0x00, ENTROPY_LENGTH]
    data, sw1, sw2 = connection.transmit(apdu)
    if (sw1, sw2) != SW_SUCCESS:
        raise RuntimeError(f"generate_entropy failed: {sw1:02X}{sw2:02X}")
    return bytes(data)


def main():
    reader = get_reader()
    print(f"Using reader: {reader}")
    connection = reader.createConnection()
    connection.connect()
    print("ATR:", toHexString(connection.getATR()))

    select_applet(connection)
    print("Selected CreateBitcoinAddressApplet")

    data = generate_entropy(connection)
    print(f"generate_entropy -> {data.hex().upper()} ({len(data)} bytes)")
    return data


if __name__ == "__main__":
    main()
