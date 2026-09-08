#!/usr/bin/env Rscript
# -*- coding: utf-8 -*-
# ==========================================================================
# GT-002.2 — f4 SCREEN WITH ADMIXTOOLS2
# ==========================================================================
# Network-based Western Mediterranean screen.
#
# Phases:
#   A — f4(Maghreb, Africa; Iberia, X): where does shared drift attach?
#   B — Time-stratified: same test by T0-T3 layer
#   C — Alternative route controls: Italy/Sicily/Sardinia as mediating nodes
#   D — N.Africa.East controls
#
# IMPORTANT: This script computes f4-statistics from pre-computed f2 blocks.
# D-statistics (ABBA-BABA) require allele-frequency normalization data that
# is only available when reading directly from genotype files, not from f2
# blocks.  For the screening phase, f4 sign and Z-scores are sufficient:
# D and f4 always share the same sign, and their Z-scores are nearly
# identical (D = f4 / normalization).  If D-statistics are needed for
# specific confirmatory tests, run f4() with the genotype prefix directly.
#
# Prerequisites:
#   1. gt002/prep_gt002_2.py has run (creates popmap.tsv + f4_tests.tsv)
#   2. AADR genotype files downloaded:
#      v66.p1_1240K.aadr.patch.PUB.geno / .snp / .ind
#
# Outputs (to gt002/f4_results/):
#   GT-002.2.f4_results.tsv  — all f4 statistics (est, se, z, p)
#   GT-002.2.sig_f4.tsv     — significant results (|Z| > 3)
#   GT-002.2.summary.tsv    — per-phase summary
# ==========================================================================

suppressPackageStartupMessages({
  library(admixtools)
  library(data.table)
})

# Print traceback on error so CI logs show the actual failure point.
# quit(status=1) ensures the script STOPS on error (default options(error=...)
# would silently continue, masking the real problem).
options(error = function() {
  cat("\n=== ERROR TRACEBACK ===\n")
  traceback(2)
  cat("\n=== Session Info ===\n")
  print(sessionInfo())
  cat("\n=== SCRIPT STOPPED DUE TO ERROR ===\n")
  quit(status = 1)
})

# --- CONFIG ---
GENO_PREFIX  <- "v66.p1_1240K.aadr.patch.PUB"    # EIGENSTRAT prefix
MOD_PREFIX   <- paste0(GENO_PREFIX, "_gt002")    # modified prefix
POP_DIR      <- "gt002/popinv"
RESULTS_DIR  <- "gt002/f4_results"
F2_DIR       <- "f2_blocks"

dir.create(RESULTS_DIR, showWarnings = FALSE, recursive = TRUE)
dir.create(F2_DIR,       showWarnings = FALSE, recursive = TRUE)

disk_free <- function() {
  tryCatch({
    s <- system2("df", c("-h", "--output=avail", "."), stdout = TRUE, stderr = TRUE)
    tail(s, 1)
  }, error = function(e) "?")
}

# ==========================================================================
# 1. CREATE MODIFIED .ind FILE WITH CUSTOM POPULATION LABELS
# ==========================================================================
cat("[1/6] Creating modified .ind file...\n")
cat("  Disk free:", disk_free(), "\n")

popmap <- fread(file.path(POP_DIR, "GT-002.2.popmap.tsv"))
setnames(popmap, c("sample_id", "custom_pop_label", "group_id",
                    "region", "layer", "qc"))
cat(sprintf("  popmap: %d samples, %d unique pop labels\n",
            nrow(popmap), length(unique(popmap$custom_pop_label))))

# Read original .ind file (EIGENSTRAT: sample_id, sex, population — whitespace-delimited)
orig_ind <- fread(paste0(GENO_PREFIX, ".ind"), header = FALSE,
                  colClasses = "character")
cat(sprintf("  .ind file: %d rows, %d columns\n", nrow(orig_ind), ncol(orig_ind)))

if (ncol(orig_ind) < 3) {
  stop(sprintf("ERROR: .ind file has only %d columns (expected >= 3). First row: %s",
               ncol(orig_ind), paste(orig_ind[1], collapse = " | ")))
}

setnames(orig_ind, c("sample_id", "sex", "population"))

# Match population labels preserving original .ind order.
# CRITICAL: .geno columns correspond to .ind rows by position, so we must
# NOT reorder via merge(). Use match() to look up labels in place.
mod_ind <- copy(orig_ind)
mod_ind[, population := popmap$custom_pop_label[match(sample_id, popmap$sample_id)]]
mod_ind[is.na(population), population := "UNUSED"]

# Write modified .ind file (EIGENSTRAT format: whitespace, no header)
fwrite(mod_ind[, .(sample_id, sex, population)],
       paste0(MOD_PREFIX, ".ind"), sep = "\t", col.names = FALSE)

# RENAME (not copy!) .geno and .snp to modified prefix.
# file.copy would double the 7.1 GB .geno → 14.2 GB peak → disk overflow.
# file.rename just moves the file, zero extra disk.
file.rename(paste0(GENO_PREFIX, ".geno"), paste0(MOD_PREFIX, ".geno"))
file.rename(paste0(GENO_PREFIX, ".snp"),  paste0(MOD_PREFIX, ".snp"))
file.remove(paste0(GENO_PREFIX, ".ind"))  # remove original .ind (tiny)

n_pops    <- length(unique(mod_ind$population[mod_ind$population != "UNUSED"]))
n_samples <- sum(mod_ind$population != "UNUSED")
n_unused  <- sum(mod_ind$population == "UNUSED")
cat(sprintf("  %d samples mapped to %d populations (%d unused)\n",
            n_samples, n_pops, n_unused))
cat("  Disk free after rename:", disk_free(), "\n")

# ==========================================================================
# 2. EXTRACT f2 BLOCKS
# ==========================================================================
cat("[2/6] Extracting f2 blocks (may take 5-30 min)...\n")

# Only include populations that actually exist in the .ind file.
# The popmap comes from the .anno file which has ALL samples, but the .ind
# file only has samples with genotype data.  extract_f2 fails if a pop
# in the pops argument doesn't appear in the .ind file.
analysis_pops <- unique(mod_ind$population[mod_ind$population != "UNUSED"])
cat(sprintf("  %d analysis populations (from .ind file)\n", length(analysis_pops)))
cat("  First 10 pops:", paste(head(analysis_pops, 10), collapse = ", "), "\n")

# maxmiss = 1: keep all SNPs even if missing in some populations.
#   Ancient DNA has high missingness; default maxmiss = 0 would discard
#   almost all SNPs.  maxmiss = 1 retains everything (RSCS correction
#   handles the bias).
# minac2 = TRUE: recommended for pseudohaploid ancient data.
cat("  Starting extract_f2...\n")
tryCatch({
  extract_f2(
    pref      = MOD_PREFIX,
    outdir    = F2_DIR,
    pops      = analysis_pops,
    overwrite = TRUE,
    blgsize   = 0.05,     # 5 cM block size (standard for ancient DNA)
    maxmiss   = 1,        # retain all SNPs (high missingness in aDNA)
    minac2    = TRUE,     # correct for pseudohaploid bias
    maxmem    = 8000,     # use up to 8 GB RAM (runner has ~14 GB)
    verbose   = TRUE
  )
}, error = function(e) {
  cat("\n  FATAL: extract_f2() failed!\n")
  cat("  Error message:", conditionMessage(e), "\n")
  cat("  Checking if genotype files exist:\n")
  cat("    .geno:", file.exists(paste0(MOD_PREFIX, ".geno")), "\n")
  cat("    .snp:", file.exists(paste0(MOD_PREFIX, ".snp")), "\n")
  cat("    .ind:", file.exists(paste0(MOD_PREFIX, ".ind")), "\n")
  cat("  Disk free:", disk_free(), "\n")
  stop("extract_f2() failed: ", conditionMessage(e))
})

cat("  f2 blocks extracted.\n")

# Free disk: remove .geno after f2 extraction (saves ~7 GB)
file.remove(paste0(MOD_PREFIX, ".geno"))
cat("  .geno removed. Disk free:", disk_free(), "\n")

# Load f2 blocks into memory
cat("  Loading f2 blocks from disk...\n")
tryCatch({
  f2_blocks <- f2_from_precomp(F2_DIR, pops = analysis_pops)
}, error = function(e) {
  cat("\n  FATAL: f2_from_precomp() failed!\n")
  cat("  Error message:", conditionMessage(e), "\n")
  cat("  F2_DIR contents:\n")
  print(list.files(F2_DIR, recursive = TRUE))
  cat("  Disk free:", disk_free(), "\n")
  stop("f2_from_precomp() failed: ", conditionMessage(e))
})

cat(sprintf("  f2 blocks loaded: %d populations, %d blocks\n",
            length(analysis_pops),
            dim(f2_blocks)[3]))
cat("  Disk free:", disk_free(), "\n")

# ==========================================================================
# 3. READ f4 TEST DESIGN & FILTER
# ==========================================================================
cat("[3/6] Reading f4 test design...\n")

f4_design <- fread(file.path(POP_DIR, "GT-002.2.f4_tests.tsv"))
cat(sprintf("  %d tests designed (%d usable, %d partial)\n",
            nrow(f4_design),
            sum(f4_design$usable == "YES"),
            sum(f4_design$usable == "PARTIAL")))

# Get per-population sample counts from modified .ind
pop_sizes <- table(mod_ind$population)
analysis_pop_names <- names(pop_sizes)[pop_sizes >= 1 & names(pop_sizes) != "UNUSED"]

# Filter: keep only tests where all 4 populations exist and have >= 2 samples
keep <- sapply(seq_len(nrow(f4_design)), function(i) {
  pops4 <- as.character(unlist(f4_design[i, .(pop1, pop2, pop3, pop4)]))
  if (any(pops4 %in% c("UNUSED", "", NA))) return(FALSE)
  if (!all(pops4 %in% analysis_pop_names)) return(FALSE)
  all(pop_sizes[pops4] >= 2)
})

f4_design_run <- f4_design[keep]
f4_design_skip <- f4_design[!keep]
cat(sprintf("  %d tests runnable, %d skipped (pop n<2 or missing)\n",
            nrow(f4_design_run), nrow(f4_design_skip)))

# ==========================================================================
# 4. COMPUTE f4 STATISTICS (BATCH)
# ==========================================================================
cat("[4/6] Computing f4 statistics (batch mode)...\n")

# ADMIXTOOLS2 f4() signature:
#   f4(pop1, pop2, pop3, pop4, f2_blocks, block_lengths, f2_dir,
#      f2_denom, sure, unique_only, verbose)
# With comb-like behavior: pass equal-length vectors for pop1-pop4.
# sure = TRUE suppresses the safety check for >10000 combos.
if (nrow(f4_design_run) > 0) {
  results <- tryCatch({
    f4(pop1 = as.character(f4_design_run$pop1),
       pop2 = as.character(f4_design_run$pop2),
       pop3 = as.character(f4_design_run$pop3),
       pop4 = as.character(f4_design_run$pop4),
       f2_blocks = f2_blocks,
       sure = TRUE)
  }, error = function(e) {
    cat("  Batch f4 failed:", conditionMessage(e), "\n")
    cat("  Falling back to loop mode...\n")
    # Fallback: loop one test at a time
    res_list <- list()
    for (i in seq_len(nrow(f4_design_run))) {
      t <- f4_design_run[i]
      r <- tryCatch({
        f4(pop1 = as.character(t$pop1),
           pop2 = as.character(t$pop2),
           pop3 = as.character(t$pop3),
           pop4 = as.character(t$pop4),
           f2_blocks = f2_blocks,
           sure = TRUE)
      }, error = function(e) {
        cat(sprintf("    Test %d failed: %s\n", i, conditionMessage(e)))
        NULL
      })
      if (!is.null(r) && nrow(r) > 0) res_list[[length(res_list) + 1]] <- r
      if (i %% 50 == 0) cat(sprintf("  %d/%d\n", i, nrow(f4_design_run)))
    }
    if (length(res_list) > 0) do.call(rbind, res_list) else NULL
  })
} else {
  results <- NULL
  cat("  No runnable tests!\n")
}

# Merge results with test metadata
if (!is.null(results) && nrow(results) > 0) {
  f4_df <- as.data.table(results)
  # Column name is 'est' in ADMIXTOOLS2 output (not 'f4')
  setnames(f4_df, "est", "f4")
  # Attach phase + description from design
  f4_df[, phase := f4_design_run$phase]
  f4_df[, description := f4_design_run$description]
  f4_df[, usable := f4_design_run$usable]
} else {
  f4_df <- data.table()
  cat("  WARNING: No f4 results computed!\n")
}

cat(sprintf("  %d f4 results computed\n", nrow(f4_df)))

# Write full results
fwrite(f4_df, file.path(RESULTS_DIR, "GT-002.2.f4_results.tsv"), sep = "\t")

# ==========================================================================
# 5. SUMMARY — SIGNIFICANT RESULTS (|Z| > 3)
# ==========================================================================
cat("[5/6] Generating summary...\n")

if (nrow(f4_df) > 0) {
  sig_f4 <- f4_df[abs(z) > 3][order(-abs(z))]
  fwrite(sig_f4, file.path(RESULTS_DIR, "GT-002.2.sig_f4.tsv"), sep = "\t")

  # Per-phase summary
  phase_summary <- f4_df[, .(
    n_tests         = .N,
    n_sig           = sum(abs(z) > 3),
    n_sig_positive  = sum(z > 3),
    n_sig_negative  = sum(z < -3),
    max_abs_z       = max(abs(z)),
    mean_f4         = mean(f4, na.rm = TRUE),
    mean_z          = mean(z, na.rm = TRUE)
  ), by = phase][order(phase)]

  fwrite(phase_summary, file.path(RESULTS_DIR, "GT-002.2.summary.tsv"),
         sep = "\t")

  cat(sprintf("\n=== GT-002.2 f4 SCREEN COMPLETE ===\n"))
  cat(sprintf("Total tests run:     %d\n", nrow(f4_df)))
  cat(sprintf("Significant |Z|>3:   %d (%.1f%%)\n",
              nrow(sig_f4),
              100 * nrow(sig_f4) / max(1, nrow(f4_df))))
  cat("\nPhase summary:\n")
  print(phase_summary)

  cat("\nTop 15 significant f4:\n")
  if (nrow(sig_f4) > 0)
    print(head(sig_f4[, .(description, f4, z, p)], 15))
} else {
  cat("No results to summarize.\n")
}

# ==========================================================================
# 6. SKIP LOG — record which tests were skipped and why
# ==========================================================================
cat("[6/6] Writing skip log...\n")

if (nrow(f4_design_skip) > 0) {
  skip_reason <- sapply(seq_len(nrow(f4_design_skip)), function(i) {
    pops4 <- as.character(unlist(f4_design_skip[i, .(pop1, pop2, pop3, pop4)]))
    missing_pops <- pops4[!pops4 %in% analysis_pop_names]
    if (length(missing_pops) > 0) {
      paste0("missing: ", paste(missing_pops, collapse = ", "))
    } else {
      small_pops <- pops4[pop_sizes[pops4] < 2]
      paste0("n<2: ", paste(small_pops, collapse = ", "))
    }
  })
  f4_design_skip[, skip_reason := skip_reason]
  fwrite(f4_design_skip, file.path(RESULTS_DIR, "GT-002.2.skipped.tsv"),
         sep = "\t")
  cat(sprintf("  %d skipped tests logged\n", nrow(f4_design_skip)))
}

cat("\nResults written to:", RESULTS_DIR, "\n")
cat("Disk free at end:", disk_free(), "\n")
