"""Checks a region directory for valid"""

from marshmallow import Schema, fields


class PolygonGeometrySchema(Schema):
    type = fields.Constant("Polygon", required=True)
    coordinates = fields.List(
        fields.List(fields.Tuple((fields.Float(), fields.Float()))),
        required=True,
    )


class PolygonFeatureSchema(Schema):
    type = fields.Constant("Feature", required=True)
    geometry = fields.Nested(PolygonGeometrySchema, required=True)
    properties = fields.Dict(required=True)


class PolygonFeatureCollectionSchema(Schema):
    type = fields.Constant("FeatureCollection", required=True)
    features = fields.List(fields.Nested(PolygonFeatureSchema))
