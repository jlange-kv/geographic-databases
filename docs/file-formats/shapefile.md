# Shapefile

Shapefile is a legacy multi-file format created by Esri in the early 1990s. It remains widespread due to decades of institutional use, but has significant limitations that modern formats address.

## What is a Shapefile?

Despite the name, a "Shapefile" is actually **multiple files** that must be kept together. The format splits geometry, attributes, and metadata across separate files sharing the same base name:

```
my_data.shp    Geometry (binary)          — Required
my_data.shx    Spatial index (offsets)     — Required
my_data.dbf    Attributes (dBASE format)   — Required
my_data.prj    Coordinate reference system — Important but optional
my_data.cpg    Character encoding          — Optional
my_data.sbn    Spatial index (Esri)        — Optional
my_data.xml    Metadata                    — Optional
```

The three required files (.shp, .shx, .dbf) must always travel together. Lose one and the dataset is broken.

### How the Files Work Together

**`.shp`** stores geometry as binary records, one per feature. Each record has a header (record number, content length) followed by the geometry in a Shapefile-specific binary format.

**`.shx`** is an offset index — it maps record numbers to byte positions in the .shp file. This allows direct access to any feature by its index without scanning from the beginning.

**`.dbf`** stores attributes in [dBASE III][dbase] format — a tabular format from the 1980s. Each row corresponds to a geometry record in the .shp file, matched by position.

**`.prj`** contains the coordinate reference system as WKT (Well-Known Text). Without it, tools don't know what coordinate system the data is in.

**`.cpg`** specifies character encoding (e.g., UTF-8, Latin-1). Without it, tools guess — which often leads to garbled characters in non-ASCII text.

## Limitations

### 2 GB File Size Limit

The .shp file uses 32-bit offsets, capping it at ~2 GB. The .dbf file has a separate ~2 GB limit. For large datasets, this is a hard wall with no workaround within the format.

### 10-Character Column Names

dBASE III limits field names to 10 characters. Long, descriptive names get silently truncated:

```
"building_category"  → "building_c"
"population_2024"    → "population"
"measurement_date"   → "measuremen"
```

This leads to cryptic, ambiguous column names that require external documentation to interpret.

### One Geometry Type Per File

A single Shapefile can only contain one geometry type. To store points, lines, and polygons for the same area, you need three separate Shapefiles (each being 3+ files).

Compare to [GeoPackage][geopackage] which stores multiple layers with different geometry types in one file.

### Limited Data Types

dBASE supports a narrow set of types:

| dBASE Type | Limitation |
|---|---|
| Character | Max 254 bytes |
| Number | Max 18 digits |
| Date | Date only (no time) |
| Logical | Boolean |
| Float | Max 18 digits |

No datetime, no large text fields, no arrays, no nested objects.

### Encoding Issues

Character encoding is not reliably declared. The optional .cpg file may be missing, wrong, or ignored by tools.

### No Null Geometry

Features must have geometry. You cannot store a record with attributes but no spatial component.

## Why It Persists

Despite these limitations, Shapefiles remain common because:

- **Institutional inertia** — Government agencies and organizations have decades of data in Shapefile format
- **Universal support** — Every GIS tool ever made reads Shapefiles
- **Procurement requirements** — Some specifications still mandate Shapefile delivery
- **Familiarity** — Users and workflows built around the format

The [Switch from Shapefile][switch-from-shapefile] campaign advocates using [GeoPackage][geopackage] as a drop-in replacement.

## When to Use Shapefile

### Only when required:

- Legacy system requires Shapefile input
- Data recipient explicitly requests Shapefile format
- Regulatory or contractual obligation

### For everything else:

| Instead of Shapefile... | Use |
|---|---|
| Sharing data | [GeoPackage][geopackage] — single file, no limitations |
| Web mapping | [FlatGeobuf][flatgeobuf] or [GeoJSON][geojson] |
| Analytics | [GeoParquet][geoparquet] |
| Archival | [GeoPackage][geopackage] |

## Tooling

### Python (GeoPandas)

```python
import geopandas as gpd

# Read
gdf = gpd.read_file("data.shp")

# Read with explicit encoding (common need)
gdf = gpd.read_file("data.shp", encoding="latin-1")

# Write (creates .shp, .shx, .dbf, .prj, .cpg)
gdf.to_file("output.shp")
```

### GDAL

```bash
# Convert Shapefile → GeoPackage
ogr2ogr -f GPKG output.gpkg input.shp

# Convert Shapefile → FlatGeobuf
ogr2ogr -f FlatGeobuf output.fgb input.shp

# List info
ogrinfo -so input.shp input
```

## Key Takeaways

1. **Multi-file format** — Minimum 3 files that must stay together
2. **Hard limitations** — 2 GB size, 10-char column names, one geometry type
3. **Encoding problems** — Non-ASCII characters are frequently garbled
4. **Legacy format** — Use [GeoPackage][geopackage] for new work
5. **Still ubiquitous** — Shapefiles are still common so it knowing how to use one is important as well

## Related Topics

- [GeoPackage][geopackage] — Direct replacement (single file, no limitations)
- [File Formats Overview][formats] — Compare all formats
- [FlatGeobuf][flatgeobuf] — Modern alternative for streaming
- [GeoParquet][geoparquet] — Modern alternative for analytics

## References

- [Esri Shapefile Technical Description (PDF)][esri-spec]
- [Switch from Shapefile][switch-from-shapefile]
- [dBASE III Format][dbase]

<!-- Reference-style links -->
[geopackage]: geopackage.md
[flatgeobuf]: flatgeobuf.md
[geoparquet]: geoparquet.md
[geojson]: geojson.md
[formats]: README.md
[process-data]: ../../process_data.py

[esri-spec]: https://www.esri.com/content/dam/esrisites/sitecore-archive/Files/Pdfs/library/whitepapers/pdfs/shapefile.pdf
[switch-from-shapefile]: https://switchfromshapefile.org/
[dbase]: https://en.wikipedia.org/wiki/DBase
