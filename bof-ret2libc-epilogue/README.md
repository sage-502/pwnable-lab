# bof-ret2libc-epilogue

## 1. 개요

이 디렉터리는 **ASLR OFF 환경에서 Buffer Overflow + ret2libc**를 시도하던 중,
`main` 함수의 **기대했던 형태와 다른 프롤로그/에필로그**로 인해
**단순한 saved RET overwrite가 성립하지 않았던 실습**에 대한 기록이다.

일반적인 ret2libc 예제와 달리,
이 바이너리는 `leave; ret` 형태가 아닌 epilogue를 사용하고 있어
단순히 offset 만큼의 임의의 padding을 사용할 경우 exploit이 실패한다.

본 실습의 목적은 다음과 같다.

* 단순한 ret2libc 실패 원인 분석
* main epilogue 구조 해석
* epilogue를 고려한 스택 재설계
* 최종적으로 ret2libc가 왜/어떻게 성공했는지 이해

---

## 2. 환경

* Architecture: x86 (32-bit)
* ASLR: OFF
* NX: ON
* PIE: OFF
* Stack Canary: OFF
* Compiler: gcc (`-O0`, 기본 main 사용)

---

## 3. 취약 코드

```c
// filename: vuln.c
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

int main() {
    setregid(getegid(), getegid());
    char buf[20];

    puts("input:");
    gets(buf);          // Buffer Overflow
    printf("%s\n", buf);

    return 0;
}
```

* `gets(buf)`로 인해 버퍼 오버플로우 발생 가능
* ASLR OFF 환경에서는 ret2libc가 가능할 것으로 예상했으나, 실제로된 점은 다음과 같다.

* **saved RET = 항상 `[ebp+4]`가 아니다**
* ret2libc 실패 시:

  * payload만 보지 말고
  * **프롤로그/에필로그를 확인해야 한다**
* 컴파일러가 생성한 epilogue는 control flow에 직접적인 영향을 줄 수 있다
* 실습용으로는:

  * `vuln()` 함수 분리
  * `-fno-omit-frame-pointer`
  
  와 같이 교과서적인 스택 구조가 더 적합할 것 같다.
