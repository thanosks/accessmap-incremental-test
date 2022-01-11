"""incremental CLI."""
from typing import Iterable

import click
import geopandas as gpd
import pandas as pd

from .annotate import annotate_crossings, annotate_sidewalks


@click.group()
def incremental() -> None:
    pass


@incremental.command()
@click.argument("transportation_geojson", type=click.Path())
@click.argument("output_geojson", type=click.Path())
@click.argument("project_geojson", type=click.Path(), nargs=-1)
def crossings(
    transportation_geojson: str,
    output_geojson: str,
    project_geojson: Iterable[str],
) -> None:
    click.echo(f"Reading file {transportation_geojson}...")

    all_gdfs = []
    gdf = gpd.read_file(transportation_geojson)
    gdf["crossings_mapped"] = 0
    for geojson in project_geojson:
        click.echo(f"    Annotating from {geojson}...")
        gdf_proj = gpd.read_file(geojson)
        gdf_mapped = gdf_proj[gdf_proj["taskStatus"] == "MAPPED"]
        # TODO: this function is so simple - just put it here instead?
        annotate_crossings(gdf, gdf_mapped)
        # Accumulate tasks
        all_gdfs.append(gdf_proj)
    click.echo(f"Writing to {output_geojson}...")
    gdf.to_file(output_geojson, driver="GeoJSON")

    output_task_geojson = output_geojson + ".crossingtasks.geojson"
    click.echo(f"Writing task status to {output_task_geojson}")
    tasks_gdf = gpd.GeoDataFrame(pd.concat(all_gdfs))
    tasks_gdf.crs = gdf_proj.crs
    tasks_gdf.to_file(output_task_geojson, driver="GeoJSON")


@incremental.command()
@click.argument("transportation_geojson", type=click.Path())
@click.argument("output_geojson", type=click.Path())
@click.argument("project_geojson", type=click.Path(), nargs=-1)
def sidewalks(
    transportation_geojson: str,
    output_geojson: str,
    project_geojson: Iterable[str],
) -> None:
    click.echo(f"Reading file {transportation_geojson}...")

    all_gdfs = []
    gdf = gpd.read_file(transportation_geojson)
    gdf["sidewalks_mapped"] = 0
    for geojson in project_geojson:
        click.echo(f"    Annotating from {geojson}...")
        gdf_proj = gpd.read_file(geojson)
        gdf_mapped = gdf_proj[gdf_proj["taskStatus"] == "MAPPED"]
        # TODO: this function is so simple - just put it here instead?
        annotate_sidewalks(gdf, gdf_mapped)
        # Accumulate tasks
        all_gdfs.append(gdf_proj)

    click.echo(f"Writing to {output_geojson}...")
    gdf.to_file(output_geojson, driver="GeoJSON")

    output_task_geojson = output_geojson + ".sidewalktasks.geojson"
    click.echo(f"Writing task status to {output_task_geojson}")
    tasks_gdf = gpd.GeoDataFrame(pd.concat(all_gdfs))
    tasks_gdf.crs = gdf_proj.crs
    tasks_gdf.to_file(output_task_geojson, driver="GeoJSON")
