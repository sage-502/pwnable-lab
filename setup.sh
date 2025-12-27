#!/bin/bash
set -e

echo "[*] pwnable-lab setup start"

# ---------------------------
# 1. 기본 패키지 설치
# ---------------------------
echo "[*] 기본 패키지 설치 시작"
apt update
apt install -y \
    gcc gdb make \
    python3 python3-pip \
    git vim \
    checksec \
    netcat-openbsd \
    file
echo "[+] 기본 패키지 설치 완료"

# ---------------------------
# 2. 32bit 환경 지원
# ---------------------------
echo "[*] 32bit 환경 구성"
dpkg --add-architecture i386
apt update
apt install -y \
    libc6:i386 \
    libc6-dbg:i386 \
    gcc-multilib
echo "[+] 32bit 환경 구성 완료"

# ---------------------------
# 3. pwntools
# ---------------------------
echo "[*] pwntools 설치 시작"
apt install -y python3-pwntools
echo "[+] pwntools 설치 완료"

# ---------------------------
# 4. baby 유저 생성 (최소 권한)
# ---------------------------
echo "[*] baby 유저 생성 시작"
if id "baby" &>/dev/null; then
    echo "[+] user 'baby' already exists"
else
    useradd -m -s /bin/bash baby
    passwd -d baby            # 비밀번호 제거
    chage -d 0 baby           # 패스워드 로그인 비활성
fi
echo "[+] baby 유저 생성 완료"

# sudo 그룹에서 제거 (혹시 모를 상황 대비)
deluser baby sudo &>/dev/null || true

# ---------------------------
# 5. core dump 활성화 (디버깅 편의)
# ---------------------------
echo "[*] core dump 활성화"
ulimit -c unlimited
echo '/tmp/core.%e.%p' > /proc/sys/kernel/core_pattern
echo "[+] core dump 활성화 완료"

echo "[+] setup complete"
