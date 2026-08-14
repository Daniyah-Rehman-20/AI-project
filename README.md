# Bushra Khan — ATS-optimized SDE resume (Overleaf)

Single-column `pdfLaTeX` resume targeting Software Development Engineer roles. Two-column templates (including AltaCV) often drop to low ATS parse scores because parsers read columns out of order, skip sidebars, and miss icon-only contact fields.

## Overleaf

1. New project → Blank project (or Upload Project).
2. Replace `main.tex` with `bushra-resume.tex` (or rename this file to `main.tex`).
3. Menu → Compiler → **pdfLaTeX**.
4. Recompile → Download PDF.
5. Upload that PDF to job portals (Workday, Greenhouse, Lever, Naukri). Do not upload the `.tex` file.

No extra class files, fonts, or images are required.

## ATS design choices

- One column, standard headings (`Education`, `Technical Skills`, `Experience`, `Projects`, `Achievements`)
- Visible emails and URLs (not icon-only “LinkedIn”)
- Skills near the top for keyword matching
- No photo, tables-as-layout grids, text boxes, or Font Awesome
- SDE keywords: Java, C++, Python, REST APIs, React.js, Node.js, MySQL, DSA, OOP, DBMS
