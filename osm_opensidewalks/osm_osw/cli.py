"""osm_opensidewalks CLI."""
import asyncio
import json
from pathlib import Path

import click
import rasterio
from shapely.geometry import shape

from .constants import TMP_DIR
from .dems.transforms import get_ned13_for_bounds, infer_incline, list_ned13s
from .dems.mask_dem import count_buildings, extract_buildings, mask_dem
from .osm.osm_clip import osm_clip
from .osm.osm_graph import OSMGraph, NodeCounter, WayCounter
from .osm.fetch import osm_fetch
from .osw.osw_normalizer import OSWWayNormalizer, OSWNodeNormalizer
from .schemas.config_schema import ConfigSchema
from .inference.curb_ramps import infer_curbramps as infer_osm_curbramps


@click.group()
def osm_osw() -> None:
    pass


@osm_osw.command()
@click.argument("config", type=click.Path())
@click.option("--workdir", envvar="OSM_OSW_WORKDIR", default=TMP_DIR)
def fetch(config: str, workdir: str) -> None:
    config = ConfigSchema.dict_from_filepath(config)

    for feature in config["features"]:
        click.echo(f"Fetching osm.pbf for {feature['properties']['name']}...")
        download_path = osm_fetch(
            feature["properties"]["extract_url"],
            workdir,
            progressbar=True,
        )
        click.echo(f"osm.pbf has been saved to {download_path}")


@osm_osw.command()
@click.argument("config", type=click.Path())
@click.option("--workdir", envvar="OSM_OSW_WORKDIR", default=TMP_DIR)
def clip(config: str, workdir: str) -> None:
    # FIXME: add option to configure number of simultaneous processes and/or
    # maximum memory usage.
    config = ConfigSchema.dict_from_filepath(config)

    regions = [region["properties"]["id"] for region in config["features"]]
    click.echo(f"Extracting clipped .osm.pbf regions for {', '.join(regions)}")

    osm_clips = []
    for region in config["features"]:
        extract_path = Path(
            workdir, Path(region["properties"]["extract_url"]).name
        )

        region_id = region["properties"]["id"]

        clipped_path = Path(workdir, f"{region_id}.osm.pbf")

        osm_clips.append(osm_clip(extract_path, clipped_path, region))

    async def run_all_osm_clips():
        await asyncio.gather(*osm_clips)

    asyncio.run(run_all_osm_clips())

    click.echo("Clipped OSM PBFs.")


@osm_osw.command()
@click.argument("config", type=click.Path())
@click.option("--workdir", envvar="OSM_OSW_WORKDIR", default=TMP_DIR)
@click.option("-s/-ns", "--simplify/--no_simplify", default=True)
def network(config: str, workdir: str, simplify: bool) -> None:
    # FIXME: move at least some of the async functionality to upstream modules,
    # e.g. the 'asyncifying' run_in_executor-using async functions
    config = ConfigSchema.dict_from_filepath(config)

    # FIXME: define this at a module-level and make it the default behavior.
    # OpenSidewalks Schema-fication should be hardcoded (for now).
    def opensidewalks_way_filter(tags):
        normalizer = OSWWayNormalizer(tags)
        return normalizer.filter()

    def opensidewalks_node_filter(tags):
        normalizer = OSWNodeNormalizer(tags)
        return normalizer.filter()

    #
    # Get counts of all ways/nodes in each dataset
    #

    async def count_ways(pbf_path: str):
        loop = asyncio.get_event_loop()
        way_counter = WayCounter()
        await loop.run_in_executor(None, way_counter.apply_file, pbf_path)
        return way_counter.count

    async def count_nodes(pbf_path: str):
        loop = asyncio.get_event_loop()
        node_counter = NodeCounter()
        await loop.run_in_executor(None, node_counter.apply_file, pbf_path)
        return node_counter.count

    tasks = []
    for region in config["features"]:
        region_id = region["properties"]["id"]
        pbf_path = str(Path(workdir, f"{region_id}.osm.pbf"))
        tasks.append(count_ways(pbf_path))
        tasks.append(count_nodes(pbf_path))

    with click.progressbar(
        length=len(tasks),
        label="Estimating number of ways and nodes in datasets...",
    ) as pbar:

        async def count_main():
            results = []
            for future in asyncio.as_completed(tasks):
                pbar.update(1)
                results.append(await future)
            return results

        count_results = asyncio.run(count_main())
    graph_element_count = sum(count_results)

    #
    # Create an OSMGraph per region
    #
    async def get_osmgraph(region_id, pbf_path, way_filter, node_filter, pbar):
        loop = asyncio.get_event_loop()
        OG = await loop.run_in_executor(
            None,
            OSMGraph.from_pbf,
            pbf_path,
            way_filter,
            node_filter,
            pbar,
        )
        return region_id, OG

    with click.progressbar(
        length=graph_element_count,
        label="Creating networks from region extracts...",
    ) as pbar:

        tasks = []
        for region in config["features"]:
            region_id = region["properties"]["id"]
            pbf_path = str(Path(workdir, f"{region_id}.osm.pbf"))
            tasks.append(
                get_osmgraph(
                    region_id,
                    pbf_path,
                    opensidewalks_way_filter,
                    opensidewalks_node_filter,
                    pbar,
                )
            )

        async def osm_graph_main():
            return await asyncio.gather(*tasks)

        osm_graph_results = asyncio.run(osm_graph_main())

    osm_graph_results = list(osm_graph_results)
    #
    # Optionally, simplify ways by joining simple connection nodes (degree-2)
    #
    if simplify:

        async def simplify_og(og):
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, og.simplify)

        with click.progressbar(
            length=len(osm_graph_results),
            label="Simplifying ways...",
        ) as pbar:

            async def simplify_main():
                tasks = [
                    simplify_og(OG) for region_id, OG in osm_graph_results
                ]
                for future in asyncio.as_completed(tasks):
                    pbar.update(1)
                    await future

            asyncio.run(simplify_main())

    #
    # Construct geometries
    #
    async def construct_geometries(og, pbar):
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, og.construct_geometries, pbar)

    with click.progressbar(
        length=len(osm_graph_results),
        label="Constructing geometries...",
    ) as pbar:

        async def construct_geometries_main():
            tasks = [
                construct_geometries(OG, pbar)
                for region_id, OG in osm_graph_results
            ]
            await asyncio.gather(*tasks)

        asyncio.run(construct_geometries_main())

    #
    # Write to file
    #
    async def write_og(region_id: str, og):
        loop = asyncio.get_event_loop()
        nodes_path = Path(workdir, f"{region_id}.graph.nodes.geojson")
        edges_path = Path(workdir, f"{region_id}.graph.edges.geojson")
        await loop.run_in_executor(None, og.to_geojson, nodes_path, edges_path)

    with click.progressbar(
        length=len(osm_graph_results),
        label="Writing graph nodes and edges GeoJSONs to file...",
    ) as pbar:

        async def write_main():
            tasks = [
                write_og(region_id, OG) for region_id, OG in osm_graph_results
            ]
            for future in asyncio.as_completed(tasks):
                pbar.update(1)
                await future

        asyncio.run(write_main())

    regions = ", ".join(r for r, o in osm_graph_results)
    click.echo(f"Created networks from the clipped {regions} region(s).")


"""
    for region in config["features"]:
        region_id = region["properties"]["id"]
        clipped_path = Path(workdir, f"{region_id}.osm.pbf")

        # TODO: add a progressbar
        click.echo(f"Counting network ways in {region_id}...")
        way_counter = WayCounter()
        way_counter.apply_file(str(clipped_path))
        node_counter = NodeCounter()
        node_counter.apply_file(str(clipped_path))
        with click.progressbar(
            length=way_counter.count + node_counter.count,
            label=f"Importing ways for {region_id}...",
        ) as pbar:
            OG = OSMGraph.from_pbf(
                str(clipped_path),
                way_filter=opensidewalks_way_filter,
                node_filter=opensidewalks_node_filter,
                progressbar=pbar,
            )

        if simplify:
            click.echo(f"Joining degree-2 nodes for {region_id}...")
            OG.simplify()

        with click.progressbar(
            length=len(OG.G.edges) + len(OG.G.nodes),
            label=f"Constructing geometries for {region_id}...",
        ) as pbar:
            OG.construct_geometries(progressbar=pbar)

        graph_nodes_path = Path(workdir, f"{region_id}.graph.nodes.geojson")
        graph_edges_path = Path(workdir, f"{region_id}.graph.edges.geojson")
        OG.to_geojson(graph_nodes_path, graph_edges_path)

        click.echo(f"Created network from clipped {region_id} region.")
        """


@osm_osw.command()
@click.argument("config", type=click.Path())
@click.option("--workdir", envvar="OSM_OSW_WORKDIR", default=TMP_DIR)
def mask(config: str, workdir: str) -> None:
    config = ConfigSchema.dict_from_filepath(config)

    tilesets = list_ned13s(workdir)
    tileset_paths = [
        Path(workdir, "dems", f"{tileset}.tif") for tileset in tilesets
    ]

    # Create blank mask by default - no pixels are masked.
    for path in tileset_paths:
        with rasterio.open(path, "r+") as rast:
            rast.write_mask(True)

    # Add masked regions
    for region in config["features"]:
        region_id = region["properties"]["id"]
        # Fetch DEMs if they aren't already cached
        get_ned13_for_bounds(
            shape(region["geometry"]).bounds, workdir, progressbar=True
        )

        clipped_extract_path = Path(workdir, f"{region_id}.osm.pbf")
        click.echo(f"Counting buildings in {region_id}...")
        building_count = count_buildings(clipped_extract_path)
        with click.progressbar(
            length=building_count,
            label=f"Extracting buildings from {region_id}: ",
        ) as pbar:
            building_geoms = extract_buildings(
                clipped_extract_path, progressbar=pbar
            )

        for tileset, path in zip(tilesets, tileset_paths):
            with click.progressbar(
                length=building_count,
                label=f"Masking {tileset} with geometries from {region_id}",
            ) as pbar2:
                mask_dem(path, building_geoms, progressbar=pbar2)


@osm_osw.command()
@click.argument("config", type=click.Path())
@click.option("--workdir", envvar="OSM_OSW_WORKDIR", default=TMP_DIR)
def infer_curbramps(config: str, workdir: str) -> None:
    config = ConfigSchema.dict_from_filepath(config)

    # Infer inclines
    for region in config["features"]:
        region_id = region["properties"]["id"]

        graph_nodes_path = Path(workdir, f"{region_id}.graph.nodes.geojson")
        graph_edges_path = Path(workdir, f"{region_id}.graph.edges.geojson")

        OG = OSMGraph.from_geojson(graph_nodes_path, graph_edges_path)
        with click.progressbar(
            length=len(OG.G.edges),
            label=f"Inferring curbramps for {region_id}",
        ) as bar:
            infer_osm_curbramps(OG, progressbar=bar)
        OG.to_geojson(graph_nodes_path, graph_edges_path)


@osm_osw.command()
@click.argument("config", type=click.Path())
@click.option("--workdir", envvar="OSM_OSW_WORKDIR", default=TMP_DIR)
def incline(config: str, workdir: str) -> None:
    config = ConfigSchema.dict_from_filepath(config)

    # Infer inclines
    for region in config["features"]:
        # Download region(s) if necessary
        get_ned13_for_bounds(
            shape(region["geometry"]).bounds, workdir, progressbar=True
        )
        region_id = region["properties"]["id"]

        graph_nodes_path = Path(workdir, f"{region_id}.graph.nodes.geojson")
        graph_edges_path = Path(workdir, f"{region_id}.graph.edges.geojson")

        # FIXME: using unweaver's geopackage might make many of these steps
        # easier
        OG = OSMGraph.from_geojson(graph_nodes_path, graph_edges_path)

        tilesets = list_ned13s(workdir)
        for tileset in tilesets:
            tileset_path = Path(workdir, "dems", f"{tileset}.tif")

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

        OG.to_geojson(graph_nodes_path, graph_edges_path)


@osm_osw.command()
@click.argument("config", type=click.Path())
@click.option("--workdir", envvar="OSM_OSW_WORKDIR", default=TMP_DIR)
def merge(config: str, workdir: str) -> None:
    config = ConfigSchema.dict_from_filepath(config)

    fc = {"type": "FeatureCollection", "features": []}

    for region in config["features"]:
        region_id = region["properties"]["id"]
        graph_geojson_path = Path(workdir, f"{region_id}.graph.edges.geojson")

        with open(graph_geojson_path) as f:
            region_fc = json.load(f)

        fc["features"] = fc["features"] + region_fc["features"]

    with open(Path(workdir, "transportation.geojson"), "w") as f:
        json.dump(fc, f)


@osm_osw.command()
@click.argument("config", type=click.Path())
@click.option("--workdir", envvar="OSM_OSW_WORKDIR", default=TMP_DIR)
@click.pass_context
def runall(ctx: click.Context, config: str, workdir: str) -> None:
    ctx.forward(clip)
    ctx.forward(network)
    ctx.forward(infer_curbramps)
    ctx.forward(mask)
    ctx.forward(incline)
    ctx.forward(merge)
