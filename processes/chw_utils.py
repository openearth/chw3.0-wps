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
import numpy as np
from .db_utils import DB


from .raster_utils import (
    calc_slope,
    cut_wcs,
    get_elevation_profile,
    get_landuse_profile,
    detect_sea_patterns,
    median_elevation,
    calc_slope_200m_inland,
)
from .utils import create_temp_dir, read_config
from .vector_utils import change_coords, geojson_to_wkt, get_bounds

service_path = Path(__file__).resolve().parent
host, user, password, db, port, owsurl, dem_layer, landuse_layer = read_config()


class CHW:
    def __init__(self, transect):

        # The transect will be always 500 meters inland
        self.transect = transect

        # Initiate the DB class
        self.db = DB(user, password, host, db)

        # Give default values to the information layers
        self.geological_layout = "Any"
        self.wave_exposure = "Any"
        self.tidal_range = "Any"
        self.flora_fauna = "Any"
        self.sediment_balance = "Balance/Deficit"
        self.storm_climate = "Any"

        # Filenames/TMP #TODO more the dem, dem_3857, glob
        # unique temp directory for every run
        self.tmp = create_temp_dir(service_path / "outputs")
        self.dem = Path(self.tmp) / "dem.tif"
        self.dem_5km2 = Path(self.tmp) / "dem_5km2.tif"
        self.dem_3857 = Path(self.tmp) / "dem_3857.tif"
        self.globcover = Path(self.tmp) / "globcover.tif"

        self.transect_wkt = geojson_to_wkt(self.transect)
        print("self.transect", self.transect_wkt)

      

        self.transect_length = change_coords(self.transect).length

        # Create transects for different procedures:
        # 8km and 180 m from the coast to check if intersects with corals(coral-island)
        # 5km and -180 from the coast: To check if corals vegetation exist
        # 10km and -180 from the coast: To check if intersects coastline (wave exposure)
        # 100km and -180 from the coast: To check if intersects coastline (wave exposure)
        self.transect_8km = self.db.ST_line_extend(
            wkt=self.transect_wkt,
            dist=8000,
            direction=180,
        )
        self.transect_5km = self.db.ST_line_extend(
            wkt=self.transect_wkt,
            dist=5000,
            direction=180,
        )
        self.transect_5km = self.db.ST_line_extend(
            wkt=self.transect_wkt, dist=5000, direction=-180
        )
        self.transect_10km = self.db.ST_line_extend(
            wkt=self.transect_wkt, dist=10000, direction=-180
        )
        self.transect_100km = self.db.ST_line_extend(
            wkt=self.transect_wkt, dist=100000, direction=-180
        )


        # TODO add extra meters to the bbox to prevent cases that the bbox is parallel.
        # bboxes of the transect : To cut the DEM
        self.bbox = get_bounds(self.transect)
        self.bbox_5km = get_bounds(self.transect_5km)

        # CUT the WCS of the DEM with the b
        try:
            cut_wcs(*self.bbox, dem_layer, owsurl, self.dem)
            self.elevations, self.segments = get_elevation_profile(
                dem=self.dem,
                line=change_coords(self.transect_wkt),
                line_length=change_coords(self.transect_wkt).length,
                outfname=self.dem_3857,
            )
            # Mean slope
            self.slope, self.max_slope = calc_slope(self.elevations, self.segments)
            self.slope = round(self.slope, 3)
        except Exception:
            print("SLOPE Exception: if it is not feasible to cut the dem")
            self.slope = 0.00

        try:
            self.geology = self.db.get_closest_geology_glim(self.transect_wkt)
        except Exception:
            self.geology = None

    # 1st level check
    def get_info_geological_layout(self):
        """Priority check of geological layout.
        First corals, then special cases of flat hard rock or sloping hard rock in case that
        there is coral vegetation in the area, then delta/low estaury islands, barriers and
        finally geology type check.
        """

        if self.check_coral_islands() is True:
            self.geological_layout = "Coral island"

        elif self.special_case_flat_hard_rock() is True:
            self.geological_layout = "Flat hard rock"

        elif self.special_case_sloping_hard_rock() is True:
            self.geological_layout = "Sloping hard rock"

        elif self.db.intersect_with_estuaries(self.transect_wkt) and self.slope < 3:
            self.geological_layout = "Delta/ low estuary island"

        elif self.db.intersect_with_barrier_island(self.transect_wkt) is True:
            self.geological_layout = "Barrier"

        elif self.geology != None:
            self.geological_layout = self.check_geology_type()
        print("----GEOLOGICAL_LAYOUT---:", self.geological_layout)

    # 2nd level check
    def get_info_wave_exposure(self):
        """Retrieves the wave exposure values from the database.

        If exposed it is possible to drop either to moderately exposed
        (<100 km closest coastline that proects it)
        or to protected (<10 km closest coastline that protects it).
        If moderately exposed it can drop to protected(<10 km closest coastline that protects it)
        """
        closest_coasts_10km = self.db.fetch_closest_coasts(self.transect_10km)
        closest_coasts_100km = self.db.fetch_closest_coasts(self.transect_100km)
        # print(
        #    f"----FETCH DEBUGGING part 1-- 10 and 100km closest coasts: {closest_coasts_10km}, {closest_coasts_100km}"
        # )
        try:
            self.wave_exposure = self.db.get_wave_exposure_value(self.transect_wkt)
        except Exception:
            self.wave_exposure = "exposed"
        # print(f"----FETCH DEBUGGING-- Database returns: {self.wave_exposure}")

        if self.wave_exposure == "moderately exposed":
            if len(closest_coasts_10km) > 1:
                self.wave_exposure = "protected"

        elif self.wave_exposure == "exposed":
            if len(closest_coasts_100km) > 1:
                self.wave_exposure = "moderately exposed"

            if len(closest_coasts_10km) > 1:
                self.wave_exposure = "protected"
        # print(f"----FETCH DEBUGGING-- Database returns: ")
        # print("----WAVE EXPOSURE---:", self.wave_exposure)

    # 3rd level check
    def get_info_tidal_range(self):
        try:
            self.tidal_range = self.db.get_tidal_range_values(self.transect_wkt)
        except Exception:
            self.tidal_range = "any"
        print("----TIDAL RANGE-----", self.tidal_range)

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
            "Coral island",
        }:
            if self.db.intersect_with_corals(self.transect_5km):
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
            else:
                lat = self.transect["geometry"]["coordinates"][0][1]
                print("----LAT----", lat)
                if lat >= -25 and lat <= 25:
                    print("---Intermittent mangrove ---")
                    self.flora_fauna = (
                        "Intermittent mangrove"
                        if self.tidal_range == "micro"
                        else "Mangrove/tidal flat"
                    )
                else:
                    print("---Intermittent marsh ---")
                    self.flora_fauna = (
                        "Intermittent marsh"
                        if self.tidal_range == "micro"
                        else "Marsh/tidal flat"
                    )
        print("-----FLORA FAUNA-----", self.flora_fauna)

    # 5th level check
    def get_info_sediment_balance(self):

        if self.geological_layout in {"Flat hard rock", "Sloping hard rock"}:
            beach = self.db.intersect_with_osm_beaches(self.transect_wkt)
            if beach is True:
                self.sediment_balance = "Beach"
            else:
                self.sediment_balance = "No Beach"
        else:
            try:
                if (
                    self.db.get_shorelinechange_values(self.transect_wkt) != "Low"
                    and self.db.get_sediment_changerate_values(self.transect_wkt) > 0
                ):
                    self.sediment_balance = "Surplus"
            except Exception:
                # NOTE Accordin to documentation of CHW, if doubts regarding the sediment balance,
                # then always choose balance/deficit as it is the default.
                self.sediment_balance = "Balance/Deficit"
        print("----SEDIMENT BALANCE-----", self.sediment_balance)

    # 6th level check
    def get_info_storm_climate(self):
        # TODO try exception in order to prevent error in Norway. I have to check why it happens.
        # TODO cyclone risks sometimes does not work. See when and why.
        # NOTE there are cases where no cyclon_risk is return while there are values according to the
        # online version of the tool.
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
        Checks if unconsolidated sediments and carbonate sediment rocks
        values are dominant in the area

             Sediment plain
             Sloping soft rock
             Flat hard rock
             Sloping hard rock
        Returns:
            str: The name of the geology type
        """

        unconsol = ["su", "sc"]

        if self.geology in unconsol and self.slope <= 3:
            return "Sediment plain"

        elif self.geology in unconsol and self.slope > 3:
            return "Sloping soft rock"

        elif self.geology not in unconsol and self.slope <= 3:
            return "Flat hard rock"

        else:
            return "Sloping hard rock"


    def get_vegetation(self):
        """check vegetation with slope 200m inland
        if slope >30% then too steep to have vegetation
        """
        # Max slope
        slope = calc_slope_200m_inland(self.elevations, self.segments)
        print("SLOPE VEGETATION-----", slope)
        if slope >= 30:
            return "Not vegetated"
        else:
            return "Vegetated"

    def check_coral_islands(self):
        try:
            cut_wcs(*self.bbox_5km, dem_layer, owsurl, self.dem_5km2)
            self.median_elevation = median_elevation(self.dem_5km2)
        except Exception:
            self.median_elevation = 0
        if (
            self.db.intersect_with_corals(self.transect_8km)
            and self.db.intersect_with_island(self.transect_wkt)
            and self.db.intersect_with_corals(self.transect_5km)
            and self.median_elevation < 2
        ):
            coral_island = True
        else:
            coral_island = False
        return coral_island

    def special_case_flat_hard_rock(self):
        # and self.db.intersect_with_island(self.transect_wkt) is False
        if self.db.intersect_with_corals(self.transect_5km) and self.slope < 3:
            flat_hard_rock = True
        else:
            flat_hard_rock = False
        return flat_hard_rock

    def special_case_sloping_hard_rock(self):
        if self.db.intersect_with_corals(self.transect_5km) and self.slope > 3:
            sloping_hard_rock = True
        else:
            sloping_hard_rock = False
        return sloping_hard_rock