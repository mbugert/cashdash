from typing import List

import pandas as pd

SOURCE = "source"
TARGET = "target"


class LinkReconstructor:
    def reconstruct(self, splits: pd.DataFrame) -> List:
        """
        Given splits of a single transaction, reconstruct the cash flow between all accounts involved in the transaction.
        In essence, this task is equal to finding all edge flows in a flow network given the flow at each node (== account).
        Unfortunately, the problem is underconstrained and has infinitely many solutions for moderately complex transactions
        (two expense accounts being fed from two asset accounts; or one income account, two asset accounts and one expense
        account).
        :param splits:
        :return: links
        """
        raise NotImplementedError
