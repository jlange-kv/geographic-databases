#!/usr/bin/env python3
"""
Quick test script for PostGIS backend.
Run this after starting PostgreSQL with PostGIS.
"""

import asyncio

from app.postgis_backend import PostGISBackend
from shared.models import FeatureCreate, Geometry

# Database connection (adjust if needed)
DB_URL = "postgresql://postgres:postgres@localhost:5432/geodata"


async def main():
    print("Initializing PostGIS backend...")
    backend = PostGISBackend(DB_URL)
    await backend.connect()

    try:
        # Test 1: Count (should be 0 initially)
        count = await backend.count_features()
        print(f"Initial count: {count}")

        # Test 2: Create a feature
        feature_data = FeatureCreate(
            geometry=Geometry(
                type="Point",
                coordinates=[10.0, 59.0],  # Oslo, Norway
            ),
            properties={"name": "Test Point", "category": "test"},
        )
        created = await backend.create_feature(feature_data)
        print(f"Created feature with ID: {created.id}")
        print(f"Geometry: {created.geometry.type} at {created.geometry.coordinates}")
        print(f"Properties: {created.properties}")

        # Test 3: Get the feature back
        retrieved = await backend.get_feature(created.id)
        assert retrieved is not None, "Feature should exist"
        assert retrieved.id == created.id, "IDs should match"
        print(f"Retrieved feature ID {retrieved.id}")

        # Test 4: Create another feature
        feature_data2 = FeatureCreate(
            geometry=Geometry(
                type="Point",
                coordinates=[5.0, 60.0],  # Bergen area
            ),
            properties={"name": "Another Point"},
        )
        created2 = await backend.create_feature(feature_data2)
        print(f"Created second feature with ID: {created2.id}")

        # Test 5: List all features
        all_features = await backend.list_features(limit=10)
        print(f"Listed {len(all_features)} features")

        # Test 6: List with bbox (should include Oslo but not Bergen)
        oslo_bbox = (9.5, 58.5, 10.5, 59.5)  # min_lon, min_lat, max_lon, max_lat
        oslo_features = await backend.list_features(bbox=oslo_bbox)
        print(f"Bbox filter found {len(oslo_features)} feature(s) near Oslo")
        assert len(oslo_features) == 1, "Should only find Oslo point"

        # Test 7: Update the first feature
        updated_data = FeatureCreate(
            geometry=Geometry(type="Point", coordinates=[10.1, 59.1]),
            properties={"name": "Updated Point", "category": "modified"},
        )
        updated = await backend.update_feature(created.id, updated_data)
        assert updated is not None, "Update should succeed"
        assert updated.properties["name"] == "Updated Point", "Name should be updated"
        print(f"Updated feature ID {created.id}")

        # Test 8: Try to update non-existent feature
        not_found = await backend.update_feature(99999, updated_data)
        assert not_found is None, "Should return None for non-existent ID"
        print("Update with invalid ID correctly returned None")

        # Test 9: Delete a feature
        deleted = await backend.delete_feature(created2.id)
        assert deleted is True, "Delete should return True"
        print(f"Deleted feature ID {created2.id}")

        # Test 10: Try to delete non-existent feature
        not_deleted = await backend.delete_feature(99999)
        assert not_deleted is False, "Should return False for non-existent ID"
        print("Delete with invalid ID correctly returned False")

        # Test 11: Final count
        final_count = await backend.count_features()
        print(f"Final count: {final_count}")
        assert final_count == 1, "Should have 1 feature remaining"

        print("\nAll tests passed!")

    finally:
        await backend.disconnect()
        print("Disconnected")


if __name__ == "__main__":
    asyncio.run(main())
