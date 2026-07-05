import random
from collections import defaultdict

def unpack_tk4(data: bytes) -> bytes:
    src = 4
    dst = bytearray(b"\x00" * 0x800)

    while True:
        if src >= len(data):
            break

        ctrl = data[src]
        src += 1

        if ctrl == 0:
            break

        u = ctrl

        while u > 1:
            if u & 1:
                dst.append(data[src])
                src += 1
            else:
                word = (data[src] << 8) | data[src + 1]
                src += 2
                offset = word & 0x7FF
                if offset == 0:
                    offset = 0x800
                length = (word >> 11) & 0x1F
                if length == 0:
                    length = 0x20

                for _ in range(length):
                    dst.append(dst[-offset])

            u >>= 1

    return bytes(dst[0x800:])

def repack_tk4(data: bytes, header_size: bytes = b"\x80\x01\x18\x00") -> bytes:
    PAD = 0x800
    MAX_LEN = 0x20
    MAX_OFFSET = 0x800
    MIN_LEN = 3
    MAX_CHAIN = 128  # cap search depth per hash bucket for speed

    buf = bytearray(PAD) + bytearray(data)
    total_len = len(buf)

    out = bytearray()
    out += header_size

    chains = defaultdict(list)

    def key(p):
        return bytes(buf[p:p + 3])

    pending_flags = []
    pending_bytes = bytearray()

    def flush_group():
        nonlocal pending_flags, pending_bytes
        if not pending_flags:
            return
        n = len(pending_flags)
        bits = 0
        for i, is_lit in enumerate(pending_flags):
            if is_lit:
                bits |= (1 << i)
        ctrl = (1 << n) | bits
        out.append(ctrl)
        out.extend(pending_bytes)
        pending_flags = []
        pending_bytes = bytearray()

    pos = PAD
    while pos < total_len:
        best_len = 0
        best_off = 0

        if pos + 3 <= total_len:
            k = key(pos)
            candidates = chains.get(k)
            if candidates:
                max_possible = min(MAX_LEN, total_len - pos)
                checked = 0
                for cand in reversed(candidates):
                    off = pos - cand
                    if off > MAX_OFFSET:
                        break
                    checked += 1
                    if checked > MAX_CHAIN:
                        break
                    l = 0
                    while l < max_possible and buf[cand + l] == buf[pos + l]:
                        l += 1
                    if l > best_len:
                        best_len = l
                        best_off = off
                        if best_len == MAX_LEN:
                            break

        if best_len >= MIN_LEN:
            offset_field = 0 if best_off == MAX_OFFSET else best_off
            length_field = 0 if best_len == MAX_LEN else best_len
            token = (length_field << 11) | offset_field

            pending_flags.append(False)
            pending_bytes.append((token >> 8) & 0xFF)
            pending_bytes.append(token & 0xFF)

            for i in range(best_len):
                p = pos + i
                if p + 3 <= total_len:
                    chains[key(p)].append(p)
            pos += best_len
        else:
            pending_flags.append(True)
            pending_bytes.append(buf[pos])
            if pos + 3 <= total_len:
                chains[key(pos)].append(pos)
            pos += 1

        if len(pending_flags) == 7:
            flush_group()

    flush_group()
    out.append(0)  # terminator
    return bytes(out)


def _selftest():
    random.seed(1)

    def test(data, label):
        packed = repack_tk4(data)
        unpacked = unpack_tk4(packed)
        ok = unpacked == data
        print(f"{label}: len(data)={len(data)} len(packed)={len(packed)} OK={ok}")
        if not ok:
            print("  MISMATCH!")
            for i in range(min(len(data), len(unpacked))):
                if data[i] != unpacked[i]:
                    print("  first diff at", i)
                    break

    test(bytes(random.randrange(256) for _ in range(5000)), "random")
    test((b"ABCD1234" * 2000), "repetitive")

    mixed = bytearray()
    for _ in range(50):
        mixed += bytes(random.randrange(256) for _ in range(random.randint(1, 50)))
        mixed += bytes([random.randint(1, 200)])
    test(bytes(mixed), "mixed")

    test(b"", "empty")
    test(b"A", "one byte")
    test(b"AA", "two bytes")
    test(b"AAA", "three bytes")
    test(b"Z" * 10000, "long run")


def main():
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        description="(un)packs the main game binary from TEKKEN4 'mc0:TKGAME'"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_unpack = subparsers.add_parser("unpack", help="Decompress file")
    p_unpack.add_argument("input", help="Packed input")
    p_unpack.add_argument("output", help="Unpacked output")

    p_pack = subparsers.add_parser("pack", help="Compress file")
    p_pack.add_argument("input", help="Unpacked input")
    p_pack.add_argument("output", help="Packed output")
    p_pack.add_argument(
        "--header",
        help="4 byte header that seems to be unused. Default: 80 01 18 00",
        default="00000000",
    )

    subparsers.add_parser("selftest", help="Quick selftest with random data")

    args = parser.parse_args()

    if args.command == "unpack":
        with open(args.input, "rb") as f:
            data = f.read()
        result = unpack_tk4(data)
        with open(args.output, "wb") as f:
            f.write(result)
        print(f"Unpacked: {args.input} ({len(data)} bytes) -> {args.output} ({len(result)} bytes). ratio: {(len(data)/len(result)*100):.1f}%")

    elif args.command == "pack":
        header_bytes = bytes.fromhex(args.header)
        if len(header_bytes) != 4:
            print("Error: --header must be 4 hex bytes (8 chars)", file=sys.stderr)
            sys.exit(1)
        with open(args.input, "rb") as f:
            data = f.read()
        result = repack_tk4(data, header_size=header_bytes)
        with open(args.output, "wb") as f:
            f.write(result)
        print(f"Packed: {args.input} ({len(data)} bytes) -> {args.output} ({len(result)} bytes). ratio: {(len(result)/len(data)*100):.1f}%")

    elif args.command == "selftest":
        _selftest()


if __name__ == "__main__":
    main()