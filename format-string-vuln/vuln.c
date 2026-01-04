//filename: vuln.c

#include <stdio.h>

int main() {
    int target = 0;
    char buf[100];

    printf("target addr = %p\n", &target);
    fgets(buf, sizeof(buf), stdin);
    printf(buf);
    printf("\ntarget = %d\n", target);

    return 0;
}
