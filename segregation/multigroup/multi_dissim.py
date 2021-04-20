"""Multigroup dissimilarity index"""

__author__ = "Renan X. Cortes <renanc@ucr.edu>, Sergio J. Rey <sergio.rey@ucr.edu> and Elijah Knaap <elijah.knaap@ucr.edu>"

from .._base import MultiGroupIndex, SpatialImplicitIndex
import numpy as np
from sklearn.metrics.pairwise import manhattan_distances

from segregation.util.util import _dep_message, DeprecationHelper, _nan_handle

np.seterr(divide="ignore", invalid="ignore")


def _multi_dissim(data, groups):
    """Calculation of Multigroup Dissimilarity index.

    Parameters
    ----------
    data : pandas.DataFrame
        DataFrame holding counts of population groups
    groups : list of strings.
        The variables names in data of the groups of interest of the analysis.

    Returns
    -------
    statistic : float
        Multigroup Dissimilarity Index
    core_data : pandas.DataFrame
        DataFrame that contains the columns used to perform the estimate.

    Notes
    -----
    Based on Sakoda, James M. "A generalized index of dissimilarity." Demography 18.2 (1981): 245-250.

    Reference: :cite:`sakoda1981generalized`.

    """
    core_data = data[groups]
    data = _nan_handle(core_data)

    df = np.array(core_data)

    n = df.shape[0]
    K = df.shape[1]

    T = df.sum()

    ti = df.sum(axis=1)
    pik = df / ti[:, None]
    Pk = df.sum(axis=0) / df.sum()

    Is = (Pk * (1 - Pk)).sum()

    multi_D = (
        1
        / (2 * T * Is)
        * np.multiply(abs(pik - Pk), np.repeat(ti, K, axis=0).reshape(n, K)).sum()
    )

    return multi_D, core_data, groups


class MultiDissim(MultiGroupIndex, SpatialImplicitIndex):
    """Dissimilarity Index.

    Parameters
    ----------
    data : pandas.DataFrame or geopandas.GeoDataFrame, required
        dataframe or geodataframe if spatial index holding data for location of interest
    groups : list, required
        list of columns on dataframe holding population totals for each group
    w : libpysal.weights.KernelW, optional
        lipysal spatial kernel weights object used to define an egohood
    network : pandana.Network
        pandana Network object representing the study area
    distance : int
        Maximum distance (in units of geodataframe CRS) to consider the extent of the egohood
    decay : str
        type of decay function to apply. Options include
    precompute : bool
        Whether to precompute the pandana Network object

    Attributes
    ----------
    statistic : float
        Multigroup Dissimilarity Index value
    core_data : a pandas DataFrame
        DataFrame that contains the columns used to perform the estimate.
    """

    def __init__(
        self,
        data,
        groups,
        w=None,
        network=None,
        distance=None,
        decay=None,
        precompute=None,
    ):
        """Init."""

        MultiGroupIndex.__init__(self, data, groups)
        if any([w, network, distance]):
            SpatialImplicitIndex.__init__(self, w, network, distance, decay, precompute)
        aux = _multi_dissim(self.data, self.groups)

        self.statistic = aux[0]
        self.data = aux[1]
        self.groups = aux[2]
        self._function = _multi_dissim
