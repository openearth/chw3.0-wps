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

from .wcs_utils import LS
import logging
import numpy as np
import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling
from scipy.stats import linregress
from statistics import mean
from pathlib import Path


def cut_wcs(
    xst, yst, xend, yend, layername, owsurl, outfname, crs=4326, all_box=False
) -> str:
    """Implements the GetCoverage request with a given bbox from the user
    Args:
        xst (float): xmin
        yst (float): ymin
        xend (float): xmax
        yend (float): ymax
        layername (string): layername on geoserver
        owsurl (string): ows endpoint
        outfname (string): fname to store retrieved raster
        crs (int, optional): Defaults to 4326.
        all_box (bool, optional): Defaults to False.
    """
    linestr = "LINESTRING ({} {}, {} {})".format(xst, yst, xend, yend)
    ls = LS(linestr, crs, owsurl, layername)
    ls.line()
    ls.getraster(outfname, all_box=all_box)
    ls = None
    logging.info("Writing: {}".format(outfname))
    return outfname


def reproject_raster(infname, outfname, dst_crs="EPSG:3857"):
    """Tranforms a raster to another epsg, writes the new raster in the temp

    Args:
        in_file (str, optional): [description]. Defaults to "temp".
        dst_crs (str, optional): [description]. Defaults to "EPSG:3857".
        out_file (str, optional): [description]. Defaults to "temp".
    """

    with rasterio.open(infname) as src:
        transform, width, height = calculate_default_transform(
            src.crs, dst_crs, src.width, src.height, *src.bounds
        )
        kwargs = src.meta.copy()
        kwargs.update(
            {"crs": dst_crs, "transform": transform, "width": width, "height": height}
        )
        with rasterio.open(outfname, "w", **kwargs) as dst:
            for i in range(1, src.count + 1):
                reproject(
                    source=rasterio.band(src, i),
                    destination=rasterio.band(dst, i),
                    src_transform=src.transform,
                    src_crs=src.crs,
                    dst_transform=transform,
                    dst_crs=dst_crs,
                    resampling=Resampling.nearest,
                )


# line in epsg: 3857 as shapely object
# line_length


def line_segmentation(line, line_length, step):
    """Returns the transect in segments

    Args:
        line ([type]): [description]
        line_length ([type]): [description]
        step ([type]): [description]

    Returns:
        [type]: [description]
    """
    segments = [segment for segment in range(0, int(line_length), step)]

    points = tuple(
        map(
            lambda segment: (line.interpolate(segment).x, line.interpolate(segment).y),
            segments,
        )
    )
    return segments, points


def get_landuse_profile(landuse, line, line_length, temp, step=300):
    """Returns landuse values over the transect with a step equal to the size of the raster

    Args:
        landuse
        line
        line_length
        outfname
        step (int, optional);

    Returns:
        landuse_values, segments
    """
    reproject_fname = Path(temp) / "landuse_3857.tif"
    segments, points = line_segmentation(line, line_length, step)
    reproject_raster(landuse, reproject_fname)

    # sample raster
    with rasterio.open(reproject_fname) as dst:
        values = dst.sample(points, 1, True)
        landuse_values = [value[0] for value in values]
        return landuse_values, segments


def get_elevation_profile(dem, line, line_length, outfname, step=30):
    """Returns elevation values over the transect with a step eqaul to the size of the raster

    Args:
        dem
        line
        line_length
        outfname
        step (int, optional):

    Returns:
        elevations, segments
    """

    segments, points = line_segmentation(line, line_length, step)
    # reproject raster
    reproject_raster(dem, outfname)

    # sample raster
    with rasterio.open(outfname) as dst:
        values = dst.sample(points, 1, True)
        elevations = [value[0] for value in values]
        return elevations, segments


def detect_pattern(searchval, array):
    pattern = (array[:-1] == searchval[0]) & (array[1:] == searchval[1])
    return pattern


def calc_slope(
    elevations,
    segments,
):
    # print("elev", elevations, segments)
    try:
        # Replace nan with 0
        y = np.array(elevations)
        y = np.nan_to_num(y)

        x = np.array(segments)
        # inland500 = (np.argwhere(x < 500).shape)[0]
        # print("inalnd", inland500)
        # print("insland500", inland500)

        # x = x[:inland500]
        # print("x", x)
        # y = y[:inland500]
        # print("y", y)
        # slope of every segment
        m = np.diff(y) / np.diff(x)
        # print("m", m)

        # detect change of slope (negative to positive and reverse)
        msign = np.sign(m)
        slope_patterns = np.array(
            [
                any(pattern)
                for pattern in zip(
                    detect_pattern([0, 1], msign),
                    detect_pattern([1, -1], msign),
                    detect_pattern([-1, 1], msign),
                    detect_pattern([-1, 0], msign),
                    detect_pattern([1, 0], msign),
                )
            ]
        )

        indeces = np.where(slope_patterns == True)[0] + 2
        slopes = []
        indeces_start = indeces - 1
        loops = len(indeces) + 1
        indeces_end = indeces

        for i in range(loops):
            if i == 0:
                elevations = y[: indeces_end[i]]
                distances = x[: indeces_end[i]]
                a = linregress(distances, elevations)
                slopes.append(a.slope)
            elif i == len(indeces):
                elevations = y[indeces_start[i - 1] :]
                distances = x[indeces_start[i - 1] :]
                a = linregress(distances, elevations)
                slopes.append(a.slope)
            else:
                elevations = y[indeces_start[i - 1] : indeces_end[i]]
                distances = x[indeces_start[i - 1] : indeces_end[i]]
                a = linregress(distances, elevations)
                slopes.append(a.slope)

        slopes = [abs(slope * 100) for slope in slopes]
        mean_slope = mean(slopes)
        max_slope = max(slopes)
    except Exception:
        logging.info("slope is 0 along the line")
        mean_slope = 0.00
        max_slope = 0.00

    return mean_slope, max_slope


def detect_sea_patterns(landuse_values):
    # The globcover dataset is very coarse dataset (300m)
    # We want alwasy the first point of the transect to be on the sea
    if landuse_values[0] != 210:
        landuse_values[0] = 210
    # print("land_use before pattern", [i for i in landuse_values])
    landuse_array = np.array(landuse_values)
    landuse_array = np.where(landuse_array == 210, "sea", "land")
    # print("land_use after np where", [i for i in landuse_array])

    sea_land_pattern = detect_pattern(["sea", "land"], landuse_array)
    land_sea_pattern = detect_pattern(["land", "sea"], landuse_array)

    return sea_land_pattern, land_sea_pattern


def read_raster_values(file):
    with rasterio.open(file) as dataset:
        values = dataset.read(1)
        return values


def mean_elevation(dem):
    values = read_raster_values(dem)
    values = np.where(values == -9999, 0, values)
    return np.mean(values)
