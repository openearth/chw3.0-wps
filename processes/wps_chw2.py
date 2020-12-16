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

from .chw_utils import CHW
from .utils import write_output

logging.basicConfig(level=logging.INFO)


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

        try:
            # Read input
            line_str = request.inputs["transect"][0].data
            # load geojson
            line_geojson = geojson.loads(line_str)
        except Exception:
            msg = "Failed to read the input"
            res = {"errMsg": msg}
            response.outputs["output_json"].data = json.dumps(res)
        try:
            # Initiate chw object
            chw = CHW(line_geojson)
        except Exception:
            msg = "Failed to initiate the CHW"
            res = {"errMsg": msg}
            response.outputs["output_json"].data = json.dumps(res)
        try:
            # 1st level check
            chw.get_info_geological_layout()
            logging.INFO(f"geological_layout:{chw.geological_layout}")
        except Exception:
            msg = "Failed to get information for geological layout"
            res = {"errMsg": msg}
            response.outputs["output_json"].data = json.dumps(res)
        try:
            # 2nd level check
            chw.get_info_wave_exposure()
            logging.INFO(f"wave_exposure:{chw.wave_exposure}")
        except Exception:
            msg = "Failed to get information for wave exposure"
            res = {"errMsg": msg}
            response.outputs["output_json"].data = json.dumps(res)
        try:
            # 3rd level check
            chw.get_info_tida_range()
            logging.INFO(f"tidal_range:{chw.tidal_range}")
        except Exception:
            msg = "Failed to get information tidal range"
            res = {"errMsg": msg}
            response.outputs["output_json"].data = json.dumps(res)
        try:
            # 4th level check
            chw.get_info_flora_fauna()
            logging.INFO(f"flora_fauna:{chw.flora_fauna}")
        except Exception:
            msg = "Failed to get information for flora fauna"
            res = {"errMsg": msg}
            response.outputs["output_json"].data = json.dumps(res)
        try:
            # 5th level check
            chw.get_info_sediment_balance()
            logging.INFO(f"sediment_balance:{chw.sediment_balance}")
        except Exception:
            msg = "Failed to get information for sediment balance"
            res = {"errMsg": msg}
            response.outputs["output_json"].data = json.dumps(res)
        try:
            # 6th level check
            chw.get_info_storm_climate()
            logging.INFO(f"storm_climate:{chw.storm_climate}")
        except Exception:
            msg = "Failed to get information for storm climate"
            res = {"errMsg": msg}
            response.outputs["output_json"].data = json.dumps(res)
        try:
            # classify hazards according to coastalhazardwheel decision tree
            chw.hazards_classification()
        except Exception:
            msg = "Something went wrong during the classification"
            res = {"errMsg": msg}
            response.outputs["output_json"].data = json.dumps(res)
        try:
            # get measures
            chw.provide_measures()
            output = write_output(chw)
            response.outputs["output_json"].data = json.dumps(output)
        except Exception:
            msg = "Failde to provide measures"
            res = {"errMsg": msg}
            response.outputs["output_json"].data = json.dumps(res)
