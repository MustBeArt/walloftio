from Crypto.Cipher import AES
from Crypto.Random import _UserFriendlyRNG as RNG

# First 14 bytes of the key. The last two bytes, taken from the
# device id, have to be appended before use.
key = b'\x4d\x92\x91\x63\x8b\x4b\x46\xd0\x67\x8d\x67\x53\xa3\xc8'
cipher = None


# Add the device ID to the key and initialize the cipher.
def customize_cipher(device_id):
    global key, cipher

    key += device_id.to_bytes(2, byteorder='little')
    cipher = AES.new(key, AES.MODE_ECB)


# Convert the first 4 bytes of a bytestring to a 32-bit number,
# using the badge's endianness.
def bytes_to_ctr(iv):
    return (iv[3] << 24) + (iv[2] << 16) + (iv[1] << 8) + iv[0]


# Convert a 32-bit number to a bytestring, using the badge's endianness.
def ctr_to_bytes(val):
    return bytes((val & 0xFF,
                  (val >> 8) & 0xFF,
                  (val >> 16) & 0xFF,
                  (val >> 24) & 0xFF))


# Increment the Counter (first four bytes) in an IV
def increment_ctr(iv):
    counter = bytes_to_ctr(iv)
    counter += 1
    return ctr_to_bytes(counter) + iv[4:]


def decrypt_short_cryptable(cryptable):
    iv = cryptable[0:16]
    ciphertext = cryptable[16:]
    cleartext = bytes(a ^ b for a, b in
                       zip(ciphertext, cipher.encrypt(iv)))
    return cleartext


def decrypt_cryptable(cryptable):
    iv = cryptable[0:16]
    ciphertext = cryptable[16:]
    cleartext = b''
    while len(ciphertext) > 0:
        block = bytes(a ^ b for a, b in
                       zip(ciphertext, cipher.encrypt(iv)))
        cleartext += block
        iv = increment_ctr(iv)
        ciphertext = ciphertext[16:]
    return cleartext


def encrypt(cleartext):
    counter = 0
    nonce = RNG.get_random_bytes(12)
    iv = ctr_to_bytes(counter) + nonce
    ciphertext = iv
    while len(cleartext) > 0:
        block = bytes(a ^ b for a, b in
                       zip(cleartext, cipher.encrypt(iv)))
        ciphertext += block
        iv = increment_ctr(iv)
        cleartext = cleartext[16:]
    return ciphertext


def eval_score_characteristic(characteristic):
    if len(characteristic) != 25:
        return None

    cleartext = decrypt_short_cryptable(characteristic)

    if (cleartext[0] != 0xa6 or
        cleartext[1] != 0xe5 or
        cleartext[2] != 0xd1 or
        cleartext[3] != 0x8c):
        return None

    device_id = "%02x%02x" % (cleartext[5], cleartext[4])
    score = (cleartext[7] << 8) + cleartext[6]
    lld = cleartext[8]
    return (device_id, score, lld)


if __name__ == "__main__":
    customize_cipher(b'\xbe\x7e')

    result = eval_score_characteristic(b'\x00\x00\x00\x00\xb3\x10\x68\xa8\x4b\x15\x5a\x8c\xe8\x3f\xf4\xef\xc4\x8e\xd7\xa2\x2e\x94\x9d\xeb\x40')
    if result is None:
        print("Invalid")
    else:
        (d, s, l) = result
        print("Device ID: %s" % d)
        print("Score: %d" % s)
        print("LLD: %d" % l)

    shadow = b'\x00\x00\x00\x00\x6d\x69\xf8\xe0\x36\x5c\x8f\x19\x51\x23\x66\x38\xb9\x71\x44\x87\x90\x81\x48\x4c\x51\xfd\x52\x26\x76\xfe\xc9\xa8\x08\x17\xa2\xa4\x80\x57\x8c\xd2\x1e\x7a\xbc\xf5\x5e\xdc\xf0\x06\x01\xf9\x3f\x68\x12\x33\x6a\xdc\x1e\x2d\xc0\x85\x10\x6b\x53\xb4\x92\xe4\x36\xf1\xe2\xfa\x03\xd4\x24\x63\x77\x74\xc3\xeb\x19\x62\xdb\x5d\xbd\x1c\xc9\xfa\x06\xd3\x8f\x9f\x00\x08\xbc\x96\x49\x42\xe2\x84\x79\xc2\x25\x18\xf0\x51\x0b\x56\x9a\x05\x85\x20\x10\x18\x41\x28\x6b\x73\xac\xa5\x17\x67\xc7\xce\xed\xed\xb4\x85\x1d\x37\xd2\xe5\x12\x9e\x68\x1d\x41\x83\x97\xe6\x01\xda\x72\xca'
    result = decrypt_cryptable(shadow)
    print("SHADOW.DAT decrypted, look for readable message strings:")
    print(result)

    poem = b'I met a traveller from an antique land\nWho said: Two vast and trunkless legs of stone\nStand in the desert... near them, on the sand,\nHalf sunk, a shattered visage lies, whose frown,\nAnd wrinkled lip, and sneer of cold command,\nTell that its sculptor well those passions read\nWhich yet survive, stamped on these lifeless things,\nThe hand that mocked them and the heart that fed;\n\nAnd on the pedestal these words appear:\n"My name is Ozymandias, king of kings;\nLook on my works, ye Mighty, and despair!"\nNothing beside remains. Round the decay\nOf that colossal wreck, boundless and bare\nThe lone and level sands stretch far away.'
    code = encrypt(poem)
    text = decrypt_cryptable(code)
    print(text.decode('ascii'))
