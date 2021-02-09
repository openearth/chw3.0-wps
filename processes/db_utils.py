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

# host, user, password, db, port, _, _, _ = read_config()
# connection = psycopg2.connect(user=user, password=password, host=host, database=db)
# cursor = connection.cursor()


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
                    WHERE ST_Intersects(geom, ST_GeomFromText(\'{wkt}\', {crs}))
                )"""
        cursor = self.connection.cursor()
        cursor.execute(query)
        estuaries = cursor.fetchone()[0]
        cursor.close()
        return estuaries

    def intersect_with_corals(self, wkt, crs=4326) -> bool:
        """vegetation.corals
        Args:
            wkt (str): [description]
            crs (int): [description]


        Returns:
            bool: True if intersects, false if not
        """

        query = f"""SELECT EXISTS(
                    SELECT 1 
                    FROM vegetation.corals
                    WHERE ST_Intersects(geom, ST_GeomFromText(\'{wkt}\', {crs}))
                )"""
        cursor = self.connection.cursor()
        cursor.execute(query)
        corals = cursor.fetchone()[0]
        cursor.close()
        print("---Intersect with corals is -->", corals)
        return corals

    def intersect_with_mangroves(self, wkt, crs=4326) -> bool:
        """
        vegetation.mangroves
        Args:
            wkt ([type]): [description]
            crs ([type]): [description]

        Returns:
            bool: [description]
        """

        query = f"""SELECT EXISTS(
                    SELECT 1 
                    FROM vegetation.mangroves
                    WHERE ST_Intersects(geom, ST_GeomFromText(\'{wkt}\', {crs}))
                )"""
        cursor = self.connection.cursor()
        cursor.execute(query)
        mangroves = cursor.fetchone()[0]
        cursor.close()
        return mangroves

    def intersect_with_saltmarshes(self, wkt, crs=4326) -> str:
        """
        vegetation.saltmarshes
        Args:
            wkt ([type]): [description]
            crs ([type]): [description]
            db_epsg ([type]): [description]

        Returns:
            Any: [description]
        """

        query = f"""SELECT EXISTS(
                    SELECT 1 
                    FROM vegetation.saltmarshes
                    WHERE ST_Intersects(geom, ST_GeomFromText(\'{wkt}\', {crs}))
                )"""
        cursor = self.connection.cursor()
        cursor.execute(query)
        saltmarshes = cursor.fetchone()[0]
        cursor.close()
        return saltmarshes

    def get_wave_exposure_value(self, wkt, crs=4326, dist=1):
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
        cursor = self.connection.cursor()
        cursor.execute(query)
        wave_exposure = cursor.fetchone()[0]
        cursor.close()
        return wave_exposure

    def get_tidal_range_values(self, wkt, crs=4326, dist=1):
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
        cursor = self.connection.cursor()

        cursor.execute(query)
        print("---GET cyclone reisk query", query)
        cyclone_risk = cursor.fetchone()[0]
        # print("cyclone_risk", cyclone_risk)
        cursor.close()
        return cyclone_risk

    def fetch_closest_coasts(self, wkt, crs=4326):
        """coast.osm_coastline
        values to expect: coasts ids

        Args:
            wkt ([type]): [description]
            crs (int, optional): [description]. Defaults to 4326.

        Returns:
            [type]: [description]
        """
        # extend line for searching for closest coasts
        query = f"""SELECT gid
                FROM coast.osm_coastline
                WHERE ST_Intersects(geom, ST_GeomFromText(\'{wkt}\', {crs}))"""  # LINESTRING wkt
        cursor = self.connection.cursor()
        cursor.execute(query)
        coast_lines = cursor.fetchall()
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
        logging.info(
            f"""geological_layout:{geological_layout}
            wave_exposure: {wave_exposure}
            tidal_range: {tidal_range}
            flora_fauna: {flora_fauna}
            sediment_balance: {sediment_balance}
            storm_climate: {storm_climate}"""
        )
        query = f"""SELECT code, ecosystem_disruption, gradual_inundation, salt_water_intrusion, erosion, flooding
                    FROM chw.decision_wheel
                    WHERE geological_layout = '{geological_layout}' and
                        '{wave_exposure}' = ANY(wave_exposure) and
                        '{tidal_range}' = ANY(tidal_range) and
                        '{flora_fauna}' = ANY(flora_fauna) and
                        '{sediment_balance}' = ANY(sediment_balance) and
                        '{storm_climate}' = ANY(storm_climate);"""

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
        cursor = self.connection.cursor()
        cursor.execute(query)
        measures = cursor.fetchall()
        cursor.close()
        return measures

    def point_in_landpolygon(self, wkt, crs=4326):
        """coast.osm_landpolygon
        Args:
            wkt: str
            crs: int


        Returns:
            bool: True if point in a land polygon, false if not
        """

        query = f"""SELECT EXISTS(
                    SELECT 1
                    FROM coast.osm_landpolygon
                    WHERE ST_Contains(geom, ST_GeomFromText(\'{wkt}\', {crs}))
                );"""
        cursor = self.connection.cursor()
        cursor.execute(query)
        point_inland = cursor.fetchone()[0]
        cursor.close()
        return point_inland

    def create_transect_to_coast(self, wkt, crs=4326):
        """coast.osm_landpolygon
        Args:
            wkt: str
            crs: int


        Returns:
            line: GeoJson
        """
        query = f"""SELECT ST_AsText(ST_MakeLine(
                           ST_ClosestPoint(closest_line.geom, ST_GeomFromText(\'{wkt}\', {crs})),
                                           ST_GeomFromText(\'{wkt}\', {crs})))
                    FROM (SELECT geom
                    FROM coast.osm_coastline
                    WHERE ST_DWithin(geom, ST_GeomFromText(\'{wkt}\', {crs}), 1)
                    ORDER BY ST_Distance(geom, ST_GeomFromText(\'{wkt}\', {crs})) LIMIT 1) AS closest_line;
                """
        cursor = self.connection.cursor()
        cursor.execute(query)
        transect = cursor.fetchone()[0]
        cursor.close()
        return transect

    def ST_line_extend(
        self, wkt, transect_length=0, P=False, dist=0, crs=4326, direction=-180
    ):
        """Extends the transect based on a given length, to either 180 or -180 direction

        Args:
            wkt
            transect_length (int, optional): [description]. Defaults to 0.
            P (bool, optional): [description]. Defaults to False.
            dist (int, optional): [description]. Defaults to 0.
            crs (int, optional): [description]. Defaults to 4326.
            direction (int, optional): [description]. Defaults to -180.

        Returns:
            [type]: [description]
        """
        transect = f"ST_GeomFromText('{wkt}', {crs})"
        if direction == -180:

            P1 = f"ST_EndPoint({transect})"
            P2 = f"ST_StartPoint({transect})"
            azimuth = f"ST_Azimuth({P1}::geometry,{P2}::geometry)"
            if P:
                P1 = f"ST_GeomFromText('{P}', {crs})"

            extension_length = transect_length + dist
            projection = f"ST_Project({P1}, {extension_length}, {azimuth})"

            query = (
                f"SELECT ST_AsText(ST_MakeLine({P1}::geometry, {projection}::geometry))"
            )

        elif direction == 180:
            P1 = f"ST_StartPoint({transect})"
            P2 = f"ST_EndPoint({transect})"
            azimuth = f"ST_Azimuth({P1}::geometry,{P2}::geometry)"

            if P:
                P1 = f"ST_GeomFromText('{P}', {crs})"

            extension_length = transect_length + dist
            projection = f"ST_Project({P1}, {extension_length}, {azimuth})"

            query = (
                f"SELECT ST_AsText(ST_MakeLine({P1}::geometry, {projection}::geometry))"
            )

        cursor = self.connection.cursor()
        cursor.execute(query)
        line = cursor.fetchone()[0]
        cursor.close()
        return line

    # wkt = transect
    def point_on_coast(self, wkt, crs=4326):

        """"""
        query = f"""SELECT ST_AsText(ST_ClosestPoint(closest_line.geom, ST_GeomFromText(\'{wkt}\', {crs})))            
                    FROM (SELECT geom
                    FROM coast.osm_coastline
                    WHERE ST_DWithin(geom, ST_GeomFromText(\'{wkt}\', {crs}), 1)
                    ORDER BY ST_Distance(geom, ST_GeomFromText(\'{wkt}\', {crs})) LIMIT 1) AS closest_line;
                """

        cursor = self.connection.cursor()
        cursor.execute(query)
        point = cursor.fetchone()[0]
        cursor.close()
        return point

    def create_coast_transect(self, point_on_sea, point_on_coast, dist, crs=4326):

        P1 = f"ST_GeomFromText('{point_on_sea}', {crs})"
        P2 = f"ST_GeomFromText('{point_on_coast}', {crs})"

        azimuth = f"ST_Azimuth({P1}::geometry,{P2}::geometry)"

        projection = f"ST_Project({P2}, {dist}, {azimuth})"

        query = f"SELECT ST_AsText(ST_MakeLine({P2}::geometry, {projection}::geometry))"
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
        cursor = self.connection.cursor()
        cursor.execute(query)
        tot = cursor.fetchone()
        gar = float(tot[0])
        pop = float(tot[1])
        cursor.close()
        return gar, pop

    def intersect_with_osm_beaches(self, wkt, crs=4326) -> str:
        """
        coast.osm_beach
        Args:
            wkt ([type]): [description]
            crs ([type]): [description]
            db_epsg ([type]): [description]

        Returns:
            Any: [description]
        """

        query = f"""SELECT EXISTS(
                    SELECT 1 
                    FROM coast.osm_beach
                    WHERE ST_Intersects(geom, ST_GeomFromText(\'{wkt}\', {crs}))
                )"""
        print("--- INTERSECT WITH OSM BEACHES QUERY", query)
        cursor = self.connection.cursor()
        cursor.execute(query)
        beach = cursor.fetchone()[0]
        print("BEACH", beach)
        cursor.close()
        return beach

    # TODO get rid of this function? Intersect with osm beach polygons the new one.
    def get_beach_value(self, wkt, crs=4326, dist=1):
        """coast.shorelinechange
        values to expect from database:
            boolean
        """
        query = f"""SELECT flag_sandy
                    FROM coast.shorelinechange 
                    WHERE ST_DWithin(geom, 
                        ST_GeomFromText(\'{wkt}\', {crs}), {dist}) 
                    ORDER BY ST_Distance(geom, 
                                        ST_GeomFromText(\'{wkt}\', {crs})) 
                    LIMIT 1;"""
        cursor = self.connection.cursor()
        cursor.execute(query)
        beach = cursor.fetchone()[0]
        cursor.close()
        return beach

    def get_closest_geology_glim(self, wkt, crs=4326, db_crs=3857, dist=15000):
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

    def intersect_with_island(self, wkt, crs=4326):
        """coast.usgs_islands
        Args:
            wkt (str): [description]
            crs (int): [description]


        Returns:
            bool: True if intersects, false if not
        """

        query = f"""SELECT EXISTS(
                    SELECT 1 
                    FROM coast.usgs_islands
                    WHERE ST_Intersects(wkb_geometry, ST_GeomFromText(\'{wkt}\', {crs}))
                )"""
        print("INTERSECTS WITH ISLANDS QUERY")
        cursor = self.connection.cursor()
        cursor.execute(query)
        island = cursor.fetchone()[0]
        print("intersect with island:", island)
        cursor.close()
        return island
