/*
 * m3og: the helper library of the A7 III (ILCE-7M3, firmware 4.04) open-gate test kit 2 (a7m3_map, design og_m3_v2).
 *
 * How it runs: the kit writes this file to /tmp/jiritsu/libJit.so with the service file-write command; libJiritsu.so's
 * adj_cmd_set_file2 then loads it with dlopen (a7m3_map M3-F011), which runs the constructor below once inside the
 * service process; the firmware calls dlclose and the kit deletes the file again. The kit sends Jiritsu MOUNT first
 * (M3-F030). Built once per level (build_m3og.sh):
 *
 *   level 1   DUMP, read-only. /proc and /sys facts, the kernel log, where av-cam sits in memory (checked against the 4.04
 *             file), what each block of the design holds now, copies of the sensor and front-end tables, and (v3)
 *             the camera's application log and the state of its output-sync refresh loop.
 *   level 11  TEST 1. Writes the seven sensor bytes of og_m3_v1 into the IMX410 register list (column 14 = drives 0x1f
 *             and 0x89, 4K 24p/25p full frame): the sensor reads 4036 rows from row 61 instead of 3412 from row 373.
 *   level 21  TEST 2. Test 1 plus both front-end records of those drives (heights +624, vertical step 6888) and, new
 *             in v3, the camera-core timing pair of the drive (line count 2030 for the 4050-line head, cycle 726 /
 *             696): the whole sensor height, squeezed into the stock 4K frame. v2's test 2 left the timing pair at
 *             the stock 3436 lines; the camera lost its output sync and restarted itself (M3-F039..F041).
 *   level 22  TEST 3. The same three parts for half the extra height (3724 rows from row 217, heights +312).
 *   level 23  TEST 4. The same for a quarter (3568 rows from row 295, heights +156): the smallest change of line rate.
 *   level 24  TEST 5 (v7). Test 3's bytes (92 more rows, stock line period) plus the size row's inner height in three more
 *             blocks of the TV-system slot: the ROM size row, the runtime entry and the runtime read-out row the
 *             firmware derives from it. Two clips showed the valid picture ending at the stock last sensor row
 *             (M3-F046); this tests whether the size row is what sets that row.
 *   level 25  TEST 6 (v8). Test 3 with the first sensor row moved up by the whole 92 rows (row 281, not 327). Tests whether
 *             the valid picture ends at a fixed sensor row (M3-F048): if so, this frame is whole.
 *   level 26  TEST 7 (v9). Test 3 with the line-pair count of the timing pair raised by twice as much (1810; the period
 *             shortens to 815 / 781 to keep the blank). Whole frame if a stale stock count is added to ours.
 *   level 27  TEST 8 (v9). Test 3 with the sensor's row-count register raised by twice as much (3596 rows from row 327).
 *             Whole frame if a second sensor row count stays stock (M3-F049).
 *   level 28  TEST 9 (v10). Test 3 plus the front end's own register lists for the 4K full-frame drives (M3-F051): every
 *             line count + 92 in the receiver, link, image, output-format and transfer generators of both channels,
 *             the two frame totals derived from them, and the transfer generator's cycle. No earlier test wrote them.
 *   level 29  TEST 10 (v10). Test 9 plus the front end's drive table: its twelve height words + 92.
 *   level 30  TEST 11 (v11). Test 9 with the line period of the timing pair and of the front end's transfer generator
 *             shortened so that the taller frame ends when the stock one does (814 instead of 836 on the 59.94
 *             system; on the 50 system test 9 already holds that value, 801, and the two tests are the same bytes).
 *             With test 9 the frame ran out of time 64 lines before its end (M3-F056).
 *   level 51  TEST 12 (v12). Test 11 plus the front end's three frame-memory port entries at 3529 lines instead of 3437
 *             (two write ports, one read port). With tests 9 and 11 the output stage stopped at line 3437, the
 *             line count of those ports, and the rest of the frame was never written (M3-F058).
 *   level 52  TEST 13 (v12). Test 9 plus the same three entries: the stock line period on the 59.94 system.
 *             Tests 9 to 13 also set the no-restart bit (level 41) and the status-print bits (level 43) themselves.
 *   level 31  PUT BACK. Writes the 4.04 bytes back wherever a test changed them, and clears the switch bits below.
 *   level 41  NO RESTART (v4). Sets bit 0x40 of the firmware's own switch byte for its output-sync refresh loop: the loop
 *             keeps retrying but never forces the restart. One byte.
 *   level 42  NO CHECK (v4). Sets bit 0x02 of the same byte: the refresh loop does nothing at all. One byte.
 *             With tests 2 to 4 of v3 the picture came up, then the loop retried ten times and forced a restart
 *             (M3-F042). These two steps show how often it retries (the dump reads its counters) and whether the
 *             picture is good without it.
 *   level 43  FRONT-END LOG (v10). Sets four bits of one flag byte: the firmware's own status print for its front end
 *             (FUN_637a35bc) then writes the generators' cycles, counters and states to the camera's log each time the
 *             sensor's drive mode changes. The dump copies that log (below). One byte; put back clears it.
 *
 * v10, dump: the camera core's own log lines. av-cam's print function sends each line to the kernel's log module, which
 * keeps them in RAM (log buffer at 0x03085000, laid out from /setting/ulogio.bin): subsystem 3, area 1 = the latest
 * 8 KB, area 3 = the first 40 KB since the camera started. Both are copied as text if their headers are where the
 * layout says (M3-F054). v11: the header check of v10 required a word that changes while the camera runs and so
 * copied nothing (M3-F056); it now checks the marker, the start pointer and the size. The copy of the kernel's
 * application log (alog) is gone: it was 14 bytes on every camera, and the library has to fit one upload packet.
 *
 * Memory: av-cam.bin runs from RAM at physical = link address - 0x60000000 (kernel command line: klog at 0x035A5000,
 * size 0x20000; av-cam's LIRO image follows at 0x035C6000; the reservation 0x02E68000 + 0x1A5E000 ends where av-cam's
 * data ends). It is read and written with pread/pwrite on /dev/mem, the method the original A7S kits used on the
 * same platform family (A7s Claude a7s_poke). Confirmed on a camera by the first kit-2 run (M3-F038): the LIRO header
 * is at 0x035C6000 and liro's own parameter adr is 0x635C6000. Before anything else the LIRO header and two code ranges
 * must equal the 4.04 file, or nothing is written. If only the header matches, the dump still reads the tables.
 * v2: the first 64 KB of the image change while the camera runs. They are reported page by page and no longer required
 * (v1 required them and refused on every camera).
 *
 * A write level writes only bytes of its blocks (the register list, the two records, the front end's lists and drive
 * table, and the small timing and size blocks in the slot of the camera's TV system), only where the
 * 4.04 values and the target differ, only if every byte of every block holds the 4.04 byte or the target byte. Each
 * run of bytes is read back; on any mismatch every byte written is put back. A restart undoes everything: av-cam is
 * loaded again from the warm-boot image (seen after the forced restart of the second run, and after a battery pull).
 * The power switch alone does not reset RAM on this platform family.
 *
 * It writes ONE file: /tmp_network/m3og_result.txt (a RAM tmpfs in service mode), or if that cannot be created,
 * /tmp/jiritsu/m3og_result.txt. If either already exists it does nothing at all. No other file is written, no ioctl,
 * no mmap, no process, no library call (the library has no imports).
 */
typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned int u32;
typedef unsigned long long u64;

#ifndef LEVEL
#define LEVEL 1
#endif
#if LEVEL != 1 && LEVEL != 11 && !(LEVEL >= 21 && LEVEL <= 30) && LEVEL != 31 && LEVEL != 41 && LEVEL != 42 && LEVEL != 43 && LEVEL != 51 && LEVEL != 52
#error "LEVEL must be 1, 11, 21 to 30, 31, 41, 42, 43, 51 or 52"
#endif
#define GUARD_ONLY (LEVEL == 41 || LEVEL == 42 || LEVEL == 43)
/* v10: tests 9 to 13 also set the no-restart bit and the status-print bits themselves (one session instead of three) */
#define TEST_SETS_FLAGS (LEVEL == 28 || LEVEL == 29 || LEVEL == 30 || LEVEL == 51 || LEVEL == 52)
/* the test a level writes: test1 = 0, test2..test11 = 1..10 (levels 21..30), test12 and test13 = 11, 12 (levels 51, 52) */
#if LEVEL == 11
#define TEST_IDX 0
#elif LEVEL >= 21 && LEVEL <= 30
#define TEST_IDX (LEVEL - 20)
#elif LEVEL == 51 || LEVEL == 52
#define TEST_IDX (LEVEL - 40)
#endif
#define WRITES (LEVEL != 1)

struct ident { const char *name; u32 va; u32 len; u8 sha[32]; };
/* poff[n]: where in PATCHES the bytes of test n+1 that differ from stock start; npatch[n] triplets {offset low,
 * offset high, value} (v11: offsets into one table instead of a pointer each, to keep the library in one packet) */
struct block { const char *name; u32 va; u32 len; const u8 *stock; u16 poff[13]; u8 npatch[13]; };
struct range { const char *name; u32 va; u32 len; };
#include "m3og_design.h"

#define VERSION "m3og_v12"
#define KLOG_PHYS 0x035A5000u
#define KLOG_LEN 0x20000u
#define RESULT_CAP (900u * 1024u)        /* /tmp_network is a 1024 KB tmpfs: the log copies stop here */
#define FILE_CAP (64 * 1024)

/* ------------------------------------------------------------------ system calls (ARM EABI, ARM state) */

#define NR_read 3
#define NR_write 4
#define NR_open 5
#define NR_close 6
#define NR_getpid 20
#define NR_fsync 118
#define NR_pread64 180
#define NR_pwrite64 181
#define NR_geteuid32 201
#define NR_getdents64 217
#define O_RDONLY 0
#define O_WRONLY 1
#define O_RDWR 2
#define O_CREAT 0x40
#define O_EXCL 0x80
#define O_DIRECTORY 0x4000
#define EEXIST 17

static long sc6(long n, long a, long b, long c, long d, long e, long f)
{
    register long r0 __asm__("r0") = a;
    register long r1 __asm__("r1") = b;
    register long r2 __asm__("r2") = c;
    register long r3 __asm__("r3") = d;
    register long r4 __asm__("r4") = e;
    register long r5 __asm__("r5") = f;
    register long r7 __asm__("r7") = n;
    __asm__ volatile("svc 0" : "+r"(r0) : "r"(r1), "r"(r2), "r"(r3), "r"(r4), "r"(r5), "r"(r7) : "memory");
    return r0;
}
#define sc3(n, a, b, c) sc6((n), (long)(a), (long)(b), (long)(c), 0, 0, 0)

static int sys_open(const char *p, int flags, int mode) { return (int)sc3(NR_open, p, flags, mode); }
static long sys_read(int fd, void *b, u32 n) { return sc3(NR_read, fd, b, n); }
static long sys_write(int fd, const void *b, u32 n) { return sc3(NR_write, fd, b, n); }
static void sys_close(int fd) { sc3(NR_close, fd, 0, 0); }
/* EABI: the 64-bit offset goes in an even register pair (r4, r5); r3 is padding */
static long sys_pread(int fd, void *b, u32 n, u32 off) { return sc6(NR_pread64, fd, (long)b, n, 0, (long)off, 0); }
#if WRITES                                   /* the read-only dump build has no write call at all */
static long sys_pwrite(int fd, const void *b, u32 n, u32 off) { return sc6(NR_pwrite64, fd, (long)b, n, 0, (long)off, 0); }
#endif

/* ------------------------------------------------------------------ small library */

__attribute__((visibility("hidden"))) void *memcpy(void *d, const void *s, unsigned n)
{
    u8 *o = d;
    const u8 *i = s;
    while (n--) *o++ = *i++;
    return d;
}
__attribute__((visibility("hidden"))) void *memset(void *d, int v, unsigned n)
{
    u8 *o = d;
    while (n--) *o++ = (u8)v;
    return d;
}
static u32 slen(const char *s) { u32 n = 0; while (s[n]) n++; return n; }
static int same(const u8 *a, const u8 *b, u32 n) { for (u32 i = 0; i < n; i++) if (a[i] != b[i]) return 0; return 1; }

/* ------------------------------------------------------------------ the result file */

static int out_fd = -1;
static u32 out_total;
static char obuf[8192];
static u32 olen;

static void flush(void)
{
    u32 off = 0;
    while (off < olen) {
        long r = sys_write(out_fd, obuf + off, olen - off);
        if (r <= 0) break;
        off += (u32)r;
    }
    out_total += olen;
    olen = 0;
}
static void put(const char *s, u32 n)
{
    while (n) {
        u32 room = sizeof obuf - olen, k = n < room ? n : room;
        memcpy(obuf + olen, s, k);
        olen += k; s += k; n -= k;
        if (olen == sizeof obuf) flush();
    }
}
static void ps(const char *s) { put(s, slen(s)); }
static const char HEX[] = "0123456789abcdef";
static void phex(u32 v, int digits)
{
    char b[10];
    b[0] = '0'; b[1] = 'x';
    for (int i = 0; i < digits; i++) b[2 + i] = HEX[(v >> (4 * (digits - 1 - i))) & 15];
    put(b, 2 + digits);
}
static void px(u32 v) { phex(v, 8); }
static void pdec(u32 v)
{
    char b[10];
    int n = 0;
    do { b[n++] = (char)('0' + v % 10); v /= 10; } while (v);
    while (n) put(&b[--n], 1);
}
static void pbytes(const u8 *b, u32 n)
{
    char t[2];
    for (u32 i = 0; i < n; i++) { t[0] = HEX[b[i] >> 4]; t[1] = HEX[b[i] & 15]; put(t, 2); }
}
static void nl(void) { put("\n", 1); }

/* ------------------------------------------------------------------ SHA-256 */

static const u32 K256[64] = {
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5, 0xd807aa98, 0x12835b01,
    0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174, 0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc,
    0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da, 0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147,
    0x06ca6351, 0x14292967, 0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070, 0x19a4c116, 0x1e376c08,
    0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3, 0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208,
    0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2};
struct sha { u32 h[8]; u8 buf[64]; u32 n; u32 total; };
#define ROR(x, r) (((x) >> (r)) | ((x) << (32 - (r))))
static void sha_block(struct sha *s, const u8 *p)
{
    u32 w[64], a, b, c, d, e, f, g, h;
    for (int i = 0; i < 16; i++) w[i] = (u32)p[4 * i] << 24 | (u32)p[4 * i + 1] << 16 | (u32)p[4 * i + 2] << 8 | p[4 * i + 3];
    for (int i = 16; i < 64; i++) {
        u32 s0 = ROR(w[i - 15], 7) ^ ROR(w[i - 15], 18) ^ (w[i - 15] >> 3);
        u32 s1 = ROR(w[i - 2], 17) ^ ROR(w[i - 2], 19) ^ (w[i - 2] >> 10);
        w[i] = w[i - 16] + s0 + w[i - 7] + s1;
    }
    a = s->h[0]; b = s->h[1]; c = s->h[2]; d = s->h[3]; e = s->h[4]; f = s->h[5]; g = s->h[6]; h = s->h[7];
    for (int i = 0; i < 64; i++) {
        u32 t1 = h + (ROR(e, 6) ^ ROR(e, 11) ^ ROR(e, 25)) + ((e & f) ^ (~e & g)) + K256[i] + w[i];
        u32 t2 = (ROR(a, 2) ^ ROR(a, 13) ^ ROR(a, 22)) + ((a & b) ^ (a & c) ^ (b & c));
        h = g; g = f; f = e; e = d + t1; d = c; c = b; b = a; a = t1 + t2;
    }
    s->h[0] += a; s->h[1] += b; s->h[2] += c; s->h[3] += d; s->h[4] += e; s->h[5] += f; s->h[6] += g; s->h[7] += h;
}
static void sha_init(struct sha *s)
{
    static const u32 iv[8] = {0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19};
    for (int i = 0; i < 8; i++) s->h[i] = iv[i];
    s->n = 0; s->total = 0;
}
static void sha_add(struct sha *s, const u8 *p, u32 n)
{
    s->total += n;
    while (n) {
        u32 k = 64 - s->n;
        if (k > n) k = n;
        memcpy(s->buf + s->n, p, k);
        s->n += k; p += k; n -= k;
        if (s->n == 64) { sha_block(s, s->buf); s->n = 0; }
    }
}
static void sha_end(struct sha *s, u8 out[32])
{
    u32 bits = s->total << 3, hi = s->total >> 29;
    u8 pad = 0x80, z = 0;
    sha_add(s, &pad, 1);
    while (s->n != 56) sha_add(s, &z, 1);
    u8 len[8] = {(u8)(hi >> 24), (u8)(hi >> 16), (u8)(hi >> 8), (u8)hi, (u8)(bits >> 24), (u8)(bits >> 16), (u8)(bits >> 8), (u8)bits};
    sha_add(s, len, 8);
    for (int i = 0; i < 8; i++) { out[4 * i] = (u8)(s->h[i] >> 24); out[4 * i + 1] = (u8)(s->h[i] >> 16); out[4 * i + 2] = (u8)(s->h[i] >> 8); out[4 * i + 3] = (u8)s->h[i]; }
}

/* ------------------------------------------------------------------ reading files (dump) */

static u8 fbuf[FILE_CAP];

static void dump_file(const char *path)
{
    ps("== file "); ps(path); nl();
    int fd = sys_open(path, O_RDONLY, 0);
    if (fd < 0) { ps("!! open failed "); px((u32)fd); ps("\n== end 0 bytes\n"); return; }
    u32 got = 0;
    for (;;) {
        if (got == FILE_CAP) break;
        long r = sys_read(fd, fbuf + got, FILE_CAP - got);
        if (r <= 0) break;
        got += (u32)r;
    }
    sys_close(fd);
    /* /proc/cpuinfo on ARM can carry a "Serial" line: it is not copied */
    u32 i = 0;
    while (i < got) {
        u32 j = i;
        while (j < got && fbuf[j] != '\n') j++;
        if (j - i >= 6 && fbuf[i] == 'S' && fbuf[i + 1] == 'e' && fbuf[i + 2] == 'r' && fbuf[i + 3] == 'i' && fbuf[i + 4] == 'a' && fbuf[i + 5] == 'l')
            ps("Serial\t\t: (not copied by m3og)");
        else
            put((const char *)fbuf + i, j - i);
        if (j < got) nl();
        i = j + 1;
    }
    if (got && fbuf[got - 1] != '\n') nl();
    ps("== end "); px(got); ps(" bytes"); if (got == FILE_CAP) ps(" (cut at the cap)"); nl();
}

#if LEVEL == 1
struct dirent64 { u64 ino; u64 off; u16 reclen; u8 type; char name[1]; };

/* list a directory; with read_each, also copy each regular entry (small /sys parameter files) */
static void dump_dir(const char *path, int read_each)
{
    static u8 dbuf[4096];
    static char p2[160];
    ps("== dir "); ps(path); nl();
    int fd = sys_open(path, O_RDONLY | O_DIRECTORY, 0);
    if (fd < 0) { ps("!! open failed "); px((u32)fd); ps("\n== end\n"); return; }
    u32 count = 0;
    for (;;) {
        long n = sc3(NR_getdents64, fd, dbuf, sizeof dbuf);
        if (n <= 0) break;
        for (long o = 0; o < n;) {
            struct dirent64 *d = (struct dirent64 *)(dbuf + o);
            if (d->reclen == 0) break;
            o += d->reclen;
            if (d->name[0] == '.' && (d->name[1] == 0 || (d->name[1] == '.' && d->name[2] == 0))) continue;
            ps(d->name); ps(" type "); phex(d->type, 2); nl();
            if (++count > 256) break;
            if (read_each && d->type == 8) {
                u32 a = slen(path), b = slen(d->name);
                if (a + 1 + b + 1 < sizeof p2) {
                    memcpy(p2, path, a); p2[a] = '/'; memcpy(p2 + a + 1, d->name, b); p2[a + 1 + b] = 0;
                    int f = sys_open(p2, O_RDONLY, 0);
                    if (f >= 0) {
                        long r = sys_read(f, fbuf, 256);
                        sys_close(f);
                        ps("  = ");
                        if (r > 0) {
                            for (long k = 0; k < r; k++) if (fbuf[k] == '\n') fbuf[k] = ' ';
                            put((const char *)fbuf, (u32)r);
                        }
                        nl();
                    }
                }
            }
        }
        if (count > 256) break;
    }
    sys_close(fd);
    ps("== end\n");
}
#endif

/* ------------------------------------------------------------------ memory */

static int mem_fd = -1;
static int mem_rd(u32 phys, u8 *b, u32 n) { return sys_pread(mem_fd, b, n, phys) == (long)n; }
#if WRITES
static int mem_wr(u32 phys, const u8 *b, u32 n) { return sys_pwrite(mem_fd, b, n, phys) == (long)n; }
#endif

static u8 page[4096];

/* v2: the first 64 KB of the image hold data that changes while the camera runs (first kit-2 run, M3-F038): they are
 * hashed page by page and reported, never required. Up to four pages that differ are remembered for the dump. */
static u32 live_pages[4];
static int n_live;

static void image_pages(void)
{
    for (u32 k = 0; k < N_PAGES; k++) {
        struct sha s;
        u8 d[32];
        u32 va = PAGES_VA + 0x1000 * k;
        ps("page va "); px(va);
        if (!mem_rd(va - PHYS_DELTA, page, sizeof page)) { ps("  read failed (not required)\n"); continue; }
        sha_init(&s); sha_add(&s, page, sizeof page); sha_end(&s, d);
        ps(" sha256 "); pbytes(d, 32);
        if (same(d, PAGE_SHA[k], 32)) ps("  matches 4.04\n");
        else {
            ps("  differs from 4.04 (live data, not required)\n");
            if (n_live < 4) live_pages[n_live++] = va;
        }
    }
}

/* *loc: the LIRO header is where the kit expects it (av-cam's location is confirmed). Return: the location and every
 * required code range match the 4.04 file (writes are allowed only then). */
static int identity(int *loc)
{
    int ok = 1;
    u8 hdr[16];
    *loc = 0;
    ps("== identity\n");
    if (!mem_rd(AVCAM_PHYS, hdr, 16)) {
        ps("!! /dev/mem read at "); px(AVCAM_PHYS); ps(" failed\n");
        return 0;
    }
    ps("lirohdr phys "); px(AVCAM_PHYS); ps(" bytes "); pbytes(hdr, 16);
    if (same(hdr, LIROHDR, 16)) ps("  SAME as the 4.04 file\n"); else { ps("  DIFFERS from the 4.04 file\n"); ok = 0; }
    if (!ok) return 0;
    *loc = 1;
    for (int i = 0; i < N_IDENT; i++) {
        struct sha s;
        u8 d[32];
        sha_init(&s);
        int rd_ok = 1;
        for (u32 o = 0; o < IDENT[i].len; o += sizeof page) {
            u32 k = IDENT[i].len - o < sizeof page ? IDENT[i].len - o : sizeof page;
            if (!mem_rd(IDENT[i].va - PHYS_DELTA + o, page, k)) { rd_ok = 0; break; }
            sha_add(&s, page, k);
        }
        sha_end(&s, d);
        ps("range "); ps(IDENT[i].name); ps(" va "); px(IDENT[i].va); ps(" len "); px(IDENT[i].len);
        if (!rd_ok) { ps("  READ FAILED\n"); ok = 0; continue; }
        ps(" sha256 "); pbytes(d, 32);
        if (same(d, IDENT[i].sha, 32)) ps("  SAME as the 4.04 file\n"); else { ps("  DIFFERS from the 4.04 file\n"); ok = 0; }
    }
    image_pages();
    return ok;
}

/* v3: six blocks. Three are the same in every camera (register list, two front-end records); three hold the
 * camera-core timing pair of the 4K full-frame drive and sit in the slot of the camera's TV system (59.94: slot 28,
 * 50: slot 27). Until the system is known only the first three are read and nothing can be written. */
#define N_BLOCKS (N_COMMON + N_SYSBLK)
static const struct block *B[N_BLOCKS];
static int n_blk;
static int tv_sys = -1;
/* v10: the blocks' bytes sit one after another in a row of POOL_STEP bytes: one row for what the camera holds now and
 * one per test for its full bytes (built from stock + patch when a block is taken). */
static u32 boff[N_BLOCKS];
static u32 pool_used;
static u8 cur_pool[POOL_STEP];
static u8 tgt_pool[N_STEPS][POOL_STEP];
#define CUR(i) (cur_pool + boff[i])
#define TGT(n, i) (tgt_pool[n] + boff[i])
static u16 eq[N_BLOCKS];                /* bit 0: every byte is the stock byte; bit n: every byte is test n's byte */
#if N_STEPS != 13
#error "the state names below are for thirteen tests"
#endif
enum { ST_STOCK, ST_T1, ST_MIXED = ST_T1 + N_STEPS, ST_OTHER, ST_UNREAD };
static const char *const STATE_NAME[] = {"STOCK", "TEST1", "TEST2", "TEST3", "TEST4", "TEST5", "TEST6", "TEST7", "TEST8", "TEST9", "TEST10", "TEST11", "TEST12", "TEST13",
                                         "MIXED", "OTHER", "NOT READ"};

static void take_block(int i, const struct block *b)
{
    B[i] = b;
    boff[i] = pool_used;
    pool_used += b->len;                 /* the design's POOL_STEP is the sum of one system's block lengths */
    for (int n = 0; n < N_STEPS; n++) {
        memcpy(TGT(n, i), b->stock, b->len);
        for (u32 k = 0; k < b->npatch[n]; k++) {
            const u8 *p = PATCHES + b->poff[n] + 3 * k;
            TGT(n, i)[p[0] | (u32)p[1] << 8] = p[2];
        }
    }
}

/* The runtime drive table has a real row (HMAX 525) in the slot of the active TV system and a placeholder (1) in the
 * other one. */
static void pick_system(void)
{
    u8 a[4], b[4];
    for (int i = 0; i < N_COMMON; i++) take_block(i, &BLK_COMMON[i]);
    n_blk = N_COMMON;
    ps("== tv system\n");
    if (!mem_rd(T14_VA + 28 * T14_STRIDE + T14_HMAX_OFF - PHYS_DELTA, a, 4) ||
        !mem_rd(T14_VA + 27 * T14_STRIDE + T14_HMAX_OFF - PHYS_DELTA, b, 4)) { ps("tv system  READ FAILED\n"); return; }
    u32 h28 = a[0] | a[1] << 8 | a[2] << 16 | (u32)a[3] << 24, h27 = b[0] | b[1] << 8 | b[2] << 16 | (u32)b[3] << 24;
    ps("slot 28 hmax "); px(h28); ps(" slot 27 hmax "); px(h27);
    if (h28 == HMAX_4K && h27 == 1) tv_sys = 0;
    else if (h27 == HMAX_4K && h28 == 1) tv_sys = 1;
    if (tv_sys < 0) { ps("  tv system NOT RECOGNISED\n"); return; }
    ps(tv_sys == 0 ? "  tv system 59.94 (slot 28)\n" : "  tv system 50 (slot 27)\n");
    for (int i = 0; i < N_SYSBLK; i++) take_block(N_COMMON + i, &BLK_SYS[tv_sys][i]);
    n_blk = N_BLOCKS;
}

/* state of one block from its current bytes */
static int block_state(int i)
{
    const struct block *b = B[i];
    u32 ds = 0, d[N_STEPS], other = 0;
    for (int n = 0; n < N_STEPS; n++) d[n] = 0;
    for (u32 k = 0; k < b->len; k++) {
        u8 c = CUR(i)[k];
        int known = c == b->stock[k];
        if (!known) ds++;
        for (int n = 0; n < N_STEPS; n++) {
            if (c != TGT(n, i)[k]) d[n]++; else known = 1;
        }
        if (!known) other++;
    }
    int st = ST_MIXED;
    eq[i] = ds == 0;
    for (int n = N_STEPS - 1; n >= 0; n--) if (d[n] == 0) { eq[i] |= (u16)(2u << n); st = ST_T1 + n; }
    if (ds == 0) st = ST_STOCK;
    else if (st == ST_MIXED && other) st = ST_OTHER;
    ps("block "); ps(b->name); ps(" va "); px(b->va); ps(" len "); phex(b->len, 4);
    ps(" differs from stock "); phex(ds, 4);
    for (int n = 0; n < N_STEPS; n++) { ps(" from test"); pdec((u32)n + 1); ps(" "); phex(d[n], 4); }
    ps("  "); ps(STATE_NAME[st]); nl();
    if (other) {
        u32 shown = 0;
        for (u32 k = 0; k < b->len && shown < 16; k++) {
            u8 c = CUR(i)[k];
            int known = c == b->stock[k];
            for (int n = 0; n < N_STEPS; n++) known = known || c == TGT(n, i)[k];
            if (!known) {
                ps("  other at "); px(b->va + k); ps(" now "); phex(c, 2); ps(" stock "); phex(b->stock[k], 2); nl();
                shown++;
            }
        }
    }
    return st;
}

static int read_blocks(int st[N_BLOCKS])
{
    int ok = 1;
    ps("== blocks\n");
    for (int i = 0; i < N_BLOCKS; i++) { st[i] = ST_UNREAD; eq[i] = 0; }
    for (int i = 0; i < n_blk; i++) {
        if (!mem_rd(B[i]->va - PHYS_DELTA, CUR(i), B[i]->len)) {
            ps("block "); ps(B[i]->name); ps("  READ FAILED\n");
            ok = 0; continue;
        }
        st[i] = block_state(i);
    }
    return ok;
}

static void verdict(int idok, const int st[N_BLOCKS])
{
    ps("VERDICT ");
    if (!idok) { ps("NOT READY (av-cam is not where or what the 4.04 file says)\n"); return; }
    if (n_blk != N_BLOCKS) { ps("NOT READY (the TV system slot of the 4K drive was not recognised)\n"); return; }
    u32 all = (2u << N_STEPS) - 1;
    for (int i = 0; i < N_BLOCKS; i++) all &= st[i] == ST_UNREAD ? 0 : eq[i];
    if (all & 1) { ps("READY (stock)\n"); return; }
#ifdef TEST_IDX
    /* two tests can be the same bytes on one TV system (9 and 11 on the 50 system): a test level names its own */
    if (all & (2u << TEST_IDX)) { ps("READY (test "); pdec((u32)TEST_IDX + 1); ps(" applied)\n"); return; }
#endif
    for (int n = 0; n < N_STEPS; n++)
        if (all & (2u << n)) { ps("READY (test "); pdec((u32)n + 1); ps(" applied)\n"); return; }
    ps("NOT READY (the design's bytes are partly applied or changed by something else)\n");
}

/* v4: the firmware's own switches for its output-sync refresh loop. FUN_63935730 reads this byte every frame:
 * bit 0x02 = the loop does nothing; bit 0x40 = the loop never forces the restart. */
static void guard_show(void)
{
    u8 g;
    ps("GUARD ");
    if (!mem_rd(GUARD_VA - PHYS_DELTA, &g, 1)) { ps("NOT READ\n"); return; }
    ps("flag byte "); phex(g, 2);
    ps((g & GUARD_OFF) ? "  refresh loop OFF" : (g & GUARD_NOFORCE) ? "  refresh loop on, NO FORCED RESTART" : "  refresh loop STOCK");
    nl();
    /* v10: the flag byte of the firmware's front-end status print */
    ps("DFELOG ");
    if (!mem_rd(DFELOG_VA - PHYS_DELTA, &g, 1)) { ps("NOT READ\n"); return; }
    ps("flag byte "); phex(g, 2);
    ps((g & DFELOG_BITS) == DFELOG_BITS ? "  front-end status print ON" : (g & DFELOG_BITS) ? "  front-end status print PARTLY ON" : "  front-end status print off");
    nl();
}

#if LEVEL == 31 || GUARD_ONLY || TEST_SETS_FLAGS
/* sets and clears bits of one flag byte, leaving its other bits alone. Returns 1 if a byte was written and read
 * back, 0 if nothing had to change, 0xffffffff on a failure (the old byte is written back). */
static u32 flag_write(u32 va, u8 set, u8 clear)
{
    u8 g, w, back;
    if (!mem_rd(va - PHYS_DELTA, &g, 1)) return 0xffffffffu;
    w = (u8)((g | set) & (u8)~clear);
    if (w == g) return 0;
    if (!mem_wr(va - PHYS_DELTA, &w, 1) || !mem_rd(va - PHYS_DELTA, &back, 1) || back != w) {
        mem_wr(va - PHYS_DELTA, &g, 1);
        return 0xffffffffu;
    }
    return 1;
}
#endif

#if LEVEL == 1
static void dump_range(const char *name, u32 va, u32 len)
{
    ps("== mem "); ps(name); ps(" va "); px(va); ps(" phys "); px(va - PHYS_DELTA); ps(" len "); px(len); nl();
    for (u32 o = 0; o < len; o += 32) {
        u32 k = len - o < 32 ? len - o : 32;
        u8 b[32];
        if (!mem_rd(va - PHYS_DELTA + o, b, k)) { ps("!! read failed\n"); break; }
        px(va + o); ps(" "); pbytes(b, k); nl();
    }
    ps("== end\n");
}

static int hexd(u8 c) { return (c >= '0' && c <= '9') || (c >= 'a' && c <= 'f') || (c >= 'A' && c <= 'F'); }

/* A log ring as text: printable bytes as they are, zero bytes dropped, anything else as '.' (a run of them as one
 * '.' when squeeze is set), MAC-address-like patterns (hh:hh:hh:hh:hh:hh) blanked. Stops when the result file would
 * pass RESULT_CAP, so the closing lines of the result always fit. */
static void dump_log(const char *name, u32 phys, u32 len, int squeeze)
{
    ps("== "); ps(name); ps(" phys "); px(phys); ps(" len "); px(len); nl();
    u32 col = 0;
    int dot = 0, cut = 0;
    for (u32 o = 0; o < len && !cut; o += sizeof page) {
        u32 n = len - o < sizeof page ? len - o : sizeof page;
        if (!mem_rd(phys + o, page, n)) { ps("\n!! read failed\n"); break; }
        for (u32 k = 0; k + 17 <= n; k++) {
            int mac = 1;
            for (u32 j = 0; j < 17 && mac; j++) mac = (j % 3 == 2) ? page[k + j] == ':' : hexd(page[k + j]);
            if (mac) for (u32 j = 0; j < 17; j++) if (j % 3 != 2) page[k + j] = 'x';
        }
        for (u32 k = 0; k < n; k++) {
            u8 c = page[k];
            if (c == '\n') { nl(); col = 0; dot = 0; continue; }
            if (c == 0) continue;
            int printable = c >= 0x20 && c < 0x7f;
            if (!printable && squeeze && dot) continue;
            dot = !printable;
            char t = printable ? (char)c : '.';
            put(&t, 1);
            if (++col >= 200) { nl(); col = 0; }
        }
        if (out_total + olen > RESULT_CAP) cut = 1;
    }
    ps(cut ? "\n== cut (result size limit)\n" : "\n== end\n");
}

static u32 le32(const u8 *p) { return p[0] | (u32)p[1] << 8 | (u32)p[2] << 16 | (u32)p[3] << 24; }

/* v10: one area of the camera core's log (see the top of this file). The log module's area header is 0x24 bytes
 * (osal_ulogio.ko, ulogio_lbm_init). v11: on a camera it reads "RBUF", the address of the area's data as av-cam sees
 * it (physical + PHYS_DELTA) at +4, and the data size at +8; the word at +12 counts down as lines arrive (run 13). The
 * area is copied as text only if those three are what the layout says. */
static void dump_camlog(const char *name, u32 phys, u32 size)
{
    u8 h[0x24];
    ps("camlog area "); ps(name); ps(" phys "); px(phys); ps(" size "); px(size);
    if (!mem_rd(phys, h, sizeof h)) { ps("  HEADER NOT READ\n"); return; }
    ps(" header "); pbytes(h, sizeof h);
    if (le32(h) != 0x46554252u || le32(h + 4) != phys + 0x24 + PHYS_DELTA || le32(h + 8) != size - 0x24) { ps("  NOT AS EXPECTED, not copied\n"); return; }
    ps("  as expected, written up to "); px(le32(h + 20) - le32(h + 4)); nl();
    dump_log(name, phys + 0x24, size - 0x24, 1);
}

static void dump_camlogs(void)
{
    u8 h[12];
    ps("== camlog\n");
    ps("camlog subsystem phys "); px(ULOG_SUB_PHYS);
    if (!mem_rd(ULOG_SUB_PHYS, h, sizeof h)) { ps("  NOT READ\n"); return; }
    ps(" header "); pbytes(h, sizeof h);
    ps(le32(h + 4) == 3 && le32(h + 8) == ULOG_SUB_TOTAL ? "  as expected\n" : "  NOT AS EXPECTED\n");
    dump_camlog("camlog_first", CAMLOG_FIRST_PHYS, CAMLOG_FIRST_SIZE);
    dump_camlog("camlog_last", CAMLOG_LAST_PHYS, CAMLOG_LAST_SIZE);
}
#endif

#if GUARD_ONLY
static void write_level(int idok, const int st[N_BLOCKS])
{
    (void)st;
    ps("== write level "); phex(LEVEL, 2); nl();
    if (!idok) { ps("NOT DONE: av-cam identity not confirmed; nothing is written\n"); return; }
#if LEVEL == 43
    u32 w = flag_write(DFELOG_VA, DFELOG_BITS, 0);
#else
    u32 w = flag_write(GUARD_VA, LEVEL == 41 ? GUARD_NOFORCE : GUARD_OFF, 0);
#endif
    if (w == 0xffffffffu) ps("NOT DONE: the switch byte could not be written; it was put back\n");
    else if (!w) ps("NOTHING TO DO: the switch bit is already set\n");
    else ps("DONE: 0x00000001 bytes written in 0x00000001 runs, each read back\n");
}
#elif WRITES
/* the target of this level for block i */
static const u8 *target(int i)
{
#ifdef TEST_IDX
    return TGT(TEST_IDX, i);
#else
    return B[i]->stock;
#endif
}

struct run { int blk; u32 off; u32 len; };
static struct run done_runs[512];
static int n_done;

static void undo(void)
{
    int bad = 0;
    for (int r = n_done - 1; r >= 0; r--) {
        struct run *w = &done_runs[r];
        u8 back[64];
        if (!mem_wr(B[w->blk]->va - PHYS_DELTA + w->off, CUR(w->blk) + w->off, w->len) ||
            !mem_rd(B[w->blk]->va - PHYS_DELTA + w->off, back, w->len) || !same(back, CUR(w->blk) + w->off, w->len))
            bad = 1;
    }
    ps(bad ? "!! UNDO INCOMPLETE: battery out for ten seconds now\n" : "everything written was put back\n");
}

static void write_level(int idok, const int st[N_BLOCKS])
{
    ps("== write level "); phex(LEVEL, 2); nl();
    if (!idok) { ps("NOT DONE: av-cam identity not confirmed; nothing is written\n"); return; }
    u32 total = 0, extra_runs = 0;
#if LEVEL == 31
    /* put back clears the refresh loop's two switch bits first, whatever the blocks hold */
    {
        u32 w = flag_write(GUARD_VA, 0, GUARD_OFF | GUARD_NOFORCE);
        if (w == 0xffffffffu) { ps("NOT DONE: the refresh loop's switch byte could not be cleared\n"); return; }
        if (w) { ps("guard: switch bits cleared, 1 byte written and read back\n"); total = 1; extra_runs = 1; }
        w = flag_write(DFELOG_VA, 0, DFELOG_BITS);
        if (w == 0xffffffffu) { ps("NOT DONE: the front-end status print's flag byte could not be cleared\n"); return; }
        if (w) { ps("dfelog: status print bits cleared, 1 byte written and read back\n"); total++; extra_runs++; }
    }
#endif
    if (n_blk != N_BLOCKS) { ps("NOT DONE: the TV system slot of the 4K drive was not recognised; nothing is written\n"); return; }
    /* every byte must already be the stock byte or this level's target byte (put back: or any test's byte) */
    for (int i = 0; i < N_BLOCKS; i++) {
        if (st[i] == ST_UNREAD) { ps("NOT DONE: a block could not be read; nothing is written\n"); return; }
        const u8 *t = target(i);
        for (u32 k = 0; k < B[i]->len; k++) {
            u8 c = CUR(i)[k];
            int fine = c == B[i]->stock[k] || c == t[k], test_byte = 0;
            for (int n = 0; n < N_STEPS; n++) test_byte = test_byte || c == TGT(n, i)[k];
#if LEVEL == 31
            fine = fine || test_byte;
#endif
            if (!fine) {
                ps("NOT DONE: block "); ps(B[i]->name); ps(" byte at "); px(B[i]->va + k); ps(" holds "); phex(c, 2);
                if (test_byte) ps(" (another test is applied: run the put-back first)");
                ps("; nothing is written\n");
                return;
            }
        }
    }
    for (int i = 0; i < N_BLOCKS; i++) {
        const u8 *t = target(i);
        u32 k = 0;
        while (k < B[i]->len) {
            if (CUR(i)[k] == t[k]) { k++; continue; }
            u32 s = k;
            while (k < B[i]->len && CUR(i)[k] != t[k] && k - s < 64) k++;
            u8 back[64];
            u32 n = k - s;
            if (n_done >= (int)(sizeof done_runs / sizeof done_runs[0])) { ps("NOT DONE: too many runs\n"); undo(); return; }
            int okw = mem_wr(B[i]->va - PHYS_DELTA + s, t + s, n);
            done_runs[n_done].blk = i; done_runs[n_done].off = s; done_runs[n_done].len = n; n_done++;
            if (!okw || !mem_rd(B[i]->va - PHYS_DELTA + s, back, n) || !same(back, t + s, n)) {
                ps("NOT DONE: write or read-back at "); px(B[i]->va + s); ps(" failed; putting back\n");
                undo();
                return;
            }
            total += n;
        }
    }
#if TEST_SETS_FLAGS
    {
        u32 w = flag_write(GUARD_VA, GUARD_NOFORCE, 0);
        if (w == 0xffffffffu) { ps("NOT DONE: the no-restart bit could not be set; putting back\n"); undo(); return; }
        if (w) { ps("guard: no-restart bit set, 1 byte written and read back\n"); total++; extra_runs++; }
        u32 w2 = flag_write(DFELOG_VA, DFELOG_BITS, 0);
        if (w2 == 0xffffffffu) {
            ps("NOT DONE: the status-print bits could not be set; putting back\n");
            if (w) flag_write(GUARD_VA, 0, GUARD_NOFORCE);
            undo();
            return;
        }
        if (w2) { ps("dfelog: status print bits set, 1 byte written and read back\n"); total++; extra_runs++; }
    }
#endif
    if (!total) { ps("NOTHING TO DO: every byte already holds the target\n"); return; }
    ps("DONE: "); px(total); ps(" bytes written in "); px((u32)n_done + extra_runs); ps(" runs, each read back\n");
}
#endif

/* ------------------------------------------------------------------ the constructor */

static const char *const LEVEL_NAME =
#if LEVEL == 1
    "dump";
#elif LEVEL == 11
    "test1";
#elif LEVEL == 21
    "test2";
#elif LEVEL == 22
    "test3";
#elif LEVEL == 23
    "test4";
#elif LEVEL == 24
    "test5";
#elif LEVEL == 25
    "test6";
#elif LEVEL == 26
    "test7";
#elif LEVEL == 27
    "test8";
#elif LEVEL == 28
    "test9";
#elif LEVEL == 29
    "test10";
#elif LEVEL == 30
    "test11";
#elif LEVEL == 51
    "test12";
#elif LEVEL == 52
    "test13";
#elif LEVEL == 41
    "norestart";
#elif LEVEL == 42
    "nocheck";
#elif LEVEL == 43
    "dfelog";
#else
    "putback";
#endif

__attribute__((constructor, used)) static void m3og_main(void)
{
    /* v2: /tmp_network is a RAM tmpfs (1 MB) in service mode; /ramdsk does not exist there (first kit-2 run) */
    static const char *const paths[2] = {"/tmp_network/m3og_result.txt", "/tmp/jiritsu/m3og_result.txt"};
    for (int i = 0; i < 2 && out_fd < 0; i++) {
        int fd = sys_open(paths[i], O_WRONLY | O_CREAT | O_EXCL, 0644);
        if (fd == -EEXIST) return;                      /* an earlier result is still there: do nothing at all */
        if (fd >= 0) out_fd = fd;
    }
    if (out_fd < 0) return;

    ps("m3og "); ps(VERSION); ps(" level "); ps(LEVEL_NAME); ps(" for ILCE-7M3 4.04"); nl();
    ps("euid "); px((u32)sc3(NR_geteuid32, 0, 0, 0)); ps(" pid "); px((u32)sc3(NR_getpid, 0, 0, 0)); nl();
    dump_file("/proc/cmdline");
    dump_file("/proc/version");
#if LEVEL == 1
    dump_file("/proc/uptime");
    dump_file("/proc/cpuinfo");
    dump_file("/proc/meminfo");
    dump_file("/proc/iomem");
    dump_file("/proc/modules");
    dump_file("/proc/interrupts");
    dump_file("/proc/mounts");
    dump_file("/proc/devices");
    dump_file("/proc/self/status");
    dump_file("/proc/self/maps");
    dump_dir("/sys/module/liro/parameters", 1);
    dump_dir("/sys/module/dmm/parameters", 1);
    dump_dir("/tmp_network", 0);
    dump_dir("/tmp/jiritsu", 0);
#endif

    mem_fd = sys_open("/dev/mem", WRITES ? O_RDWR : O_RDONLY, 0);
    if (mem_fd < 0) {
        ps("!! /dev/mem open failed "); px((u32)mem_fd); nl();
        ps("VERDICT NOT READY (no /dev/mem)\n");
    } else {
        int st[N_BLOCKS];
        int loc = 0;
        int idok = identity(&loc);
        /* v2: the blocks are read (and the dump copies its ranges) once the location is confirmed, so a code-range
         * mismatch still shows what the tables hold; writes still need the full identity */
        if (loc) { pick_system(); read_blocks(st); }
        else for (int i = 0; i < N_BLOCKS; i++) st[i] = ST_UNREAD;
        verdict(idok, st);
        if (loc) guard_show();
#if WRITES
        write_level(idok, st);
        if (idok && n_blk == N_BLOCKS) {
            ps("after:\n");
            read_blocks(st);
            verdict(idok, st);
        }
        if (idok) guard_show();
#else
        if (loc) {
            for (int i = 0; i < N_DUMP; i++) dump_range(DUMP[i].name, DUMP[i].va, DUMP[i].len);
            for (int i = 0; i < n_blk; i++) dump_range(B[i]->name, B[i]->va, B[i]->len);
            for (int i = 0; i < n_live; i++) dump_range("image_page", live_pages[i], 0x1000);
        }
        dump_log("klog", KLOG_PHYS, KLOG_LEN, 0);
        /* v10: the camera core's own log lines, kept in RAM by the kernel's log module */
        dump_camlogs();
#endif
        sys_close(mem_fd);
    }
    ps("== done, bytes before this line: ");
    px(out_total + olen);
    nl();
    flush();
    sc3(NR_fsync, out_fd, 0, 0);
    sys_close(out_fd);
}
