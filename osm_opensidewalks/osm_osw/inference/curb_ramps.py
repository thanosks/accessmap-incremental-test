"""Infer the presence of curb ramps at each side of a crossing."""
import pygeos
import utm


ACCESSIBLE_KERBS = ("flush", "lowered")


def _is_crossing(properties):
    if (
        properties.get("highway", "") == "footway"
        and properties.get("footway", "") == "crossing"
    ):
        return True
    return False


def near_curbramp(endpoints, sindex, distance):
    for endpoint in endpoints:
        x, y = utm.from_latlon(*reversed(endpoint))[:2]
        point = pygeos.points((x, y))
        buffered = pygeos.buffer(point, distance)
        if sindex.query(buffered, "intersects").shape[0]:
            # Found a nearby kerb ramp!
            return True
    return False


def infer_curbramps(OG, distance=3, progressbar=None):
    """Populate the 'curbramps' field of crossing LineStrings within an
    OpenSidewalks dataset based on proximity.

    :param OG: An OpenSidewalks Graph normalized to the OpenSidewalks schema.
               Its graph object (OG.G) will be updated in-place
    :type OG: osm_osw.osm.osm_graph.OSMGraph
    :param distance: Search distance for nearest curb ramp in meters.
    :type distance: Numeric

    """
    # Put all curb nodes into a spatial index (for rapid distance queries)
    kerbs = []
    for n, d in OG.G.nodes(data=True):
        if "kerb" in d and d["kerb"] in ACCESSIBLE_KERBS:
            # Extract geometry while converting to UTM coordinates
            x, y = utm.from_latlon(d["geometry"].y, d["geometry"].x)[:2]
            kerbs.append(pygeos.points([x, y]))
    sindex = pygeos.STRtree(kerbs)

    # For each crossing, query start and end nodes for proximity to a curb ramp
    # node. If at least one side is close enough to a curb ramp, mark as having
    # curb ramps. This *should* be safe given that crossings get split at
    # street centerlines.
    # FIXME: guarantee this by checking the non-street-intersecting end node.
    for u, v, d in OG.G.edges(data=True):
        if progressbar is not None:
            progressbar.update(1)
        if _is_crossing(d):
            start = d["geometry"].coords[0]
            end = d["geometry"].coords[-1]
            d["curbramps"] = int(near_curbramp((start, end), sindex, distance))
