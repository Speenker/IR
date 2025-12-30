#include <cassert>
#include <cstring>
#include <cstdio>
#include <cstdlib>
#include <cstdint>
#include <cmath>
#include <iostream>
#include <vector>
#include <string>


static void* xmalloc(size_t n) {
    void* p = std::malloc(n);
    if (!p) { std::fprintf(stderr, "OOM\n"); std::exit(2); }
    return p;
}

static uint32_t fnv1a32(const char* s) {
    uint32_t h = 2166136261u;
    for (; *s; ++s) { h ^= (unsigned char)(*s); h *= 16777619u; }
    return h ? h : 1u;
}

static const char* stop_words[] = {
    "и", "в", "не", "на", "с", "по", "для", "как", "из", "к", "а", "то", "что", "это", "он", "она", "оно", "они", "мы", "вы", "я", "его", "ее", "их", "наш", "ваш", "мой", "твой",
    "этот", "тот", "такой", "какой", "где", "когда", "почему", "если", "или", "но", "да", "нет", "ну", "вот", "здесь", "там", "тут", "туда", "сюда",
    "от", "до", "из", "к", "на", "под", "над", "за", "перед", "после", "во", "со", "про", "через", "между", "без", "для", "о", "об", "при", "по", "с", "у"
};
static int num_stop_words = sizeof(stop_words)/sizeof(stop_words[0]);
static int is_stop_word(const char* s) {
    for(int i=0; i<num_stop_words; i++) if(std::strcmp(s, stop_words[i]) == 0) return 1;
    return 0;
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

int csv_find_col(const char* header_line, const char* col_name) {
    char tmp[256];
    for (int i = 0; i < 256; i++) {
        tmp[0] = 0;
        if (!csv_get_field(header_line, i, tmp, (int)sizeof(tmp))) break;
        if (std::strcmp(tmp, col_name) == 0) return i;
    }
    return -1;
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

#define TERM_HT_CAP 100
struct TermEntry {
    char* term;
    uint32_t hash;
    uint32_t df;
    TermEntry* next;
};
static TermEntry* term_ht[TERM_HT_CAP];

static TermEntry* term_find_or_add(const char* term) {
    uint32_t h = fnv1a32(term);
    uint32_t b = h % TERM_HT_CAP;
    for (TermEntry* e = term_ht[b]; e; e = e->next) {
        if (e->hash == h && std::strcmp(e->term, term) == 0) return e;
    }
    TermEntry* e = (TermEntry*)xmalloc(sizeof(TermEntry));
    std::memset(e, 0, sizeof(*e));
    e->term = (char*)xmalloc(std::strlen(term) + 1);
    std::strcpy(e->term, term);
    e->hash = h;
    e->df = 0;
    e->next = term_ht[b];
    term_ht[b] = e;
    return e;
}

static void term_add_docid(TermEntry* e, uint32_t docid) {
    (void)docid;
    e->df++;
}

void tokenize_and_index(const unsigned char* s, size_t n,
                        uint32_t docid, int keep_numbers, int yo2e, int min_len,
                        uint64_t* io_tokens_total, uint64_t* io_token_chars_total, uint64_t* io_doc_len) {
    char tok[512];
    int tlen_bytes = 0;
    int tlen_chars = 0;
    uint64_t tok_count = 0;

    size_t i = 0;
    while (1) {
        uint32_t cp = 0;
        if (!utf8_read(s, n, &i, &cp)) break;

        cp = to_lower_ru(cp);
        if (yo2e) cp = yo_to_e(cp);

        int is_word = is_latin(cp) || is_cyrillic_ru(cp) || (keep_numbers && is_digit(cp));
        if (is_word) {
            if (tlen_bytes < (int)sizeof(tok) - 8) {
                char tmp[8];
                int w = utf8_write(tmp, cp);
                for (int k = 0; k < w && tlen_bytes < (int)sizeof(tok) - 1; k++) tok[tlen_bytes++] = tmp[k];
                tlen_chars++;
            }
        } else {
            if (tlen_chars >= min_len) {
                tok[tlen_bytes] = 0;

                ru_stem_inplace(tok);
                if ((int)std::strlen(tok) >= min_len && !is_stop_word(tok)) {
                    TermEntry* e = term_find_or_add(tok);
                    term_add_docid(e, docid);
                    if (io_tokens_total) (*io_tokens_total)++;
                    if (io_token_chars_total) (*io_token_chars_total) += (uint64_t)tlen_chars;
                    tok_count++;
                }
            }
            tlen_bytes = 0;
            tlen_chars = 0;
        }
    }
    if (tlen_chars >= min_len) {
        tok[tlen_bytes] = 0;

        ru_stem_inplace(tok);
        if ((int)std::strlen(tok) >= min_len && !is_stop_word(tok)) {
            TermEntry* e = term_find_or_add(tok);
            term_add_docid(e, docid);
            if (io_tokens_total) (*io_tokens_total)++;
            if (io_token_chars_total) (*io_token_chars_total) += (uint64_t)tlen_chars;
            tok_count++;
        }
    }
    if (io_doc_len) *io_doc_len = tok_count;
}

int main() {
    const char* header = "doc_id,final_url,text_path";
    assert(csv_find_col(header, "doc_id") == 0);
    assert(csv_find_col(header, "final_url") == 1);
    assert(csv_find_col(header, "text_path") == 2);
    assert(csv_find_col(header, "missing") == -1);

    char out[256];
    assert(csv_get_field("1,http://example.com,file.txt", 0, out, sizeof(out)));
    assert(std::strcmp(out, "1") == 0);
    assert(csv_get_field("1,http://example.com,file.txt", 1, out, sizeof(out)));
    assert(std::strcmp(out, "http://example.com") == 0);
    assert(csv_get_field("1,http://example.com,file.txt", 2, out, sizeof(out)));
    assert(std::strcmp(out, "file.txt") == 0);
    assert(!csv_get_field("1,http://example.com,file.txt", 3, out, sizeof(out)));

    assert(is_stop_word("и") == 1);
    assert(is_stop_word("word") == 0);

    const unsigned char* text = (const unsigned char*)"hello world hello";
    uint64_t tokens_total = 0, token_chars_total = 0, doc_len = 0;
    tokenize_and_index(text, std::strlen((const char*)text), 1, 0, 1, 2, &tokens_total, &token_chars_total, &doc_len);
    assert(tokens_total == 3);
    assert(doc_len == 3);
    TermEntry* e1 = term_find_or_add("hello");
    assert(e1->df == 2);
    TermEntry* e2 = term_find_or_add("world");
    assert(e2->df == 1);

    std::cout << "All indexing tests passed!" << std::endl;
    return 0;
}