// filename: fix.c
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

void vuln() {
    char buf[24];
    puts("input:");
    fgets(buf, sizeof(buf), stdin);
}

int main() {
    setregid(getegid(), getegid());
    setvbuf(stdout, NULL, _IONBF, 0);
    vuln();
    puts("done");
    return 0;
}
