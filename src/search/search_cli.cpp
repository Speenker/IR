
#include <cstdio>
#include <cstdlib>
#include <cstdint>
#include <cstring>

static void* xmalloc(size_t n){ void* p=std::malloc(n); if(!p){std::fprintf(stderr,"OOM\n"); std::exit(2);} return p; }
static void* xrealloc(void* p,size_t n){ void* q=std::realloc(p,n); if(!q){std::fprintf(stderr,"OOM\n"); std::exit(2);} return q; }
static char* xstrdup(const char* s){ size_t n=std::strlen(s); char* p=(char*)xmalloc(n+1); std::memcpy(p,s,n+1); return p; }
static void normalize_seps(char* s){
#ifndef _WIN32
    for (; *s; ++s) if (*s=='\\') *s='/';
#else
    (void)s;
#endif
}

static uint32_t read_u32(FILE* f){ uint32_t v=0; std::fread(&v,4,1,f); return v; }
static uint64_t read_u64(FILE* f){ uint64_t v=0; std::fread(&v,8,1,f); return v; }
static uint16_t read_u16(FILE* f){ uint16_t v=0; std::fread(&v,2,1,f); return v; }


struct InvHeader {
    char magic[4];      
    uint32_t version;   
    uint32_t term_count;
    uint32_t doc_count;
    uint64_t postings_off;
    uint64_t dict_off;
    uint8_t reserved[32];
};

struct FwdHeader {
    char magic[4];       
    uint32_t version;    
    uint32_t doc_count;
    uint32_t min_docid;
    uint32_t max_docid;
    uint64_t offsets_off;
    uint8_t reserved[32];
};

struct DictEntry {
    char* term;
    uint32_t df;
    uint64_t postings_off;
};

struct Index {
    FILE* finv;
    FILE* ffwd;
    InvHeader ih;
    FwdHeader fh;
    DictEntry* dict;
    uint32_t dict_n;

    uint64_t* fwd_offsets;   
    uint32_t all_docs_n;
    uint32_t* all_docs;      
};


static int utf8_read(const unsigned char* s, size_t n, size_t* i, uint32_t* out){
    if(*i>=n) return 0;
    unsigned char c0=s[*i];
    if(c0<0x80){ *out=c0; (*i)++; return 1; }
    int need=0; uint32_t cp=0;
    if((c0&0xE0)==0xC0){ need=1; cp=c0&0x1F; }
    else if((c0&0xF0)==0xE0){ need=2; cp=c0&0x0F; }
    else if((c0&0xF8)==0xF0){ need=3; cp=c0&0x07; }
    else { (*i)++; return 1; }
    if(*i+(size_t)need>=n){ *i=n; return 1; }
    for(int k=1;k<=need;k++){
        unsigned char cx=s[*i+(size_t)k];
        if((cx&0xC0)!=0x80){ (*i)++; return 1; }
        cp=(cp<<6)|(cx&0x3F);
    }
    *out=cp;
    *i+=(size_t)need+1;
    return 1;
}
static int utf8_write(char* buf, uint32_t cp){
    if (cp<=0x7F){ buf[0]=(char)cp; return 1; }
    if (cp<=0x7FF){ buf[0]=(char)(0xC0|((cp>>6)&0x1F)); buf[1]=(char)(0x80|(cp&0x3F)); return 2; }
    if (cp<=0xFFFF){ buf[0]=(char)(0xE0|((cp>>12)&0x0F)); buf[1]=(char)(0x80|((cp>>6)&0x3F)); buf[2]=(char)(0x80|(cp&0x3F)); return 3; }
    buf[0]=(char)(0xF0|((cp>>18)&0x07)); buf[1]=(char)(0x80|((cp>>12)&0x3F)); buf[2]=(char)(0x80|((cp>>6)&0x3F)); buf[3]=(char)(0x80|(cp&0x3F)); return 4;
}
static int is_digit(uint32_t cp){ return cp>='0' && cp<='9'; }
static int is_latin(uint32_t cp){ return (cp>='A'&&cp<='Z')||(cp>='a'&&cp<='z'); }
static int is_cyr(uint32_t cp){ return (cp>=0x0410&&cp<=0x044F)||cp==0x0401||cp==0x0451; }
static uint32_t to_lower_ru(uint32_t cp){
    if(cp>='A'&&cp<='Z') return cp+32;
    if(cp>=0x0410&&cp<=0x042F) return cp+0x20;
    if(cp==0x0401) return 0x0451;
    return cp;
}
static uint32_t yo_to_e(uint32_t cp){
    if(cp==0x0451) return 0x0435;
    if(cp==0x0401) return 0x0415;
    return cp;
}

static void ru_stem_inplace(char* s) {
    int len = (int)std::strlen(s);
    if (len <= 3) return;

    const char* suffixes[] = {
        "ыми","ими","ого","его","ому","ему","ами","ями","ов","ев","ей","ой","ей","ою","ею",
        "ах","ях","ам","ям","ом","ем","ым","им","ах","ях",
        "ать","ять","еть","оть","уть","ешь","ишь","ете","ите","ают","яют","уют","ют","ут",
        "лся","лась","лись","лось",
        "ия","ий","ый","ий","ое","ее","ая","яя",
        "а","я","о","е","ы","и","у","ю"
    };
    int suf_count = (int)(sizeof(suffixes)/sizeof(suffixes[0]));

    for (int i = 0; i < suf_count; i++) {
        const char* suf = suffixes[i];
        int slen = (int)std::strlen(suf);
        if (len <= slen + 2) continue;
        if (std::strcmp(s + len - slen, suf) == 0) {
            s[len - slen] = 0;
            len -= slen;
            break;
        }
    }
}

static char* normalize_term(const char* s_in, int yo2e){
  
    const unsigned char* s=(const unsigned char*)s_in;
    size_t n=std::strlen(s_in);
    char out[512];
    int olen=0;
    size_t i=0;
    while(1){
        uint32_t cp=0;
        if(!utf8_read(s,n,&i,&cp)) break;
        cp=to_lower_ru(cp);
        if(yo2e) cp=yo_to_e(cp);
        int ok = is_latin(cp) || is_cyr(cp) || is_digit(cp);
        if(!ok) continue;
        if(olen >= (int)sizeof(out)-8) break;
        char tmp[8];
        int w=utf8_write(tmp,cp);
        for(int k=0;k<w && olen<(int)sizeof(out)-1;k++) out[olen++]=tmp[k];
    }
    out[olen]=0;
    ru_stem_inplace(out);
    return xstrdup(out);
}


static int cmp_dict_term(const void* a, const void* b){
    const DictEntry* x=(const DictEntry*)a;
    const DictEntry* y=(const DictEntry*)b;
    return std::strcmp(x->term,y->term);
}

static int dict_find(Index* idx, const char* term){
    
    int lo=0, hi=(int)idx->dict_n-1;
    while(lo<=hi){
        int mid=(lo+hi)/2;
        int c=std::strcmp(idx->dict[mid].term, term);
        if(c==0) return mid;
        if(c<0) lo=mid+1; else hi=mid-1;
    }
    return -1;
}

static uint32_t* load_postings(Index* idx, uint64_t off, uint32_t* out_n){
    std::fseek(idx->finv, (long)off, SEEK_SET);
    uint32_t df=read_u32(idx->finv);
    uint32_t* a=(uint32_t*)xmalloc(sizeof(uint32_t)* (size_t)df);
    if(df) std::fread(a, sizeof(uint32_t), df, idx->finv);
    *out_n=df;
    return a;
}


static uint64_t fwd_offset(Index* idx, uint32_t docid){
    if(docid < idx->fh.min_docid || docid > idx->fh.max_docid) return 0;
    return idx->fwd_offsets[docid - idx->fh.min_docid];
}

static int fwd_get(Index* idx, uint32_t docid, char* title, int title_cap, char* url, int url_cap){
    uint64_t off=fwd_offset(idx, docid);
    if(off==0) return 0;
    std::fseek(idx->ffwd, (long)off, SEEK_SET);
    uint32_t did=read_u32(idx->ffwd);
    if(did!=docid) {  }
    uint16_t ulen=read_u16(idx->ffwd);
    int ur = (ulen < (uint16_t)(url_cap-1)) ? (int)ulen : (url_cap-1);
    if(ur>0) std::fread(url,1,(size_t)ur,idx->ffwd);
    url[ur]=0;
    if(ulen > (uint16_t)ur) std::fseek(idx->ffwd, (long)(ulen-ur), SEEK_CUR);

    uint16_t tlen=read_u16(idx->ffwd);
    int tr = (tlen < (uint16_t)(title_cap-1)) ? (int)tlen : (title_cap-1);
    if(tr>0) std::fread(title,1,(size_t)tr,idx->ffwd);
    title[tr]=0;
    return 1;
}


static uint32_t* list_and(const uint32_t* a, uint32_t na, const uint32_t* b, uint32_t nb, uint32_t* out_n){
    uint32_t* out=(uint32_t*)xmalloc(sizeof(uint32_t)*(size_t)((na<nb)?na:nb));
    uint32_t i=0,j=0,k=0;
    while(i<na && j<nb){
        uint32_t x=a[i], y=b[j];
        if(x==y){ out[k++]=x; i++; j++; }
        else if(x<y) i++; else j++;
    }
    *out_n=k;
    return out;
}
static uint32_t* list_or(const uint32_t* a, uint32_t na, const uint32_t* b, uint32_t nb, uint32_t* out_n){
    uint32_t* out=(uint32_t*)xmalloc(sizeof(uint32_t)*(size_t)(na+nb));
    uint32_t i=0,j=0,k=0;
    while(i<na || j<nb){
        if(j>=nb || (i<na && a[i]<b[j])) out[k++]=a[i++];
        else if(i>=na || (j<nb && b[j]<a[i])) out[k++]=b[j++];
        else { out[k++]=a[i]; i++; j++; }
    }
    *out_n=k;
    return out;
}
static uint32_t* list_not(const uint32_t* universe, uint32_t nu, const uint32_t* b, uint32_t nb, uint32_t* out_n){
    uint32_t* out=(uint32_t*)xmalloc(sizeof(uint32_t)*(size_t)nu);
    uint32_t i=0,j=0,k=0;
    while(i<nu){
        if(j>=nb){ out[k++]=universe[i++]; continue; }
        uint32_t x=universe[i], y=b[j];
        if(x==y){ i++; j++; }
        else if(x<y){ out[k++]=x; i++; }
        else { j++; }
    }
    *out_n=k;
    return out;
}


enum TokType { T_TERM, T_AND, T_OR, T_NOT, T_LP, T_RP };

struct Tok { TokType t; char* s; };

static int is_space(char c){ return c==' '||c=='\t'||c=='\r'||c=='\n'; }

static Tok* toks_push(Tok* arr, uint32_t* n, uint32_t* cap, Tok x){
    if(*n >= *cap){ *cap = (*cap ? (*cap*2) : 64); arr=(Tok*)xrealloc(arr, sizeof(Tok)*(size_t)(*cap)); }
    arr[(*n)++] = x;
    return arr;
}

static Tok* tokenize_basic(const char* q, uint32_t* out_n, int yo2e){
    Tok* arr=NULL; uint32_t n=0, cap=0;
    const char* p=q;
    while(*p){
        if(is_space(*p)){ p++; continue; }
        if(p[0]=='&' && p[1]=='&'){ Tok x={T_AND,NULL}; arr=toks_push(arr,&n,&cap,x); p+=2; continue; }
        if(p[0]=='|' && p[1]=='|'){ Tok x={T_OR,NULL}; arr=toks_push(arr,&n,&cap,x); p+=2; continue; }
        if(*p=='!'){ Tok x={T_NOT,NULL}; arr=toks_push(arr,&n,&cap,x); p++; continue; }
        if(*p=='('){ Tok x={T_LP,NULL}; arr=toks_push(arr,&n,&cap,x); p++; continue; }
        if(*p==')'){ Tok x={T_RP,NULL}; arr=toks_push(arr,&n,&cap,x); p++; continue; }

        
        char buf[1024]; int bl=0;
        while(*p && !is_space(*p)){
            
            if(p[0]=='&'&&p[1]=='&') break;
            if(p[0]=='|'&&p[1]=='|') break;
            if(*p=='!'||*p=='('||*p==')') break;
            if(bl < (int)sizeof(buf)-1) buf[bl++] = *p;
            p++;
        }
        buf[bl]=0;
        char* norm = normalize_term(buf, yo2e);
        if(norm[0]){ Tok x={T_TERM,norm}; arr=toks_push(arr,&n,&cap,x); }
        else std::free(norm);
    }
    *out_n=n;
    return arr;
}

static int is_operand_or_close(TokType t){ return t==T_TERM || t==T_RP; }
static int is_operand_or_open_or_not(TokType t){ return t==T_TERM || t==T_LP || t==T_NOT; }

static Tok* inject_implicit_and(Tok* in, uint32_t nin, uint32_t* out_n){
    Tok* out=NULL; uint32_t n=0, cap=0;
    for(uint32_t i=0;i<nin;i++){
        out=toks_push(out,&n,&cap,in[i]);
        if(i+1<nin){
            TokType a=in[i].t;
            TokType b=in[i+1].t;
            if(is_operand_or_close(a) && is_operand_or_open_or_not(b)){
                Tok x={T_AND,NULL};
                out=toks_push(out,&n,&cap,x);
            }
        }
    }
    *out_n=n;
    return out;
}

static int prec(TokType t){
    if(t==T_NOT) return 3;
    if(t==T_AND) return 2;
    if(t==T_OR)  return 1;
    return 0;
}
static int is_right_assoc(TokType t){ return t==T_NOT; }

static Tok* to_postfix(const Tok* in, uint32_t nin, uint32_t* out_n){
    Tok* out=NULL; uint32_t on=0, ocap=0;
    Tok* st=NULL;  uint32_t sn=0, scap=0;

    for(uint32_t i=0;i<nin;i++){
        Tok cur=in[i];
        if(cur.t==T_TERM){
            out=toks_push(out,&on,&ocap,cur);
        } else if(cur.t==T_LP){
            st=toks_push(st,&sn,&scap,cur);
        } else if(cur.t==T_RP){
            while(sn>0 && st[sn-1].t!=T_LP) out=toks_push(out,&on,&ocap,st[--sn]);
            if(sn>0 && st[sn-1].t==T_LP) sn--;
        } else {
            while(sn>0){
                TokType top=st[sn-1].t;
                if(top==T_LP) break;
                int ptop=prec(top), pcur=prec(cur.t);
                if(ptop>pcur || (ptop==pcur && !is_right_assoc(cur.t))){
                    out=toks_push(out,&on,&ocap,st[--sn]);
                } else break;
            }
            st=toks_push(st,&sn,&scap,cur);
        }
    }
    while(sn>0) out=toks_push(out,&on,&ocap,st[--sn]);
    std::free(st);
    *out_n=on;
    return out;
}


struct List { uint32_t* a; uint32_t n; };

static List* stack_push(List* st, uint32_t* n, uint32_t* cap, List x){
    if(*n>=*cap){ *cap=(*cap?(*cap*2):64); st=(List*)xrealloc(st,sizeof(List)*(size_t)(*cap)); }
    st[(*n)++]=x;
    return st;
}

static List eval_postfix(Index* idx, Tok* pf, uint32_t npf){
    List* st=NULL; uint32_t sn=0, scap=0;

    for(uint32_t i=0;i<npf;i++){
        Tok t=pf[i];
        if(t.t==T_TERM){
            int pos=dict_find(idx, t.s);
            if(pos<0){
                uint32_t* empty=(uint32_t*)xmalloc(0);
                List x={empty,0};
                st=stack_push(st,&sn,&scap,x);
            } else {
                uint32_t dn=0;
                uint32_t* a=load_postings(idx, idx->dict[pos].postings_off, &dn);
                List x={a,dn};
                st=stack_push(st,&sn,&scap,x);
            }
        } else if(t.t==T_NOT){
            if(sn<1){ continue; }
            List b=st[--sn];
            uint32_t rn=0;
            uint32_t* r=list_not(idx->all_docs, idx->all_docs_n, b.a, b.n, &rn);
            std::free(b.a);
            List x={r,rn};
            st=stack_push(st,&sn,&scap,x);
        } else if(t.t==T_AND || t.t==T_OR){
            if(sn<2){ continue; }
            List b=st[--sn];
            List a=st[--sn];
            uint32_t rn=0;
            uint32_t* r = (t.t==T_AND) ? list_and(a.a,a.n,b.a,b.n,&rn) : list_or(a.a,a.n,b.a,b.n,&rn);
            std::free(a.a); std::free(b.a);
            List x={r,rn};
            st=stack_push(st,&sn,&scap,x);
        }
    }

    List res;
    if(sn==0){ res.a=(uint32_t*)xmalloc(0); res.n=0; }
    else { res=st[sn-1]; }
   
    for(uint32_t i=0;i+1<sn;i++) std::free(st[i].a);
    std::free(st);
    return res;
}


static int load_index(Index* idx, const char* inv_path, const char* fwd_path){
    std::memset(idx,0,sizeof(*idx));

    idx->finv=std::fopen(inv_path,"rb");
    if(!idx->finv){ std::fprintf(stderr,"ERROR: cannot open %s\n", inv_path); return 0; }
    idx->ffwd=std::fopen(fwd_path,"rb");
    if(!idx->ffwd){ std::fprintf(stderr,"ERROR: cannot open %s\n", fwd_path); return 0; }

    std::fread(&idx->ih, sizeof(idx->ih), 1, idx->finv);
    std::fread(&idx->fh, sizeof(idx->fh), 1, idx->ffwd);

    if(std::memcmp(idx->ih.magic,"INV1",4)!=0 || std::memcmp(idx->fh.magic,"FWD1",4)!=0){
        std::fprintf(stderr,"ERROR: bad magic in index files\n");
        return 0;
    }

   
    idx->dict_n = idx->ih.term_count;
    idx->dict = (DictEntry*)xmalloc(sizeof(DictEntry)*(size_t)idx->dict_n);
    std::fseek(idx->finv, (long)idx->ih.dict_off, SEEK_SET);
    for(uint32_t i=0;i<idx->dict_n;i++){
        uint16_t tl=read_u16(idx->finv);
        char* term=(char*)xmalloc((size_t)tl+1);
        if(tl) std::fread(term,1,tl,idx->finv);
        term[tl]=0;
        uint32_t df=read_u32(idx->finv);
        uint64_t off=read_u64(idx->finv);
        idx->dict[i].term=term;
        idx->dict[i].df=df;
        idx->dict[i].postings_off=off;
    }

   
    uint32_t range = (idx->fh.max_docid >= idx->fh.min_docid) ? (idx->fh.max_docid - idx->fh.min_docid + 1) : 0;
    idx->fwd_offsets = (uint64_t*)xmalloc(sizeof(uint64_t)*(size_t)range);
    std::fseek(idx->ffwd, (long)idx->fh.offsets_off, SEEK_SET);
    for(uint32_t i=0;i<range;i++) idx->fwd_offsets[i]=read_u64(idx->ffwd);

   
    idx->all_docs = (uint32_t*)xmalloc(sizeof(uint32_t)*(size_t)range);
    uint32_t k=0;
    for(uint32_t i=0;i<range;i++){
        if(idx->fwd_offsets[i]!=0){
            idx->all_docs[k++] = idx->fh.min_docid + i;
        }
    }
    idx->all_docs_n = k;
    return 1;
}

static void free_index(Index* idx){
    if(idx->dict){
        for(uint32_t i=0;i<idx->dict_n;i++) std::free(idx->dict[i].term);
        std::free(idx->dict);
    }
    if(idx->fwd_offsets) std::free(idx->fwd_offsets);
    if(idx->all_docs) std::free(idx->all_docs);
    if(idx->finv) std::fclose(idx->finv);
    if(idx->ffwd) std::fclose(idx->ffwd);
}


static void usage(){
    std::fprintf(stderr,
        "Usage:\n"
        "  search_cli --inv index/inv.bin --fwd index/fwd.bin [--queries file]\n"
    );
}

int main(int argc, char** argv){
    const char* inv="index/inv.bin";
    const char* fwd="index/fwd.bin";
    const char* queries_path=NULL;
    int offset = 0;
    int limit = 50;

    for(int i=1;i<argc;i++){
        if(std::strcmp(argv[i],"--inv")==0 && i+1<argc) inv=argv[++i];
        else if(std::strcmp(argv[i],"--fwd")==0 && i+1<argc) fwd=argv[++i];
        else if(std::strcmp(argv[i],"--queries")==0 && i+1<argc) queries_path=argv[++i];
        else if(std::strcmp(argv[i],"--offset")==0 && i+1<argc) offset = std::atoi(argv[++i]);
        else if(std::strcmp(argv[i],"--limit")==0 && i+1<argc)  limit  = std::atoi(argv[++i]);
        else { usage(); return 1; }
    }

    Index idx;
    if(!load_index(&idx, inv, fwd)) return 2;

    FILE* in = queries_path ? std::fopen(queries_path,"rb") : stdin;
    if(queries_path && !in){ std::fprintf(stderr,"ERROR: cannot open %s\n", queries_path); return 3; }

    char q[8192];
    while(true){
        if(!queries_path){
            std::fprintf(stderr, "query> ");
            std::fflush(stderr);
        }
        if(!std::fgets(q, (int)sizeof(q), in)) break;

       
        size_t L=std::strlen(q);
        while(L>0 && (q[L-1]=='\r'||q[L-1]=='\n')) q[--L]=0;
        if(L==0) continue;

        uint32_t n0=0;
        Tok* t0=tokenize_basic(q, &n0, 1);
        uint32_t n1=0;
        Tok* t1=inject_implicit_and(t0, n0, &n1);
        std::free(t0); 


        uint32_t npf=0;
        Tok* pf=to_postfix(t1, n1, &npf);
        std::free(t1);

        List res = eval_postfix(&idx, pf, npf);

       

        for(uint32_t i=0;i<npf;i++) if(pf[i].t==T_TERM && pf[i].s) std::free(pf[i].s);
        std::free(pf);

       
        if (offset < 0) offset = 0;
        if (limit <= 0) limit = 50;

        uint32_t shown = 0;
        for (uint32_t i = (uint32_t)offset; i < res.n && shown < (uint32_t)limit; i++) {
            char title[512], urlbuf[2048];
            if (fwd_get(&idx, res.a[i], title, (int)sizeof(title), urlbuf, (int)sizeof(urlbuf))) {
                std::printf("%u\t%s\t%s\n", res.a[i], title, urlbuf);
                shown++;
            }
        }


        std::free(res.a);
        if(!queries_path) std::printf("\n");
    }

    if(queries_path) std::fclose(in);
    free_index(&idx);
    return 0;
}
