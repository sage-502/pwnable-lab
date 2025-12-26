//filename: vuln.c
#include<stdio.h>
#include<stdlib.h>
#include <unistd.h>

void win(){
    setregid(getegid(), getegid());
    system("/bin/sh");
}

void vuln(int value){
    char buf[16];
    printf("input: ");
    gets(buf);
    printf("value: %d\n", value);
    printf("buf: %s\n", buf);
}

int main(){
    int num = 5;
    vuln(num);
}
