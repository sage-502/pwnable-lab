//filename: vuln.c
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

void win(){
  puts("good!");
  setregid(getegid(), getegid());
  system("/bin/bash");
}

int main() {
  char buf[100];
  puts("input:");
  fgets(buf, sizeof(buf), stdin);
  printf(buf);
  return 0;
}
