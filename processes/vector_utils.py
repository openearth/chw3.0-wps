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


from shapely.ops import transform
import pyproj
from pyproj import Proj
from shapely.geometry import shape
import geojson
from shapely import wkt


def get_bounds(line):
    g = shape(line.geometry)
    return g.bounds


def geojson_to_wkt(feature):
    g = shape(feature.geometry)
    return g.wkt


def calc_line_length(line):
    g = shape(line.geometry)
    return g.length


def change_coords(line, epsgin="EPSG:4326", epsgout="EPSG:3857"):
    """Change coordinates of a shapely object

    Args:
        feature ([type]): [description]
        epsgin (str, optional): [description]. Defaults to 'EPSG:3857'.
        epsgout (str, optional): [description]. Defaults to 'EPSG:4326'.

    Returns:
        [type]: [description]
    """
    g = shape(line.geometry)
    pyprojc_object = pyproj.Transformer.from_crs(
        pyproj.CRS(epsgin), pyproj.CRS(epsgout), always_xy=True
    ).transform
    g = transform(pyprojc_object, g)
    return g
