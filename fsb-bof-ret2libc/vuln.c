//filename: vuln.c
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

int main() {
    setregid(getegid(), getegid());
    char buf[20];

    puts("input1:");
    fgets(buf, sizeof(buf), stdin);
    printf(buf);
  
    puts("input2:");
    gets(buf);
    printf("%s\n", buf);

    //exit(0);
    return 0;
}
