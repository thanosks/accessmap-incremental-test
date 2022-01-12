"""Checks a region directory for valid"""
import json
from pathlib import Path

from marshmallow import Schema, fields


class TaskingManagerJSON(Schema):
    url = fields.Str(required=True)
    crossing_projects = fields.List(fields.Integer, required=False)
    sidewalk_projects = fields.List(fields.Integer, required=False)


class ConfigSchema(Schema):
    tasking_managers = fields.List(
        fields.Nested(TaskingManagerJSON), required=True
    )

    @classmethod
    def dict_from_filepath(self, path):
        config_path = Path(path)

        with open(config_path) as f:
            config = json.load(f)

        schema = ConfigSchema()
        config_dict = schema.load(config)
        return config_dict
