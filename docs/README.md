# Geographic Data Storage - Learning Documentation

A comprehensive guide to understanding geographic data storage, file formats, and database technologies.

### 📚 Core Concepts
Start here to understand fundamental concepts:

- [Row-Based vs Columnar Storage](row-vs-columnar.md) - How data is physically organized
- [Spatial Indexing](spatial-indexing.md) - How spatial queries are optimized
- [Databases](databases/README.md) - Storing and managing data

### 📄 File Formats
Detailed guides on geographic file formats:

- [File Formats Overview](file-formats/README.md) - Comparison and decision guide
- [Shapefile](file-formats/shapefile.md) - The legacy standard
- [GeoPackage](file-formats/geopackage.md) - Modern single-file format
- [GeoParquet](file-formats/geoparquet.md) - Columnar format for analytics
- [FlatGeobuf](file-formats/flatgeobuf.md) - Streaming spatial format
- [GeoJSON](file-formats/geojson.md) - Web-friendly format

### ⚡ Performance
Understanding performance characteristics:

- [Performance Overview](performance/README.md) - Summary and recommendations
- [Read Performance](performance/read-performance.md) - Query speed comparisons
- [Write Performance](performance/write-performance.md) - Insert/update/delete speed
- [Use Cases & Decision Matrix](performance/use-cases.md) - Which format for which scenario

### 🗄️ Databases
Database technologies for geographic data:

- [Database Options Overview](databases/README.md) - Comparison of database systems
- [PostgreSQL + PostGIS](databases/postgresql-postgis.md) - Production-grade spatial database
- [DuckDB](databases/duckdb.md) - Analytical database for data exploration
- [Cloud Options](databases/cloud-options.md) - AWS, GCP, Azure spatial services

## Quick Navigation

### By Use Case

- **Learning & Exploration** → [DuckDB](databases/duckdb.md) + [GeoParquet](file-formats/geoparquet.md)
- **Production Applications** → [PostgreSQL + PostGIS](databases/postgresql-postgis.md)
- **Data Analytics** → [GeoParquet](file-formats/geoparquet.md) + [Read Performance](performance/read-performance.md)
- **Frequent Updates** → [PostgreSQL + PostGIS](databases/postgresql-postgis.md) + [Write Performance](performance/write-performance.md)
- **Web Mapping** → [FlatGeobuf](file-formats/flatgeobuf.md) or [GeoJSON](file-formats/geojson.md)
- **Data Sharing** → [GeoPackage](file-formats/geopackage.md)

### By Question

- "Which format should I use?" → [File Formats Overview](file-formats/README.md)
- "Why are my queries slow?" → [Spatial Indexing](concepts/spatial-indexing.md)
- "How do I handle real-time data?" → [Write Performance](performance/write-performance.md)
- "What's the difference between row and column storage?" → [Row-Based vs Columnar Storage](concepts/row-vs-columnar.md)
- "Which database for cloud deployment?" → [Cloud Options](databases/cloud-options.md)

## About This Documentation

This documentation was created as a learning resource for understanding geographic data storage technologies. It covers theoretical concepts, practical implementations, and performance considerations to help make informed decisions about data architecture.

**Last Updated:** 2026-02-04
