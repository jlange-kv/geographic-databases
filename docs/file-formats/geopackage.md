# GeoPackage

GeoPackage is a single-file SQLite database with OGC-standardized conventions for storing geospatial data. It provides full SQL query support, multiple layers, and broad tool compatibility.

## What is GeoPackage?

A `.gpkg` file is a [SQLite][sqlite] database with a `.gpkg` extension. The [OGC GeoPackage standard][ogc-gpkg] defines:

- Which **metadata tables** must exist (layer registry, coordinate reference systems, geometry column info)
- How **geometry is encoded** (GeoPackage Binary — a thin wrapper around WKB)
- How **spatial indexes** work (SQLite's built-in R-tree module)

You can open any GeoPackage with a SQLite client and query it directly. The standard just ensures that geospatial tools all agree on where to find things.

**Design goals:**
- Single portable file
- Universal tool compatibility (OGC standard)
- Full database capabilities in a file
- Store multiple data types (vector layers, raster tiles, metadata)

## Internal Structure

```
my_data.gpkg (SQLite database)
│
├── Metadata tables (defined by OGC standard)
│   ├── gpkg_contents              What layers are in this file
│   ├── gpkg_spatial_ref_sys       Coordinate reference systems
│   └── gpkg_geometry_columns      Which columns hold geometry
│
├── Feature tables (your actual data)
│   ├── buildings                  Geometry + attributes as rows
│   ├── roads                      Another layer
│   └── land_use                   As many layers as you need
│
└── Spatial index tables (optional)
    ├── rtree_buildings_geom       R-tree for buildings layer
    └── rtree_roads_geom           R-tree for roads layer
```

### Feature Tables

Each layer is a regular SQLite table. One column holds geometry as binary, the rest are normal attribute columns:

```
buildings table:
┌────┬──────────────────┬─────────────┬──────┬──────────┐
│ id │ geom (GPB binary)│ name        │ area │ type     │
├────┼──────────────────┼─────────────┼──────┼──────────┤
│  1 │ <polygon bytes>  │ City Hall   │ 2500 │ public   │
│  2 │ <polygon bytes>  │ Library     │  800 │ public   │
│  3 │ <polygon bytes>  │ Apartment A │  400 │ housing  │
└────┴──────────────────┴─────────────┴──────┴──────────┘
```

This is [row-based storage][row-vs-columnar]: each row contains the complete feature (geometry + all attributes). Reading a feature is fast; reading a single column across all features requires scanning every row.

### Geometry Encoding

GeoPackage stores geometry as **GeoPackage Binary (GPB)**, which wraps standard WKB with a small header:

```
GPB = GeoPackage header (8 bytes) + WKB geometry
       │
       ├── Magic number (2 bytes): "GP"
       ├── Version (1 byte)
       ├── Flags (1 byte): byte order, envelope type
       └── SRS ID (4 bytes): coordinate reference system
```

The WKB payload is the same format used by PostGIS and GeoParquet, making conversion between formats straightforward.

## SQL Query Support

Since GeoPackage is SQLite, you get full SQL:

```sql
-- Attribute queries
SELECT name, area FROM buildings WHERE type = 'public';

-- Aggregations
SELECT type, COUNT(*), AVG(area) FROM buildings GROUP BY type;

-- Joins across layers
SELECT b.name, l.category
FROM buildings b
JOIN land_use l ON ST_Within(b.geom, l.geom);
```

### Updates and Transactions

Unlike [GeoParquet][geoparquet] and [FlatGeobuf][flatgeobuf] which are immutable, GeoPackage supports in-place modifications:

```sql
-- Insert
INSERT INTO buildings (geom, name, area, type)
VALUES (GPB_geometry, 'New Building', 500, 'commercial');

-- Update
UPDATE buildings SET area = 550 WHERE name = 'New Building';

-- Delete
DELETE FROM buildings WHERE name = 'Old Building';
```

SQLite provides **ACID transactions** — changes are atomic, consistent, isolated, and durable. If your program crashes mid-write, the database won't be corrupted.

## Spatial Index

GeoPackage supports **R-tree spatial indexes** using SQLite's built-in R-tree module. The concept is the same as [FlatGeobuf's R-tree][spatial-indexing] — hierarchical bounding boxes that enable fast spatial queries.

**Key difference from FlatGeobuf:** The spatial index is **optional and managed by the database engine**. Tools may or may not create one when writing data.

```sql
-- Spatial query (uses R-tree if available)
SELECT * FROM buildings
WHERE buildings.geom IN (
    SELECT id FROM rtree_buildings_geom
    WHERE minx <= 280000 AND maxx >= 240000
    AND miny <= 6660000 AND maxy >= 6620000
);
```

In practice, most GIS tools (QGIS, GDAL, GeoPandas) handle spatial index creation and querying transparently.

## Multiple Layers

A single GeoPackage can contain any number of layers with different geometry types:

```
norway_data.gpkg
├── municipalities   (MultiPolygon — administrative boundaries)
├── roads            (LineString — road network)
├── cities           (Point — city locations)
├── elevation_tiles  (raster tiles)
└── metadata         (non-spatial attribute table)
```

This is a significant advantage over formats that are limited to one layer or one geometry type per file ([FlatGeobuf][flatgeobuf], [Shapefile][shapefile]).

The `gpkg_contents` metadata table lists all layers:

```sql
SELECT table_name, data_type, srs_id FROM gpkg_contents;
-- municipalities | features | 25833
-- roads          | features | 25833
-- elevation      | tiles    | 25833
```

## Cloud Access Limitations

GeoPackage is **not cloud-optimized**. Unlike [FlatGeobuf][flatgeobuf] and [GeoParquet][geoparquet], you cannot efficiently query a GeoPackage over HTTP:

- **SQLite requires random access** to the file (page reads at arbitrary offsets)
- **No predictable byte ranges** — data and index pages are scattered throughout the file
- **Must download the entire file** before querying

```
Cloud-optimized (FlatGeobuf, GeoParquet):
  HTTP range request → Read specific bytes → Get specific features

GeoPackage:
  Download entire file → Open as SQLite → Query locally
```

For cloud scenarios, convert to GeoParquet (analytics) or FlatGeobuf (spatial queries) and keep GeoPackage for local work and sharing.

## Comparison with PostGIS

GeoPackage and [PostGIS][postgis] are conceptually similar — both are SQL databases with spatial extensions. The difference is file vs server:

| | GeoPackage | PostGIS |
|---|---|---|
| **Architecture** | Single file (SQLite) | Client-server (PostgreSQL) |
| **Portability** | Email it, put on USB | Requires running server |
| **Concurrent access** | Single writer | Multiple readers and writers |
| **Scale** | Good for small-medium datasets | Handles billions of features |
| **Spatial functions** | Basic (via SpatiaLite) | Comprehensive (ST_Buffer, ST_Union, ...) |
| **Setup** | None — just a file | Install and configure server |

**Rule of thumb:** Use GeoPackage when you need a portable file. Use PostGIS when you need a shared database with concurrent access or advanced spatial operations.

## When to Use GeoPackage

### Ideal for:

**Sharing and archiving:**
- Send data to colleagues (single file, nothing to lose)
- Archive datasets for long-term storage
- Exchange data between different GIS tools

**Multi-layer packaging:**
- Bundle related layers into one file (buildings + roads + boundaries)
- Include metadata alongside the data

**Desktop GIS workflows:**
- Working in QGIS or ArcGIS
- Need to edit features interactively
- Want SQL query capability without a server

**Shapefile replacement:**
- Everything Shapefile does, but without the limitations

### Not ideal for:

**Cloud-based workflows:**
- Must download entire file before querying
- Use [GeoParquet][geoparquet] or [FlatGeobuf][flatgeobuf] instead

**Large-scale analytics:**
- Row-based storage is slow for column-wide aggregations
- Use [GeoParquet][geoparquet] instead

**Web mapping / streaming:**
- Can't stream partial data over HTTP
- Use [FlatGeobuf][flatgeobuf] instead

**Concurrent multi-user access:**
- SQLite is single-writer
- Use [PostGIS][postgis] instead

## Tooling

### Python (GeoPandas)

```python
import geopandas as gpd

# Read a specific layer
gdf = gpd.read_file("data.gpkg", layer="buildings")

# List available layers
import fiona
fiona.listlayers("data.gpkg")

# Write (creates layer in GeoPackage)
gdf.to_file("output.gpkg", layer="buildings", driver="GPKG")

# Append another layer to the same file
roads.to_file("output.gpkg", layer="roads", driver="GPKG")
```

### SQL (direct SQLite access)

```python
import sqlite3

conn = sqlite3.connect("data.gpkg")
cursor = conn.execute("SELECT name, area FROM buildings WHERE type = 'public'")
for row in cursor:
    print(row)
```

### QGIS / GDAL

```bash
# Convert from Shapefile
ogr2ogr -f GPKG output.gpkg input.shp

# Add another layer to existing GeoPackage
ogr2ogr -f GPKG -append output.gpkg roads.shp -nln roads

# Query with SQL
ogr2ogr -f GeoJSON output.json input.gpkg -sql "SELECT * FROM buildings WHERE area > 1000"
```

## Key Takeaways

1. **SQLite database** — Full SQL support, ACID transactions, single file
2. **Row-based storage** — Fast for complete features, slower for analytics (see [Row-Based vs Columnar][row-vs-columnar])
3. **Multiple layers** — Bundle different geometry types and raster data in one file
4. **Updatable** — Insert, update, delete individual features (unlike GeoParquet/FlatGeobuf)
5. **Universal support** — Works in QGIS, ArcGIS, GDAL, Python, R, and more
6. **Not cloud-optimized** — Must download entirely before querying
7. **Shapefile replacement** — Same use cases, none of the limitations

## Related Topics

- [Row-Based vs Columnar Storage][row-vs-columnar] — Why GeoPackage is row-based
- [Spatial Indexing][spatial-indexing] — How R-tree indexes work
- [FlatGeobuf][flatgeobuf] — Row-based alternative (cloud-optimized, spatial streaming)
- [GeoParquet][geoparquet] — Columnar alternative (better for analytics)
- [Shapefile][shapefile] — Legacy format that GeoPackage replaces
- [PostGIS][postgis] — Server-based alternative for concurrent/large-scale use
- [File Formats Overview][formats] — Compare all formats

## References

- [OGC GeoPackage Standard][ogc-gpkg]
- [GeoPackage.org](https://www.geopackage.org/)
- [SQLite Documentation][sqlite]
- [SpatiaLite](https://www.gaia-gis.it/fossil/libspatialite/index)
- [Switch from Shapefile](https://switchfromshapefile.org/)

<!-- Reference-style links -->
[row-vs-columnar]: ../concepts/row-vs-columnar.md
[spatial-indexing]: ../concepts/spatial-indexing.md
[flatgeobuf]: flatgeobuf.md
[geoparquet]: geoparquet.md
[geojson]: geojson.md
[shapefile]: shapefile.md
[formats]: README.md
[postgis]: ../databases/postgresql-postgis.md

[ogc-gpkg]: https://www.ogc.org/standard/geopackage/
[sqlite]: https://www.sqlite.org/
