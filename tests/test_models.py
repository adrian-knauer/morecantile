"""Test TileMatrixSet model."""

import json
import os
import random
from collections.abc import Iterable

import pytest
from pydantic import ValidationError
from rasterio.crs import CRS

import morecantile
from morecantile.errors import InvalidIdentifier
from morecantile.models import TileMatrix, TileMatrixSet

from .conftest import gdal_version

data_dir = os.path.join(os.path.dirname(__file__), "../morecantile/data")
tilesets = [
    os.path.join(data_dir, f) for f in os.listdir(data_dir) if f.endswith(".json")
]


@pytest.mark.parametrize("tileset", tilesets)
def test_tile_matrix_set(tileset):
    """Load TileMatrixSet in models."""
    # Confirm model validation is working
    ts = TileMatrixSet.parse_file(tileset)
    # This would fail if `supportedCRS` isn't supported by GDAL/Rasterio
    epsg = ts.crs
    isinstance(epsg, CRS)


def test_tile_matrix_iter():
    """Test iterator"""
    tms = morecantile.tms.get("WebMercatorQuad")
    assert isinstance(tms, Iterable)
    for matrix in tms:
        assert isinstance(matrix, TileMatrix)


def test_tile_matrix_order():
    """Test matrix order"""
    tms = morecantile.tms.get("WebMercatorQuad")
    matrices = tms.tileMatrix[:]
    random.shuffle(matrices)
    tms_ordered = TileMatrixSet(
        title=tms.title,
        identifier=tms.identifier,
        supportedCRS=tms.supportedCRS,
        tileMatrix=matrices,
    )
    # Confirm sort
    assert [matrix.identifier for matrix in tms.tileMatrix] == [
        matrix.identifier for matrix in tms_ordered.tileMatrix
    ]

    # Confirm sort direction
    assert int(tms_ordered.tileMatrix[-1].identifier) > int(
        tms_ordered.tileMatrix[0].identifier
    )


def test_tile_matrix():
    variable_matrix = {
        "type": "TileMatrixType",
        "identifier": "3",
        "scaleDenominator": 34942641.5017948,
        "topLeftCorner": [-180, 90],
        "tileWidth": 256,
        "tileHeight": 256,
        "matrixWidth": 16,
        "matrixHeight": 8,
        "variableMatrixWidth": [
            {
                "type": "VariableMatrixWidthType",
                "coalesce": 2,
                "minTileRow": 0,
                "maxTileRow": 0,
            },
            {
                "type": "VariableMatrixWidthType",
                "coalesce": 2,
                "minTileRow": 3,
                "maxTileRow": 3,
            },
        ],
    }
    with pytest.raises(ValidationError):
        TileMatrix(**variable_matrix)


def test_load():
    """Should raise an error when file not found."""
    with pytest.warns(DeprecationWarning):
        TileMatrixSet.load("WebMercatorQuad")

    with pytest.raises(InvalidIdentifier):
        TileMatrixSet.load("ANotValidName")


def test_findMatrix():
    """Should raise an error when TileMatrix is not found."""
    tms = morecantile.tms.get("WebMercatorQuad")
    m = tms.matrix(0)
    assert m.identifier == "0"

    with pytest.warns(UserWarning):
        tms.matrix(26)


def test_Custom():
    """Create custom TMS grid."""
    tms = morecantile.tms.get("WebMercatorQuad")

    # Web Mercator Extent
    extent = (-20037508.3427892, -20037508.3427892, 20037508.3427892, 20037508.3427892)
    custom_tms = TileMatrixSet.custom(extent, CRS.from_epsg(3857))

    assert tms.tile(20.0, 15.0, 5) == custom_tms.tile(20.0, 15.0, 5)

    wmMat = tms.matrix(5)
    cusMat = custom_tms.matrix(5)
    assert wmMat.matrixWidth == cusMat.matrixWidth
    assert wmMat.matrixHeight == cusMat.matrixHeight
    assert round(wmMat.scaleDenominator, 6) == round(cusMat.scaleDenominator, 6)
    assert round(wmMat.topLeftCorner[0], 6) == round(cusMat.topLeftCorner[0], 6)

    extent = (-180.0, -85.051128779806, 180.0, 85.051128779806)
    custom_tms = TileMatrixSet.custom(
        extent, CRS.from_epsg(3857), extent_crs=CRS.from_epsg(4326)
    )

    assert tms.tile(20.0, 15.0, 5) == custom_tms.tile(20.0, 15.0, 5)

    wmMat = tms.matrix(5)
    cusMat = custom_tms.matrix(5)
    assert wmMat.matrixWidth == cusMat.matrixWidth
    assert wmMat.matrixHeight == cusMat.matrixHeight
    assert round(wmMat.scaleDenominator, 6) == round(cusMat.scaleDenominator, 6)
    assert round(wmMat.topLeftCorner[0], 6) == round(cusMat.topLeftCorner[0], 6)


# Before GDAL3, `morecantile.models.crs_axis_inverted` will always return False for
# CRS defined with `epsg`, which is why this test should fail in GDAL 2.
# ref https://github.com/mapbox/rasterio/blob/8cb216ca83e57284f8a56bafbe8eda4334a34db6/rasterio/crs.py#L509-L538
@pytest.mark.xfail(
    gdal_version.major < 3,
    reason="In GDAL < 3.0, CRS defined with EPSG will always return False in morecantile.models.crs_axis_inverted",
)
def test_custom_tms_bounds_epsg4326():
    """Check bounds with epsg4326."""
    custom_tms = TileMatrixSet.custom((-120, 30, -110, 40), CRS.from_epsg(4326))
    assert custom_tms.xy_bbox == (-120, 30, -110, 40)
    assert custom_tms.bbox == (-120, 30, -110, 40)
    assert custom_tms.xy_bounds(0, 0, 0) == (-120, 30, -110, 40)
    assert custom_tms.bounds(0, 0, 0) == (-120, 30, -110, 40)


# When using `from_user_input`, `morecantile.models.crs_axis_inverted` should return the valid result.
def test_custom_tms_bounds_user_crs():
    """Check bounds with epsg4326."""
    custom_tms = TileMatrixSet.custom(
        (-120, 30, -110, 40),
        CRS.from_user_input("http://www.opengis.net/def/crs/EPSG/0/4326"),
    )
    assert custom_tms.xy_bbox == (-120, 30, -110, 40)
    assert custom_tms.bbox == (-120, 30, -110, 40)
    assert custom_tms.xy_bounds(0, 0, 0) == (-120, 30, -110, 40)
    assert custom_tms.bounds(0, 0, 0) == (-120, 30, -110, 40)


def test_InvertedLatLonGrids():
    """Check Inverted LatLon grids."""
    tms = morecantile.tms.get("NZTM2000")
    bound = tms.xy_bounds(morecantile.Tile(1, 2, 0))
    assert bound == (1293760.0, 3118720.0, 3587520.0, 5412480.0)
    assert tms.xy_bbox == (274000.0, 3087000.0, 3327000.0, 7173000.0)

    tms = morecantile.tms.get("LINZAntarticaMapTilegrid")
    assert tms.xy_bbox == (
        -918457.73,
        -22441670.269999996,
        28441670.269999996,
        6918457.73,
    )


def test_zoom_for_res():
    """Get TMS zoom level corresponding to a specific resolution."""
    tms = morecantile.tms.get("WebMercatorQuad")

    # native resolution of zoom 7 is 1222.9924525628178
    # native resolution of zoom 8 is 611.4962262814075
    assert tms.zoom_for_res(612.0) == 8
    assert tms.zoom_for_res(612.0, zoom_level_strategy="lower") == 7
    assert tms.zoom_for_res(612.0, zoom_level_strategy="upper") == 8

    assert tms.zoom_for_res(610.0) == 8

    # native resolution of zoom 24 is 0.009330691929342784
    assert tms.zoom_for_res(0.0001) == 24

    # theoritical resolution of zoom 25 is 0.004665345964671392
    with pytest.warns(UserWarning):
        assert tms.zoom_for_res(0.0001, max_z=25) == 25


def test_schema():
    """Translate Model to Schema."""
    tms = morecantile.tms.get("WebMercatorQuad")
    assert tms.schema()
    assert tms.schema_json()
    assert tms.json(exclude_none=True)
    assert tms.dict(exclude_none=True)

    crs = CRS.from_proj4(
        "+proj=stere +lat_0=90 +lon_0=0 +k=2 +x_0=0 +y_0=0 +R=3396190 +units=m +no_defs"
    )
    extent = [-13584760.000, -13585240.000, 13585240.000, 13584760.000]
    tms = morecantile.TileMatrixSet.custom(extent, crs, identifier="MarsNPolek2MOLA5k")
    assert tms.schema()
    assert tms.schema_json()
    assert tms.dict(exclude_none=True)
    json_doc = json.loads(tms.json(exclude_none=True))
    # We cannot translate PROJ4 to epsg so it's set to None
    assert json_doc["supportedCRS"] == "http://www.opengis.net/def/crs/EPSG/0/None"

    crs = CRS.from_epsg(3031)
    extent = [-948.75, -543592.47, 5817.41, -3333128.95]  # From https:///epsg.io/3031
    tms = morecantile.TileMatrixSet.custom(
        extent, crs, identifier="MyCustomTmsEPSG3031"
    )
    assert tms.schema()
    assert tms.schema_json()
    assert tms.json(exclude_none=True)
    json_doc = json.loads(tms.json(exclude_none=True))
    assert json_doc["supportedCRS"] == "http://www.opengis.net/def/crs/EPSG/0/3031"
