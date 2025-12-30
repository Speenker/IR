#include <cassert>
#include <cstring>
#include <cstdio>
#include <cstdlib>
#include <cstdint>
#include <iostream>

static void* xmalloc(size_t n) {
    void* p = std::malloc(n);
    if (!p) { std::fprintf(stderr, "OOM\n"); std::exit(2); }
    return p;
}
static char* xstrdup(const char* s) {
    size_t n = std::strlen(s);
    char* p = (char*)xmalloc(n + 1);
    std::memcpy(p, s, n + 1);
    return p;
}

static int utf8_read(const unsigned char* s, size_t n, size_t* i, uint32_t* out) {
    if (*i >= n) return 0;
    unsigned char c0 = s[*i];
    if (c0 < 0x80) { *out = c0; (*i)++; return 1; }
    int need = 0;
    uint32_t cp = 0;
    if ((c0 & 0xE0) == 0xC0) { need = 1; cp = c0 & 0x1F; }
    else if ((c0 & 0xF0) == 0xE0) { need = 2; cp = c0 & 0x0F; }
    else if ((c0 & 0xF8) == 0xF0) { need = 3; cp = c0 & 0x07; }
    else { (*i)++; return 1; }
    if (*i + (size_t)need >= n) { *i = n; return 1; }
    for (int k = 1; k <= need; k++) {
        unsigned char cx = s[*i + (size_t)k];
        if ((cx & 0xC0) != 0x80) { (*i)++; return 1; }
        cp = (cp << 6) | (cx & 0x3F);
    }
    *out = cp;
    *i += (size_t)need + 1;
    return 1;
}
static int utf8_write(char* buf, uint32_t cp) {
    if (cp <= 0x7F) { buf[0] = (char)cp; return 1; }
    if (cp <= 0x7FF) {
        buf[0] = (char)(0xC0 | ((cp >> 6) & 0x1F));
        buf[1] = (char)(0x80 | (cp & 0x3F));
        return 2;
    }
    if (cp <= 0xFFFF) {
        buf[0] = (char)(0xE0 | ((cp >> 12) & 0x0F));
        buf[1] = (char)(0x80 | ((cp >> 6) & 0x3F));
        buf[2] = (char)(0x80 | (cp & 0x3F));
        return 3;
    }
    buf[0] = (char)(0xF0 | ((cp >> 18) & 0x07));
    buf[1] = (char)(0x80 | ((cp >> 12) & 0x3F));
    buf[2] = (char)(0x80 | ((cp >> 6) & 0x3F));
    buf[3] = (char)(0x80 | (cp & 0x3F));
    return 4;
}
static int is_digit(uint32_t cp) { return cp >= '0' && cp <= '9'; }
static int is_latin(uint32_t cp) { return (cp >= 'A' && cp <= 'Z') || (cp >= 'a' && cp <= 'z'); }
static int is_cyrillic_ru(uint32_t cp) {
    return (cp >= 0x0410 && cp <= 0x044F) || cp == 0x0401 || cp == 0x0451;
}
static uint32_t to_lower_ru(uint32_t cp) {
    if (cp >= 'A' && cp <= 'Z') return cp + 32;
    if (cp >= 0x0410 && cp <= 0x042F) return cp + 0x20;
    if (cp == 0x0401) return 0x0451;
    return cp;
}
static uint32_t yo_to_e(uint32_t cp) {
    if (cp == 0x0451) return 0x0435;
    if (cp == 0x0401) return 0x0415;
    return cp;
}

void ru_stem_inplace(char* s) {
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

char* normalize_term(const char* s_in, int yo2e) {
    const unsigned char* s = (const unsigned char*)s_in;
    size_t n = std::strlen(s_in);
    char out[512];
    int olen = 0;
    size_t i = 0;
    while (1) {
        uint32_t cp = 0;
        if (!utf8_read(s, n, &i, &cp)) break;
        cp = to_lower_ru(cp);
        if (yo2e) cp = yo_to_e(cp);
        int ok = is_latin(cp) || is_cyrillic_ru(cp) || is_digit(cp);
        if (!ok) continue;
        if (olen >= (int)sizeof(out) - 8) break;
        char tmp[8];
        int w = utf8_write(tmp, cp);
        for (int k = 0; k < w && olen < (int)sizeof(out) - 1; k++) out[olen++] = tmp[k];
    }
    out[olen] = 0;
    ru_stem_inplace(out);
    return xstrdup(out);
}

int main() {
    char test1[256] = "домов";
    ru_stem_inplace(test1);
    assert(std::strcmp(test1, "дом") == 0);

    char test2[256] = "столов";
    ru_stem_inplace(test2);
    assert(std::strcmp(test2, "стол") == 0);

    char test3[256] = "делать";
    ru_stem_inplace(test3);
    assert(std::strcmp(test3, "дел") == 0);

    char* norm1 = normalize_term("ДОМОВ", 0);
    assert(std::strcmp(norm1, "дом") == 0);
    std::free(norm1);

    char* norm2 = normalize_term("ёлка", 1);
    assert(std::strcmp(norm2, "елк") == 0);
    std::free(norm2);

    char* norm3 = normalize_term("ёлка", 0);
    assert(std::strcmp(norm3, "ёлк") == 0);
    std::free(norm3);

    char* norm4 = normalize_term("hello123", 0);
    assert(std::strcmp(norm4, "hello123") == 0);
    std::free(norm4);

    std::cout << "All stemming tests passed!" << std::endl;
    return 0;
}