"""
Identifiers for CreateBitcoinAddressApplet -- see
applets/create_bitcoin_address/.

Loaded from create_bitcoin_address.json, the single source of truth shared
with the Java side: build.xml's gen-constants target runs
gen_java_constants.py against the same JSON file to regenerate the applet's
Constants.java before every build, so neither side hand-maintains a
duplicate of these values.
"""
import json
import os

_JSON_PATH = os.path.join(os.path.dirname(__file__), "create_bitcoin_address.json")
with open(_JSON_PATH) as _f:
    _DATA = json.load(_f)

AID = _DATA["aid"]

# Hex-string form, e.g. "30" -- matches how gp_client.py builds raw APDU hex.
INS_GENERATE_ENTROPY = format(int(_DATA["ins_generate_entropy"], 16), "02X")
