#!/bin/sh
# Kokoaa The Nameless Day -epubin. Vaatii pandocin.
# Käyttö: sh the-nameless-day/build/build.sh  (repon juuresta)
set -e
D=the-nameless-day
V=$(cat "$D/build/VERSION")
B=$(date +%Y-%m-%d)
T=$(mktemp)
printf 'date: "%s"\ndescription: "Version %s, built %s. One night at Mustakorpi, told twice. A homage to Kie\u015blowski'"'"'s Przypadek."\n' "$B" "$V" "$B" > "$T"
pandoc "$D/01-exhibits.md" "$D/02-report.md" "$D/03-account.md" "$D/04-what-does-not-care.md" \
  --metadata-file="$D/build/meta.yaml" \
  --metadata-file="$T" \
  --epub-cover-image="$D/build/cover.jpg" \
  --css="$D/build/style.css" \
  --toc --toc-depth=2 --split-level=1 \
  -o "$D/the-nameless-day.epub"
rm -f "$T"
echo "OK: $D/the-nameless-day.epub (versio $V, koottu $B)"
