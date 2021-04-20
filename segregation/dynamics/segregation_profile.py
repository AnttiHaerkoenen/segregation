"""Compute multiscalar segregation profiles."""

import numpy as np
import pandas as pd
from libpysal.weights import Kernel
from .._base import SingleGroupIndex, MultiGroupIndex


def compute_multiscalar_profile(
    gdf,
    segregation_index=None,
    groups=None,
    group_pop_var=None,
    total_pop_var=None,
    distances=None,
    network=None,
    decay="linear",
    function="triangular",
    precompute=True,
):
    """Compute multiscalar segregation profile.

    This function calculates several Spatial Information Theory indices with
    increasing distance parameters.

    Parameters
    ----------
    gdf : geopandas.GeoDataFrame
        geodataframe with rows as observations and columns as population
        variables. Note that if using a network distance, the coordinate
        system for this gdf should be 4326. If using euclidian distance,
        this must be projected into planar coordinates like state plane or UTM.
    segregation_index : SpatialImplicit SegregationIndex Class
        a class from the library such as MultiInformationTheory, or MinMax
    groups : list
        list of population groups for calculating multigroup indices
    group_pop_var : str
        name of population group on gdf for calculating single group indices
    total_pop_var : str
        bame of total population on gdf for calculating single group indices
    distances : list
        list of floats representing bandwidth distances that define a local
        environment.
    network : pandana.Network (optional)
        A pandana.Network likely created with
        `segregation.network.get_osm_network`.
    decay : str (optional)
        decay type to be used in pandana accessibility calculation (the
        default is 'linear').
    function: 'str' (optional)
        which weighting function should be passed to libpysal.weights.Kernel
        must be one of: 'triangular','uniform','quadratic','quartic','gaussian'
    precompute: bool
        Whether the pandana.Network instance should precompute the range
        queries.This is true by default, but if you plan to calculate several
        segregation profiles using the same network, then you can set this
        parameter to `False` to avoid precomputing repeatedly inside the
        function

    Returns
    -------
    pandas DataFrame
        DataFrame with distances as keys and index statistics as values

    Notes
    -----
    Based on Sean F. Reardon, Stephen A. Matthews, David O’Sullivan, Barrett A. Lee, Glenn Firebaugh, Chad R. Farrell, & Kendra Bischoff. (2008). The Geographic Scale of Metropolitan Racial Segregation. Demography, 45(3), 489–514. https://doi.org/10.1353/dem.0.0019.

    Reference: :cite:`Reardon2008`.

    """
    if not segregation_index:
        raise ValueError("You must pass a segregation SpatialImplicit Index Class")
    gdf = gdf.copy()
    indices = {}

    if isinstance(segregation_index, MultiGroupIndex):
        gdf[groups] = gdf[groups].astype(float)
        indices[0] = segregation_index(gdf, groups=groups).statistic
    else:
        indices[0] = segregation_index(
            gdf, group_pop_var=group_pop_var, total_pop_var=total_pop_var,
        ).statistic
    if network:
        if not gdf.crs.name == "WGS 84":
            gdf = gdf.to_crs(epsg=4326)
        if precompute:
            maxdist = max(distances)
            network.precompute(maxdist)
        for distance in distances:
            distance = np.float(distance)
            if isinstance(segregation_index, SingleGroupIndex):
                idx = segregation_index(
                    gdf,
                    group_pop_var=group_pop_var,
                    total_pop_var=total_pop_var,
                    network=network,
                    decay=decay,
                    variables=groups,
                    distance=distance,
                    precompute=False,
                )
            else:
                idx = segregation_index(
                    gdf,
                    groups=groups,
                    network=network,
                    decay=decay,
                    variables=groups,
                    distance=distance,
                    precompute=False,
                )
            indices[distance] = idx.statistic
    else:
        for distance in distances:
            w = Kernel.from_dataframe(gdf, bandwidth=distance, function=function)
            if isinstance(segregation_index, MultiGroupIndex):
                idx = segregation_index(gdf, groups, w=w)
            else:
                idx = segregation_index(
                    gdf, group_pop_var=group_pop_var, total_pop_var=total_pop_var, w=w
                )
            indices[distance] = idx.statistic
    return pd.Series(indices)
