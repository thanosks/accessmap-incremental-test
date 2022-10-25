#!/bin/bash

set -e

docker-compose run --rm data_osm_osw
docker-compose run --rm data_incremental
docker-compose run --rm build_router & docker-compose run --rm build_tiles
docker-compose run --rm build_webapp
docker-compose restart caddy
