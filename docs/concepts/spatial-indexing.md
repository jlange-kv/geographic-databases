# Spatial Indexing

Understanding how spatial queries are optimized is fundamental to working with geographic data efficiently.

## The Problem: Regular Indexes Don't Work

Traditional database indexes (B-trees) work great for one-dimensional queries:
- "Find all users with age > 30" → Index on age column
- "Find products with price < 100" → Index on price column

But spatial queries are **multi-dimensional**:
- "Find all buildings within 5km of this point"
- "Show me roads that intersect this area"
- "Which countries overlap with this bounding box?"

A B-tree can't efficiently answer "which points are near THIS point?" because **proximity in 2D space doesn't translate to simple number comparisons**. You can't sort geographic features in a way that preserves spatial relationships.

Without a spatial index, the database must check every single feature against your query - slow for large datasets.

## What is a Spatial Index?

A **spatial index** organizes geographic data by location to enable fast spatial queries. The most common type is the **R-tree** (Rectangle tree), which creates a **hierarchy of bounding boxes** around your data.

**Core idea:** Group nearby features into rectangular bounding boxes, then group those boxes into larger boxes, creating a tree structure. This lets you quickly eliminate large portions of data that can't possibly match your query.

## How the R-tree is Constructed

### Hierarchical Bounding Boxes

The R-tree organizes spatial data into levels of nested bounding boxes:

- **Level 3 (Root)**: One large bounding box covering the entire dataset (e.g., entire city)
- **Level 2**: A few boxes covering major regions (e.g., neighborhoods)
- **Level 1**: Many boxes covering smaller areas (e.g., city blocks)
- **Level 0 (Leaves)**: Individual bounding boxes for each feature (e.g., buildings)

The tree structure:

```
Level 3 (Root): One large box covering entire city
    │
    ├─→ Level 2: Neighborhood box 1
    │       │
    │       ├─→ Level 1: City block box 1
    │       │       │
    │       │       └─→ Level 0 (Leaves): Building 1, Building 2, Building 3...
    │       │
    │       └─→ Level 1: City block box 2
    │               │
    │               └─→ Level 0 (Leaves): Building 10, Building 11...
    │
    └─→ Level 2: Neighborhood box 2
            │
            ├─→ Level 1: City block box 3
            │       │
            │       └─→ Level 0 (Leaves): Building 20, Building 21...
            │
            └─→ Level 1: City block box 4
```

### What Each Node Contains

**Higher levels (internal nodes):**
```
Node = {
  bounding_box: {min_x, min_y, max_x, max_y},  // 4 numbers
  children: [pointer_to_child_1, pointer_to_child_2, ...]
}
```

**Level 0 (leaf nodes):**
```
Leaf = {
  bounding_box: {min_x, min_y, max_x, max_y},  // 4 numbers
  feature_reference: byte_offset_or_id  // where actual geometry is stored
}
```

### Important Property: Boxes Can Overlap

Unlike B-trees where ranges are strictly separated, **R-tree boxes at the same level can overlap**:

```
┌─────────────┐
│  Box A      │
│   ┌─────────┼─────┐
│   │ Overlap │     │
└───┼─────────┘     │
    │    Box B      │
    └───────────────┘
```

**Why?** Spatial objects don't naturally partition into non-overlapping regions. A building on a corner might be near features in two different areas, so both boxes might include it.

This means a query might explore multiple branches, but you still prune away boxes that don't overlap your query area.

## Why the Index is Compact

The index is much smaller than the actual geometry data because it only stores **simple rectangles**.

**Index storage:**
- Rectangle = 4 floating-point numbers (min_x, min_y, max_x, max_y)
- Typically ~32 bytes per box (including pointers)

**Geometry storage:**
- Complex polygon with 100 vertices = ~800 bytes just for coordinates
- Plus attribute data, topology, etc.

**Example for 1 million buildings:**

R-tree index:
- Level 0: ~10,000 leaf boxes × 32 bytes = 320 KB
- Level 1: ~100 boxes × 32 bytes = 3.2 KB
- Level 2: ~10 boxes × 32 bytes = 320 bytes
- **Total: ~325 KB**

Actual geometry:
- 1 million complex polygons × ~1 KB average = ~1 GB

**Result:** Index is ~0.03% of data size in this example. The storage overhead is small because the index only contains simple rectangles rather than complex geometries.


## How Spatial Search Works

### Search Algorithm

When you query "find features in this bounding box [x1, y1, x2, y2]":

```
1. Start at root level
2. For each child box:
   - Check if child's bounding box overlaps query box
   - If YES: recursively search that child
   - If NO: skip entire branch (pruning!)
3. At level 0, collect all matching features
4. Fetch actual geometry and do precise intersection test
```

### Example Search

**Query:** "Buildings in downtown area [13.40, 52.51, 13.41, 52.52]"

```
Level 3 (Root):
  ├─ North District [13.30-13.50, 52.55-52.60]
  │  Does [13.30-13.50, 52.55-52.60] overlap [13.40-13.41, 52.51-52.52]?
  │  → NO (query is south of this box)
  │  → Skip entire North District
  │
  └─ South District [13.35-13.45, 52.48-52.53]
     Does [13.35-13.45, 52.48-52.53] overlap [13.40-13.41, 52.51-52.52]?
     → YES, explore children

Level 2 (within South District):
  ├─ Downtown [13.38-13.42, 52.50-52.52]
  │  → YES, explore children
  │
  └─ Suburbs [13.40-13.45, 52.48-52.49]
     → NO (query is north of this box)
     → Skip entire Suburbs

Level 1 (within Downtown):
  ├─ Block A [13.39-13.40, 52.51-52.52]
  │  → YES, explore
  │
  └─ Block B [13.41-13.42, 52.50-52.51]
     → Partial overlap, explore

Level 0:
  Get byte offsets for buildings in Block A and Block B
  Fetch actual geometries
  Do precise intersection tests
```

**Result:** Checked maybe 100 boxes instead of 1 million features. Pruned entire branches (North District, Suburbs) without looking at any individual buildings there.

## FlatGeobuf Streaming with Spatial Index

FlatGeobuf demonstrates the power of spatial indexing for cloud-based data:

### File Structure

```
FlatGeobuf file:
┌─────────────────────┐
│ Header              │ ← Metadata about file
├─────────────────────┤
│ R-tree Index        │ ← ENTIRE spatial index
│ (all levels)        │   (compact due to simple rectangles)
├─────────────────────┤
│ Feature 1           │ ← Actual geometry data
│ Feature 2           │   (much larger, complex geometries)
│ Feature 3           │
│ ...                 │
└─────────────────────┘
```

### Streaming Workflow

**User pans map to show a specific area:**

```
1. First request: Fetch header + entire R-tree index
   GET bytes 0-50000
   → Loads complete index into memory (one round-trip)

2. Query index in memory for bbox [x1, y1, x2, y2]
   → Traverse tree (instant, no network)
   → Result: "Features at byte ranges [500000-510000, 800000-805000]"

3. Fetch only relevant features
   GET bytes 500000-510000, 800000-805000
   → Downloads only matching features

4. Render features on map

User pans to different area:
   → Skip step 1 (already have index!)
   → Query index for new bbox
   → Fetch new byte ranges
```

**Why this is efficient:**
- **Index fetch**: One-time cost (small due to compact rectangles)
- **Data fetch**: Only what you need
- **No server processing**: Client does all spatial filtering

This is why FlatGeobuf is called a "cloud-native" format - you can work with massive files without downloading them entirely or needing a database server.

## Trade-offs

### Benefits

**Query speed:**
- Spatial queries are orders of magnitude faster
- Essential for large datasets (millions+ features)
- Enables interactive applications (web maps, real-time queries)

**Cloud efficiency:**
- Stream only needed data over network
- No server-side processing required

### Costs

**Storage:**
- Index adds overhead to file size
- Usually small relative to total data (as shown in example above)

**Build time:**

Building an R-tree from scratch is **O(n log n)**, the same complexity class as building a B-tree (see [B-tree Lookup](relational-databases.md#b-tree-lookup)).

A naive construction can create trees that are still slow, but in practice, spatial tools use **bulk loading**: sort the data spatially first then build the tree bottom-up, filling leaves with spatially adjacent features. The sort is O(n log n), the tree construction after sorting is O(n), so the total is still O(n log n) but produces a much better tree with less bounding box overlap. This is what FlatGeobuf does at file creation and what PostGIS does with `CREATE INDEX ... USING GIST`.

**Inserting into an existing R-tree:**

Inserting a single element is **O(log n)**, same as a B-tree. But more expensive in practice — at each level the algorithm must compare bounding box enlargements to decide which child to descend into (not just a simple left-or-right comparison), and node splits require minimizing overlap between the resulting bounding boxes.

If the table has multiple indexes (spatial + attribute), each insert must update all of them independently.

**Immutable file formats:**

For file-based formats like FlatGeobuf, the R-tree is static. You can't insert into it without rebuilding the entire file. This is fine for "write once, read many" use cases. PostGIS indexes, by contrast, update dynamically on every insert.

## When Spatial Indexes Matter

### Essential for:

**Large datasets:**
- Millions+ features where full scans are prohibitively slow
- Interactive applications requiring subsecond response

**Spatial queries:**
- "Features within area" (bounding box queries)
- "Features near point" (radius queries)
- "Features intersecting geometry" (overlap queries)

**Streaming/cloud scenarios:**
- Serving map tiles
- Progressive loading of data
- Working with remote files without full download

### Less important for:

**Small datasets:**
- Few thousand features where full scan is fast enough
- Simple analytical queries on all data

**Non-spatial queries:**
- "All buildings with area > 1000m²" (attribute filtering)
- Columnar formats (GeoParquet) may be better for pure analytics

**Write-heavy workloads:**
- If constantly inserting/updating, index maintenance overhead may dominate
- Consider batch updates and index rebuilds

## Spatial Index Types

While R-tree is most common, other types exist:

**R-tree variants:**
- **R-tree**: Original, used in PostGIS, FlatGeobuf
- **R*-tree**: Optimized splitting strategy (better performance)
- **R+ tree**: Non-overlapping boxes (more complex)

**Grid-based:**
- **Quadtree**: Recursively divide space into quarters
- **Geohash**: Encode location as string for lexicographic sorting

**Space-filling curves:**
- **Hilbert curve**: Map 2D space to 1D while preserving locality
- **Z-order curve**: Similar concept, simpler implementation

R-tree is most common because it:
- Adapts to data distribution (not fixed grid)
- Handles varying feature densities well
- Works for any geometry type

## Key Takeaways

1. **Spatial indexes organize data by location** - Not by attribute values
2. **R-tree uses hierarchical bounding boxes** - Group nearby features together
3. **Pruning is the key insight** - Skip entire branches that can't match
4. **Index is compact** - Only stores simple rectangles (4 numbers each)
5. **Enables streaming** - Know exactly which bytes to fetch
6. **Essential for large datasets** - Makes million-feature queries practical
7. **Trade-off: build time vs query speed** - One-time cost for massive speedup

## Related Topics

- [FlatGeobuf][flatgeobuf] - File format with built-in R-tree index
- [GeoParquet][geoparquet] - Columnar format (less spatial indexing, better analytics)
- [Row-Based vs Columnar Storage][row-vs-columnar] - Why FlatGeobuf uses row-based storage
- [File Formats Overview][formats] - Which formats support spatial indexing

## References

- [R-tree Wikipedia](https://en.wikipedia.org/wiki/R-tree)
- [PostGIS Indexing](https://postgis.net/workshops/postgis-intro/indexing.html)
- [FlatGeobuf Specification](http://flatgeobuf.org/)

<!-- Reference-style links -->
[flatgeobuf]: ../file-formats/flatgeobuf.md
[geoparquet]: ../file-formats/geoparquet.md
[row-vs-columnar]: row-vs-columnar.md
[formats]: ../file-formats/README.md