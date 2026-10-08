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

## Local setup

The Conda environment is defined in `environment.yml`. Create and activate it with:

```bash
conda env create -f environment.yml
conda activate chw3
```

The CHW processes depend on external PostGIS and GeoServer services. Before starting the service, provide `processes/configuration.txt` with the connection and layer settings read by `processes/utils.py`:

- `[PostGIS]`: `host`, `user`, `pass`, `db`, and `port`
- `[GeoServer]`: `ows_url`, `dem`, `landuse`, `username`, `password`, and `dem_test`

The values must point to services and datasets available to your installation. Keep credentials out of version control. The configuration file is not included in this repository. The CHW process also writes temporary raster data below `processes/outputs`; create that directory if it is not already present.

Start the local development server from the repository root:

```bash
python pywps.wsgi
```

By default it listens on `http://127.0.0.1:5000`. The optional `--all-addresses` flag binds to all network interfaces. This Flask server is intended for local testing, not production deployment.

## WPS endpoint and requests

The WPS endpoint is `http://localhost:5000/wps` (or the URL configured in `pywps.cfg`). The root URL, `http://localhost:5000/`, provides a service overview. Use these OGC WPS 1.0.0 requests to inspect the running service:

- Capabilities: `http://localhost:5000/wps?service=WPS&request=GetCapabilities&version=1.0.0`
- All process descriptions: `http://localhost:5000/wps?service=WPS&request=DescribeProcess&version=1.0.0&identifier=all`

Execute requests are sent to `/wps` using WPS 1.0.0. GeoJSON coordinates are longitude/latitude in EPSG:4326. The main workflow is:

1. Call `create_transect` with a GeoJSON `Feature` containing a sea-point `Point` as `sea_point`.
2. Use the returned `transect_coordinates` to make a GeoJSON `Feature` containing a `LineString`, and include the returned `notification` value in `properties.notification`.
3. Call `chw_risk_classification` with that feature as `transect`.

Both processes return JSON in the `output_json` output. Classification results contain hazard, risk, and measure sections; failures may be returned as a JSON object with an `errMsg` field. The transect process also requires a working PostGIS connection and coastline data.

## Registered processes

The following process identifiers are registered by `pywps.wsgi`:

| Identifier | Input | Purpose |
| --- | --- | --- |
| `create_transect` | `sea_point` (GeoJSON Point) | Finds the nearest coastline and creates an inland transect. |
| `chw_risk_classification` | `transect` (GeoJSON LineString Feature) | Runs the main Coastal Hazard Wheel classification and returns hazards, risk information, and measures. |
| `chw_risk_classification_test` | `transect` (GeoJSON LineString Feature) | Classification using the test data configuration. |
| `chw_risk_classification_test_environment` | `transect` (GeoJSON LineString Feature) | Classification using the test-environment implementation. |
| `chw_risk_classification_fabdem_test_environment` | `transect` (GeoJSON LineString Feature) | Classification test process for the FABDEM environment. |
| `ultimate_question` | None | Returns the string answer `42`. |

The XML files in `templates/` are examples from an earlier process version. Their process and input identifiers do not match the current registrations; use the identifiers and input names above, or inspect the live process description before constructing an Execute request.
