#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GT-002 AADR V66.p1 COHORT BUILDER
=================================
Reproducibly derives the GT-002 sample cohort from the Allen Ancient DNA Resource
(AADR) v66.p1 .anno file (1240K public release).

PROVENANCE
  AADR version : v66.p1  (Harvard Dataverse, versionNumber 14, released 2026-06-08)
  Source file  : v66.p1_1240K.aadr.PUB.anno
  Dataverse DOI: https://doi.org/10.7910/DVN/FFIDCW
  Expected size: 13,443,726 bytes ; 49 columns ; ~23,089 individuals
  License      : CC0 1.0
  Citation     : Mallick, S. & Reich, D. The Allen Ancient DNA Resource (AADR):
                 A curated compendium of ancient human genomes, v66.p1 (2026-06-08).
                 Harvard Dataverse.  + the AADR Scientific Data paper (2024).

HOW TO RUN (phone, no install)
  1. Open https://colab.research.google.com in your phone browser (needs a Google
     account). Create a new notebook.
  2. Paste this whole file into one code cell.
  3. Run the cell (Run all). It downloads the .anno directly from your GitHub
     raw URL, builds the cohort, and writes 5 TSV files into the Colab working
     directory. Use the left-side file browser (folder icon) to download them.
  This is pure standard library Python 3 - no pip installs needed.
  You can also run it on any machine: set ANNO_PATH to a local .anno file and it
  will skip the download.

GT-002 SCHEMA (region = conservative GEOGRAPHIC classification, not genetic)
  regions : IBERIA | MAGHREB | LEVANT | NORTH_AFRICA_EAST | EUROPE_CONTROL |
            WEST_AFRICA | EAST_AFRICA | OUTGROUP
  NOTE    : Libya is kept as its own NORTH_AFRICA_EAST group (NOT auto-folded into
            Maghreb) - the Maghreb-vs-Libya distinction is exactly the assumption
            GT-002 is testing, so it must not be baked in. Egypt & Sudan are also
            placed in NORTH_AFRICA_EAST (eastern North Africa); edit if you differ.
  time layers (from date_mean_bp, half-open intervals, lower-inclusive):
    T0 [0,2000)  T1 [2000,6000)  T2 [6000,12000)  T3 [12000,20000)
    T4 [20000,50000)  T5 [50000,100000)  T6 [100000,inf)  UNDATED (no date)
  QC       : ASSESSMENT kept for every candidate. Analysis set = {PASS,
            PROVISIONAL_PASS}. QUESTIONABLE / CRITICAL stay in the review pool.

OUTPUTS (written next to the script / Colab working dir)
  GT-002.samples.tsv            - all candidates, 15-col GT-002 schema (+assessment)
  GT-002.samples.all.tsv        - all candidates + extra raw AADR cols + qc_eligible
  GT-002.samples.analysis.tsv   - QC-eligible subset (PASS / PROVISIONAL_PASS)
  GT-002.population-map.tsv     - per-sample region/layer classification
  GT-002.counts.regionxlayer.tsv- region x layer count matrix (analysis set)
  GT-002.counts.regionxlayer.all.tsv - same matrix, all candidates
"""

import os
import sys
import re
import csv
import io
import hashlib
import urllib.request
from collections import Counter, defaultdict

# ----------------------------------------------------------------------------
# CONFIG
# ----------------------------------------------------------------------------
# Raw .anno from the public GitHub repo (works in Colab / any internet host).
ANNO_URL = "https://raw.githubusercontent.com/AetherContinuity/ACI-Geno/main/v66.p1_1240K.aadr.PUB.anno"
# If you have the file locally, set this to its path and the download is skipped.
ANNO_PATH = "v66.p1_1240K.aadr.PUB.anno"   # repo-local .anno (checked out by Actions)
OUT_DIR = "gt002/output"   # outputs committed back to the repo
EXPECTED_SIZE = 13443726  # bytes, official v66.p1 1240K .anno size
# Known column count for v66.p1 .anno (auto-detected at runtime; this is a fallback).
FALLBACK_NCOLS = 49

# ----------------------------------------------------------------------------
# REGION CLASSIFICATION (geographic). Edit this single dictionary to reclassify.
# ----------------------------------------------------------------------------
COUNTRY_REGION = {
    # IBERIA
    "Spain": "IBERIA", "Portugal": "IBERIA", "Andorra": "IBERIA", "Gibraltar": "IBERIA",
    # MAGHREB (Libya deliberately NOT here)
    "Morocco": "MAGHREB", "Algeria": "MAGHREB", "Tunisia": "MAGHREB",
    "Western Sahara": "MAGHREB", "Mauritania": "MAGHREB",
    # LEVANT
    "Israel": "LEVANT", "Palestine": "LEVANT", "Palestinian Territory": "LEVANT",
    "Palestinian Territories": "LEVANT", "West Bank": "LEVANT", "Gaza": "LEVANT",
    "Jordan": "LEVANT", "Lebanon": "LEVANT", "Syria": "LEVANT", "Cyprus": "LEVANT",
    # NORTH_AFRICA_EAST (Libya kept separate; Egypt/Sudan = eastern N. Africa)
    "Libya": "NORTH_AFRICA_EAST", "Egypt": "NORTH_AFRICA_EAST", "Sudan": "NORTH_AFRICA_EAST",
    # WEST_AFRICA
    "Nigeria": "WEST_AFRICA", "Senegal": "WEST_AFRICA", "Gambia": "WEST_AFRICA",
    "Guinea": "WEST_AFRICA", "Guinea-Bissau": "WEST_AFRICA", "Sierra Leone": "WEST_AFRICA",
    "Liberia": "WEST_AFRICA", "Ivory Coast": "WEST_AFRICA", "Cote dIvoire": "WEST_AFRICA",
    "Côte d'Ivoire": "WEST_AFRICA", "Ghana": "WEST_AFRICA", "Togo": "WEST_AFRICA",
    "Benin": "WEST_AFRICA", "Burkina Faso": "WEST_AFRICA", "Niger": "WEST_AFRICA",
    "Mali": "WEST_AFRICA", "Cape Verde": "WEST_AFRICA", "Cabo Verde": "WEST_AFRICA",
    "Cameroon": "WEST_AFRICA", "Equatorial Guinea": "WEST_AFRICA", "Gabon": "WEST_AFRICA",
    "Congo": "WEST_AFRICA", "Republic of the Congo": "WEST_AFRICA",
    "Democratic Republic of the Congo": "WEST_AFRICA", "DR Congo": "WEST_AFRICA",
    # EAST_AFRICA
    "Ethiopia": "EAST_AFRICA", "Eritrea": "EAST_AFRICA", "Djibouti": "EAST_AFRICA",
    "Somalia": "EAST_AFRICA", "Kenya": "EAST_AFRICA", "Uganda": "EAST_AFRICA",
    "Tanzania": "EAST_AFRICA", "Rwanda": "EAST_AFRICA", "Burundi": "EAST_AFRICA",
    "South Sudan": "EAST_AFRICA", "Mozambique": "EAST_AFRICA", "Zambia": "EAST_AFRICA",
    "Malawi": "EAST_AFRICA", "Zimbabwe": "EAST_AFRICA", "Madagascar": "EAST_AFRICA",
}

# European countries (minus Iberia) -> EUROPE_CONTROL
EUROPE_CONTROL = {
    "Italy", "San Marino", "Vatican", "Holy See", "Malta", "France", "Monaco",
    "Germany", "Belgium", "Netherlands", "Luxembourg", "Switzerland", "Liechtenstein",
    "Austria", "Czech Republic", "Czechia", "Slovakia", "Hungary", "Poland",
    "Slovenia", "Croatia", "Serbia", "Bosnia and Herzegovina", "Montenegro",
    "Kosovo", "Albania", "North Macedonia", "Macedonia", "Greece", "Bulgaria",
    "Romania", "Moldova", "Ukraine", "Belarus", "Russia", "Estonia", "Latvia",
    "Lithuania", "Finland", "Sweden", "Norway", "Denmark", "Iceland", "Ireland",
    "United Kingdom", "UK", "Great Britain", "Britain", "England", "Scotland",
    "Wales", "Svalbard",
}

# Subregion (finer geographic label within region)
EUROPE_SUBREGION = {
    "Italy": "Southern_Europe", "San Marino": "Southern_Europe", "Vatican": "Southern_Europe",
    "Holy See": "Southern_Europe", "Malta": "Southern_Europe", "Greece": "Southern_Europe",
    "France": "NW_Europe", "Monaco": "NW_Europe", "Belgium": "NW_Europe",
    "Netherlands": "NW_Europe", "Luxembourg": "NW_Europe", "United Kingdom": "British_Isles",
    "UK": "British_Isles", "Great Britain": "British_Isles", "Britain": "British_Isles",
    "England": "British_Isles", "Scotland": "British_Isles", "Wales": "British_Isles",
    "Ireland": "British_Isles", "Iceland": "British_Isles",
    "Germany": "Central_Europe", "Switzerland": "Central_Europe",
    "Liechtenstein": "Central_Europe", "Austria": "Central_Europe",
    "Czech Republic": "Central_Europe", "Czechia": "Central_Europe",
    "Slovakia": "Central_Europe", "Hungary": "Central_Europe", "Poland": "Central_Europe",
    "Slovenia": "Balkans", "Croatia": "Balkans", "Serbia": "Balkans",
    "Bosnia and Herzegovina": "Balkans", "Montenegro": "Balkans", "Kosovo": "Balkans",
    "Albania": "Balkans", "North Macedonia": "Balkans", "Macedonia": "Balkans",
    "Bulgaria": "Balkans", "Romania": "Balkans",
    "Sweden": "Northern_Europe", "Norway": "Northern_Europe", "Denmark": "Northern_Europe",
    "Finland": "Northern_Europe", "Estonia": "Northern_Europe", "Latvia": "Northern_Europe",
    "Lithuania": "Northern_Europe",
    "Russia": "Eastern_Europe", "Ukraine": "Eastern_Europe", "Belarus": "Eastern_Europe",
    "Moldova": "Eastern_Europe",
}

# Continent label for OUTGROUP countries (coarse)
OUTGROUP_SUBREGION = {
    "Turkey": "Anatolia", "Georgia": "Caucasus", "Armenia": "Caucasus",
    "Azerbaijan": "Caucasus", "Iran": "Iran", "Iraq": "Mesopotamia",
    "Saudi Arabia": "Arabia", "Yemen": "Arabia", "Oman": "Arabia",
    "United Arab Emirates": "Arabia", "Qatar": "Arabia", "Kuwait": "Arabia",
    "Bahrain": "Arabia", "Jordan": "Levant",
    "Kazakhstan": "Central_Asia", "Uzbekistan": "Central_Asia",
    "Turkmenistan": "Central_Asia", "Kyrgyzstan": "Central_Asia",
    "Tajikistan": "Central_Asia", "Afghanistan": "Central_Asia",
    "Pakistan": "South_Asia", "India": "South_Asia", "Sri Lanka": "South_Asia",
    "Nepal": "South_Asia", "Bangladesh": "South_Asia",
    "China": "East_Asia", "Mongolia": "East_Asia", "Japan": "East_Asia",
    "North Korea": "East_Asia", "South Korea": "East_Asia", "Taiwan": "East_Asia",
    "Vietnam": "SE_Asia", "Thailand": "SE_Asia", "Laos": "SE_Asia",
    "Cambodia": "SE_Asia", "Myanmar": "SE_Asia", "Malaysia": "SE_Asia",
    "Indonesia": "SE_Asia", "Philippines": "SE_Asia",
    "Russia": "Siberia",
    "United States": "Americas", "USA": "Americas", "Canada": "Americas",
    "Mexico": "Americas", "Guatemala": "Americas", "Belize": "Americas",
    "Honduras": "Americas", "El Salvador": "Americas", "Nicaragua": "Americas",
    "Costa Rica": "Americas", "Panama": "Americas", "Colombia": "Americas",
    "Venezuela": "Americas", "Ecuador": "Americas", "Peru": "Americas",
    "Bolivia": "Americas", "Chile": "Americas", "Argentina": "Americas",
    "Brazil": "Americas", "Paraguay": "Americas", "Uruguay": "Americas",
    "Australia": "Oceania", "New Zealand": "Oceania", "Papua New Guinea": "Oceania",
    "Greenland": "Arctic",
}

ROLE = {
    "IBERIA": "TARGET", "MAGHREB": "TARGET", "LEVANT": "TARGET",
    "NORTH_AFRICA_EAST": "TARGET",
    "EUROPE_CONTROL": "CONTROL",
    "WEST_AFRICA": "OUTGROUP", "EAST_AFRICA": "OUTGROUP", "OUTGROUP": "OUTGROUP",
}

# Conservative bounding boxes for lat/lon fallback (only used when country unknown)
COORD_BOXES = [
    ("IBERIA",          36.0, 44.0,  -9.5,  3.5),
    ("LEVANT",           29.0, 37.5,  34.0, 42.0),
    ("NORTH_AFRICA_EAST",16.0, 32.5,  25.0, 38.0),
    ("MAGHREB",          20.0, 37.5, -17.0, -1.0),
    ("WEST_AFRICA",      -5.0, 18.0, -17.0, 16.0),
    ("EAST_AFRICA",     -12.0, 18.0,  28.0, 48.0),
]

REGION_ORDER = ["IBERIA", "MAGHREB", "LEVANT", "NORTH_AFRICA_EAST",
                "EUROPE_CONTROL", "WEST_AFRICA", "EAST_AFRICA", "OUTGROUP"]
LAYER_ORDER = ["T0", "T1", "T2", "T3", "T4", "T5", "T6", "UNDATED"]
ANALYSIS_QC = {"PASS", "PROVISIONAL_PASS"}


# ----------------------------------------------------------------------------
# HELPERS
# ----------------------------------------------------------------------------
def clean(v):
    """Strip surrounding double quotes and turn AADR '..' (missing) into ''."""
    if v is None:
        return ""
    v = v.strip()
    if len(v) >= 2 and v[0] == '"' and v[-1] == '"':
        v = v[1:-1]
    if v == "..":
        return ""
    return v


def to_float(v):
    v = clean(v)
    if v == "":
        return None
    try:
        return float(v)
    except ValueError:
        return None


def layer_from_bp(bp):
    if bp is None:
        return "UNDATED"
    if bp < 2000:
        return "T0"
    if bp < 6000:
        return "T1"
    if bp < 12000:
        return "T2"
    if bp < 20000:
        return "T3"
    if bp < 50000:
        return "T4"
    if bp < 100000:
        return "T5"
    return "T6"


def norm_qc(assessment):
    a = clean(assessment).upper()
    a = a.split(";")[0].strip()      # take leading token if ';'-joined
    return a.replace(" ", "_")        # PROVISIONAL PASS -> PROVISIONAL_PASS


def region_for(country, lat=None, lon=None):
    c = clean(country)
    if c in COUNTRY_REGION:
        return COUNTRY_REGION[c]
    if c in EUROPE_CONTROL:
        return "EUROPE_CONTROL"
    # lat/lon fallback only when country is blank/unknown
    if c == "" and lat is not None and lon is not None:
        for name, lat0, lat1, lon0, lon1 in COORD_BOXES:
            if lat0 <= lat <= lat1 and lon0 <= lon <= lon1:
                return name
    return "OUTGROUP"


def subregion_for(region, country):
    c = clean(country)
    if region == "IBERIA":
        return "Iberia"
    if region == "LEVANT":
        return "Levant"
    if region == "MAGHREB":
        return c or "Maghreb"
    if region == "NORTH_AFRICA_EAST":
        return c or "North_Africa_East"
    if region in ("WEST_AFRICA", "EAST_AFRICA"):
        return region.title()  # West_Africa / East_Africa
    if region == "EUROPE_CONTROL":
        return EUROPE_SUBREGION.get(c, "Europe_other")
    if region == "OUTGROUP":
        return OUTGROUP_SUBREGION.get(c, "Other")
    return region


# ----------------------------------------------------------------------------
# DOWNLOAD
# ----------------------------------------------------------------------------
def get_anno_text():
    if ANNO_PATH and os.path.exists(ANNO_PATH):
        print(f"[anno] using local file: {ANNO_PATH}")
        with open(ANNO_PATH, "rb") as f:
            data = f.read()
    else:
        print(f"[anno] downloading from:\n  {ANNO_URL}")
        req = urllib.request.Request(ANNO_URL, headers={"User-Agent": "GT-002-builder/1.0"})
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = resp.read()
        print(f"[anno] downloaded {len(data):,} bytes")
    if len(data) != EXPECTED_SIZE:
        print(f"[anno] WARNING: size {len(data):,} != expected {EXPECTED_SIZE:,}. "
              f"Proceeding anyway - verify provenance.")
    md5 = hashlib.md5(data).hexdigest()
    print(f"[anno] md5 = {md5}")
    return data.decode("utf-8", errors="replace")


# ----------------------------------------------------------------------------
# PARSE  (header spans several physical lines; data rows start with a Genetic ID)
# ----------------------------------------------------------------------------
def idlike(s):
    """True if s looks like an AADR Genetic ID (not header prose / a fragment)."""
    s = (s or "").strip()
    if not s or len(s) > 40:
        return False
    if s.startswith("Genetic ID"):
        return False
    # Genetic IDs are short tokens with no spaces, and always contain a letter.
    if not re.match(r"^[A-Za-z0-9._+\-]+$", s):
        return False
    if not re.search(r"[A-Za-z]", s):
        return False
    return True


def parse_records(text):
    """Parse AADR .anno text into (header_fields, data_records, N).

    Uses csv.reader to properly handle double-quoted fields that contain
    embedded newlines — the #1 cause of dropped records in v66.p1 which
    has ~23k samples but the old manual tab-splitter only found ~3.4k.
    """
    reader = csv.reader(io.StringIO(text), delimiter='\t', quotechar='"')
    rows = list(reader)
    if not rows:
        return [], [], FALLBACK_NCOLS

    # Auto-detect column count N = most common field count among "wide" rows.
    cnt = Counter(len(r) for r in rows)
    wide = {k: v for k, v in cnt.items() if k >= 20}
    N = max(wide, key=wide.get) if wide else FALLBACK_NCOLS
    print(f"[parse] detected column count N = {N} (from field-count mode)")

    # The header may span several logical rows (long descriptions with embedded
    # newlines). Every data record STARTS with a Genetic ID, so the first row
    # whose first field looks like a Genetic ID marks the start of data.
    first_data = -1
    for i, row in enumerate(rows):
        if row and idlike(row[0]):
            first_data = i
            break
    if first_data < 0:
        print("[parse] WARNING: no Genetic-ID-like row found; row 0 treated as header")
        first_data = 0

    # Header: flatten all pre-data rows into one field list
    header_fields = []
    for row in rows[:first_data]:
        header_fields.extend(row)
    print(f"[parse] header = rows [0:{first_data}] -> {len(header_fields)} fields")

    # Data: keep only N-field rows that start with a Genetic ID.
    # csv.reader already assembled multi-line quoted fields, so each row
    # is a complete record — no manual buffering needed.
    data = ["\t".join(row) for row in rows[first_data:]
            if len(row) == N and idlike(row[0])]
    print(f"[parse] assembled {len(data):,} data records")
    return header_fields, data, N


# ----------------------------------------------------------------------------
# COLUMN RESOLUTION  (match by header description keywords - index-agnostic)
# ----------------------------------------------------------------------------
def find_col(header, *must_contain, exact=False, startswith=False):
    targets = [s.lower() for s in must_contain]
    for i, name in enumerate(header):
        nl = name.strip().lower()
        if exact and nl in targets:
            return i
        if startswith and any(nl.startswith(t) for t in targets):
            return i
        if not exact and not startswith and all(t in nl for t in targets):
            return i
    return None


def resolve_columns(header):
    R = {}
    R["sample_id"] = find_col(header, "genetic id", startswith=True)
    # Master ID preferred; fall back to Individual ID
    R["master_id"] = find_col(header, "master id") or find_col(header, "individual id", startswith=True)
    R["group_id"] = find_col(header, "group id", exact=True) or find_col(header, "group id", startswith=True)
    # population: prefer a column literally named 'Population', else reuse Group ID
    R["population"] = find_col(header, "population", exact=True) or find_col(header, "population", startswith=True)
    if R["population"] is None:
        R["population"] = R["group_id"]
    R["country"] = find_col(header, "political entity", startswith=True)
    R["latitude"] = find_col(header, "latitude", startswith=True)
    R["longitude"] = find_col(header, "longitude", startswith=True)
    R["date_mean_bp"] = find_col(header, "date mean", "bp")
    R["date_sd_bp"] = find_col(header, "date standard deviation")
    R["assessment"] = find_col(header, "assessment", exact=True) or find_col(header, "assessment", startswith=True)
    # 1240K SNP count: prefer the column mentioning 1240K, else first 'snps hit on autosomal targets'
    snp1240 = find_col(header, "snps hit on autosomal targets", "1240k")
    R["snps_1240k"] = snp1240 or find_col(header, "snps hit on autosomal targets")
    # extras for the .all.tsv
    R["publication"] = find_col(header, "publication abbreviation", startswith=True)
    R["doi"] = find_col(header, "doi for publication", startswith=True) or find_col(header, "doi", startswith=True)
    R["full_date"] = find_col(header, "full date", startswith=True)
    R["assessment_warnings"] = find_col(header, "assessment warnings", startswith=True)
    print("[parse] resolved column indices:")
    for k, v in R.items():
        print(f"   {k:20s} -> {v}")
    missing = [k for k, v in R.items() if v is None and k in
               ("sample_id", "group_id", "country", "latitude", "longitude",
                "date_mean_bp", "assessment", "snps_1240k")]
    if missing:
        print(f"[parse] WARNING: could not resolve required columns: {missing}")
    return R


def g(rec, idx):
    if idx is None:
        return ""
    parts = rec.split("\t")
    return parts[idx] if idx < len(parts) else ""


# ----------------------------------------------------------------------------
# BUILD COHORT
# ----------------------------------------------------------------------------
def build():
    text = get_anno_text()
    header, data, N = parse_records(text)
    if not data:
        print("[build] no data records parsed - aborting.")
        return
    if len(header) != N:
        print(f"[build] note: header field count {len(header)} (record N={N})")
    col = resolve_columns(header)

    rows = []  # each: dict of GT-002 fields + extras
    for rec in data:
        f = rec.split("\t")
        if len(f) < N:
            continue
        sample_id = clean(g(rec, col["sample_id"]))
        if sample_id == "":
            continue
        country = clean(g(rec, col["country"]))
        lat = to_float(g(rec, col["latitude"]))
        lon = to_float(g(rec, col["longitude"]))
        dmean = to_float(g(rec, col["date_mean_bp"]))
        dsd = to_float(g(rec, col["date_sd_bp"]))
        snps = clean(g(rec, col["snps_1240k"]))
        assessment_raw = g(rec, col["assessment"])
        qc = norm_qc(assessment_raw)
        eligible = qc in ANALYSIS_QC
        region = region_for(country, lat, lon)
        sub = subregion_for(region, country)
        layer = layer_from_bp(dmean)
        role = ROLE.get(region, "OUTGROUP")
        rows.append({
            "sample_id": sample_id,
            "master_id": clean(g(rec, col["master_id"])),
            "group_id": clean(g(rec, col["group_id"])),
            "population": clean(g(rec, col["population"])),
            "region": region,
            "subregion": sub,
            "country": country,
            "latitude": f"{lat}" if lat is not None else "",
            "longitude": f"{lon}" if lon is not None else "",
            "date_mean_bp": f"{dmean:g}" if dmean is not None else "",
            "date_sd_bp": f"{dsd:g}" if dsd is not None else "",
            "snps_1240k": snps,
            "assessment": qc,
            "layer": layer,
            "role": role,
            # extras
            "_publication": clean(g(rec, col["publication"])),
            "_doi": clean(g(rec, col["doi"])),
            "_full_date": clean(g(rec, col["full_date"])),
            "_assessment_warnings": clean(g(rec, col["assessment_warnings"])),
            "_qc_eligible": "Y" if eligible else "N",
        })

    print(f"\n[build] GT-002 cohort rows: {len(rows):,}")
    write_outputs(rows)
    print_summary(rows)


# ----------------------------------------------------------------------------
# WRITE OUTPUTS
# ----------------------------------------------------------------------------
SCHEMA = ["sample_id", "master_id", "group_id", "population", "region",
          "subregion", "country", "latitude", "longitude", "date_mean_bp",
          "date_sd_bp", "snps_1240k", "assessment", "layer", "role"]


def tsv(path, header_cols, row_dicts):
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write("\t".join(header_cols) + "\n")
        for r in row_dicts:
            fh.write("\t".join(str(r.get(c, "")) for c in header_cols) + "\n")
    print(f"[write] {path}  ({len(row_dicts):,} rows)")


def write_outputs(rows):
    os.makedirs(OUT_DIR, exist_ok=True)
    # 1. main cohort (all candidates)
    tsv(os.path.join(OUT_DIR, "GT-002.samples.tsv"), SCHEMA, rows)
    # 2. extended (all candidates + raw AADR extras + qc flag)
    ext = SCHEMA + ["publication", "doi", "full_date", "assessment_warnings", "qc_eligible"]
    extrows = []
    for r in rows:
        d = {c: r[c] for c in SCHEMA}
        d["publication"] = r["_publication"]
        d["doi"] = r["_doi"]
        d["full_date"] = r["_full_date"]
        d["assessment_warnings"] = r["_assessment_warnings"]
        d["qc_eligible"] = r["_qc_eligible"]
        extrows.append(d)
    tsv(os.path.join(OUT_DIR, "GT-002.samples.all.tsv"), ext, extrows)
    # 3. analysis subset (QC-eligible)
    analysis = [r for r in rows if r["_qc_eligible"] == "Y"]
    tsv(os.path.join(OUT_DIR, "GT-002.samples.analysis.tsv"), SCHEMA, analysis)
    # 4. population / classification map (per sample)
    mapcols = ["sample_id", "master_id", "group_id", "population", "region",
               "subregion", "layer", "role"]
    tsv(os.path.join(OUT_DIR, "GT-002.population-map.tsv"), mapcols, rows)
    # 5. counts matrix (analysis set)
    write_matrix(os.path.join(OUT_DIR, "GT-002.counts.regionxlayer.tsv"), analysis)
    # bonus: counts matrix (all candidates)
    write_matrix(os.path.join(OUT_DIR, "GT-002.counts.regionxlayer.all.tsv"), rows)


def write_matrix(path, row_dicts):
    mat = defaultdict(lambda: defaultdict(int))
    for r in row_dicts:
        mat[r["region"]][r["layer"]] += 1
    regions = list(REGION_ORDER)  # keep full region order, include zero-count rows
    cols = LAYER_ORDER
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write("region\t" + "\t".join(cols) + "\tTOTAL\n")
        for reg in regions:
            vals = [mat[reg][c] for c in cols]
            fh.write(reg + "\t" + "\t".join(str(v) for v in vals) +
                     "\t" + str(sum(vals)) + "\n")
        # totals row
        tots = [sum(mat[reg][c] for reg in regions) for c in cols]
        fh.write("TOTAL\t" + "\t".join(str(v) for v in tots) +
                 "\t" + str(sum(tots)) + "\n")
    print(f"[write] {path}  ({len(regions)} regions x {len(cols)} layers)")


# ----------------------------------------------------------------------------
# SUMMARY
# ----------------------------------------------------------------------------
def print_summary(rows):
    print("\n=== SUMMARY ===")
    print(f"Total candidates      : {len(rows):,}")
    by_qc = Counter(r["assessment"] for r in rows)
    print("ASSESSMENT distribution:")
    for k, v in by_qc.most_common():
        print(f"   {k or '(empty)':22s} {v:>6,}")
    n_elig = sum(1 for r in rows if r["_qc_eligible"] == "Y")
    print(f"QC-eligible (analysis): {n_elig:,}")
    by_reg = Counter(r["region"] for r in rows)
    print("REGION distribution:")
    for reg in REGION_ORDER:
        print(f"   {reg:20s} {by_reg.get(reg,0):>6,}")
    by_layer = Counter(r["layer"] for r in rows)
    print("LAYER distribution:")
    for lay in LAYER_ORDER:
        print(f"   {lay:8s} {by_layer.get(lay,0):>6,}")
    print("\nFiles written to:", os.path.abspath(OUT_DIR))
    print("In Colab: click the folder icon on the left to find & download the TSVs.")
    print("Cite AADR as: Mallick & Reich, AADR v66.p1, Harvard Dataverse, "
          "https://doi.org/10.7910/DVN/FFIDCW (2026-06-08) + the AADR Scientific "
          "Data paper (2024).")


if __name__ == "__main__":
    build()
