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
| Saved RBP        |
+------------------+
| buf[20]          |  <- overflow 시작
+------------------+
낮은 주소
```

---

## 취약 코드 포인트
```c
void vuln(int value){
    char buf[20];
    printf("input: ");
    gets(buf);                 // 길이 제한 없음 -> overflow 가능
    printf("value: %d\n", value);
    printf("buf: %s\n", buf);
}
```
