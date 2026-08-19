# -*- coding: utf-8 -*-
"""Standalone check for DB.closest_point_of_coastline / DB.create_transect_in_coast.

Connects to a PostGIS host (given on the command line, other credentials taken
from configuration.txt unless overridden) and verifies that the generated
transect has the expected length in meters, to catch the "world-scale
coordinate" bug where ST_Project was applied without a geography cast.

Usage (run from the repository root, since db_utils.py imports via the
`processes` package):
    python -m processes.test_cloasestpoint --host c-oet18499.directory.intra
    python -m processes.test_cloasestpoint --host localhost --lon 1.570195 --lat 6.221786 --dist 500
    python -m processes.test_cloasestpoint --host localhost --point '{"type": "Point", "coordinates": [1.570195, 6.221786]}'
"""

import argparse
import sys
from pathlib import Path

import geojson
from pyproj import Geod

from .db_utils import DB
from .utils import read_config
from .vector_utils import geojson_to_wkt, wkt_geometry


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", required=True, help="PostGIS host to connect to")
    parser.add_argument("--user", default=None, help="Defaults to configuration.txt")
    parser.add_argument("--password", default=None, help="Defaults to configuration.txt")
    parser.add_argument("--db", default=None, help="Defaults to configuration.txt")
    parser.add_argument(
        "--point",
        default=None,
        help="Sea point as a GeoJSON Point string, e.g. '{\"type\": \"Point\", \"coordinates\": [lon, lat]}'. "
        "Overrides --lon/--lat.",
    )
    parser.add_argument("--lon", type=float, default=1.570195, help="Sea point longitude")
    parser.add_argument("--lat", type=float, default=6.221786, help="Sea point latitude")
    parser.add_argument("--dist", type=float, default=500, help="Transect distance in meters")
    parser.add_argument("--crs", type=int, default=4326)
    return parser.parse_args()


def main():
    args = parse_args()

    cfg_host, cfg_user, cfg_password, cfg_db, *_ = read_config(
        str(Path(__file__).with_name("configuration.txt"))
    )
    user = args.user or cfg_user
    password = args.password or cfg_password
    db_name = args.db or cfg_db

    print(f"Connecting to host={args.host!r} db={db_name!r} user={user!r} ...")
    db = DB(user, password, args.host, db_name)

    if args.point:
        sea_point_geojson = geojson.loads(args.point)
        sea_point_wkt = geojson_to_wkt(sea_point_geojson)
    else:
        sea_point_wkt = f"POINT({args.lon} {args.lat})"
    print(f"Sea point: {sea_point_wkt}")

    coastline_point, coastline_id = db.closest_point_of_coastline(sea_point_wkt, args.crs)
    print(f"Closest coastline point: {coastline_point} (coastline_id={coastline_id})")

    transect_wkt = db.create_transect_in_coast(sea_point_wkt, coastline_point, args.dist, args.crs)
    print(f"Transect: {transect_wkt}")

    coords = wkt_geometry(transect_wkt)["coordinates"]
    print(f"Transect coordinates: {coords}")

    geod = Geod(ellps="WGS84")
    (start_lon, start_lat), (end_lon, end_lat) = coords[0], coords[-1]
    _, _, measured_dist = geod.inv(start_lon, start_lat, end_lon, end_lat)
    print(f"Measured transect length: {measured_dist:.2f} m (expected ~{args.dist} m)")

    db.close_db_connection()

    if abs(measured_dist - args.dist) > args.dist * 0.05:
        print("FAIL: transect length deviates more than 5% from the requested distance.")
        sys.exit(1)

    print("OK: transect length matches the requested distance.")


if __name__ == "__main__":
    main()
