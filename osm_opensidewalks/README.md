# `osm_osw`

## Installation

`osm_osw` requires these external tools:

- `osmium`, package name `osmium-tool` on Debian/Ubuntu. This provides
performant Python adapters for stream-processing of .osm.pbf files.

- `osmosis`, package name `osmosis` on Debian/Ubuntu. This provides low-memory
operations on .osm.pbf files and is used in `osm_osw` for parallel extraction
of subregions from .osm.pbf files.

## Commands and configuration

`osm_osw` makes heavy use of a working directory that contains fetched vector
data (including OpenStreetMap extracts), fetched DEMs, and some of the
"intermediate" data artifacts produced during the data processing pipeline.
This working directory defaults to `/tmp/osm_osw` but can be set for each
command using either the `OSM_OSW_WORKDIR=/path/to/dir` environment variable or
the `--workdir=/path/to-dir` option.
