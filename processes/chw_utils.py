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
    get_sediment_changerate_values,
    get_shorelinechange_values,
    get_cyclone_risk,
    get_classes,
    get_measures,
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
dem = Path(output_dir) / "dem.tif"
dem_reprojected = Path(output_dir) / "dem_reprojected.tif"
globcover = Path(output_dir) / "globcover.tif"
_, _, _, _, _, owsurl, dem_layer, landuse_layer = read_config()


class CHW:
    def __init__(self, transect):
        self.transect = transect

        self.geological_layout = "Any"
        self.wave_exposure = "Any"
        self.tidal_range = "Any"
        self.flora_fauna = "Any"
        self.sediment_balance = "Balance/Deficit"
        self.storm_climate = "Any"

        self.ecosystem_disruption = 1
        self.gradual_inundation = 1
        self.salt_water_intrusion = 1
        self.erosion = 1
        self.flooding = 1

        self.transect_wkt = geojson_to_wkt(self.transect)
        self.bbox = get_bounds(self.transect)
        self.transect_projected = change_coords(self.transect)
        self.transect_length = self.transect_projected.length

        # get dem
        cut_wcs(*self.bbox, dem_layer, owsurl, dem)
        self.elevations, self.segments = get_elevation_profile(
            dem, self.transect_projected, self.transect_length, dem_reprojected
        )
        self.slope = round(calc_slope(self.elevations, self.segments), 3)

    # 1st level check
    def get_info_geological_layout(self):
        # TODO check correct order of checks
        if self.check_barrier():
            self.geological_layout = "Barrier"

        elif intersect_with_estuaries(self.transect_wkt):
            self.geological_layout = "Delta/ low estuary island"

        elif intersect_with_corals(self.transect_wkt):
            # TODO Do I check correctly for coral islands?
            # NOTE what is a coral island?
            self.geological_layout = "Coral island"

        else:
            self.geological_layout = self.check_geology_type()

    # 2nd level check
    def get_info_wave_exposure(self):
        self.wave_exposure = get_wave_exposure_value(self.transect_wkt)

    # 3rd level check
    def get_info_tida_range(self):
        self.tidal_range = get_tidal_range_values(self.transect_wkt)

    # 4th level check
    def get_info_flora_fauna(self):
        # special case
        if self.geological_layout == "Sloping soft rock":
            self.flora_fauna = self.get_vegetation()
        elif self.geological_layout in {"Sloping hard rock", "Flat hard rock"}:
            if intersect_with_corals(self.transect_wkt):
                self.flora_fauna = "Corals"
            elif intersect_with_mangroves(
                self.transect_wkt
            ) or intersect_with_saltmarshes(self.transect_wkt):
                self.flora_fauna = "Marsh/mangrove"

        else:
            if intersect_with_saltmarshes(self.transect_wkt):
                self.flora_fauna = (
                    "Intermittent marsh"
                    if self.tidal_range == "micro"
                    else "Marsh/tidal flat"
                )

            elif intersect_with_mangroves(self.transect_wkt):
                self.flora_fauna = (
                    "Intermittent mangrove"
                    if self.tidal_range == "micro"
                    else "Mangrove/tidal flat"
                )

    # 5th level check
    def get_info_sediment_balance(self):
        if self.geological_layout in {"Flat hard rock", "Sloping hard rock"}:
            self.sediment_balance = "Beach"
        elif (
            get_shorelinechange_values(self.transect_wkt) != "Low"
            and get_sediment_changerate_values(self.transect_wkt) > 0
        ):
            self.sediment_balance = "Surplus"

    # 6th level check
    def get_info_storm_climate(self):
        self.storm_climate = get_cyclone_risk(self.transect_wkt)

    def hazards_classification(self):

        (
            self.code,
            self.ecosystem_disruption,
            self.gradual_inundation,
            self.salt_water_intrusion,
            self.erosion,
            self.flooding,
        ) = get_classes(
            self.geological_layout,
            self.wave_exposure,
            self.tidal_range,
            self.flora_fauna,
            self.sediment_balance,
            self.storm_climate,
        )

    # TODO method Provide measures
    def provide_measures(self):

        measures = {}
        for row in get_measures(self.code):
            measures.update(
                {
                    row[0]: row[1],
                }
            )
        self.ecosystem_disruption_measures = measures["Ecosystem disruption"]
        self.gradual_inundation_measures = measures["Gradual inundation"]
        self.salt_water_intrusion_measures = measures["Salt water intrusion"]
        self.erosion_measures = measures["Erosion"]
        self.flooding_measures = measures["Flooding"]

    def check_geology_type(self) -> str:
        """
        Connects to database and gets the su values of geology type
        Checks if su values are dominant in the area
        According to slope and su values checks for:
             Sediment plain
             Sloping soft rock
             Flat hard rock
             Sloping hard rock
        Returns:
            str: The name of the geology type
        """

        geology_values = get_geol_glim_values(self.transect_wkt)

        non_su_values = sum(x != ("su",) for x in geology_values)
        su_values = sum(x == ("su",) for x in geology_values)
        if su_values >= non_su_values:
            geology = "su"
        else:
            geology = ""

        if geology == "su" and self.slope <= 3:
            return "Sediment plain"

        elif geology == "su" and self.slope > 3:
            return "Sloping soft rock"

        elif geology != "su" and self.slope <= 3:
            return "Flat hard rock"

        else:
            return "Sloping hard rock"

    def check_barrier(self) -> bool:
        sea_pattern = detect_sea_patterns(self.elevations)
        land_sea_changes = np.count_nonzero(sea_pattern is True)
        if land_sea_changes > 1:
            barrier = True
        else:
            barrier = False
        return barrier

    def get_vegetation(self):
        cut_wcs(*self.bbox, landuse_layer, owsurl, globcover)
        values = read_raster_values(globcover)

        non_vegetated = np.count_nonzero(np.logical_and(values >= 190, values <= 220))
        vegetated = np.count_nonzero(np.logical_and(values >= 20, values <= 150))
        if vegetated >= non_vegetated:
            self.flora_fauna = "Vegetated"
        else:
            self.flora_fauna = "Not vegetated"
