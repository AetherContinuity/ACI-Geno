#!/usr/bin/env python3
"""Compile The Weight of a Bunch into an EPUB 3.

Reads front.md and chapters/*.md, renumbers chapters in reading order with
explicit part dividers, converts the simplified Markdown (headings,
paragraphs, pipe tables, em-dash prose) to XHTML, and emits an EPUB 3.
"""
import os
import re
import zipfile
from xml.sax.saxutils import escape

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'the-weight-of-a-bunch.epub')

BOOK_ID = 'urn:uuid:8f5c31aa-6b7e-4b1f-9d3c-2a1f0c4d5e6b'
TITLE = 'The Weight of a Bunch'
SUBTITLE = 'A Novel'
LANG = 'en-GB'
MODIFIED = '2026-11-25T12:00:00Z'

# Reading order with part dividers: (part title, [(file, [chapter indices])])
PARTS = [
    ('Part One: The Data of Ice', [('ch01.md', [0, 1, 2])]),
    ('Part Two: The Warm Moss', [('ch02.md', [0, 1]), ('ch05.md', [0])]),
    ('Part Three: The Receipts', [('ch03.md', [0, 1]), ('ch06.md', [0, 1]), ('ch03.md', [2, 3, 4])]),
    ('Part Four: The Nameless Day', [('ch04.md', [0, 1, 2]), ('ch06.md', [2]), ('ch04.md', [3, 4])]),
    ('Part Five: The Winter Account', [('ch07.md', [0, 1, 2, 3, 4])]),
]


def read(rel):
    with open(os.path.join(HERE, rel), encoding='utf-8') as f:
        return f.read()


PART_CACHE = {}


def chapters_of(fname):
    if fname not in PART_CACHE:
        text = read(os.path.join('chapters', fname))
        out = []
        chunks = re.split(r'(?m)^## ', text)
        for chunk in chunks[1:]:
            lines = chunk.split('\n')
            heading = lines[0].strip()
            body = '\n'.join(lines[1:]).strip()
            out.append((heading, body))
        PART_CACHE[fname] = out
    return PART_CACHE[fname]


def strip_number(heading):
    return re.sub(r'^Chapter\s*\d*\s*:?\s*', '', heading).strip()


def md_to_html(md):
    lines = md.split('\n')
    out = []
    i = 0
    para = []

    def flush():
        if para:
            out.append('<p>%s</p>' % ' '.join(para))
            para.clear()

    while i < len(lines):
        line = lines[i]
        s = line.strip()
        if not s:
            flush()
            i += 1
            continue
        if s.startswith('|'):
            rows = []
            while i < len(lines) and lines[i].strip().startswith('|'):
                cells = [c.strip() for c in lines[i].strip().strip('|').split('|')]
                if not all(re.fullmatch(r':?-{2,}:?', c) for c in cells):
                    rows.append(cells)
                i += 1
            flush()
            out.append('<table>')
            head = rows[0]
            out.append('<thead><tr>%s</tr></thead>' % ''.join('<th>%s</th>' % escape(c) for c in head))
            out.append('<tbody>')
            for r in rows[1:]:
                out.append('<tr>%s</tr>' % ''.join('<td>%s</td>' % escape(c) for c in r))
            out.append('</tbody></table>')
            continue
        if s.startswith('#### '):
            flush()
            out.append('<h4>%s</h4>' % escape(s[5:]))
        elif s.startswith('### '):
            flush()
            out.append('<h3>%s</h3>' % escape(s[4:]))
        elif s == '---':
            flush()
            out.append('<hr/>')
        else:
            para.append(escape(s))
        i += 1
    flush()
    return '\n'.join(out)


def xhtml(title, body_html, chapter_id, body_type=None):
    return ('<?xml version="1.0" encoding="utf-8"?>\n'
            '<!DOCTYPE html>\n'
            '<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" '
            'xml:lang="%s" lang="%s">\n<head>\n  <meta charset="utf-8"/>\n  <title>%s</title>\n'
            '  <link rel="stylesheet" type="text/css" href="../style.css"/>\n</head>\n'
            '<body epub:type="%s">\n<section id="%s">\n%s\n</section>\n</body>\n</html>\n'
            ) % (LANG, LANG, escape(title), body_type or 'bodymatter', chapter_id, body_html)


STYLE = '''body { font-family: Georgia, serif; line-height: 1.55; }
h1 { font-size: 1.9em; margin: 3em 0 0.3em; }
h2 { font-size: 1.3em; margin: 0 0 0.6em; }
h3 { font-size: 1.05em; margin: 2em 0 0.5em; }
h5 { text-align: center; letter-spacing: 0.15em; font-size: 0.85em; margin: 4em 0 0.3em; font-weight: normal; text-indent:0; }
h6 { text-align: center; font-size: 1em; margin: 0.2em 0 2em; font-weight: normal; text-indent:0; }
p { text-indent: 1.2em; margin: 0 0 0.25em; }
h2 + p, h3 + p, h4 + p, hr + p { text-indent: 0; }
table { border-collapse: collapse; margin: 1em 0; width: 100%; font-size: 0.92em; }
th, td { border: 1px solid #999; padding: 4px 7px; text-align: left; vertical-align: top; }
hr { border: 0; border-top: 1px solid #999; margin: 2em 15%; }
.titlepage { text-align: center; }
.titlepage h1 { margin-top: 6em; font-size: 2.1em; }
.titlepage p { text-indent: 0; }
.colophon p { text-indent: 0; font-size: 0.9em; }
img.cover { width: 100%; height: auto; }
.coverp { text-indent: 0; margin: 0; }
.part p, .part h1 { text-indent: 0; text-align: center; }
.part h1 { margin-top: 8em; font-size: 1.5em; letter-spacing: 0.06em; }
'''


def main():
    front_md = read('front.md')
    note_md = front_md.split('---', 1)[1].strip()

    title_body = ('<h1>%s</h1>\n<h2>%s</h2>\n<h5>%s</h5>\n<h6>%s</h6>'
                  % (escape(TITLE), escape(SUBTITLE),
                     escape('Being a book of the wet season at Mustakorpi,'),
                     escape('and of one banana.')))

    note_body = md_to_html(note_md)

    cover_body = '<p class="coverp"><img class="cover" src="../media/cover.jpg" alt="Cover: The Weight of a Bunch"/></p>'
    docs = [('cover', 'Cover', cover_body, 'cover'),
            ('titlepage', 'Title Page', title_body, 'frontmatter titlepage'),
            ('note', 'A Note on This Book', note_body, 'frontmatter colophon')]

    chapter_no = 0
    for part_title, spec in PARTS:
        docs.append(('part%d' % (len(docs) - 1), part_title,
                     '<h1>%s</h1>' % escape(part_title), 'bodymatter part'))
        for fname, idxs in spec:
            chapters = chapters_of(fname)
            for i in idxs:
                heading, body = chapters[i]
                chapter_no += 1
                title = strip_number(heading)
                cid = 'ch%02d' % chapter_no
                body_html = ('<h1>Chapter %d</h1>\n<h2>%s</h2>\n\n%s'
                             % (chapter_no, escape(title), md_to_html(body)))
                docs.append((cid, '%d. %s' % (chapter_no, title), body_html, 'bodymatter'))

    tail_md = (
        '# The End\n\n'
        'What is eaten is eaten. What is grown is grown.\n\n'
        '---\n\n'
        '### After the last page\n\n'
        'This book was formed as an independent English-language work from three Finnish-language '
        'source chronicles held in the same repository. It is not a translation of them, and it '
        'borrows no passages. Its debt, like that of the state it describes, is recorded in full: '
        'the hill, the glass, the snowman with the carrot, the counting, and the fruit itself.\n\n'
        'Kuopio, in the wet season.\n')
    docs.append(('theend', 'The End', md_to_html(tail_md), 'colophon'))

    container = ('<?xml version="1.0"?><container version="1.0" '
                 'xmlns="urn:oasis:names:tc:opendocument:xmlns:container"><rootfiles>'
                 '<rootfile full-path="OEBPS/content.opf" '
                 'media-type="application/oebps-package+xml"/></rootfiles></container>')

    manifest_items = ['<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>',
                      '<item id="cover-image" href="media/cover.jpg" media-type="image/jpeg" properties="cover-image"/>',
                      '<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>',
                      '<item id="css" href="style.css" media-type="text/css"/>']
    spine_items = []
    nav_lis = []
    ncx_points = []
    for i, (cid, doctitle, body, btype) in enumerate(docs):
        manifest_items.append('<item id="%s" href="text/%s.xhtml" media-type="application/xhtml+xml"/>' % (cid, cid))
        spine_items.append('<itemref idref="%s"/>' % cid)
        nav_lis.append('<li><a href="text/%s.xhtml">%s</a></li>' % (cid, escape(doctitle)))
        ncx_points.append('<navPoint id="np%d" playOrder="%d"><navLabel><text>%s</text></navLabel>'
                          '<content src="text/%s.xhtml"/></navPoint>' % (i + 1, i + 1, escape(doctitle), cid))

    opf = ('<?xml version="1.0" encoding="utf-8"?>\n'
           '<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="pub-id" '
           'xml:lang="%s">\n  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">\n'
           '    <dc:identifier id="pub-id">%s</dc:identifier>\n'
           '    <dc:title>%s</dc:title>\n    <dc:title id="t2">%s</dc:title>\n'
           '    <meta refines="#t2" property="title-type">subtitle</meta>\n'
           '    <dc:language>%s</dc:language>\n'
           '    <dc:description>An independent English-language novel inspired by the Bannanivaltio '
           'chronicles. Not a translation.</dc:description>\n'
           '    <dc:source>https://github.com/AetherContinuity/ACI-Geno</dc:source>\n'
           '    <meta property="dcterms:modified">%s</meta>\n'
           '    <meta name="cover" content="cover-image"/>\n'
           '  </metadata>\n  <manifest>\n'
           '%s\n  </manifest>\n  <spine toc="ncx">\n%s\n  </spine>\n</package>\n'
           % (LANG, BOOK_ID, TITLE, SUBTITLE, LANG, MODIFIED,
              '\n'.join('    ' + m for m in manifest_items),
              '\n'.join('    ' + s for s in spine_items)))

    ncx = ('<?xml version="1.0" encoding="utf-8"?>\n'
           '<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">\n'
           '  <head><meta name="dtb:uid" content="%s"/></head>\n'
           '  <docTitle><text>%s</text></docTitle>\n  <navMap>\n'
           '%s\n  </navMap>\n</ncx>\n'
           % (BOOK_ID, TITLE, '\n'.join('    ' + p for p in ncx_points)))

    nav = ('<?xml version="1.0" encoding="utf-8"?>\n<!DOCTYPE html>\n'
           '<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" '
           'lang="%s">\n<head><meta charset="utf-8"/><title>Contents</title></head>\n'
           '<body><nav epub:type="toc" id="toc"><h1>Contents</h1><ol>\n%s\n</ol></nav></body></html>'
           % (LANG, '\n'.join('  ' + li for li in nav_lis)))

    with zipfile.ZipFile(OUT, 'w') as z:
        z.writestr('mimetype', 'application/epub+zip', compress_type=zipfile.ZIP_STORED)
        z.writestr('META-INF/container.xml', container)
        z.writestr('OEBPS/content.opf', opf)
        z.writestr('OEBPS/nav.xhtml', nav)
        z.writestr('OEBPS/toc.ncx', ncx)
        z.writestr('OEBPS/style.css', STYLE)
        with open(os.path.join(HERE, 'cover.jpg'), 'rb') as cimg:
            z.writestr('OEBPS/media/cover.jpg', cimg.read())
        for cid, doctitle, body, btype in docs:
            z.writestr('OEBPS/text/%s.xhtml' % cid, xhtml(doctitle, body, cid, btype))
    print('wrote %s (%d documents, %d numbered chapters)' % (OUT, len(docs), chapter_no))


if __name__ == '__main__':
    main()
