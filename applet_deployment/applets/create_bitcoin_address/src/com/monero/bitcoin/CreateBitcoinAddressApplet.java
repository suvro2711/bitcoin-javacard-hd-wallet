package com.monero.bitcoin;

import javacard.framework.*;
import javacard.security.CryptoException;
import javacard.security.RandomData;

/**
 * generate_entropy(): returns 256 bits (32 bytes) of raw output from the
 * card's hardware TRNG (javacard.security.RandomData.ALG_TRNG -- no DRBG
 * conditioning). Confirmed supported on this card via
 * applets/random_number_generator/'s broader RNG survey.
 *
 * This is entropy only, not a private key -- nothing here does secp256k1
 * key generation or BIP32 derivation yet. See RandomNumberApplet for
 * comparing this against ALG_PSEUDO_RANDOM/ALG_SECURE_RANDOM output.
 */
public class CreateBitcoinAddressApplet extends Applet {

    private static final byte INS_GENERATE_ENTROPY = (byte) 0x30;
    private static final short ENTROPY_LENGTH = (short) 32; // 256 bits

    private RandomData trng;

    protected CreateBitcoinAddressApplet() {
        try {
            trng = RandomData.getInstance(RandomData.ALG_TRNG);
        } catch (CryptoException e) {
            trng = null;
        }
        register();
    }

    public static void install(byte[] bArray, short bOffset, byte bLength) {
        new CreateBitcoinAddressApplet();
    }

    public void process(APDU apdu) {
        if (selectingApplet()) {
            return;
        }

        byte[] buffer = apdu.getBuffer();
        if (buffer[ISO7816.OFFSET_INS] != INS_GENERATE_ENTROPY) {
            ISOException.throwIt(ISO7816.SW_INS_NOT_SUPPORTED);
        }
        if (trng == null) {
            // This card's firmware doesn't implement ALG_TRNG.
            ISOException.throwIt(ISO7816.SW_FUNC_NOT_SUPPORTED);
        }

        trng.generateData(buffer, (short) 0, ENTROPY_LENGTH);
        apdu.setOutgoingAndSend((short) 0, ENTROPY_LENGTH);
    }
}
