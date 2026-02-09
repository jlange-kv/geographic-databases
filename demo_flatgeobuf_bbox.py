"""Demonstrate FlatGeobuf spatial filtering with bounding box queries.

Shows how FlatGeobuf's built-in R-tree spatial index enables fast
spatial filtering, reading only features that intersect the query area.
"""

import time
from pathlib import Path

import geopandas as gpd

FGB_PATH = Path("data/processed/SandGrusRegistrering.fgb")

# Bounding box roughly covering the Oslo region (EPSG:25833)
OSLO_BBOX = (240000, 6620000, 280000, 6660000)

N_RUNS = 100


def benchmark(
    path: Path, bbox: tuple | None = None, n: int = N_RUNS
) -> tuple[gpd.GeoDataFrame, float]:
    """Run multiple reads and return (last GeoDataFrame, average_time)."""
    start = time.perf_counter()
    gdf = None
    for _ in range(n):
        gdf = gpd.read_file(path, bbox)
    avg_time = (time.perf_counter() - start) / n
    return gdf, avg_time


def memory_usage_mb(gdf: gpd.GeoDataFrame) -> float:
    """Estimate memory usage of a GeoDataFrame in MB."""
    return gdf.memory_usage(deep=True).sum() / (1024**2)


def main():
    if not FGB_PATH.exists():
        print(f"Data file not found: {FGB_PATH}")
        print()
        print("Run process_data.py first to generate the FlatGeobuf files.")
        print("See process_data.py for download instructions.")
        return

    print("=== FlatGeobuf Spatial Filtering Demo ===\n")
    print(f"Averaging over {N_RUNS} runs\n")

    # Full read (no spatial filter)
    gdf_full, full_time = benchmark(FGB_PATH)
    bounds = gdf_full.total_bounds
    full_mem = memory_usage_mb(gdf_full)
    print(f"Full read:  {len(gdf_full):>6} features in {full_time:.4f}s (avg)")
    print(
        f"  Bounding box: x=[{bounds[0]:.0f}, {bounds[2]:.0f}], y=[{bounds[1]:.0f}, {bounds[3]:.0f}]"
    )
    print(f"  Memory usage: {full_mem:.2f} MB")
    print()

    # Bbox-filtered read (uses R-tree spatial index)
    gdf_bbox, bbox_time = benchmark(FGB_PATH, bbox=OSLO_BBOX)
    bbox_mem = memory_usage_mb(gdf_bbox)
    print(f"Bbox read:  {len(gdf_bbox):>6} features in {bbox_time:.4f}s (avg)")
    print(
        f"  Bounding box: x=[{OSLO_BBOX[0]}, {OSLO_BBOX[2]}], y=[{OSLO_BBOX[1]}, {OSLO_BBOX[3]}]"
    )
    print(f"  Memory usage: {bbox_mem:.2f} MB")
    print()

    # Summary
    print("--- Results ---")
    print(f"Speedup:        {full_time / bbox_time:.1f}x faster with bbox filter")
    print(
        f"Data reduction: {len(gdf_full)} → {len(gdf_bbox)} features ({len(gdf_bbox) / len(gdf_full) * 100:.1f}%)"
    )
    print(
        f"Memory saving:  {full_mem:.2f} MB → {bbox_mem:.2f} MB ({bbox_mem / full_mem * 100:.1f}%)"
    )
    print()

    # Show the features found in the bbox
    if len(gdf_bbox) > 0:
        print("Features found in Oslo region:")
        print(gdf_bbox[["FOREKNAVN", "RASTO_NAVN"]].to_string())


if __name__ == "__main__":
    main()
