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


host, user, password, db, port, _, _, _ = read_config()
connection = psycopg2.connect(user=user, password=password, host=host, database=db)
cursor = connection.cursor()


def close_db_connection():
    if connection:
        connection.close()


def get_geol_glim_values(wkt, crs=4326, db_crs=3857) -> List[str]:
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
    # geology_values = fetch_all(query)
    cursor.execute(query)
    geology_values = cursor.fetchall()

    return geology_values


def intersect_with_estuaries(wkt, crs=4326) -> bool:
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
    cursor.execute(query)
    estuaries = cursor.fetchone()[0]
    return estuaries


def intersect_with_corals(wkt, crs=4326) -> bool:
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
    cursor.execute(query)
    corals = cursor.fetchone()[0]
    return corals


def intersect_with_mangroves(wkt, crs=4326) -> bool:
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
    cursor.execute(query)
    mangroves = cursor.fetchone()[0]
    return mangroves


def intersect_with_saltmarshes(wkt, crs=4326) -> str:
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
    cursor.execute(query)
    saltmarshes = cursor.fetchone()[0]
    return saltmarshes


def get_wave_exposure_value(wkt, crs=4326, dist=100000):
    """ocean.wave_exposure
    values to expect from database:
        exposed
        moderately exposed
        Protected
    """

    query = f"""SELECT ts_exposure
                FROM ocean.wave_exposure 
                WHERE ST_DWithin(geom::geography, 
                      ST_GeomFromText(\'{wkt}\', {crs})::geography, {dist}) 
                ORDER BY ST_Distance(geom::geography, 
                                     ST_GeomFromText(\'{wkt}\', {crs})::geography) 
                LIMIT 1;"""
    cursor.execute(query)
    wave_exposure = cursor.fetchone()[0]
    return wave_exposure


def get_tidal_range_values(wkt, crs=4326, dist=100000):
    """ocean.tidal_range
    values to expect:
    micro
    meso
    macro

    """

    query = f"""SELECT exposure
                FROM ocean.tidal_range 
                WHERE ST_DWithin(geom::geography, 
                      ST_GeomFromText(\'{wkt}\', {crs})::geography, {dist}) 
                ORDER BY ST_Distance(geom::geography, 
                                     ST_GeomFromText(\'{wkt}\', {crs})::geography) 
                LIMIT 1;"""
    cursor.execute(query)
    tidal_range = cursor.fetchone()[0]

    return tidal_range


def get_sediment_changerate_values(wkt, crs=4326, dist=100000):
    """coast.sediment
    values to expect:
    float
    """

    query = f"""SELECT changerate
                FROM coast.sediment 
                WHERE ST_DWithin(geom::geography, 
                      ST_GeomFromText(\'{wkt}\', {crs})::geography, {dist}) 
                ORDER BY ST_Distance(geom::geography, 
                                     ST_GeomFromText(\'{wkt}\', {crs})::geography) 
                LIMIT 1;"""

    cursor.execute(query)
    change_rate = cursor.fetchone()[0]
    return change_rate


def get_shorelinechange_values(wkt, crs=4326, dist=100000):
    """coast.shorelinechange
    values to expect:
    float
    """

    query = f"""SELECT change
                FROM coast.shorelinechange 
                WHERE ST_DWithin(geom::geography, 
                      ST_GeomFromText(\'{wkt}\', {crs})::geography, {dist}) 
                ORDER BY ST_Distance(geom::geography, 
                                     ST_GeomFromText(\'{wkt}\', {crs})::geography) 
                LIMIT 1;"""

    cursor.execute(query)
    change = cursor.fetchone()[0]
    return change


def get_cyclone_risk(wkt, crs=4326, dist=100000):
    """ocea.shorelinechange
    values to expect:
    Yes
    No
    """

    query = f"""SELECT bcyclone
                FROM ocean.diva_points_with_cyclone_risk 
                WHERE ST_DWithin(geom::geography, 
                      ST_GeomFromText(\'{wkt}\', {crs})::geography, {dist}) 
                ORDER BY ST_Distance(geom::geography, 
                                     ST_GeomFromText(\'{wkt}\', {crs})::geography) 
                LIMIT 1;"""

    cursor.execute(query)
    cyclone_risk = cursor.fetchone()[0]
    return cyclone_risk


def get_classes(
    geological_layout,
    wave_exposure,
    tidal_range,
    flora_fauna,
    sediment_balance,
    storm_climate,
):
    query = f"""SELECT code, ecosystem_disruption, gradual_inundation, salt_water_intrusion, erosion, flooding
                FROM chw.decision_wheel
                WHERE geological_layout = '{geological_layout}' and
                      '{wave_exposure}' = ANY(wave_exposure) and
                      '{tidal_range}' = ANY(tidal_range) and
                      '{flora_fauna}' = ANY(flora_fauna) and
                      '{sediment_balance}' = ANY(sediment_balance) and
                      '{storm_climate}' = ANY(storm_climate);"""
    cursor.execute(query)
    classes = cursor.fetchone()
    return classes


def get_measures(code):
    query = f""" SELECT opt.hazard, array_agg(opt.managementoption) as measures 
                  FROM 
                 (SELECT h.hid, h.hazard, ms.managementoption
                  FROM management.managementoptions mo JOIN management.hazards h on mo.hid = h.hid
                  JOIN management.measures ms on ms.mid = mo.mid
                  WHERE code = '{code}') as opt
                  GROUP BY opt.hazard;"""

    cursor.execute(query)
    measures = cursor.fetchall()
    return measures