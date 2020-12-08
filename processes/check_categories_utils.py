# -*- coding: utf-8 -*-
# Copyright notice
#   --------------------------------------------------------------------
#   Copyright (C) 2020 Deltares
#       Gerrit Hendriksen, Ioanna Micha
#
#       gerrit.hendriksen@deltares.nl, ioanna.micha@deltares.nl
#
#   This library is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This library is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this library.  If not, see <http://www.gnu.org/licenses/>.
#   --------------------------------------------------------------------
#
# This tool is part of <a href="http://www.OpenEarth.eu">OpenEarthTools</a>.
# OpenEarthTools is an online collaboration to share and manage data and
# programming tools in an open source, version controlled environment.
# Sign up to recieve regular updates of this function, and to contribute
# your own tools.
# Date: 10-2020
# Abstract: CHW classification according to:
#               6 steps of check
#               Geological layout (Result of either, sediment_plain, sloping soft rock, flat hard rock, sloping hard rock, barrier, corals, "havent checked for that" )
#               Wave exposure
#               Tidal range
#               Flora/Fauna
#               Sediment balance
#               Storm climate
# Extra info: https://www.coastalhazardwheel.org/
from pathlib import Path
from typing import Any, List
import numpy as np
from .db_utils import (
    get_geol_glim_values,
    get_wave_exposure_value,
    intersect_with_corals,
    intersect_with_estuaries,
    intersect_with_mangroves,
    intersect_with_saltmarshes,
    get_tidal_range_values,
)
from .raster_utils import (
    calc_slope,
    cut_wcs,
    get_elevation_profile,
    detect_sea_patterns,
    read_raster_values,
)
from .utils import create_temp_dir, read_config
from .vector_utils import change_coords, geojson_to_wkt, get_bounds

service_path = Path(__file__).resolve().parent
output_dir = create_temp_dir(service_path / "outputs")

output = {
    "coastenv": "BA-24",
    "erosion": "1 (low)",
    "landcover": "any",
    "roads": "0 meters",
    "barrier_islands": "",
    "surge_levels": "",
    "rivermouths": "",
    "risk": [[0.6922, 88.046]],
    "capital_stock": "Usd. 692.200,-",
    "population": "88 inhabitants",
    "gar_distance": "no data",
    "code": "BA-24",
    "breakwaters": "",
    "groynes": "null",
    "jetties": "null",
    "revetments": "null",
    "seawalls": "null",
    "dikes": "null",
    "stormsurgebarriers": "null",
    "beachnourishment": "null",
    "duneconstab": "null",
    "cliffstab": "null",
    "wetlandrest": "V",
    "floodwarning": "null",
    "floodproofing": "null",
    "coastalzoning": "null",
    "groundwatermgmt": "null",
    "fluvsedmgmt": "V",
    "riskindication": "Low",
}


def check_geological_layout(transect):
    """ check geological layout"""
    # TODO check correct order of checks
    if check_barrier(transect):
        geological_layout = "Barrier"
        return geological_layout

    elif intersect_with_estuaries(transect):
        geological_layout = "Delta/ low estuary island"
        return geological_layout

    elif intersect_with_corals(transect):
        geological_layout = "Coral island"
        return geological_layout

    else:
        geological_layout = check_geology_type(transect)
        return geological_layout

    return geological_layout


def check_geology_type(transect: dict) -> List[bool]:
    """Calculates the slope and gets the glim value of the transect
    from geollayout.glim. Checks if: sediment plain
                                     sloping soft rock
                                     flat hard rock
                                     sloping hard rock
    Args:
        transect ([type]): [description]

    Returns:
        List: [Booleans]
    """

    # 1. Get geology(su or !su) from database
    geology_values = get_geol_glim_values(transect)
    non_su_values = sum(x != ("su",) for x in geology_values)
    su_values = sum(x == ("su",) for x in geology_values)
    if su_values >= non_su_values:
        geology = "su"
    else:
        geology = ""

    # 3. Get elevation profile
    ## NOTE I have already cut and reprojected the dem in barrier
    ## TODO improve it
    # transect_projected = change_coords(transect)
    # transect_length = transect_projected.length
    dem = Path(output_dir) / "dem.tif"
    dem_reprojected = Path(output_dir) / "dem_reprojected.tif"
    transect_projected = change_coords(transect)
    transect_length = transect_projected.length
    elevations, segments = get_elevation_profile(
        dem, transect_projected, transect_length, dem_reprojected
    )

    # 3  Calculate slope
    slope = calc_slope(elevations, segments)
    output.update({"slope": slope})

    if geology == "su" and slope <= 1.6:
        return "Sediment plain"
    elif geology == "su" and slope > 1.6:
        return "Sloping soft rock"
    elif geology != "su" and slope <= 1.6:
        return "Flat hard rock"
    else:
        return "Sloping hard rock"


def check_barrier(transect) -> bool:
    """get_elevation function, do some magic and get if barrier is there or not

    Args:
        transect ([type]): [description]

    Returns:
        bool: [description]
    """
    transect_wkt = geojson_to_wkt(transect)
    # 2. Get coverage
    _, _, _, _, _, owsurl, layername, _ = read_config()
    bbox = get_bounds(transect_wkt)
    dem = Path(output_dir) / "dem.tif"
    cut_wcs(*bbox, layername, owsurl, dem)

    # 3. Get elevation profile
    transect_projected = change_coords(transect)
    transect_length = transect_projected.length
    dem_reprojected = Path(output_dir) / "dem_reprojected.tif"

    elevations, segments = get_elevation_profile(
        dem, transect_projected, transect_length, dem_reprojected
    )
    print("barrier check", elevations)
    sea_pattern = detect_sea_patterns(elevations)
    changes = np.count_nonzero(sea_pattern == True)
    print("changes", changes)
    if changes > 1:
        barrier = True
    else:
        barrier = False
    print(barrier, sea_pattern, sea_pattern.shape, "barrier")
    return barrier


def check_flora_fauna(transect) -> List:
    """
    For the cases of:
    sediment_plain, Barrier, Delta_low estuary
    """
    if intersect_with_mangroves(transect):
        flora_fauna = "mangroves"
    elif intersect_with_saltmarshes(transect):
        flora_fauna = "marsh"
    else:
        flora_fauna = "Any"
    return flora_fauna


def check_flora_fauna_sl_soft_rock(transect) -> Any:
    """check the values of the globcover
    globcover>=190 & <=220: not vegetated
    globcover>=20 & <=150: vegatated
    Any
    Returns:
        [type]: [description]
    """
    # 2. Get coverage
    transect_wkt = geojson_to_wkt(transect)
    _, _, _, _, _, owsurl, _, layername = read_config()
    bbox = get_bounds(transect_wkt)
    globcover = Path(output_dir) / "globcover.tif"
    cut_wcs(*bbox, layername, owsurl, globcover)
    values = read_raster_values(globcover)
    non_vegetated = np.count_nonzero(values >= 190 and values <= 220)
    vegetated = np.count_nonzero(values >= 20 and values <= 150)
    if vegetated >= non_vegetated:
        return "Vegetated"
    else:
        return "Not vegetated"


def check_flora_fauna_hard_rock(transect) -> List:
    """Intersects with vegetation.corals: Corals
    Returns:
        List: [description]
    """
    if intersect_with_corals(transect):
        return "corals"
    elif intersect_with_mangroves(transect):
        return "mangroves"
    else:
        return "any"


def check_flora_fauna_sl_hard_rock(transect) -> List:
    """Intersects with vegetation.corals: Corals
    Returns:
        List: [description]
    """

    if intersect_with_corals(transect):
        return "corals"
    else:
        return "any"


def check_sediment_balance():
    """database data"""
    pass


def check_storm_climate() -> bool:
    """chech if instersects with cyclone data"""
    return storm_climate


def coastal_hazard_wheel(transect):
    """fill in the values of each category according to the coastal hazard wheel
    There are six categories. Not all the categories needs to be checked according to the case.
    The first category always needs to be ckecked.
    1st point check: Geological layout
    2nd check: Wave exposure
    3rd check: Tidal range
    4th check: Flora_Fauna
    5th check: Sediment balance
    6h check: Storm climate
    """
    geological_layout = check_geological_layout(transect)
    wave_exposure = get_wave_exposure_value(transect)
    tidal_range = get_tidal_range_values(transect)

    if (
        geological_layout == "Sediment plain"
        or geological_layout == "Barrier"
        or geological_layout == "Delta/ low estuary island"
    ):
        flora_fauna = check_flora_fauna(transect)
    elif geological_layout == "Sloping soft rock":
        flora_fauna = check_flora_fauna_sl_soft_rock(transect)
    elif geological_layout == "corals":
        flora_fauna = "corals"
    elif geological_layout == "Flat hard rock":
        flora_fauna = check_flora_fauna_hard_rock(transect)
    elif geological_layout == "Sloping hard rock":
        flora_fauna = check_flora_fauna_sl_hard_rock(transect)
    sediment_balance = "Balance/Deficit"
    storm_climate = "Yes"
    output.update(
        {
            "geological_layout": geological_layout,
            "wave_exposure": wave_exposure,
            "tidal_range": tidal_range,
            "flora_fauna": flora_fauna,
            "sediment_balance": sediment_balance,
            "storm_climate": storm_climate,
        }
    )
    return output
