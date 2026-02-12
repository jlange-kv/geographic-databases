# File Format Decision Tree

A simple guide to choosing the right geographic file format.

For detailed comparison and technical details, see [File Formats Overview][overview].

## Decision Flow

```
What is your primary use case?
│
├─→ [ANALYTICS & DATA SCIENCE]
│   │
│   ├─→ Do you need frequent updates/writes?
│       ├─→ YES: Use PostgreSQL + PostGIS (database)
│       │         • Optimized for transactional writes
│       │         See: ../databases/postgresql-postgis.md
│       │
│       └─→ NO:  Use GeoParquet
│                 • Columnar = fast aggregations/statistics
│                 • 5-10x better compression
│                 • Best for read-heavy analytical workflows
│                 • Works great with cloud storage (S3, etc.)
│                 See: geoparquet.md
│
├─→ [WEB MAPPING / STREAMING]
│   │
│   ├─→ Is your dataset small (< 10,000 features)?
│       ├─→ YES: Use GeoJSON
│       │         • Simple, JavaScript-friendly
│       │         • Human-readable
│       │         See: geojson.md
│       │
│       └─→ NO:  Use FlatGeobuf
│                 • Built-in spatial index
│                 • Stream partial data over HTTP
│                 • Fast spatial filtering
│                 • Cloud-optimized
│                 See: flatgeobuf.md
│
├─→ [SHARING / ARCHIVING / GENERAL PURPOSE]
│   │
│   └─→ Use GeoPackage
│       • Single file (easy to share)
│       • Universal support (works in QGIS, ArcGIS, Python, etc.)
│       • Can store multiple layers
│       • OGC standard
│       See: geopackage.md
│
├─→ [DATA STORAGE LOCATION]
│   │
│   ├─→ Cloud storage (S3, Azure Blob, GCS)?
│   │   └─→ Use GeoParquet or FlatGeobuf
│   │       • Both support streaming/partial reads
│   │       • GeoParquet: Better for analytics
│   │       • FlatGeobuf: Better for spatial filtering
│   │       See: ../concepts/row-vs-columnar.md
│   │
│   └─→ Local files?
│       └─→ Any format works, choose by use case above
│
├─→ [TOOLS & ECOSYSTEM]
│   │
│   ├─→ Using Python/Pandas/DuckDB?
│   │   └─→ Use GeoParquet
│   │       • Best integration with data science tools
│   │       • Native support in DuckDB
│   │       See: ../databases/duckdb.md
│   │
│   ├─→ Using traditional GIS (QGIS, ArcGIS)?
│   │   └─→ Use GeoPackage or Shapefile
│   │       • Universal support in all GIS software
│   │       • GeoPackage preferred (modern standard)
│   │       See: geopackage.md
│   │
│   ├─→ Using JavaScript/web frameworks?
│   │   └─→ Use GeoJSON (small data) or FlatGeobuf (large data)
│   │       • GeoJSON: Native JSON parsing
│   │       • FlatGeobuf: Efficient streaming for maps
│   │       See: geojson.md, flatgeobuf.md
│   │
│   └─→ Using SQL databases?
│       └─→ Use PostgreSQL + PostGIS
│           • Full spatial database capabilities
│           • ACID compliance
│           See: ../databases/postgresql-postgis.md
│
└─→ [LEGACY COMPATIBILITY]
    │
    └─→ Use Shapefile (only if required)
        • Only when you must support old systems
        • Has severe limitations (2GB limit, 10-char column names)
        • Try to avoid for new work
        See: shapefile.md
```

---

**Related:** [File Formats Overview][overview] • @Snippet:links:performanceOverview@ • [Database Options][databases]

[overview]: README.md
[databases]: ../databases/README.md
