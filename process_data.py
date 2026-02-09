"""Process raw shapefiles into FlatGeobuf format.

Reads all shapefile layers from data/raw/gruvedata/ and writes each
as a separate FlatGeobuf file to data/processed/.

The raw shapefiles can be ordered from:
https://kartkatalog.geonorge.no/metadata/grus-og-pukk/a26e57bc-15bd-46db-8504-6c6ed1e7c501

Note: Uses fiona engine because pyogrio has encoding issues with
Norwegian characters in these particular shapefiles.
"""

from pathlib import Path

import geopandas as gpd

RAW_DIR = Path("data/raw/gruvedata")
OUTPUT_DIR = Path("data/processed")

DATA_URL = (
    "https://kartkatalog.geonorge.no/metadata/grus-og-pukk/"
    "a26e57bc-15bd-46db-8504-6c6ed1e7c501"
)


def process_shapefiles():
    if not RAW_DIR.is_dir() or not list(RAW_DIR.glob("*.shp")):
        print(f"No shapefiles found in {RAW_DIR}/")
        print()
        print("To get the data:")
        print(f"  1. Order shapefiles from: {DATA_URL}")
        print(f"  2. Extract and save to: {RAW_DIR}/")
        print("  3. Run this script again")
        return

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
