from cashdash.algo.zinc_links import ZincLinkReconstructor
from test.abstract_link_test import AbstractTest


class ZincLinkReconstructionTest(AbstractTest.LinkReconstructionTest):

    def setUp(self) -> None:
        self.uut = ZincLinkReconstructor()
