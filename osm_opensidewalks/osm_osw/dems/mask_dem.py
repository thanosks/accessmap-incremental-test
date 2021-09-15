import json

import osmium
from osmium.geom import GeoJSONFactory
import rasterio
from shapely.geometry import Point, shape


class BuildingCounter(osmium.SimpleHandler):
    def __init__(self):
        super().__init__()
        self.count = 0

    def area(self, a):
        if "building" in a.tags:
            self.count += 1


class BuildingHandler(osmium.SimpleHandler):
    def __init__(self, progressbar=None):
        super().__init__()
        self.buildings = []
        self.geojson_factory = GeoJSONFactory()
        self.progressbar = progressbar

    def area(self, a):
        if "building" in a.tags:
            geojson = self.geojson_factory.create_multipolygon(a)
            geojson_geom = json.loads(geojson)
            self.buildings.append(geojson_geom)
            if self.progressbar is not None:
                self.progressbar.update(1)


def count_buildings(path):
    """Count the number of buildings in an OSM PBF file.

    :param path: Path to the .osm.pbf
    :type path: str

    """
    # FIXME: include bridges and other features, rename to reflect this.
    building_counter = BuildingCounter()
    building_counter.apply_file(str(path))

    return building_counter.count


def extract_buildings(path, progressbar=None):
    """Extract (multi)polygons of buildings from an OSM PBF file.

    :param path: Path to the .osm.pbf file.
    :type path: str
    :param progressbar: An (optional) click.progressbar object that will be
                        updated as buildings are extracted.
    :type progressbar: click.progressbar

    """
    # FIXME: include bridges and other features, rename to reflect this.
    building_handler = BuildingHandler(progressbar=progressbar)
    building_handler.apply_file(str(path))

    return building_handler.buildings


def mask_dem(dem_path, polygons, progressbar=False):
    """Insert a nodata mask into a DEM based on attributes of an OSM PBF file,
    namely masking out pixels near buildings and bridges.

    :param dem_path: Path to a DEM raster.
    :type dem_path: str
    :param polygons: Iterable of GeoJSON (multi)polygon geometries.
    :type polygons: Iterable of GeoJSON (multi)polygon geometries (dict).

    """
    with rasterio.open(dem_path, "r+") as rast:
        rast.write_mask(True)
        for polygon in polygons:
            mask_polygon(polygon, rast)
            if progressbar is not None:
                progressbar.update(1)


def to_raster_coords(geometry, raster):
    affine = ~raster.transform
    polygons = []
    for polygon in geometry["coordinates"]:
        new_polygon = []
        for ring in polygon:
            new_ring = []
            for coord in ring:
                x, y = affine * (coord[0], coord[1])
                new_ring.append([x, y])
            new_polygon.append(new_ring)
        polygons.append(new_polygon)

    new_geometry = {"type": "MultiPolygon", "coordinates": polygons}

    return new_geometry


def mask_polygon(polygon, raster):
    raster_coord_geojson = to_raster_coords(polygon, raster)
    geom = shape(raster_coord_geojson)
    bounds = geom.bounds
    minx = int(bounds[0])
    miny = int(bounds[1])
    maxx = int(bounds[2]) + 1
    maxy = int(bounds[3]) + 1

    if minx < 0 or miny < 0 or maxx > raster.width or maxy > raster.height:
        # Geometry falls outside of raster extent: do nothing
        return

    # Geometry bounds fall within raster extent, but could overlap boundary:
    # adjust window to be within boundary
    minx = max(0, minx)
    miny = max(0, miny)
    maxx = min(raster.width, maxx)
    maxy = min(raster.height, maxy)

    # Create windowed read indices
    dx = maxx - minx
    dy = maxy - miny

    # Object at boundary may not overlap properly - throw out
    if not dx or not dy:
        return

    # mask = np.ones((dy, dx)).astype(bool)
    xs = [p + 0.5 for p in range(minx, maxx)]
    ys = [p + 0.5 for p in range(miny, maxy)]

    window = rasterio.windows.Window(minx, miny, dx, dy)

    mask = raster.read_masks(indexes=1, window=window)

    for i, y in enumerate(ys):
        for j, x in enumerate(xs):
            point = Point(x, y)
            if geom.distance(point) == 0:
                mask[i, j] = False

    raster.write_mask(mask, window=rasterio.windows.Window(minx, miny, dx, dy))
