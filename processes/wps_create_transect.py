# -*- coding: utf-8 -*-
# Copyright notice
#   --------------------------------------------------------------------
#   Copyright (C) 2020 Deltares
#       Gerrit Hendriksen, Ioanna Micha
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

# $HeadURL: https://svn.oss.deltares.nl/repos/openearthtools/trunk/python/applications/wps/ri2de/processes/wps_ri2de_slope.py $
# $Keywords: $
# http://localhost:5000/wps?request=Execute&service=WPS&identifier=ra2ce_calc_ratio&version=1.0.0&datainputs=layer_name=plasvorming;json_matrix={"values":[[1,1,3,1,1],[1,1,4,1,1],[1,1,5,1,1],[1,1,2,1,1],[1,1,1,1,5]]}
# PyWPS

# http://localhost:5000/wps?request=GetCapabilities&service=WPS&version=1.0.0
# http://localhost:5000/wps?request=DescribeProcess&service=WPS&version=1.0.0&Identifier=chw_transect
# http://localhost:5000/wps?request=Execute&service=WPS&identifier=chw_transect&version=1.0.0&datainputs=wktline=LINESTRING(-76.254%209.325,-75.876%209.041)

from pywps import Process, Format
from pywps.inout.inputs import ComplexInput, LiteralInput
from pywps.inout.outputs import ComplexOutput
from pywps.app.Common import Metadata

import json
import geojson

from .utils import read_config
from .db_utils import DB
from .vector_utils import geojson_to_wkt, wkt_geometry, change_coords


class WpsCreateTransect(Process):
    def __init__(self):
        # Input [in json format ]
        inputs = [
            ComplexInput(
                identifier="point",
                title="point",
                supported_formats=[Format("application/json")],
                abstract="Complex input abstract",
            )
        ]

        # Output [in json format]
        outputs = [
            ComplexOutput(
                identifier="output_json",
                title="Perpedicular transect over the coast line",
                supported_formats=[Format("application/json")],
            )
        ]

        super(WpsCreateTransect, self).__init__(
            self._handler,
            identifier="create_transect",
            version="1.0",
            title="Create perpedicular transect on a coast line",
            abstract="""Creates perpedicular line on a coast line from a given point. Checks also if the given point is 
            in the sea or on the land""",
            profile="",
            metadata=[
                Metadata("WpsCreateTransect"),
                Metadata("create_transect"),
            ],
            inputs=inputs,
            outputs=outputs,
            store_supported=False,
            status_supported=False,
        )

    def _handler(self, request, response):
        """Handler function of the WpsCreateTransect"""

        try:
            host, user, password, db, port, _, _, _ = read_config()
            db = DB(user, password, host, db)

            # Read input
            point_str = request.inputs["point"][0].data
            # load geojson
            point_geojson = geojson.loads(point_str)
            point_wkt = geojson_to_wkt(point_geojson)

            if db.point_in_landpolygon(point_wkt):
                output = {"errMsg": "Please select a point on the sea"}
                response.outputs["output_json"].data = json.dumps(output)
            else:

                transect = db.create_transect_to_coast(point_wkt)
                length = change_coords(transect).length

                # NOTE -180 as the first point is the point on the coast
                transect_extension = db.ST_line_extend(
                    wkt=transect, transect_length=length, dist=1000, direction=-180
                )

                transect_geometry = wkt_geometry(transect_extension)

                output = {"transect_coordinates": transect_geometry["coordinates"]}
                response.outputs["output_json"].data = json.dumps(output)
        except Exception:
            msg = "Something went wrong during processing"
            res = {"errMsg": msg}
            response.outputs["output_json"].data = json.dumps(res)
