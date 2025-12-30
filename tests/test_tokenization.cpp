#include <cassert>
#include <cstring>
#include <cstdio>
#include <cstdint>
#include <iostream>

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

int csv_get_field(const char* line, int field_idx, char* out, int out_cap) {
    int idx = 0;
    int in_q = 0;
    int o = 0;
    for (const char* p = line; *p; p++) {
        char c = *p;
        if (c == '\r' || c == '\n') break;
        if (!in_q) {
            if (c == '"') { in_q = 1; continue; }
            if (c == ',') { idx++; if (idx > field_idx) break; continue; }
            if (idx == field_idx && o < out_cap - 1) out[o++] = c;
        } else {
            if (c == '"' && p[1] == '"') { if (idx == field_idx && o < out_cap - 1) out[o++] = '"'; p++; continue; }
            if (c == '"') { in_q = 0; continue; }
            if (idx == field_idx && o < out_cap - 1) out[o++] = c;
        }
    }
    out[o] = 0;
    return (idx >= field_idx) ? 1 : 0;
}

int main() {
    uint32_t cp;
    size_t i = 0;
    const unsigned char* test = (const unsigned char*)"hello";
    assert(utf8_read(test, 5, &i, &cp) && cp == 'h');
    i = 0;
    const unsigned char* cyr = (const unsigned char*)"привет";
    assert(utf8_read(cyr, 12, &i, &cp) && cp == 0x043F);

    char buf[8];
    int len = utf8_write(buf, 'A');
    assert(len == 1 && buf[0] == 'A');
    len = utf8_write(buf, 0x043F);
    assert(len == 2);

    assert(is_latin('A'));
    assert(is_cyrillic_ru(0x0410));
    assert(is_digit('5'));

    char out[256];
    assert(csv_get_field("hello,world,test", 0, out, sizeof(out)));
    assert(std::strcmp(out, "hello") == 0);
    assert(csv_get_field("hello,world,test", 1, out, sizeof(out)));
    assert(std::strcmp(out, "world") == 0);

    std::cout << "All tokenization tests passed!" << std::endl;
    return 0;
}