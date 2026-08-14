# Bushra Khan — ATS-optimized SDE resume (Overleaf)

Single-column **one-page** A4 `pdfLaTeX` resume targeting Software Development Engineer roles.

## Overleaf

1. New project → Blank project (or Upload Project).
2. Replace `main.tex` with `bushra-resume.tex` (or rename this file to `main.tex`).
3. Menu → Compiler → **pdfLaTeX** (not XeLaTeX, not LuaLaTeX).
4. Menu → Paper Size → **A4**. Orientation stays **Portrait**.
5. Recompile → Download PDF.
6. Upload that PDF to job portals. Do not upload the `.tex` file.

Do not paste this into an AltaCV project. AltaCV’s `right=10cm` sidebar geometry squeezes the body into a thin column and overlaps dates with titles.

No extra class files, fonts, or images are required.

## ATS design choices

- One column, standard headings (`Education`, `Technical Skills`, `Experience`, `Projects`, `Achievements`)
- Visible emails and URLs (not icon-only “LinkedIn”)
- Skills near the top for keyword matching
- No photo, tables-as-layout grids, text boxes, or Font Awesome
- SDE keywords: Java, C++, Python, REST APIs, React.js, Node.js, MySQL, DSA, OOP, DBMS
