#include <cstdio>
#include <cstdlib>
#include <cstdint>
#include <cstring>
#include <ctime>


static void* xmalloc(size_t n) {
    void* p = std::malloc(n);
    if (!p) { std::fprintf(stderr, "OOM\n"); std::exit(2); }
    return p;
}
static void* xrealloc(void* p, size_t n) {
    void* q = std::realloc(p, n);
    if (!q) { std::fprintf(stderr, "OOM\n"); std::exit(2); }
    return q;
}
static char* xstrdup(const char* s) {
    size_t n = std::strlen(s);
    char* p = (char*)xmalloc(n + 1);
    std::memcpy(p, s, n + 1);
    return p;
}
static uint32_t fnv1a32(const char* s) {
    uint32_t h = 2166136261u;
    for (; *s; ++s) { h ^= (unsigned char)(*s); h *= 16777619u; }
    return h ? h : 1u;
}
static unsigned char* read_file(const char* path, size_t* out_n, size_t limit_bytes) {
    FILE* f = std::fopen(path, "rb");
    if (!f) return NULL;
    if (std::fseek(f, 0, SEEK_END) != 0) { std::fclose(f); return NULL; }
    long sz = std::ftell(f);
    if (sz < 0) { std::fclose(f); return NULL; }
    if (std::fseek(f, 0, SEEK_SET) != 0) { std::fclose(f); return NULL; }
    if (limit_bytes > 0 && (size_t)sz > limit_bytes) { std::fclose(f); return NULL; }

    unsigned char* buf = (unsigned char*)xmalloc((size_t)sz + 1);
    size_t rd = std::fread(buf, 1, (size_t)sz, f);
    std::fclose(f);
    buf[rd] = 0;
    *out_n = rd;
    return buf;
}
static void write_u16(FILE* f, uint16_t v) { std::fwrite(&v, 2, 1, f); }
static void write_u32(FILE* f, uint32_t v) { std::fwrite(&v, 4, 1, f); }
static void write_u64(FILE* f, uint64_t v) { std::fwrite(&v, 8, 1, f); }
static uint16_t clamp_u16(size_t n) { return (n > 65535u) ? 65535u : (uint16_t)n; }

static void normalize_seps(char* s) {
#ifndef _WIN32
    for (; *s; ++s) if (*s == '\\') *s = '/';
#else
    (void)s;
#endif
}

static void join_path(char* out, int outcap, const char* root, const char* rel) {
    if (!rel) rel = "";
    if (!root) root = ".";
    if (!root[0]) { std::snprintf(out, (size_t)outcap, "%s", rel); normalize_seps(out); return; }

#ifdef _WIN32
    if ((std::strlen(rel) >= 2 && rel[1] == ':') || (rel[0] == '\\' && rel[1] == '\\')) {
        std::snprintf(out, (size_t)outcap, "%s", rel); return;
    }
#endif
    if (rel[0] == '/' ) { std::snprintf(out, (size_t)outcap, "%s", rel); normalize_seps(out); return; }

    std::snprintf(out, (size_t)outcap, "%s/%s", root, rel);
    normalize_seps(out);
}

static int csv_get_field(const char* line, int field_idx, char* out, int out_cap) {
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
static int csv_find_col(const char* header_line, const char* col_name) {
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

struct Posting {
    uint32_t docid;
    uint32_t tf;
};

static void encode_delta_vbyte(const Posting* postings, uint32_t n, uint8_t** out_buf, size_t* out_len) {
    if (n == 0) {
        *out_buf = NULL;
        *out_len = 0;
        return;
    }
    size_t max_len = 5 * (size_t)(n * 2 + 1);
    uint8_t* buf = (uint8_t*)xmalloc(max_len);
    size_t pos = 0;
    uint32_t x = postings[0].docid;
    do {
        uint8_t b = x & 0x7F;
        x >>= 7;
        if (x == 0) b |= 0x80;
        buf[pos++] = b;
    } while (x > 0);
    x = postings[0].tf;
    do {
        uint8_t b = x & 0x7F;
        x >>= 7;
        if (x == 0) b |= 0x80;
        buf[pos++] = b;
    } while (x > 0);
    uint32_t prev_doc = postings[0].docid;
    for (uint32_t i = 1; i < n; i++) {
        uint32_t delta_doc = postings[i].docid - prev_doc;
        prev_doc = postings[i].docid;
        x = delta_doc;
        do {
            uint8_t b = x & 0x7F;
            x >>= 7;
            if (x == 0) b |= 0x80;
            buf[pos++] = b;
        } while (x > 0);
        x = postings[i].tf;
        do {
            uint8_t b = x & 0x7F;
            x >>= 7;
            if (x == 0) b |= 0x80;
            buf[pos++] = b;
        } while (x > 0);
    }
    *out_len = pos;
    *out_buf = (uint8_t*)xrealloc(buf, pos);
}


struct TermEntry {
    char* term;
    uint32_t hash;
    Posting* postings;
    uint32_t df;
    uint32_t cap;
    TermEntry* next;
};

#ifndef TERM_HT_CAP
#define TERM_HT_CAP 500009u
#endif
static TermEntry* term_ht[TERM_HT_CAP];

static TermEntry* term_find_or_add(const char* term) {
    uint32_t h = fnv1a32(term);
    uint32_t b = h % TERM_HT_CAP;
    for (TermEntry* e = term_ht[b]; e; e = e->next) {
        if (e->hash == h && std::strcmp(e->term, term) == 0) return e;
    }
    TermEntry* e = (TermEntry*)xmalloc(sizeof(TermEntry));
    std::memset(e, 0, sizeof(*e));
    e->term = xstrdup(term);
    e->hash = h;
    e->cap = 4;
    e->postings = (Posting*)xmalloc(sizeof(Posting) * e->cap);
    e->df = 0;
    e->next = term_ht[b];
    term_ht[b] = e;
    return e;
}
static void term_add_docid(TermEntry* e, uint32_t docid) {
    if (e->df >= e->cap) {
        e->cap *= 2;
        e->postings = (Posting*)xrealloc(e->postings, sizeof(Posting) * e->cap);
    }
    e->postings[e->df].docid = docid;
    e->postings[e->df].tf = 1;
    e->df++;
}
static int cmp_u32(const void* a, const void* b) {
    uint32_t x = *(const uint32_t*)a, y = *(const uint32_t*)b;
    if (x < y) return -1;
    if (x > y) return 1;
    return 0;
}
static int cmp_posting(const void* a, const void* b) {
    uint32_t x = ((Posting*)a)->docid, y = ((Posting*)b)->docid;
    if (x < y) return -1;
    if (x > y) return 1;
    return 0;
}
static void finalize_postings(uint64_t* out_terms, uint64_t* out_term_chars) {
    uint64_t tc = 0, tchars = 0;
    for (uint32_t b = 0; b < TERM_HT_CAP; b++) {
        for (TermEntry* e = term_ht[b]; e; e = e->next) {
            tc++;
            tchars += (uint64_t)std::strlen(e->term);
            if (e->df == 0) continue;
            std::qsort(e->postings, e->df, sizeof(Posting), cmp_posting);
            uint32_t w = 1;
            for (uint32_t i = 1; i < e->df; i++) {
                if (e->postings[i].docid == e->postings[w - 1].docid) {
                    e->postings[w - 1].tf += e->postings[i].tf;
                } else {
                    e->postings[w] = e->postings[i];
                    w++;
                }
            }
            e->df = w;
        }
    }
    if (out_terms) *out_terms = tc;
    if (out_term_chars) *out_term_chars = tchars;
}
struct TermPtr { TermEntry* e; uint64_t postings_off; };
static int cmp_termptr_lex(const void* a, const void* b) {
    const TermPtr* x = (const TermPtr*)a;
    const TermPtr* y = (const TermPtr*)b;
    return std::strcmp(x->e->term, y->e->term);
}
static TermPtr* collect_terms(uint32_t* out_n) {
    uint32_t n = 0;
    for (uint32_t b = 0; b < TERM_HT_CAP; b++)
        for (TermEntry* e = term_ht[b]; e; e = e->next) n++;
    TermPtr* arr = (TermPtr*)xmalloc(sizeof(TermPtr) * (size_t)n);
    uint32_t k = 0;
    for (uint32_t b = 0; b < TERM_HT_CAP; b++)
        for (TermEntry* e = term_ht[b]; e; e = e->next) { arr[k].e = e; arr[k].postings_off = 0; k++; }
    *out_n = n;
    std::qsort(arr, n, sizeof(TermPtr), cmp_termptr_lex);
    return arr;
}


static char* extract_title_from_json(const unsigned char* buf, size_t n) {
    if (!buf || n == 0) return NULL;
    const char* s = (const char*)buf;
    const char* key = "\"title\"";
    const char* p = std::strstr(s, key);
    if (!p) return NULL;
    p += std::strlen(key);
    while (*p && (*p==' '||*p=='\t'||*p=='\r'||*p=='\n'||*p==':')) p++;
    if (*p != '"') return NULL;
    p++;
    const char* start = p;
    while (*p) {
        if (*p == '\\' && p[1]) { p += 2; continue; }
        if (*p == '"') break;
        p++;
    }
    if (*p != '"') return NULL;
    size_t len = (size_t)(p - start);
    char* out = (char*)xmalloc(len + 1);
    std::memcpy(out, start, len);
    out[len] = 0;
    return out;
}

static char* extract_title_from_text(const unsigned char* buf, size_t n, size_t maxlen) {
    if (!buf || n == 0) return xstrdup("");
    size_t i = 0;
   
    while (i < n && (buf[i] == '\r' || buf[i] == '\n' || buf[i] == ' ' || buf[i] == '\t')) i++;
    size_t start = i;
    while (i < n && buf[i] != '\r' && buf[i] != '\n') i++;
    size_t len = (i > start) ? (i - start) : 0;
    if (len > maxlen) len = maxlen;
    char* out = (char*)xmalloc(len + 1);
    std::memcpy(out, buf + start, len);
    out[len] = 0;
    return out;
}


static void tokenize_and_index(const unsigned char* s, size_t n,
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
                if ((int)std::strlen(tok) >= min_len) {
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
        if ((int)std::strlen(tok) >= min_len) {
            TermEntry* e = term_find_or_add(tok);
            term_add_docid(e, docid);
            if (io_tokens_total) (*io_tokens_total)++;
            if (io_token_chars_total) (*io_token_chars_total) += (uint64_t)tlen_chars;
            tok_count++;
        }
    }
    if (io_doc_len) *io_doc_len = tok_count;
}



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

static int write_inverted(const char* path, TermPtr* terms, uint32_t term_count, uint32_t doc_count) {
    FILE* f = std::fopen(path, "wb");
    if (!f) { std::fprintf(stderr, "ERROR: cannot write %s\n", path); return 0; }

    InvHeader hdr;
    std::memset(&hdr, 0, sizeof(hdr));
    hdr.magic[0]='I'; hdr.magic[1]='N'; hdr.magic[2]='V'; hdr.magic[3]='1';
    hdr.version = 2;
    hdr.term_count = term_count;
    hdr.doc_count = doc_count;

    std::fwrite(&hdr, sizeof(hdr), 1, f);

    hdr.postings_off = (uint64_t)std::ftell(f);

    uint64_t total_uncomp = 0, total_comp = 0;

    for (uint32_t i = 0; i < term_count; i++) {
        terms[i].postings_off = (uint64_t)std::ftell(f);
        TermEntry* e = terms[i].e;
        if (e->df == 0) {
            write_u32(f, 0); 
            write_u32(f, 0); 
        } else {
            uint8_t* cbuf;
            size_t clen;
            encode_delta_vbyte(e->postings, e->df, &cbuf, &clen);
            write_u32(f, e->df);
            write_u32(f, (uint32_t)clen);
            std::fwrite(cbuf, 1, clen, f);
            std::free(cbuf);
            total_uncomp += (uint64_t)e->df * 8;
            total_comp += clen;
        }
    }

    std::fprintf(stderr, "Postings uncompressed: %llu bytes\n", total_uncomp);
    std::fprintf(stderr, "Postings compressed: %llu bytes\n", total_comp);
    std::fprintf(stderr, "Compression ratio: %.2f\n", total_uncomp > 0 ? (double)total_comp / total_uncomp : 0);

    hdr.dict_off = (uint64_t)std::ftell(f);

    
    for (uint32_t i = 0; i < term_count; i++) {
        TermEntry* e = terms[i].e;
        uint16_t tlen = clamp_u16(std::strlen(e->term));
        write_u16(f, tlen);
        std::fwrite(e->term, 1, tlen, f);
        write_u32(f, e->df);
        write_u64(f, terms[i].postings_off);
    }

    std::fflush(f);
    std::fseek(f, 0, SEEK_SET);
    std::fwrite(&hdr, sizeof(hdr), 1, f);
    std::fclose(f);
    return 1;
}


static void usage() {
    std::fprintf(stderr,
        "Usage:\n"
        "  build_index --manifest <manifest_fixed.csv> --outdir <dir> [--root <root>]\n"
        "             [--yo2e 0|1] [--keepnumbers 0|1] [--minlen N] [--maxdocbytes N]\n"
    );
}

int main(int argc, char** argv) {
    const char* manifest = NULL;
    const char* outdir = "index";
    const char* root = ".";
    int yo2e = 1;
    int keep_numbers = 0;
    int min_len = 2;
    size_t max_doc_bytes = 0;

    for (int i = 1; i < argc; i++) {
        if (std::strcmp(argv[i], "--manifest") == 0 && i + 1 < argc) manifest = argv[++i];
        else if (std::strcmp(argv[i], "--outdir") == 0 && i + 1 < argc) outdir = argv[++i];
        else if (std::strcmp(argv[i], "--root") == 0 && i + 1 < argc) root = argv[++i];
        else if (std::strcmp(argv[i], "--yo2e") == 0 && i + 1 < argc) yo2e = std::atoi(argv[++i]);
        else if (std::strcmp(argv[i], "--keepnumbers") == 0 && i + 1 < argc) keep_numbers = std::atoi(argv[++i]);
        else if (std::strcmp(argv[i], "--minlen") == 0 && i + 1 < argc) min_len = std::atoi(argv[++i]);
        else if (std::strcmp(argv[i], "--maxdocbytes") == 0 && i + 1 < argc) max_doc_bytes = (size_t)std::strtoull(argv[++i], NULL, 10);
        else { usage(); return 1; }
    }
    if (!manifest) { usage(); return 1; }

    FILE* mf = std::fopen(manifest, "rb");
    if (!mf) { std::fprintf(stderr, "ERROR: cannot open manifest %s\n", manifest); return 1; }

    char line[1 << 16];
    if (!std::fgets(line, (int)sizeof(line), mf)) {
        std::fprintf(stderr, "ERROR: empty manifest\n");
        std::fclose(mf);
        return 1;
    }

   
    int col_docid   = csv_find_col(line, "doc_id");
    int col_url     = csv_find_col(line, "final_url");
    int col_text    = csv_find_col(line, "text_path");
    int col_meta    = csv_find_col(line, "meta_path");

    if (col_docid < 0 || col_url < 0 || col_text < 0) {
        std::fprintf(stderr, "ERROR: manifest header must have doc_id, final_url, text_path\n");
        std::fprintf(stderr, "Header: %s\n", line);
        std::fclose(mf);
        return 1;
    }

    char inv_path[1024], fwd_path[1024];
#ifdef _WIN32
    std::snprintf(inv_path, sizeof(inv_path), "%s\\inv.bin", outdir);
    std::snprintf(fwd_path, sizeof(fwd_path), "%s\\fwd.bin", outdir);
#else
    std::snprintf(inv_path, sizeof(inv_path), "%s/inv.bin", outdir);
    std::snprintf(fwd_path, sizeof(fwd_path), "%s/fwd.bin", outdir);
#endif

    FILE* fwd = std::fopen(fwd_path, "wb");
    if (!fwd) { std::fprintf(stderr, "ERROR: cannot write %s (create folder?)\n", fwd_path); std::fclose(mf); return 1; }

    FwdHeader fh;
    std::memset(&fh, 0, sizeof(fh));
    fh.magic[0]='F'; fh.magic[1]='W'; fh.magic[2]='D'; fh.magic[3]='1';
    fh.version = 1;
    std::fwrite(&fh, sizeof(fh), 1, fwd); 

    uint64_t* offsets = NULL;
    uint32_t offsets_cap = 0;
    uint32_t min_docid_seen = 0, max_docid_seen = 0;

    uint64_t docs = 0;
    uint64_t tokens_total = 0;
    uint64_t token_chars_total = 0;

    char docid_s[64], url_s[2048], textpath_s[1024], metapath_s[1024];
    std::clock_t t0 = std::clock();

    while (std::fgets(line, (int)sizeof(line), mf)) {
        docid_s[0]=0; url_s[0]=0; textpath_s[0]=0; metapath_s[0]=0;

        if (!csv_get_field(line, col_docid, docid_s, (int)sizeof(docid_s))) continue;
        if (!csv_get_field(line, col_url, url_s, (int)sizeof(url_s))) continue;
        if (!csv_get_field(line, col_text, textpath_s, (int)sizeof(textpath_s))) continue;
        if (col_meta >= 0) csv_get_field(line, col_meta, metapath_s, (int)sizeof(metapath_s));

        if (!docid_s[0] || !url_s[0] || !textpath_s[0]) continue;
        uint32_t docid = (uint32_t)std::strtoul(docid_s, NULL, 10);
        if (docid == 0) continue;

        char full_textpath[2048];
        join_path(full_textpath, (int)sizeof(full_textpath), root, textpath_s);

        size_t ntext = 0;
        unsigned char* text = read_file(full_textpath, &ntext, max_doc_bytes);
        if (!text || ntext == 0) { if (text) std::free(text); continue; }

        if (docs == 0) { min_docid_seen = docid; max_docid_seen = docid; }
        if (docid < min_docid_seen) min_docid_seen = docid;
        if (docid > max_docid_seen) max_docid_seen = docid;

        if (offsets_cap == 0) {
            offsets_cap = max_docid_seen + 1;
            offsets = (uint64_t*)xmalloc(sizeof(uint64_t) * (size_t)offsets_cap);
            std::memset(offsets, 0, sizeof(uint64_t) * (size_t)offsets_cap);
        } else if (max_docid_seen + 1 > offsets_cap) {
            uint32_t newcap = offsets_cap;
            while (newcap < max_docid_seen + 1) newcap *= 2;
            offsets = (uint64_t*)xrealloc(offsets, sizeof(uint64_t) * (size_t)newcap);
            std::memset(offsets + offsets_cap, 0, sizeof(uint64_t) * (size_t)(newcap - offsets_cap));
            offsets_cap = newcap;
        }

       
        char* title = NULL;
        if (metapath_s[0]) {
            char full_metapath[2048];
            join_path(full_metapath, (int)sizeof(full_metapath), root, metapath_s);
            size_t nm = 0;
            unsigned char* mbuf = read_file(full_metapath, &nm, 0);
            if (mbuf) { title = extract_title_from_json(mbuf, nm); std::free(mbuf); }
        }
        if (!title) title = extract_title_from_text(text, ntext, 200);

        uint64_t doc_len = 0;
        tokenize_and_index(text, ntext, docid, keep_numbers, yo2e, min_len, &tokens_total, &token_chars_total, &doc_len);
        std::free(text);

        uint64_t rec_off = (uint64_t)std::ftell(fwd);
        offsets[docid] = rec_off;

        write_u32(fwd, docid);

        uint16_t url_len = clamp_u16(std::strlen(url_s));
        write_u16(fwd, url_len);
        std::fwrite(url_s, 1, url_len, fwd);

        uint16_t title_len = clamp_u16(std::strlen(title));
        write_u16(fwd, title_len);
        std::fwrite(title, 1, title_len, fwd);

        write_u32(fwd, (uint32_t)doc_len);

        std::free(title);

        docs++;
        if ((docs % 1000u) == 0u) std::fprintf(stderr, "Processed docs: %llu\n", (unsigned long long)docs);
    }

    std::fclose(mf);

   
    uint64_t uniq_terms = 0, term_chars = 0;
    finalize_postings(&uniq_terms, &term_chars);

   
    fh.doc_count = (uint32_t)docs;
    fh.min_docid = min_docid_seen;
    fh.max_docid = max_docid_seen;
    fh.offsets_off = (uint64_t)std::ftell(fwd);

    for (uint32_t d = fh.min_docid; d <= fh.max_docid; d++) {
        uint64_t off = (d < offsets_cap) ? offsets[d] : 0;
        write_u64(fwd, off);
        if (d == 0xFFFFFFFFu) break;
    }

    std::fflush(fwd);
    std::fseek(fwd, 0, SEEK_SET);
    std::fwrite(&fh, sizeof(fh), 1, fwd);
    std::fclose(fwd);
    if (offsets) std::free(offsets);

  
    uint32_t term_count_u32 = 0;
    TermPtr* terms = collect_terms(&term_count_u32);
    if (!write_inverted(inv_path, terms, term_count_u32, (uint32_t)docs)) {
        std::fprintf(stderr, "ERROR: failed to write inverted index\n");
        std::free(terms);
        return 2;
    }
    std::free(terms);

    std::clock_t t1 = std::clock();
    double sec = (double)(t1 - t0) / (double)CLOCKS_PER_SEC;
    double avg_token_len = (tokens_total > 0) ? ((double)token_chars_total / (double)tokens_total) : 0.0;
    double avg_term_len  = (uniq_terms > 0) ? ((double)term_chars / (double)uniq_terms) : 0.0;

    std::fprintf(stderr, "DONE\n");
    std::fprintf(stderr, "Docs: %llu\n", (unsigned long long)docs);
    std::fprintf(stderr, "Unique terms: %llu\n", (unsigned long long)uniq_terms);
    std::fprintf(stderr, "Tokens total: %llu\n", (unsigned long long)tokens_total);
    std::fprintf(stderr, "Avg token length (chars): %.3f\n", avg_token_len);
    std::fprintf(stderr, "Avg term length (chars): %.3f\n", avg_term_len);
    std::fprintf(stderr, "Indexing time (sec): %.3f\n", sec);
    if (docs > 0) std::fprintf(stderr, "Time per doc (ms): %.3f\n", (sec * 1000.0) / (double)docs);
    std::fprintf(stderr, "Wrote: %s\n", fwd_path);
    std::fprintf(stderr, "Wrote: %s\n", inv_path);
    return 0;
}
