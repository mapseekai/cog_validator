from pathlib import Path
from osgeo import gdal
from osgeo_utils.samples import validate_cloud_optimized_geotiff as reference
import struct, json

gdal.UseExceptions()
root = Path(__file__).parent

def tags(raw, ifd=None):
    endian = '<' if raw[:2] == b'II' else '>'
    if ifd is None:
        ifd = struct.unpack_from(endian + 'I', raw, 4)[0]
    count = struct.unpack_from(endian + 'H', raw, ifd)[0]
    result = {}
    for i in range(count):
        entry = ifd + 2 + 12 * i
        tag, kind, n, value = struct.unpack_from(endian + 'HHII', raw, entry)
        size = {1:1, 2:1, 3:2, 4:4, 5:8, 12:8}.get(kind, 1)
        result[tag] = (kind, n, entry + 8 if n * size <= 4 else value)
    return endian, result

def swap_bands(interleave, overview=False):
    ds = gdal.GetDriverByName('MEM').Create('', 256, 256, 3)
    for i in range(1, 4):
        ds.GetRasterBand(i).Fill(i * 10)
    stem = 'order_' + interleave.lower() + ('_overview' if overview else '')
    control = root / (stem + '_valid.tif')
    out = gdal.Translate(str(control), ds, format='COG', creationOptions=[
        'BLOCKSIZE=128', 'COMPRESS=DEFLATE', 'OVERVIEWS=AUTO' if overview else 'OVERVIEWS=NONE', 'INTERLEAVE=' + interleave])
    out = None
    ds = gdal.Open(str(control))
    ifd = int(ds.GetRasterBand(1).GetOverview(0).GetMetadataItem('IFD_OFFSET', 'TIFF')) if overview else None
    ds = None
    raw = bytearray(control.read_bytes())
    endian, entries = tags(raw, ifd)
    for tag in [324, 325]:
        kind, n, pos = entries[tag]
        unit, fmt = {3:(2, 'H'), 4:(4, 'I')}[kind]
        values = list(struct.unpack_from(endian + fmt * n, raw, pos))
        per_band = n // 3
        values[:per_band], values[per_band:2*per_band] = values[per_band:2*per_band], values[:per_band]
        struct.pack_into(endian + fmt * n, raw, pos, *values)
    changed = root / (stem + '_swapped.tif')
    changed.write_bytes(raw)
    return [control, changed]

def tiny(bad=False, length=1):
    md = b'LAYOUT=IFDS_BEFORE_DATA\nBLOCK_ORDER=ROW_MAJOR\nBLOCK_LEADER=SIZE_AS_UINT4\nBLOCK_TRAILER=LAST_4_BYTES_REPEATED\nKNOWN_INCOMPATIBLE_EDITION=NO\n'
    header = ('GDAL_STRUCTURAL_METADATA_SIZE=%06d bytes\n' % len(md)).encode()
    ifd = 8 + len(header) + len(md)
    ifd += ifd % 2
    n = 10
    offset = ifd + 2 + n * 12 + 4 + 4
    values = [(256,3,1,length), (257,3,1,1), (258,3,1,8), (259,3,1,1),
              (262,3,1,1), (273,4,1,offset), (277,3,1,1), (278,3,1,1),
              (279,4,1,length), (284,3,1,1)]
    raw = bytearray(b'II' + struct.pack('<HI', 42, ifd) + header + md)
    raw.extend(b'\0' * (ifd - len(raw)))
    raw.extend(struct.pack('<H', n))
    for entry in values:
        raw.extend(struct.pack('<HHII', *entry))
    raw.extend(struct.pack('<I', 0))
    raw.extend(struct.pack('<I', 99 if bad else length))
    raw.extend(b'\x2a' * length)
    if length >= 4:
        raw.extend(b'\x2a' * 4)
    stem = 'tiny' if length == 1 else f'tiny_{length}'
    path = root / (stem + ('_bad_leader.tif' if bad else '_valid.tif'))
    path.write_bytes(raw)
    return path

paths = swap_bands('BAND') + swap_bands('TILE') + swap_bands('BAND', overview=True)
paths += [tiny(bad, length) for length in (1, 4, 5) for bad in (False, True)]
for path in paths:
    warnings, errors, details = reference.validate(str(path), full_check=True)
    print(json.dumps({'file': path.name, 'reference_errors': errors, 'warnings': warnings}))
