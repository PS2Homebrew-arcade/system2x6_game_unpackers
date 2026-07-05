# _____ ______________  ___  ___   _   _ 
#|_   _|  ___|  _  \  \/  | / _ \ | \ | |
#  | | | |__ | | | | .  . |/ /_\ \|  \| |
#  | | |  __|| | | | |\/| ||  _  || . ` |
#  | | | |___| |/ /| |  | || | | || |\  |
#  \_/ \____/|___/ \_|  |_/\_| |_/\_| \_/
# (un)packer for TEDGAME file from all the taiko no tatsujin titles of system256
# MIT License (c) 2026 github.com/PS2Homebrew-arcade
                                        
import argparse
from collections import defaultdict

parser = argparse.ArgumentParser()

mode = parser.add_mutually_exclusive_group(required=True)
mode.add_argument("-x", "--extract", action="store_true")
mode.add_argument("-c", "--compress", action="store_true")

parser.add_argument("input")
parser.add_argument("output")

args = parser.parse_args()

def decompr(data):
    if data[:4] != b'\x00\x00\x10\x00':
        raise RuntimeError(
            f"Invalid header: '{data[:4].hex(' ').upper()}' (expected '00 00 10 00')\nreport this in https://github.com/PS2Homebrew-arcade/DrumTools/issues"
        )
    print("--- decompressing...")

    src = 4
    dst = bytearray()

    bVar1 = data[src]
    src += 1

    while bVar1 != 0:

        uVar3 = bVar1

        while True:
            bit = uVar3 & 1
            uVar3 >>= 1

            if bit == 0:
                word = (data[src] << 8) | data[src + 1]
                src += 2

                offset = word & 0x7FF
                if offset == 0:
                    offset = 0x800

                length = (word >> 11) & 0x1F
                if length == 0:
                    length = 0x20

                if offset > len(dst):
                    print(
                        f"# INVALID BACKREF "
                        f"src={src-2:08X} "
                        f"word={word:04X} "
                        f"offset={offset:04X} "
                        f"len={length} "
                        f"dst_size={len(dst)}"
                    )
                    raise RuntimeError("invalid backref")

                for _ in range(length):
                    dst.append(dst[-offset])

            else:
                dst.append(data[src])
                src += 1

            if uVar3 <= 1:
                break

        bVar1 = data[src]
        src += 1

    print(f"  - original size   {len(data):08X}")
    print(f"  - decompressed size {len(dst):08X}")
    print(f"  - ratio           {len(data)/len(dst)*100:.1f}%")
    return bytes(dst)

def compr(data, load_address=0x00100000):
    print("--- Compressing payload...")

    out = bytearray()
    out += load_address.to_bytes(4, "little")

    pos = 0

    matches = defaultdict(list)

    while pos < len(data):
        print(f"\r    {pos / len(data) * 100:.1f}%", end="")
        flag_pos = len(out)
        out.append(0)

        flags = 0
        token_count = 0

        while token_count < 7 and pos < len(data):
            best_len = 0
            best_off = 0

            if pos + 2 < len(data):

                key = bytes(data[pos:pos + 3])

                for ref in reversed(matches.get(key, [])):

                    off = pos - ref

                    if off <= 0 or off > 0x800:
                        continue

                    length = 0

                    while (
                        length < 0x20 and
                        pos + length < len(data) and
                        data[ref + length] == data[pos + length]
                    ):
                        length += 1

                    if length > best_len:
                        best_len = length
                        best_off = off

                        if length == 0x20:
                            break
            if best_len < 2:
                flags |= (1 << token_count)

                out.append(data[pos])

                if pos + 2 < len(data):
                    matches[bytes(data[pos:pos + 3])].append(pos)

                pos += 1
            else:
                length = best_len
                offset = best_off
                enc_len = length & 0x1F
                enc_off = offset & 0x7FF

                if length == 0x20:
                    enc_len = 0
                if offset == 0x800:
                    enc_off = 0

                word = (enc_len << 11) | enc_off
                out.append((word >> 8) & 0xFF)
                out.append(word & 0xFF)

                for p in range(pos, pos + length):
                    if p + 2 < len(data):
                        matches[bytes(data[p:p + 3])].append(p)

                pos += length

            token_count += 1

        flags |= (1 << token_count)

        out[flag_pos] = flags & 0xFF

    out.append(0)

    print(f"  - original size   {len(data):08X}")
    print(f"  - compressed size {len(out):08X}")
    print(f"  - ratio           {len(out)/len(data)*100:.1f}%")

    return bytes(out)

print("-- Opening", args.input)

with open(args.input, "rb") as f:
    data = f.read()

if args.extract:
    out = decompr(data)
elif args.compress:
    out = compr(data)

with open(args.output, "wb") as f:
    written = f.write(out)
    print(f"-- output: written 0x{written:X} bytes")