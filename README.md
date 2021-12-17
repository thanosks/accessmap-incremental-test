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

## Creating Audit-Annotated OpenSidewalks Data

This repo is derived from the
[AccessMap deployment workflow](https://github.com/accessmap/accessmap), with
three big differences:

1. It includes a full bottom-up data pipeline using OpenStreetMap and public
DEM datasets. The main `accessmap` deployment workflow assumes you can bring
your own OpenSidewalks-format `transportation.geojson` file, whereas this
repo does not.

2. You must define a `config.geojson` file to configure the data process. This
file is identical to the `regions.geojson` file expected by AccessMap, except
now each region include information on where to retrieve its OpenStreetMap
data. This repo hardcodes the current, live config file at
`input/config.geojson` and you can use it as an example.

3. This repo also supports an "audit" annotation pipeline based on
OpenStreetMap Tasking Manager task exports (on a tasking manager, enable expert
mode for your account, go to a project page, scroll to the bottom and export
the ask grid). Namely, it expects you to populate a sidewalks tasks and a
crossings tasks input folders with such exports. Any OpenSidewalks data that
intersects completed tasks will be marked as audited. The output of this step
is used as the `transportation.geojson` used to drive the AccessMap web
application.

### Creating OpenSidewalks data from OpenStreetMap

This is a simple, two-step process: (1) edit `input/config.geojson` to your
preferences and (2) run `docker-compose up data_osm_osw`. This process uses the
`osm_osw` package defined in this repo.

#### `config.geojson`

This configuration file is a GeoJSON FeatureCollection, which is essentially
just an annotated list of (Multi)Polygon shapes representing an area intended
to be extracted from OpenStreetMap and turned into routable OpenSidewalks data.
An example is already present in `input/config.geojson`. Each "Feature" will
have a polygon describing the area covered and a set of properties, all of
which must be defined:

- `id`: A unique identifier string for this region. It can be anything so long
as it is unique, it is only used internally. We typically use `country.city`
or something along those lines.

- `name`: The human-readable name for this region, it will appear in the
AccessMap web application.

- `lon`, `lat`, and `zoom`: The coordinates and map zoom level for a canonical
"view" of the city. This will determine the initial view of this region within
AccessMap when someone selects this region.

- `extract_url`: A URL to a `.osm.pbf` file that includes this region. It will
be fetched automatically and used to extract path information.

#### Running the data process

### Fetching and extracting data into an OpenSidewalks Schema-compatible
### GeoJSON

In the main directory of this repo, run:

    docker-compose up data_osm_osw

### Annotating with audit information

AccessMap incremental's primary value-add is the ability to distinguish
between areas that have been audited for pedestrian network data and those
that have not, then allowing website visitors to set parameters based on these
data (uncertainty, safety, confidence, etc). Whether a network element has
been audited falls under the data process included in this repo, but it is
a separate one from the initial OpenSidewalks data process and uses a package
called `incremental` defined in this repo.

The `incremental` process is similarly two-step: (1) Put tasking manager
task grid exports into `input/tasks/crossings_tasks` and
`input/tasks/sidewalks_tasks` and (2) run `docker-compose up data_incremental`.

This will create `output/transportation-tasks.geojson`, which is a version of
the `transportation.geojson` file created in the OpenSidewalks data process
that has been enriched with two new properties: `crossings_mapped` and
`sidewalks_mapped`. All network elements will have this property, set to either
0 (not audited) or 1 (audited). This file is expected by the next steps of
building assets and running the application.

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
