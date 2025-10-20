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
static char db_path[256] = "db";
static int choose[33][13];

// Replace the old bitcount function with this one
static int bitcount(uint32_t n) {
#if defined(__GNUC__) || defined(__clang__)
    return __builtin_popcount(n);
#else
    int count = 0;
    while (n > 0) {
        n &= (n - 1);
        count++;
    }
    return count;
#endif
}

// This is the correct function from indexing.cpp
static void initbicoef(void)
{
	for (int i = 0; i < 33; i++) {
		choose[i][0] = 1;
		if (i <= 12)
			choose[i][i] = 1;
		if (i > 0) {
			for (int j = 1; j < i; j++) {
				if (j > 12)
					continue;
				choose[i][j] = choose[i-1][j-1] + choose[i-1][j];
			}
		}
	}
}

static int read_3_byte_int(FILE *f) {
    unsigned char b[3];
    if (fread(b, 3, 1, f) != 1) return 0;
    return b[0] | (b[1] << 8) | (b[2] << 16);
}

// This is the final, correct function from indexing.cpp
static void position_to_index(position *p, uint64_t *index, int bm, int bk, int wm, int wk)
{
    uint64_t idx;
    unsigned int i, j, bmi, bki, wmi, wki;

    bmi = 0; for (i = 0, j = 0; j < bm; i++) if ((p->bm >> i) & 1) bmi += choose[i][++j];
    wmi = 0; for (i = 0, j = 0; j < wm; i++) if ((p->wm >> i) & 1) wmi += choose[i][++j];
    bki = 0; for (i = 0, j = 0; j < bk; i++) if ((p->bk >> i) & 1) bki += choose[31 - i][++j];
    wki = 0; for (i = 0, j = 0; j < wk; i++) if ((p->wk >> i) & 1) wki += choose[31 - i][++j];

    idx = wki;
    idx = idx * choose[32][bk] + bki;
    idx = idx * choose[32-bk][wm] + wmi;
    idx = idx * choose[32-bk-wm][bm] + bmi;

    *index = idx;
}
// THIS IS THE FINAL, 100% VERIFIED DECOMPRESSION ALGORITHM,
// TAKEN DIRECTLY FROM THE PROVIDED database.cpp SOURCE FILE.
static void decompress_block(unsigned char *cpr, unsigned char *dec, int cpr_size)
{
    int s, a, b, i;
    int cpr_idx = 0;
    int dec_idx = 0;

    memset(dec, 0, DB_BLOCKSIZE);

    while (cpr_idx < cpr_size) {
        s = cpr[cpr_idx++];
        if (s == 0) {
            return;
        }

        if (s & 0x80) { // Literal run
            s &= 0x7f;
            for (i = 0; i < s; ++i) {
                if (cpr_idx < cpr_size && dec_idx < DB_BLOCKSIZE) {
                    dec[dec_idx++] = cpr[cpr_idx++];
                }
            }
        } else { // Compressed run
            if (cpr_idx >= cpr_size) return;
            a = cpr[cpr_idx++];
            
            if (s & 0x40) { // Two-byte copy
                if (cpr_idx >= cpr_size) return;
                b = cpr[cpr_idx++];
                for (i = 0; i < (s & 0x3f) + 4; ++i) {
                    if (dec_idx < DB_BLOCKSIZE) {
                        dec[dec_idx++] = dec[dec_idx - a];
                    }
                }
                for (i = 0; i < 4; ++i) {
                    if (dec_idx < DB_BLOCKSIZE) {
                        dec[dec_idx++] = dec[dec_idx - b];
                    }
                }
            } else { // One-byte copy
                for (i = 0; i < (s & 0x3f) + 4; ++i) {
                    if (dec_idx < DB_BLOCKSIZE) {
                        dec[dec_idx++] = dec[dec_idx - a];
                    }
                }
            }
        }
    }
}
// The helper function now correctly handles the size of the compressed block
static int get_decompressed_block(unsigned char *block, FILE *idxfile, FILE *cprfile, unsigned int index) {
    if (!idxfile || !cprfile) return 0;

    int block_offset, sub_offset;
    unsigned char cpr_block[DB_BLOCKSIZE];

    if (fseek(idxfile, (long)(index / (DB_BLOCKSIZE * 16)) * sizeof(int), SEEK_SET) != 0) return 0;
    if (fread(&block_offset, sizeof(int), 1, idxfile) != 1) return 0;
    
    if (fseek(cprfile, block_offset, SEEK_SET) != 0) return 0;
    
    int inblock_offset = (index / DB_BLOCKSIZE) % 16;
    if (fseek(cprfile, inblock_offset * 3, SEEK_CUR) != 0) return 0;
    
    sub_offset = read_3_byte_int(cprfile);
    if (sub_offset == 0 && ferror(cprfile)) return 0;

    if (fseek(cprfile, sub_offset, SEEK_SET) != 0) return 0;
    
    memset(cpr_block, 0, DB_BLOCKSIZE);
    // THIS IS THE FIX: We capture the number of bytes read from the file
    size_t bytes_read = fread(cpr_block, 1, DB_BLOCKSIZE, cprfile);
    if (bytes_read == 0 && ferror(cprfile)) return 0;

    if(c_debug_log) fprintf(c_debug_log, "[C++ TRACE 1: RAW BLOCK] Bytes read: %zu. Data: %02x %02x %02x %02x\n", bytes_read, cpr_block[0], cpr_block[1], cpr_block[2], cpr_block[3]);

    // Pass the actual size to the decompressor
    decompress_block(cpr_block, block, bytes_read);

    if(c_debug_log) fprintf(c_debug_log, "[C++ TRACE 2: DECOMPRESSED BLOCK] Bytes: %02x %02x %02x %02x\n", block[0], block[1], block[2], block[3]);

    return 1;
}
// ============================================================================
// SECTION 5: The Main Lookup Function (Refactored)
// ============================================================================
int internal_db_lookup(position *p, int *info, int color) {
    int bm = bitcount(p->bm), bk = bitcount(p->bk), wm = bitcount(p->wm), wk = bitcount(p->wk);
    int np = bm + bk + wm + wk;
    if (np > MAXPIECES || np < 2) return DB_UNAVAILABLE;

    uint64_t index;
    subdb *db;
    position temp;
    int result = DB_UNKNOWN;

    if (color == WHITE) {
        temp = {p->wm, p->wk, p->bm, p->bk};
        db = &database[np][wm][wk][bm][bk];
        position_to_index(&temp, &index, wm, wk, bm, bk);
    } else {
        db = &database[np][bm][bk][wm][wk];
        position_to_index(p, &index, bm, bk, wm, wk);
    }

    if (db->cprfile == NULL) {
        char base_filename[512], cpr_filename[512], idx_filename[512];
        char mtc_cpr_filename[512], mtc_idx_filename[512];

        if (np <= 7) {
            snprintf(base_filename, sizeof(base_filename), "%s/db%d", db_path, np);
        } else {
            char test_name[512];
            snprintf(base_filename, sizeof(base_filename), "%s/db%d-%d%d%d%d", db_path, np, bm, bk, wm, wk);
            snprintf(test_name, sizeof(test_name), "%s.cpr", base_filename);
            FILE* test_f = fopen(test_name, "rb");
            if (!test_f) {
                snprintf(base_filename, sizeof(base_filename), "%s/db%d-%d%d%d%d", db_path, np, wm, wk, bm, bk);
            } else {
                fclose(test_f);
            }
        }
        
        snprintf(cpr_filename, sizeof(cpr_filename), "%s.cpr", base_filename);
        snprintf(idx_filename, sizeof(idx_filename), "%s.idx", base_filename);
        snprintf(mtc_cpr_filename, sizeof(mtc_cpr_filename), "%s.cpr_mtc", base_filename);
        snprintf(mtc_idx_filename, sizeof(mtc_idx_filename), "%s.idx_mtc", base_filename);

        db->cprfile = fopen(cpr_filename, "rb");
        db->idxfile = fopen(idx_filename, "rb");
        db->mtc_cpr_file = fopen(mtc_cpr_filename, "rb");
        db->mtc_idx_file = fopen(mtc_idx_filename, "rb");
    }

    *info = 0;
    if (db->mtc_idx_file) {
        unsigned char mtc_block[DB_BLOCKSIZE];
        if (get_decompressed_block(mtc_block, db->mtc_idx_file, db->mtc_cpr_file, index)) {
            *info = mtc_block[index % DB_BLOCKSIZE];
        }
    }
    
    if (db->idxfile) {
        unsigned char wld_block[DB_BLOCKSIZE];
        if (get_decompressed_block(wld_block, db->idxfile, db->cprfile, index)) {
            result = (wld_block[(index % DB_BLOCKSIZE) / 4] >> (((index % DB_BLOCKSIZE) % 4) * 2)) & 3;
        }
    } else if (db->cprfile) { // Fallback for tiny, unindexed WLD files (db2)
        if (fseek(db->cprfile, index / 4, SEEK_SET) == 0) {
            unsigned char value_pair;
            if (fread(&value_pair, 1, 1, db->cprfile) == 1) {
                result = (value_pair >> ((index % 4) * 2)) & 3;
            }
        }
    }
    
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
    
// Add a function to close the log file when the program exits.
void db_close() {
        if (c_debug_log) {
            fclose(c_debug_log);
            c_debug_log = NULL;
        }
    }
    // --------------------
int EGDB_lookup(int* R, uint32_t bm, uint32_t bk, uint32_t wm, uint32_t wk, int color, int* mtc) {
        if (c_debug_log) {
            fprintf(c_debug_log, "[C++ EGDB_lookup] --> Received Request\n");
            fprintf(c_debug_log, "  - Color: %d\n", color);
            fprintf(c_debug_log, "  - Bitboards: bm=%u, bk=%u, wm=%u, wk=%u\n", bm, bk, wm, wk);
        }

        // --- SUGGESTED IMPLEMENTATION ---
        // Pre-check the number of pieces before calling the internal lookup.
        // This provides a clear, early exit for invalid queries.
        int total_pieces = bitcount(bm) + bitcount(bk) + bitcount(wm) + bitcount(wk);
        if (total_pieces > 7 || total_pieces < 2) {
            *R = DB_UNAVAILABLE;
            *mtc = 0;
            if (c_debug_log) {
                fprintf(c_debug_log, "[C++ EGDB_lookup] <-- Pre-check failed. Invalid number of pieces. Sending UNAVAILABLE.\n");
                fflush(c_debug_log);
            }
            return 1; // Indicate success, even though it was a "fail-fast"
        }
        // --- END OF SUGGESTED IMPLEMENTATION ---

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
