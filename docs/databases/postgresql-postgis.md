# PostgreSQL + PostGIS

PostGIS is an extension that adds spatial data types and functions to PostgreSQL, turning it into a full-featured geographic database.

## What is a Database Server?

Geographic data can be stored in **files** or in a **database server**. These are fundamentally different approaches:

```
File approach:
  Your program → opens file → reads data → closes file
  One user at a time, no server needed

Database approach:
  PostgreSQL server (running continuously)
       ↑          ↑          ↑
   Web app     Analyst    QGIS user
   (writes)    (queries)  (visualizes)
```

A file (whether [FlatGeobuf][flatgeobuf], [GeoParquet][geoparquet], [GeoPackage][geopackage], or any other format) is opened by one program at a time. A database server is a separate process that runs continuously, clients connect to it over a network and send SQL queries. The server processes queries, manages concurrent access, and ensures data integrity.

File-based formats can still be served over the web. For example, [FlatGeobuf][flatgeobuf] files can be hosted on a static file server (S3, nginx, CDN) and clients filter data spatially using HTTP range requests — no server-side processing needed. Similarly, [GeoParquet][geoparquet] files can be queried remotely using predicate pushdown. But in both cases the server just serves bytes. It can't combine spatial and attribute filters, enforce data integrity, or handle writes from multiple users. That's where a database server comes in.

## What PostGIS Adds to PostgreSQL

PostgreSQL by itself has no concept of geography. PostGIS adds:

### Spatial Data Types

```sql
-- geometry type: for projected coordinates (meters, etc.)
CREATE TABLE buildings (
    id SERIAL PRIMARY KEY,
    name TEXT,
    area DOUBLE PRECISION,
    geom GEOMETRY(Polygon, 25833)  -- Polygon in EPSG:25833 (UTM 33N)
);

-- geography type: for lat/lon with geodesic calculations
CREATE TABLE cities (
    id SERIAL PRIMARY KEY,
    name TEXT,
    geom GEOGRAPHY(Point, 4326)  -- Point in WGS84
);
```

The `geometry` type works in projected coordinates (flat math, fast). The `geography` type works on the sphere (accurate distances over large areas, slower).

### Spatial Functions

PostGIS provides hundreds of functions. Key categories:

**Measurements:**
```sql
-- Distance between two points
SELECT ST_Distance(a.geom, b.geom) FROM cities a, cities b
WHERE a.name = 'Oslo' AND b.name = 'Bergen';

-- Area of a polygon
SELECT name, ST_Area(geom) FROM buildings;
```

**Relationships:**
```sql
-- Which buildings are within a municipality?
SELECT b.name FROM buildings b, municipalities m
WHERE m.name = 'Oslo' AND ST_Within(b.geom, m.geom);

-- Do these two polygons overlap?
SELECT ST_Intersects(a.geom, b.geom) FROM zones a, zones b;
```

**Geometry operations:**
```sql
-- Buffer a road by 50 meters
SELECT ST_Buffer(geom, 50) FROM roads WHERE name = 'E18';

-- Intersection of two polygon layers
SELECT ST_Intersection(a.geom, b.geom) FROM zones a, zones b
WHERE ST_Intersects(a.geom, b.geom);

-- Union overlapping polygons into one
SELECT ST_Union(geom) FROM parcels WHERE owner = 'Municipality';
```

These operations would require loading everything into memory with file-based workflows. PostGIS does them server-side, which matters when datasets don't fit in memory.

### Spatial Indexes

PostGIS uses **GiST indexes** (Generalized Search Trees) — PostgreSQL's framework for building R-tree-like structures. Same concept as [FlatGeobuf's R-tree][spatial-indexing]: hierarchical bounding boxes, branch pruning.

```sql
-- Create spatial index
CREATE INDEX idx_buildings_geom ON buildings USING GIST (geom);

-- Create attribute index
CREATE INDEX idx_buildings_area ON buildings (area);
```

Key difference from file-based indexes:

- **Dynamic:** Insert a new feature and the index updates automatically
- **Multiple indexes:** Create indexes on any column, the query planner combines them
- **No rebuild needed:** FlatGeobuf's index is static (baked at file creation); PostGIS indexes adapt to changes

```sql
-- PostGIS combines spatial + attribute indexes automatically
SELECT * FROM buildings
WHERE ST_Within(geom, oslo_boundary)  -- uses spatial index
AND area > 1000                        -- uses attribute index
AND type = 'commercial';               -- can add more indexes
```

This is the key advantage over file-based spatial filtering. With FlatGeobuf, you can only filter by bounding box. With PostGIS, you can combine any number of conditions.

## Why Use a Database Instead of Files?

### Concurrent Access

Multiple users and applications can read and write simultaneously:

```
Web application → INSERT new features
Analyst         → SELECT aggregations     (all at the same time)
QGIS user       → UPDATE geometries
Backup script   → pg_dump
```

With file-based formats:
- GeoPackage: single writer at a time (SQLite limitation)
- FlatGeobuf/GeoParquet: immutable — can't write at all without replacing the file

### Live Updates

Insert, update, and delete individual features without rewriting anything:

```sql
-- Insert
INSERT INTO buildings (name, area, geom)
VALUES ('New Office', 1200, ST_GeomFromText('POLYGON(...)', 25833));

-- Update
UPDATE buildings SET area = 1300 WHERE name = 'New Office';

-- Delete
DELETE FROM buildings WHERE name = 'Old Warehouse';
```

Indexes update automatically. No file rebuild, no re-export.

### Data Integrity

PostgreSQL enforces rules at the database level:

```sql
-- Every building must have a positive area
ALTER TABLE buildings ADD CONSTRAINT positive_area CHECK (area > 0);

-- Foreign key: every building references a valid municipality
ALTER TABLE buildings ADD CONSTRAINT fk_municipality
    FOREIGN KEY (municipality_id) REFERENCES municipalities(id);
```

With files, these rules only exist in application code — nothing stops someone from writing invalid data.

### Complex Queries Across Tables

```sql
-- "Average building area by municipality, only for commercial buildings"
SELECT m.name, AVG(b.area)
FROM buildings b
JOIN municipalities m ON ST_Within(b.geom, m.geom)
WHERE b.type = 'commercial'
GROUP BY m.name
ORDER BY AVG(b.area) DESC;
```

With files, you'd load both datasets into GeoPandas and do a spatial join in memory. With PostGIS, the database handles it — including cases where the data is too large for memory.

## Static File Serving vs Database Server

A common question: when do you need PostGIS instead of just hosting FlatGeobuf files on a static server?

### Static file approach (FlatGeobuf on S3/CDN)

```
Browser → HTTP range requests → Static server (S3, nginx)
          Client does spatial filtering locally
```

- No server-side processing
- Cheap to host (just file storage)
- Only spatial filtering (bounding box)
- Read-only
- No attribute filtering built in

### Database approach (PostGIS)

```
Browser → API request → Application server → PostGIS
          Server does filtering and returns results
```

- Server processes queries
- Requires running database + application
- Spatial + attribute + join queries
- Read and write
- Any query you can express in SQL

### When static files are enough

- Read-only web map
- Spatial filtering is the primary query ("show features in this area")
- Data rarely changes (rebuild files when it does)
- You control the UI and know what filters users need

### When you need PostGIS

- Users submit or edit data
- Combined spatial + attribute queries ("commercial buildings > 1000m² near Oslo")
- Complex spatial operations (buffer, intersect, union)
- Multiple applications share the same data
- Data changes frequently
- Joins across different datasets

## How Geometry is Stored

PostGIS stores geometry as **EWKB** (Extended Well-Known Binary) in a regular PostgreSQL column. Similar to [GeoPackage's GPB][geopackage] — binary geometry in a table column.

```
buildings table (PostgreSQL):
┌────┬──────────────────┬─────────┬──────┬──────────┐
│ id │ geom (EWKB)      │ name    │ area │ type     │
├────┼──────────────────┼─────────┼──────┼──────────┤
│  1 │ <polygon bytes>  │ City H. │ 2500 │ public   │
│  2 │ <polygon bytes>  │ Library │  800 │ public   │
└────┴──────────────────┴─────────┴──────┴──────────┘
```

Row-based, like GeoPackage. But PostgreSQL is built for concurrent access, transactions, and scale — things SQLite (GeoPackage's engine) isn't designed for.

## Architecture: Where PostGIS Fits

### Hybrid Architecture

PostGIS handles live data; export to analytical formats for heavy analytics:

```
Live updates → PostGIS (transactional, row-based)
      ↓ (periodic export: nightly, weekly)
GeoParquet files (analytical, columnar)
      ↓
DuckDB / Pandas for dashboards, reports, statistics
```

See [Row-Based vs Columnar — Hybrid Architecture][hybrid-architecture] for more on this pattern.

### Web Application Stack

```
Browser (map)
    ↓
API server (Flask, FastAPI, Express)
    ↓
PostGIS database
    ↓
Optional: FlatGeobuf export for static layers
```

Dynamic layers (user-edited data) go through PostGIS. Static reference layers (country boundaries, base maps) can be served as FlatGeobuf files.

## Comparison with GeoPackage

Both are SQL databases with spatial support, but serve different roles:

| | GeoPackage | PostGIS |
|---|---|---|
| **Engine** | SQLite (embedded) | PostgreSQL (client-server) |
| **Deployment** | Just a file | Install and run server |
| **Concurrent writes** | No (single writer) | Yes (multiple writers) |
| **Scale** | Small-medium datasets | Billions of features |
| **Spatial functions** | Basic (SpatiaLite) | Comprehensive (hundreds) |
| **Network access** | Copy the file | Connect over network |
| **Maintenance** | None | Backups, updates, monitoring |
| **Best for** | Sharing, archiving | Production applications |

## Tooling

### Python (psycopg2 + Shapely)

```python
import psycopg2
from shapely.geometry import shape
from shapely import wkb

conn = psycopg2.connect("dbname=geodata user=postgres")
cur = conn.cursor()

cur.execute("""
    SELECT name, area, ST_AsBinary(geom)
    FROM buildings
    WHERE ST_Within(geom, ST_MakeEnvelope(240000, 6620000, 280000, 6660000, 25833))
    AND area > 500
""")

for name, area, geom_bytes in cur:
    geometry = wkb.loads(geom_bytes)
    print(f"{name}: {area}m², {geometry.geom_type}")
```

### Python (GeoPandas)

```python
import geopandas as gpd
from sqlalchemy import create_engine

engine = create_engine("postgresql://postgres@localhost/geodata")

# Read with SQL query
gdf = gpd.read_postgis(
    "SELECT * FROM buildings WHERE area > 500",
    engine,
    geom_col="geom"
)

# Write GeoDataFrame to PostGIS
gdf.to_postgis("buildings", engine, if_exists="replace")
```

### QGIS

QGIS can connect directly to PostGIS as a data source. Layers are loaded on demand — only the features visible in the current map extent are fetched.

### Command Line (ogr2ogr)

```bash
# Import Shapefile into PostGIS
ogr2ogr -f PostgreSQL PG:"dbname=geodata" input.shp

# Import FlatGeobuf
ogr2ogr -f PostgreSQL PG:"dbname=geodata" input.fgb

# Export PostGIS table to GeoParquet
ogr2ogr -f Parquet output.parquet PG:"dbname=geodata" -sql "SELECT * FROM buildings"
```

### psql (PostgreSQL CLI)

```sql
-- Connect
psql -d geodata

-- Enable PostGIS
CREATE EXTENSION postgis;

-- Check PostGIS version
SELECT PostGIS_Full_Version();

-- Import data from file (using COPY or ogr2ogr is more common)
```

## Operational Considerations

Running PostGIS means running a PostgreSQL server. Key things to be aware of:

**Setup:**
- Install PostgreSQL + PostGIS extension
- Create database and enable PostGIS (`CREATE EXTENSION postgis;`)
- Configure connection settings, authentication

**Maintenance:**
- Regular backups (`pg_dump`)
- Monitor disk space and performance
- Update PostgreSQL and PostGIS versions
- Vacuum and analyze tables periodically

**Alternatives for lighter setups:**
- Docker: `docker run -e POSTGRES_PASSWORD=pass postgis/postgis` gets you a running instance quickly
- Cloud managed: AWS RDS, Google Cloud SQL, Azure Database for PostgreSQL all offer PostGIS

## Key Takeaways

1. **Client-server database** — Runs as a service, clients connect over network
2. **Spatial + attribute queries** — Combine any conditions, database optimizes automatically
3. **Dynamic indexes** — Create on any column, update automatically on writes
4. **Concurrent access** — Multiple users reading and writing simultaneously
5. **Complex spatial operations** — Buffer, intersect, union, etc. done server-side
6. **Operational overhead** — Must install, configure, and maintain a server
7. **Use when files aren't enough** — Live data, multi-user access, complex queries

## Related Topics

- [Spatial Indexing][spatial-indexing] — How R-tree indexes work (applies to PostGIS GiST indexes)
- [Row-Based vs Columnar Storage][row-vs-columnar] — PostGIS is row-based; export to GeoParquet for analytics
- [GeoPackage][geopackage] — File-based SQL alternative (SQLite, single user)
- [FlatGeobuf][flatgeobuf] — Static file alternative for read-only spatial queries
- [GeoParquet][geoparquet] — Columnar format for analytical exports
- [File Formats Overview][formats] — When files are sufficient vs when you need a database

## References

- [PostGIS Documentation](https://postgis.net/documentation/)
- [PostGIS Introduction Workshop](https://postgis.net/workshops/postgis-intro/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [PostGIS Docker Image](https://hub.docker.com/r/postgis/postgis)
- [PostGIS Spatial Functions Reference](https://postgis.net/docs/reference.html)

<!-- Reference-style links -->
[spatial-indexing]: ../concepts/spatial-indexing.md
[row-vs-columnar]: ../concepts/row-vs-columnar.md
[hybrid-architecture]: ../concepts/row-vs-columnar.md#pattern-1-hybrid-architecture
[flatgeobuf]: ../file-formats/flatgeobuf.md
[geoparquet]: ../file-formats/geoparquet.md
[geopackage]: ../file-formats/geopackage.md
[geojson]: ../file-formats/geojson.md
[formats]: ../file-formats/README.md
