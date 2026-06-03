#!/usr/bin/env python3
# Registration code generator for Nuance TALKS / ZOOMS (Symbian S60).
#
# Code format: base-32 string, 5 bits per symbol, least-significant bit first,
# using a fixed 32-symbol alphabet. It decodes to 10 bytes:
#   bytes 0-3 : field5  (device hash)
#   bytes 4-7 : v11 ^ 0xA5DCE7F8   (capabilities, flags, perpetual bit)
#   bytes 8-9 : v12 ^ 0xCD5A       (expiry + edition)
# The device accepts the code when:
#   field5 == crc32( v11_le32 + v12_le32 + salt + imei[:15] )
# with salt 0x1D5FAC39 and the standard CRC-32 (poly 0xEDB88320).

import zlib
import struct

ALPHABET = b"WY23456789ABCDEFGHZJKLMNXPQRSTUV"
SALT = bytes([0x39, 0xAC, 0x5F, 0x1D])      # 0x1D5FAC39
XOR_V11 = 0xA5DCE7F8
XOR_V12 = 0xCD5A

# Edition -> product. Edition 6 = Zooms is confirmed; edition must be >= 6.
EDITIONS = [
    ("Talks & Zooms", 7),
    ("Zooms", 6),
    ("Talks & Braille", 8),
    ("Talks Premium", 9),
    ("Speech2Go Reader", 10),
]


def device_hash(v11, v12, imei):
    buf = struct.pack("<I", v11 & 0xFFFFFFFF)
    buf += struct.pack("<I", v12 & 0xFFFF)
    buf += SALT
    buf += imei[:15].encode("ascii")
    return zlib.crc32(buf) & 0xFFFFFFFF


def b32_encode(data):
    bits = nbits = 0
    out = bytearray()
    for byte in data:
        bits |= byte << nbits
        nbits += 8
        while nbits >= 5:
            out.append(ALPHABET[bits & 0x1F])
            bits >>= 5
            nbits -= 5
    if nbits:
        out.append(ALPHABET[bits & 0x1F])
    return out.decode()


def make_code(imei, edition):
    v11 = 0xFF00FFFF                # caps: perpetual, counter check skipped
    v12 = (edition & 0xF) << 10     # edition in bits 10-13, no expiry
    raw = struct.pack("<I", device_hash(v11, v12, imei))
    raw += struct.pack("<I", (v11 ^ XOR_V11) & 0xFFFFFFFF)
    raw += struct.pack("<H", (v12 ^ XOR_V12) & 0xFFFF)
    return b32_encode(raw)


def luhn_check_digit(digits14):
    total = 0
    for i, ch in enumerate(reversed(digits14)):
        n = int(ch)
        if i % 2 == 0:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return (10 - total % 10) % 10


def normalize_imei(raw):
    digits = "".join(c for c in raw if c.isdigit())
    if len(digits) == 14:
        digits += str(luhn_check_digit(digits))
    return digits


def prompt_imei():
    while True:
        raw = input("IMEI (dial *#06#): ").strip()
        imei = normalize_imei(raw)
        if len(imei) < 14:
            print("Need at least 14 digits.\n")
            continue
        if len(imei) > 15:
            imei = imei[:15]
        return imei


def prompt_edition():
    print()
    for i, (name, edition) in enumerate(EDITIONS, 1):
        print("  %d) %s" % (i, name))
    print("  %d) Other edition number" % (len(EDITIONS) + 1))
    while True:
        choice = input("Product: ").strip()
        if choice.isdigit():
            n = int(choice)
            if 1 <= n <= len(EDITIONS):
                return EDITIONS[n - 1][1]
            if n == len(EDITIONS) + 1:
                num = input("Edition number (6-15): ").strip()
                if num.isdigit() and 6 <= int(num) <= 15:
                    return int(num)
        print("Invalid choice.")


def group(code):
    return "-".join(code[i:i + 4] for i in range(0, len(code), 4))


def main():
    print("TALKS / ZOOMS registration code generator\n")
    imei = prompt_imei()
    edition = prompt_edition()
    code = make_code(imei, edition)
    print()
    print("IMEI:    %s" % imei)
    print("Edition: %d" % edition)
    print()
    print("    %s" % group(code))
    print()


if __name__ == "__main__":
    main()
