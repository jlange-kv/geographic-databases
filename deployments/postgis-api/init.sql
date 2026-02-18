CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE features (
    id SERIAL PRIMARY KEY,
    geometry geometry(Geometry, 4326),
    properties JSONB NOT NULL DEFAULT '{}'
);

CREATE INDEX idx_features_geom ON features USING GIST (geometry);