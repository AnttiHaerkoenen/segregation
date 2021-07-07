"""Tools for simulating spatial population distributions."""

import itertools
import multiprocessing

import geopandas as gpd
import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from tqdm.auto import tqdm


def _generate_estimate(input):
    if hasattr(input[0], "_original_data"):
        df = input[0]._original_data.copy()
    else:
        df = input[0].data.copy()
    if input[0].index_type == "singlegroup":
        df = input[1](df, group=input[0].group_pop_var, total=input[0].total_pop_var,)
        estimate = (
            input[0]
            .__class__(df, input[0].group_pop_var, input[0].total_pop_var, **input[2])
            .statistic
        )
    else:
        df = input[1](df, groups=input[0].groups)
        estimate = input[0].__class__(df, input[0].groups, **input[2]).statistic
    return estimate


def simulate_null(
    iterations=500,
    sim_func=None,
    seg_func=None,
    n_jobs=-1,
    backend="loky",
    index_kwargs=None,
):
    """Simulate a series of index values in parallel to serve as a null distribution.

    Parameters
    ----------
    iterations : int, optional
        Number of iterations to simulate (size of the distribution), by default 1000
    sim_func : function, required
        population randomization function from segregation.inference to serve as
        the null hypothesis.
    seg_func : Class from segregation.singlegroup or segregation.singlegroup, required
        fitted segregation class from which to generate a reference distribution
    n_jobs : int, optional
        number of cpus to initialize for parallelization. If -1, use all available,
        by default -1
    backend : str, optional
        backend passed to joblib.Parallel, by default "loky"
    index_kwargs : dict, optional
        additional keyword arguments used to fit the index, such as distance or network
        if estimating a spatial index; by default None

    Returns
    -------
    list
        list of segregation index values
    """
    if not index_kwargs:
        index_kwargs = {}
    if n_jobs == -1:
        n_jobs = multiprocessing.cpu_count()
    estimates = Parallel(n_jobs=n_jobs, backend=backend)(
        delayed(_generate_estimate)((seg_func, sim_func, index_kwargs))
        for i in tqdm(range(iterations))
    )
    return pd.Series(estimates)


def simulate_person_permutation(df, group=None, total=None, groups=None):
    """Simulate the permutation of individuals across spatial units.

    Parameters
    ----------
    df : geopandas.GeoDataFrame
        geodataframe with population data to be randomized
    group : str, optional
        name of column on geodataframe that holds the group total
        (for use with single group indices)
    total : str, optional
        name of column on geodataframe that holds the total population for
        each unit (for use with single group indices)
    groups : list, optional
        list of columns on inut dataframe that hold total population counts
        for each group of interest

    Returns
    -------
    geopandas.GeoDataFrame
        geodataframe with randomly reallocated population

    Notes
    -------
    Simulates the random permutation of the existing population's location. Given a pool
    of the total population in the region, randomly allocate each person to a
    geographic unit, subject to the total capacity of each unit. Results are
    guaranteed to respect regional and local totals for geographic units as well
    as regional totals and relative shares for groups
    """
    df = df.copy()
    # ensure we have a coilumn named "index"
    df = df.reset_index(drop=True)
    df = df.reset_index()
    geoms = df[[df.geometry.name]]
    if not total:
        total = "total"
        df["total"] = df[groups].sum(axis=1).astype(int)
    df = df[df[total] > 0]
    if group:
        df[total] = df[total].astype(int)
        df["other"] = df[total] - df[group]
        groups = [group, "other"]

    # create a list of group membership for each person
    members = [[group for i in range(df[group].sum().astype(int))] for group in groups]
    pop_groups = list(itertools.chain.from_iterable(members))

    # create a  list of 1s representing the population in each unit
    df["people"] = df[total].apply(lambda x: [1 for i in range(x)])

    # explode the dataframe to have n_rows = total_population
    df = df["people"].explode().reset_index()["index"].to_frame()
    df["groups"] = pop_groups

    # randomize people's group id
    df["groups"] = df["groups"].sample(frac=1).values

    # reaggregate by unit index
    df = df.groupby("index")["groups"].value_counts().unstack()
    df[total] = df[groups].sum(axis=1)
    df = df.join(geoms)

    return gpd.GeoDataFrame(df, geometry=geoms.geometry.name)


def simulate_evenness(df, group=None, total=None, groups=None):
    """Simulate even redistribution of population groups across spatial units.

    Parameters
    ----------
    df : geopandas.GeoDataFrame
        geodataframe with population data to be randomized
    group : str, optional
        name of column on geodataframe that holds the group total
        (for use with single group indices)
    total : str, optional
        name of column on geodataframe that holds the total population for
        each unit (for use with single group indices)
    groups : list, optional
        list of columns on inut dataframe that hold total population counts
        for each group of interest

    Returns
    -------
    geopandas.GeoDataFrame
        geodataframe with evenly distributed population groups

    Notes
    -------
    Simulates the random allocation of groups, given the total population of
    each geographic unit (randomizes group totals for each location). Given the total
    population of each location, take draws from a multinomial distribution to assign
    group categories for each person, where the probability of each group is equal to
    its regional share. Results are guaranteed to match regional and local population
    totals, but will include variation in the relative share of each group
    """
    df = df.copy()
    geoms = df[df.geometry.name].values
    if group:
        df[[group, total]] = df[[group, total]].astype(int)
        p_null = df[group].sum() / df[total].sum()

        output = gpd.GeoDataFrame()
        output[group] = np.random.binomial(n=df[total].values, p=p_null)
        output[total] = df[total].tolist()
    if groups:
        df = df[groups]
        global_prob_vector = df.sum(axis=0) / df.sum().sum()
        t = df[groups].sum(axis=1).astype(int)

        simul = list(
            map(lambda i: list(np.random.multinomial(i, global_prob_vector)), t)
        )
        output = pd.DataFrame(simul, columns=groups)
    output["geometry"] = geoms

    return gpd.GeoDataFrame(output)


def simulate_systematic_randomization(df, group=None, total=None, groups=None):
    """Simulate even redistribution of population groups across spatial units.

    Parameters
    ----------
    df : geopandas.GeoDataFrame
        geodataframe with population data to be randomized
    group : str, optional
        name of column on geodataframe that holds the group total
        (for use with single group indices)
    total : str, optional
        name of column on geodataframe that holds the total population for
        each unit (for use with single group indices)
    groups : list, optional
        list of columns on inut dataframe that hold total population counts
        for each group of interest

    Returns
    -------
    geopandas.GeoDataFrame
        geodataframe with systematically randomized population groups

    Notes
    -------
    Simulates the random allocation of each group across geographic units, given the total population
    of each group (randomizes location totals for each group). Given the total population of
    each group in the region, take draws from a multinomial distribution where the
    probability of choosing each geographic unit is equal to the total regional share
    currently residing in the unit. Results will include regional and local variation in
    both total population and relative group shares.
    """
    if groups:
        df[total] = df[groups].sum(axis=1)
    if group:
        assert (
            total
        ), "If simulating a single group, you must also supply a total population column"
        df["other_group_pop"] = df[total] - df[group]
        groups = [group, "other_group_pop"]

    p_j = df[total] / df[total].sum()
    data_aux = {}
    for group in groups:
        n = df[group].sum()
        sim = np.random.multinomial(n, p_j)
        data_aux[group] = sim.tolist()
    data_aux[total] = df[total].tolist()
    df_aux = pd.DataFrame.from_dict(data_aux)
    if isinstance(df, gpd.GeoDataFrame):
        df_aux = df[[df.geometry.name]].reset_index().join(df_aux)

    return df_aux


def simulate_bootstrap_resample(df, **kwargs):
    """Generate bootstrap replications of the units with replacement of the same size of the original data.

    Parameters
    ----------
    df : geopandas.GeoDataFrame or pandas.DataFrame
        (geo)dataframe with population counts to be randomized

    Returns
    -------
    DataFrame
        DataFrame with bootstrap resampled observations

    Notes
    -------
    Simulate a synthetic dataset by drawing from rows of the input data with replacement
    until reaching the same number of observations in the original dataframe. Note that if
    input is a geodataframe, then the output will not be planar-enforced, as more than one of
    the same unit may appear in the sample.
    """
    df = df.copy()
    df = df.reset_index(drop=True)
    sample_index = np.random.choice(df.index, size=len(df), replace=True)
    df_aux = df.iloc[sample_index]
    return df_aux


def simulate_geo_permutation(df, **kwargs):
    """Simulate a synthetic dataset by random permutation of geographic units.

    Parameters
    ----------
    df : geopandas.GeoDataFrame
        geodataframe with population counts to be randomized

    Returns
    -------
    DataFrame
        Simulate a synthetic dataset by randomly allocating the units over space
        keeping their original values.
    """
    df = df.copy()
    df = df.reset_index(drop=True)
    data = df.assign(
        geometry=df[df.geometry.name][
            list(np.random.choice(df.shape[0], df.shape[0], replace=False))
        ].reset_index()[df.geometry.name]
    )
    return data


def simulate_systematic_geo_permutation(df, group=None, total=None, groups=None):
    """Simulate systematic redistribution followed by random permutation of geographic units.

    Parameters
    ----------
    df : geopandas.GeoDataFrame
        geodataframe with population data to be randomized
    group : str, optional
        name of column on geodataframe that holds the group total
        (for use with single group indices)
    total : str, optional
        name of column on geodataframe that holds the total population for
        each unit (for use with single group indices)
    groups : list, optional
        list of columns on inut dataframe that hold total population counts
        for each group of interest

    Returns
    -------
    geopandas.GeoDataFrame
        geodataframe with systematically randomized population groups
    """
    df = simulate_systematic_randomization(df, group=group, total=total, groups=groups)
    df = simulate_geo_permutation(df)
    return df


def simulate_evenness_geo_permutation(df, group=None, total=None, groups=None):
    """Simulate evenness followed by random permutation of geographic units.

    Parameters
    ----------
    df : geopandas.GeoDataFrame
        geodataframe with population data to be randomized
    group : str, optional
        name of column on geodataframe that holds the group total
        (for use with single group indices)
    total : str, optional
        name of column on geodataframe that holds the total population for
        each unit (for use with single group indices)
    groups : list, optional
        list of columns on inut dataframe that hold total population counts
        for each group of interest

    Returns
    -------
    geopandas.GeoDataFrame
        geodataframe with evenly distributed population groups
    """
    df = simulate_evenness(df=df, group=group, total=total, groups=groups)
    df = simulate_geo_permutation(df)
    return df


SIMULATORS = {
    "systematic": simulate_systematic_randomization,
    "bootstrap": simulate_bootstrap_resample,
    "evenness": simulate_evenness,
    "person_permutation": simulate_person_permutation,
    "geographic_permutation": simulate_geo_permutation,
    "systematic_permutation": simulate_systematic_geo_permutation,
    "even_permutation": simulate_evenness_geo_permutation,
}

