package com.monero.rng;

import javacard.framework.*;
import javacard.security.CryptoException;
import javacard.security.RandomData;

/**
 * Test applet: hands back raw bytes from the card's javacard.security.RandomData
 * generators on request, so their output can be pulled off-card and run
 * through an entropy analyzer (see tools/ent_src/).
 *
 * Not a wallet component -- this exists purely to answer "what does this
 * card's RNG actually look like", empirically, instead of trusting a
 * datasheet claim.
 */
public class RandomNumberApplet extends Applet {

    private static final byte INS_GET_RANDOM = (byte) 0x20;

    // ALG_TRNG (raw hardware TRNG, no DRBG conditioning) was added in
    // JavaCard API 3.0.5. Whether this specific card's firmware actually
    // implements it (vs. just the classes being present in the API jar we
    // compiled against) is exactly the kind of thing this applet exists to
    // reveal -- if unsupported, RandomData.getInstance() throws
    // CryptoException.NO_SUCH_ALGORITHM at construction time, and GET_RANDOM
    // with P1=ALG_TRNG returns SW_FUNC_NOT_SUPPORTED below.

    // Max bytes returned per APDU -- comfortably under the ~256-byte short
    // APDU response limit, leaving headroom in the buffer.
    private static final short MAX_CHUNK = (short) 250;

    private RandomData pseudoRandom;
    private RandomData secureRandom;
    private RandomData trng;

    protected RandomNumberApplet() {
        pseudoRandom = tryGetInstance(RandomData.ALG_PSEUDO_RANDOM);
        secureRandom = tryGetInstance(RandomData.ALG_SECURE_RANDOM);
        trng = tryGetInstance(RandomData.ALG_TRNG);
        register();
    }

    public static void install(byte[] bArray, short bOffset, byte bLength) {
        new RandomNumberApplet();
    }

    // Swallow "algorithm not implemented on this card" at construction time
    // rather than failing the whole applet install -- we want GET_RANDOM to
    // report per-algorithm support at runtime instead.
    private static RandomData tryGetInstance(byte algorithm) {
        try {
            return RandomData.getInstance(algorithm);
        } catch (CryptoException e) {
            return null;
        }
    }

    public void process(APDU apdu) {
        if (selectingApplet()) {
            return;
        }

        byte[] buffer = apdu.getBuffer();
        if (buffer[ISO7816.OFFSET_INS] != INS_GET_RANDOM) {
            ISOException.throwIt(ISO7816.SW_INS_NOT_SUPPORTED);
        }

        RandomData generator = selectGenerator(buffer[ISO7816.OFFSET_P1]);
        if (generator == null) {
            // Valid P1, but this card doesn't implement that algorithm.
            ISOException.throwIt(ISO7816.SW_FUNC_NOT_SUPPORTED);
        }

        short le = apdu.setOutgoing();
        if (le <= 0 || le > MAX_CHUNK) {
            le = MAX_CHUNK;
        }
        apdu.setOutgoingLength(le);
        generator.generateData(buffer, (short) 0, le);
        apdu.sendBytes((short) 0, le);
    }

    private RandomData selectGenerator(byte alg) {
        switch (alg) {
            case RandomData.ALG_PSEUDO_RANDOM:
                return pseudoRandom;
            case RandomData.ALG_SECURE_RANDOM:
                return secureRandom;
            case RandomData.ALG_TRNG:
                return trng;
            default:
                ISOException.throwIt(ISO7816.SW_INCORRECT_P1P2);
                return null; // unreachable
        }
    }
}
