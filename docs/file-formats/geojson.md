# GeoJSON

GeoJSON is a text-based format that encodes geographic data as standard JSON. Defined by [RFC 7946][rfc-7946], it is the default exchange format for web mapping.

## What is GeoJSON?

A GeoJSON file is plain JSON with a specific structure for geographic features. No binary encoding, no index, no metadata tables — just text you can read in any editor.

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Point",
        "coordinates": [10.75, 59.91]
      },
      "properties": {
        "name": "Oslo",
        "population": 709037
      }
    }
  ]
}
```

**Design goals:**
- Human-readable
- Native to JavaScript and the web
- Simple structure, easy to generate and consume
- No special tools required

## Structure

GeoJSON has three building blocks:

### Geometry

The spatial part — a type and an array of coordinates:

```json
{"type": "Point", "coordinates": [10.75, 59.91]}

{"type": "LineString", "coordinates": [[10.7, 59.9], [10.8, 59.9], [10.8, 60.0]]}

{"type": "Polygon", "coordinates": [[[10.6, 59.8], [10.9, 59.8], [10.9, 60.0], [10.6, 60.0], [10.6, 59.8]]]}
```

Also supports `MultiPoint`, `MultiLineString`, `MultiPolygon`, and `GeometryCollection`.

**Coordinate order is [longitude, latitude]** — this is a common source of confusion since most people say "lat/lon".

### Feature

A geometry paired with properties (attributes):

```json
{
  "type": "Feature",
  "geometry": {"type": "Point", "coordinates": [10.75, 59.91]},
  "properties": {
    "name": "Oslo",
    "population": 709037,
    "country": "Norway"
  }
}
```

Properties is a freeform JSON object — there is no fixed schema. Different features in the same file can have different properties.

### FeatureCollection

An array of Features — this is what most GeoJSON files are:

```json
{
  "type": "FeatureCollection",
  "features": [
    {"type": "Feature", "geometry": {...}, "properties": {...}},
    {"type": "Feature", "geometry": {...}, "properties": {...}}
  ]
}
```

## CRS Restriction

RFC 7946 mandates **WGS84 (EPSG:4326)** as the only valid coordinate reference system.

If your data is in a projected CRS (like UTM zone 33N / EPSG:25833), you must **reproject to WGS84** before writing valid GeoJSON. Tools like GeoPandas handle this automatically:

```python
# Data in EPSG:25833 → must reproject for GeoJSON
gdf_wgs84 = gdf.to_crs(epsg=4326)
gdf_wgs84.to_file("output.geojson", driver="GeoJSON")
```

Earlier GeoJSON specifications allowed other CRS, but RFC 7946 locked it to WGS84 for interoperability.

## Why It's Large

GeoJSON is typically the largest format for the same data. Three reasons:

### Text Encoding of Numbers

Every coordinate is stored as text:

```
Binary (float64):  8 bytes for 59.913868
Text (GeoJSON):    9 bytes for "59.913868" + separators
```

A polygon with 100 vertices needs ~200 coordinate values. The text overhead accumulates.

### Repeated Property Names

Every feature repeats all property names:

```json
{"properties": {"name": "Oslo", "population": 709037}}
{"properties": {"name": "Bergen", "population": 289330}}
{"properties": {"name": "Trondheim", "population": 212660}}
```

`"name"` and `"population"` appear in every feature. In binary formats, column names are stored once in the schema.

### JSON Syntax Overhead

Brackets, braces, quotes, commas, and colons add up:

```json
{"type":"Feature","geometry":{"type":"Point","coordinates":[10.75,59.91]},"properties":{"name":"Oslo"}}
```

Compare to a binary format where the same feature might be ~30 bytes instead of ~100.

## No Spatial Index

GeoJSON has no built-in spatial index. To find features in a bounding box, you must:

1. Parse the entire JSON file
2. Check every feature's geometry against the query area

For small datasets this is fine. For large datasets, this is why formats like [FlatGeobuf][flatgeobuf] exist.

## No Fixed Schema

Properties can vary between features:

```json
{"properties": {"name": "Oslo", "population": 709037}}
{"properties": {"name": "Nordkapp", "tourism": true}}
```

**Flexible** — good for heterogeneous data or quick prototyping.
**Unpredictable** — tools can't assume which properties exist, making validation and type checking harder.

## Newline-Delimited GeoJSON (GeoJSONSeq)

Standard GeoJSON wraps everything in a FeatureCollection array, requiring the entire file to be parsed as one JSON document.

**GeoJSON Text Sequences** ([RFC 8142][rfc-8142]) puts one Feature per line:

```
{"type":"Feature","geometry":{"type":"Point","coordinates":[10.75,59.91]},"properties":{"name":"Oslo"}}
{"type":"Feature","geometry":{"type":"Point","coordinates":[5.32,60.39]},"properties":{"name":"Bergen"}}
```

**Advantages:**
- Process line by line without loading entire file into memory
- Append features by appending lines
- Easier to process with standard unix tools (`wc -l`, `head`, `grep`)

**GDAL/ogr2ogr** supports this as the `GeoJSONSeq` driver.

## When to Use GeoJSON

### Ideal for:

**Web APIs and JavaScript:**
- Native JSON parsing — no special libraries needed
- Every web mapping library accepts GeoJSON (Leaflet, Mapbox GL, OpenLayers)
- Default format for most geospatial REST APIs

**Small datasets:**
- Under ~10,000 features where size and parse time don't matter
- Quick data exchange

**Debugging and development:**
- Human-readable — open in a text editor
- Easy to hand-edit or generate
- Inspect data without special tools

### Not ideal for:

**Large datasets:**
- File size grows fast (text encoding, repeated property names)
- Parse time increases linearly — no way to skip features
- Use [FlatGeobuf][flatgeobuf] or [GeoParquet][geoparquet] instead

**Spatial queries:**
- No spatial index — must check every feature
- Use [FlatGeobuf][flatgeobuf] instead

**Non-WGS84 data:**
- Must reproject to EPSG:4326
- If you need to preserve a projected CRS, use [GeoPackage][geopackage] or [GeoParquet][geoparquet]

**Data with fixed schema:**
- No schema enforcement
- Use [GeoPackage][geopackage] (SQL schema) or [GeoParquet][geoparquet] (typed columns)

## Tooling

### Python (GeoPandas)

```python
import geopandas as gpd

# Read
gdf = gpd.read_file("data.geojson")

# Write (reprojects to WGS84 if needed)
gdf.to_crs(epsg=4326).to_file("output.geojson", driver="GeoJSON")

# Write newline-delimited
gdf.to_file("output.geojsonl", driver="GeoJSONSeq")
```

### JavaScript

```javascript
// Native parsing — no library needed
const response = await fetch("data.geojson");
const geojson = await response.json();

// Use with Leaflet
L.geoJSON(geojson).addTo(map);

// Use with Mapbox GL
map.addSource("data", { type: "geojson", data: geojson });
```

### GDAL

```bash
# Convert to GeoJSON
ogr2ogr -f GeoJSON output.geojson input.gpkg

# Convert to newline-delimited
ogr2ogr -f GeoJSONSeq output.geojsonl input.gpkg

# Reproject to WGS84 during conversion
ogr2ogr -f GeoJSON -t_srs EPSG:4326 output.geojson input_utm.gpkg
```

## Key Takeaways

1. **Plain JSON** — Human-readable, no special tools needed
2. **JavaScript-native** — Default format for web mapping
3. **WGS84 only** — Must reproject from other CRS (RFC 7946)
4. **No spatial index** — Must parse entire file for spatial queries
5. **No fixed schema** — Flexible but unpredictable properties
6. **Largest file size** — Text encoding and JSON verbosity
7. **Best for small data and web** — Not for large datasets or analytics

## Related Topics

- [FlatGeobuf][flatgeobuf] — Binary alternative with spatial index (for larger web datasets)
- [GeoParquet][geoparquet] — Columnar binary format (for analytics)
- [GeoPackage][geopackage] — SQLite-based with schema (for sharing)
- [File Formats Overview][formats] — Compare all formats

## References

- [RFC 7946 — The GeoJSON Format][rfc-7946]
- [RFC 8142 — GeoJSON Text Sequences][rfc-8142]
- [geojson.org](https://geojson.org/)
- [geojson.io](https://geojson.io/) — Interactive GeoJSON editor

<!-- Reference-style links -->
[flatgeobuf]: flatgeobuf.md
[geoparquet]: geoparquet.md
[geopackage]: geopackage.md
[shapefile]: shapefile.md
[formats]: README.md

[rfc-7946]: https://tools.ietf.org/html/rfc7946
[rfc-8142]: https://tools.ietf.org/html/rfc8142
