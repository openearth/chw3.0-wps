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
# OpenEarthTools is an onwkt collaboration to share and manage data and
# programming tools in an open source, version controlled environment.
# Sign up to recieve regular updates of this function, and to contribute
# your own tools.

from .utils import read_config
import psycopg2
from typing import List
import logging


class DB:
    def __init__(self, user, password, host, db):
        self.user = user
        self.password = password
        self.host = host
        self.db = db
        self.connection = psycopg2.connect(
            user=self.user, password=self.password, host=self.host, database=self.db
        )

    def close_db_connection(self):
        self.connection.close()

    def intersect_with_estuaries(self, wkt, crs=4326) -> bool:
        """coast.estuaries
        Args:
            wkt: str
            crs: int


        Returns:
            bool: True if intersects, false if not
        """

        query = f"""SELECT EXISTS(
                    SELECT 1 
                    FROM coast.estuaries
                    WHERE ST_Intersects(geom, ST_GeomFromText(\'{wkt}\', {crs})) and area_km2 > 50
                )"""
        with self.connection:
            cursor = self.connection.cursor()
            cursor.execute(query)
            estuaries = cursor.fetchone()[0]
            cursor.close()

        return estuaries

    def intersect_with_small_estuaries(self, wkt, crs=4326) -> bool:
        """coast.estuaries Small estuaries are considered estuaries with area <50km
        Args:
            wkt: str
            crs: int


        Returns:
            bool: True if intersects, false if not
        """

        query = f"""SELECT EXISTS(
                    SELECT 1 
                    FROM coast.estuaries
                    WHERE ST_Intersects(geom, ST_GeomFromText(\'{wkt}\', {crs})) and area_km2 < 50
                )"""

        with self.connection:
            cursor = self.connection.cursor()
            cursor.execute(query)
            estuaries = cursor.fetchone()[0]
            cursor.close()
        return estuaries

    def intersect_with_corals(self, wkt, crs=4326) -> bool:
        """vegetation.corals
        Args:
            wkt (str):
            crs (int):


        Returns:
            bool: True if intersects, false if not
        """

        query = f"""SELECT EXISTS(
                    SELECT 1 
                    FROM vegetation.corals
                    WHERE ST_Intersects(geom, ST_GeomFromText(\'{wkt}\', {crs}))
                )"""
        with self.connection:
            cursor = self.connection.cursor()
            cursor.execute(query)
            corals = cursor.fetchone()[0]
            cursor.close()
        return corals

    def intersect_with_mangroves(self, wkt, crs=4326) -> bool:
        """
        vegetation.mangroves
        Args:
            wkt: str
            crs: int

        Returns:
            bool:
        """

        query = f"""SELECT EXISTS(
                    SELECT 1 
                    FROM vegetation.mangroves
                    WHERE ST_Intersects(geom, ST_GeomFromText(\'{wkt}\', {crs}))
                )"""
        with self.connection:
            cursor = self.connection.cursor()
            cursor.execute(query)
            mangroves = cursor.fetchone()[0]
            cursor.close()
        return mangroves

    def intersect_with_saltmarshes(self, wkt, crs=4326) -> str:
        """
        vegetation.saltmarshes
        Args:
            wkt: str
            crs: int
            db_epsg :

        Returns:
            Any:
        """

        query = f"""SELECT EXISTS(
                    SELECT 1 
                    FROM vegetation.saltmarshes
                    WHERE ST_Intersects(geom, ST_GeomFromText(\'{wkt}\', {crs}))
                )"""
        with self.connection:
            cursor = self.connection.cursor()
            cursor.execute(query)
            saltmarshes = cursor.fetchone()[0]
            cursor.close()
        return saltmarshes

    def get_wave_exposure_value(self, wkt, crs=4326, dist=1.5):
        """ocean.wave_exposure
        values to expect from database:
            exposed
            moderately exposed
            Protected
        """

        query = f"""SELECT ts_exposure
                    FROM ocean.wave_exposure 
                    WHERE ST_DWithin(geom, 
                        ST_GeomFromText(\'{wkt}\', {crs}), {dist}) 
                    ORDER BY ST_Distance(geom, 
                                        ST_GeomFromText(\'{wkt}\', {crs})) 
                    LIMIT 1;"""
        with self.connection:
            cursor = self.connection.cursor()
            cursor.execute(query)
            wave_exposure = cursor.fetchone()[0]
            cursor.close()
        return wave_exposure

    def get_tidal_range_values(self, wkt, crs=4326, dist=1.5):
        """ocean.tidal_range
        values to expect:
        micro
        meso
        macro

        """

        query = f"""SELECT exposure
                    FROM ocean.tidal_range 
                    WHERE ST_DWithin(geom, 
                        ST_GeomFromText(\'{wkt}\', {crs}), {dist}) 
                    ORDER BY ST_Distance(geom, 
                                        ST_GeomFromText(\'{wkt}\', {crs})) 
                    LIMIT 1;"""
        with self.connection:
            cursor = self.connection.cursor()
            cursor.execute(query)
            tidal_range = cursor.fetchone()[0]
            cursor.close()
        return tidal_range

    def get_sediment_changerate_values(self, wkt, crs=4326, dist=1):
        """coast.sediment
        values to expect:
        float
        """

        query = f"""SELECT changerate
                    FROM coast.sediment 
                    WHERE ST_DWithin(geom, 
                        ST_GeomFromText(\'{wkt}\', {crs}), {dist}) 
                    ORDER BY ST_Distance(geom, 
                                        ST_GeomFromText(\'{wkt}\', {crs})) 
                    LIMIT 1;"""
        cursor = self.connection.cursor()
        try:
            cursor.execute(query)
            change_rate = cursor.fetchone()[0]
        except Exception:
            change_rate = None
        cursor.close()
        return change_rate

    def get_shorelinechange_values(self, wkt, crs=4326, dist=1):
        """coast.shorelinechange
        values to expect:
        float
        """

        query = f"""SELECT change
                    FROM coast.shorelinechange 
                    WHERE ST_DWithin(geom, 
                        ST_GeomFromText(\'{wkt}\', {crs}), {dist}) 
                    ORDER BY ST_Distance(geom, 
                                        ST_GeomFromText(\'{wkt}\', {crs})) 
                    LIMIT 1;"""

        cursor = self.connection.cursor()
        try:
            cursor.execute(query)
            change = cursor.fetchone()[0]
        except Exception:
            change = None
        cursor.close()
        return change

    def get_cyclone_risk(self, wkt, crs=4326, dist=1):
        """ocean.shorelinechange
        values to expect:
        Yes
        No
        """

        query = f"""SELECT bcyclone
                    FROM ocean.diva_points_with_cyclone_risk 
                    WHERE ST_DWithin(geom, 
                        ST_GeomFromText(\'{wkt}\', {crs}), {dist}) 
                    ORDER BY ST_Distance(geom, 
                                        ST_GeomFromText(\'{wkt}\', {crs})) 
                    LIMIT 1;"""
        with self.connection:
            cursor = self.connection.cursor()
            cursor.execute(query)
            cyclone_risk = cursor.fetchone()[0]
            cursor.close()
        return cyclone_risk

    def fetch_closest_coasts(self, wkt, crs=4326):
        """coast.osm_segment1000m
        values to expect: coasts ids

        Args:
            wkt :
            crs : Defaults to 4326.

        Returns:
            coast line ids
        """
        # extend line for searching for closest coasts
        query = f"""SELECT gid
                FROM coast.osm_segment1000m
                WHERE ST_Intersects(geom, ST_GeomFromText(\'{wkt}\', {crs}))"""  # LINESTRING wkt
        with self.connection:
            cursor = self.connection.cursor()
            cursor.execute(query)
            # coast_lines = cursor.fetchall()
            coast_lines = [r[0] for r in cursor.fetchall()]
            cursor.close()
        return coast_lines

    def get_classes(
        self,
        geological_layout: str,
        wave_exposure: str,
        tidal_range: str,
        flora_fauna: str,
        sediment_balance: str,
        storm_climate: str,
    ):
        query = f"""SELECT code, ecosystem_disruption, gradual_inundation, salt_water_intrusion, erosion, flooding
                    FROM chw.decision_wheel
                    WHERE geological_layout = '{geological_layout}' and
                        '{wave_exposure}' = ANY(wave_exposure) and
                        '{tidal_range}' = ANY(tidal_range) and
                        '{flora_fauna}' = ANY(flora_fauna) and
                        '{sediment_balance}' = ANY(sediment_balance) and
                        '{storm_climate}' = ANY(storm_climate);"""
        with self.connection:
            cursor = self.connection.cursor()
            cursor.execute(query)
            classes = cursor.fetchone()
            cursor.close()
        return classes

    def get_measures(self, code):
        query = f""" SELECT opt.hazard, array_agg(opt.managementoption) as measures 
                    FROM 
                    (SELECT h.hid, h.hazard, ms.managementoption
                    FROM management.managementoptions mo JOIN management.hazards h on mo.hid = h.hid
                    JOIN management.measures ms on ms.mid = mo.mid
                    WHERE code = '{code}') as opt
                    GROUP BY opt.hazard;"""
        with self.connection:
            cursor = self.connection.cursor()
            cursor.execute(query)
            measures = cursor.fetchall()
            cursor.close()
        return measures

    def area_not_supported(self, wkt, crs=4326):
        """coast.osm_landpolygon
        Args:
            wkt: str
            crs: int


        Returns:
            bool: True if point in a land polygon, false if not
        """
        query = f"""
                    SELECT 'Please choose a point in sea'
                    FROM coast.osm_landpolygon
                    WHERE ST_Contains(geom, ST_GeomFromText(\'{wkt}\', {crs}))
                    UNION
                    SELECT 'This is a special case and CHW methodology does not yield a coastal classification'
                    FROM coast.excludedregions
                    WHERE st_contains(geom,st_transform(ST_GeomFromText(\'{wkt}\', {crs}),3857));"""
        with self.connection:
            try:
                cursor = self.connection.cursor()
                cursor.execute(query)
                non_supported = cursor.fetchone()[0]
                cursor.close()
            except:
                non_supported = False
        return non_supported

    def ST_line_extend(self, wkt, dist=0, crs=4326, direction=-180):
        """Extends the transect based on a given dist, to either 180 or -180 direction

        Args:
            wkt: Input line at eps
            dist :  Defaults to 0 . to be extended to.
            crs : Crs of the transect. Defaults to 4326.
            direction :  -180 to be extended in the sea, 180 to be extended in land.

        Returns:
            line: extended line. Start point coast, End point either sea or land.
        """
        transect = f"ST_GeomFromText('{wkt}', {crs})"
        P1 = f"ST_StartPoint({transect})"
        P2 = f"ST_EndPoint({transect})"
        if direction == -180:
            azimuth = f"ST_Azimuth({P2}::geometry,{P1}::geometry)"
        elif direction == 180:
            azimuth = f"ST_Azimuth({P1}::geometry,{P2}::geometry)"

        extension_length = dist
        projection = f"ST_Project({P1}, {extension_length}, {azimuth})"

        query = f"SELECT ST_AsText(ST_MakeLine({P1}::geometry, {projection}::geometry))"
        with self.connection:
            cursor = self.connection.cursor()
            cursor.execute(query)
            line = cursor.fetchone()[0]
            cursor.close()
        return line

    # wkt = transect
    def closest_point_of_coastline(self, wkt, crs=4326):

        """Find the closest point of the coastline from the given point of the user
           Returns also the coastline id.

        Returns:
           Closets point and coastline id
           #NOTE the coastline id is returned from the create_transect process and
           # is an input at the coastal_hazard_wheel process in order to correct accuracy errors during fetch

           #NOTE Replace osm_coastline with osm_segment1000m (sometimes during fetch one coastline was so
           # long resulting to same id during extension)
        """

        query = f"""SELECT ST_AsText(ST_ClosestPoint(closest_line.geom, ST_GeomFromText(\'{wkt}\', {crs}))), gid            
                    FROM (SELECT *
                    FROM coast.osm_segment1000m
                    WHERE ST_DWithin(geom, ST_GeomFromText(\'{wkt}\', {crs}), 1)
                    ORDER BY ST_Distance(geom, ST_GeomFromText(\'{wkt}\', {crs})) LIMIT 1) AS closest_line;
                """
        with self.connection:
            cursor = self.connection.cursor()
            cursor.execute(query)
            point, coastline_id = cursor.fetchall()[0]
            cursor.close()
        return point, coastline_id

    def create_transect_in_coast(self, point_on_sea, point_on_coast, dist, crs=4326):

        P1 = f"ST_GeomFromText('{point_on_sea}', {crs})"
        P2 = f"ST_GeomFromText('{point_on_coast}', {crs})"

        azimuth = f"ST_Azimuth({P1}::geometry,{P2}::geometry)"

        projection = f"ST_Project({P2}, {dist}, {azimuth})"

        query = f"SELECT ST_AsText(ST_MakeLine({P2}::geometry, {projection}::geometry))"
        with self.connection:
            cursor = self.connection.cursor()
            cursor.execute(query)
            transect = cursor.fetchone()[0]
            cursor.close()
        return transect

    def get_gar_pop_values(self, wkt, crs=4326, dist=1):
        """gar.gar
        values to expect from database:
            number
        """

        query = f"""SELECT tot_val,tot_pob
                    FROM gar.gar 
                    WHERE ST_DWithin(wkb_geometry, 
                        ST_GeomFromText(\'{wkt}\', {crs}), {dist}) 
                    ORDER BY ST_Distance(wkb_geometry, 
                                        ST_GeomFromText(\'{wkt}\', {crs})) 
                    LIMIT 1;"""
        with self.connection:
            cursor = self.connection.cursor()
            cursor.execute(query)
            tot = cursor.fetchone()
            gar = float(tot[0])
            pop = float(tot[1])
            cursor.close()
        return int(gar), int(pop)  # round(self.slope, 1)

    def intersect_with_osm_beaches(self, wkt, crs=4326) -> str:
        """
        coast.osm_beach
        Args:
            wkt :
            crs :
            db_epsg :

        Returns:
            Any:
        """

        query = f"""SELECT EXISTS(
                    SELECT 1 
                    FROM coast.osm_beach
                    WHERE ST_Intersects(geom, ST_GeomFromText(\'{wkt}\', {crs}))
                )"""
        # With the with keyword, Python automatically releases the resources. It also provides error handling.
        with self.connection:
            cursor = self.connection.cursor()
            cursor.execute(query)
            beach = cursor.fetchone()[0]
            cursor.close()
        return beach

    def get_closest_geology_glim(self, wkt, crs=4326, db_crs=3857, dist=25000):
        """
        check for closest geology glim values from
        the database table geollayout.glim
        in a buffer of 15000m

        Get values in a buffer, sort them by distance
        and gets the closest one.

        """

        query = f"""SELECT xx
                    FROM geollayout.glim 
                    WHERE ST_DWithin(shape, 
                        ST_Transform(ST_GeomFromText(\'{wkt}\', {crs}), {db_crs}), {dist}) 
                    ORDER BY ST_Distance(shape, 
                                        ST_Transform(ST_GeomFromText(\'{wkt}\', {crs}), {db_crs})) 
                    LIMIT 1;"""
        cursor = self.connection.cursor()
        try:
            cursor.execute(query)
            glim = cursor.fetchone()[0]

        except Exception:
            glim = None
        cursor.close()
        return glim

    def get_geol_glim_values(self, wkt, crs=4326, db_crs=3857) -> List[str]:
        """Connects to the chw2 database and gets the
        'su' type where the wkt intersects
        NOTE: sediment plain, sloping soft rock, flat hard rock, sloping hard rock
        NOTE: geollayout.glim -- Global lithological map database v1.0
        Args:
            wkt:str
            crs:int
            db_crs:int
        """

        query = f"""SELECT xx 
                FROM geollayout.glim
                WHERE ST_Intersects(shape, ST_Transform(ST_GeomFromText(\'{wkt}\', {crs}), {db_crs}))
                """
        cursor = self.connection.cursor()
        cursor.execute(query)
        geology_values = cursor.fetchall()
        cursor.close()
        return geology_values

    def get_geology_value(self, wkt, crs=4326, db_crs=3857, dist=25000):
        """
        check for closest geology glim values from
        the database table geollayout.glim
        in a buffer of 15000m

        Get values in a buffer, sort them by distance
        and gets the closest one.
        """
        query = f"""
        SELECT
            CASE
                WHEN ((SELECT count(*)
                        FROM geollayout.fluvisols
                        WHERE ST_Intersects(geom, ST_GeomFromText(\'{wkt}\', {crs}))) != 0 )
        THEN 'fluvisol'
        ELSE (SELECT xx as glim
              FROM geollayout.glim
              WHERE ST_DWithin(shape, 
                        ST_Transform(ST_GeomFromText(\'{wkt}\', {crs}), {db_crs}), {dist})
                        AND xx NOT IN ('wb', 'nd')
              ORDER BY ST_Distance(shape,
                ST_Transform(ST_GeomFromText(\'{wkt}\', {crs}), {db_crs}))
              LIMIT 1) 
        END
        """
        with self.connection:
            cursor = self.connection.cursor()
            cursor.execute(query)
            geology = cursor.fetchone()[0]
            cursor.close()

        return geology

    def intersect_with_island(self, wkt, crs=4326):
        """coast.usgs_islands
        Args:
            wkt (str):
            crs (int):


        Returns:
            bool: True if intersects, false if not
        """

        query = f"""SELECT EXISTS(
                    SELECT 1 
                    FROM coast.usgs_islands
                    WHERE ST_Intersects(wkb_geometry, ST_GeomFromText(\'{wkt}\', {crs})) 
                )"""
        with self.connection:
            cursor = self.connection.cursor()
            cursor.execute(query)
            island = cursor.fetchone()[0]
            cursor.close()
        return island

    def intersect_with_small_island(self, wkt, crs=4326):
        """coast.usgs_islands
        the small island is defined as an island with area < 25km2
        Args:
            wkt :
            crs :

        Returns:
            bool: True if intersects, false if not
        """

        query = f"""SELECT EXISTS(
                    SELECT 1 
                    FROM coast.usgs_islands
                    WHERE ST_Intersects(wkb_geometry, ST_GeomFromText(\'{wkt}\', {crs})) and islandarea < 25
                )"""
        with self.connection:
            cursor = self.connection.cursor()
            cursor.execute(query)
            small_island = cursor.fetchone()[0]
            cursor.close()
        return small_island

    def intersect_with_barriers_sandspits(self, wkt, crs=4326):
        """coast.barriers_sandspits
        Args:
            wkt (str): Transect
            crs (int): crs of transect, default to 4326

        Returns:
            bool: True if intersects, false if not
        """

        query = f"""SELECT EXISTS(
                    SELECT 1 
                    FROM coast.barriers_sandspits
                    WHERE ST_Intersects(geom, ST_GeomFromText(\'{wkt}\', {crs})) 
                )"""
        with self.connection:
            cursor = self.connection.cursor()
            cursor.execute(query)
            barriers_sandspits = cursor.fetchone()[0]
            cursor.close()
        return barriers_sandspits
