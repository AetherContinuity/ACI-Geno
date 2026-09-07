#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GT-002.2 — POPULATION INVENTORY & f4 TEST DESIGN
================================================
Reads the AADR v66.p1 .anno file, inventories ALL populations by region ×
time layer, identifies Mediterranean mediating-node populations (Italy,
Sicily, Sardinia, Greece, Balkans, Malta, Anatolia, Cyprus), and designs
the f4/D test battery for the network-based Western Mediterranean screen.

Outputs (to gt002/popinv/):
  GT-002.2.popinventory.tsv       — all populations per region × layer
  GT-002.2.mediterranean_pops.tsv — Mediterranean populations with n≥1
  GT-002.2.popmap.tsv             — sample_id → custom_pop_label (for ADMIXTOOLS2)
  GT-002.2.f4_tests.tsv            — f4 test design (pop1, pop2, pop3, pop4, phase)
  GT-002.2.pop_labels.tsv          — custom_pop_label → member populations + n
"""

import os
import sys
from collections import defaultdict, Counter

# Reuse build_cohort.py
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_cohort import (
    COUNTRY_REGION, EUROPE_CONTROL, ROLE, REGION_ORDER, LAYER_ORDER,
    ANALYSIS_QC, clean, to_float, layer_from_bp, norm_qc,
    region_for, idlike, resolve_columns, get_anno_text, parse_records, g,
    FALLBACK_NCOLS, ANNO_PATH,
)

OUT_DIR = "gt002/popinv"

# ---------------------------------------------------------------------------
# MEDITERRANEAN COUNTRY/GROUP PATTERNS — identifies mediating-node populations
# ---------------------------------------------------------------------------
# Italy is in EUROPE_CONTROL in COUNTRY_REGION, but for GT-002.2 we need it
# as a separate node. Same for Greece, Balkans, Malta, Anatolia.
# Sicily/Sardinia are usually under Italy in country but distinct in group_id.

ITALY_COUNTRIES = {"Italy", "San Marino", "Vatican", "Holy See"}
GREECE_COUNTRIES = {"Greece"}
BALKAN_COUNTRIES = {"Serbia", "Croatia", "Bosnia and Herzegovina",
                     "Albania", "North Macedonia", "Macedonia",
                     "Bulgaria", "Romania", "Montenegro", "Kosovo",
                     "Slovenia"}
MALTA_COUNTRIES = {"Malta"}
ANATOLIA_COUNTRIES = {"Turkey"}  # currently OUTGROUP in COUNTRY_REGION

# Island detection from group_id (case-insensitive substring match)
ISLAND_PATTERNS = {
    "SICILY":  ["sicily", "sicilia", "sicilia"],
    "SARDINIA": ["sardinia", "sardegna"],
    "CRETE":   ["crete", "cretan"],
    "CYPRUS":  ["cyprus"],
}

# NW / Central / Northern Europe subregions (from EUROPE_SUBREGION in build_cohort.py)
NW_EUROPE = {"France", "Monaco", "Belgium", "Netherlands", "Luxembourg",
             "United Kingdom", "UK", "Great Britain", "Britain", "England",
             "Scotland", "Wales", "Ireland", "Iceland"}
CENTRAL_EUROPE = {"Germany", "Switzerland", "Liechtenstein", "Austria",
                  "Czech Republic", "Czechia", "Slovakia", "Hungary", "Poland"}
NORTHERN_EUROPE = {"Sweden", "Norway", "Denmark", "Finland", "Estonia",
                   "Latvia", "Lithuania"}
EASTERN_EUROPE = {"Russia", "Ukraine", "Belarus", "Moldova"}


def detect_island(group_id, country):
    """Check if this sample is from an island (Sicily, Sardinia, etc.)."""
    gid_lower = (group_id or "").lower()
    for island, patterns in ISLAND_PATTERNS.items():
        for p in patterns:
            if p in gid_lower:
                return island
    return None


def med_node(country, group_id):
    """Classify a sample into a Mediterranean mediating-node category.
    Returns (node_name, is_mediterranean)."""
    c = clean(country)
    gid = clean(group_id)

    # Check islands first (by group_id pattern)
    island = detect_island(gid, c)
    if island:
        return island, True

    # Italy (but not Sicily/Sardinia — already caught above)
    if c in ITALY_COUNTRIES:
        return "ITALY", True

    # Greece
    if c in GREECE_COUNTRIES:
        return "GREECE", True

    # Balkans
    if c in BALKAN_COUNTRIES:
        return "BALKANS", True

    # Malta
    if c in MALTA_COUNTRIES:
        return "MALTA", True

    # Anatolia (Turkey — currently OUTGROUP but a potential mediating node)
    if c in ANATOLIA_COUNTRIES:
        return "ANATOLIA", True

    # Cyprus (already in LEVANT but also Mediterranean)
    if c == "Cyprus":
        return "CYPRUS", True

    return None, False


def europe_subgroup(country):
    """Classify European control country into subregion."""
    c = clean(country)
    if c in NW_EUROPE:
        return "EUROPE_NW"
    if c in CENTRAL_EUROPE:
        return "EUROPE_CENTRAL"
    if c in NORTHERN_EUROPE:
        return "EUROPE_NORTH"
    if c in EASTERN_EUROPE:
        return "EUROPE_EAST"
    return "EUROPE_OTHER"


def custom_pop_label(region, country, group_id, layer, qc_eligible):
    """Determine the custom population label for ADMIXTOOLS2.

    Target regions → {REGION}_{LAYER} (merged across populations)
    Mediterranean nodes → {NODE}_{LAYER} (Italy, Sicily, Sardinia, etc.)
    Europe control → {EUROPE_SUBGROUP}_{LAYER}
    Africa → {AFRICA_SUBREGION}_{LAYER}
    Outgroup → kept by subregion for flexibility

    Only analysis-eligible samples get labels; others get empty string.
    """
    if not qc_eligible:
        return ""

    # Check Mediterranean mediating nodes first
    node, is_med = med_node(country, group_id)
    if is_med and node:
        return f"{node}_{layer}"

    # Target regions (IBERIA, MAGHREB, LEVANT, NORTH_AFRICA_EAST)
    if region in ("IBERIA", "MAGHREB", "LEVANT", "NORTH_AFRICA_EAST"):
        return f"{region}_{layer}"

    # Africa
    if region == "WEST_AFRICA":
        return f"AFRICA_W_{layer}"
    if region == "EAST_AFRICA":
        return f"AFRICA_E_{layer}"

    # Europe control → by subregion
    if region == "EUROPE_CONTROL":
        sub = europe_subgroup(country)
        return f"{sub}_{layer}"

    # Outgroup → by subregion (for flexibility)
    return f"OUTGROUP_{layer}"


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    text = get_anno_text()
    header, data, N = parse_records(text)
    col = resolve_columns(header)

    # Build per-sample records
    samples = []
    for rec in data:
        sample_id = clean(g(rec, col["sample_id"]))
        if sample_id == "":
            continue
        group_id = clean(g(rec, col["group_id"]))
        country = clean(g(rec, col["country"]))
        lat = to_float(g(rec, col["latitude"]))
        lon = to_float(g(rec, col["longitude"]))
        dmean = to_float(g(rec, col["date_mean_bp"]))
        layer = layer_from_bp(dmean)
        qc = norm_qc(g(rec, col["assessment"]))
        qc_eligible = qc in ANALYSIS_QC
        region = region_for(country, lat, lon)
        label = custom_pop_label(region, country, group_id, layer, qc_eligible)

        node, is_med = med_node(country, group_id)

        samples.append({
            "sample_id": sample_id,
            "group_id": group_id,
            "country": country,
            "region": region,
            "layer": layer,
            "qc": qc,
            "qc_eligible": qc_eligible,
            "custom_label": label,
            "med_node": node or "",
            "is_mediterranean": is_med,
        })

    # === 1. POPULATION INVENTORY (all populations per region × layer) ===
    pop_inv = defaultdict(lambda: defaultdict(int))
    pop_meta = {}  # group_id → (region, country, med_node)
    for s in samples:
        if not s["qc_eligible"]:
            continue
        pop_inv[s["group_id"]][s["layer"]] += 1
        pop_meta[s["group_id"]] = (s["region"], s["country"], s["med_node"])

    inv_path = os.path.join(OUT_DIR, "GT-002.2.popinventory.tsv")
    with open(inv_path, "w") as f:
        f.write("group_id\tregion\tcountry\tmed_node\t"
                + "\t".join(LAYER_ORDER) + "\tTOTAL\n")
        for pop in sorted(pop_inv):
            reg, country, node = pop_meta[pop]
            vals = [pop_inv[pop].get(l, 0) for l in LAYER_ORDER]
            total = sum(vals)
            f.write(f"{pop}\t{reg}\t{country}\t{node}\t"
                    + "\t".join(str(v) for v in vals) + f"\t{total}\n")
    print(f"[prep] {inv_path} ({len(pop_inv)} populations)")

    # === 2. MEDITERRANEAN POPULATIONS ===
    med_pops = {}
    for s in samples:
        if not s["qc_eligible"] or not s["is_mediterranean"]:
            continue
        if s["group_id"] not in med_pops:
            med_pops[s["group_id"]] = {
                "node": s["med_node"],
                "country": s["country"],
                "region": s["region"],
                "layers": defaultdict(int),
            }
        med_pops[s["group_id"]]["layers"][s["layer"]] += 1

    med_path = os.path.join(OUT_DIR, "GT-002.2.mediterranean_pops.tsv")
    with open(med_path, "w") as f:
        f.write("group_id\tmed_node\tcountry\tregion\t"
                + "\t".join(LAYER_ORDER) + "\tTOTAL\n")
        for pop in sorted(med_pops, key=lambda p: (med_pops[p]["node"], -sum(med_pops[p]["layers"].values()))):
            info = med_pops[pop]
            vals = [info["layers"].get(l, 0) for l in LAYER_ORDER]
            total = sum(vals)
            f.write(f"{pop}\t{info['node']}\t{info['country']}\t{info['region']}\t"
                    + "\t".join(str(v) for v in vals) + f"\t{total}\n")
    print(f"[prep] {med_path} ({len(med_pops)} Mediterranean populations)")

    # === 3. POPULATION MAP (sample_id → custom_pop_label) ===
    popmap_path = os.path.join(OUT_DIR, "GT-002.2.popmap.tsv")
    n_mapped = 0
    with open(popmap_path, "w") as f:
        f.write("sample_id\tcustom_pop_label\tgroup_id\tregion\tlayer\tqc\n")
        for s in samples:
            if not s["qc_eligible"] or not s["custom_label"]:
                continue
            f.write(f"{s['sample_id']}\t{s['custom_label']}\t{s['group_id']}\t"
                    f"{s['region']}\t{s['layer']}\t{s['qc']}\n")
            n_mapped += 1
    print(f"[prep] {popmap_path} ({n_mapped} mapped samples)")

    # === 4. POPULATION LABELS SUMMARY (custom_label → members + n) ===
    label_counts = defaultdict(lambda: {"n": 0, "pops": set()})
    for s in samples:
        if not s["qc_eligible"] or not s["custom_label"]:
            continue
        label_counts[s["custom_label"]]["n"] += 1
        label_counts[s["custom_label"]]["pops"].add(s["group_id"])

    labels_path = os.path.join(OUT_DIR, "GT-002.2.pop_labels.tsv")
    with open(labels_path, "w") as f:
        f.write("custom_pop_label\tn_samples\tn_populations\tpopulations\n")
        for label in sorted(label_counts):
            info = label_counts[label]
            pops = "; ".join(sorted(info["pops"]))
            f.write(f"{label}\t{info['n']}\t{len(info['pops'])}\t{pops}\n")
    print(f"[prep] {labels_path} ({len(label_counts)} custom labels)")

    # === 5. f4 TEST DESIGN ===
    # Identify which custom labels have n ≥ 5 (usable) vs n < 5 (exploratory)
    usable = {l for l, info in label_counts.items() if info["n"] >= 5}
    all_labels = set(label_counts.keys())

    # Population groups for f4 tests
    maghreb = [f"MAGHREB_{l}" for l in ["T0", "T1", "T2", "T3"] if f"MAGHREB_{l}" in all_labels]
    iberia  = [f"IBERIA_{l}" for l in ["T0", "T1", "T2", "T3"] if f"IBERIA_{l}" in all_labels]
    levant  = [f"LEVANT_{l}" for l in ["T0", "T1", "T2", "T3"] if f"LEVANT_{l}" in all_labels]
    nae     = [f"NORTH_AFRICA_EAST_{l}" for l in ["T0"] if f"NORTH_AFRICA_EAST_{l}" in all_labels]

    # Mediterranean nodes
    italy    = [l for l in all_labels if l.startswith("ITALY_")]
    sicily   = [l for l in all_labels if l.startswith("SICILY_")]
    sardinia = [l for l in all_labels if l.startswith("SARDINIA_")]
    greece   = [l for l in all_labels if l.startswith("GREECE_")]
    balkans  = [l for l in all_labels if l.startswith("BALKANS_")]
    malta    = [l for l in all_labels if l.startswith("MALTA_")]
    anatolia = [l for l in all_labels if l.startswith("ANATOLIA_")]

    # Europe controls
    europe_nw = [l for l in all_labels if l.startswith("EUROPE_NW_")]
    europe_central = [l for l in all_labels if l.startswith("EUROPE_CENTRAL_")]

    # Africa
    africa_w = [l for l in all_labels if l.startswith("AFRICA_W_")]
    africa_e = [l for l in all_labels if l.startswith("AFRICA_E_")]

    # Outgroup (use Mbuti-like or SSA)
    outgroup = africa_w + africa_e  # use as outgroup baseline

    tests = []

    def add_test(pop1, pop2, pop3, pop4, phase, description):
        """Add an f4 test if all 4 populations are available."""
        if all(p in all_labels for p in [pop1, pop2, pop3, pop4]):
            usable_flag = "YES" if all(p in usable for p in [pop1, pop2, pop3, pop4]) else "PARTIAL"
            tests.append({
                "pop1": pop1, "pop2": pop2, "pop3": pop3, "pop4": pop4,
                "phase": phase, "description": description,
                "usable": usable_flag,
            })

    # --- PHASE A: f4(Maghreb, Africa; Iberia, X) ---
    # X rotates through Mediterranean nodes + Levant + Europe
    x_candidates = []
    for node_list, node_name in [
        (levant, "LEVANT"), (italy, "ITALY"), (sicily, "SICILY"),
        (sardinia, "SARDINIA"), (greece, "GREECE"), (balkans, "BALKANS"),
        (malta, "MALTA"), (anatolia, "ANATOLIA"),
        (europe_nw, "EUROPE_NW"), (europe_central, "EUROPE_CENTRAL"),
    ]:
        x_candidates.extend(node_list)

    for mgh in maghreb:
        for iber in iberia:
            # Need same time layer for meaningful comparison
            m_layer = mgh.split("_")[-1]
            i_layer = iber.split("_")[-1]
            for x in x_candidates:
                x_layer = x.split("_")[-1]
                # Phase A: match layers where possible, but also cross-layer
                if x_layer == m_layer or x_layer == i_layer:
                    add_test(mgh, "AFRICA_W_T0", iber, x, "A",
                             f"f4({mgh}, Africa; {iber}, {x})")
            # Also add cross-layer (Maghreb T0 vs Iberia T2, etc.)
            if m_layer != i_layer:
                for x in x_candidates:
                    add_test(mgh, "AFRICA_W_T0", iber, x, "A_cross",
                             f"f4({mgh}, Africa; {iber}, {x}) [cross-layer]")

    # --- PHASE B: Time-stratified (same-layer Maghreb-Iberia-X) ---
    for layer in ["T0", "T1", "T2", "T3"]:
        mgh = f"MAGHREB_{layer}"
        iber = f"IBERIA_{layer}"
        if mgh not in all_labels or iber not in all_labels:
            continue
        for x_node_list, x_name in [
            (levant, "LEVANT"), (italy, "ITALY"), (sicily, "SICILY"),
            (sardinia, "SARDINIA"), (greece, "GREECE"), (balkans, "BALKANS"),
        ]:
            x = f"{x_name.split('_')[0]}_{layer}"  # e.g., LEVANT_T0
            # Try both the node-specific and the general label
            for x_candidate in x_node_list:
                if x_candidate.endswith(layer):
                    add_test(mgh, "AFRICA_W_T0", iber, x_candidate, "B",
                             f"f4({mgh}, Africa; {iber}, {x_candidate}) [same-layer]")
                    break

    # --- PHASE C: Alternative route controls ---
    # f4(Maghreb, Africa; Italy, X) — does signal go through Italy?
    # f4(Italy, Africa; Iberia, X) — is there direct Italy-Iberia?
    # f4(Maghreb, Africa; Levant, X) — Levant route?
    for mgh in maghreb:
        for ita in italy + sicily + sardinia:
            for x in levant + europe_nw + greece + balkans:
                add_test(mgh, "AFRICA_W_T0", ita, x, "C_route",
                         f"f4({mgh}, Africa; {ita}, {x}) [route via Italy]")
        for lev in levant:
            for x in iberia + italy + europe_nw:
                add_test(mgh, "AFRICA_W_T0", lev, x, "C_route",
                         f"f4({mgh}, Africa; {lev}, {x}) [route via Levant]")

    # f4(Italy, Africa; Iberia, X) — Italy as source for Iberia?
    for ita in italy + sicily + sardinia:
        for iber in iberia:
            for x in levant + europe_nw + greece:
                add_test(ita, "AFRICA_W_T0", iber, x, "C_reverse",
                         f"f4({ita}, Africa; {iber}, {x}) [Italy→Iberia?]")

    # --- PHASE D: N_AFRICA_EAST controls ---
    for nae_pop in nae:
        for iber in iberia:
            for x in levant + italy + africa_w:
                add_test(nae_pop, "AFRICA_W_T0", iber, x, "D_nae",
                         f"f4({nae_pop}, Africa; {iber}, {x}) [N.Africa.E control]")

    # Write f4 test design
    tests_path = os.path.join(OUT_DIR, "GT-002.2.f4_tests.tsv")
    with open(tests_path, "w") as f:
        f.write("pop1\tpop2\tpop3\tpop4\tphase\tdescription\tusable\n")
        for t in tests:
            f.write(f"{t['pop1']}\t{t['pop2']}\t{t['pop3']}\t{t['pop4']}\t"
                    f"{t['phase']}\t{t['description']}\t{t['usable']}\n")
    print(f"[prep] {tests_path} ({len(tests)} f4 tests designed)")

    # Summary
    print("\n=== GT-002.2 PREP SUMMARY ===")
    print(f"Total analysis-eligible samples: {n_mapped}")
    print(f"Custom population labels: {len(label_counts)}")
    print(f"Labels with n≥5 (usable): {len(usable)}")
    print(f"Labels with n<5 (exploratory): {len(all_labels) - len(usable)}")
    print(f"f4 tests designed: {len(tests)}")
    print(f"  Phase A (direct W-Med): {sum(1 for t in tests if t['phase']=='A')}")
    print(f"  Phase A (cross-layer): {sum(1 for t in tests if t['phase']=='A_cross')}")
    print(f"  Phase B (time-stratified): {sum(1 for t in tests if t['phase']=='B')}")
    print(f"  Phase C (route controls): {sum(1 for t in tests if t['phase'].startswith('C'))}")
    print(f"  Phase D (N.Africa.E): {sum(1 for t in tests if t['phase']=='D_nae')}")

    # Mediterranean node summary
    print("\nMediterranean mediating nodes:")
    for node_name, node_labels in [
        ("ITALY", italy), ("SICILY", sicily), ("SARDINIA", sardinia),
        ("GREECE", greece), ("BALKANS", balkans), ("MALTA", malta),
        ("ANATOLIA", anatolia),
    ]:
        if node_labels:
            for l in node_labels:
                n = label_counts.get(l, {}).get("n", 0)
                flag = "✓" if l in usable else "△" if n > 0 else "✗"
                print(f"  {flag} {l}: n={n}")
        else:
            print(f"  ✗ {node_name}: NO DATA")

    # Target region summary
    print("\nTarget populations (region × layer):")
    for reg in ["MAGHREB", "IBERIA", "LEVANT", "NORTH_AFRICA_EAST"]:
        for layer in ["T0", "T1", "T2", "T3"]:
            label = f"{reg}_{layer}"
            n = label_counts.get(label, {}).get("n", 0)
            flag = "✓" if label in usable else "△" if n > 0 else "✗"
            print(f"  {flag} {label}: n={n}")


if __name__ == "__main__":
    main()
