//filename: vuln.c
#include <stdio.h>
#include <stdlib.h>

int main() {
    int target = 0xcafebabe;
    char buf[100];

    printf("target addr = %p\n", &target);
    fgets(buf, sizeof(buf), stdin);
    printf(buf);
    printf("\ntarget = 0x%x\n", target);

    if(target == 0xdeadbeef){
	printf("good!\n");
        system("/bin/bash");
    }	    

    return 0;
}
