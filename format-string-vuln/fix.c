#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

int main() {
    int target = 0xcafebabe;
    char buf[100];

    printf("target addr = %p\n", &target);
    fgets(buf, sizeof(buf), stdin);
    printf("%s", buf);
    printf("\ntarget = 0x%x\n", target);

    if (target == 0xdeadbeef) {
        puts("good!");
        setregid(getegid(), getegid());
	system("/bin/bash");
    }

    return 0;
}
