"""Process raw shapefiles into FlatGeobuf format.

Reads all shapefile layers from data/raw/gruvedata/ and writes each
as a separate FlatGeobuf file to data/processed/.

Note: Uses fiona engine because pyogrio has encoding issues with
Norwegian characters in these particular shapefiles.
"""

from pathlib import Path

import geopandas as gpd

RAW_DIR = Path("data/raw/gruvedata")
OUTPUT_DIR = Path("data/processed")


def process_shapefiles():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    shapefiles = sorted(RAW_DIR.glob("*.shp"))
    print(f"Found {len(shapefiles)} shapefile layers\n")

    for shp in shapefiles:
        layer_name = shp.stem.rsplit("_", 1)[0]  # Remove date suffix
        output_path = OUTPUT_DIR / f"{layer_name}.fgb"

        print(f"Processing: {shp.stem}")
        gdf = gpd.read_file(shp, engine="fiona")

        # Add layer name as column for easy identification
        gdf.insert(0, "layer", layer_name)

        gdf.to_file(output_path, driver="FlatGeobuf")

        geom_types = gdf.geometry.geom_type.unique().tolist()
        print(f"  → {output_path} ({len(gdf)} features, {geom_types})")
        print()

    print("Done!")


if __name__ == "__main__":
    process_shapefiles()
