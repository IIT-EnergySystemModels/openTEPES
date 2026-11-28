# Diagrams

## Architecture diagram

Two files make up the architecture diagram shown in the project `README.md`:

- `openTEPES_architecture.pptx` — the source. It is one PowerPoint slide, and every box,
  arrow and label is a shape that can be edited. Open it in PowerPoint or LibreOffice
  Impress, make the change, and save.
- `openTEPES_architecture.png` — the slide exported as an image, 1710 pixels wide. The
  project `README.md` embeds the PNG, because some pages (for example the PyPI project
  page) do not display other formats.

Modules drawn in **green** are implemented (merged upstream); modules drawn in
**white**, with a dashed edge, are planned and their names are indicative.

After editing the slide, export the PNG again so the two stay in step. In PowerPoint,
use File > Export, choose PNG, and set the width to 1710 pixels. From the command line,
with LibreOffice and poppler:

```
soffice --headless --convert-to pdf openTEPES_architecture.pptx
pdftoppm -scale-to-x 1710 -scale-to-y -1 -png -singlefile openTEPES_architecture.pdf openTEPES_architecture
```

Delete the PDF afterwards; only the slide and the PNG are kept.

## AC formulation diagrams

Three single-line diagrams are embedded in `doc/md/MathematicalFormulation.md`. Each
is hand-drawn SVG, edited directly, with a PNG rendered from it, and the documentation
embeds the PNG.

- `ac_branch_model.svg` — one AC branch: the tap, the series impedance, and half the
  charging susceptance at each end, with the flows marked at their own ends.
- `ac_hvdc_converter.svg` — an HVDC link under both converter models, with the reactive
  power and the station losses at each terminal.
- `ac_converter_capability.svg` — the capability disc of one terminal and the twelve
  tangent lines that stand in for it.

Symbols follow the notation table in `MathematicalFormulation.md`. Parameters are drawn
in blue and variables in red, so a reader can tell at a glance what the model decides
and what the case file fixes.

Regenerate each PNG with `rsvg-convert` (librsvg) or Inkscape, at a width of 1400:

```
rsvg-convert -w 1400 ac_branch_model.svg -o ac_branch_model.png
```
