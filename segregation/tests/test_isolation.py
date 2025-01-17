import unittest
import libpysal
import geopandas as gpd
import numpy as np
from segregation.aspatial import Isolation


class Isolation_Tester(unittest.TestCase):
    def test_Isolation(self):
        s_map = gpd.read_file(libpysal.examples.get_path("sacramentot2.shp"))
        df = s_map[['geometry', 'HISP_', 'TOT_POP']]
        index = Isolation(df, 'HISP_', 'TOT_POP')
        np.testing.assert_almost_equal(index.statistic, 0.2319615486459151)


if __name__ == '__main__':
    unittest.main()
