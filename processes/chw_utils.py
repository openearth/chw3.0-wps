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
from .db_utils import DB
import time


from .raster_utils import (
    calc_slope,
    cut_wcs,
    get_elevation_profile,
    get_landuse_profile,
    detect_sea_patterns,
    read_raster_values,
)
from .utils import create_temp_dir, read_config
from .vector_utils import change_coords, geojson_to_wkt, get_bounds

service_path = Path(__file__).resolve().parent
host, user, password, db, port, owsurl, dem_layer, landuse_layer = read_config()


class CHW:
    def __init__(self, transect):
        self.transect = transect

        self.db = DB(user, password, host, db)
        self.geological_layout = "Any"
        self.wave_exposure = "Any"
        self.tidal_range = "Any"
        self.flora_fauna = "Any"
        self.sediment_balance = "Balance/Deficit"
        self.storm_climate = "Any"

        # TMP-DEM-GLOBCOVER

        self.tmp = create_temp_dir(service_path / "outputs")
        self.dem = Path(self.tmp) / "dem.tif"
        self.dem_3857 = Path(self.tmp) / "dem_3857.tif"
        self.globcover = Path(self.tmp) / "globcover.tif"

        self.transect_wkt = geojson_to_wkt(self.transect)
        self.bbox = get_bounds(self.transect)

        self.transect_length = change_coords(self.transect).length

        # 10km from the point on the coast and -180 direction
        self.transect2km = self.db.ST_line_extend(
            wkt=self.transect_wkt, dist=2000, direction=-180
        )

        # 10km from the point on the coast and -180 direction
        self.transect10km = self.db.ST_line_extend(
            wkt=self.transect_wkt, dist=10000, direction=-180
        )

        # 100km from the point on the coast and -180 deg direction
        self.transect100km = self.db.ST_line_extend(
            wkt=self.transect_wkt, dist=100000, direction=-180
        )

        # self.transect_500_inland = self.db.ST_line_extend(
        #    wkt=self.transect_wkt, dist=500, direction=180
        # )

        # TODO add length of 20km.
        # 20 km transect = + 20km from point on the coast of the given transect (180 deg direction)
        self.transect20km = self.db.ST_line_extend(
            wkt=self.transect_wkt,
            transect_length=self.transect_length,
            dist=20000,
            direction=180,
        )

        self.bbox_20km = get_bounds(self.transect20km)

        # get dem
        cut_wcs(*self.bbox_20km, dem_layer, owsurl, self.dem)
        # TODO pass the path only and or give another name to the oufname.
        # it is not an output of elevation profile but something that I use
        # in the whole process
        self.elevations, self.segments = get_elevation_profile(
            dem=self.dem,
            line=change_coords(self.transect_wkt),
            line_length=change_coords(self.transect_wkt).length,
            outfname=self.dem_3857,
        )

        self.slope = round(calc_slope(self.elevations, self.segments), 3)

        self.geology = self.db.get_geol_glim_values(self.transect_wkt)

    # 1st level check
    def get_info_geological_layout(self):
        """"""

        if self.db.intersect_with_estuaries(self.transect_wkt) and self.slope < 3:
            self.geological_layout = "Delta/ low estuary island"

        elif self.geology != [] and self.check_barrier() is True:
            self.geological_layout = "Barrier"

        elif self.geology != []:
            self.geological_layout = self.check_geology_type()
        elif (
            self.geology == []
            and self.db.intersect_with_corals(self.transect_wkt) is True
        ):
            self.geological_layout = "Coral island"

    # 2nd level check
    def get_info_wave_exposure(self):
        """Retrieves the wave exposure values from the database.

        If exposed it is possible to drop either to moderately exposed
        (<100 km closest coastline that proects it)
        or to protected (<10 km closest coastline that protects it).
        If moderately exposed it can drop to protected(<10 km closest coastline that protects it)
        """
        self.wave_exposure = self.db.get_wave_exposure_value(self.transect_wkt)
        print("self.wave_exposure", self.wave_exposure)

        if self.wave_exposure == "moderately exposed":
            closest_coasts = self.db.fetch_closest_coasts(self.transect10km)
            print("closest_coasts 10km", closest_coasts)
            if len(closest_coasts) > 1:
                self.wave_exposure = "protected"
        elif self.wave_exposure == "exposed":
            closest_coasts = self.db.fetch_closest_coasts(self.transect100km)
            print("closest_coasts 100km", closest_coasts)
            if len(closest_coasts) > 1:
                self.wave_exposure = "moderately exposed"
            closest_coasts = self.db.fetch_closest_coasts(self.transect10km)
            print("closest_coasts 10km", closest_coasts)
            if len(closest_coasts) > 1:
                self.wave_exposure = "protected"

    # 3rd level check
    def get_info_tidal_range(self):
        self.tidal_range = self.db.get_tidal_range_values(self.transect_wkt)

    # 4th level check
    def get_info_flora_fauna(self):
        """
        Retrieve information from various layers:
            - detect mangroves
            - detect corals (coral reefs)
            - salt marshes
            - overal vegetation presence

        Returns
        -------
        None.

        """
        # special cases
        if self.geological_layout == "Sloping soft rock":
            self.flora_fauna = self.get_vegetation()
        elif self.geological_layout in {
            "Sloping hard rock",
            "Flat hard rock",
            "Corals",
        }:
            # corals check intersection with transect 2 km -180 (close to the coast)
            if self.db.intersect_with_corals(self.transect2km):
                self.flora_fauna = "Corals"
            elif self.db.intersect_with_mangroves(
                self.transect_wkt
            ) or self.db.intersect_with_saltmarshes(self.transect_wkt):
                self.flora_fauna = "Marsh/mangrove"
        else:
            if self.db.intersect_with_saltmarshes(self.transect_wkt):
                self.flora_fauna = (
                    "Intermittent marsh"
                    if self.tidal_range == "micro"
                    else "Marsh/tidal flat"
                )

            elif self.db.intersect_with_mangroves(self.transect_wkt):
                self.flora_fauna = (
                    "Intermittent mangrove"
                    if self.tidal_range == "micro"
                    else "Mangrove/tidal flat"
                )

    # 5th level check
    def get_info_sediment_balance(self):

        if self.geological_layout in {"Flat hard rock", "Sloping hard rock"}:
            try:
                beach = self.db.intersect_with_osm_beaches(self.transect_wkt)
                if beach is True:
                    self.sediment_balance = "Beach"
                else:
                    self.sediment_balance = "No Beach"
            except Exception:
                self.sediment_balance = "Beach"
        elif (
            self.db.get_shorelinechange_values(self.transect_wkt) != "Low"
            and self.db.get_sediment_changerate_values(self.transect_wkt) > 0
        ):
            self.sediment_balance = "Surplus"

    # 6th level check
    def get_info_storm_climate(self):
        # TODO try exception in order to prevent error in Norway. I have to check why this is happens.
        try:
            self.storm_climate = self.db.get_cyclone_risk(self.transect_wkt)
        except Exception:
            self.storm_climate = "No"

    def hazards_classification(self):

        try:

            (
                self.code,
                self.ecosystem_disruption,
                self.gradual_inundation,
                self.salt_water_intrusion,
                self.erosion,
                self.flooding,
            ) = self.db.get_classes(
                self.geological_layout,
                self.wave_exposure,
                self.tidal_range,
                self.flora_fauna,
                self.sediment_balance,
                self.storm_climate,
            )
        except Exception:
            self.code = "None"
            self.ecosystem_disruption = "None"
            self.gradual_inundation = "None"
            self.salt_water_intrusion = "None"
            self.erosion = "None"
            self.flooding = "None"

    def provide_measures(self):

        measures = {}
        try:
            for row in self.db.get_measures(self.code):
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
        except Exception:
            self.ecosystem_disruption_measures = ["No measures were found"]
            self.gradual_inundation_measures = ["No measures were found"]
            self.salt_water_intrusion_measures = ["No measures were found"]
            self.erosion_measures = ["No measures were found"]
            self.flooding_measures = ["No measures were found"]

    def get_risk_info(self):
        try:
            self.gar, self.population = self.db.get_gar_pop_values(self.transect_wkt)
        except Exception:
            self.gar, self.population = "No data", "No data"

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

        unconsol = sum(x in [("su",), ("sm",), ("ss",), ("sc",)] for x in self.geology)
        non_unconsol = sum(
            x not in [("su",), ("sm",), ("ss",), ("sc",)] for x in self.geology
        )

        if unconsol >= non_unconsol:
            geology_type = "soft"
        else:
            geology_type = "hard"

        if geology_type == "soft" and self.slope <= 3:
            return "Sediment plain"

        elif geology_type == "soft" and self.slope > 3:
            return "Sloping soft rock"

        elif geology_type == "hard" and self.slope <= 3:
            return "Flat hard rock"

        else:
            return "Sloping hard rock"

    def check_barrier(self) -> bool:
        """
        Returns
        -------
        bool
            DESCRIPTION.
            The pattern that is used here detects 210 water value from the GlobCover dataset over a transect of 20 km.
            In order to classify as barrier:
                If unconsolidated values &&
                If pattern sea-land is detected more than one time over the transect
                If the land sea pattern is not detected far from the first sea land pattern (A way to prevent recognize as barriers
                big (in widht) pieces of land)
        """
        # cut the globcover dataset with the bbox of the 20km transect extension
        globcover20km = Path(self.tmp) / "globcover_20km.tif"
        cut_wcs(*self.bbox_20km, landuse_layer, owsurl, globcover20km)

        # Land use profile over the transect
        landuse, _ = get_landuse_profile(
            globcover20km,
            line=change_coords(self.transect20km),
            line_length=change_coords(self.transect20km).length,
            temp=self.tmp,
        )

        # Detect sea pattern: Sea, land and land_sea
        sea_land_pattern, land_sea_pattern = detect_sea_patterns(landuse)

        # find where sea-land pattern is detected
        sea_land_changes = np.argwhere(sea_land_pattern == True)
        # find where the land-sea pattern is detected
        land_sea_changes = np.argwhere(land_sea_pattern == True)
        print("CHANGES", sea_land_changes, land_sea_changes)
        print("geology", self.geology)

        try:
            first_sea_land_change = sea_land_changes[0][0]
            first_land_sea_change = land_sea_changes[0][0]
        except Exception:
            first_sea_land_change = None
            first_land_sea_change = None

        # Check if unconsolitated values on the coast
        unconsol = sum(x == ("su",) for x in self.geology)
        non_unconsol = sum(x != ("su",) for x in self.geology)

        if (
            unconsol >= non_unconsol
            and sea_land_changes.shape[0] > 1
            and (
                first_land_sea_change - first_sea_land_change < 4
            )  # 4*300 = 1200 meter width?
        ):
            barrier = True
        else:
            barrier = False
        return barrier

    def get_vegetation(self):
        cut_wcs(*self.bbox, landuse_layer, owsurl, self.globcover)
        values = read_raster_values(self.globcover)
        non_vegetated = np.count_nonzero(np.logical_and(values >= 190, values <= 220))
        vegetated = np.count_nonzero(np.logical_and(values >= 20, values <= 150))
        if vegetated >= non_vegetated:
            return "Vegetated"
        else:
            return "Not vegetated"
