"""
Simplest possible Java Card interaction: no custom applet required.

Connects to the card over the USB reader and SELECTs the Issuer Security
Domain (the card manager / "ISD"), which is always present on a
GlobalPlatform Java Card by default. A 90 00 status word back proves the
reader, PC/SC stack, and card are all talking to each other.
"""

# pyscard docs: https://pyscard.sourceforge.io/user-guide.html
from smartcard.System import readers
from smartcard.util import toHexString

from constants import SMARTCARD_READER

SELECT_ISD = [0x00, 0xA4, 0x04, 0x00, 0x00]


def main():
    available = readers()
    if not available:
        raise SystemExit("No PC/SC readers found")

    reader = available[0]
    print(f"Using reader: {reader}")

    connection = reader.createConnection()
    connection.connect()
    print("ATR:", toHexString(connection.getATR()))

    data, sw1, sw2 = connection.transmit(SELECT_ISD)
    print("SELECT ISD ->", toHexString(data), f"{sw1:02X} {sw2:02X}")

    if (sw1, sw2) == (0x90, 0x00):
        print("Success: card responded to SELECT")
    else:
        print("Card returned a non-success status word")

def get_reader():
    available_readers = readers()
    if not available_readers:
        raise SystemExit("No PC/SC readers found")

    for reader in available_readers:
        if str(reader) == SMARTCARD_READER:
            print(f"Found reader: {reader}")
            return reader

def create_connection(reader):
    connection = reader.createConnection()
    connection.connect()
    print("ATR:", toHexString(connection.getATR()))
    return connection

if __name__ == "__main__":
    reader = get_reader()
    if reader:
        create_connection(reader)
