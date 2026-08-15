# Java Card POC — `select_card_manager.py`

## What it does

Proves the whole chain works — USB reader → PC/SC → card — **without installing
any applet**. It talks to a piece of software that's already present on every
GlobalPlatform Java Card by default: the **Issuer Security Domain (ISD)**,
also called the "card manager."

## How it works

1. **`readers()`** — asks the OS's PC/SC service (Windows Smart Card service)
   for a list of connected readers. On this machine that returns
   `Generic EMV Smartcard Reader 0` (contact/USB) and
   `Windows Hello for Business 1` (a virtual reader Windows creates for its
   own auth, unrelated to the Java Card).
2. **`reader.createConnection()` + `.connect()`** — powers up the card and
   performs the ISO 7816 activation sequence.
3. **`connection.getATR()`** — reads the Answer To Reset, a byte string the
   card sends on power-up identifying itself (protocol, historical bytes,
   etc.). This is passive — no APDU involved.
4. **`connection.transmit([0x00, 0xA4, 0x04, 0x00, 0x00])`** — sends a
   `SELECT` APDU (`CLA=00 INS=A4 P1=04 P2=00 Lc=00`) with no AID data. Per the
   GlobalPlatform spec, `SELECT` with an empty AID selects the default
   security domain — the ISD — which is always present and doesn't require
   anything to be loaded onto the card first.
5. The card replies with **FCI data + a status word**. `SW = 90 00` means
   "success"; anything else (e.g. `6A 82`, "file not found") would mean the
   reader/card link works but the SELECT itself failed.

## What the output means

```
ATR: 3B F8 13 00 00 81 31 FE 45 4A 43 4F 50 76 32 34 31 B7
```
Card identifies itself (the `4A 43 4F 50 76 32 34 31` bytes decode to
`JCOPv241`, i.e. this is a JCOP card).

```
SELECT ISD -> 6F 10 84 08 A0 00 00 01 51 00 00 00 A5 04 9F 65 01 FF 90 00
```
`6F...` is the FCI template; `84 08 A0 00 00 01 51 00 00 00` is the ISD's AID
(`A0 00 00 01 51 00 00 00` — a standard GlobalPlatform test/reference AID);
`90 00` at the end is the success status word.

This confirms: reader detected → card powered → APDU round-trip works —
the minimum needed before doing anything more interesting (installing an
applet, talking to one, etc.).

## Would this let us deploy applets?

**Short answer: pyscard can carry the bytes, but it doesn't speak the
protocol.** Deploying a CAP file (what `gp.jar --install` does) isn't a
single APDU — it's a whole GlobalPlatform sub-protocol:

1. Authenticate to the ISD and open a **Secure Channel (SCP02/SCP03)** —
   derive session keys from the card's static keys, then MAC (and often
   encrypt) every subsequent APDU.
2. Split the `.cap` file into load-file blocks and send them via a sequence
   of `LOAD` APDUs over that secure channel.
3. Send `INSTALL [for install]` to instantiate the applet from the loaded
   package, with the right AID/privileges.

`pyscard.CardConnection.transmit()` is exactly the same kind of primitive as
Java's `javax.smartcardio` `Card.transmit()` — **GlobalPlatformPro (`gp.jar`)
is built on top of that primitive**, not something more privileged. So in
principle the same protocol could be reimplemented on top of pyscard in
Python. In practice:

- There's no mature, actively maintained pure-Python library that already
  implements SCP02/SCP03 + CAP loading the way GlobalPlatformPro does —
  you'd be reimplementing (and re-debugging) key derivation and secure
  messaging from the GlobalPlatform spec yourself.
- `gp.jar` already does this correctly and is what `monero_wallet`'s
  `HelloWorldApplet` was installed with.

**Recommendation:** keep using `gp.jar` (optionally shelled out to from
Python via `subprocess`) for loading/installing applets, and use pyscard for
everything *after* an applet is on the card — selecting it and sending it
APDUs, exactly like this script does for the ISD. That split (Java tool for
deployment, Python for runtime interaction/testing) avoids reimplementing
secure-channel crypto for no real benefit.
