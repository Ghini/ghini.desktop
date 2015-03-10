import bauble.utils as utils
from bauble.test import BaubleTestCase

class Utils(BaubleTestCase):
    
    def test_topological_sort_total(self):
        self.assertEqual(utils.topological_sort([1,2,3], [(2,1), (3,2)]), [3, 2, 1])

    def test_topological_sort_partial(self):
        self.assertEqual(utils.topological_sort([1,2,3,4], [(2,1)]), [4, 3, 2, 1])

    def test_topological_sort_loop(self):
        self.assertEqual(utils.topological_sort([1,2], [(2,1), (1,2)]), None)
