// counts malloc/calloc/realloc calls in the process and prints the totals at exit
#include <stdlib.h>
#include <stdio.h>
#include <stdatomic.h>
static atomic_ulong nm, nc, nr;
static void *my_malloc(size_t s){ atomic_fetch_add(&nm,1); return malloc(s); }
static void *my_calloc(size_t a, size_t b){ atomic_fetch_add(&nc,1); return calloc(a,b); }
static void *my_realloc(void *p, size_t s){ atomic_fetch_add(&nr,1); return realloc(p,s); }
__attribute__((destructor)) static void done(void){ fprintf(stderr,"MALLOC_COUNT malloc=%lu calloc=%lu realloc=%lu\n",(unsigned long)nm,(unsigned long)nc,(unsigned long)nr); }
typedef struct { const void *r; const void *o; } interpose_t;
__attribute__((used)) static const interpose_t ip[] __attribute__((section("__DATA,__interpose"))) = {
  {(const void*)my_malloc,(const void*)malloc}, {(const void*)my_calloc,(const void*)calloc}, {(const void*)my_realloc,(const void*)realloc} };
