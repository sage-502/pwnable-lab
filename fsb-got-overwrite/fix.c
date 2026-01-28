// fix.c
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

int main() {
    char buf[100];

    setregid(getegid(), getegid());

    puts("input:");
    fgets(buf, sizeof(buf), stdin);
    printf("%s\n", buf);

    puts("done");
    exit(0);
}
