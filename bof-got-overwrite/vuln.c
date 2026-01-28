//filename: vuln.c
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

int main() {
    setregid(getegid(), getegid());
    char buf[32];
  
    puts("input:");
    gets(buf);
    printf("%s\n", buf);

    exit(0);
}
