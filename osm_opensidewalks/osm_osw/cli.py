"""osm_opensidewalks CLI."""
import json
from pathlib import Path

import click
import rasterio
from shapely.geometry import shape

from .constants import TMP_DIR
from .dems.constants import DEM_DIR
from .dems.transforms import get_ned13_for_bounds, infer_incline, list_ned13s
from .dems.mask_dem import count_buildings, extract_buildings, mask_dem
from .osm.osm_clip import osm_clip
from .osm.osm_graph import OSMGraph
from .osm.fetch import osm_fetch
from .osw.osw_normalizer import OSWNormalizer
from .schemas.config_schema import ConfigSchema


@click.group()
def osm_osw() -> None:
    pass


@osm_osw.command()
@click.argument("config", type=click.Path())
def fetch(config: str) -> None:
    config = ConfigSchema.dict_from_filepath(config)

    for feature in config["features"]:
        click.echo(f"Fetching osm.pbf for {feature['properties']['name']}...")
        download_path = osm_fetch(
            feature["properties"]["extract_url"], progressbar=True
        )
        click.echo(f"osm.pbf has been saved to {download_path}")


@osm_osw.command()
@click.argument("config", type=click.Path())
def clip(config: str) -> None:
    config = ConfigSchema.dict_from_filepath(config)

    for region in config["features"]:
        extract_path = Path(
            TMP_DIR, Path(region["properties"]["extract_url"]).name
        )

        region_id = region["properties"]["id"]
        click.echo(f"Extracting clipped region of .osm.pbf for {region_id}...")

        clipped_path = Path(TMP_DIR, f"{region_id}.osm.pbf")

        osm_clip(extract_path, clipped_path, region)

        click.echo(f"Clipped OSM PBF is at {clipped_path}.")


@osm_osw.command()
@click.argument("config", type=click.Path())
def network(config: str) -> None:
    config = ConfigSchema.dict_from_filepath(config)

    def opensidewalks_filter(tags):
        normalizer = OSWNormalizer(tags)
        return normalizer.filter()

    for region in config["features"]:
        region_id = region["properties"]["id"]
        clipped_path = Path(TMP_DIR, f"{region_id}.osm.pbf")

        OG = OSMGraph.from_pbf(
            str(clipped_path), way_filter=opensidewalks_filter
        )
        OG.simplify()
        OG.construct_geometries()

        graph_path = Path(TMP_DIR, f"{region_id}.graph.geojson")
        OG.to_geojson(graph_path)

        click.echo("Inserted network from clipped region.")


@osm_osw.command()
@click.argument("config", type=click.Path())
def mask(config: str) -> None:
    config = ConfigSchema.dict_from_filepath(config)

    tilesets = list_ned13s()
    for region in config["features"]:
        extract_path = Path(
            TMP_DIR, Path(region["properties"]["extract_url"]).name
        )
        building_count = count_buildings(extract_path)
        with click.progressbar(
            length=building_count,
            label=f"Extracting building geometries from {extract_path}: ",
        ) as pbar:
            building_geoms = extract_buildings(extract_path, progressbar=pbar)

        for tileset in tilesets:
            tileset_path = Path(DEM_DIR, f"{tileset}.tif")
            with click.progressbar(
                length=building_count,
                label=f"Masking {tileset} with geometries from {extract_path}",
            ) as pbar:
                mask_dem(tileset_path, building_geoms, progressbar=pbar)


@osm_osw.command()
@click.argument("config", type=click.Path())
def incline(config: str) -> None:
    config = ConfigSchema.dict_from_filepath(config)

    # Infer inclines
    for region in config["features"]:
        # Download region(s) if necessary
        get_ned13_for_bounds(
            shape(region["geometry"]).bounds, progressbar=True
        )
        region_id = region["properties"]["id"]

        graph_geojson_path = Path(TMP_DIR, f"{region_id}.graph.geojson")

        # FIXME: using unweaver's geopackage might make many of these steps
        # easier
        OG = OSMGraph.from_geojson(Path(TMP_DIR, f"{region_id}.graph.geojson"))

        tilesets = list_ned13s()
        for tileset in tilesets:
            tileset_path = Path(DEM_DIR, f"{tileset}.tif")

            with rasterio.open(tileset_path) as dem:
                with click.progressbar(
                    length=len(OG.G.edges),
                    label=f"Estimating inclines for {region_id} for {tileset}",
                ) as bar:
                    for u, v, d in OG.G.edges(data=True):
                        incline = infer_incline(
                            d["geometry"], d["length"], dem, 3
                        )
                        if incline is not None:
                            d["incline"] = incline
                        bar.update(1)
        OG.to_geojson(graph_geojson_path)


@osm_osw.command()
@click.argument("config", type=click.Path())
def merge(config: str) -> None:
    config = ConfigSchema.dict_from_filepath(config)

    fc = {"type": "FeatureCollection", "features": []}

    for region in config["features"]:
        region_id = region["properties"]["id"]
        graph_geojson_path = Path(TMP_DIR, f"{region_id}.graph.geojson")

        with open(graph_geojson_path) as f:
            region_fc = json.load(f)

        fc["features"] = fc["features"] + region_fc["features"]

    with open(Path(TMP_DIR, "transportation.geojson"), "w") as f:
        json.dump(fc, f)
