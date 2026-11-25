# The Weight of a Bunch

An independent English-language novel formed from the Finnish-language source
chronicles in this repository (`Bannanivaltio.epub`, `Puijon_piiritys (4).epub`,
`Puijon_terttu.epub`). Per the project charter, it is **not a translation**: it is
a new prose work with its own plot and characters, set in the same fictional
landscape (Mustakorpi, Puijo, greenhouse 3 row 14, bunch 1/2033, the snowman,
the audit office) and carrying forward the source tradition where the elder
capuchin left it: *what is eaten is eaten*.

- **Length:** ~18,600 words, 24 numbered chapters in 5 parts
- **Narrator:** Akseli Hämäläinen, junior frost-maintenance man of the State of
  Bannanivaltio
- **Delivery:** `the-weight-of-a-bunch.epub` (EPUB 3), plus Markdown sources

## Layout

- `front.md` — title page and author's note
- `chapters/ch01.md` … `ch07.md` — chapter sources (part headers included)
- `build_epub.py` — Python (stdlib only) EPUB 3 packager
- `the-weight-of-a-bunch.epub` — compiled book

## Build

```bash
python3 build_epub.py
```

## Continuity notes

The chapter numbering in the Markdown sources is deliberately loose (inserted
chapters carry no number); `build_epub.py` renumbers chapters in reading order
and emits part-divider pages. Reading order, with part structure, is declared in
`PARTS` inside the build script. New chapters should be added there, not
renumbered by hand.
