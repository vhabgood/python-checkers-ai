// checkers_db_unity.cpp
// A single-file "unity build" to compile the database library.
// This file incorporates the core logic from the Kingsrow endgame database,
// providing a standard C-style interface for use by other programs.

// ============================================================================
// SECTION 1: C Standard Headers
// ============================================================================
#define _FILE_OFFSET_BITS 64
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h> // For uint32_t

// ============================================================================
// SECTION 2: Core Database Definitions (from dblookup.h)
// ============================================================================
#define MAXPIECES 10
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
// SECTION 3: Internal Database State and Helper Functions
// ============================================================================
static FILE* c_debug_log = NULL;
static subdb database[MAXPIECES + 1][MAXPIECES + 1][MAXPIECES + 1][MAXPIECES + 1][MAXPIECES + 1];
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
    int i, j;
    for (i = 0; i <= 32; ++i) {
        bicoef[i][0] = 1;
        for (j = 1; j <= 10; ++j) {
            if (i < j)
                bicoef[i][j] = 0;
            else
                bicoef[i][j] = bicoef[i - 1][j - 1] + bicoef[i - 1][j];
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

static uint64_t db_get_index(int manidx, int kingidx, int kings, int men) {
    if (kings < 0 || men < 0) return 0;
    if (kings == 0) return bicoef[manidx][men];
    return bicoef[32][men] * bicoef[32 - men][kings]
           - bicoef[kingidx][men] * bicoef[32 - men][kings]
           + db_get_index(kingidx, kingidx, kings - 1, men);
}

// ===========================================================================
// SECTION 5: Core Lookup Logic
// ===========================================================================
// Forward declarations for the functions used by internal_db_lookup
int opendb(int nwm, int nwk, int nbm, int nbk, subdb* db);
uint64_t get_index(position *p, int color);
int db_get_value(subdb *db, uint64_t index);
int db_get_mtc(subdb *db, uint64_t index);

int internal_db_lookup(position *p, int *mtc, int color) {
    int nmen, nkings;
    int bm, bk, wm, wk;

    if (color == WHITE) {
        nmen = bitcount(p->bm);
        nkings = bitcount(p->bk);
        bm = nmen;
        bk = nkings;
        wm = bitcount(p->wm);
        wk = bitcount(p->wk);
    } else {
        nmen = bitcount(p->wm);
        nkings = bitcount(p->wk);
        wm = nmen;
        wk = nkings;
        bm = bitcount(p->bm);
        bk = bitcount(p->bk);
    }

    subdb db; 
    if (opendb(wm, wk, bm, bk, &db) < 0) {
        return DB_UNAVAILABLE;
    }

    int result = DB_UNKNOWN;
    uint64_t index = get_index(p, color);
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
    int db_init(const char *path, int wld_cache, int mtc_cache) {
        if (c_debug_log == NULL) {
            c_debug_log = fopen("c_debug.log", "w");
        }

        if (path) strncpy(db_path, path, sizeof(db_path) - 1);
        initbicoef();
        memset(database, 0, sizeof(database));
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
            fprintf(c_debug_log, "[C++ EGDB_lookup] --> Received Request\n");
            fprintf(c_debug_log, "  - Color: %d\n", color);
            fprintf(c_debug_log, "  - Bitboards: bm=%u, bk=%u, wm=%u, wk=%u\n", bm, bk, wm, wk);
        }

        int total_pieces = bitcount(bm) + bitcount(bk) + bitcount(wm) + bitcount(wk);
        if (total_pieces > 7 || total_pieces < 2) {
            *R = DB_UNAVAILABLE;
            *mtc = 0;
            if (c_debug_log) {
                fprintf(c_debug_log, "[C++ EGDB_lookup] <-- Pre-check failed. Invalid number of pieces. Sending UNAVAILABLE.\n");
                fflush(c_debug_log);
            }
            return 1;
        }

        position p = {bm, bk, wm, wk};
        *R = internal_db_lookup(&p, mtc, color);

        if (c_debug_log) {
            fprintf(c_debug_log, "[C++ EGDB_lookup] <-- Sending Response\n");
            fprintf(c_debug_log, "  - Result: %d, MTC: %d\n", *R, *mtc);
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

    if (total_pieces > 8) {
        // Filename format: db<total_pieces>-<white_men><white_kings><black_men><black_kings>
        snprintf(name, sizeof(name), "%s/db%d-%d%d%d%d.cpr", db_path, total_pieces, nwm, nwk, nbm, nbk);
    } else {
        // Filename format: db<total_pieces>.cpr (for 2-8 pieces)
        snprintf(name, sizeof(name), "%s/db%d.cpr", db_path, total_pieces);
    }
    
    // --- DEBUGGING: Print the filename we are trying to open ---
    if (c_debug_log) {
        fprintf(c_debug_log, "[C++ opendb] Trying to open: %s\n", name);
        fflush(c_debug_log);
    }

    db->cprfile = fopen(name, "rb");

    // Repeat for .idx file
    if (total_pieces > 8) {
        snprintf(name, sizeof(name), "%s/db%d-%d%d%d%d.idx", db_path, total_pieces, nwm, nwk, nbm, nbk);
    } else {
        snprintf(name, sizeof(name), "%s/db%d.idx", db_path, total_pieces);
    }
    if (c_debug_log) {
        fprintf(c_debug_log, "[C++ opendb] Trying to open: %s\n", name);
        fflush(c_debug_log);
    }
    db->idxfile = fopen(name, "rb");
    
    // Repeat for .cpr_mtc file
    if (total_pieces > 8) {
        snprintf(name, sizeof(name), "%s/db%d-%d%d%d%d.cpr_mtc", db_path, total_pieces, nwm, nwk, nbm, nbk);
    } else {
        snprintf(name, sizeof(name), "%s/db%d.cpr_mtc", db_path, total_pieces);
    }
    if (c_debug_log) {
        fprintf(c_debug_log, "[C++ opendb] Trying to open: %s\n", name);
        fflush(c_debug_log);
    }
    db->mtc_cpr_file = fopen(name, "rb");

    // Repeat for .idx_mtc file
    if (total_pieces > 8) {
        snprintf(name, sizeof(name), "%s/db%d-%d%d%d%d.idx_mtc", db_path, total_pieces, nwm, nwk, nbm, nbk);
    } else {
        snprintf(name, sizeof(name), "%s/db%d.idx_mtc", db_path, total_pieces);
    }
    if (c_debug_log) {
        fprintf(c_debug_log, "[C++ opendb] Trying to open: %s\n", name);
        fflush(c_debug_log);
    }
    db->mtc_idx_file = fopen(name, "rb");

    if (db->cprfile && db->idxfile) return 0;
    
    // --- DEBUGGING: If we failed, print a message ---
    if (c_debug_log) {
        fprintf(c_debug_log, "[C++ opendb] Failed to open required database files.\n");
        fflush(c_debug_log);
    }
    return -1;
}

// In checkers_db_unity.cpp SECTION 7
uint64_t get_index(position *p, int color) {
    int i, j, k;
    uint32_t bm, bk, wm, wk;
    uint64_t index = 0;

    if (color == WHITE) {
        bm = p->bm;
        bk = p->bk;
        wm = p->wm;
        wk = p->wk;
    } else { // Invert colors for BLACK to move
        bm = 0;
        bk = 0;
        for (i = 0; i < 32; ++i) {
            if ((p->wm >> i) & 1) bm |= (1 << (31 - i));
            if ((p->wk >> i) & 1) bk |= (1 << (31 - i));
        }
        wm = 0;
        wk = 0; // <<< --- THIS IS THE FIX ---
        for (i = 0; i < 32; ++i) {
            if ((p->bm >> i) & 1) wm |= (1 << (31 - i));
            if ((p->bk >> i) & 1) wk |= (1 << (31 - i));
        }
    }

    int nbm = bitcount(bm);
    int nbk = bitcount(bk);
    
    for (k = nbm; k > 0; --k) {
        i = get_msb(bm);
        bm &= ~(1 << i);
        index += bicoef[i][k];
    }

    index *= bicoef[32-nbm][nbk];

    for (k = nbk; k > 0; --k) {
        i = get_msb(bk);
        bk &= ~(1 << i);
        index += bicoef[i][k];
    }

    // The rest of the logic remains a placeholder for now
    int nwm = bitcount(wm);
    int nwk = bitcount(wk);
    index *= bicoef[32][nwm] * bicoef[32][nwk];

    return index;
}

int db_get_value(subdb *db, uint64_t index) {
    uint32_t block[DB_BLOCKSIZE/4];
    uint32_t block_nr = (uint32_t) (index / (DB_BLOCKSIZE * 4));
    uint32_t block_offset = (uint32_t) (index % (DB_BLOCKSIZE * 4));
    uint32_t offset;
    int result = DB_UNAVAILABLE;

    if (!db->idxfile || fseek(db->idxfile, block_nr * 4, SEEK_SET) != 0) {
        return DB_UNAVAILABLE;
    }
    if (fread(&offset, 4, 1, db->idxfile) != 1) {
        return DB_UNAVAILABLE;
    }
    if (!db->cprfile || fseek(db->cprfile, offset, SEEK_SET) != 0) {
        return DB_UNAVAILABLE;
    }
    
    // Decompression stub
    unsigned char value_pair;
    if (fread(&value_pair, 1, 1, db->cprfile) == 1) {
        result = (value_pair >> ((index % 4) * 2)) & 3;
    }

    return result;
}

int db_get_mtc(subdb *db, uint64_t index) {
    if (!db->mtc_cpr_file || !db->mtc_idx_file) {
        return 0; 
    }

    uint32_t block_nr = (uint32_t) (index / DB_BLOCKSIZE);
    uint32_t block_offset = (uint32_t) (index % DB_BLOCKSIZE);
    uint32_t offset;
    int mtc_val = 0;
    
    if (fseek(db->mtc_idx_file, block_nr * 4, SEEK_SET) != 0) {
        return 0;
    }
    if (fread(&offset, 4, 1, db->mtc_idx_file) != 1) {
        return 0;
    }
    if (fseek(db->mtc_cpr_file, offset + block_offset, SEEK_SET) != 0) {
        return 0;
    }

    // Decompression stub for MTC
    unsigned char raw_mtc;
    if (fread(&raw_mtc, 1, 1, db->mtc_cpr_file) == 1) {
        mtc_val = raw_mtc;
    }
    
    return mtc_val;
}
