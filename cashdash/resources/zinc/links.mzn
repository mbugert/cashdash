% Find edge flows in a special directed flow graph.

% number of nodes
int: n;

% maximum expected flow between nodes, to constrain variable bounds
int: max_flow;

% observed flow delta at each node
array[1..n] of int: deltas;

% graph as adjacency matrix
array[1..n,1..n] of bool: E;

% ---------------------------------------------------------------------

% to be determined: edge flows between nodes
array[1..n,1..n] of var 0..max_flow: F;

% edge flow between non-adjacent nodes must be 0
constraint forall(i,j in 1..n)(not E[i,j] -> F[i,j] == 0);

% unidirectionality constraint
constraint forall(
    [
        not (F[i,j] > 0 /\ F[j,i] > 0) | i,j in 1..n where i>j
    ]
);

% flow conservation constraint: ingoing flow plus outgoing flow equals node delta
constraint forall(
    [
        let {
            var int: ingoing = sum([F[j,i] | j in 1..n]);
            var int: outgoing = sum([F[i,j] | j in 1..n])
        } in ingoing - outgoing == deltas[i]
        | i in 1..n
    ]
);

% We want a simple solution, i.e. no unnecessarily long flows throughout the graph which would drive up edge weights.
% We therefore minimize the total weight of all edges.
solve minimize sum(F);