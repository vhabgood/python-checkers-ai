// checkers_db_unity.cpp
// A single-file "unity build" to compile the database library.

// ============================================================================
// SECTION 1: C Standard Headers
// ============================================================================
#define _FILE_OFFSET_BITS 64
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

// ============================================================================
// SECTION 2: Core Database Definitions
// ============================================================================
#define MAXPIECES 8 // We only have databases up to 8 pieces.
#define DB_BLOCKSIZE 1024
#define DB_UNKNOWN 0
#define DB_WIN 1
#define DB_LOSS 2
#define DB_DRAW 3
#define DB_UNAVAILABLE 4
#define BLACK 2
#define WHITE 1

typedef struct {
    uint32_t bm, bk, wm, wk;
} position;

typedef struct {
    FILE *cprfile, *idxfile;
    FILE *mtc_cpr_file, *mtc_idx_file;
} subdb;

// ============================================================================
// SECTION 3: Internal Database State and Helpers
// ============================================================================
static FILE* c_debug_log = NULL;
static char db_path[1024] = "./db";
static uint64_t bicoef[33][11];

static int bitcount(uint32_t n) {
    int count = 0;
    while (n) {
        n &= (n - 1);
        count++;
    }
    return count;
}

static void initbicoef(void) {
    for (int i = 0; i <= 32; ++i) {
        bicoef[i][0] = 1;
        for (int j = 1; j <= 10; ++j) {
            bicoef[i][j] = (i < j) ? 0 : bicoef[i - 1][j - 1] + bicoef[i - 1][j];
        }
    }
}

// ============================================================================
// SECTION 4: Compression and Indexing Utilities
// ============================================================================
static int get_msb(uint32_t n) {
    int b = 0;
    if (n & 0xFFFF0000) b += 16;
    if (n & 0xFF00FF00) b += 8;
    if (n & 0xF0F0F0F0) b += 4;
    if (n & 0xCCCCCCCC) b += 2;
    if (n & 0xAAAAAAAA) b += 1;
    return b;
}

// ===========================================================================
// SECTION 5: Core Lookup Logic
// ===========================================================================
int opendb(int nwm, int nwk, int nbm, int nbk, subdb* db);
uint64_t get_index(position *p, int color, int nwm, int nwk, int nbm, int nbk);
int db_get_value(subdb *db, uint64_t index);
int db_get_mtc(subdb *db, uint64_t index);

int internal_db_lookup(position *p, int *mtc, int color) {
    int bm_count = bitcount(p->bm);
    int bk_count = bitcount(p->bk);
    int wm_count = bitcount(p->wm);
    int wk_count = bitcount(p->wk);

    int nbm, nbk, nwm, nwk;
    // Database files are named based on white having fewer or equal pieces.
    if (wm_count + wk_count > bm_count + bk_count) {
        nwm = bm_count; nwk = bk_count; nbm = wm_count; nbk = wk_count;
    } else {
        nwm = wm_count; nwk = wk_count; nbm = bm_count; nbk = bk_count;
    }

    subdb db; 
    if (opendb(nwm, nwk, nbm, nbk, &db) < 0) {
        return DB_UNAVAILABLE;
    }

    int result = DB_UNKNOWN;
    uint64_t index = get_index(p, color, nwm, nwk, nbm, nbk);
    result = db_get_value(&db, index);
    
    if (result != DB_UNKNOWN && result != DB_UNAVAILABLE) {
        *mtc = db_get_mtc(&db, index);
    } else {
        *mtc = 0;
    }

    if (db.cprfile) fclose(db.cprfile);
    if (db.idxfile) fclose(db.idxfile);
    if (db.mtc_cpr_file) fclose(db.mtc_cpr_file);
    if (db.mtc_idx_file) fclose(db.mtc_idx_file);

    return result;
}

// ============================================================================
// SECTION 6: Public C API (Exported for Python)
// ============================================================================
extern "C" {
    int db_init(const char *path, int, int) {
        if (c_debug_log == NULL) {
            c_debug_log = fopen("c_debug.log", "w");
        }
        if (path) strncpy(db_path, path, sizeof(db_path) - 1);
        initbicoef();
        return 0;
    }

    void db_close() {
        if (c_debug_log) {
            fclose(c_debug_log);
            c_debug_log = NULL;
        }
    }

    int EGDB_lookup(int* R, uint32_t bm, uint32_t bk, uint32_t wm, uint32_t wk, int color, int* mtc) {
        if (c_debug_log) {
            fprintf(c_debug_log, "[C++ EGDB_lookup] --> Received Request | Color: %d | Bitboards: bm=%u, bk=%u, wm=%u, wk=%u\n", color, bm, bk, wm, wk);
        }

        int total_pieces = bitcount(bm) + bitcount(bk) + bitcount(wm) + bitcount(wk);
        if (total_pieces > MAXPIECES || total_pieces < 2) {
            *R = DB_UNAVAILABLE; *mtc = 0;
            return 1;
        }

        position p = {bm, bk, wm, wk};
        *R = internal_db_lookup(&p, mtc, color);

        if (c_debug_log) {
            fprintf(c_debug_log, "[C++ EGDB_lookup] <-- Sending Response | Result: %d, MTC: %d\n", *R, *mtc);
            fflush(c_debug_log);
        }
        return 1;
    }
}

// ============================================================================
// SECTION 7: File I/O and Database Access Definitions
// ============================================================================
int opendb(int nwm, int nwk, int nbm, int nbk, subdb* db) {
    char name[1024];
    int total_pieces = nwm + nwk + nbm + nbk;
    
    if (total_pieces > MAXPIECES) return -1;

    if (total_pieces < 8) {
        snprintf(name, sizeof(name), "%s/db%d.cpr", db_path, total_pieces);
    } else {
        snprintf(name, sizeof(name), "%s/db8-%d%d%d%d.cpr", db_path, nwm, nwk, nbm, nbk);
    }
    db->cprfile = fopen(name, "rb");

    if (total_pieces < 8) snprintf(name, sizeof(name), "%s/db%d.idx", db_path, total_pieces);
    else snprintf(name, sizeof(name), "%s/db8-%d%d%d%d.idx", db_path, nwm, nwk, nbm, nbk);
    db->idxfile = fopen(name, "rb");

    if (total_pieces < 8) snprintf(name, sizeof(name), "%s/db%d.cpr_mtc", db_path, total_pieces);
    else snprintf(name, sizeof(name), "%s/db8-%d%d%d%d.cpr_mtc", db_path, nwm, nwk, nbm, nbk);
    db->mtc_cpr_file = fopen(name, "rb");

    if (total_pieces < 8) snprintf(name, sizeof(name), "%s/db%d.idx_mtc", db_path, total_pieces);
    else snprintf(name, sizeof(name), "%s/db8-%d%d%d%d.idx_mtc", db_path, nwm, nwk, nbm, nbk);
    db->mtc_idx_file = fopen(name, "rb");
    
    if (db->cprfile && db->idxfile) return 0;
    return -1;
}

uint64_t get_index(position *p, int color, int nwm, int nwk, int nbm, int nbk) {
    uint32_t bm, bk, wm, wk;
    int i, k;

    if ((color == WHITE && (nwm + nwk > nbm + nbk)) || (color == BLACK && (nwm + nwk <= nbm + nbk))) {
        bm = 0; bk = 0; wm = 0; wk = 0;
        for(i = 0; i < 32; ++i) {
            if((p->wm >> i) & 1) bm |= (1 << (31 - i));
            if((p->wk >> i) & 1) bk |= (1 << (31 - i));
            if((p->bm >> i) & 1) wm |= (1 << (31 - i));
            if((p->bk >> i) & 1) wk |= (1 << (31 - i));
        }
    } else {
        bm = p->bm; bk = p->bk; wm = p->wm; wk = p->wk;
    }
    
    uint64_t index = 0;
    for (k = nwm; k > 0; --k) {
        i = get_msb(wm);
        wm &= ~(1 << i);
        index += bicoef[i][k];
    }
    
    uint32_t b = wk;
    for (k = nwk; k > 0; --k) {
        i = get_msb(b);
        b &= ~(1 << i);
        index += bicoef[i][k] * bicoef[32 - nwm][nwk - k + 1];
    }

    uint64_t factor = bicoef[32][nwm] * bicoef[32 - nwm][nwk];
    uint64_t subindex = 0;
    
    uint32_t temp = ~0;
    for (k = 1; k <= nwm; ++k) {
        i = get_msb(p->wm);
        p->wm &= ~(1 << i);
        temp &= ~(1 << (31-i));
    }
    for (k = 1; k <= nwk; ++k) {
        i = get_msb(p->wk);
        p->wk &= ~(1 << i);
        temp &= ~(1 << (31-i));
    }

    for (k = nbm; k > 0; --k) {
        i = get_msb(bm);
        bm &= ~(1 << i);
        int j = get_msb(temp & ((1 << i) - 1));
        subindex += bicoef[i][k] - bicoef[j][k];
    }
    
    index += subindex * factor;
    return index;
}

int db_get_value(subdb *db, uint64_t index) {
    uint32_t block[DB_BLOCKSIZE / 4];
    uint32_t block_nr = (uint32_t)(index / (DB_BLOCKSIZE * 4));
    uint32_t block_offset = (uint32_t)(index % (DB_BLOCKSIZE * 4));
    uint32_t offset;

    if (fseek(db->idxfile, block_nr * 4, SEEK_SET) != 0) return DB_UNAVAILABLE;
    if (fread(&offset, 4, 1, db->idxfile) != 1) return DB_UNAVAILABLE;
    if (fseek(db->cprfile, offset, SEEK_SET) != 0) return DB_UNAVAILABLE;

    int n = fread(block, 4, DB_BLOCKSIZE / 4, db->cprfile);
    if (n <= 0) return DB_UNAVAILABLE;
    
    unsigned char *c = (unsigned char*)block;
    int val = c[0];
    if (val == 0) {
        val = c[1] & 3;
        uint32_t fill = (val << 30) | (val << 28) | (val << 26) | (val << 24) | (val << 22) | (val << 20) | (val << 18) | (val << 16) | (val << 14) | (val << 12) | (val << 10) | (val << 8) | (val << 6) | (val << 4) | (val << 2) | val;
        for (int i = 0; i < DB_BLOCKSIZE / 4; ++i) block[i] = fill;
    } else {
        uint32_t *p = block + (DB_BLOCKSIZE / 4) - 1;
        unsigned char *q = c + n * 4 - 1;
        uint32_t bits = 0;
        int bit_count = 0;
        while(p >= block) {
            bits |= *q-- << bit_count;
            bit_count += 8;
            while(bit_count >= 2) {
                *p-- = (bits & 3);
                bits >>= 2;
                bit_count -= 2;
            }
        }
    }
    return (block[block_offset / 4] >> ((block_offset % 4) * 2)) & 3;
}

int db_get_mtc(subdb *db, uint64_t index) {
    if (!db->mtc_cpr_file || !db->mtc_idx_file) return 0;
    
    unsigned char block[DB_BLOCKSIZE];
    uint32_t block_nr = (uint32_t)(index / DB_BLOCKSIZE);
    uint32_t block_offset = (uint32_t)(index % DB_BLOCKSIZE);
    uint32_t offset;

    if (fseek(db->mtc_idx_file, block_nr * 4, SEEK_SET) != 0) return 0;
    if (fread(&offset, 4, 1, db->mtc_idx_file) != 1) return 0;
    if (fseek(db->mtc_cpr_file, offset, SEEK_SET) != 0) return 0;

    int n = fread(block, 1, DB_BLOCKSIZE, db->cprfile);
    if (n <= 0) return 0;

    int val = block[0];
    if (val == 0) return block[1];
    
    unsigned char *p = block + DB_BLOCKSIZE - 1;
    unsigned char *q = block + n - 1;
    uint32_t bits = 0;
    int bit_count = 0;
    int width = val;
    while (p >= block) {
        bits |= *q-- << bit_count;
        bit_count += 8;
        while(bit_count >= width) {
            *p-- = bits & ((1 << width) - 1);
            bits >>= width;
            bit_count -= width;
        }
    }
    return block[block_offset];
}
