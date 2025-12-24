#define _CRT_SECURE_NO_WARNINGS
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <time.h>

#ifndef HASH_CAP
#define HASH_CAP 500009
#endif

typedef struct Entry {
    char* key;
    uint32_t val;
    struct Entry* next;
} Entry;

static Entry* ht[HASH_CAP];

static void* xmalloc(size_t n) {
    void* p = malloc(n);
    if (!p) { fprintf(stderr, "OOM\n"); exit(2); }
    return p;
}

static char* xstrdup(const char* s) {
    size_t n = strlen(s);
    char* p = (char*)xmalloc(n + 1);
    memcpy(p, s, n + 1);
    return p;
}

static uint32_t hstr(const char* s) {
    uint32_t h = 2166136261u;
    for (; *s; s++) { h ^= (unsigned char)(*s); h *= 16777619u; }
    return h;
}

static void ht_add(const char* key) {
    uint32_t h = hstr(key) % HASH_CAP;
    Entry* e = ht[h];
    while (e) {
        if (strcmp(e->key, key) == 0) { e->val++; return; }
        e = e->next;
    }
    e = (Entry*)xmalloc(sizeof(Entry));
    e->key = xstrdup(key);
    e->val = 1;
    e->next = ht[h];
    ht[h] = e;
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

static int is_hyphen(uint32_t cp) {
    return cp == '-' || cp == 0x2010 || cp == 0x2011 || cp == 0x2012 || cp == 0x2013 || cp == 0x2014;
}

static unsigned char* read_file(const char* path, size_t* out_n, size_t limit_bytes) {
    FILE* f = fopen(path, "rb");
    if (!f) return NULL;
    fseek(f, 0, SEEK_END);
    long sz = ftell(f);
    fseek(f, 0, SEEK_SET);
    if (sz < 0) { fclose(f); return NULL; }
    if (limit_bytes > 0 && (size_t)sz > limit_bytes) { fclose(f); return NULL; }
    unsigned char* buf = (unsigned char*)xmalloc((size_t)sz + 1);
    size_t rd = fread(buf, 1, (size_t)sz, f);
    fclose(f);
    buf[rd] = 0;
    *out_n = rd;
    return buf;
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

static void tokenize_bytes(const unsigned char* s, size_t n, int keep_numbers, int yo2e, int min_len,
                           uint64_t* tokens_total, uint64_t* token_chars_total) {
    char tok[512];
    int tlen_bytes = 0;
    int tlen_chars = 0;

    size_t i = 0;
    while (1) {
        uint32_t cp = 0;
        size_t prev_i = i;
        if (!utf8_read(s, n, &i, &cp)) break;

        cp = to_lower_ru(cp);
        if (yo2e) cp = yo_to_e(cp);

        int is_word = is_latin(cp) || is_cyrillic_ru(cp) || (keep_numbers && is_digit(cp));

        if (is_word) {
            char tmp[4];
            int w = utf8_write(tmp, cp);
            if (tlen_bytes + w < (int)sizeof(tok) - 1) {
                memcpy(tok + tlen_bytes, tmp, (size_t)w);
                tlen_bytes += w;
                tlen_chars += 1;
            }
            continue;
        }

       
        if (is_hyphen(cp) && tlen_chars > 0) {
            size_t k = i;
            uint32_t next = 0;
            if (utf8_read(s, n, &k, &next)) {
                next = to_lower_ru(next);
                if (yo2e) next = yo_to_e(next);
                int next_word = is_latin(next) || is_cyrillic_ru(next) || (keep_numbers && is_digit(next));
                if (next_word) {
                    if (tlen_bytes + 1 < (int)sizeof(tok) - 1) {
                        tok[tlen_bytes++] = '-';
                        tlen_chars += 1;
                    }
                    continue;
                }
            }
        }

        if (tlen_chars >= min_len) {
            tok[tlen_bytes] = 0;
            ht_add(tok);
            (*tokens_total)++;
            (*token_chars_total) += (uint64_t)tlen_chars;
        }
        tlen_bytes = 0;
        tlen_chars = 0;

        (void)prev_i;
    }

    if (tlen_chars >= min_len) {
        tok[tlen_bytes] = 0;
        ht_add(tok);
        (*tokens_total)++;
        (*token_chars_total) += (uint64_t)tlen_chars;
    }
}

static int ensure_dir(const char* path) {
    char cmd[512];
    snprintf(cmd, sizeof(cmd), "mkdir \"%s\" >NUL 2>NUL", path);
    return system(cmd);
}

typedef struct Pair {
    char* term;
    unsigned freq;
} Pair;

static int cmp_pair(const void* a, const void* b) {
    const Pair* x = (const Pair*)a;
    const Pair* y = (const Pair*)b;
    if (x->freq != y->freq) return (y->freq > x->freq) ? 1 : -1;
    return strcmp(x->term, y->term);
}


int main(int argc, char** argv) {
    const char* manifest = "data\\manifest_fixed.csv";
    const char* out_dir = "out";
    int limit_docs = -1;
    size_t limit_file_bytes = (size_t)-1; 
    int keep_numbers = 1;
    int yo2e = 1;
    int min_len = 2;

    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--manifest") == 0 && i + 1 < argc) manifest = argv[++i];
        else if (strcmp(argv[i], "--out") == 0 && i + 1 < argc) out_dir = argv[++i];
        else if (strcmp(argv[i], "--limit-docs") == 0 && i + 1 < argc) limit_docs = atoi(argv[++i]);
        else if (strcmp(argv[i], "--limit-file-bytes") == 0 && i + 1 < argc) limit_file_bytes = (size_t)_strtoui64(argv[++i], NULL, 10);
        else if (strcmp(argv[i], "--keep-numbers") == 0 && i + 1 < argc) keep_numbers = atoi(argv[++i]) != 0;
        else if (strcmp(argv[i], "--yo-to-e") == 0 && i + 1 < argc) yo2e = atoi(argv[++i]) != 0;
        else if (strcmp(argv[i], "--min-len") == 0 && i + 1 < argc) min_len = atoi(argv[++i]);
    }

    ensure_dir(out_dir);

    clock_t t0 = clock();

    FILE* f = fopen(manifest, "rb");
    if (!f) { fprintf(stderr, "Cannot open manifest: %s\n", manifest); return 1; }

    char line[8192];
    if (!fgets(line, sizeof(line), f)) { fclose(f); return 1; } 

    uint64_t docs = 0;
    uint64_t tokens_total = 0;
    uint64_t token_chars_total = 0;
    uint64_t bytes_in = 0;

    const int COL_TEXT_PATH = 10;

    while (fgets(line, sizeof(line), f)) {
        if (limit_docs >= 0 && (int)docs >= limit_docs) break;

        char text_path[1024];
        if (!csv_get_field(line, COL_TEXT_PATH, text_path, (int)sizeof(text_path))) {
            fprintf(stderr, "bad csv line\n");
            continue;
        }
        if (text_path[0] == 0) {
            fprintf(stderr, "empty text_path\n");
            continue;
        }

        size_t n = 0;
        unsigned char* buf = read_file(text_path, &n, limit_file_bytes);
        if (!buf) {
            fprintf(stderr, "cant read: %s\n", text_path);
            continue;
        }

        bytes_in += (uint64_t)n;
        tokenize_bytes(buf, n, keep_numbers, yo2e, min_len, &tokens_total, &token_chars_total);

        free(buf);
        docs++;
        if (docs % 1000 == 0) fprintf(stderr, "Processed docs: %llu\n", (unsigned long long)docs);
    }
    fclose(f);

    char tf_path[512];
    snprintf(tf_path, sizeof(tf_path), "%s\\term_freq.csv", out_dir);
    FILE* out = fopen(tf_path, "wb");
    if (!out) { fprintf(stderr, "Cannot write: %s\n", tf_path); return 1; }
    fprintf(out, "term,freq\n");
    uint64_t uniq = 0;
    uint32_t f1 = 0;

    typedef struct { char* term; uint32_t freq; } Pair;
    Pair* arr = NULL;
    size_t arr_cap = 0, arr_n = 0;

    for (size_t b = 0; b < HASH_CAP; b++) {
        for (Entry* e = ht[b]; e; e = e->next) {
            if (arr_n == arr_cap) {
                arr_cap = arr_cap ? arr_cap * 2 : 65536;
                arr = (Pair*)realloc(arr, arr_cap * sizeof(Pair));
                if (!arr) { fprintf(stderr, "OOM\n"); exit(2); }
            }
            arr[arr_n].term = e->key;
            arr[arr_n].freq = e->val;
            arr_n++;
            uniq++;
            fprintf(out, "\"%s\",%u\n", e->key, e->val);
        }
    }
    fclose(out);

    qsort(arr, arr_n, sizeof(Pair), cmp_pair);
    if (arr_n > 0) f1 = arr[0].freq;

    char z_path[512];
    snprintf(z_path, sizeof(z_path), "%s\\zipf.csv", out_dir);
    FILE* zout = fopen(z_path, "wb");
    if (zout) {
        fprintf(zout, "rank,freq,zipf_pred\n");
        for (size_t r = 0; r < arr_n; r++) {
            size_t rank = r + 1;
            double pred = (rank > 0) ? ((double)f1 / (double)rank) : 0.0;
            fprintf(zout, "%llu,%u,%.6f\n", (unsigned long long)rank, arr[r].freq, pred);
        }
        fclose(zout);
    }

    clock_t t1 = clock();
    double elapsed_sec = (double)(t1 - t0) / (double)CLOCKS_PER_SEC;

    double avg_token_len = tokens_total
        ? (double)token_chars_total / (double)tokens_total
        : 0.0;

    double kb_in = (double)bytes_in / 1024.0;
    double kb_per_sec = elapsed_sec > 0.0 ? kb_in / elapsed_sec : 0.0;

    fprintf(stderr, "DONE\n");
    fprintf(stderr, "docs=%llu\n", (unsigned long long)docs);
    fprintf(stderr, "tokens=%llu\n", (unsigned long long)tokens_total);
    fprintf(stderr, "unique_terms=%llu\n", (unsigned long long)uniq);
    fprintf(stderr, "avg_token_len=%.3f\n", avg_token_len);
    fprintf(stderr, "bytes_in=%llu\n", (unsigned long long)bytes_in);
    fprintf(stderr, "time_sec=%.3f\n", elapsed_sec);
    fprintf(stderr, "KB_per_sec=%.2f\n", kb_per_sec);
    fprintf(stderr, "term_freq_file=%s\n", tf_path);
    fprintf(stderr, "zipf_file=%s\n", z_path);

    free(arr);
    return 0;
}
