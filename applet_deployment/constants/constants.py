import os

# Substring-matched against PC/SC reader names by both pyscard and gp.jar.
SMARTCARD_READER = "Generic EMV Smartcard Reader 0"

# Path to GlobalPlatformPro (https://github.com/martinpaljak/GlobalPlatformPro
# /releases). Not vendored in this repo -- point GP_JAR_PATH at your local copy.
GP_JAR_PATH = os.environ.get("GP_JAR_PATH")

# ISO 7816 status word for success.
SW_SUCCESS = (0x90, 0x00)
