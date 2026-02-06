# Row-Based vs Columnar Storage

Understanding how data is physically organized on disk is fundamental to choosing the right storage format.

## The Core Difference

### Row-Based Storage

Data is stored **feature-by-feature** (row-by-row):

```
Imagine a table of cities:
┌────┬────────┬─────────┬────────────┬──────────────────┐
│ id │  name  │ country │ population │     geometry     │
├────┼────────┼─────────┼────────────┼──────────────────┤
│ 1  │ Paris  │ France  │ 2,161,000  │ POINT(2.35 48.86)│
│ 2  │ London │ UK      │ 8,982,000  │ POINT(-0.12 51.5)│
│ 3  │ Berlin │ Germany │ 3,645,000  │ POINT(13.4 52.5) │
└────┴────────┴─────────┴────────────┴──────────────────┘

On disk (row-based):
Block 1: [1|Paris|France|2161000|POINT(...)]
Block 2: [2|London|UK|8982000|POINT(...)]
Block 3: [3|Berlin|Germany|3645000|POINT(...)]
```

Each disk block contains **all attributes** for one feature.

### Columnar Storage

Data is stored **attribute-by-attribute** (column-by-column):

```
Same table, different organization:

On disk (columnar):
Block 1 (id):         [1|2|3]
Block 2 (name):       [Paris|London|Berlin]
Block 3 (country):    [France|UK|Germany]
Block 4 (population): [2161000|8982000|3645000]
Block 5 (geometry):   [POINT(...)|POINT(...)|POINT(...)]
```

Each disk block contains **one attribute** for all features.

## Why This Matters

The storage layout dramatically affects performance for different operations.

### When Row-Based is Faster: Getting Complete Records

**Query: "Get all information about Paris"**

**Row-based approach:**
```
1. Use index to find: name = "Paris" → Block 1
2. Read Block 1: [1|Paris|France|2161000|POINT(...)]
3. Return all attributes

Blocks read: 1
Result: Fast
```

**Columnar approach:**
```
1. Scan name column to find "Paris" → position 1
2. Read from id column, position 1 → 1
3. Read from name column, position 1 → "Paris"
4. Read from country column, position 1 → "France"
5. Read from population column, position 1 → 2161000
6. Read from geometry column, position 1 → POINT(...)

Blocks read: 5 (one per column)
Result: Slower
```

**The principle:** When you need **all attributes** for specific records, row-based storage retrieves them in **one block read**. Columnar storage must read from **every column** separately.

### When Columnar is Faster: Analytical Queries

**Query: "What is the average population?"**

**Row-based approach:**
```
1. Read Block 1: [1|Paris|France|2161000|POINT(...)]
   → Extract: 2161000
2. Read Block 2: [2|London|UK|8982000|POINT(...)]
   → Extract: 8982000
3. Read Block 3: [3|Berlin|Germany|3645000|POINT(...)]
   → Extract: 3645000
4. Calculate average

Blocks read: ALL blocks (entire table)
Wasted I/O: id, name, country, geometry (not needed!)
```

**Columnar approach:**
```
1. Read Block 4 (population): [2161000|8982000|3645000]
2. Calculate average

Blocks read: ONLY population block
Wasted I/O: None
```

**The principle:** Columnar storage lets you read **only the columns you need**. Row-based storage forces you to read **entire rows** even if you only want one attribute.

For 1 million cities, columnar might read 1 block while row-based reads 1 million blocks.

### Writing Data

**Operation: Insert one new city**

**Row-based approach:**
```
1. Create new row: [4|Madrid|Spain|3223000|POINT(...)]
2. Append to end of file (or insert into B-tree)
3. Update index with new entry

Blocks modified: 1 (plus index update)
Time: Fast (milliseconds)
```

**Columnar approach:**
```
1. Open id column → append 4 → close
2. Open name column → append "Madrid" → close
3. Open country column → append "Spain" → close
4. Open population column → append 3223000 → close
5. Open geometry column → append POINT(...) → close

Blocks modified: 5 (one per column)
Time: Slower (must touch every column)
```

**The principle:** Row-based storage writes **one block** for one record. Columnar storage must modify **every column** for one record.

This gets worse with compression (explained below).

### Compression

This is where columnar storage truly shines.

**Why columnar compresses better:**

Imagine a country column with many cities:

**Row-based (mixed data in each block):**
```
Block 1: [1|Paris|France|2161000|POINT(...)]
Block 2: [2|Lyon|France|513000|POINT(...)]
Block 3: [3|London|UK|8982000|POINT(...)]
...

Compression challenge: Each block has mixed data types
- Integer (id)
- String (names - all different)
- String (countries - repeated but scattered)
- Integer (populations - all different)
- Complex type (geometries - all different)

Result: Difficult to find compression patterns
```

**Columnar (similar data together):**
```
Country column:
[France|France|France|France|UK|UK|UK|Germany|Germany|Germany|...]

Compression opportunity:
    Original: ["France", "France", "France", "France", "UK", "UK", "UK", ...]

    Dictionary + encoding:
    - Dictionary: {0: "France", 1: "UK", 2: "Germany"}
    - Data: [0, 0, 0, 0, 1, 1, 1, 2, 2, 2, ...]

    Further compression (run-length):
    - [0×4, 1×3, 2×3, ...]

Comparison:
    ["France"×1000, "UK"×500, ...] vs Dictionary + [0×1000, 1×500, ...]

    UTF-8 string "France" = ~6 bytes × 1000 = ~6000 bytes
    Single byte 0 = 1 byte × 1000 = 1000 bytes + small dictionary
    (Since <255 countries exist, we can encode each with 1 byte)

Result: Much smaller for large datasets. Roughly 83% compression in this case.
```

**The principle:** Storing **similar values together** enables powerful compression techniques:
- Dictionary encoding (replace repeated strings with small integers)
- Run-length encoding (store value once, then "repeated N times")
- Bit-packing (integers with limited range)

Mixed data types in row-based storage can't exploit these patterns as effectively.

### Updates

**Operation: Change population of London from 8,982,000 to 9,000,000**

**Row-based:**
```
1. Find row (using index): [2|London|UK|8982000|POINT(...)]
2. Modify in place: [2|London|UK|9000000|POINT(...)]
3. Update affected indexes

Blocks modified: 1
Time: Fast (milliseconds)
```

**Columnar:**
```
Option A: Modify in place
1. Find position in population column (position 2)
2. Decompress block containing position 2
3. Change value: 8982000 → 9000000
4. Recompress entire block
5. Write back to disk

Problem: If compressed with dictionary/run-length encoding,
changing one value may require recompressing large chunks.

Option B: Rewrite file (common in practice)
1. Read entire file
2. Modify value
3. Write new file
4. Replace old file

Blocks modified: Potentially all blocks
Time: Slow (seconds for large files)
```

**The principle:** Row-based storage can modify **one record** easily. Columnar storage with compression makes single-record updates expensive, often requiring **rewriting entire column blocks**.

This is why GeoParquet is effectively **immutable** in practice.

## Performance Summary

| Operation | Row-Based | Columnar | Winner |
|-----------|-----------|----------|--------|
| **Read full record** | Fast (1 block) | Slow (N blocks for N columns) | Row-based |
| **Read one attribute across many records** | Slow (read all, extract one) | Fast (1 block) | Columnar |
| **Analytical query** (avg, sum, filter) | Slow (scan all data) | Fast (read only needed columns) | Columnar |
| **Insert one record** | Fast (append 1 block) | Slow (append to all columns) | Row-based |
| **Update one record** | Fast (modify 1 block) | Very slow (recompress/rewrite) | Row-based |
| **Delete one record** | Fast (mark deleted) | Very slow (rewrite file) | Row-based |
| **Compression ratio** | Lower (mixed data types) | Higher (similar values together) | Columnar |
| **Spatial query** | Medium (with spatial index) | Slower (less optimized for spatial) | Row-based* |

*With proper spatial indexing like FlatGeobuf's R-tree

## When to Use Each

### Use Row-Based Storage When:

- **Frequent writes/updates/deletes** - Transactional workloads (OLTP)
- **Need complete records** - "Get all info for user #12345"
- **Spatial filtering is primary** - "Features in this bounding box"
- **Real-time data collection** - Sensor data, logs, continuous updates

**Examples:**
- PostgreSQL + PostGIS (production database)
- FlatGeobuf (web mapping with spatial index)
- GeoPackage (general-purpose sharing)

### Use Columnar Storage When:

- **Analytical queries** - Aggregations, statistics, filtering by attributes
- **Read-heavy workloads** - "Write once, read many" (OLAP)
- **Need efficient compression** - Bandwidth/storage constraints
- **Cloud storage** - Minimize data transfer costs
- **Large datasets** - Millions to billions of records

**Examples:**
- GeoParquet (data science, analytics)
- Data warehouses (BigQuery, Snowflake)
- Analytical databases (DuckDB, ClickHouse)

## Real-World Patterns

### Pattern 1: Hybrid Architecture

Many systems use **both** strategically:

```
Live Data (changing frequently)
    ↓
PostgreSQL + PostGIS (row-based)
    ↓ Export nightly
GeoParquet in Data Lake (columnar)
    ↓ Analytics
Reports & Dashboards
```

**Why:** Optimize for different access patterns
- PostgreSQL: Fast writes for live updates
- GeoParquet: Fast analytics on historical data

### Pattern 2: Format Conversion

Start with one, convert for different uses:

```
Survey Data Collection
    ↓
GeoPackage (row-based, easy sharing)
    ↓ Convert for analysis
GeoParquet (columnar analytics)
    ↓ Convert for web map
FlatGeobuf (row-based with spatial index)
```

**Why:** Each format optimized for its use case

## Key Takeaways

1. **Physical layout matters** - How data is stored on disk determines performance
2. **Row-based wins for complete records** - One block read gets all attributes
3. **Columnar wins for analytics** - Read only columns needed, skip irrelevant data
4. **Compression favors columnar** - Similar values together enable dictionary/run-length encoding
5. **Writes favor row-based** - One record = one block, no need to touch multiple columns
6. **No universal best** - Choose based on access patterns
7. **Hybrid approaches work** - Use both for different stages of data lifecycle

## Related Topics

- [File Formats Overview][formats] - Which formats use which storage
- [GeoParquet][geoparquet] - Columnar format details
- [FlatGeobuf][flatgeobuf] - Row-based with spatial index
- [Write Performance][write-perf] - Detailed write comparisons
- [Read Performance][read-perf] - Detailed read comparisons

## References

- [Parquet Format Documentation](https://parquet.apache.org/docs/file-format/)
- [Column-Oriented DBMS (Wikipedia)](https://en.wikipedia.org/wiki/Column-oriented_DBMS)
- [DuckDB: Why Columnar?](https://duckdb.org/why_duckdb#fast-analytical-queries)

<!-- Reference-style links -->
[formats]: ../file-formats/README.md
[geoparquet]: ../file-formats/geoparquet.md
[flatgeobuf]: ../file-formats/flatgeobuf.md
[write-perf]: ../performance/write-performance.md
[read-perf]: ../performance/read-performance.md