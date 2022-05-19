#!/bin/bash

# First argument should be a path to the docker-compose file

set -e

docker-compose run --rm data_osm_osw
docker-compose run --rm data_incremental
docker-compose run --rm build_router & docker-compose run --rm build_tiles
