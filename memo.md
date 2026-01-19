# memo

메모장 :)

---

## want to do

- [x] stack bof basic - ret2win : ASLR off
- [x] format string vuln1 - local overwrite : ASLR off, 로컬 변수 주소 제시 (개념용)
- [x] format string vuln2 - ret2win : ASLR off
  - GDB 내부에서 system("/bin/bash")로 쉘 쓰는 게 어려웠음.
- [x] fsb leak - stack leak, libc leak : ASLR off, on 각각
  - off 하는 거 까먹음.
- [ ] fsb local overwrite - local overwrite : ASLR on
- [ ] bof ret2libc
- [ ] fsb ret2libc
- [ ] fsb got overwrite
- [ ] bof fs canary leak
- [ ] ROP...

---

### vulnerability

- Buffer overflow : bof
- Format string vulnerability : fs

---

### method

- local overwrite
- ret overwrite : ret2win, ret2libc
- got overwrite
- leak
- return oriented programming
