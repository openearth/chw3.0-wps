# chw3.0-wps

## introduction
CHW3.0-wps is the 3rd version of WPS for the CHW - Coastal Hazard Wheel project. The CHW is basically a decision tree. More information see [Coastalhazardwheel.org](https://coastalhazardwheel.org/). The initial request was to apply the methodogy of the CHW for the Colombian coast based on available data, somewhere in 2016. While searching for available data most of the available sources were global data sources. Since the method was applied via Python scripts it was decided to spend some research budget to apply it for the whole world.
Since 2021 there is a new version of the CHW application with an updated set of data, procedures and appliying the 4th version of the CHW methodology

## Data
CHW3.0-wps and the [platform](https://chw-app.coastalhazardwheel.org/) use global open data sources that are served via OGC services.

## Processes
Via the [platform](https://chw-app.coastalhazardwheel.org/) users can click nearby a coast which triggers following actions:
1. The closest shoreline (base on OpenStreetMap Coastline layer) is searched within a radius of 0.1 degree
2. The closes point on the shoreline is used to make a perpendicular transect on the coast
3. For this transect various datasets are sampled over the transect and indicators (slope, majority landuse, wave height etc.) are derived
4. The indicators are used to retrieve a coastal classification code
5. With the coastal classification end users get insigth in challenges on the selected part of the coast, including number of people and level of assets exposed to one of the hazards

# WPS processes
The WPS implemented in this application is based on PyWPS4.2.8.
