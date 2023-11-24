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

### Before doing anything else

Clone this repo! Run:

    git clone https://github.com/accessmap/accessmap-incremental

Then
    cd accessmap-incremental

All of the instructions below assume you're running commands in the
`accessmap-incremental` directory.

### Creating OpenSidewalks data from OpenStreetMap

This is a simple, three-step process: (1) `create accessmap-incremental.env`,
(2) edit `input/config.geojson` to your preferences (3) run
`docker-compose up data_fetch` to fetch the source data and (4)
`docker-compose up data_osm_osw` to build the data. This process uses the
`osm_osw` package defined in this repo.

#### `accessmap-incremental.env`

`docker-compose` needs to find settings in a file named
`accessmap-incremental.env` in the same directory as the `docker-compose.yml`
file. This repository provides a sample file to get you started quickly, and
only one change to it is required in order to run the data process. To use this
sample file, run:

    cp accessmap-incremental.env.sample accessmap-incremental.env

(Or just create a copy with your file manager and rename it)

The one change required is to set the `MAPBOX_TOKEN` environment variable to
a valid Mapbox token id.

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

To fetch the source data, run this in the main directory of this repo:

    docker-compose up data_fetch

To build/process the data into an OpenSidewalks-compatible format, run this in
the main directory of this repo:

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

After creating the `transportation-tasks.geojson` file produced in the data
process, run:

    docker-compose --profile build up

This will prepare all the assets for the next stages.

#### 3. Running the web application

After building the assets, simply run:

    docker-compose up

## Maintaining / updating a deployment

### `rebuild.sh`

This repository includes a simple bash script that, when run, will
automatically:
1. Fetch fresh OpenStreetMap and tasking manager data
2. Rebuild all data via existing pipelines
3. Rebuild all relevant `docker-compose` services (the router, the React
front end, etc).
4. Re-deploy all relevant `docker-compose` services (the router, the React
front end, and the Caddy reverse proxy).

The current main deployment of `accessmap-incremental` runs this script at
2 AM every day via a cron job.

### Updating

`accessmap-incremental` is developed from an open source, public git repository
and will be updated from time to time. If you want to pull the latest changes,
you can use git directly via `git pull origin main`.

If you know what services do and don't need to be updated, you can of course
run your own `docker-compose` commands to rebuild and redeploy them. But in
general, after pulling a new version of `accessmap-incremental` you may run
these commands to ensure a complete update:
1. `docker-compose build --profile data --no-cache`
2. `docker-compose build --profile build --no-cache`
3. `docker-compose build --no-cache`
4. `docker-compose down --profile data && docker-compose up -d --profile data`
5. `docker-compose down --profile build && docker-compose up -d --profile build`
5. `docker-compose down && docker-compose up -d`

## Rebuilding the router

There are circumstances in which you want to redeploy the router. To be sure
that it's fully redeployed, run:

    docker-compose up build_router

And then

    docker-compose up -d router

## Editing the cost function

There are two contexts in which you might want to edit the cost function:

* When developing a new one and you need rapid feedback.

* When you have a clear cost function developed and want it to be used in
future deployments.

For the rapid feedback mode, edit `build/router/cost-*.py`, where the `.py`
file is a given cost function. Restarting the router container
(`docker-compose stop router && docker-compose rm -f router && docker-compose up -d router`)
will load the changes. However, the `build` directory is overwritten on future
deployments, so once you like how the cost function looks, copy it to the
`config/unweaver` directory. Keep a close look at permissions - the `build`
directory might be owned by a root user and you'll need to change permissions,
e.g. `chown youruser:youruser config/router/cost-*.py`.

## Running a local development environment

The local development environment shares nearly all of the same steps as for
the production environment. The only real changes are to use a different
"cascading" docker-compose YAML file. In production, you must also apply the
production settings by cascading `docker-compose.prod.yml` on top of the
default `docker-compose.yml` file whenever calling `docker-compose`. For
example, to run the servers during the final step, you need to run
`docker-compose -f docker-compose.yml -f docker-compose.prod.yml up`.

During local development, you'll cascade a `docker-compose.override.yml` file
instead of a `docker-compose.prod.yml` file. Once it is present, this
"override" YAML will be automatically recognized by `docker-compose`, so to
run the servers in the final step, you will only need to write
`docker-compose up`.

To set up the development environment, you'll need to make changes to two
files. First, you will need to edit the `accessmap-incrementa.env` file, which holds environment variables
for confguring the app, to use settings safe for local development. Then you
will need to create a `docker-compose.override.yml` that will hold
settings specific to how the services should run, mostly just opening ports.

### Modifying the `accessmap-incremental.env` file for local development

You will want to change the following settings for local development:

- `HOST`: Change the value to be `http://localhost:2015`, which is where the
reverse proxy will be running locally.

- `TLS`: Change the value to be "off", indicating that you will not be using
a secure TLS connection for local requests. There will be no external requests
to the services, so this is not a significant security concern.

- `ANALYTICS`: You should usually set this to "no" during development unless
you want to specifically debug a new analytics project.

- `SECRET_KEY`: Use a different value during development.

- `JWT_SECRET_KEY`: Use a different value during development.

- `OSM_URI`: Set this to `https://master.apis.dev.openstreetmap.org/` if it
isn't already set to this. This is the dev server for OpenStreetMap, where it
is safe to authenticate and make changes without impacting the main OSM db.
You will need to create an account and OAuth1.0a credentials at this endpoint,
as OpenStreetMap does not copy users to its dev server.

- `OSM_CLIENT_SECRET`: This will be an OAuth1.0a secret for the OSM dev server.

- `OSM_CONSUMER_CALLBACK_URI`: Set this to
`http://localhost:2015/login_callback`.

- `SQLALCHEMY_DATABASE_URL`: Set this to `sqlite:////tmp/accessmap-api.db`, or
to any SQLite URI for the path where you'd like to store the `API` database
during development.

### Set up docker-compose

Copy the `docker-compose.override.yml.example` to
`docker-compose.override.yml`.

Once copied, running `docker-compose` commands will automatically cascade the
`docker-compose.yml` and `docker-compose.override.yml` files, opening up ports
for each service. Here is a list of the services that can be reached after
running `docker-compose up`:

- The web app can be reached at `localhost:2015`.

- The API server will be at both `localhost:5000` and `localhost:2015/api/v1`.

- The routing server will be at both `localhost:5656` and
`localhost:2015/api/routing`.

- The tile server will be at `localhost:2015/tiles`.

- The public regions GeoJSON file will be at
`localhost:2015/api/regions/regions.geojson`. Some versions of the React
app (used for the AccessMap front end) will require you to download this file
and put it in the root directory of the web application. Some newer versions
will expect to find it relative to the root of the API endpoint.
