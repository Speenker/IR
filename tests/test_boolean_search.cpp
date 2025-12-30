#include <cassert>
#include <cstring>
#include <cstdio>
#include <cstdlib>
#include <cstdint>
#include <cmath>
#include <iostream>
#include <vector>
#include <string>

static void* xmalloc(size_t n){ void* p=std::malloc(n); if(!p){std::fprintf(stderr,"OOM\n"); std::exit(2);} return p; }
static void* xrealloc(void* p,size_t n){ void* q=std::realloc(p,n); if(!q){std::fprintf(stderr,"OOM\n"); std::exit(2);} return q; }
static char* xstrdup(const char* s){ size_t n=std::strlen(s); char* p=(char*)xmalloc(n+1); std::memcpy(p,s,n+1); return p; }

static const char* stop_words[] = {
    "и","в","во","не","что","он","на","я","с","со","как","а","то","все","она","так","его","но","да",
    "ты","к","у","же","вы","за","бы","по","ее","мне","было","вот","от","меня","еще","нет","о","из",
    "ему","теперь","когда","даже","ну","вдруг","ли","если","уже","или","ни","быть","был","него","до",
    "вас","нибудь","опять","уж","вам","ведь","там","потом","себя","ничего","ей","может","они","тут",
    "где","есть","надо","ней","для","мы","тебя","их","чем","была","сам","чтоб","без","будто","чего",
    "раз","тоже","себе","под","будет","ж","тогда","кто","этот","того","потому","этого","какой","совсем",
    "ним","здесь","этом","один","почти","мой","тем","чтобы","нее","сейчас","были","куда","зачем","всех",
    "никогда","можно","при","наконец","два","об","другой","хоть","после","над","больше","тот","через",
    "эти","нас","про","всего","них","какая","много","разве","три","эту","моя","впрочем","хорошо","свою",
    "этой","перед","иногда","лучше","чуть","том","нельзя","такой","им","более","всегда","конечно","всю",
    "между",
};
static int num_stop_words = sizeof(stop_words)/sizeof(stop_words[0]);
int is_stop_word(const char* s) {
    for(int i=0; i<num_stop_words; i++) if(std::strcmp(s, stop_words[i]) == 0) return 1;
    return 0;
}

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

char* normalize_term(const char* s_in, int yo2e){
   
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

enum TokType { T_TERM, T_AND, T_OR, T_NOT, T_LP, T_RP };

struct Tok { TokType t; char* s; };

static int is_space(char c){ return c==' '||c=='\t'||c=='\r'||c=='\n'; }

static Tok* toks_push(Tok* arr, uint32_t* n, uint32_t* cap, Tok x){
    if(*n >= *cap){ *cap = (*cap ? (*cap*2) : 64); arr=(Tok*)xrealloc(arr, sizeof(Tok)*(size_t)(*cap)); }
    arr[(*n)++] = x;
    return arr;
}

Tok* tokenize_basic(const char* q, uint32_t* out_n, int yo2e){
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
        if(norm[0] && !is_stop_word(norm)){ Tok x={T_TERM,norm}; arr=toks_push(arr,&n,&cap,x); }
        else std::free(norm);
    }
    *out_n=n;
    return arr;
}

static int is_operand_or_close(TokType t){ return t==T_TERM || t==T_RP; }
static int is_operand_or_open_or_not(TokType t){ return t==T_TERM || t==T_LP || t==T_NOT; }

Tok* inject_implicit_and(Tok* in, uint32_t nin, uint32_t* out_n){
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

Tok* to_postfix(const Tok* in, uint32_t nin, uint32_t* out_n){
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

uint32_t* list_and(const uint32_t* a, uint32_t na, const uint32_t* b, uint32_t nb, uint32_t* out_n){
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
uint32_t* list_or(const uint32_t* a, uint32_t na, const uint32_t* b, uint32_t nb, uint32_t* out_n){
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
uint32_t* list_not(const uint32_t* universe, uint32_t nu, const uint32_t* b, uint32_t nb, uint32_t* out_n){
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

int main() {
    
    assert(is_stop_word("и") == 1);
    assert(is_stop_word("word") == 0);

    char* norm = normalize_term("PYTHON", 1);
    assert(std::strcmp(norm, "python") == 0);
    std::free(norm);



    uint32_t a[] = {1,3,5};
    uint32_t b[] = {2,3,4};
    uint32_t out_n = 0;
    uint32_t* res = list_and(a, 3, b, 3, &out_n);
    assert(out_n == 1 && res[0] == 3);
    std::free(res);

    res = list_or(a, 3, b, 3, &out_n);
    assert(out_n == 5);
    assert(res[0] == 1 && res[1] == 2 && res[2] == 3 && res[3] == 4 && res[4] == 5);
    std::free(res);

    uint32_t universe[] = {1,2,3,4,5};
    uint32_t c[] = {2,4};
    res = list_not(universe, 5, c, 2, &out_n);
    assert(out_n == 3);
    assert(res[0] == 1 && res[1] == 3 && res[2] == 5);
    std::free(res);

    std::cout << "All search tests passed!" << std::endl;
    return 0;
}