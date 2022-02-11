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


# $Abstract: Creates a 500m transectfrom a point in the sea to the closest line$
#
# PyWPS

# http://localhost:5000/wps?request=GetCapabilities&service=WPS&version=1.0.0
# http://localhost:5000/wps?request=DescribeProcess&service=WPS&version=1.0.0&Identifier=chw_transect
#

from pywps import Process, Format
from pywps.inout.inputs import ComplexInput, LiteralInput
from pywps.inout.outputs import ComplexOutput
from pywps.app.Common import Metadata

import json
import geojson

from .utils import read_config
from .db_utils import DB
from .vector_utils import geojson_to_wkt, wkt_geometry


class WpsCreateTransect(Process):
    def __init__(self):
        # Input [in json format ]
        inputs = [
            ComplexInput(
                identifier="sea_point",
                title="sea_point",
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
            title="Creates a transect 500 m inland from the coastline.",
            abstract="""Creates a transect 500 m inland from the closest point of the coastline, of a point in the sea. Checks also if the given point is 
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
            host, user, password, db, _, _, _, _ = read_config()
            db = DB(user, password, host, db)

            # Read input
            sea_point_as_str = request.inputs["sea_point"][0].data
            # load geojson
            sea_point_as_geojson = geojson.loads(sea_point_as_str)
            sea_point_as_wkt = geojson_to_wkt(sea_point_as_geojson)
            # Checks if the point is inside a land polygon, if yes then it returns a message
            proceed, notification = db.find_special_areas(sea_point_as_wkt)

            if proceed is False:
                output = {"errMsg": notification}
                response.outputs["output_json"].data = json.dumps(output)
            else:
                coastline_point, coastline_id = db.closest_point_of_coastline(
                    sea_point_as_wkt
                )
                transect = db.create_transect_in_coast(
                    sea_point_as_wkt, coastline_point, 500
                )
                # prepare the output. Send the transect as a geosjon.
                geom = wkt_geometry(transect)
                output = {
                    "transect_coordinates": geom["coordinates"],
                    "coastline_id": coastline_id,
                    "notification": notification,
                }
                response.outputs["output_json"].data = json.dumps(output)

        except Exception:
            msg = "Please click closer to the coast"
            res = {"errMsg": msg}
            response.outputs["output_json"].data = json.dumps(res)
