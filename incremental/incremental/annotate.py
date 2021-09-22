import geopandas as gpd


def annotate_intersected_gdf(
    gdf_in: gpd.GeoDataFrame,
    gdf_proj: gpd.GeoDataFrame,
    label: str,
    subset=None,
) -> None:
    """Annotate a GeoDataFrame with a custom boolean (1 or 0) label based on
    whether the elements of the input GeoDataFrame intersect with GeoDataFrame
    of project task polygons (will actually work with any Polygon
    GeoDataFrame).

    :param gdf_in: Input GeoDataFrame. It will be modified in-place.
    :type gdf_in: GeoDataFrame
    :param gdf_proj: Polygon GeoDataFrame.
    :type gdf_in: GeoDataFrame
    :param label: The key to use for the new boolean annotations.
    :type label: str
    :param subset: A boolean-valued Series equivalent to a Pandas query.
    :type subset: Iterable of booleans
    :returns: None

    """

    joined = gpd.sjoin(
        gdf_in, gdf_proj, how="inner", op="intersects", rsuffix="_proj"
    )

    if subset is not None:
        index = gdf_in.index[subset & gdf_in.index.isin(joined.index)]
    else:
        index = joined.index
    gdf_in.loc[index, "crossings_mapped"] = 1


def annotate_crossings(
    gdf_in: gpd.GeoDataFrame,
    gdf_proj: gpd.GeoDataFrame,
) -> None:
    # subset = (gdf_in["highway"] == "footway") & (
    #     gdf_in["footway"] == "crossing"
    # )
    annotate_intersected_gdf(gdf_in, gdf_proj, "crossings_mapped")


# FIXME: how to handle kerb nodes?


def annotate_sidewalks(
    gdf_in: gpd.GeoDataFrame,
    gdf_proj: gpd.GeoDataFrame,
) -> None:
    # subset = (gdf_in["highway"] == "footway") & (
    #     gdf_in["footway"] == "sidewalk"
    # )
    annotate_intersected_gdf(gdf_in, gdf_proj, "sidewalks_mapped")
