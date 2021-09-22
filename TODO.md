## Add ASTER fallback for global DEMs

While the ASTER DEM dataset has about 10X worse resolution (30 m instead of
10 m), it has global(ish) coverage. We should see how far we can get with this
dataset when better DEMs are unavailable.

## Add custom DEMs, particularly for Santiago

Users (like us) may wish to supply their own DEM data. For example, we want to
support elevation estimation in Santiago using the only high-resolution
data source we've been able to find, which is in point cloud data format. We
will need to process this on our side to create a DEM. Rather than forcing us
to then republish it at a URL, we should also allow the use of a local DEM.

The dataset is on opentopography
