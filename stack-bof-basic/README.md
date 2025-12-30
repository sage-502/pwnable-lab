# Stack Buffer Overflow (Basic) — ret2win

## 개요
Stack Buffer Overflow는 스택에 할당된 버퍼(예: `char buf[20]`)에 **버퍼 크기보다 더 많은 입력**을 넣어서,
스택 상의 인접한 데이터(저장된 레지스터, 반환 주소 등)를 덮어쓰는 취약점이다.

이 디렉터리에서는 `gets()`로 인해 발생하는 전형적인 스택 버퍼 오버플로우를 이용해,
원래 흐름대로라면 호출되지 않는 `win()` 함수를 실행하는 **ret2win** 공격을 실습한다.

---

## 왜 위험한가?
함수 호출이 끝나면 CPU는 스택에 저장된 **반환 주소(Return Address)** 를 꺼내서 그 주소로 돌아간다.
그런데 입력이 버퍼를 넘쳐서 **반환 주소까지 덮어쓸 수 있으면**,
프로그램이 “돌아가야 할 곳” 대신 공격자가 원하는 주소(예: `win()`)로 점프하게 된다.

```
높은 주소
+------------------+
| Return Address   |  <- 덮을 목표
+------------------+
| Saved EBP(RBP)   |
+------------------+
| buf[20]          |  <- overflow 시작
+------------------+
낮은 주소
```

---

## 취약 코드 포인트
```c
void vuln(int value){
    char buf[16];
    printf("input: ");
    gets(buf);                 // 길이 제한 없음 -> overflow 가능
    printf("value: %d\n", value);
    printf("buf: %s\n", buf);
}
```
vuln()함수에서 gets()를 사용하고 있으므로 길이 제한 없이 입력 가능하다.

---

## 바이너리 분석

### condition

![파일 확인](/images/stack-bof-basic/00.png)

vuln에는 setgid가 설정되어 있다.
vuln은 32bit 로 컴파일되었으며, 리틀엔디안이 적용되어 있다.
또한 보호 기법을 전부 꺼두었기에 canary도 없고, pie도 꺼져있다.

### main() 함수

설명 생략.

![main-asm](/images/stack-bof-basic/01.png)

### vuln() 함수

![vuln-asm](/images/stack-bof-basic/02.png)

gets() 함수를 호출하기 전에 인자로 push되는 게 buf.

### 리턴 주소 직전까지 입력

vuln()함수 에필로그 직전에 bp를 걸고, 리턴 주소 직전까지 A를 넣어봤다.
사진과 같이 메모리에 들어간다.

![test](/images/stack-bof-basic/04.png)

### exploit
오프셋 만큼 쓰레기를 넣고, return addr을 win()함수의 주소로 입력한다.
그러면 다음과 같은 형태가 된다.

```
높은 주소
+------------------+
| Return Address   |  <- win()함수 주소
+------------------+
| Saved EBP(RBP)   |  <- AAAA
+------------------+
| buf[20]          |  <- AAAA...AA
+------------------+
낮은 주소
```

ret를 실행 시 win()함수로 점프하게 되어, win()함수 내의 system("/bin/sh")를 실행할 수 있게 된다.

![exploit](/images/stack-bof-basic/06.png)

id에서 group이 root임을 확인 할 수 있다.
