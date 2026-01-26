//filename: vuln.c
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

int main() {
    setregid(getegid(), getegid());
    char buf[20];

    puts("input:");
    gets(buf);
    printf("%s\n", buf);

    return 0;
}
