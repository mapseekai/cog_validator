# COG regression fixtures

Generated with GDAL 3.12.2 and checked with its Python reference validator using `full_check=True`. These files are deliberately small, uncompressed or DEFLATE-compressed, and require no network access or optional codecs to test.

Run `python3 generate.py` and `python3 mutations.py` from this directory (or by absolute path) to regenerate the samples. Generation requires the GDAL Python bindings and `osgeo_utils`; Rust tests only read the committed TIFF files.

- `sparse`, `sparse_mixed`, `sparse_mask`: `SPARSE_OK=YES` with all-zero imagery, only the last main-image tile populated, or empty imagery with a nonempty mask, including overviews.
- `narrow`, `narrow_vertical`: 2048×1 and 1×2048 COGs with overviews.
- `baseline`, `band_mask`, `pixel_mask`, `tile_mask`: valid main images and internal masks used as controls.
- `external_mask.tif` and `.msk`: the baseline plus a separate mask, whose offsets must not be read against the main file.
- `order_{band,tile}_valid`: 3-band controls with 128×128 tiles.
- `order_{band,tile}_swapped`: the controls with bands 1 and 2's offset/size arrays swapped; each band's own offsets remain sorted, but cross-band order is wrong.
- `order_band_overview_{valid,swapped}`: the equivalent BAND mutation applied only to the overview, leaving the main image intact.
- `tiny*`: one-, four-, and five-byte imagery, each with either the correct leader or the deliberately incorrect 99 (`bad_leader`).

Only the swapped-order and bad-leader samples should be rejected. The scripts print reference results for comparison. Test expectations assert the corresponding Rust error variants, not incidental GDAL error strings.
