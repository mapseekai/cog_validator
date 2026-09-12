from pathlib import Path
from osgeo import gdal, osr
from osgeo_utils.samples import validate_cloud_optimized_geotiff as reference
import json, shutil

gdal.UseExceptions()
root = Path(__file__).parent

def make(name, width=1024, height=1024, bands=1, opts=(), sparse=False, mask=False, mixed=False):
    ds = gdal.GetDriverByName('MEM').Create('', width, height, bands, gdal.GDT_Byte)
    ds.SetGeoTransform([0, 1, 0, 0, 0, -1])
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(4326)
    ds.SetSpatialRef(srs)
    for i in range(1, bands + 1):
        ds.GetRasterBand(i).Fill(0 if sparse else i * 10)
        if mixed:
            ds.GetRasterBand(i).WriteRaster(width - 128, height - 128, 128, 128, bytes([i * 10]) * (128 * 128))
    if mask:
        ds.GetRasterBand(1).CreateMaskBand(gdal.GMF_PER_DATASET)
        ds.GetRasterBand(1).GetMaskBand().Fill(255)
    path = root / (name + '.tif')
    out = gdal.Translate(str(path), ds, format='COG', creationOptions=['COMPRESS=DEFLATE', 'BLOCKSIZE=128', *opts])
    out = None
    return path

paths = [
    make('baseline'),
    make('sparse', opts=['SPARSE_OK=YES'], sparse=True),
    make('sparse_mixed', opts=['SPARSE_OK=YES'], sparse=True, mixed=True),
    make('sparse_mask', opts=['SPARSE_OK=YES'], sparse=True, mask=True),
    make('narrow', width=2048, height=1),
    make('narrow_vertical', width=1, height=2048),
    make('tile_mask', bands=3, mask=True, opts=['INTERLEAVE=TILE']),
    make('band_mask', bands=3, mask=True, opts=['INTERLEAVE=BAND']),
    make('pixel_mask', bands=3, mask=True, opts=['INTERLEAVE=PIXEL']),
]

external = root / 'external_mask.tif'
shutil.copyfile(paths[0], external)
gdal.SetConfigOption('GDAL_TIFF_INTERNAL_MASK', 'NO')
ds = gdal.OpenEx(str(external), gdal.OF_RASTER | gdal.OF_UPDATE, open_options=['IGNORE_COG_LAYOUT_BREAK=YES'])
ds.CreateMaskBand(gdal.GMF_PER_DATASET)
ds.GetRasterBand(1).GetMaskBand().Fill(255)
ds = None
gdal.SetConfigOption('GDAL_TIFF_INTERNAL_MASK', None)
paths.append(external)

for path in paths:
    ds = gdal.Open(str(path))
    band = ds.GetRasterBand(1)
    warnings, errors, details = reference.validate(ds, full_check=True)
    print(json.dumps({'file': path.name, 'reference_errors': errors, 'warnings': warnings,
        'interleave': ds.GetMetadata('IMAGE_STRUCTURE'),
        'first_offset': band.GetMetadataItem('BLOCK_OFFSET_0_0', 'TIFF'),
        'overviews': [(band.GetOverview(i).XSize, band.GetOverview(i).YSize) for i in range(band.GetOverviewCount())]}))
