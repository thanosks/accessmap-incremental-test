#!/bin/bash

# First argument should be a path to the docker-compose file

set -e

docker-compose -f ${1} run --rm data_osm_osw
docker-compose -f ${1} run --rm data_incremental
docker-compose -f ${1} run --rm build_router & docker-compose -f ${1} run --rm build_tiles
