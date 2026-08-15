"""
Central store of raw APDU byte sequences used across this project, each
documented with its GlobalPlatform Card Specification / ISO 7816 meaning.

Kept as hex strings, since that's what gp.jar's -a/--apdu and -s/--secure-apdu
take directly. Use to_int_list() to convert to the list-of-ints form pyscard's
CardConnection.transmit() expects instead.
"""
import re


# Matches a debug-trace response line, e.g.
#   A<< (0012+2) (32ms) 09A000000001010100010700 9000
#   A<< (0000+2) (15ms) 6E00
_APDU_RESPONSE_RE = re.compile(
    r"^A<<\s+\(\d+\+2\)\s+\(\d+ms\)\s+(?:([0-9A-Fa-f]+)\s+)?([0-9A-Fa-f]{4})\s*$"
)


# SELECT, with an empty AID -> selects the default security domain (the ISD),
# which is always present on a GlobalPlatform Java Card, no applet load
# required.
#
# | Bytes | Field | Meaning |
# |-------|-------|---------|
# | `00`  | CLA   | Standard ISO 7816 class byte (not GlobalPlatform-proprietary) |
# | `A4`  | INS   | Instruction code for **SELECT** |
# | `04`  | P1    | Select by name (AID) |
# | `00`  | P2    | First or only occurrence, standard response |
# | `00`  | Lc    | Length of the data that follows — 0 bytes, i.e. an empty AID. Per GlobalPlatform, SELECT with an empty AID selects the default security domain |
SELECT_ISD = "00A4040000"

# GET STATUS, category = Issuer Security Domain, no AID filter (return all).
# Requires an authenticated secure channel first (SW=6982 otherwise).
#
# | Bytes   | Field | Meaning |
# |---------|-------|---------|
# | `80`    | CLA   | Class byte — `0x80` marks this as a GlobalPlatform-proprietary command (not a plain ISO 7816 one) |
# | `F2`    | INS   | Instruction code for **GET STATUS**, defined by the GP spec |
# | `80`    | P1    | Which category to query — bitmask: `0x80`=Issuer Security Domain, `0x40`=Applications, `0x20`=Executable Load Files, `0x10`=Load Files+Modules. `80` = "give me the ISD" |
# | `00`    | P2    | Response-format control bits (kept at default here) |
# | `02`    | Lc    | Length of the data that follows — 2 bytes |
# | `4F 00` | Data  | A TLV filter: tag `0x4F` is the AID tag, length `0x00` means an empty AID — i.e. "don't filter by a specific AID, match everything" |
GET_STATUS_ISD = "80F28000024F00"

# GET STATUS, category = Applications (applets), no AID filter (return all).
# Requires an authenticated secure channel first (SW=6982 otherwise -- see
# select_card_manager.py's unauthenticated attempt vs gp_client.py's
# authenticated one).
#
# | Bytes   | Field | Meaning |
# |---------|-------|---------|
# | `80`    | CLA   | Class byte — `0x80` marks this as a GlobalPlatform-proprietary command (not a plain ISO 7816 one) |
# | `F2`    | INS   | Instruction code for **GET STATUS**, defined by the GP spec |
# | `40`    | P1    | Which category to query — bitmask: `0x80`=Issuer Security Domain, `0x40`=Applications, `0x20`=Executable Load Files, `0x10`=Load Files+Modules. `40` = "give me applets" |
# | `00`    | P2    | Response-format control bits (kept at default here) |
# | `02`    | Lc    | Length of the data that follows — 2 bytes |
# | `4F 00` | Data  | A TLV filter: tag `0x4F` is the AID tag, length `0x00` means an empty AID — i.e. "don't filter by a specific AID, match everything" |
GET_STATUS_APPLICATIONS = "80F24000024F00"

# GET STATUS, category = Executable Load Files (packages), no AID filter
# (return all). Requires an authenticated secure channel first.
#
# | Bytes   | Field | Meaning |
# |---------|-------|---------|
# | `80`    | CLA   | Class byte — `0x80` marks this as a GlobalPlatform-proprietary command (not a plain ISO 7816 one) |
# | `F2`    | INS   | Instruction code for **GET STATUS**, defined by the GP spec |
# | `20`    | P1    | Which category to query — bitmask: `0x80`=Issuer Security Domain, `0x40`=Applications, `0x20`=Executable Load Files, `0x10`=Load Files+Modules. `20` = "give me packages" |
# | `00`    | P2    | Response-format control bits (kept at default here) |
# | `02`    | Lc    | Length of the data that follows — 2 bytes |
# | `4F 00` | Data  | A TLV filter: tag `0x4F` is the AID tag, length `0x00` means an empty AID — i.e. "don't filter by a specific AID, match everything" |
GET_STATUS_LOAD_FILES = "80F22000024F00"

# GET STATUS, category = Executable Load Files and their Executable Modules,
# no AID filter (return all). Requires an authenticated secure channel first.
#
# | Bytes   | Field | Meaning |
# |---------|-------|---------|
# | `80`    | CLA   | Class byte — `0x80` marks this as a GlobalPlatform-proprietary command (not a plain ISO 7816 one) |
# | `F2`    | INS   | Instruction code for **GET STATUS**, defined by the GP spec |
# | `10`    | P1    | Which category to query — bitmask: `0x80`=Issuer Security Domain, `0x40`=Applications, `0x20`=Executable Load Files, `0x10`=Load Files+Modules. `10` = "give me packages plus their modules" |
# | `00`    | P2    | Response-format control bits (kept at default here) |
# | `02`    | Lc    | Length of the data that follows — 2 bytes |
# | `4F 00` | Data  | A TLV filter: tag `0x4F` is the AID tag, length `0x00` means an empty AID — i.e. "don't filter by a specific AID, match everything" |
GET_STATUS_LOAD_FILES_AND_MODULES = "80F21000024F00"


def to_int_list(hex_apdu):
    """Convert a hex-string APDU to the list-of-ints form pyscard expects."""
    return [int(hex_apdu[i:i + 2], 16) for i in range(0, len(hex_apdu), 2)]
