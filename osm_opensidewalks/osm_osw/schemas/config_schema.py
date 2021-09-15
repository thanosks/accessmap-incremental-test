"""Checks a region directory for valid"""
import json
from pathlib import Path

from marshmallow import fields

from .geojson import PolygonFeatureSchema, PolygonFeatureCollectionSchema
from .region_schema import RegionPropertiesSchema


class ConfigPropertiesSchema(RegionPropertiesSchema):
    extract_url = fields.Str(required=True)


class ConfigFeatureSchema(PolygonFeatureSchema):
    properties = fields.Nested(ConfigPropertiesSchema, required=True)


class ConfigSchema(PolygonFeatureCollectionSchema):
    features = fields.List(fields.Nested(ConfigFeatureSchema))

    @classmethod
    def dict_from_filepath(self, path):
        config_path = Path(path)

        with open(config_path) as f:
            config = json.load(f)

        schema = ConfigSchema()
        config_dict = schema.load(config)
        return config_dict
