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

import configparser

import psycopg2
from typing import List
import geojson
from shapely.geometry import shape
from pathlib import Path
import tempfile
from jinja2 import Environment, PackageLoader, FileSystemLoader
import json

service_path = Path(__file__).resolve().parent


def read_config() -> tuple:
    """Reads the configuration file
    Returns:
        List with configuration
    """
    cf_file = service_path / "configuration.txt"
    cf = configparser.RawConfigParser()
    cf.read(cf_file)
    # POSTGIS
    host = cf.get("PostGIS", "host")
    user = cf.get("PostGIS", "user")
    psword = cf.get("PostGIS", "pass")
    db = cf.get("PostGIS", "db")
    port = cf.get("PostGIS", "port")
    # GeoServer
    ows_url = cf.get("GeoServer", "ows_url")
    dem = cf.get("GeoServer", "dem")
    landuse = cf.get("GeoServer", "landuse")
    return host, user, psword, db, port, ows_url, dem, landuse


def create_temp_dir(dir):
    # Temporary folder setup
    tmpdir = tempfile.mkdtemp(dir=dir)
    return tmpdir


def write_output(chw):
    p = Path(__file__).parent.parent / "static"
    env = Environment(loader=FileSystemLoader(Path(p)))
    template = env.get_template("output_template.json")
    output = template.render(chw=chw)
    return json.loads(output)