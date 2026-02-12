# Geographic File Formats Overview

This guide compares different file formats for storing vector geographic data.

## Quick Comparison Table

| Format | Type | Best For | File Structure | Compression | Cloud-Ready |
|--------|------|----------|----------------|-------------|-------------|
| [GeoParquet][geoparquet] | Columnar | Analytics, big data | Single file | Excellent | ✅ |
| [GeoPackage][geopackage] | Row-based (SQLite) | Sharing, archiving | Single file | Good | ⚠️ |
| [FlatGeobuf][flatgeobuf] | Row-based | Spatial filtering, streaming | Single file | Good | ✅ |
| [GeoJSON][geojson] | Text | Web APIs, small data | Single file | None | ⚠️ |
| [Shapefile][shapefile] | Row-based | Legacy compatibility | Multiple files | Minimal | ❌ |

See the [Decision Tree][decision-tree] for a guided selection process.

**Need concurrent writes, complex spatial operations, or multi-user access?** File formats may not be enough — consider a database like [PostgreSQL + PostGIS][postgis].

## Storage Architecture

Understanding how data is organized helps you choose the right format:

- **Row-based formats** (Shapefile, FlatGeobuf, GeoJSON, GeoPackage): Store complete features together → Fast for retrieving whole records
- **Columnar formats** (GeoParquet): Store each attribute separately → Fast for analytics across many records

See: [Row-Based vs Columnar Storage][row-vs-columnar]

## Format Guide

#### [GeoParquet][geoparquet] - Great for Analytics

**Key strengths:**
- Columnar storage = extremely fast analytical queries
- Excellent compression (5-10x smaller than GeoJSON)
- Cloud-native (query without downloading entire file)
- Immutable by design (perfect for "write once, read many")

**Trade-offs:**
- Not suitable for frequent updates (must rewrite entire file)
- Less optimized for spatial filtering compared to FlatGeobuf
- Newer format (growing but not yet universal tool support)

**Use when:**
- Analyzing large datasets (millions of features)
- Running aggregations and statistics
- Working with cloud data lakes
- Using modern data tools (DuckDB, Pandas, Spark)

**Learn more:** [GeoParquet details][geoparquet] • [Read Performance][read-perf] • [Write Performance][write-perf]

---

#### [GeoPackage][geopackage] - Universal Sharing Format

**Key strengths:**
- Single file (nothing gets lost, easy to transfer)
- OGC standard (works in QGIS, ArcGIS, Python, web tools)
- SQLite database (full SQL query support, no size limits)
- Multi-purpose (multiple layers, raster data, metadata)

**Trade-offs:**
- Must download entirely for cloud access (not streaming-friendly)
- Slower than columnar formats for large-scale analytics
- Row-based storage (reads all columns even if you only need one)

**Use when:**
- Sharing data with colleagues or external parties
- Need to package multiple layers together
- Want both vector and raster data in one file
- Need broad tool compatibility

**Learn more:** [GeoPackage details][geopackage]

---

#### [FlatGeobuf][flatgeobuf] - Great for Streaming

**Key strengths:**
- Built-in R-tree spatial index
- Stream partial data over network (HTTP range requests)
- Fast spatial filtering
- Cloud-optimized for remote access

**Trade-offs:**
- Not optimized for analytical queries (row-based storage)
- Newer format with less ecosystem support
- Less compression than Parquet

**Use when:**
- Building interactive web maps
- Need fast spatial filtering ("show me features in this bounding box")
- Streaming data over HTTP
- Cloud-deployed mapping applications

**Learn more:** [FlatGeobuf details][flatgeobuf]

---

### Special Purpose Formats

#### [GeoJSON][geojson] - Web API Standard

**Key strengths:**
- Human-readable text format (JSON)
- Native JavaScript support
- Simple and easy to debug

**Trade-offs:**
- Large file sizes (no compression, verbose text)
- Slow for large data (must parse entire text file)
- Limited coordinate precision

**Use when:**
- Small datasets (< 10,000 features)
- Web APIs and JavaScript applications
- Human-readable output needed
- Prototyping and development

**Learn more:** [GeoJSON details][geojson]

---

### Legacy Formats

#### [Shapefile][shapefile] - For older systems

**Key limitations:**
- 2GB file size limit (hard constraint)
- 10-character column names (fixed field size)
- Multiple files (.shp, .shx, .dbf, .prj) - easy to lose pieces
- No mixed geometries

**Use when:**
- Required for legacy system compatibility
- No other option accepted by recipient

**Modern alternative:** Use [GeoPackage][geopackage] - specifically designed as the Shapefile replacement.

**Learn more:** [Shapefile details][shapefile] • [Switch from Shapefile](https://switchfromshapefile.org/)

---

## Data Type Support

All listed formats support **vector data**:
- Points (cities, sensors, landmarks)
- LineStrings (roads, rivers, routes)
- Polygons (boundaries, buildings, lakes)
- MultiGeometries (archipelagos, highway systems)
- Attribute data (names, populations, measurements)

**Special case:** Only [GeoPackage][geopackage] also supports raster data (satellite imagery, elevation models)

For raster-focused work, see: [Vector vs Raster Data][vector-vs-raster]

## References and Standards

- [GeoParquet Specification](https://geoparquet.org/)
- [FlatGeobuf Specification](http://flatgeobuf.org/)
- [GeoPackage Standard (OGC)](https://www.geopackage.org/)
- [GeoJSON Specification (RFC 7946)](https://tools.ietf.org/html/rfc7946)
- [Switch from Shapefile Campaign](https://switchfromshapefile.org/)

## Related Topics

- [Decision Tree][decision-tree] - Quick format selection guide
- [Row-Based vs Columnar Storage][row-vs-columnar] - Fundamental storage concepts
- [Spatial Indexing][spatial-index] - How spatial queries are optimized
- @Snippet:links:readPerformance@ - Benchmarks and query speed
- @Snippet:links:writePerformance@ - Insert/update/delete speed
- @Snippet:links:useCases@ - Real-world scenario patterns
- [Database Options][databases] - When to use databases vs files

<!-- Reference-style links -->
[decision-tree]: decision-tree.md
[geoparquet]: geoparquet.md
[geopackage]: geopackage.md
[flatgeobuf]: flatgeobuf.md
[geojson]: geojson.md
[shapefile]: shapefile.md
[row-vs-columnar]: ../concepts/row-vs-columnar.md
[spatial-index]: ../concepts/spatial-indexing.md
[databases]: ../databases/README.md
[duckdb]: ../databases/duckdb.md
[postgis]: ../databases/postgresql-postgis.md