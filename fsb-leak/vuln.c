//filename: vuln.c
#include <stdio.h>
#include <stdlib.h>

int main() {
    char buf[100];
    puts("input:");
    fgets(buf, sizeof(buf), stdin);
    printf(buf);
    return 0;
}
