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
static void* xrealloc(void* p, size_t n) {
    void* q = std::realloc(p, n);
    if (!q) { std::fprintf(stderr, "OOM\n"); std::exit(2); }
    return q;
}

struct Posting {
    uint32_t docid;
    uint32_t tf;
};

void encode_delta_vbyte(const Posting* postings, uint32_t n, uint8_t** out_buf, size_t* out_len) {
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

Posting* decode_delta_vbyte_postings(const uint8_t* buf, size_t len, uint32_t n) {
    Posting* postings = (Posting*)xmalloc(sizeof(Posting) * (size_t)n);
    size_t pos = 0;
    uint32_t idx = 0;
    while (idx < n && pos < len) {
        uint32_t x = 0;
        int shift = 0;
       
        while (pos < len) {
            uint8_t b = buf[pos++];
            x |= (uint32_t)(b & 0x7F) << shift;
            if (b & 0x80) break;
            shift += 7;
            if (shift >= 32) break;
        }
        if (idx == 0) {
            postings[0].docid = x;
        } else {
            postings[idx].docid = postings[idx - 1].docid + x;
        }
        
       
        x = 0;
        shift = 0;
        while (pos < len) {
            uint8_t b = buf[pos++];
            x |= (uint32_t)(b & 0x7F) << shift;
            if (b & 0x80) break;
            shift += 7;
            if (shift >= 32) break;
        }
        postings[idx].tf = x;
        idx++;
    }
    return postings;
}

int main() {

    Posting p1 = {1, 2};
    uint8_t* buf;
    size_t len;
    encode_delta_vbyte(&p1, 1, &buf, &len);
    assert(len > 0);
    assert(buf != NULL);

    Posting* decoded = decode_delta_vbyte_postings(buf, len, 1);
    assert(decoded[0].docid == 1);
    assert(decoded[0].tf == 2);
    std::free(buf);
    std::free(decoded);

    Posting p2[] = {{1, 1}, {3, 2}, {5, 1}};
    encode_delta_vbyte(p2, 3, &buf, &len);
    assert(len > 0);

    decoded = decode_delta_vbyte_postings(buf, len, 3);
    assert(decoded[0].docid == 1 && decoded[0].tf == 1);
    assert(decoded[1].docid == 3 && decoded[1].tf == 2);
    assert(decoded[2].docid == 5 && decoded[2].tf == 1);
    std::free(buf);
    std::free(decoded);

    encode_delta_vbyte(NULL, 0, &buf, &len);
    assert(len == 0);
    assert(buf == NULL);

    std::cout << "All compression tests passed!" << std::endl;
    return 0;
}