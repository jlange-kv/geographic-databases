# Geographic Data Storage - Overview

A guide to understanding geographic data storage, file formats, and database technologies.

### Core Concepts
Start here to understand fundamental concepts:

- [Row-Based vs Columnar Storage](row-vs-columnar.md) - How data is physically organized
- [Spatial Indexing](spatial-indexing.md) - How spatial queries are optimized
- [Databases](databases/README.md) - Storing and managing data
- [Query performance and database design](query-performance.md) - Optimising the performance of a database

### File Formats
Detailed guides on geographic file formats:

- [File Formats Overview](file-formats/README.md) - Comparison and decision guide
- [Shapefile](file-formats/shapefile.md) - The legacy standard
- [GeoPackage](file-formats/geopackage.md) - Modern single-file format
- [GeoParquet](file-formats/geoparquet.md) - Columnar format for analytics
- [FlatGeobuf](file-formats/flatgeobuf.md) - Streaming spatial format
- [GeoJSON](file-formats/geojson.md) - Web-friendly format

### Performance
Understanding performance characteristics:

- @Snippet:links:performanceOverview@ - Summary and recommendations
- @Snippet:links:readPerformance@ - Query speed comparisons
- @Snippet:links:writePerformance@ - Insert/update/delete speed
- @Snippet:links:perFormanceDecisionMatrix@ - Which format for which scenario

### Databases
Database technologies for geographic data:

- @Snippet:links:databaseOptionsOverview@ - Comparison of database systems
- [PostgreSQL + PostGIS](databases/postgresql-postgis.md) - Production-grade spatial database
- @Snippet:links:duckDB@ - Analytical database for data exploration
- @Snippet:links:cloudOptions@ - AWS, GCP, Azure spatial services
## Quick Navigation

### By Use Case

- **Learning & Exploration** → [DuckDB](databases/duckdb.md) + [GeoParquet](file-formats/geoparquet.md)
- **Production Applications** → [PostgreSQL + PostGIS](databases/postgresql-postgis.md)
- **Data Analytics** → [GeoParquet](file-formats/geoparquet.md) + @Snippet:links:readPerformance@
- **Frequent Updates** → [PostgreSQL + PostGIS](databases/postgresql-postgis.md) + @Snippet:links:writePerformance@
- **Web Mapping** → [FlatGeobuf](file-formats/flatgeobuf.md) or [GeoJSON](file-formats/geojson.md)
- **Data Sharing** → [GeoPackage](file-formats/geopackage.md)

### By Question

- "Which format should I use?" → [File Formats Overview](file-formats/README.md)
- "Why are my queries slow?" → [Spatial Indexing](concepts/spatial-indexing.md)
- "How do I handle real-time data?" → @Snippet:links:writePerformance@
- "What's the difference between row and column storage?" → [Row-Based vs Columnar Storage](concepts/row-vs-columnar.md)
- "Which database for cloud deployment?" → @Snippet:links:cloudOptions@
