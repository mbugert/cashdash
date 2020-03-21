import itertools
from typing import List

import cvxpy as cp
import deprecation
import numpy as np
import pandas as pd

from cashdash.algo.base import LinkReconstructor
from cashdash.algo.base import SOURCE, TARGET
from cashdash.data import (
    TYPE,
    VALUE,
    ACCOUNT,
    INCOME,
    LIABILITY,
    ASSET,
    BANK,
    CASH,
    EXPENSE,
)


@deprecation.deprecated(
    details="Somewhat fast, but does not model all constraints. Use "
    + "cashdash.algo.zinc_links.ZincLinkReconstructor instead."
)
class CvxpyLinkReconstructor(LinkReconstructor):
    def reconstruct(self, splits: pd.DataFrame) -> List:
        # most transactions likely are non-split transactions, so they deserve to be dealt with quickly
        if len(splits) == 2:
            return [
                {
                    SOURCE: splits.loc[splits[VALUE] < 0, ACCOUNT].values[0],
                    TARGET: splits.loc[splits[VALUE] > 0, ACCOUNT].values[0],
                    VALUE: max(splits[VALUE]),
                }
            ]

        # one node per account
        num_nodes = len(splits)

        # two variables per edge\textsc{}
        edges = cp.Variable((num_nodes, num_nodes), nonneg=True)

        constraints = []

        # we have no loops, so the diagonal should remain 0
        constraints.append(cp.trace(edges) == 0)

        asset_types = [CASH, BANK, ASSET, LIABILITY]
        has_assets = not splits.loc[
            splits[TYPE].isin([CASH, BANK, ASSET, LIABILITY])
        ].empty

        # unidirectionality constraint
        for n1, n2 in itertools.combinations(range(num_nodes), 2):
            n1_type, n2_type = splits.iloc[n1][TYPE], splits.iloc[n2][TYPE]

            if n1_type in asset_types:
                n1_type = ASSET
            if n2_type in asset_types:
                n2_type = ASSET

            types = sorted([n1_type, n2_type])

            # permit flow between these account pairs
            is_active_edge_pair = (
                types == [ASSET, INCOME]
                or types == [ASSET, EXPENSE]
                or types == [ASSET, ASSET]
                or not has_assets
                and types == [EXPENSE, INCOME]
            )

            if is_active_edge_pair:
                # TODO can't model unidirectionality here
                # constraint = edges[n1, n2] * edges[n2, n1] == 0
                # constraints.append(constraint)
                pass
            else:
                constraints += [edges[n1, n2] == 0, edges[n2, n1] == 0]

        # flow conservation constraint
        for n in range(num_nodes):
            _from = cp.sum(edges[n, :])
            to = cp.sum(edges[:, n])
            node_delta = splits.iloc[n][VALUE]
            constraints.append(_from - to == node_delta)

        objective = cp.Minimize(cp.sum(cp.abs(edges)))
        prob = cp.Problem(objective, constraints)

        prob.solve()
        assert edges.value is not None
        flows = np.around(
            edges.value, 2
        )  # two decimals should be enough for currencies

        # nonzero edges indicate flow between account
        links = []
        for idx_dest, idx_src in np.stack(np.nonzero(flows), axis=1):
            value = flows[idx_dest, idx_src]
            links.append(
                {
                    SOURCE: splits.iloc[idx_src][ACCOUNT],
                    TARGET: splits.iloc[idx_dest][ACCOUNT],
                    VALUE: value,
                }
            )

        return links
