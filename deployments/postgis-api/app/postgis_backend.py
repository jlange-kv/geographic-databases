import json

from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from psycopg_pool import AsyncConnectionPool
from shared.models import Feature, FeatureCreate, Geometry
from shared.storage import StorageBackend


class PostGISBackend(StorageBackend):
    def __init__(self, database_url: str):
        self._database_url = database_url
        self._pool: AsyncConnectionPool | None = None

    async def connect(self) -> None:
        self._pool = AsyncConnectionPool(
            self._database_url,
            min_size=2,
            max_size=10,
            kwargs={"row_factory": dict_row},
        )
        await self._pool.open()

    async def disconnect(self) -> None:
        if self._pool is not None:
            await self._pool.close()

    def _row_to_feature(self, row: dict) -> Feature:
        """Convert a database row (dict) to a Feature model."""
        return Feature(
            id=row["id"],
            geometry=Geometry(**json.loads(row["geometry"])),
            properties=row["properties"],
        )

    async def create_feature(self, feature: FeatureCreate) -> Feature:
        async with self._pool.connection() as conn:
            serialised_geom = json.dumps(feature.geometry.model_dump())
            result = await conn.execute(
                """
                INSERT INTO features (geometry, properties)
                VALUES (ST_GeomFromGeoJSON(%(geometry)s), %(properties)s)
                RETURNING id, ST_AsGeoJSON(geometry) AS geometry, properties
                """,
                {
                    "geometry": serialised_geom,
                    "properties": Jsonb(feature.properties),
                },  # Prevent SQL injection
            )
            row = await result.fetchone()
        return self._row_to_feature(row)

    async def get_feature(self, feature_id: int) -> Feature | None:
        async with self._pool.connection() as conn:
            result = await conn.execute(
                """
                SELECT id, ST_AsGeoJSON(geometry) AS geometry, properties 
                FROM features WHERE id = %(id)s
                """,
                {"id": feature_id},  # Prevent SQL Injection
            )
            row = await result.fetchone()
        if row is None:
            return None
        return self._row_to_feature(row)

    async def list_features(self, bbox=None, limit=100, offset=0) -> list[Feature]:
        async with self._pool.connection() as conn:
            query = """
                    SELECT id, ST_AsGeoJSON(geometry) AS geometry, properties
                    FROM features 
                    """
            params = {"limit": limit, "offset": offset}
            if bbox is not None:
                query += " WHERE geometry && ST_MakeEnvelope(%(minx)s, %(miny)s, %(maxx)s, %(maxy)s, 4326)"
                params.update(
                    {"minx": bbox[0], "miny": bbox[1], "maxx": bbox[2], "maxy": bbox[3]}
                )
            query += " LIMIT %(limit)s OFFSET %(offset)s"
            result = await conn.execute(query=query, params=params)
            rows = await result.fetchall()
        return list(map(self._row_to_feature, rows))

    async def update_feature(
        self, feature_id: int, feature: FeatureCreate
    ) -> Feature | None:
        serialised_geom = json.dumps(feature.geometry.model_dump())
        async with self._pool.connection() as conn:
            result = await conn.execute(
                """
                UPDATE features
                SET geometry = ST_GeomFromGeoJSON(%(geometry)s), properties = %(properties)s
                WHERE id = %(id)s
                RETURNING id, ST_AsGeoJSON(geometry) as geometry, properties 
                """,
                {
                    "geometry": serialised_geom,
                    "properties": Jsonb(feature.properties),
                    "id": feature_id,
                },
            )
            new_feature = await result.fetchone()
        if new_feature is None:
            return new_feature
        return self._row_to_feature(new_feature)

    async def delete_feature(self, feature_id: int) -> bool:
        async with self._pool.connection() as conn:
            result = await conn.execute(
                """
                DELETE FROM features WHERE id = %(id)s
                """,
                {"id": feature_id},
            )
        return result.rowcount > 0

    async def count_features(self) -> int:
        async with self._pool.connection() as conn:
            result = await conn.execute("SELECT COUNT(*) FROM features")
            row = await result.fetchone()
        return row["count"]
