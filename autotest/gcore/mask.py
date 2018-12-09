#!/usr/bin/env python
###############################################################################
# $Id$
#
# Project:  GDAL/OGR Test Suite
# Purpose:  Test RFC 15 "mask band" default functionality (nodata/alpha/etc)
# Author:   Frank Warmerdam <warmerdam@pobox.com>
#
###############################################################################
# Copyright (c) 2007, Frank Warmerdam <warmerdam@pobox.com>
# Copyright (c) 2008-2012, Even Rouault <even dot rouault at mines-paris dot org>
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
# OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.
###############################################################################

import os
import sys


import gdaltest
from osgeo import gdal
import pytest

###############################################################################
# Verify the checksum and flags for "all valid" case.


def test_mask_1():

    ds = gdal.Open('data/byte.tif')

    assert ds is not None, 'Failed to open test dataset.'

    band = ds.GetRasterBand(1)

    assert band.GetMaskFlags() == gdal.GMF_ALL_VALID, 'Did not get expected mask.'

    cs = band.GetMaskBand().Checksum()
    assert cs == 4873, 'Got wrong mask checksum'

    my_min, my_max, mean, stddev = band.GetMaskBand().ComputeStatistics(0)
    assert (my_min, my_max, mean, stddev) == (255, 255, 255, 0), 'Got wrong mask stats'

    return 'success'

###############################################################################
# Verify the checksum and flags for "nodata" case.


def test_mask_2():

    ds = gdal.Open('data/byte.vrt')

    assert ds is not None, 'Failed to open test dataset.'

    band = ds.GetRasterBand(1)

    assert band.GetMaskFlags() == gdal.GMF_NODATA, 'Did not get expected mask.'

    cs = band.GetMaskBand().Checksum()
    assert cs == 4209, 'Got wrong mask checksum'

    return 'success'

###############################################################################
# Verify the checksum and flags for "alpha" case.


def test_mask_3():

    ds = gdal.Open('data/stefan_full_rgba.png')

    assert ds is not None, 'Failed to open test dataset.'

    # Test first mask.

    band = ds.GetRasterBand(1)

    assert band.GetMaskFlags() == gdal.GMF_ALPHA + gdal.GMF_PER_DATASET, \
        'Did not get expected mask.'

    cs = band.GetMaskBand().Checksum()
    assert cs == 10807, 'Got wrong mask checksum'

    # Verify second and third same as first.

    band_2 = ds.GetRasterBand(2)
    band_3 = ds.GetRasterBand(3)

    # We have commented the following tests as SWIG >= 1.3.37 is buggy !
    #  or str(band_2.GetMaskBand()) != str(band.GetMaskBand()) \
    #   or str(band_3.GetMaskBand()) != str(band.GetMaskBand())
    assert band_2.GetMaskFlags() == band.GetMaskFlags() and band_3.GetMaskFlags() == band.GetMaskFlags(), \
        'Band 2 or 3 does not seem to match first mask'

    # Verify alpha has no mask.
    band = ds.GetRasterBand(4)
    assert band.GetMaskFlags() == gdal.GMF_ALL_VALID, \
        'Did not get expected mask for alpha.'

    cs = band.GetMaskBand().Checksum()
    assert cs == 36074, 'Got wrong alpha mask checksum'

    return 'success'

###############################################################################
# Copy a *real* masked dataset, and confirm masks copied properly.


def test_mask_4():

    src_ds = gdal.Open('../gdrivers/data/masked.jpg')

    assert src_ds is not None, 'Failed to open test dataset.'

    # NOTE: for now we copy to PNM since it does everything (overviews too)
    # externally. Should eventually test with gtiff, hfa.
    drv = gdal.GetDriverByName('PNM')
    ds = drv.CreateCopy('tmp/mask_4.pnm', src_ds)
    src_ds = None

    # confirm we got the custom mask on the copied dataset.
    assert ds.GetRasterBand(1).GetMaskFlags() == gdal.GMF_PER_DATASET, \
        'did not get expected mask flags'

    msk = ds.GetRasterBand(1).GetMaskBand()
    cs = msk.Checksum()
    expected_cs = 770

    assert cs == expected_cs, 'Did not get expected checksum'

    msk = None
    ds = None

    return 'success'

###############################################################################
# Create overviews for masked file, and verify the overviews have proper
# masks built for them.


def test_mask_5():

    # This crashes with libtiff 3.8.2, so skip it
    md = gdal.GetDriverByName('GTiff').GetMetadata()
    if md['DMD_CREATIONOPTIONLIST'].find('BigTIFF') == -1:
        pytest.skip()

    ds = gdal.Open('tmp/mask_4.pnm', gdal.GA_Update)

    assert ds is not None, 'Failed to open test dataset.'

    # So that we instantiate the mask band before.
    ds.GetRasterBand(1).GetMaskFlags()

    ds.BuildOverviews(overviewlist=[2, 4])

    # confirm mask flags on overview.
    ovr = ds.GetRasterBand(1).GetOverview(1)

    assert ovr.GetMaskFlags() == gdal.GMF_PER_DATASET, 'did not get expected mask flags'

    msk = ovr.GetMaskBand()
    cs = msk.Checksum()
    expected_cs = 20505

    assert cs == expected_cs, 'Did not get expected checksum'
    ovr = None
    msk = None
    ds = None

    # Reopen and confirm we still get same results.
    ds = gdal.Open('tmp/mask_4.pnm')

    # confirm mask flags on overview.
    ovr = ds.GetRasterBand(1).GetOverview(1)

    assert ovr.GetMaskFlags() == gdal.GMF_PER_DATASET, 'did not get expected mask flags'

    msk = ovr.GetMaskBand()
    cs = msk.Checksum()
    expected_cs = 20505

    assert cs == expected_cs, 'Did not get expected checksum'

    ovr = None
    msk = None
    ds = None

    gdal.GetDriverByName('PNM').Delete('tmp/mask_4.pnm')

    return 'success'

###############################################################################
# Test a TIFF file with 1 band and an embedded mask of 1 bit


def test_mask_6():

    gdal.SetConfigOption('GDAL_TIFF_INTERNAL_MASK_TO_8BIT', 'FALSE')
    ds = gdal.Open('data/test_with_mask_1bit.tif')

    assert ds is not None, 'Failed to open test dataset.'

    band = ds.GetRasterBand(1)

    assert band.GetMaskFlags() == gdal.GMF_PER_DATASET, 'Did not get expected mask.'

    cs = band.GetMaskBand().Checksum()
    assert cs == 100, 'Got wrong mask checksum'

    gdal.SetConfigOption('GDAL_TIFF_INTERNAL_MASK_TO_8BIT', 'TRUE')

    return 'success'

###############################################################################
# Test a TIFF file with 3 bands and an embedded mask of 1 band of 1 bit


def test_mask_7():

    gdal.SetConfigOption('GDAL_TIFF_INTERNAL_MASK_TO_8BIT', 'FALSE')
    ds = gdal.Open('data/test3_with_1mask_1bit.tif')

    assert ds is not None, 'Failed to open test dataset.'

    for i in (1, 2, 3):
        band = ds.GetRasterBand(i)

        assert band.GetMaskFlags() == gdal.GMF_PER_DATASET, 'Did not get expected mask.'

        cs = band.GetMaskBand().Checksum()
        assert cs == 100, 'Got wrong mask checksum'

    gdal.SetConfigOption('GDAL_TIFF_INTERNAL_MASK_TO_8BIT', 'TRUE')

    return 'success'

###############################################################################
# Test a TIFF file with 1 band and an embedded mask of 8 bit.
# Note : The TIFF6 specification, page 37, only allows 1 BitsPerSample && 1 SamplesPerPixel,


def test_mask_8():

    ds = gdal.Open('data/test_with_mask_8bit.tif')

    assert ds is not None, 'Failed to open test dataset.'

    band = ds.GetRasterBand(1)

    assert band.GetMaskFlags() == gdal.GMF_PER_DATASET, 'Did not get expected mask.'

    cs = band.GetMaskBand().Checksum()
    assert cs == 1222, 'Got wrong mask checksum'

    return 'success'

###############################################################################
# Test a TIFF file with 3 bands with an embedded mask of 1 bit with 3 bands.
# Note : The TIFF6 specification, page 37, only allows 1 BitsPerSample && 1 SamplesPerPixel,


def test_mask_9():

    ds = gdal.Open('data/test3_with_mask_1bit.tif')

    assert ds is not None, 'Failed to open test dataset.'

    for i in (1, 2, 3):
        band = ds.GetRasterBand(i)

        assert band.GetMaskFlags() == 0, 'Did not get expected mask.'

        cs = band.GetMaskBand().Checksum()
        assert cs == 100, 'Got wrong mask checksum'

    return 'success'

###############################################################################
# Test a TIFF file with 3 bands with an embedded mask of 8 bit with 3 bands.
# Note : The TIFF6 specification, page 37, only allows 1 BitsPerSample && 1 SamplesPerPixel,


def test_mask_10():

    ds = gdal.Open('data/test3_with_mask_8bit.tif')

    assert ds is not None, 'Failed to open test dataset.'

    for i in (1, 2, 3):
        band = ds.GetRasterBand(i)

        assert band.GetMaskFlags() == 0, 'Did not get expected mask.'

        cs = band.GetMaskBand().Checksum()
        assert cs == 1222, 'Got wrong mask checksum'

    return 'success'

###############################################################################
# Test a TIFF file with an overview, an embedded mask of 1 bit, and an embedded
# mask for the overview


def test_mask_11():

    gdal.SetConfigOption('GDAL_TIFF_INTERNAL_MASK_TO_8BIT', 'FALSE')
    ds = gdal.Open('data/test_with_mask_1bit_and_ovr.tif')

    assert ds is not None, 'Failed to open test dataset.'

    band = ds.GetRasterBand(1)

    # Let's fetch the mask
    assert band.GetMaskFlags() == gdal.GMF_PER_DATASET, 'Did not get expected mask.'

    cs = band.GetMaskBand().Checksum()
    assert cs == 100, 'Got wrong mask checksum'

    # Let's fetch the overview
    band = ds.GetRasterBand(1).GetOverview(0)
    cs = band.Checksum()
    assert cs == 1126, 'Got wrong overview checksum'

    # Let's fetch the mask of the overview
    assert band.GetMaskFlags() == gdal.GMF_PER_DATASET, 'Did not get expected mask.'

    cs = band.GetMaskBand().Checksum()
    assert cs == 25, 'Got wrong checksum for the mask of the overview'

    # Let's fetch the overview of the mask == the mask of the overview
    band = ds.GetRasterBand(1).GetMaskBand().GetOverview(0)
    cs = band.Checksum()
    assert cs == 25, 'Got wrong checksum for the overview of the mask'

    gdal.SetConfigOption('GDAL_TIFF_INTERNAL_MASK_TO_8BIT', 'TRUE')

    return 'success'


###############################################################################
# Test a TIFF file with 3 bands, an overview, an embedded mask of 1 bit, and an embedded
# mask for the overview

def test_mask_12():

    gdal.SetConfigOption('GDAL_TIFF_INTERNAL_MASK_TO_8BIT', 'FALSE')
    ds = gdal.Open('data/test3_with_mask_1bit_and_ovr.tif')

    assert ds is not None, 'Failed to open test dataset.'

    for i in (1, 2, 3):
        band = ds.GetRasterBand(i)

        # Let's fetch the mask
        assert band.GetMaskFlags() == gdal.GMF_PER_DATASET, 'Did not get expected mask.'

        cs = band.GetMaskBand().Checksum()
        assert cs == 100, 'Got wrong mask checksum'

        # Let's fetch the overview
        band = ds.GetRasterBand(i).GetOverview(0)
        cs = band.Checksum()
        assert cs == 1126, 'Got wrong overview checksum'

        # Let's fetch the mask of the overview
        assert band.GetMaskFlags() == gdal.GMF_PER_DATASET, 'Did not get expected mask.'

        cs = band.GetMaskBand().Checksum()
        assert cs == 25, 'Got wrong checksum for the mask of the overview'

        # Let's fetch the overview of the mask == the mask of the overview
        band = ds.GetRasterBand(i).GetMaskBand().GetOverview(0)
        cs = band.Checksum()
        assert cs == 25, 'Got wrong checksum for the overview of the mask'

    gdal.SetConfigOption('GDAL_TIFF_INTERNAL_MASK_TO_8BIT', 'TRUE')

    return 'success'

###############################################################################
# Test creation of external TIFF mask band


def test_mask_13():

    gdal.SetConfigOption('GDAL_TIFF_INTERNAL_MASK', 'NO')

    src_ds = gdal.Open('data/byte.tif')

    assert src_ds is not None, 'Failed to open test dataset.'

    drv = gdal.GetDriverByName('GTiff')
    ds = drv.CreateCopy('tmp/byte_with_mask.tif', src_ds)
    src_ds = None

    ds.CreateMaskBand(gdal.GMF_PER_DATASET)

    cs = ds.GetRasterBand(1).GetMaskBand().Checksum()
    assert cs == 0, 'Got wrong checksum for the mask'

    ds.GetRasterBand(1).GetMaskBand().Fill(1)

    cs = ds.GetRasterBand(1).GetMaskBand().Checksum()
    assert cs == 400, 'Got wrong checksum for the mask'

    ds = None

    try:
        os.stat('tmp/byte_with_mask.tif.msk')
    except OSError:
        pytest.fail('tmp/byte_with_mask.tif.msk is absent')

    ds = gdal.Open('tmp/byte_with_mask.tif')

    assert ds.GetRasterBand(1).GetMaskFlags() == gdal.GMF_PER_DATASET, \
        'wrong mask flags'

    cs = ds.GetRasterBand(1).GetMaskBand().Checksum()
    assert cs == 400, 'Got wrong checksum for the mask'

    ds = None

    drv.Delete('tmp/byte_with_mask.tif')

    try:
        os.stat('tmp/byte_with_mask.tif.msk')
        pytest.fail('tmp/byte_with_mask.tif.msk is still there')
    except OSError:
        pass

    return 'success'

###############################################################################
# Test creation of internal TIFF mask band


def test_mask_14():

    src_ds = gdal.Open('data/byte.tif')

    assert src_ds is not None, 'Failed to open test dataset.'

    drv = gdal.GetDriverByName('GTiff')
    gdal.SetConfigOption('GDAL_TIFF_INTERNAL_MASK_TO_8BIT', 'FALSE')
    ds = drv.CreateCopy('tmp/byte_with_mask.tif', src_ds)
    gdal.SetConfigOption('GDAL_TIFF_INTERNAL_MASK_TO_8BIT', 'TRUE')
    src_ds = None

    # The only flag value supported for internal mask is GMF_PER_DATASET
    with gdaltest.error_handler():
        with gdaltest.config_option('GDAL_TIFF_INTERNAL_MASK', 'YES'):
            ret = ds.CreateMaskBand(0)
    assert ret != 0, 'Error expected'

    with gdaltest.config_option('GDAL_TIFF_INTERNAL_MASK', 'YES'):
        ret = ds.CreateMaskBand(gdal.GMF_PER_DATASET)
    assert ret == 0, 'Creation failed'

    cs = ds.GetRasterBand(1).GetMaskBand().Checksum()
    assert cs == 0, 'Got wrong checksum for the mask (1)'

    ds.GetRasterBand(1).GetMaskBand().Fill(1)

    cs = ds.GetRasterBand(1).GetMaskBand().Checksum()
    assert cs == 400, 'Got wrong checksum for the mask (2)'

    # This TIFF dataset has already an internal mask band
    with gdaltest.error_handler():
        with gdaltest.config_option('GDAL_TIFF_INTERNAL_MASK', 'YES'):
            ret = ds.CreateMaskBand(gdal.GMF_PER_DATASET)
    assert ret != 0, 'Error expected'

    # This TIFF dataset has already an internal mask band
    with gdaltest.error_handler():
        with gdaltest.config_option('GDAL_TIFF_INTERNAL_MASK', 'YES'):
            ret = ds.GetRasterBand(1).CreateMaskBand(gdal.GMF_PER_DATASET)
    assert ret != 0, 'Error expected'

    ds = None

    try:
        os.stat('tmp/byte_with_mask.tif.msk')
        pytest.fail('tmp/byte_with_mask.tif.msk should not exist')
    except OSError:
        pass

    gdal.SetConfigOption('GDAL_TIFF_INTERNAL_MASK_TO_8BIT', 'FALSE')
    ds = gdal.Open('tmp/byte_with_mask.tif')

    assert ds.GetRasterBand(1).GetMaskFlags() == gdal.GMF_PER_DATASET, \
        'wrong mask flags'

    gdal.SetConfigOption('GDAL_TIFF_INTERNAL_MASK_TO_8BIT', 'TRUE')

    cs = ds.GetRasterBand(1).GetMaskBand().Checksum()
    assert cs == 400, 'Got wrong checksum for the mask (3)'

    # Test fix for #5884
    gdal.SetConfigOption('GDAL_TIFF_INTERNAL_MASK', 'YES')
    old_val = gdal.GetCacheMax()
    gdal.SetCacheMax(0)
    out_ds = drv.CreateCopy('/vsimem/byte_with_mask.tif', ds, options=['COMPRESS=JPEG'])
    gdal.SetConfigOption('GDAL_TIFF_INTERNAL_MASK', None)
    gdal.SetCacheMax(old_val)
    assert out_ds.GetRasterBand(1).Checksum() != 0
    cs = ds.GetRasterBand(1).GetMaskBand().Checksum()
    assert cs == 400, 'Got wrong checksum for the mask (4)'
    out_ds = None
    drv.Delete('/vsimem/byte_with_mask.tif')

    ds = None

    drv.Delete('tmp/byte_with_mask.tif')

    return 'success'

###############################################################################
# Test creation of internal TIFF overview, mask band and mask band of overview


def mask_and_ovr(order, method):

    src_ds = gdal.Open('data/byte.tif')

    assert src_ds is not None, 'Failed to open test dataset.'

    drv = gdal.GetDriverByName('GTiff')
    ds = drv.CreateCopy('tmp/byte_with_ovr_and_mask.tif', src_ds)
    src_ds = None

    if order == 1:
        gdal.SetConfigOption('GDAL_TIFF_INTERNAL_MASK', 'YES')
        ds.CreateMaskBand(gdal.GMF_PER_DATASET)
        gdal.SetConfigOption('GDAL_TIFF_INTERNAL_MASK', 'NO')
        ds.BuildOverviews(method, overviewlist=[2, 4])
        gdal.SetConfigOption('GDAL_TIFF_INTERNAL_MASK', 'YES')
        ds.GetRasterBand(1).GetOverview(0).CreateMaskBand(gdal.GMF_PER_DATASET)
        ds.GetRasterBand(1).GetOverview(1).CreateMaskBand(gdal.GMF_PER_DATASET)
        gdal.SetConfigOption('GDAL_TIFF_INTERNAL_MASK', 'NO')
    elif order == 2:
        gdal.SetConfigOption('GDAL_TIFF_INTERNAL_MASK', 'YES')
        ds.BuildOverviews(method, overviewlist=[2, 4])
        ds.CreateMaskBand(gdal.GMF_PER_DATASET)
        ds.GetRasterBand(1).GetOverview(0).CreateMaskBand(gdal.GMF_PER_DATASET)
        ds.GetRasterBand(1).GetOverview(1).CreateMaskBand(gdal.GMF_PER_DATASET)
        gdal.SetConfigOption('GDAL_TIFF_INTERNAL_MASK', 'NO')
    elif order == 3:
        gdal.SetConfigOption('GDAL_TIFF_INTERNAL_MASK', 'YES')
        ds.BuildOverviews(method, overviewlist=[2, 4])
        ds.GetRasterBand(1).GetOverview(0).CreateMaskBand(gdal.GMF_PER_DATASET)
        ds.GetRasterBand(1).GetOverview(1).CreateMaskBand(gdal.GMF_PER_DATASET)
        ds.CreateMaskBand(gdal.GMF_PER_DATASET)
        gdal.SetConfigOption('GDAL_TIFF_INTERNAL_MASK', 'NO')
    elif order == 4:
        gdal.SetConfigOption('GDAL_TIFF_INTERNAL_MASK', 'YES')
        ds.CreateMaskBand(gdal.GMF_PER_DATASET)
        ds.GetRasterBand(1).GetMaskBand().Fill(1)
        # The overview for the mask will be implicitly created and computed.
        ds.BuildOverviews(method, overviewlist=[2, 4])
        gdal.SetConfigOption('GDAL_TIFF_INTERNAL_MASK', 'NO')

    if order < 4:
        ds = None
        ds = gdal.Open('tmp/byte_with_ovr_and_mask.tif', gdal.GA_Update)
        ds.GetRasterBand(1).GetMaskBand().Fill(1)
        # The overview of the mask will be implicitly recomputed.
        ds.BuildOverviews(method, overviewlist=[2, 4])

    ds = None

    try:
        os.stat('tmp/byte_with_ovr_and_mask.tif.msk')
        pytest.fail('tmp/byte_with_mask.tif.msk should not exist')
    except OSError:
        pass

    gdal.SetConfigOption('GDAL_TIFF_INTERNAL_MASK_TO_8BIT', 'FALSE')
    ds = gdal.Open('tmp/byte_with_ovr_and_mask.tif')

    assert ds.GetRasterBand(1).GetMaskFlags() == gdal.GMF_PER_DATASET, \
        'wrong mask flags'

    gdal.SetConfigOption('GDAL_TIFF_INTERNAL_MASK_TO_8BIT', 'TRUE')

    cs = ds.GetRasterBand(1).GetMaskBand().Checksum()
    assert cs == 400, 'Got wrong checksum for the mask'

    cs = ds.GetRasterBand(1).GetOverview(0).GetMaskBand().Checksum()
    assert cs == 100, 'Got wrong checksum for the mask of the first overview'

    cs = ds.GetRasterBand(1).GetOverview(1).GetMaskBand().Checksum()
    assert cs == 25, 'Got wrong checksum for the mask of the second overview'

    ds = None

    drv.Delete('tmp/byte_with_ovr_and_mask.tif')

    return 'success'


def test_mask_15():
    return mask_and_ovr(1, 'NEAREST')


def test_mask_16():
    return mask_and_ovr(2, 'NEAREST')


def test_mask_17():
    return mask_and_ovr(3, 'NEAREST')


def test_mask_18():
    return mask_and_ovr(4, 'NEAREST')


def test_mask_15_avg():
    return mask_and_ovr(1, 'AVERAGE')


def test_mask_16_avg():
    return mask_and_ovr(2, 'AVERAGE')


def test_mask_17_avg():
    return mask_and_ovr(3, 'AVERAGE')


def test_mask_18_avg():
    return mask_and_ovr(4, 'AVERAGE')

###############################################################################
# Test NODATA_VALUES mask


def test_mask_19():

    ds = gdal.Open('data/test_nodatavalues.tif')

    assert ds is not None, 'Failed to open test dataset.'

    assert ds.GetRasterBand(1).GetMaskFlags() == gdal.GMF_PER_DATASET + gdal.GMF_NODATA, \
        'did not get expected mask flags'

    msk = ds.GetRasterBand(1).GetMaskBand()
    cs = msk.Checksum()
    expected_cs = 11043

    assert cs == expected_cs, 'Did not get expected checksum'

    msk = None
    ds = None

    return 'success'

###############################################################################
# Extensive test of nodata mask for all data types


def test_mask_20():

    types = [gdal.GDT_Byte, gdal.GDT_Int16, gdal.GDT_UInt16,
             gdal.GDT_Int32, gdal.GDT_UInt32, gdal.GDT_Float32, gdal.GDT_Float64,
             gdal.GDT_CFloat32, gdal.GDT_CFloat64]

    nodatavalue = [1, -1, 1, -1, 1, 0.5, 0.5, 0.5, 0.5]

    drv = gdal.GetDriverByName('GTiff')
    for i, typ in enumerate(types):
        ds = drv.Create('tmp/mask20.tif', 1, 1, 1, typ)
        ds.GetRasterBand(1).Fill(nodatavalue[i])
        ds.GetRasterBand(1).SetNoDataValue(nodatavalue[i])

        assert ds.GetRasterBand(1).GetMaskFlags() == gdal.GMF_NODATA, \
            ('did not get expected mask flags for type %s' % gdal.GetDataTypeName(typ))

        msk = ds.GetRasterBand(1).GetMaskBand()
        assert msk.Checksum() == 0, \
            ('did not get expected mask checksum for type %s : %d' % gdal.GetDataTypeName(typ, msk.Checksum()))

        msk = None
        ds = None
        drv.Delete('tmp/mask20.tif')

    return 'success'

###############################################################################
# Extensive test of NODATA_VALUES mask for all data types


def test_mask_21():

    types = [gdal.GDT_Byte, gdal.GDT_Int16, gdal.GDT_UInt16,
             gdal.GDT_Int32, gdal.GDT_UInt32, gdal.GDT_Float32, gdal.GDT_Float64,
             gdal.GDT_CFloat32, gdal.GDT_CFloat64]

    nodatavalue = [1, -1, 1, -1, 1, 0.5, 0.5, 0.5, 0.5]

    drv = gdal.GetDriverByName('GTiff')
    for i, typ in enumerate(types):
        ds = drv.Create('tmp/mask21.tif', 1, 1, 3, typ)
        md = {}
        md['NODATA_VALUES'] = '%f %f %f' % (nodatavalue[i], nodatavalue[i], nodatavalue[i])
        ds.SetMetadata(md)
        ds.GetRasterBand(1).Fill(nodatavalue[i])
        ds.GetRasterBand(2).Fill(nodatavalue[i])
        ds.GetRasterBand(3).Fill(nodatavalue[i])

        assert ds.GetRasterBand(1).GetMaskFlags() == gdal.GMF_PER_DATASET + gdal.GMF_NODATA, \
            ('did not get expected mask flags for type %s' % gdal.GetDataTypeName(typ))

        msk = ds.GetRasterBand(1).GetMaskBand()
        assert msk.Checksum() == 0, \
            ('did not get expected mask checksum for type %s : %d' % gdal.GetDataTypeName(typ, msk.Checksum()))

        msk = None
        ds = None
        drv.Delete('tmp/mask21.tif')

    return 'success'

###############################################################################
# Test creation of external TIFF mask band just after Create()


def test_mask_22():

    drv = gdal.GetDriverByName('GTiff')
    ds = drv.Create('tmp/mask_22.tif', 20, 20)
    ds.CreateMaskBand(gdal.GMF_PER_DATASET)

    cs = ds.GetRasterBand(1).GetMaskBand().Checksum()
    assert cs == 0, 'Got wrong checksum for the mask'

    ds.GetRasterBand(1).GetMaskBand().Fill(1)

    cs = ds.GetRasterBand(1).GetMaskBand().Checksum()
    assert cs == 400, 'Got wrong checksum for the mask'

    ds = None

    try:
        os.stat('tmp/mask_22.tif.msk')
    except OSError:
        pytest.fail('tmp/mask_22.tif.msk is absent')

    ds = gdal.Open('tmp/mask_22.tif')

    assert ds.GetRasterBand(1).GetMaskFlags() == gdal.GMF_PER_DATASET, \
        'wrong mask flags'

    cs = ds.GetRasterBand(1).GetMaskBand().Checksum()
    assert cs == 400, 'Got wrong checksum for the mask'

    ds = None

    drv.Delete('tmp/mask_22.tif')

    try:
        os.stat('tmp/mask_22.tif.msk')
        pytest.fail('tmp/mask_22.tif.msk is still there')
    except OSError:
        pass

    return 'success'

###############################################################################
# Test CreateCopy() of a dataset with a mask into a JPEG-compressed TIFF with
# internal mask (#3800)


def test_mask_23():

    drv = gdal.GetDriverByName('GTiff')
    md = drv.GetMetadata()
    if md['DMD_CREATIONOPTIONLIST'].find('JPEG') == -1:
        pytest.skip()

    src_ds = drv.Create('tmp/mask_23_src.tif', 3000, 2000, 3, options=['TILED=YES', 'SPARSE_OK=YES'])
    src_ds.CreateMaskBand(gdal.GMF_PER_DATASET)

    gdal.SetConfigOption('GDAL_TIFF_INTERNAL_MASK', 'YES')
    old_val = gdal.GetCacheMax()
    gdal.SetCacheMax(15000000)
    gdal.ErrorReset()
    ds = drv.CreateCopy('tmp/mask_23_dst.tif', src_ds, options=['TILED=YES', 'COMPRESS=JPEG'])
    gdal.SetConfigOption('GDAL_TIFF_INTERNAL_MASK', 'NO')
    gdal.SetCacheMax(old_val)

    del ds
    error_msg = gdal.GetLastErrorMsg()
    src_ds = None

    drv.Delete('tmp/mask_23_src.tif')
    drv.Delete('tmp/mask_23_dst.tif')

    # 'ERROR 1: TIFFRewriteDirectory:Error fetching directory count' was triggered before
    assert error_msg == ''

    return 'success'

###############################################################################
# Test on a GDT_UInt16 RGBA (#5692)


def test_mask_24():

    ds = gdal.GetDriverByName('GTiff').Create('/vsimem/mask_24.tif', 100, 100, 4,
                                              gdal.GDT_UInt16, options=['PHOTOMETRIC=RGB', 'ALPHA=YES'])
    ds.GetRasterBand(1).Fill(65565)
    ds.GetRasterBand(2).Fill(65565)
    ds.GetRasterBand(3).Fill(65565)
    ds.GetRasterBand(4).Fill(65565)

    assert ds.GetRasterBand(1).GetMaskFlags() == gdal.GMF_ALPHA + gdal.GMF_PER_DATASET, \
        'Did not get expected mask.'
    mask = ds.GetRasterBand(1).GetMaskBand()

    # IRasterIO() optimized case
    import struct
    assert struct.unpack('B', mask.ReadRaster(0, 0, 1, 1))[0] == 255

    # IReadBlock() code path
    (blockx, blocky) = mask.GetBlockSize()
    assert struct.unpack('B' * blockx * blocky, mask.ReadBlock(0, 0))[0] == 255
    mask.FlushCache()

    # Test special case where dynamics is only 0-255
    ds.GetRasterBand(4).Fill(255)
    assert struct.unpack('B', mask.ReadRaster(0, 0, 1, 1))[0] == 1

    ds = None

    gdal.Unlink('/vsimem/mask_24.tif')

    return 'success'

###############################################################################
# Test various error conditions


def test_mask_25():

    ds = gdal.GetDriverByName('GTiff').Create('/vsimem/mask_25.tif', 1, 1)
    assert ds.GetRasterBand(1).GetMaskFlags() == gdal.GMF_ALL_VALID
    ds = None

    # No INTERNAL_MASK_FLAGS_x metadata
    gdal.GetDriverByName('GTiff').Create('/vsimem/mask_25.tif.msk', 1, 1)
    ds = gdal.Open('/vsimem/mask_25.tif')
    assert ds.GetRasterBand(1).GetMaskFlags() == gdal.GMF_ALL_VALID
    cs = ds.GetRasterBand(1).GetMaskBand().Checksum()
    assert cs == 3
    ds = None
    gdal.Unlink('/vsimem/mask_25.tif')
    gdal.Unlink('/vsimem/mask_25.tif.msk')

    # Per-band mask
    ds = gdal.GetDriverByName('GTiff').Create('/vsimem/mask_25.tif', 1, 1)
    ds.GetRasterBand(1).CreateMaskBand(0)
    ds = None
    ds = gdal.Open('/vsimem/mask_25.tif')
    assert ds.GetRasterBand(1).GetMaskFlags() == 0
    cs = ds.GetRasterBand(1).GetMaskBand().Checksum()
    assert cs == 0
    ds = None
    gdal.Unlink('/vsimem/mask_25.tif')
    gdal.Unlink('/vsimem/mask_25.tif.msk')

    # .msk file does not have enough bands
    gdal.GetDriverByName('GTiff').Create('/vsimem/mask_25.tif', 1, 1, 2)
    ds = gdal.GetDriverByName('GTiff').Create('/vsimem/mask_25.tif.msk', 1, 1)
    ds.SetMetadataItem('INTERNAL_MASK_FLAGS_2', '0')
    ds = None
    ds = gdal.Open('/vsimem/mask_25.tif')
    with gdaltest.error_handler():
        assert ds.GetRasterBand(2).GetMaskFlags() == gdal.GMF_ALL_VALID
    ds = None
    gdal.Unlink('/vsimem/mask_25.tif')
    gdal.Unlink('/vsimem/mask_25.tif.msk')

    # Invalid sequences of CreateMaskBand() calls
    ds = gdal.GetDriverByName('GTiff').Create('/vsimem/mask_25.tif', 1, 1, 2)
    ds.GetRasterBand(1).CreateMaskBand(gdal.GMF_PER_DATASET)
    with gdaltest.error_handler():
        assert ds.GetRasterBand(2).CreateMaskBand(0) != 0
    ds = None
    gdal.Unlink('/vsimem/mask_25.tif')
    gdal.Unlink('/vsimem/mask_25.tif.msk')

    # CreateMaskBand not supported by this dataset
    with gdaltest.error_handler():
        ds = gdal.GetDriverByName('MEM').Create('', 1, 1)
        ds.CreateMaskBand(0)

    return 'success'

###############################################################################
# Test on a GDT_UInt16 1band data


def test_mask_26():

    ds = gdal.GetDriverByName('GTiff').Create('/vsimem/mask_26.tif', 100, 100, 2,
                                              gdal.GDT_UInt16, options=['ALPHA=YES'])
    ds.GetRasterBand(1).Fill(65565)
    ds.GetRasterBand(2).Fill(65565)

    assert ds.GetRasterBand(1).GetMaskFlags() == gdal.GMF_ALPHA + gdal.GMF_PER_DATASET, \
        'Did not get expected mask.'
    mask = ds.GetRasterBand(1).GetMaskBand()

    # IRasterIO() optimized case
    import struct
    assert struct.unpack('B', mask.ReadRaster(0, 0, 1, 1))[0] == 255

    ds = None

    gdal.Unlink('/vsimem/mask_26.tif')

    return 'success'

###############################################################################
# Cleanup.


###############################################################################
# Extensive test of nodata mask for all complex types using real part only


def test_mask_27():

    types = [gdal.GDT_CFloat32, gdal.GDT_CFloat64]

    nodatavalue = [0.5, 0.5]

    drv = gdal.GetDriverByName('GTiff')
    for i, typ in enumerate(types):
        ds = drv.Create('tmp/mask27.tif', 1, 1, 1, typ)
        ds.GetRasterBand(1).Fill(nodatavalue[i], 10)
        ds.GetRasterBand(1).SetNoDataValue(nodatavalue[i])

        assert ds.GetRasterBand(1).GetMaskFlags() == gdal.GMF_NODATA, \
            ('did not get expected mask flags for type %s' % gdal.GetDataTypeName(typ))

        msk = ds.GetRasterBand(1).GetMaskBand()
        assert msk.Checksum() == 0, \
            ('did not get expected mask checksum for type %s : %d' % gdal.GetDataTypeName(typ, msk.Checksum()))

        msk = None
        ds = None
        drv.Delete('tmp/mask27.tif')

    return 'success'

###############################################################################
# Extensive test of real NODATA_VALUES mask for all complex types

gdaltest_list = [
    test_mask_1,
    test_mask_2,
    test_mask_3,
    test_mask_4,
    test_mask_5,
    test_mask_6,
    test_mask_7,
    test_mask_8,
    test_mask_9,
    test_mask_10,
    test_mask_11,
    test_mask_12,
    test_mask_13,
    test_mask_14,
    test_mask_15,
    test_mask_16,
    test_mask_17,
    test_mask_18,
    test_mask_15_avg,
    test_mask_16_avg,
    test_mask_17_avg,
    test_mask_18_avg,
    test_mask_19,
    test_mask_20,
    test_mask_21,
    test_mask_22,
    test_mask_23,
    test_mask_24,
    test_mask_25,
    test_mask_26,
    test_mask_27]

if __name__ == '__main__':

    gdaltest.setup_run('mask')

    gdaltest.run_tests(gdaltest_list)

    sys.exit(gdaltest.summarize())
