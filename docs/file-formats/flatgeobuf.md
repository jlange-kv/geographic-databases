# FlatGeobuf

FlatGeobuf is a row-based binary format designed for fast spatial queries and efficient streaming over HTTP. It combines Google's FlatBuffers serialization with a built-in R-tree spatial index.

## What is FlatGeobuf?

FlatGeobuf was created to solve a specific problem: **how do you serve geographic data over the web without a database server?**

It builds on two technologies:

- **[FlatBuffers][flatbuffers]** (Google): A binary serialization library where the on-disk format matches the in-memory layout — enabling zero-copy reads
- **[Packed Hilbert R-tree][packed-rtree]**: A static spatial index embedded directly in the file

**Design goals:**
- Stream partial data over HTTP (only download what you need)
- Fast spatial filtering without server-side processing
- Simple file format (no database engine required)
- Zero parsing overhead when reading features

## File Structure

```
FlatGeobuf file:
┌─────────────────────┐
│ Header              │  Schema, CRS, geometry type, feature count
├─────────────────────┤
│ R-tree Index        │  Packed Hilbert R-tree (all levels)
│                     │  Compact: only bounding boxes (4 numbers each)
├─────────────────────┤
│ Feature 1           │  Geometry + attributes (FlatBuffer encoded)
│ Feature 2           │
│ Feature 3           │
│ ...                 │
└─────────────────────┘
```

**Header:** Contains metadata about the file — schema (column names/types), coordinate reference system, geometry type, and total feature count.

**R-tree Index:** A spatial index covering all features. The index stores only bounding rectangles, making it compact relative to the actual geometry data. See [Spatial Indexing][spatial-indexing] for how R-trees work and why the index is small.

**Feature Data:** Each feature is stored as a complete FlatBuffer — geometry and all attributes together. This is [row-based storage][row-vs-columnar]: you always read the full feature.

## Zero-Copy Reading

### How FlatGeobuf Stores Data

FlatBuffers uses a memory layout where the bytes on disk are identical to how they would be arranged in memory. When you read a feature, the bytes don't need to be parsed or transformed — they're already in the right format.

```
On disk (FlatGeobuf file):
┌──────────────┬────────────┬─────────────────┐
│ geometry     │ name_offset│ area (float64)   │
│ (WKB bytes)  │ → "Oslo"   │ 150.5            │
└──────────────┴────────────┴─────────────────┘

In memory (after reading):
┌──────────────┬────────────┬─────────────────┐
│ geometry     │ name_offset│ area (float64)   │
│ (WKB bytes)  │ → "Oslo"   │ 150.5            │
└──────────────┴────────────┴─────────────────┘

Same layout — no transformation needed
```

The application can read fields directly from the buffer by offset, without building intermediate objects.

### Trade-offs of Zero-Copy

**Fast reads:**
- No parsing step (compare GeoJSON where text must be parsed into numbers)
- No deserialization (compare GeoPackage where SQLite rows must be decoded)
- Fields accessed by offset — only read the fields you actually use

**Incompatible with compression:**
- Zero-copy requires that on-disk bytes match memory layout
- Compression transforms bytes into a different representation
- You would have to decompress first, which defeats the purpose
- This is a deliberate design choice: **read speed over file size**

**Not human-readable:**
- Binary format — can't open in a text editor like GeoJSON
- Need tools to inspect contents

## Compression and Size

FlatGeobuf has **no built-in compression**. This is a direct consequence of the zero-copy design.

**Size comparison to other formats:**
- Larger than GeoParquet (which uses dictionary encoding, run-length encoding, and codecs like ZSTD)
- Larger than compressed GeoPackage
- Smaller than GeoJSON (text encoding is inherently verbose)

**The trade-off is intentional:**

```
GeoParquet:  Small file → Decompress → Parse → Use
FlatGeobuf:  Larger file → Use directly
```

For FlatGeobuf's primary use case (streaming over HTTP), this works well: you're only fetching the features you need via spatial filtering, so total transfer size is small even though individual features are uncompressed.

**External compression** (gzip, brotli) can be applied for archival or transfer, but then you lose zero-copy and streaming capabilities.

## Streaming Over HTTP

This is FlatGeobuf's core strength. The file structure enables clients to read only the features they need from a remote file.

### How It Works

See [Spatial Indexing — FlatGeobuf Streaming][spatial-indexing-streaming] for the full workflow. The key steps:

1. **Fetch header + index** — One HTTP request. The index is compact (only bounding boxes), so this is fast.
2. **Query index in memory** — Traverse the R-tree for your bounding box. No network needed.
3. **Fetch matching features** — HTTP range requests for specific byte offsets. Only download what you need.

### Spatial Filtering Benchmark

Using GeoPandas with a `bbox` parameter (see [Tooling — Python](#python-geopandas) for code), the reader consults the R-tree index and only reads features whose bounding box intersects the query area.

**Results** from [demo_flatgeobuf_bbox.py][demo-bbox] on Norwegian mining registration data (EPSG:25833):

```
Full read:    6562 features in 0.0701s
Bbox read:       9 features in 0.0014s

Speedup:        50x faster with bbox filter
Data reduction: 6562 → 9 features (0.1%)
Memory saving:  5.71 MB → 0.01 MB (0.1%)
```

### Pattern: Spatial Pre-Filter + Pandas Analytics

Since bbox-filtered reads return a regular GeoDataFrame, you can chain spatial filtering with analytical operations. FlatGeobuf handles the spatial part efficiently (via R-tree), then Pandas handles the analytics on the reduced subset.

This pattern works well when the spatial filter reduces data to a manageable size — see [Tooling — Python](#python-geopandas) for a concrete example.

## Indexed vs Non-Indexed Mode

FlatGeobuf supports two modes:

**Indexed (default for files):**
- R-tree index is written between header and features
- Features are sorted by Hilbert curve value (preserves spatial locality)
- Enables spatial filtering and HTTP range requests

**Non-indexed (streaming mode):**
- No index section
- Features written sequentially as they arrive
- Used for pipes and progressive output (e.g., writing to stdout)
- Cannot do spatial filtering — must read all features

When writing a FlatGeobuf file with tools like GeoPandas or ogr2ogr, the index is created automatically. Non-indexed mode is mainly used in streaming pipelines where the full dataset isn't known upfront.

## When to Use FlatGeobuf

### Ideal for:

**Spatial filtering:**
- "Show me features in this bounding box" as primary query
- Interactive map panning/zooming
- Any workflow where you need a spatial subset

**Web mapping:**
- Serve data directly from static file storage (S3, CDN)
- No database server needed
- Client-side spatial filtering via JavaScript

**Cloud-optimized access:**
- HTTP range requests for partial reads
- One-time index fetch, then targeted data requests

### Not ideal for:

**Analytics and aggregations:**
- "Average area by region" requires reading all features anyway
- Row-based storage reads all columns even if you only need one
- Use [GeoParquet][geoparquet] instead

**Frequent updates:**
- Static index must be rebuilt on changes
- No append support (must rewrite file)
- Use [PostgreSQL + PostGIS][postgis] for live data

**Multi-layer datasets:**
- One geometry type per file
- Use [GeoPackage][geopackage] for packaging multiple layers

## Tooling

### Python (GeoPandas)

```python
import geopandas as gpd

# Read all features
gdf = gpd.read_file("data.fgb")

# Spatial filter — uses R-tree index, only reads matching features
gdf = gpd.read_file("data.fgb", bbox=(240000, 6620000, 280000, 6660000))

# Write (index created automatically)
gdf.to_file("output.fgb", driver="FlatGeobuf")
```

GeoPandas loads all matching features into a GeoDataFrame in memory at once. This is not progressive streaming (features aren't yielded one by one), but it does leverage the spatial index to avoid reading non-matching features from disk.

**Spatial pre-filter + analytics pattern:**

```python
# 1. Spatial pre-filter: only features in Oslo region
gdf = gpd.read_file("registrations.fgb", bbox=OSLO_BBOX)

# 2. Standard Pandas analytics on the filtered subset
counts_by_type = gdf["RASTO_NAVN"].value_counts()
avg_area = gdf.geometry.area.mean()
```

### JavaScript (flatgeobuf)

```javascript
import { deserialize } from "flatgeobuf/geojson";

// True progressive streaming — features arrive one by one
const iter = flatgeobuf.deserialize("https://example.com/data.fgb", bbox);
for await (const feature of iter) {
  map.addFeature(feature); // render each feature as it arrives
}
```

The JavaScript library provides true progressive streaming: features are fetched and yielded one by one via HTTP range requests. This is the original use case FlatGeobuf was designed for.

### QGIS / GDAL

```bash
# Convert to FlatGeobuf
ogr2ogr -f FlatGeobuf output.fgb input.gpkg

# Query with spatial filter
ogr2ogr -f GeoJSON output.json input.fgb -spat xmin ymin xmax ymax
```

QGIS can open FlatGeobuf files directly and will use the spatial index when zooming/panning.

## Key Takeaways

1. **Row-based with built-in spatial index** — Optimized for spatial queries, not analytics
2. **Zero-copy reading** — On-disk layout matches memory layout (FlatBuffers)
3. **No compression** — Deliberate trade-off for read speed
4. **Cloud-native streaming** — Fetch index once, then targeted range requests
5. **50x speedup** with bbox filtering in our [benchmark][demo-bbox] (dataset-dependent)
6. **One geometry type per file** — Separate files for points, lines, polygons

## Related Topics

- [Spatial Indexing][spatial-indexing] — How R-trees enable fast spatial queries
- [Row-Based vs Columnar Storage][row-vs-columnar] — Why FlatGeobuf is row-based
- [GeoParquet][geoparquet] — Columnar alternative (better for analytics)
- [GeoPackage][geopackage] — Row-based alternative (better for sharing/multi-layer)
- [File Formats Overview][formats] — Compare all formats

## References

- [FlatGeobuf Specification][flatgeobuf-spec]
- [FlatBuffers Documentation][flatbuffers]
- [Cloud-Native Geospatial — FlatGeobuf Guide][cng-fgb]
- [Packed Hilbert R-tree][packed-rtree]

<!-- Reference-style links -->
[spatial-indexing]: ../concepts/spatial-indexing.md
[spatial-indexing-streaming]: ../concepts/spatial-indexing.md#flatgeobuf-streaming-with-spatial-index
[row-vs-columnar]: ../concepts/row-vs-columnar.md
[geoparquet]: geoparquet.md
[geopackage]: geopackage.md
[geojson]: geojson.md
[formats]: README.md
[postgis]: ../databases/postgresql-postgis.md
[demo-bbox]: ../../demo_flatgeobuf_bbox.py

[flatgeobuf-spec]: http://flatgeobuf.org/
[flatbuffers]: https://flatbuffers.dev/
[cng-fgb]: https://guide.cloudnativegeo.org/flatgeobuf/
[packed-rtree]: https://en.wikipedia.org/wiki/Hilbert_R-tree#Packed_Hilbert_R-trees
