# Hand-drawn diagrams

## Architecture diagram

Two files make up the architecture diagram shown in the project `README.md`:

- `openTEPES_architecture.svg` — the source. It is hand-drawn SVG (the boxes and
  text are plain SVG elements) and is edited directly; there is no script that
  generates it. Open it in any text or vector editor, change what you need, save.
- `openTEPES_architecture.png` — a raster copy rendered from the SVG. The project
  `README.md` embeds the PNG, because some pages (for example the PyPI project
  page) do not display SVG images.

Modules drawn in **green** are implemented (merged upstream); modules drawn in
**white** are planned and their names are indicative.

After editing the SVG, regenerate the PNG so the two stay in step. Use a vector
tool such as [Inkscape](https://inkscape.org), which runs on Windows, macOS and
Linux:

Windows (Command Prompt or PowerShell):

```
inkscape openTEPES_architecture.svg --export-type=png --export-filename=openTEPES_architecture.png -w 1710
```

Linux / macOS (Inkscape, or `rsvg-convert` from librsvg):

```
inkscape openTEPES_architecture.svg --export-type=png --export-filename=openTEPES_architecture.png -w 1710
rsvg-convert -w 1710 openTEPES_architecture.svg -o openTEPES_architecture.png
```

## AC formulation diagrams

Three single-line diagrams are embedded in `doc/md/MathematicalFormulation.md`. They
follow the same arrangement: hand-drawn SVG as the source, a PNG rendered from it, and
the documentation embeds the PNG.

- `ac_branch_model.svg` — one AC branch: the tap, the series impedance, and half the
  charging susceptance at each end, with the flows marked at their own ends.
- `ac_hvdc_converter.svg` — an HVDC link under both converter models, with the reactive
  power and the station losses at each terminal.
- `ac_converter_capability.svg` — the capability disc of one terminal and the twelve
  tangent lines that stand in for it.

Symbols follow the notation table in `MathematicalFormulation.md`. Parameters are drawn
in blue and variables in red, so a reader can tell at a glance what the model decides
and what the case file fixes.

Regenerate each PNG the same way as the architecture diagram, at a width of 1400:

```
rsvg-convert -w 1400 ac_branch_model.svg -o ac_branch_model.png
```
