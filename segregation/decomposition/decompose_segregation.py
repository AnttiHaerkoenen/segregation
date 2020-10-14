"""
Decomposition Segregation based Metrics
"""

__author__ = "Renan X. Cortes <renanc@ucr.edu>, Elijah Knaap <elijah.knaap@ucr.edu>, and Sergio J. Rey <sergio.rey@ucr.edu>"


import warnings
import seaborn as sns
import matplotlib.pyplot as plt
import pandas as pd
from segregation.util.util import _generate_counterfactual

# Including old and new api in __all__ so users can use both

__all__ = ['DecomposeSegregation']

# The Deprecation calls of the classes are located in the end of this script #

def _decompose_segregation(index1,
                           index2,
                           counterfactual_approach='composition'):
    """Decompose segregation differences into spatial and attribute components.

    Given two segregation indices of the same type, use Shapley decomposition
    to measure whether the differences between index measures arise from
    differences in spatial structure or population structure

    Parameters
    ----------
    index1 : segregation.SegIndex class
        First SegIndex class to compare.
    index2 : segregation.SegIndex class
        Second SegIndex class to compare.
    counterfactual_approach : str, one of
                              ["composition", "share", "dual_composition"]
        The technique used to generate the counterfactual population
        distributions.

    Returns
    -------
    tuple
        (shapley spatial component,
         shapley attribute component,
         core data of index1,
         core data of index2,
         data with counterfactual variables for index1,
         data with counterfactual variables for index2)

    """
    df1 = index1.core_data.copy()
    df2 = index2.core_data.copy()

    assert index1._function == index2._function, "Segregation indices must be of the same type"

    counterfac_df1, counterfac_df2 = _generate_counterfactual(
        df1,
        df2,
        'group_pop_var',
        'total_pop_var',
        counterfactual_approach=counterfactual_approach)

    seg_func = index1._function

    # index for spatial 1, attribute 1
    G_S1_A1 = index1.statistic

    # index for spatial 2, attribute 2
    G_S2_A2 = index2.statistic

    # index for spatial 1 attribute 2 (counterfactual population for structure 1)
    G_S1_A2 = seg_func(counterfac_df1, 'counterfactual_group_pop',
                       'counterfactual_total_pop')[0]

    # index for spatial 2 attribute 1 (counterfactual population for structure 2)
    G_S2_A1 = seg_func(counterfac_df2, 'counterfactual_group_pop',
                       'counterfactual_total_pop')[0]

    # take the average difference in spatial structure, holding attributes constant
    C_S = 1 / 2 * (G_S1_A1 - G_S2_A1 + G_S1_A2 - G_S2_A2)

    # take the average difference in attributes, holding spatial structure constant
    C_A = 1 / 2 * (G_S1_A1 - G_S1_A2 + G_S2_A1 - G_S2_A2)

    results = {'s1_a1': G_S1_A1,
            's1_a2': G_S1_A2,
            's2_a1': G_S2_A1,
            's2_a2': G_S2_A2 }

    return C_S, C_A, df1, df2, counterfac_df1, counterfac_df2, counterfactual_approach, results


class DecomposeSegregation:
    """Decompose segregation differences into spatial and attribute components.

    Given two segregation indices of the same type, use Shapley decomposition
    to measure whether the differences between index measures arise from
    differences in spatial structure or population structure

    Parameters
    ----------
    index1 : segregation.SegIndex class
        First SegIndex class to compare.
    index2 : segregation.SegIndex class
        Second SegIndex class to compare.
    counterfactual_approach : str, one of
                              ["composition", "share", "dual_composition"]
        The technique used to generate the counterfactual population
        distributions.

    Attributes
    ----------

    c_s : float
        Shapley's Spatial Component of the decomposition

    c_a : float
        Shapley's Attribute Component of the decomposition

    Methods
    ----------

    plot : Visualize features of the Decomposition performed
        plot_type : str, one of ['cdfs', 'maps']

        'cdfs' : visualize the cumulative distribution functions of the compositions/shares
        'maps' : visualize the spatial distributions for original data and counterfactuals generated and Shapley's components (only available for GeoDataFrames)

    Examples
    --------
    Several examples can be found at https://github.com/pysal/segregation/blob/master/notebooks/decomposition_wrapper_example.ipynb.

    """

    def __init__(self, index1, index2, counterfactual_approach='composition'):

        aux = _decompose_segregation(index1, index2, counterfactual_approach)

        self.c_s = aux[0]
        self.c_a = aux[1]
        self._df1 = aux[2]
        self._df2 = aux[3]
        self._counterfac_df1 = aux[4]
        self._counterfac_df2 = aux[5]
        self._counterfactual_approach = aux[6]
        self.indices = aux[7]

    def plot(self, plot_type='cdfs', figsize=(10, 10), city_a=None, city_b=None, cmap='OrRd', scheme='equalinterval', k=10, suptitle_size=20):
        """
        Plot the Segregation Decomposition Profile
        """

        if not city_a:
            city_a = 'City A'
        if not city_b:
            city_b = 'City B'

        if (plot_type == 'cdfs'):

            fig, ax = plt.subplots(figsize=figsize)
            plt.suptitle(f"Decomposing differences between\n{city_a} and {city_b}", size=suptitle_size)
            plt.title(f"Spatial Component = {round(self.c_s, 3)}, Attribute Component: {round(self.c_a, 3)}")

            temp_a = self._counterfac_df1.copy()
            temp_a['Location'] = city_a
            temp_b = self._counterfac_df2.copy()
            temp_b['Location'] = city_b
            df = pd.concat([temp_a, temp_b])

            if (self._counterfactual_approach == 'composition'):
                sns.ecdfplot(data=df, x='group_composition', hue='Location', ax=ax)
                return ax

            elif (self._counterfactual_approach == 'share'):
                f = sns.ecdfplot(data=df, x='share', hue='Location', ax=ax)
                return f

            elif (self._counterfactual_approach == 'dual_composition'):
                df['compl'] = 1-df.group_composition
                f = sns.ecdfplot(data=df, x='group_composition', hue='Location', ax=ax)
                f2 = sns.ecdfplot(data=df, x='compl', hue='Location', ax=ax)

        if (plot_type == 'maps'):
            fig, axs = plt.subplots(2, 2, figsize=figsize)
            plt.suptitle(f"Decomposing differences between\n{city_a} and {city_b}", size=suptitle_size)
            plt.title(f"Spatial Component = {round(self.c_s, 3)}, Attribute Component: {round(self.c_a, 3)}")

            # Original First Context (Upper Left)
            self._counterfac_df1.plot(column='group_composition',
                                      cmap=cmap,
                                      legend=True,
                                      scheme=scheme,
                                      k=k,
                                      ax=axs[0, 0])
            axs[0, 0].title.set_text(f'{city_a} Original Composition')
            axs[0, 0].axis('off')

            # Counterfactual First Context (Bottom Left)
            self._counterfac_df1.plot(column='counterfactual_composition',
                                      cmap=cmap,
                                      scheme=scheme,
                                      k=k,
                                      legend=True,
                                      ax=axs[1, 0])
            axs[1, 0].title.set_text(
                f'{city_a} Counterfactual Composition')
            axs[1, 0].axis('off')

            # Counterfactual Second Context (Upper Right)
            self._counterfac_df2.plot(column='counterfactual_composition',
                                      cmap=cmap,
                                      scheme=scheme,
                                      k=k,
                                      legend=True,
                                      ax=axs[0, 1])
            axs[0, 1].title.set_text(
                f'{city_b}  Counterfactual Composition')
            axs[0, 1].axis('off')

            # Original Second Context (Bottom Right)
            self._counterfac_df2.plot(column='group_composition',
                                      cmap=cmap,
                                      scheme=scheme,
                                      k=k,
                                      legend=True,
                                      ax=axs[1, 1])
            axs[1, 1].title.set_text(f'{city_b} Original Composition')
            axs[1, 1].axis('off')
