# FSB GOT overwrite

## 1. 개요

이 실습에서는 **Format String Vulnerability(FSB)** 를 이용해
**Global Offset Table(GOT)** 를 overwrite하고,
프로그램의 **함수 호출 흐름을 공격자가 원하는 함수로 변경**하는 것을 목표로 한다.

기존의 ret overwrite 공격이
*함수 리턴 시점*을 노리는 것이라면,
GOT overwrite는
*함수 호출 시점*을 가로채는 공격이다.

이를 이해하기 위해서는 **PLT와 GOT의 역할과 구조**를 먼저 정리할 필요가 있다.

---

## 2. PLT와 GOT

리눅스 ELF 바이너리에서 `printf`, `exit`, `system` 과 같은 함수들은
대부분 실행 파일 내부에 존재하지 않고,
**libc.so** 와 같은 **공유 라이브러리(shared library)** 에 존재한다.

이 때문에 실행 파일은 외부 함수의 실제 주소를 직접 알 수 없으며,
이를 해결하기 위해 **PLT와 GOT** 라는 구조를 사용한다.

### PLT (Procedure Linkage Table)

* 외부 함수를 호출할 때 사용하는 **중계용 코드 영역**
* 실행 파일 내부의 `.plt` 섹션에 존재
* 실제 함수 주소로 점프하는 역할을 수행

PLT는 실행 가능한 코드이며,
모든 외부 함수 호출은 **항상 PLT를 통해 이루어진다**.

### GOT (Global Offset Table)

* 외부 함수의 **실제 주소를 저장하는 테이블**
* 실행 파일 내부의 `.got`, `.got.plt` 섹션에 존재
* 데이터 영역이며, 함수 주소 값만 저장한다

PLT는 GOT에 저장된 주소를 참조해
해당 주소로 점프함으로써 실제 함수를 호출한다.

---

## 3. GOT의 필요성

GOT가 필요한 이유는 다음과 같다.

### 1) Shared Library 사용

외부 함수들은 libc와 같은 공유 라이브러리에 존재하며,
실행 파일에 포함되지 않는다.

### 2) ASLR(Address Space Layout Randomization)

ASLR이 활성화된 환경에서는
libc가 매 실행마다 **다른 주소에 매핑**된다.

즉, 컴파일 시점에는
외부 함수의 실제 주소를 알 수 없다.

### 3) Lazy Binding

프로그램 시작 시 모든 외부 함수 주소를 해결하지 않고,
**처음 호출될 때만 주소를 resolve** 하는 방식이다.

이때:

* PLT는 항상 동일한 코드
* GOT의 내용만 실제 함수 주소로 갱신된다

이 구조 덕분에:

* 실행 속도를 최적화할 수 있고
* 동시에 GOT overwrite 공격 가능성도 생긴다.

> **노트**
>
> resolve란, 외부 함수의 실제 메모리 주소를 libc에서 찾아 GOT에 기록하는 과정을 의미한다.

---

## 4. 실제 실행 흐름

코드에 다음과 같은 명령어가 있다고 해보자:

``` c
exit(0);
```

컴파일할 때 컴파일러는 `exit`이라는 함수가 있으며 libc 안에 있다는 것까지만 알 뿐,
정확히 어디에 있는지는 알지 못한다.

그래서 실행 파일에는

* `exit`의 실제 주소는 없으며
* 대신 **PLT + GOT 구조** 만 만들어둔다.

### 1) 실행 직후 GOT 상태

프로그램이 막 실행됐을 때:
```
exit@got → resolver (동적 링커 코드)
```

* 아직 exit 주소는 모르고
* 나중에 필요할 때 알아봄 (lazy binding)

아직 resolve가 안 된 상태.

> **노트 ── resolver**
>
> 동적 링커 (ld-linux.so, ld.so) 안에 있는 코드
> 보통 실행 중인 프로세스에는 다음과 같이 올라간다.
> ```
> [stack]
> [libc]
> [ld-linux.so]  ← resolver 코드
> [heap]
> [.got.plt]
> [.plt]
> [text]
> ```


### 2) exit()이 처음 호출될 때

``` perl
exit()
 → exit@plt
 → jmp [exit@got]
 → (resolver로 점프)
 → libc에서 exit 실제 주소 찾음
 → exit@got = libc exit 주소로 덮어씀
 → libc exit 실행
```

### 3) resolve 이후 상태

```
exit@got → 0xf7e04bd0   (libc의 exit)
```
exit의 실제 주소를 알게 된 이후. 

따라서:

```
exit@plt
 → jmp [exit@got]
 → 바로 libc exit
```

다시 resolver를 거치지 않고, GOT에 적힌 주소로 점프한다.

> **노트 ── PLT의 동작**
>
> PLT는 "resolve가 됐나" 를 판단하지 않으며,
> 그저 GOT에 적힌 주소로 무조건 점프한다.
> * GOT에 resolver 주소가 적혀 있다면 resolver로 점프하고
> * 실제 주소가 적혀있다면 그 주소로 점프될 뿐이다.


---

## 5. GOT의 위치

### ELF 파일 관점

실행 파일 내부에서 PLT와 GOT는 다음과 같은 섹션에 존재한다.

```
.text
 └─ .plt        ← PLT (코드 영역)

.data
 └─ .got
 └─ .got.plt    ← GOT (데이터 영역)
```

* **PLT** : `.plt` 섹션 (실행 코드)
* **GOT** : `.got`, `.got.plt` 섹션 (데이터)

실제 공격에서 overwrite 대상으로 사용하는 것은
대부분 **`.got.plt` 영역**이다.

---

### 프로세스 메모리 관점

프로그램이 실행되면,
PLT와 GOT는 다음과 같은 위치에 매핑된다 (32bit, PIE OFF 기준).

```
높은 주소
------------------------
stack
------------------------
libc
------------------------
heap
------------------------
.bss
.data
.got.plt   ← GOT
.got
------------------------
.plt       ← PLT
.text
------------------------
낮은 주소
```

* `.plt` : RX (읽기 + 실행)
* `.got.plt` : RW (Partial RELRO 기준)

이로 인해:

* PLT는 실행만 가능
* GOT는 쓰기 가능 → **GOT overwrite 공격 가능**

> **노트 ── GOT가 쓰기 가능인 이유**
>
> resolver가 lazy binding을 위해 실행 중 GOT를 수정해야 하기 때문

---

## 6. RELRO와 GOT 보호

RELRO(Relocation Read-Only)는
GOT 영역을 보호하기 위한 링커 보안 옵션이다.

RELRO는 GOT를 언제 읽기 전용으로 만들 것인지에 따라
Partial RELRO와 Full RELRO로 나뉜다.

### Partial RELRO

- lazy binding 사용
- 프로그램 실행 중 resolver가 GOT를 수정해야 함
- `.got.plt` 영역이 쓰기 가능(RW)

이 경우 Format String Vulnerability를 이용한
GOT overwrite 공격이 가능하다.

### Full RELRO

- lazy binding 사용하지 않음
- 프로그램 시작 시 모든 외부 함수 주소를 resolve
- 이후 GOT를 읽기 전용(RO)으로 변경

이 경우 실행 중 GOT를 수정할 수 없으므로,
GOT overwrite 공격은 불가능하다.

본 실습에서는 GOT overwrite를 위해
Partial RELRO 환경을 사용한다.

---

## 7. 실습 환
