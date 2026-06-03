# Architecture diagram

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
