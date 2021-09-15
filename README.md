# AccessMap Incremental

*Please note that this project is a tech demo and reproducing its functionality
is difficult at this time*.

AccessMap Incremental is an experimental project to provide useful pedestrian
trip planning in situations where pedestrian network data is missing for one of
two (common) reasons:

1. Nobody has audited an area for whether dedicated pedestrian network elements
exist. For example, a city that has a lot of sidewalks but they have not yet
been added to any map.

2. Certain dedicated pedestrian network elements do not exist and pedestrians
need "backup" options. For example, a suburban area may have been constructed
on the premise that the primary mode of transportation will be single occupancy
vehicles starting and ending at detached housing.

There are also scenarios in which the primary pedestrian network includes the
street network and is shared with vehicles. The current version of AccessMap
does not model this situation well, but this project will attempt to so that
AccessMap can be deployed for a wider cultural and policy context.

## Architecture and Running the Application

This project has been cobbled together from a few codebases in order to rapidly
produce a tech demo. This should not be considered a particularly maintainable
strategy. This section described how it is built in case an unlucky someone
does need to work off of this codebase.

AccessMap incremental is a web application that functions essentially
identically to AccessMap: a series of microservices serving up web APIS and a
single page React application. In addition, the data process has been embedded
into this repository, as special elements need to be tied together in order for
AccessMap Incremental to function - namely, the pedestrian network needs to be
spatially joined with a set of "audit" polygons that indicate whether an area
has been audited for pedestrian network elements.

### Deploying the Web Application

Deployment of the web application is nearly identical to a standard deployment
of AccessMap: it is managed by a two-step `docker-compose` workflow that
first builds data assets (network elements into a database, vector tiles, web
front end) and then runs the microservices and a reverse proxy that ties
everything  together.

#### 1. Configuring the system

This project is configured through the `accessmap-incremental.env` file. Modify
the settings there to the current deployment. Use `HOST=localhost` and
`TLS=tls off` for a local deployment.

#### 2. Building the assets

After placing the `transportation.geojson` file produced in the next section
(Data Process) into the `data` directory, simply run:

    docker-compose -f docker-compose.build.yml up

This will prepare all the assets for the next stages.

#### 3. Running the web application

After building the assets, simply run:

    docker-compose up

### Data Process

Like AccessMap, this project expects you to input a `transportation.geojson`
file. This file holds an edge list description of the pedestrian network in
the OpenSidewalks Schema format that has been "upgraded" with metadata about
whether a given network element is within an "audited" region or not. For
example, a sidewalk element in an area that is not known to be audited for
sidewalks yet will have the property, "sidewalk_audit=0". Even though someone
has mapped a sidewalk in this area at some point, we cannot assume that it has
been accurately connected to other elements until some auditing process has
occurred (even just one person giving the area a once-over). Therefore, this
sidewalk may be considered "de-prioritized" when interpreted by AccessMap
Incremental: the street network is, by default, treated as a high-ranking
alternative to a non-audited sidewalk network.

The AccessMap Incremental codebase includes the full data process code used to
create this tech demo under `accessmap_incremental_data_process`. The process
reads in three sources of input data and outputs a `transportation.geojson`
file that powers the web application. The data sources are:

1. An OpenStreetMap extract in `.osm.pbf` format.

2. Pedestrian network auditing polygons, by default extracted from an OSM
Tasking Manager API.

3. (optional) DEM data for inferring sidewalk inclines.

#### 1. Configuration

The only configuration for this process is in credentials for accessing the
Tasking Manager API. Everything else has been hard-coded and will break for
anything other than the specific Tasking Manager instance and projects for
which it has been designed.

Set `TASKING_MANAGER_API_KEY` to an API key that has read access on all
projects in `accessmap_incremental_data_process.env`.

#### 2. Import data into an OpenStreetMap instance

*Note: you may want to clip the `.osm.pbf` file to a smaller extent using a
tool like `osmium` first.*

The data process is awkward and first reads the `.osm.pbf` data into a
self-hosted instance of OpenStreetMap. This is in no way necessary,
theoretically, and is a holdover from a different project.

Place your `.osm.pbf` into the `osm_files` directory and run:

    docker-compose up openstreetmap_import

This will set up an instance of the OpenStreetMap website, create an admin
account, and load data into that website. The data will be stored in a
postgresql database (`osmdb`), serialized to the `pgdata` directory.

#### 3. Build the pedestrian network in-db

The next step of the build process is to transform the local OSM database
tables into an OpenSidewalks schema edge list:

    docker-compose up transform_osm

#### 4. (Optional) estimate inclines

Not all regions may have DEM data of high enough resolution for this step, so
it is left as optional. DEM data should be of at least 30-meter resolution.

Place any such data, in geotiff format, into `dem_files` and run:

    docker-compose up import_dems

This will read the DEMs into the main database in which the edge list has been
stored.

To estimate the inclines wherever DEM data and edge list data overlap, run:

    docker-compose up estimate_inclines

#### 5. Fetch audit polygon data

There are two "types" of audit polygons tracked for this project and both
result in the creation of a boolean property added to network elements stating
whether they have been audited. We acknowledge that the time of the last
audit, audit type, etc are all important aspects for properly modeling this
challenge, even though we do not yet incorporate them.

The first is for an audit of "crossings", which means the basic pedestrian
network elements describing street crossings at street intersections: whether a
crossing location has ground marking likes a crosswalk, what the curb interface
is when entering/leaving the street environment, and the small path that
connects this crossing to the center of the sidewalk. Whether a pedestrian
network element (broadly defined to include roads) overlaps with a crosswalk
"task" area will result in setting a network element attribute key named
"crossing_audit" to either 1 (True - this area was audited for crossings) or
0 (False - this area has not yet been audited for crossings).

The second is for an audit of "sidewalks", which is simply whether an area has
been audited for the presence of sidewalks and, where present, they have been
mapped as centerlines. This produces a "sidewalks_audit" property for network
elements that is set to either 1 (True - this are has been audited for
sidewalks) or 0 (False - this area has not been audited for sidewalks).

The first step of this process is to fetch audit polygon data from a tasking
manager instances' projects, which can be done with:

    docker-compose up fetch_task_polygons

This will create two GeoJSON files of polygons in `task_data`:

    1. `crossing_audit.geojson`

    2. `sidewalks_audit.geojson`


#### 6. Output the annotated pedestrian network

This process will label the in-db edge list with the audit properties described
in the last section and then create a `transportation.geojson` file in the
`output` directory:

    docker-compose up annotate_and_output

This file can then be used in the previous main section to run AccessMap
Incremental.


This workflow is relatively laborious and is not expected to be run with any
frequency: it has been designed only for a tech demo.
