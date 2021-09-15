import json
from pathlib import Path
import subprocess
import tempfile


class OSMClipError(Exception):
    pass


# FIXME: instead of dict, use dataclass for config region schema
def osm_clip(in_pbf_path: str, out_pbf_path: str, polygon: dict):
    """Clips an OSM"""

    with tempfile.TemporaryDirectory() as tmpdirname:
        temporary_path = Path(tmpdirname, "region.geojson")
        with open(temporary_path, "w") as fp:
            json.dump(polygon, fp)

        try:
            # FIXME: when input polygon is bad, this doesn't raise a
            # subprocess.CalledProcessError. How else can we catch this error?
            subprocess.run(
                [
                    "osmium",
                    "extract",
                    "-p",
                    temporary_path,
                    in_pbf_path,
                    "-o",
                    out_pbf_path,
                ]
            )
        except subprocess.CalledProcessError as e:
            raise OSMClipError(e.message)

    return out_pbf_path
