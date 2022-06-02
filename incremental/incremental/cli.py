"""incremental CLI."""
import asyncio
import json
import os
from pathlib import Path
import shutil
from typing import Iterable

import aiohttp
import click
import geopandas as gpd
import pandas as pd

from .annotate import annotate_crossings, annotate_sidewalks
from .schemas.config_schema import ConfigSchema


@click.group()
def incremental() -> None:
    pass


@incremental.command()
@click.argument("config", type=click.Path())
@click.argument("output_dir", type=click.Path())
def fetch(config, output_dir) -> None:
    config = ConfigSchema.dict_from_filepath(config)

    async def fetch_project_tasks(session, project_id):
        async with session.get(
            f"/api/v2/projects/{project_id}/tasks/"
        ) as resp:
            if resp.status != 200:
                click.echo(
                    f"Failed to fetch project {project_id}: "
                    f"status {resp.status}"
                )
                return project_id, None
            else:
                return (project_id, await resp.json())

    # TODO: abstract this to remove repetitive code, put custom logic into
    # dedicated, resuable module
    for tasking_manager in config["tasking_managers"]:
        url = tasking_manager["url"]
        crossing_projects = tasking_manager.get("crossing_projects", [])
        sidewalk_projects = tasking_manager.get("sidewalk_projects", [])

        if crossing_projects:
            click.echo(
                f"Fetching task polygons for {len(crossing_projects)} "
                "projects..."
            )

            async def crossing_tasks_main():
                project_ids = crossing_projects

                async with aiohttp.ClientSession(url) as session:
                    tasks = []
                    for project_id in project_ids:
                        task = asyncio.Task(
                            fetch_project_tasks(session, project_id)
                        )
                        tasks.append(task)

                    results = await asyncio.gather(*tasks)
                    return results

            crossings_task_list = asyncio.run(crossing_tasks_main())
            if not os.path.exists(output_dir):
                os.mkdir(output_dir)

            crossings_tasks_dir = Path(output_dir, "crossings")

            if os.path.exists(crossings_tasks_dir):
                shutil.rmtree(crossings_tasks_dir)
            os.mkdir(crossings_tasks_dir)

            for project_id, tasks_json in crossings_task_list:
                with open(
                    Path(crossings_tasks_dir, f"{project_id}_tasks.geojson"),
                    "w",
                ) as f:
                    json.dump(tasks_json, f)

        if sidewalk_projects:
            click.echo(
                f"Fetching task polygons for {len(sidewalk_projects)} "
                "projects..."
            )

            async def sidewalk_tasks_main():
                project_ids = sidewalk_projects

                async with aiohttp.ClientSession(url) as session:
                    tasks = []
                    for project_id in project_ids:
                        task = asyncio.Task(
                            fetch_project_tasks(session, project_id)
                        )
                        tasks.append(task)

                    results = await asyncio.gather(*tasks)
                    return results

            sidewalks_task_list = asyncio.run(sidewalk_tasks_main())
            if not os.path.exists(output_dir):
                os.mkdir(output_dir)

            sidewalks_tasks_dir = Path(output_dir, "sidewalks")
            if os.path.exists(sidewalks_tasks_dir):
                shutil.rmtree(sidewalks_tasks_dir)
            os.mkdir(sidewalks_tasks_dir)

            for project_id, tasks_json in sidewalks_task_list:
                with open(
                    Path(sidewalks_tasks_dir, f"{project_id}_tasks.geojson"),
                    "w",
                ) as f:
                    json.dump(tasks_json, f)


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
        mapped = gdf_proj["taskStatus"] == "MAPPED"
        validated = gdf_proj["taskStatus"] == "VALIDATED"
        gdf_mapped = gdf_proj[mapped | validated]
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
        mapped = gdf_proj["taskStatus"] == "MAPPED"
        validated = gdf_proj["taskStatus"] == "VALIDATED"
        gdf_mapped = gdf_proj[mapped | validated]
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
