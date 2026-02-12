# Query Performance and Database Design

This page covers how to write efficient queries and design tables for geographic data. It builds on concepts from [Relational Databases](relational-databases.md) (B-tree lookups, row vs column engines) and [Spatial Indexing](spatial-indexing.md) (R-tree, bounding box filtering).

## Indexes: Why They Matter

In [Relational Databases](relational-databases.md#b-tree-lookup) we saw that a primary key gets an automatic B-tree index, turning row lookups from O(n) full table scans into O(log n) tree traversals. But primary keys aren't the only columns you filter by.

Consider the buildings table:

```sql
SELECT name, area FROM buildings WHERE type = 'commercial';
```

Without an index on `type`, the database scans every row and checks if `type = 'commercial'`. For 1 million buildings, that means reading 1 million rows to find maybe 50,000 commercial ones.

You can create an index on any column:

```sql
CREATE INDEX idx_buildings_type ON buildings(type);
```

Now the database builds a separate B-tree on the `type` column. The query becomes:

1. Look up 'commercial' in the B-tree — O(log n), a few page reads
2. Get a list of row IDs that match
3. Fetch only those rows

The same principle applies to numeric filters:

```sql
CREATE INDEX idx_buildings_area ON buildings(area);

-- Now this uses the index instead of scanning every row
SELECT name FROM buildings WHERE area > 1000;
```

### The Cost of Indexes

Building a B-tree index from scratch is **O(n log n)** — each of the n values must be inserted into the tree, and each insertion traverses O(log n) levels to find the right leaf.

Once the index exists, each INSERT into the table must also insert into the B-tree index with a cost of **O(log n)** per insert. This scales linearly with the number of filters.

The indices in addition take up some storage but not much.

## Spatial Indexes

PostGIS uses **GiST indexes** (Generalized Search Trees) — PostgreSQL's framework for building R-tree-like structures. The concept is the same as covered in [Spatial Indexing](spatial-indexing.md): hierarchical bounding boxes that let you prune entire branches of data.

```sql
CREATE INDEX idx_buildings_geom ON buildings USING GIST (geom);
```

Key difference from file-based indexes like FlatGeobuf's R-tree:

- **Dynamic:** Insert a new feature and the index updates automatically
- **Multiple indexes:** Create indexes on any column; the query planner combines them
- **No rebuild needed:** FlatGeobuf's index is static (baked at file creation); PostGIS indexes adapt to changes

Building an R-tree has the same O(n log n) complexity as a B-tree, and inserting a single element is O(log n) — but with higher constant factors because 2D bounding box comparisons are more involved than 1D value comparisons. See [Spatial Indexing — Build time](spatial-indexing.md#costs) for the details on how R-trees are constructed.

### Index Cost Summary

| Operation | B-tree | R-tree |
|-----------|--------|--------|
| **Build from scratch** | O(n log n) | O(n log n) |
| **Insert one element** | O(log n) | O(log n) |
| **Insert with k indexes** | O(k × log n) | same principle |

## Two-Stage Spatial Filtering

This is the core geographic-specific performance concept.

When you write a spatial query like:

```sql
SELECT name FROM buildings WHERE ST_Intersects(geom, search_area);
```

It looks like one operation, but the database actually does **two stages**:

### Stage 1: Bounding Box Filter (cheap)

The spatial index stores bounding boxes, not actual geometries. The database first checks which buildings' bounding boxes overlap the search area's bounding box. This is the R-tree traversal from [Spatial Indexing](spatial-indexing.md#search-algorithm) — fast, index-based, eliminates most of the data.

### Stage 2: Exact Geometry Test (expensive)

Bounding boxes are rectangles — they're an approximation. A building whose bounding box overlaps the search area might not actually intersect it:

```
Search area (circle):         Building bounding box:
                              ┌─────────────────┐
       ╭───╮                  │   ┌──┐          │
      │     │                 │   │  │          │
       ╰───╯                  │   │  └────┐    │
                              │   │       │    │
                              │   └───────┘    │
                              └─────────────────┘
                              ↑ bbox overlaps, but the actual
                                L-shaped building may not intersect
```

For each candidate from stage 1, the database computes the exact geometric intersection. This is computationally expensive — it involves testing actual polygon edges — but it only runs on the small set of candidates, not the entire table.

### Why This Matters

If your table has 1 million buildings and you're searching a small area:

```
Stage 1 (bounding box filter):  1,000,000 → 200 candidates
Stage 2 (exact geometry test):  200 → 150 actual results
```

The expensive exact test runs on 200 features instead of 1,000,000. The spatial index made this possible by cheaply eliminating 99.98% of the data.

PostGIS does both stages automatically when you have a spatial index and use functions like `ST_Intersects`, `ST_Within`, or `ST_Contains`. You don't need to code the two stages yourself.

## SELECT Only What You Need

```sql
-- Fetches geometry you may not need
SELECT * FROM buildings WHERE type = 'commercial';

-- Only what you actually use
SELECT name, area FROM buildings WHERE type = 'commercial';
```

This matters differently depending on the engine:

**Row-based (SQLite/PostGIS):** The engine reads the full row from disk regardless — all columns are packed together (see [Row-Based Storage](row-vs-columnar.md#row-based-storage)). But `SELECT *` still wastes network bandwidth and application memory. Geometry columns are large (hundreds to thousands of bytes per polygon), so avoiding unnecessary geometry transfer adds up.

**Columnar (DuckDB):** The engine benefits directly — it only reads the columns you ask for from disk. Skipping the geometry column can mean reading a fraction of the data. This is the principle we saw with the [SQLite-vs-DuckDB comparison]((relational-databases.md#row-based-vs-column-based-engines)).

## Combined Filters

This is the key advantage of a database over file-based formats.

```sql
SELECT name, area FROM buildings
WHERE ST_Within(geom, oslo_boundary)
AND type = 'commercial'
AND area > 1000;
```

PostGIS's **query planner** can combine multiple indexes. It might:

1. Use the spatial index to find buildings in Oslo (~10,000 candidates)
2. Use the index on `type` to find commercial buildings (~50,000 candidates)
3. Intersect those candidate sets
4. Filter the remaining candidates by area

Or it might decide the spatial filter is more selective and apply that first, then check the other conditions on the candidates. The query planner makes these decisions based on table statistics — it picks whichever approach reads the least data.

With a file-based format like FlatGeobuf, you can only filter spatially (by bounding box). Any attribute filtering happens after the features are already loaded into memory. PostGIS can use all conditions to narrow down results before reading the full row data.

## EXPLAIN: Checking Your Query Plan

How do you know if your indexes are actually being used? `EXPLAIN` shows what the database plans to do:

```sql
EXPLAIN SELECT name FROM buildings
WHERE ST_Within(geom, oslo_boundary) AND type = 'commercial';
```

This outputs the query plan — a tree of operations. The key things to look for:

- **Index Scan** or **Bitmap Index Scan** — the database is using an index (good)
- **Seq Scan** (sequential scan) — the database is reading every row (may indicate a missing index)
- **Filter** — a condition applied after reading rows (not index-assisted)

`EXPLAIN ANALYZE` actually runs the query and shows real execution times alongside the plan:

```sql
EXPLAIN ANALYZE SELECT name FROM buildings
WHERE ST_Within(geom, oslo_boundary) AND type = 'commercial';
```

This is how you verify that adding an index actually improved things. If the output shows a Seq Scan where you expected an Index Scan, you may need to create an index on that column.

SQLite has a simpler version:

```sql
EXPLAIN QUERY PLAN SELECT name FROM buildings WHERE type = 'commercial';
-- Output: SEARCH buildings USING INDEX idx_buildings_type (type=?)
```

## Table Design Tips

These are practical guidelines, not strict rules:

**Index columns you filter by.** If you frequently query `WHERE type = ...`, create an index on `type`. If you frequently query by spatial location, create a spatial index on the geometry column.

**Use foreign keys for data integrity.** Foreign keys ensure that a `municipality_id` in `buildings` always references a valid row in `municipalities` (see [Relations](relational-databases.md#relations)).

```sql
ALTER TABLE buildings ADD CONSTRAINT fk_municipality
    FOREIGN KEY (municipality_id) REFERENCES municipalities(id);
```

**Choose appropriate data types.** Don't store numbers as text. A `TEXT` column storing "1200" can't be efficiently compared with `> 1000` — the database would do string comparison instead of numeric comparison.

**Consider separating large geometry from frequently-queried attributes.** If you often query attributes without needing geometry (dashboards, reports), having the geometry in the same row-based table means the engine reads it anyway. One option is to keep a separate table for geometry, joined by ID. This is an advanced technique — only worth it when geometry dominates your storage and most queries don't need it.

## Key Takeaways

1. **Create indexes on columns you filter by** — turns O(n) scans into O(log n) lookups
2. **Spatial indexes use bounding boxes** — cheap first stage eliminates most data
3. **Two-stage filtering** — bounding box filter then exact geometry test, done automatically by PostGIS
4. **Select only needed columns** — especially important with large geometry columns
5. **Databases combine multiple indexes** — the query planner picks the most efficient strategy
6. **Use EXPLAIN to verify** — check that your indexes are actually being used

## Related Topics

- [Relational Databases](relational-databases.md) — B-tree indexes, row vs column engines
- [Spatial Indexing](spatial-indexing.md) — R-tree structure and search algorithm
- [Row-Based vs Columnar Storage](row-vs-columnar.md) — Why SELECT columns matter differently per engine
- [PostgreSQL + PostGIS](postgresql-postgis.md) — GiST indexes, spatial functions, combined queries

## References

- [PostgreSQL EXPLAIN Documentation](https://www.postgresql.org/docs/current/using-explain.html)
- [PostGIS Indexing Workshop](https://postgis.net/workshops/postgis-intro/indexing.html)
- [SQLite Query Planning](https://www.sqlite.org/queryplanner.html)
