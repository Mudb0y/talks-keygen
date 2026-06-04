#!/usr/bin/env python3
# Registration code generator for Nuance TALKS / ZOOMS (Symbian S60).
#
# Code format: base-32 string, 5 bits per symbol, least-significant bit first,
# using a fixed 32-symbol alphabet. It decodes to 10 bytes:
#   bytes 0-3 : field5  (device hash)
#   bytes 4-7 : v11 ^ 0xA5DCE7F8   (capability word -> features + product SKU)
#   bytes 8-9 : v12 ^ 0xCD5A       (expiry/counter + edition tier, bits 10-13)
# The device accepts the code when:
#   field5 == crc32( v11_le32 + v12_le32 + salt + imei[:15] )
# with salt 0x1D5FAC39 and the standard CRC-32 (poly 0xEDB88320).
#
# This decode is byte-identical across versions v3.20 to v5.50. device_hash is
# recomputed for any v11/v12, so any choice produces a hash-valid code; the
# capability word determines which features and product SKU are enabled.

import zlib
import struct

ALPHABET = b"WY23456789ABCDEFGHZJKLMNXPQRSTUV"
SALT = bytes([0x39, 0xAC, 0x5F, 0x1D])      # 0x1D5FAC39
XOR_V11 = 0xA5DCE7F8
XOR_V12 = 0xCD5A

# Capability word (v11) -> product SKU. The product name is selected on-device
# from the bits of this word.
SKUS = [
    ("TALKS & ZOOMS",    0xFF00DFFF),
    ("All capability bits", 0xFF00FFFF),
    ("TALKS only",       0xFB005FDF),
    ("Speech2Go Reader", 0x00002000),
]

DEFAULT_SKU = 0           # index into SKUS
# Edition tier must be in 6..15 to pass the validity gate. It does not affect
# features or the product name.
EDITION = 7


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


def make_code(imei, caps=0xFF00DFFF, edition=EDITION):
    v11 = caps & 0xFFFFFFFF          # capability word (features + SKU + perpetual)
    v12 = (edition & 0xF) << 10      # edition tier in bits 10-13, no expiry
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


def prompt_caps():
    print()
    print("Product:")
    for i, (label, _caps) in enumerate(SKUS, 1):
        print("  %d) %s" % (i, label))
    print("  %d) Custom" % (len(SKUS) + 1))
    print()
    while True:
        choice = input("Choice [default %d]: " % (DEFAULT_SKU + 1)).strip()
        if choice == "":
            return SKUS[DEFAULT_SKU]
        if choice.isdigit():
            n = int(choice)
            if 1 <= n <= len(SKUS):
                return SKUS[n - 1]
            if n == len(SKUS) + 1:
                raw = input("Capability word (hex, e.g. FF00FFFF): ").strip()
                try:
                    return ("Custom", int(raw, 16) & 0xFFFFFFFF)
                except ValueError:
                    print("Not valid hex.")
                    continue
        print("Invalid choice.")


def group(code):
    return "-".join(code[i:i + 4] for i in range(0, len(code), 4))


def main():
    print("TALKS / ZOOMS registration code generator\n")
    imei = prompt_imei()
    label, caps = prompt_caps()
    code = make_code(imei, caps)
    print()
    print("IMEI:    %s" % imei)
    print("Product: %s" % label)
    print()
    print("    %s" % group(code))
    print()


if __name__ == "__main__":
    main()
