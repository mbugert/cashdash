import itertools
import os
from pathlib import Path
from typing import List

import numpy as np
import pandas as pd
from minizinc import Instance, Model, Solver

from cashdash.algo.base import LinkReconstructor, SOURCE, TARGET
from cashdash.data import (
    ACCOUNT,
    VALUE,
    TYPE,
    INCOME,
    CASH,
    BANK,
    ASSET,
    LIABILITY,
    EXPENSE,
)


class ZincLinkReconstructor(LinkReconstructor):
    def __init__(self):
        resources_root = Path(os.path.dirname(__file__)).resolve().parent / "resources"
        zinc_resources = resources_root / "zinc"
        self.model = Model(zinc_resources / "links.mzn")
        self.solver = Solver.lookup("gecode")

    def reconstruct(self, splits: pd.DataFrame) -> List:
        # We frame the problem of identifying money flow between accounts as finding edge flows in a flow graph. The
        # following specialties apply:
        #  - every node in the graph can be a source or sink
        #  - edge labels are the absolute amount of money flowing, i.e. always 0 or more
        #  - constraints:
        #    - unidirectionality: between two nodes in the flow graph, there are two edges (forward/backward edges), but
        #      only one of those edges should be non-zero at a time ()
        #    - flow conservation: ingoing money plus outgoing money equals node delta
        # TODO many more improvements are imaginable:
        #  - prefer assigning income to certain account types: CASH, then BANK, then ASSET
        #  - learn which asset accounts usually receive income based on past transactions

        # TODO use denomination matching the actual currency
        denomination = 100

        # most transactions likely are non-split transactions, so they deserve to be dealt with quickly
        if len(splits) == 2:
            return [
                {
                    SOURCE: splits.loc[splits[VALUE] < 0, ACCOUNT].values[0],
                    TARGET: splits.loc[splits[VALUE] > 0, ACCOUNT].values[0],
                    VALUE: max(splits[VALUE]),
                }
            ]

        # represent amounts of money as int
        split_values_as_int = (splits[VALUE] * denomination).map(round)

        num_nodes = len(splits)
        # we need to convert np.int64 to plain int here because they JSON-serialize all input parameters in minizinc
        max_flow = split_values_as_int.abs().sum().item()
        node_deltas = [i.item() for i in split_values_as_int.values]

        asset_types = [CASH, BANK, ASSET, LIABILITY]
        has_assets = not splits.loc[
            splits[TYPE].isin([CASH, BANK, ASSET, LIABILITY])
        ].empty

        adjacency_matrix = np.zeros((num_nodes, num_nodes)).astype(bool)
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
                adjacency_matrix[n1, n2] = True
                adjacency_matrix[n2, n1] = True
        adjacency_matrix = adjacency_matrix.tolist()

        # get it solved
        # TODO speed this up; still many assignment failures because our target objective is weak
        instance = Instance(self.solver, self.model)
        instance["n"] = num_nodes
        instance["max_flow"] = max_flow
        instance["deltas"] = node_deltas
        instance["E"] = adjacency_matrix
        result = instance.solve()
        assert result.solution is not None
        F = np.array(result.solution.F)

        links = []
        for idx_source, idx_target in zip(*F.nonzero()):
            value = F[idx_source, idx_target]
            links.append(
                {
                    SOURCE: splits.iloc[idx_source][ACCOUNT],
                    TARGET: splits.iloc[idx_target][ACCOUNT],
                    VALUE: value / denomination,
                }
            )

        return links
