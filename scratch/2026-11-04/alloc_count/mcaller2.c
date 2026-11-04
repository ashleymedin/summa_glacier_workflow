// counts malloc calls by (caller, caller's caller) function pair (single-threaded runs) and prints the top pairs at exit
#include <stdlib.h>
#include <stdio.h>
#include <dlfcn.h>
#include <stdint.h>
#define NB (1<<21)
static uintptr_t k0[NB], k1[NB]; static unsigned long cnt[NB]; static unsigned long total;
static void *my_malloc(size_t s){
  uintptr_t a=(uintptr_t)__builtin_return_address(0), b=(uintptr_t)__builtin_extract_return_addr(__builtin_return_address(1)); total++;
  size_t h=((a>>2)^(b*2654435761u))&(NB-1); while(k0[h] && (k0[h]!=a || k1[h]!=b)) h=(h+1)&(NB-1);
  k0[h]=a; k1[h]=b; cnt[h]++; return malloc(s); }
typedef struct { const char *n0,*n1; unsigned long n; } agg_t;
static int cmp(const void *x,const void *y){ unsigned long p=((agg_t*)x)->n,q=((agg_t*)y)->n; return p<q?1:p>q?-1:0; }
static const char *nm(uintptr_t a){ Dl_info d; return (dladdr((void*)a,&d) && d.dli_sname) ? d.dli_sname : "?"; }
__attribute__((destructor)) static void done(void){
  static agg_t ag[16384]; int na=0;
  for(size_t i=0;i<NB;i++) if(k0[i]){
    const char *a=nm(k0[i]), *b=nm(k1[i]); int j;
    for(j=0;j<na;j++) if(ag[j].n0==a && ag[j].n1==b) break;
    if(j==na && na<16384){ ag[na].n0=a; ag[na].n1=b; ag[na].n=0; na++; }
    if(j<16384) ag[j].n+=cnt[i]; }
  qsort(ag,na,sizeof(agg_t),cmp);
  fprintf(stderr,"MCALLER2 total %lu\n",total);
  for(int j=0;j<na && j<40;j++) fprintf(stderr,"MCALLER2 %12lu %5.1f%% %s <- %s\n",ag[j].n,100.0*ag[j].n/total,ag[j].n0,ag[j].n1); }
typedef struct { const void *r; const void *o; } interpose_t;
__attribute__((used)) static const interpose_t ip[] __attribute__((section("__DATA,__interpose"))) = {{(const void*)my_malloc,(const void*)malloc}};
