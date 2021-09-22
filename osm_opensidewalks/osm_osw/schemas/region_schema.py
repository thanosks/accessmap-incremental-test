"""Checks a region directory for valid"""

from marshmallow import Schema, fields

from .geojson import (
    MultiPolygonFeatureSchema,
    MultiPolygonFeatureCollectionSchema,
)


class RegionPropertiesSchema(Schema):
    name = fields.Str(required=True)
    id = fields.Str(required=True)
    lon = fields.Float(required=True)
    lat = fields.Float(required=True)
    zoom = fields.Number(required=True)
    bounds = fields.Tuple(
        (fields.Float(), fields.Float(), fields.Float(), fields.Float()),
        required=True,
    )


class RegionFeatureSchema(MultiPolygonFeatureSchema):
    properties = fields.Nested(RegionPropertiesSchema, required=True)


class RegionFeatureCollectionSchema(MultiPolygonFeatureCollectionSchema):
    features = fields.List(fields.Nested(RegionFeatureSchema))
