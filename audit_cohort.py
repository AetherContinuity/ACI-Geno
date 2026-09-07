#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GT-002.1 — COHORT AUDIT
======================
Comprehensive audit of the GT-002 cohort build from AADR v66.p1.

This script reuses build_cohort.py's parser and classification logic,
runs a reference parser (field-count accumulation, no strict-idlike
re-sync) to identify any records the build parser missed, and produces:

  gt002/audit/GT-002.1.audit-report.txt  — human-readable audit report
  gt002/audit/GT-002.1.popxlayer.tsv     — population × layer matrix (target regions)
  gt002/audit/GT-002.1.low-N-cells.tsv   — all sparse/empty cells

Run on GitHub Actions (same .anno file as the build).
"""

import os
import sys
import re
from collections import Counter, defaultdict

# Reuse build_cohort.py (same directory)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_cohort import (
    COUNTRY_REGION, EUROPE_CONTROL, ROLE, REGION_ORDER, LAYER_ORDER,
    ANALYSIS_QC, clean, to_float, layer_from_bp, norm_qc,
    region_for, idlike, resolve_columns, get_anno_text, parse_records, g,
    FALLBACK_NCOLS, ANNO_PATH,
)

AUDIT_DIR = "gt002/audit"
TARGET_REGIONS = {"IBERIA", "MAGHREB", "LEVANT", "NORTH_AFRICA_EAST"}


# ---------------------------------------------------------------------------
# REFERENCE PARSER — field-count accumulation, no strict-idlike re-sync
# ---------------------------------------------------------------------------
def broad_idlike(s):
    """Broader than build_cohort.idlike: any non-empty string with a letter,
    not starting with 'Genetic ID'.  No length or character-class restriction."""
    s = (s or "").strip()
    if not s or s.startswith("Genetic ID"):
        return False
    return bool(re.search(r"[A-Za-z]", s))


def idlike_fail_reasons(s):
    """Return list of reasons why build_cohort.idlike would reject s."""
    s = s.strip()
    if not s:
        return ["empty"]
    reasons = []
    if len(s) > 40:
        reasons.append(f"len={len(s)} > 40")
    if not re.match(r"^[A-Za-z0-9._+\-]+$", s):
        bad = sorted(set(
            c for c in s if not re.match(r"[A-Za-z0-9._+\-]", c)
        ))
        reasons.append(f"invalid chars {bad}")
    if not re.search(r"[A-Za-z]", s):
        reasons.append("no letter")
    return reasons


def ref_parser(lines, first_data, N):
    """Parse by accumulating field counts until N tabs, no idlike re-sync.
    Broad_idlike filter at the end.  This captures records that
    build_cohort.parse_records may miss due to strict idlike requirements
    or incorrect re-sync on multi-line cell continuations."""
    records = []
    buf = ""
    for ln in lines[first_data:]:
        cand = (buf + "\n" + ln) if buf else ln
        nf = len(cand.split("\t"))
        if nf == N:
            records.append(cand)
            buf = ""
        elif nf > N:
            parts = cand.split("\t")
            records.append("\t".join(parts[:N]))
            buf = "\t".join(parts[N:])
        else:
            buf = cand
    if buf.strip() and len(buf.split("\t")) == N:
        records.append(buf)
    # keep only N-field records whose first field passes broad_idlike
    return [r for r in records
            if len(r.split("\t")) == N and broad_idlike(r.split("\t")[0])]


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def main():
    text = get_anno_text()
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    total_physical = len(lines)

    # Detect N (same logic as build_cohort.py)
    cnt = Counter(len(l.split("\t")) for l in lines)
    wide = {k: v for k, v in cnt.items() if k >= 20}
    N = max(wide, key=wide.get) if wide else FALLBACK_NCOLS

    # Header boundary (same as build_cohort.py)
    first_data = -1
    for i, ln in enumerate(lines):
        if idlike(ln.split("\t")[0]):
            first_data = i
            break
    if first_data < 0:
        first_data = 0

    # === 1. REFERENCE PARSER ===
    ref_records = ref_parser(lines, first_data, N)
    ref_ids = set(clean(r.split("\t")[0]) for r in ref_records)

    # Single-line scan: lines with exactly N fields and broad_idlike first field
    single_line = [
        (i, lines[i].split("\t")[0].strip())
        for i in range(first_data, len(lines))
        if len(lines[i].split("\t")) == N
        and broad_idlike(lines[i].split("\t")[0])
    ]
    unique_single = set(sid for _, sid in single_line)

    # === 2. BUILD SCRIPT PARSER ===
    header, data, _ = parse_records(text)
    parsed_ids = set(clean(d.split("\t")[0]) for d in data)

    # === 3. MISSING ROWS ===
    missing = ref_ids - parsed_ids
    extra_parsed = parsed_ids - ref_ids

    missing_details = []
    for mid in sorted(missing):
        line_no = next((i for i, s in single_line if s == mid), None)
        reasons = idlike_fail_reasons(mid)
        ctx = []
        if line_no is not None:
            for j in range(max(0, line_no - 2), min(len(lines), line_no + 3)):
                marker = ">>>" if j == line_no else "   "
                ctx.append(f"  {marker} L{j}: {lines[j][:160]}")
        cause = "unknown"
        if any("len=" in r for r in reasons):
            cause = "Genetic ID exceeds 40-char idlike limit → filtered by strict idlike"
        elif any("invalid chars" in r for r in reasons):
            cause = "Genetic ID contains chars outside [A-Za-z0-9._+-] → filtered by strict idlike"
        elif not reasons:
            cause = ("Passes strict idlike — likely a multi-line record where "
                     "the parser's re-sync incorrectly split on an idlike-looking "
                     "continuation line")
        missing_details.append((mid, line_no, reasons, cause, ctx))

    # === 4. DUPLICATES ===
    parsed_list = [clean(d.split("\t")[0]) for d in data]
    dup_counter = Counter(parsed_list)
    duplicates = {k: v for k, v in dup_counter.items() if v > 1}

    # === 5. COUNTRY AUDIT ===
    col = resolve_columns(header)
    country_map = defaultdict(lambda: {"count": 0, "region": "", "analysis": 0})
    for rec in data:
        country = clean(g(rec, col["country"]))
        lat = to_float(g(rec, col["latitude"]))
        lon = to_float(g(rec, col["longitude"]))
        region = region_for(country, lat, lon)
        qc = norm_qc(g(rec, col["assessment"]))
        country_map[country]["count"] += 1
        country_map[country]["region"] = region
        if qc in ANALYSIS_QC:
            country_map[country]["analysis"] += 1

    unmapped = {
        c: i for c, i in country_map.items()
        if c and c not in COUNTRY_REGION and c not in EUROPE_CONTROL
    }

    # === 6. POPULATION × LAYER (target regions, analysis set) ===
    pop_layer = defaultdict(lambda: defaultdict(int))
    pop_meta = {}  # pop -> (region, country)
    for rec in data:
        pop = clean(g(rec, col["group_id"]))
        country = clean(g(rec, col["country"]))
        lat = to_float(g(rec, col["latitude"]))
        lon = to_float(g(rec, col["longitude"]))
        region = region_for(country, lat, lon)
        dmean = to_float(g(rec, col["date_mean_bp"]))
        layer = layer_from_bp(dmean)
        qc = norm_qc(g(rec, col["assessment"]))
        pop_meta[pop] = (region, country)
        if qc in ANALYSIS_QC:
            pop_layer[pop][layer] += 1

    # === 7. LOW-N CELLS ===
    reg_layer = defaultdict(lambda: defaultdict(int))
    for rec in data:
        country = clean(g(rec, col["country"]))
        lat = to_float(g(rec, col["latitude"]))
        lon = to_float(g(rec, col["longitude"]))
        region = region_for(country, lat, lon)
        dmean = to_float(g(rec, col["date_mean_bp"]))
        layer = layer_from_bp(dmean)
        qc = norm_qc(g(rec, col["assessment"]))
        if qc in ANALYSIS_QC:
            reg_layer[region][layer] += 1

    low_n_region = [
        (reg, lay, reg_layer[reg][lay])
        for reg in REGION_ORDER
        for lay in LAYER_ORDER
        if 0 < reg_layer[reg][lay] < 5
    ]
    empty_target = [
        (reg, lay)
        for reg in ["IBERIA", "MAGHREB", "LEVANT", "NORTH_AFRICA_EAST"]
        for lay in LAYER_ORDER
        if reg_layer[reg][lay] == 0
    ]
    low_n_pop = [
        (pop, pop_meta[pop][0], lay, pop_layer[pop][lay])
        for pop in sorted(pop_layer)
        if pop_meta[pop][0] in TARGET_REGIONS
        for lay in LAYER_ORDER
        if 0 < pop_layer[pop][lay] < 5
    ]

    # === 8. QC DISTRIBUTION ===
    qc_dist = Counter()
    for rec in data:
        qc_dist[norm_qc(g(rec, col["assessment"]))] += 1

    # === WRITE OUTPUTS ===
    os.makedirs(AUDIT_DIR, exist_ok=True)

    R = []
    R.append("=" * 72)
    R.append("GT-002.1 — COHORT AUDIT REPORT")
    R.append("=" * 72)
    R.append("")
    R.append(f"Source file   : {ANNO_PATH}")
    R.append(f"Columns (N)   : {N}")
    R.append(f"Physical lines: {total_physical:,}")
    R.append(f"Header end    : line {first_data}")
    R.append("")

    # --- 1. Missing rows ---
    R.append("-" * 72)
    R.append("1. MISSING ROWS DIAGNOSIS")
    R.append("-" * 72)
    R.append(f"Reference parser records (broad_idlike) : {len(ref_records):,}")
    R.append(f"Reference parser unique IDs            : {len(ref_ids):,}")
    R.append(f"Build script parser records (strict)   : {len(data):,}")
    R.append(f"Build script parser unique IDs         : {len(parsed_ids):,}")
    R.append(f"Missing (ref has, build script doesn't): {len(missing)}")
    R.append(f"Extra  (build has, ref doesn't)        : {len(extra_parsed)}")
    R.append("")
    R.append(f"Single-line records (broad, N fields)  : {len(single_line):,}")
    R.append(f"Single-line unique IDs                 : {len(unique_single):,}")
    R.append("")

    if missing_details:
        for mid, line_no, reasons, cause, ctx in missing_details:
            R.append(f"  ▸ Missing ID: {mid}")
            R.append(f"    Line: {line_no if line_no is not None else '(multi-line, not on single physical line)'}")
            if reasons:
                R.append(f"    idlike failure: {'; '.join(reasons)}")
            R.append(f"    → CAUSE: {cause}")
            if ctx:
                R.append("    Context:")
                R.extend(ctx)
            R.append("")
    else:
        R.append("  No missing rows from reference parser comparison.")
        R.append("  The discrepancy may be in the expected count or in")
        R.append("  multi-line records that neither parser captures.")
        R.append("")

    if extra_parsed:
        R.append(f"  Note: {len(extra_parsed)} IDs in build parser but not in ref parser.")
        R.append("  These may be multi-line records the build parser captured")
        R.append("  via idlike re-sync that the ref parser merged differently.")
        R.append("")

    # --- 2. Duplicates ---
    R.append("-" * 72)
    R.append("2. DUPLICATE GENETIC IDs (in build parser output)")
    R.append("-" * 72)
    if duplicates:
        for sid, count in sorted(duplicates.items(), key=lambda x: -x[1]):
            R.append(f"  {sid}: {count} occurrences")
    else:
        R.append("  None found.")
    R.append("")

    # --- 3. Country audit ---
    R.append("-" * 72)
    R.append("3. COUNTRY → REGION AUDIT")
    R.append("-" * 72)
    R.append(f"  Unique countries in data: {len(country_map)}")
    R.append(f"  Unmapped (not in COUNTRY_REGION / EUROPE_CONTROL): {len(unmapped)}")
    R.append("")
    if unmapped:
        R.append("  ⚠ UNMAPPED COUNTRIES (default → OUTGROUP — review if unexpected):")
        for c, i in sorted(unmapped.items(), key=lambda x: -x[1]['count']):
            R.append(f"    {c or '(blank)':35s} {i['count']:>6} → {i['region']}")
        R.append("")

    for treg in ["MAGHREB", "IBERIA", "LEVANT", "NORTH_AFRICA_EAST"]:
        countries = [(c, i) for c, i in country_map.items() if i["region"] == treg]
        countries.sort(key=lambda x: -x[1]["count"])
        total = sum(i["count"] for _, i in countries)
        analysis = sum(i["analysis"] for _, i in countries)
        R.append(f"  {treg} (total={total}, analysis={analysis}):")
        for c, i in countries:
            R.append(f"    {c:35s} {i['count']:>6}  (analysis: {i['analysis']})")
        R.append("")

    # --- 4. Low-N cells ---
    R.append("-" * 72)
    R.append("4. LOW-N CELLS (analysis set)")
    R.append("-" * 72)
    R.append("  Region × Layer — SPARSE (0 < n < 5):")
    if low_n_region:
        for reg, lay, n in low_n_region:
            R.append(f"    {reg:20s} × {lay}: n={n}")
    else:
        R.append("    (none)")
    R.append("")
    R.append("  Region × Layer — EMPTY (n=0), target regions:")
    for reg, lay in empty_target:
        R.append(f"    {reg:20s} × {lay}")
    R.append("")
    R.append("  Population × Layer — SPARSE (target regions, 0 < n < 5):")
    if low_n_pop:
        for pop, reg, lay, n in low_n_pop:
            R.append(f"    {pop:40s} ({reg}) × {lay}: n={n}")
    else:
        R.append("    (none)")
    R.append("")

    # --- 5. QC distribution ---
    R.append("-" * 72)
    R.append("5. QC DISTRIBUTION")
    R.append("-" * 72)
    for qc_val, count in qc_dist.most_common():
        R.append(f"  {qc_val or '(empty)':35s} {count:>6,}")
    n_elig = sum(v for k, v in qc_dist.items() if k in ANALYSIS_QC)
    R.append(f"  {'─' * 35} ──────")
    R.append(f"  {'QC-eligible total':35s} {n_elig:>6,}")
    R.append("")

    # --- 6. Files ---
    R.append("-" * 72)
    R.append("6. OUTPUT FILES")
    R.append("-" * 72)
    R.append("  GT-002.1.audit-report.txt  — this report")
    R.append("  GT-002.1.popxlayer.tsv     — population × layer (target regions)")
    R.append("  GT-002.1.low-N-cells.tsv   — all sparse/empty cells")
    R.append("")

    report_text = "\n".join(R)
    report_path = os.path.join(AUDIT_DIR, "GT-002.1.audit-report.txt")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_text)
    print(report_text)
    print(f"\n[audit] {report_path}")

    # --- Population × layer TSV (target regions, analysis set) ---
    tsv_path = os.path.join(AUDIT_DIR, "GT-002.1.popxlayer.tsv")
    with open(tsv_path, "w", encoding="utf-8") as f:
        f.write("population\tregion\tcountry\t"
                + "\t".join(LAYER_ORDER) + "\tTOTAL\n")
        for pop in sorted(pop_layer):
            reg, country = pop_meta[pop]
            if reg in TARGET_REGIONS:
                vals = [pop_layer[pop][lay] for lay in LAYER_ORDER]
                total = sum(vals)
                f.write(f"{pop}\t{reg}\t{country}\t"
                        + "\t".join(str(v) for v in vals)
                        + f"\t{total}\n")
    print(f"[audit] {tsv_path}")

    # --- Low-N cells TSV ---
    low_path = os.path.join(AUDIT_DIR, "GT-002.1.low-N-cells.tsv")
    with open(low_path, "w", encoding="utf-8") as f:
        f.write("type\tregion\tpopulation\tlayer\tn\n")
        for reg, lay, n in low_n_region:
            f.write(f"region_sparse\t{reg}\t\t{lay}\t{n}\n")
        for reg, lay in empty_target:
            f.write(f"region_empty\t{reg}\t\t{lay}\t0\n")
        for pop, reg, lay, n in low_n_pop:
            f.write(f"pop_sparse\t{reg}\t{pop}\t{lay}\t{n}\n")
    print(f"[audit] {low_path}")


if __name__ == "__main__":
    main()
