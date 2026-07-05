import argparse

parser = argparse.ArgumentParser()
parser.add_argument("input")
parser.add_argument("output")
args = parser.parse_args()

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

print("-- Opening", args.input)


with open(args.input, "rb") as f:
    data = f.read()

print("-- input file size:", len(data))

out = unpack_tk4(data)
print("-- decompression output size:", len(out))

with open(args.output, "wb") as f:
    written = f.write(out)
    print("-- written", written, "bytes into output file")