# GeoParquet

GeoParquet is a columnar storage format specifically designed for geospatial data, combining Apache Parquet's analytical performance with standardized geospatial metadata.

## What is GeoParquet?

GeoParquet extends the [Apache Parquet](https://parquet.apache.org/) format by adding:
- Standardized metadata for geometry columns (encoding, CRS, bbox)
- Conventions for storing spatial data types
- Interoperability across geospatial tools

**Built on Parquet's strengths:**
- Columnar storage (see [Row-Based vs Columnar Storage][row-vs-columnar])
- Excellent compression
- Cloud-optimized access patterns
- Native support in data science tools

## File Structure

### Parquet Organization

A GeoParquet file is organized into **row groups** and **columns**:

```
GeoParquet File
├─ Row Group 1 (e.g., 10,000 features)
│  ├─ id column: [1, 2, 3, ..., 10000]
│  ├─ name column: ["Building A", "Building B", ...]
│  ├─ area column: [150.5, 220.3, ...]
│  └─ geometry column: [POLYGON(...), POLYGON(...), ...]
│
├─ Row Group 2 (next 10,000 features)
│  ├─ id column: [10001, 10002, ...]
│  └─ ...
│
└─ Footer Metadata
   ├─ Schema
   ├─ Row group statistics (min/max values per column)
   └─ GeoParquet metadata (CRS, bbox, encoding)
```

**Row groups** are the key unit:
- Typical size: 64MB - 128MB of uncompressed data
- Each row group is independently readable
- Contains column chunks for all columns
- Stores statistics (min/max values) for each column

**Why row groups matter:**
When you query data, Parquet can skip entire row groups based on statistics without reading them. For example, querying "area > 1000" can skip any row group where max(area) < 1000.

## Geometry Encoding

The GeoParquet specification defines how geometry is stored in the geometry column.

### Encoding Format

Geometries are typically encoded as **Well-Known Binary (WKB)**:

```
geometry column: [
  <WKB bytes for POLYGON(...)>,
  <WKB bytes for POINT(...)>,
  <WKB bytes for LINESTRING(...)>,
  ...
]
```

**Why WKB:**
- Compact binary format
- Standard representation (ISO 19125)
- Preserves geometry type and coordinates exactly
- Efficient to parse

### GeoParquet Metadata

The file footer includes GeoParquet-specific metadata:

```json
{
  "geo": {
    "version": "1.0.0",
    "primary_column": "geometry",
    "columns": {
      "geometry": {
        "encoding": "WKB",
        "geometry_types": ["Polygon", "MultiPolygon"],
        "crs": {
          "id": {
            "authority": "EPSG",
            "code": 4326
          }
        },
        "bbox": [-180.0, -90.0, 180.0, 90.0]
      }
    }
  }
}
```

**Key metadata:**
- **encoding**: How geometries are stored (typically WKB)
- **geometry_types**: Which types are present (for validation)
- **crs**: Coordinate Reference System
- **bbox**: Overall bounding box of all geometries

## Why Analytics are Fast

GeoParquet inherits columnar storage benefits (detailed in [Row-Based vs Columnar Storage][row-vs-columnar]). Key points specific to geospatial:

### Read Only What You Need

Analytical query: "What is the average building area by city?"

```
Query needs: city column + area column
Don't need: geometry column, name column, etc.

Result: Read only 2 columns instead of all columns
```

This is the fundamental columnar advantage explained in [Row-Based vs Columnar - Analytical Queries][row-vs-columnar-analytics].

### Predicate Pushdown

Parquet stores **min/max statistics** for each column in each row group:

```
Row Group 1:
  area column: min=50.0, max=500.0

Row Group 2:
  area column: min=600.0, max=2000.0
```

Query: "Find buildings with area > 1000"

```
Row Group 1: max=500.0 < 1000 → Skip entirely ✂️
Row Group 2: max=2000.0 >= 1000 → Read and filter ✓
```

**This works over cloud storage:** Tools can read just the footer metadata, determine which row groups to read, then fetch only those byte ranges via HTTP.

### Geometry-Specific Considerations

**Bounding box filtering:**
The file metadata includes an overall bbox. Applications can:
1. Check file bbox before downloading
2. Skip files that don't overlap query area
3. Read only files with spatial overlap

**Limitation:** Unlike [FlatGeobuf's R-tree][flatgeobuf], GeoParquet doesn't have built-in spatial indexing within the file. For spatial filtering:
- Load into database (DuckDB, PostgreSQL) and create spatial index
- Or rely on partition strategies (separate files by region)

## Compression

GeoParquet achieves excellent compression through columnar organization. See [Row-Based vs Columnar - Compression][row-vs-columnar-compression] for the general principle.

### Geometry Column Compression

Geometry columns (WKB bytes) are compressed like any binary column:

```
Raw WKB: [<polygon1 bytes>, <polygon2 bytes>, ...]
    ↓
Dictionary encoding (if many identical geometries)
    ↓
Compression codec (Snappy, GZIP, ZSTD, etc.)
```

**Compression codecs:**
- **Snappy**: Fast compression/decompression, moderate ratio
- **GZIP**: Better compression, slower
- **ZSTD**: Best balance (fast + good compression)
- **LZ4**: Fastest, lower compression

### Attribute Column Compression

Attribute columns compress extremely well:

**Example: Country column in city dataset**

See [Row-Based vs Columnar - Compression][row-vs-columnar-compression] for the dictionary encoding explanation. For geospatial data, repeated values are common:
- Country names (few unique values)
- Feature types ("residential", "commercial")
- Administrative regions

## Why Updates are Slow

GeoParquet is **immutable by design**. See [Row-Based vs Columnar - Updates][row-vs-columnar-updates] for the fundamental reason.

### GeoParquet-Specific Implications

**Adding one feature:**

```
Cannot: Append to geometry column file
Reason: Columns are compressed, row groups are sealed

Must:
1. Read entire file
2. Add new feature to in-memory representation
3. Write new file with updated row groups
4. Replace old file
```

**Updating attribute:**

```
Cannot: Modify single value in compressed column
Must: Rewrite affected row group(s) or entire file
```

**Result:** GeoParquet is for "write once, read many" workflows.

### Practical Workflow

For live data:

```
Live updates → PostgreSQL + PostGIS (row-based database)
      ↓ (periodic export: nightly, weekly)
GeoParquet in data lake
      ↓
Analytics, dashboards, reports
```

## Cloud-Native Features

GeoParquet is designed for cloud storage (S3, Azure Blob, GCS).

### How Cloud Reading Works

**Traditional approach (bad):**
```
1. Download entire 5GB file from S3
2. Load into memory
3. Query for small subset
Result: Wasted bandwidth and time
```

**GeoParquet approach (good):**
```
1. HTTP GET footer metadata (~KB)
   → Read schema, row group statistics

2. Determine relevant row groups
   Query "area > 1000" → Only row groups with max(area) >= 1000

3. HTTP range requests for specific row groups
   GET bytes 1000000-2000000 (row group 5)
   GET bytes 5000000-6000000 (row group 12)

4. Read only needed columns from those row groups

Result: Download <1% of file
```

**Why this works:**
- Footer at end of file (small, one request)
- Row groups are contiguous byte ranges
- HTTP supports range requests
- Column chunks within row group also contiguous

### Tools with Cloud Support

**DuckDB:**
```sql
-- Query directly from S3, no download
SELECT city, AVG(area)
FROM read_parquet('s3://bucket/buildings.parquet')
WHERE area > 1000
GROUP BY city;
```

DuckDB reads only needed row groups and columns over HTTP.

**GeoPandas with PyArrow:**
```python
import geopandas as gpd

# Reads only needed data from cloud
gdf = gpd.read_parquet(
    's3://bucket/buildings.parquet',
    filters=[('area', '>', 1000)]
)
```

## Partitioning Strategies

For very large datasets, partition GeoParquet files:

### Spatial Partitioning

```
data/
  ├── country=USA/
  │   ├── state=CA/
  │   │   └── buildings.parquet
  │   └── state=NY/
  │       └── buildings.parquet
  └── country=UK/
      └── buildings.parquet
```

**Benefits:**
- Skip entire partitions based on query
- Better parallelization
- Easier data management

### Temporal Partitioning

```
data/
  ├── year=2023/
  │   ├── month=01/
  │   │   └── events.parquet
  │   └── month=02/
  │       └── events.parquet
  └── year=2024/
```

**Useful for:** Time-series geospatial data (sensor readings, GPS tracks)

## Tooling Ecosystem

### Reading/Writing

**Python:**
```python
import geopandas as gpd

# Read
gdf = gpd.read_parquet('data.parquet')

# Write
gdf.to_parquet('output.parquet', compression='zstd')
```

**DuckDB:**
```sql
-- Load spatial extension
LOAD spatial;

-- Read GeoParquet
SELECT * FROM read_parquet('data.parquet');

-- Create spatial index after loading for spatial queries
CREATE INDEX idx_geom ON buildings USING RTREE (geometry);
```

**R (sf package):**
```r
library(sf)

# Read
data <- st_read("data.parquet")

# Write
st_write(data, "output.parquet")
```

### Converting Formats

```bash
# Using ogr2ogr (GDAL)
ogr2ogr -f Parquet output.parquet input.gpkg
ogr2ogr -f Parquet output.parquet input.shp
```

## When to Use GeoParquet

### Ideal for:

**Analytical workloads:**
- Aggregations across millions of features
- Filtering by attributes
- Statistical analysis
- Data science pipelines

**Cloud-based workflows:**
- Data lakes (S3, Azure, GCS)
- Serverless computing
- Distributed processing (Spark, Dask)

**Read-heavy access:**
- Datasets that rarely change
- Historical/archival data
- Reference datasets

**Large datasets:**
- Millions to billions of features
- Where file size matters
- Bandwidth-constrained scenarios

### Not ideal for:

**Frequent updates:**
- Real-time data collection
- Transactional workloads
- Continuous inserts/updates
→ Use [PostgreSQL + PostGIS][postgis] instead

**Spatial-heavy queries:**
- "All features in this bounding box" as primary query
- Interactive map panning/zooming
→ Use [FlatGeobuf][flatgeobuf] with spatial index

**Small datasets:**
- Few thousand features
- Where simplicity matters more than performance
→ Use [GeoJSON][geojson] or [GeoPackage][geopackage]

## Key Takeaways

1. **Columnar storage** optimized for analytics (see [Row-Based vs Columnar][row-vs-columnar])
2. **Cloud-native** - query without full download via predicate pushdown
3. **Excellent compression** - especially for repeated attribute values
4. **Immutable** - write once, read many (updates require rewrite)
5. **No built-in spatial index** - good for analytics, less optimal for spatial filtering
6. **Standard format** - works across Python, R, DuckDB, Spark, etc.

## Related Topics

- [Row-Based vs Columnar Storage][row-vs-columnar] - Fundamental concepts
- [FlatGeobuf][flatgeobuf] - Row-based with spatial index (better for spatial queries)
- [GeoPackage][geopackage] - Row-based SQLite format (better for updates)
- [File Formats Overview][formats] - Compare all formats

## References

- [GeoParquet Specification](https://geoparquet.org/)
- [Apache Parquet Documentation](https://parquet.apache.org/docs/)
- [Cloud-Native Geospatial](https://cloudnativegeo.org/)
- [DuckDB Spatial Extension](https://duckdb.org/docs/extensions/spatial.html)

<!-- Reference-style links -->
[row-vs-columnar]: ../concepts/row-vs-columnar.md
[row-vs-columnar-analytics]: ../concepts/row-vs-columnar.md#when-columnar-is-faster-analytical-queries
[row-vs-columnar-compression]: ../concepts/row-vs-columnar.md#compression
[row-vs-columnar-updates]: ../concepts/row-vs-columnar.md#updates
[flatgeobuf]: flatgeobuf.md
[geopackage]: geopackage.md
[geojson]: geojson.md
[formats]: README.md
[postgis]: ../databases/postgresql-postgis.md
