from cashdash.algo.cvxpy_links import CvxpyLinkReconstructor
from test.abstract_link_test import AbstractTest


class ZincLinkReconstructionTest(AbstractTest.LinkReconstructionTest):

    def setUp(self) -> None:
        self.uut = CvxpyLinkReconstructor()
