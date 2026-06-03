# Architecture diagram

`openTEPES_architecture.svg` is the architecture diagram shown in the project
`README.md`. It is hand-drawn SVG and is the source you edit directly — there is
no script that generates it. Open it in any text or vector editor (the boxes and
text are plain SVG elements), change what you need, and save.

The diagram shows the layered package design. Modules drawn in **green** are
implemented (merged upstream); modules drawn in **white** are planned and their
names are indicative.

If you need a raster (PNG) copy, render it from the SVG, for example:

```bash
rsvg-convert -w 2280 openTEPES_architecture.svg -o openTEPES_architecture.png
# or: inkscape openTEPES_architecture.svg --export-filename openTEPES_architecture.png -w 2280
```
