#!/usr/bin/env python3

import argparse
import os
import io
import struct
from pathlib import Path
from sc3man import unpack_sc3game,pack_sc3game

HEADER_SIZE = 0x40
ALIGN = 0x40

def align(value):
    return (value + ALIGN - 1) & ~(ALIGN - 1)


def read_header(f):
    hdr = f.read(HEADER_SIZE)
    if len(hdr) != HEADER_SIZE:
        return None

    name = hdr[:16].split(b'\0', 1)[0].decode("ascii")

    if name == "":
        return None

    size = struct.unpack_from("<I", hdr, 0x10)[0]

    return {
        "name": name,
        "size": size,
        "raw": hdr,
    }


def list_archive(f):
    print(f"{'name':16}  {'size':<6}  entry_offset")
    while True:
        entry_offset = f.tell()

        h = read_header(f)
        if h is None:
            break

        data_offset = f.tell()

        print(
            f"{h['name']:16s}  "
            f"{h['size']:06X}  "
            f"{entry_offset:08X}  "
        )

        f.seek(align(data_offset + h["size"]))


def extract_archive(f, outdir):

    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    while True:

        h = read_header(f)
        if h is None:
            break

        data = f.read(h["size"])

        outfile = outdir / h["name"]

        with open(outfile, "wb") as o:
            o.write(data)

        print("Extracted", outfile)

        f.seek(align(f.tell()))


def build_archive(indir, outfile):

    indir = Path(indir)

    files = sorted(
        p for p in indir.iterdir()
        if p.is_file()
    )
    
    with open(outfile, "wb") as out:
        output = bytearray()
        for path in files:

            data = path.read_bytes()

            hdr = bytearray(HEADER_SIZE)

            name = path.name.encode("ascii")

            if len(name) > 15:
                raise Exception(f"Filename too long: {path.name}")

            hdr[:len(name)] = name

            struct.pack_into("<I", hdr, 0x10, len(data))
            output.extend(hdr)
            output.extend(data)

            while len(output) % ALIGN:
                output.extend(b"\0")

            print("Added", path.name)
        cmp = pack_sc3game(output)
        out.write(cmp)


def main():

    parser = argparse.ArgumentParser(description="Script for handling SYSTEM246 SOULCALIBUR3 ARCADE BATTLE IRX package (eg:'IRXPK246.301')")
    sub = parser.add_subparsers(dest="cmd")

    p = sub.add_parser("list")
    p.add_argument("archive", help="package to list contents from")

    p = sub.add_parser("extract")
    p.add_argument("archive", help="package to extract data from")
    p.add_argument("outdir", help="folder name to store output data")

    p = sub.add_parser("build")
    p.add_argument("indir", help="folder to obtain input files")
    p.add_argument("archive", help="name of the new package")

    args = parser.parse_args()

    if args.cmd == "list":
        dec = io.BufferedReader(io.BytesIO(unpack_sc3game(open(args.archive,'rb').read())))
        list_archive(dec)

    elif args.cmd == "extract":
        dec = io.BufferedReader(io.BytesIO(unpack_sc3game(open(args.archive,'rb').read())))
        extract_archive(dec, args.outdir)

    elif args.cmd == "build":
        build_archive(args.indir, args.archive)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
