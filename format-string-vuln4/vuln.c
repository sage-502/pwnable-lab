//filename: vuln.c
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

int main() {
    int target = 0xcafebabe;
    char buf[100];

    puts("input:");
    fgets(buf, sizeof(buf), stdin);
    printf(buf);

    if (target == 0xdeadbeef) {
        puts("good!");
        setregid(getegid(), getegid());
        system("/bin/sh");
    } else {
        printf("\ntarget = 0x%x\n", target);
    }
}
