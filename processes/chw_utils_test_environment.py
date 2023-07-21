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

import logging
from pathlib import Path
from .db_utils import DB

from .raster_utils import (
    calc_slope,
    cut_wcs,
    get_elevation_profile,
    calc_median_elevation,
    calc_slope_200m_inland,
    read_raster_values,
)
from .utils import create_temp_dir, read_config, translate_hazard_danger
from .vector_utils import change_coords, geojson_to_wkt, get_bounds
import numpy as np

service_path = Path(__file__).resolve().parent
(
    host,
    user,
    password,
    db,
    port,
    owsurl,
    dem_layer,
    landuse_layer,
    dem_test_layer,
    username,
    geoserver_password,
) = read_config()

LOGGER = logging.getLogger("PYWPS")

# various variables declared used in several functions (GHN 26-06-2023)
#define flat hard rock/soft rock/sediment plain cut-off value for slope, used in function check_geology_type
#cov = cut off value 

cov_slope_hr = 2.3  #hr = hard rock
cov_slope_bd = 3.5  #  bd = for barriers and deltas

# define variable for cut-off value for slope with specific vegetation, use in function check_vegetation
cov_slope_veg = 59

# define variable for cut-off value for median elevation in case of coral islands, use in function check_coral_island
cov_elev_ci = 14


class CHW:
    def __init__(self, transect, testing=False):
        LOGGER.info(f"---cut-off value slope flat hard rock/soft rock/sediment plain---: {cov_slope_hr}")
        LOGGER.info(f"---cut-off value slope vegetation---: {cov_slope_veg}")
        LOGGER.info(f"---cut-off value median elevation coral island---: {cov_elev_ci}")

        # The transect will be always 500 meters inland
        self.transect = transect
        # Notification message for that case
        self.notification = self.transect["properties"]["notification"]
        # Initiate the DB class
        self.db = DB(user, password, host, db)

        # Give default values to the information layers
        self.geological_layout = "Any"
        self.wave_exposure = "Any"
        self.tidal_range = "any"  # TODO Why is this "any" Check the database.
        self.flora_fauna = "Any"
        self.sediment_balance = "Balance/Deficit"
        self.storm_climate = "Any"

        self.dem_layer = dem_test_layer if testing else dem_layer
        # Filenames/TMP #TODO more the dem, dem_3857, glob
        # unique temp directory for every run
        self.tmp = create_temp_dir(service_path / "outputs")
        self.dem = Path(self.tmp) / "dem.tif"
        self.dem_small_island = Path(self.tmp) / "dem_small_island.tif"
        self.dem_3857 = Path(self.tmp) / "dem_3857.tif"
        self.globcover = Path(self.tmp) / "glocover.tif"

        self.transect_wkt = geojson_to_wkt(self.transect)
        LOGGER.info(f"---Input transect---: {self.transect_wkt}")

        self.transect_length = change_coords(self.transect).length

        # Create transects for different procedures:
        # 8km and 180 m from the coast to check if intersects with corals(coral-island)
        # 5km and -180 from the coast: To check if corals vegetation exist
        # 4km to the sea: To check if corals vegetation exist
        # 10km and -180 from the coast: To check if intersects coastline (wave exposure)
        # 100km and -180 from the coast: To check if intersects coastline (wave exposure)
        # TODO rename the transect in a way to be clear if they are inland or to the sea
        self.transect_5km = self.db.ST_line_extend(
            wkt=self.transect_wkt,
            dist=5000,
            direction=180,
        )
        self.transect_4km = self.db.ST_line_extend(
            wkt=self.transect_wkt,
            dist=4000,
            direction=-180,
        )
        self.transect_4km_inland = self.db.ST_line_extend(
            wkt=self.transect_wkt,
            dist=4000,
            direction=180,
        )
        self.transect_6km = self.db.ST_line_extend(
            wkt=self.transect_wkt,
            dist=6000,
            direction=-180,
        )
        self.transect_10km = self.db.ST_line_extend(
            wkt=self.transect_wkt, dist=10000, direction=-180
        )
        self.transect_100km = self.db.ST_line_extend(
            wkt=self.transect_wkt, dist=100000, direction=-180
        )
        self.transect_200m = self.db.ST_line_extend(
            wkt=self.transect_wkt, dist=200, direction=-180
        )
        self.transect_100m = self.db.ST_line_extend(
            wkt=self.transect_wkt, dist=100, direction=-180
        )

        # TODO add extra meters to the bbox to prevent cases that the bbox is parallel.
        # bboxes of the transect : To cut the DEM
        self.bbox = get_bounds(self.transect)
        self.bbox_5km = get_bounds(self.transect_5km)
        
        
        
        # Get the slope over the 500m inland transect
        try:
            cut_wcs(
                *self.bbox,
                self.dem_layer,
                owsurl,
                self.dem,
                username=username,
                password=geoserver_password,
            )
            self.elevations, self.segments = get_elevation_profile(
                dem_path=self.dem,
                line=change_coords(self.transect_wkt),
                line_length=change_coords(self.transect_wkt).length,
                temp_dir=self.tmp,
            )

            # Mean slope
            self.slope, self.max_slope = calc_slope(self.elevations, self.segments)

            self.slope = round(self.slope, 1)
        except:
            raise Exception(
                "There are no elevation data in the area, please try another location"
            )

        try:
            self.geology = self.db.get_geology_value(self.transect_wkt)
        except Exception:
            self.geology = None
        # Check if intersect with corals 4km in the sea. Important for define geological layout and coral vegetation
        self.corals = self.db.intersect_with_corals(self.transect_6km) or self.db.intersect_with_corals(self.transect_4km_inland)
        LOGGER.info(f"---Corals vegetation is---: {self.corals}")
        self.geology_material = (
            "unconsolidated"
            if self.geology in ["su", "fluvisol", "wb"]
            else "consolidated"
        )
        LOGGER.info(f"---geology material is---: {self.geology_material}")

    # 1st level check
    def get_info_geological_layout(self):
        """Priority check of geological layout.
        First corals, then special cases of flat hard rock or sloping hard rock in case that
        there is coral vegetation in the area, then delta/low estaury islands, barriers and
        finally geology type check.
        """
        # TODO check_river_mouth
        LOGGER.info(f"---slope, cov_slope_bd, geolory---: {self.slope},{cov_slope_bd},{self.geology}")
        if (
            self.db.intersect_with_small_estuaries(self.transect_wkt)
            or self.db.intersect_with_small_estuaries(self.transect_100m)
        ) and self.slope <= cov_slope_bd: 
            self.geological_layout = "River mouth"

        elif self.check_coral_islands() is True:
            self.geological_layout = "Coral island"

        elif self.special_case_flat_hard_rock() is True:
            self.geological_layout = "Flat hard rock"

        elif self.special_case_sloping_hard_rock() is True:
            self.geological_layout = "Sloping hard rock"
    
        elif (
            self.db.intersect_with_barriers_sandspits(self.transect_wkt) is True
            and self.geology_material == "unconsolidated"
            and self.slope <= cov_slope_bd):
            self.geological_layout = "Barrier"

        elif (
            (
                self.db.intersect_with_estuaries(self.transect_100m)
                or self.db.intersect_with_estuaries(self.transect_wkt)
            )
            and self.geology_material == "unconsolidated"
            and self.slope <= cov_slope_bd):
            self.geological_layout = "Delta/ low estuary island"
        elif self.geology != None:
            self.geological_layout = self.check_geology_type()
        else:
            self.geological_layout = self.special_case_hard_rock()

        LOGGER.info(f"---GEOLOGICAL_LAYOUT---: {self.geological_layout}")

    # 2nd level check
    def get_info_wave_exposure(self):
        """Retrieves the wave exposure values from the database.

        If exposed it is possible to drop either to moderately exposed
        (<100 km closest coastline that proects it)
        or to protected (<10 km closest coastline that protects it).
        If moderately exposed it can drop to protected(<10 km closest coastline that protects it)
        """
        coastline_id = float(self.transect["properties"]["coastline_id"])
        closest_coasts_10km = self.db.fetch_closest_coasts(self.transect_10km)

        closest_coasts_100km = self.db.fetch_closest_coasts(self.transect_100km)

        # Check if coastline_id is in the list of closest coasts (fix accuracy error that way)
        if coastline_id not in closest_coasts_10km:
            closest_coasts_10km.append(coastline_id)
        if coastline_id not in closest_coasts_100km:
            closest_coasts_100km.append(coastline_id)

        try:
            self.wave_exposure = self.db.get_wave_exposure_value(self.transect_wkt)
        except Exception:
            self.wave_exposure = "moderately exposed"

        if self.wave_exposure == "moderately exposed":
            if len(closest_coasts_10km) > 1:
                self.wave_exposure = "protected"

        elif self.wave_exposure == "exposed":
            if len(closest_coasts_100km) > 1:
                self.wave_exposure = "moderately exposed"

            if len(closest_coasts_10km) > 1:
                self.wave_exposure = "protected"
        LOGGER.info(f"---WAVE EXPOSURE---: {self.wave_exposure}")

    # 3rd level check
    def get_info_tidal_range(self):
        try:
            self.tidal_range = self.db.get_tidal_range_values(self.transect_wkt)
        except Exception:
            self.tidal_range = "micro"
        LOGGER.info(f"---TIDAL RANGE---: {self.tidal_range}")

    # 4th level check
    def get_info_flora_fauna(self):
        """
        flora fauna can be:
            Corals, Marsh/Mangrove, Intermittent marsh, Intermittent mangrove,
            Mangrove/tidal flat, "Marsh/tidal flat


        """
        mangroves = self.db.intersect_with_mangroves(self.transect_wkt)
        saltmarshes = self.db.intersect_with_saltmarshes(self.transect_wkt)
        LOGGER.info(f"---Saltmarshes, Mangroves---: {saltmarshes}, {mangroves}")
        # Special case of sloping soft rock
        if self.geological_layout == "Sloping soft rock":
            self.flora_fauna = self.get_vegetation()
        # Special case FR-17, FR-18
        elif (
            self.geological_layout == "Flat hard rock"
            and self.wave_exposure == "protected"
            and mangroves is False
            and saltmarshes is False
        ):
            self.flora_fauna = "No"
        elif self.geological_layout in {
            "Sloping hard rock",
            "Flat hard rock",
            "Coral island",
        }:
            if self.corals:
                self.flora_fauna = "Corals"
            elif mangroves or saltmarshes:
                self.flora_fauna = "Marsh/mangrove"
        else:
            if saltmarshes:
                self.flora_fauna = (
                    "Intermittent marsh"
                    if self.tidal_range == "micro"
                    else "Marsh/tidal flat"
                )

            elif mangroves:
                self.flora_fauna = (
                    "Intermittent mangrove"
                    if self.tidal_range == "micro"
                    else "Mangrove/tidal flat"
                )
            else:
                lat = self.transect["geometry"]["coordinates"][0][1]
                if lat >= -25 and lat <= 25:
                    self.flora_fauna = (
                        "Intermittent mangrove"
                        if self.tidal_range == "micro"
                        else "Mangrove/tidal flat"
                    )
                else:
                    self.flora_fauna = (
                        "Intermittent marsh"
                        if self.tidal_range == "micro"
                        else "Marsh/tidal flat"
                    )
        LOGGER.info(f"---FLORA FAUNA---: {self.flora_fauna}")

    # 5th level check
    def get_info_sediment_balance(self):
        """For the cases of flat hard rock and sloping hard rock the sediment balance is estimated by the presence or not of a beach
        Sediment balance can be surplus when the shoreline change is medium or high and when the change rate is >0.5.
        Surplus only when seawards (see documentation)"""
        # TODO perhaps write it more clear.
        if self.geological_layout in {"Flat hard rock", "Sloping hard rock"}:
            beach = False
            try:
                if (self.db.intersect_with_osm_beaches(self.transect_wkt)) or (
                    self.db.intersect_with_osm_beaches(self.transect_200m)
                ):
                    beach = True
                if beach is True:
                    self.sediment_balance = "Beach"
                elif beach is False:
                    self.sediment_balance = "No Beach"
            except Exception:
                self.sediment_balance = "No Beach"

        else:
            try:
                if (
                    self.db.get_shorelinechange_values(self.transect_wkt) != "Low"
                    and self.db.get_sediment_changerate_values(self.transect_wkt) > 0.5
                ):
                    self.sediment_balance = "Surplus"
            except Exception:
                # NOTE According to documentation of CHW, if doubts regarding the sediment balance,
                # then always choose balance/deficit as it is the default.
                self.sediment_balance = "Balance/Deficit"
        LOGGER.info(f"---SEDIMENT BALANCE---: {self.sediment_balance}")

    # 6th level check
    def get_info_storm_climate(self):
        """Get cyclone risk value from db"""

        try:
            self.storm_climate = self.db.get_cyclone_risk(self.transect_wkt)
        except Exception:
            self.storm_climate = "No"
        LOGGER.info(f"---STROM CLIMATE---: {self.storm_climate}")

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
        LOGGER.info(
            f"-- Database result {self.ecosystem_disruption}, {self.gradual_inundation}, {self.gradual_inundation}, {self.erosion}, {self.flooding}"
        )

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
        Connects to database and gets the values of geology type
        Checks if unconsolidated material
        values are dominant in the area
        For slope check 3% limit was selected. During the process this is finetuned to current values (GerritH, 12-06-2023)
             Sediment plain
             Sloping soft rock
             Flat hard rock
             Sloping hard rock
        Returns:
            str: The name of the geology type
        """
        if self.geology_material == "unconsolidated" and self.slope <= cov_slope_hr: 
            return "Sediment plain"

        elif self.geology_material == "unconsolidated" and self.slope > cov_slope_hr:
            return "Sloping soft rock"

        elif self.geology_material == "consolidated" and self.slope <= cov_slope_hr:
            return "Flat hard rock"

        else:
            return "Sloping hard rock"

    def special_case_hard_rock(self):

        """In case no corals, no barriers, no delta low estuary and no geology is retrieved
        then we assume that the geological layout will be either flat hard rock or sloping hard rock.
        """
        if self.slope <= cov_slope_hr:
            LOGGER.info(f"---Special case hard rock---: falt hr")
            return "Flat hard rock"
        else:
            LOGGER.info(f"---Special case hard rock---: sloping hr")
            return "Sloping hard rock" 

    def get_vegetation(self):
        """
        In that case vegetation values can be:
            -Not vegetatied
            -Vegetated
        The vegetation value is estimated by calculating the slope of
        a transect that extends 200 m inland

        Sparse (< 15%) vegetation -> 150/ Artificial surfaces -> 190 / Bare areas -> 200 / Permanent snow and ice -> 220
        """

        slope = calc_slope_200m_inland(self.elevations, self.segments)

        LOGGER.info(f"---SLOPE 200 m inland--- bnd = 60: {slope}")

        cut_wcs(
            *self.bbox,
            landuse_layer,
            owsurl,
            self.globcover,
            username=username,
            password=geoserver_password,
        )
        values = read_raster_values(self.globcover)

        snow_ice = np.count_nonzero(values == 220)
        bare_areas = np.count_nonzero(values == 200)
        artificial_surfaces = np.count_nonzero(values == 190)
        sparce = np.count_nonzero(values == 150)
        globcover_category_a = snow_ice + bare_areas + artificial_surfaces + sparce
        globcover_category_b = values.size - globcover_category_a
        
        #if slope < 30 and (globcover_category_b >= globcover_category_a):
        if slope < cov_slope_veg and (globcover_category_b >= globcover_category_a):            
            return "Vegetated"

        else:
            return "Not vegetated"

    def check_coral_islands(self):

        """
        Procedure:
        if intersects with small_island (500m transect)
            get land polygon geojson of the transect 500m
            get bounds of it
            cut wcs with the bounds of the land polygon
          
            
        In order to be classified as coral island all the following statements should be true:
            if intersect with corals
            if it is an island
            if the median elevation is <2: this limit was selected via testing #TODO: Check with Lars if we should increase it.  
        Returns:
            Boolean
        """

        if self.db.intersect_with_small_island(self.transect_wkt):
            land_polygon = self.db.get_land_polygon(self.transect_wkt)
            small_island_bbox = get_bounds(land_polygon)
            try:

                cut_wcs(
                    *small_island_bbox,
                    self.dem_layer,
                    owsurl,
                    self.dem_small_island,
                    username=username,
                    password=geoserver_password,
                )
                self.median_elevation = calc_median_elevation(self.dem_small_island, land_polygon)
                LOGGER.info(f"---MEDIAN ELEVATION OF ISLAND---: {self.median_elevation}")
            except Exception:
                self.median_elevation = 0
            
            #if(self.corals is True and self.median_elevation < 8 and self.slope < 4): #TODO if we increase to 8 add an extra check of the slope 500 m line smaller than 2.2
            LOGGER.info(f"---MEDIAN ELEVATION OF ISLAND < {cov_elev_ci}---: {self.median_elevation}")
            if(self.corals is True and self.median_elevation < cov_elev_ci):
                coral_island = True
            else:
                coral_island = False
            
        else:
            coral_island = False
        LOGGER.info(f"---ci---: {coral_island}")    
        return coral_island
        


    def special_case_flat_hard_rock(self):
        """In case we have coral vegetation then flat hard rock or
        sloping hard rock geology
        Slope class fine tuned (GerritH 12-06-2023)
        Returns:
            Boolean
        """
        LOGGER.info(f"---Special case flat hard rock < {cov_slope_hr}")
        if self.corals and self.slope < cov_slope_hr:
            flat_hard_rock = True
        else:
            flat_hard_rock = False
        LOGGER.info(f"---Special case fhr---: {flat_hard_rock}")
        return flat_hard_rock

    def special_case_sloping_hard_rock(self):
        """In case we have coral vegetation then flat hard rock or
        sloping hard rock geology
        Slope class fine tuned (GerritH 12-06-2023)
        Returns:
            Boolean
        """
        
        if self.corals and self.slope >= cov_slope_hr:
            sloping_hard_rock = True
        else:
            sloping_hard_rock = False
        LOGGER.info(f"---Special case sloping hard rock >= {cov_slope_hr}, returned: {sloping_hard_rock}")
        return sloping_hard_rock

    def translate_hazard_danger(self):
        self.ecosystem_disruption = translate_hazard_danger(self.ecosystem_disruption)
        self.gradual_inundation = translate_hazard_danger(self.gradual_inundation)
        self.salt_water_intrusion = translate_hazard_danger(self.salt_water_intrusion)
        self.erosion = translate_hazard_danger(self.erosion)
        self.flooding = translate_hazard_danger(self.flooding)
