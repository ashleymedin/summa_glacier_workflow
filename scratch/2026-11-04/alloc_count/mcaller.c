// counts malloc calls by calling function (single-threaded runs) and prints the top callers at exit
#include <stdlib.h>
#include <stdio.h>
#include <dlfcn.h>
#include <stdint.h>
#define NB (1<<20)
static uintptr_t key[NB]; static unsigned long cnt[NB]; static unsigned long total;
static void *my_malloc(size_t s){
  uintptr_t ra=(uintptr_t)__builtin_return_address(0); total++;
  size_t h=(ra>>2)&(NB-1); while(key[h] && key[h]!=ra) h=(h+1)&(NB-1);
  key[h]=ra; cnt[h]++; return malloc(s); }
typedef struct { const char *name; unsigned long n; } agg_t;
static int cmp(const void *a,const void *b){ unsigned long x=((agg_t*)a)->n,y=((agg_t*)b)->n; return x<y?1:x>y?-1:0; }
__attribute__((destructor)) static void done(void){
  static agg_t ag[4096]; int na=0;
  for(size_t i=0;i<NB;i++) if(key[i]){
    Dl_info d; const char *nm = (dladdr((void*)key[i],&d) && d.dli_sname) ? d.dli_sname : "?";
    int j; for(j=0;j<na;j++) if(ag[j].name==nm) break;
    if(j==na && na<4096){ ag[na].name=nm; ag[na].n=0; na++; }
    if(j<4096) ag[j].n+=cnt[i]; }
  qsort(ag,na,sizeof(agg_t),cmp);
  fprintf(stderr,"MCALLER total %lu\n",total);
  for(int j=0;j<na && j<40;j++) fprintf(stderr,"MCALLER %12lu %5.1f%% %s\n",ag[j].n,100.0*ag[j].n/total,ag[j].name); }
typedef struct { const void *r; const void *o; } interpose_t;
__attribute__((used)) static const interpose_t ip[] __attribute__((section("__DATA,__interpose"))) = {{(const void*)my_malloc,(const void*)malloc}};
