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
from pathlib import Path
import tempfile


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


def translate_hazard_danger(hazard):
    if hazard != "None":
        if hazard == 1:
            hazard = "Low"
        elif hazard == 2:
            hazard = "Moderate"
        elif hazard == 3:
            hazard = "High"
        elif hazard == 4:
            hazard = "Very High"
    return hazard


def write_output(chw):
    output = [
        {
            "title": "Hazards",
            "info": [
                {
                    "title": "CHW information layers",
                    "info": {
                        "Geological layout": chw.geological_layout,
                        "Wave exposure": chw.wave_exposure.capitalize(),
                        "Tidal range": chw.tidal_range.capitalize(),
                        "Flora fauna": chw.flora_fauna,
                        "Sediment balance": chw.sediment_balance,
                        "Storm climate": chw.storm_climate,
                        "slope": chw.slope,
                    },
                },
                {
                    "title": "Coastal environment",
                    "info": {
                        "code": chw.code,
                        "Ecosystem disruption": chw.ecosystem_disruption,
                        "Gradual inundation": chw.gradual_inundation,
                        "Salt water intrusion": chw.salt_water_intrusion,
                        "Erosion": chw.erosion,
                        "Flooding": chw.flooding,
                    },
                },
            ],
        },
        {
            "title": "Risk",
            "info": [
                {
                    "title": "Risk",
                    "info": {
                        "Distance to measurement point": "No data",
                        "Population": chw.population,
                        "Capital stock at closest GAR point": chw.gar,
                        "Key roads within 100m of the coast": "No data",
                    },
                }
            ],
        },
        {
            "title": "Measures",
            "info": [
                {
                    "title": "Measures for Ecosystem disruption",
                    "measures": chw.ecosystem_disruption_measures,
                },
                {
                    "title": "Measures for Gradual inundation",
                    "measures": chw.gradual_inundation_measures,
                },
                {
                    "title": "Measures for Salt water intrusion",
                    "measures": chw.salt_water_intrusion_measures,
                },
                {"title": "Measures for Erosion", "measures": chw.erosion_measures},
                {"title": "Measures for Flooding", "measures": chw.flooding_measures},
            ],
        },
    ]
    return output
