//filename: fix.c
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

void vuln(){
    char buf[20];

    puts("input1:");
    fgets(buf, sizeof(buf), stdin);
    printf("%s\n", buf);
  
    puts("input2:");
    fgets(buf, sizeof(buf), stdin);
    printf("%s\n", buf);
}

int main() {
    setregid(getegid(), getegid());
    vuln();
    puts("done");
    //exit(0);
    return 0;
}
