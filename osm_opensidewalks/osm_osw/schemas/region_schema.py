"""Checks a region directory for valid"""

from marshmallow import Schema, fields

from .geojson import PolygonFeatureSchema, PolygonFeatureCollectionSchema


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


class RegionFeatureSchema(PolygonFeatureSchema):
    properties = fields.Nested(RegionPropertiesSchema, required=True)


class RegionFeatureCollectionSchema(PolygonFeatureCollectionSchema):
    features = fields.List(fields.Nested(RegionFeatureSchema))
