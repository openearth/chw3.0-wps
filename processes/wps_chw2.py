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

#
#
#
# PyWPS

# http://localhost:5000/wps?request=GetCapabilities&service=WPS&version=1.0.0
# http://localhost:5000/wps?request=DescribeProcess&service=WPS&version=1.0.0&Identifier=chw2_risk_classification


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
import time


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

            line_str = request.inputs["transect"][0].data
            line_geojson = geojson.loads(line_str)

            chw = CHW(line_geojson)

            # 1st level check
            chw.get_info_geological_layout()
            # 2nd level check
            chw.get_info_wave_exposure()
            # 3rd level check
            chw.get_info_tidal_range()
            # 4th level check
            chw.get_info_flora_fauna()
            # 5th level check
            chw.get_info_sediment_balance()
            # 6th level check
            chw.get_info_storm_climate()

        except Exception:
            msg = "Failed during retrieving the information"
            res = {"errMsg": msg}
            response.outputs["output_json"].data = json.dumps(res)

        try:

            # classify hazards according to coastalhazardwheel decision tree
            chw.hazards_classification()
            # get measures
            chw.provide_measures()
            # get risk information for the transect
            chw.get_risk_info()
            # translate numbers 1,2,3,4 to low,
            chw.translate_hazard_danger()
        except Exception:
            msg = "Something went wrong during the classification"
            res = {"errMsg": msg}
            response.outputs["output_json"].data = json.dumps(res)

        try:

            output = write_output(chw)
            response.outputs["output_json"].data = json.dumps(output)

        except Exception:
            msg = "Failed to write the output"
            res = {"errMsg": msg}
            response.outputs["output_json"].data = json.dumps(res)
