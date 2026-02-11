# Relational Databases

**Relational databases** store data as rows and columns in tables with predefined schemas. Tables are linked within a database using relations and queried using the [SQL query language][sql-language]. Relational databases can be [row-based](row-vs-columnar.md) (SQLite/[GeoPackage](geopackage.md)) or [column-based](row-vs-columnar.md) ([DuckDB](duckdb.md)).

## Tables

The building blocks of relational databases are **tables**. A table is a structured collection of rows and columns, like a spreadsheet, but with enforced types:

```sql
CREATE TABLE buildings (
    id INTEGER PRIMARY KEY,
    name TEXT,
    area DOUBLE PRECISION,
    type TEXT,
    municipality_id INTEGER,
    geom GEOMETRY
);
```

Each column has a type (`INTEGER`, `TEXT`, `GEOMETRY`). Every row must conform to this schema. You can't put text in an integer column.

```
buildings:
| id | name        | area | type       | municipality_id | geom             |
|----|-------------|------|------------|-----------------|------------------|
| 1  | City Hall   | 2500 | public     | 1               | <polygon bytes>  |
| 2  | Library     |  800 | public     | 1               | <polygon bytes>  |
| 3  | Concert H.  | 1200 | cultural   | 2               | <polygon bytes>  |
```

### Schema Enforcement

The schema is defined once at table creation and enforced on every row. This is a key difference from formats like [GeoJSON](geojson.md), where properties are freeform JSON and different features can have different fields.

Schema enforcement means:

- Every row has the same columns with the same types
- Tools can rely on the structure (no guessing which fields exist)
- Invalid data is rejected at insertion

### Primary Keys

A table should have a **primary key**; a column (or combination of columns) that uniquely identifies each row. In the example above, `id` is the primary key; no two buildings can share the same `id`.

Primary keys serve two purposes:

1. **Uniqueness** - guarantees no duplicate rows
2. **Fast lookup** - the database builds an index on the primary key (see [How Row-Based Engines Find Data](#b-tree-lookup))

## Relations

The "relational" in relational database means tables relate to each other through shared keys. This is what distinguishes a relational database from a collection of independent tables.

Consider two tables, `municipalities` and `buildings`:

```
municipalities:
| id | name      | population |
|----|-----------|------------|
| 1  | Oslo      | 709037     |
| 2  | Bergen    | 289330     |
| 3  | Trondheim | 212660     |

buildings:
| id | name        | area | type       | municipality_id | geom             |
|----|-------------|------|------------|-----------------|------------------|
| 1  | City Hall   | 2500 | public     | 1               | <polygon bytes>  |
| 2  | Library     |  800 | public     | 1               | <polygon bytes>  |
| 3  | Concert H.  | 1200 | cultural   | 2               | <polygon bytes>  |
| 4  | Museum      |  600 | cultural   | 3               | <polygon bytes>  |
| 5  | School      |  900 | education  | 1               | <polygon bytes>  |
```

The `municipality_id` column in `buildings` points to a row in `municipalities`. This is a **foreign key**, it references the primary key of another table.

The alternative would be to duplicate municipality data in every building row ("Oslo", 709037, "Oslo", 709037...). Relations avoid this duplication — store municipality data once, reference it by ID.

### Joins

A **join** combines rows from two tables using their relationship:

```sql
SELECT b.name, b.area, m.name AS municipality
FROM buildings b
JOIN municipalities m ON b.municipality_id = m.id;
```

Result:

```
| name        | area | municipality |
|-------------|------|--------------|
| City Hall   | 2500 | Oslo         |
| Library     |  800 | Oslo         |
| Concert H.  | 1200 | Bergen       |
| Museum      |  600 | Trondheim    |
| School      |  900 | Oslo         |
```

The database matched `municipality_id = 1` to `municipalities.id = 1` ("Oslo") for each building.

## SQL

SQL (Structured Query Language) is the standard language for querying relational databases. The key operations:

```sql
-- Filter rows
SELECT name, area FROM buildings WHERE type = 'public';

-- Aggregate
SELECT type, COUNT(*), AVG(area) FROM buildings GROUP BY type;

-- Join tables
SELECT b.name, m.name AS municipality
FROM buildings b
JOIN municipalities m ON b.municipality_id = m.id;

-- Combined: average building area per municipality
SELECT m.name, AVG(b.area) AS avg_area
FROM buildings b
JOIN municipalities m ON b.municipality_id = m.id
GROUP BY m.name;
```

The same SQL syntax works across different engines — SQLite, PostgreSQL, DuckDB. The engines differ in how they *execute* the query, not in how you write it.

## Row-Based vs Column-Based Engines

Relational databases share the same query language (SQL) and data model (tables with relations), but differ in how they store and process data. The two main approaches are [row-based and column-based storage](row-vs-columnar.md).

### Same Query, Two Engines

Consider this query on the buildings table:

```sql
SELECT m.name, AVG(b.area) AS avg_area
FROM buildings b
JOIN municipalities m ON b.municipality_id = m.id
GROUP BY m.name;
```

"Average building area per municipality." Both SQLite and DuckDB return the same result, but get there very differently.

**SQLite (row-based, same engine as [GeoPackage](geopackage.md))**

SQLite stores data row by row on disk:

```
Page 1: [id=1, "City Hall", 2500, "public", 1, <500 bytes of polygon>]
Page 2: [id=2, "Library", 800, "public", 1, <300 bytes of polygon>]
Page 3: [id=3, "Concert H.", 1200, "cultural", 2, <400 bytes of polygon>]
...
```

To answer the query, SQLite:

1. Scans every row in `buildings`. It reads the full row from disk, including `name`, `type`, and `geom` columns even though the query only needs `area` and `municipality_id`
2. For each row, looks up `municipality_id` in `municipalities`
3. Accumulates sums and counts per group
4. Computes averages

The problem: the `geom` column is by far the largest (hundreds or thousands of bytes per polygon), but the query doesn't need it. SQLite reads it anyway because it's packed in the same row.

**DuckDB (columnar)**

DuckDB stores data column by column:

```
area column:         [2500, 800, 1200, 600, 900]
municipality_id col: [1, 1, 2, 3, 1]
name column:         ["City Hall", "Library", "Concert H.", "Museum", "School"]
type column:         ["public", "public", "cultural", "cultural", "education"]
geom column:         [<500 bytes>, <300 bytes>, <400 bytes>, ...]
```

To answer the query, DuckDB:

1. Reads **only** the `area` column and `municipality_id` column from `buildings` — never touches `name`, `type`, or `geom`
2. Reads only `id` and `name` from `municipalities`
3. Processes in vectorized batches (thousands of values at once, CPU-cache friendly)
4. Computes averages

The geometry column — the largest part of the data — is never read from disk.

```
SQLite reads from buildings:
  ████████████████████████████████████  ← entire rows including geom
  Only needs: ██                        ← area + municipality_id

DuckDB reads from buildings:
  ██                                    ← only area + municipality_id
```

For a table with millions of buildings where the geometry column dominates the storage, DuckDB might read 1% of the bytes that SQLite reads for the same analytical query.

We can flip the query and ask for everything about building number 42:

```sql
SELECT * FROM buildings WHERE id = 42;
```

Now SQLite wins: the entire row is stored contiguously, the location of row number 42 is quicly found using a [B-tree Lookub](#b-tree-lookup) and one row is read. DuckDB has to gather `id`, `name`, `area`, `type`, `municipality_id`, and `geom` from six different column locations (and thus read a lot of geometry objects!).

### How Each Engine Finds Data

#### B-tree Lookup

SQLite organizes each table as a **B-tree**: a tree structure indexed by primary key. The database file is divided into fixed-size pages (default 4KB):

```
B-tree for buildings (indexed by id):

         ┌──────────────┐
         │  [20, 40, 60] │  ← Root page: "ids 1-20 go left, 21-40 middle..."
         └──┬─────┬────┬─┘
            │     │    │
     ┌──────┘     │    └──────┐
     ▼            ▼           ▼
┌─────────┐ ┌─────────┐ ┌─────────┐
│ rows    │ │ rows    │ │ rows    │
│ 1-20    │ │ 21-40   │ │ 41-60   │  ← Leaf pages: actual row data
└─────────┘ └─────────┘ └─────────┘
```

`SELECT * FROM buildings WHERE id = 42`:

1. Read root page — key 42 > 40, so go right
2. Read leaf page for 41-60 — find row 42
3. Done. Two page reads.

Finding the row is thus **O(log n)** where the base of log is the branching factor (number of branches). In the example above, that would be three but for at typical B-tree it is around 100. For 1 million rows we thus get: $log_{100}(1,000,000)  = 3$ levels, meaning 3 page reads to find any row.

Without the B-tree index (no primary key or index on the column), the database falls back to a **full table scan** — checking every row, which is O(n).

#### Column Metadata Lookup

DuckDB organizes data into **row groups** (batches of rows). Within each row group, columns are stored as contiguous chunks. A metadata header maps each (row group, column) to a byte offset:

```
File metadata header:
┌────────────────────────────────────────────────┐
│ Row Group 0 (rows 0-9999):                     │
│   id column      → offset 1000,  length 40000  │
│   name column    → offset 41000, length 80000  │
│   area column    → offset 121000, length 40000  │
│   geom column    → offset 161000, length 900000 │
│                                                 │
│ Row Group 1 (rows 10000-19999):                 │
│   id column      → offset 1100000, ...          │
│   ...                                           │
└────────────────────────────────────────────────┘
```

`SELECT AVG(area) FROM buildings`:

1. Read file metadata header — entry for "area column" is at a fixed position within the header (O(1) lookup, regardless of how many rows exist)
2. Get the byte offset for the area column in row group 0
3. Seek to that offset, read the column chunk — get all 10,000 area values
4. Repeat for each row group
5. Never touch `id`, `name`, or `geom` bytes

The metadata header has a fixed structure — entry N is always at the same position within the header. The actual byte offset of the column data on disk depends on the sizes of preceding columns, but finding the entry that tells you that offset is O(1).

#### The Core Difference

```
SQLite:   B-tree → finds the ROW   → row has all columns together
DuckDB:   Header → finds the COLUMN → column has all rows together
```

|                    | Find row by key | Find column   | Scan one column       |
|--------------------|-----------------|---------------|-----------------------|
| **Row-based**      | O(log n)        | O(1)*         | O(n x row_size)       |
| **Columnar**       | O(n)            | O(1)          | O(n x column_size)    |

\* Row-based engines also find columns in O(1) within a row (fixed offsets in the schema), but must read the full row from disk to get there.

The last column is the key difference for analytics — `row_size` includes the geometry column, `column_size` is just the one column you need.

For a deeper look at the storage layout, compression, and performance trade-offs, see [Row-Based vs Columnar Storage](row-vs-columnar.md).

## Key Takeaways

1. **Tables** — Structured collections of rows and columns with enforced types
2. **Primary keys** — Uniquely identify rows, enable fast B-tree lookups
3. **Foreign keys** — Link tables together, avoiding data duplication
4. **Joins** — Combine related tables in a single query
5. **SQL** — Same query language across different engines
6. **Row-based engines** (SQLite) — Fast for retrieving complete records, reads entire rows including unused columns
7. **Column-based engines** (DuckDB) — Fast for analytics, reads only the columns the query needs

## Related Topics

- [Row-Based vs Columnar Storage](row-vs-columnar.md) — Storage layout, compression, and performance details
- [GeoPackage](geopackage.md) — SQLite-based row storage with OGC spatial support
- [DuckDB](duckdb.md) — Columnar analytical database
- [PostgreSQL + PostGIS](postgresql-postgis.md) — Row-based server database with spatial extensions

## References

- [SQL Language (Wikipedia)][sql-language]
- [SQLite B-tree Documentation](https://www.sqlite.org/btreemodule.html)
- [DuckDB: Why Columnar?](https://duckdb.org/why_duckdb#fast-analytical-queries)

<!-- Links -->
[sql-language]: https://en.wikipedia.org/wiki/SQL "SQL language"