#!/bin/sh
# Kokoaa The Nameless Day -epubin. Vaatii pandocin.
# Käyttö: sh the-nameless-day/build/build.sh  (repon juuresta)
set -e
D=the-nameless-day
V=$(cat "$D/build/VERSION")
B=$(date +%Y-%m-%d)
pandoc "$D/01-exhibits.md" "$D/02-report.md" "$D/03-account.md" "$D/04-what-does-not-care.md" \
  --metadata-file="$D/build/meta.yaml" \
  --metadata date="$B" \
  --metadata description="Version $V, built $B. One night at Mustakorpi, told twice. A homage to Kieślowski's Przypadek." \
  --epub-cover-image="$D/build/cover.jpg" \
  --css="$D/build/style.css" \
  --toc --toc-depth=2 --split-level=1 \
  -o "$D/the-nameless-day.epub"
echo "OK: $D/the-nameless-day.epub (versio $V, koottu $B)"
