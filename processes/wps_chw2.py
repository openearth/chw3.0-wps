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

import time
import json
import logging
import geojson
from pathlib import Path

from .db_utils import close_db_connection
from .chw_utils import CHW
from .utils import write_output


class WpsChw20(Process):
    def __init__(self):
        # Input [in json format ]
        inputs = [
            ComplexInput(
                identifier="transect",
                title="transect",
                supported_formats=[Format("application/json")],
                abstract="Complex input abstract",
            )
        ]

        # Output [in json format]
        outputs = [
            ComplexOutput(
                identifier="output_json",
                title="Output of the CoastaHazardWheel",
                supported_formats=[Format("application/json")],
            )
        ]

        super(WpsChw20, self).__init__(
            self._handler,
            identifier="chw2_risk_classification",
            version="2.0",
            title="Risk classification of a coastline.",
            abstract="""CHW App derives an indication of the risk based on the Coastal Hazard Wheel methodoloyg. A user drawn profile is the 
                        trigger to derive data from global datasets and re-classifies this data to classes that are input for a process that follows the CHW approach to classify the potenital risk of a coast line.""",
            profile="",
            metadata=[Metadata("WpsChw2_0"), Metadata("Chw2_0/risk_classification")],
            inputs=inputs,
            outputs=outputs,
            store_supported=False,
            status_supported=False,
        )

    def _handler(self, request, response):
        """Handler function of the WpsChw2"""
        # try:

        # Read input
        line_str = request.inputs["transect"][0].data
        # load geojson
        line_geojson = geojson.loads(line_str)
        # Initiate chw object
        chw = CHW(line_geojson)
        # 1st level check
        chw.get_info_geological_layout()
        # 2nd level check
        chw.get_info_wave_exposure()
        # 3rd level check
        chw.get_info_tida_range()
        # 4th level check
        chw.get_info_flora_fauna()
        # 5th level check
        chw.get_info_sediment_balance()
        # 6th level check
        chw.get_info_storm_climate()

        # classify hazards according to coastalhazardwheel decision tree
        chw.hazards_classification()
        # get proposed measures
        chw.provide_measures()

        output = write_output(chw)
        response.outputs["output_json"].data = json.dumps(output)

        # close_db_connection()
        # except Exception as e:
        # res = {"errMsg": "ERROR: {}".format(e)}
        # response.outputs["output_json"].data = json.dumps(res)
        # return response
