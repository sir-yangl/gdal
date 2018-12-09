#!/usr/bin/env python
# -*- coding: utf-8 -*-
###############################################################################
# $Id: ogr_sxf.py 26513 2013-10-02 11:59:50Z bishop $
#
# Project:  GDAL/OGR Test Suite
# Purpose:  Test OGR SXF driver functionality.
# Author:   Dmitry Baryshnikov <polimax@mail.ru>
#
###############################################################################
# Copyright (c) 2013, NextGIS
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Library General Public
# License as published by the Free Software Foundation; either
# version 2 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Library General Public License for more details.
#
# You should have received a copy of the GNU Library General Public
# License along with this library; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.
###############################################################################

import sys


import gdaltest
from osgeo import ogr
import pytest

###############################################################################
# Open SXF datasource.


def test_ogr_sxf_1():

    gdaltest.sxf_ds = None
    with gdaltest.error_handler():
        # Expect Warning 0 and Warning 6.
        gdaltest.sxf_ds = ogr.Open('data/100_test.sxf')

    if gdaltest.sxf_ds is not None:
        return 'success'
    pytest.fail()


###############################################################################
# Run test_ogrsf

def test_ogr_sxf_2():

    import test_cli_utilities
    if test_cli_utilities.get_test_ogrsf_path() is None:
        pytest.skip()

    ret = gdaltest.runexternal(test_cli_utilities.get_test_ogrsf_path() + ' data/100_test.sxf')

    assert ret.find('INFO') != -1 and ret.find('ERROR') == -1

    return 'success'

###############################################################################
#


def test_ogr_sxf_cleanup():

    if gdaltest.sxf_ds is None:
        pytest.skip()

    gdaltest.sxf_ds = None

    return 'success'


gdaltest_list = [
    test_ogr_sxf_1,
    test_ogr_sxf_2,
    test_ogr_sxf_cleanup]

if __name__ == '__main__':

    gdaltest.setup_run('ogr_sxf')

    gdaltest.run_tests(gdaltest_list)

    sys.exit(gdaltest.summarize())
