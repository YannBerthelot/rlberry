import pytest
import numpy as np  
import rlberry.seeding as seeding
from rlberry.agents.dynprog.utils import bellman_operator
from rlberry.agents.dynprog.utils import value_iteration


@pytest.mark.parametrize("gamma, S, A", 
                         [
                          (0.001, 2, 1), 
                          (0.25,  2, 1), 
                          (0.5,   2, 1),
                          (0.75,  2, 1), 
                          (0.999, 2, 1),
                          (0.001, 4, 2), 
                          (0.25,  4, 2), 
                          (0.5,   4, 2),
                          (0.75,  4, 2), 
                          (0.999, 4, 2),
                          (0.001, 20, 4), 
                          (0.25,  20, 4), 
                          (0.5,   20, 4),
                          (0.75,  20, 4), 
                          (0.999, 20, 4)
                          ] )
def test_bellman_operator_monotonicity_and_contraction(gamma, S, A):
    rng = seeding.get_rng()
    vmax = 1.0/(1.0-gamma)
    for sim in range(10):
        # generate random MDP
        R  = rng.uniform(0.0, 1.0, (S, A))
        P  = rng.uniform(0.0, 1.0, (S, A, S))
        for ss in range(S):
            for aa in range(A):
                P[ss, aa, :] /= P[ss, aa, :].sum()
        # generate random Q functions
        Q0 = rng.uniform(-vmax, vmax, (S, A))
        Q1 = rng.uniform(-vmax, vmax, (S, A))
        # apply Bellman operator
        TQ0 = bellman_operator(Q0, R, P, gamma)
        TQ1 = bellman_operator(Q1, R, P, gamma)

        # test contraction 
        norm_tq = np.abs(TQ1-TQ0).max()
        norm_q = np.abs(Q1-Q0).max()
        assert norm_tq <= gamma * norm_q

        # test monotonicity
        Q2 = rng.uniform(-vmax/2, vmax/2, (S, A))
        Q3 = Q2 + rng.uniform(0.0, vmax/2, (S, A))
        TQ2 = bellman_operator(Q2, R, P, gamma)
        TQ3 = bellman_operator(Q3, R, P, gamma)
        assert np.greater(TQ2, TQ3).sum() == 0

@pytest.mark.parametrize("gamma, S, A", 
                         [
                          (0.01, 20, 4), 
                          (0.25,  20, 4), 
                          (0.5,   20, 4),
                          (0.75,  20, 4), 
                          (0.99, 20, 4)
                          ] )
def test_value_iteration(gamma, S, A):
    rng = seeding.get_rng()
    for epsilon in np.logspace(-1, -6, num=5):
        for sim in range(5):
            # generate random MDP
            R  = rng.uniform(0.0, 1.0, (S, A))
            P  = rng.uniform(0.0, 1.0, (S, A, S))
            for ss in range(S):
                for aa in range(A):
                    P[ss, aa, :] /= P[ss, aa, :].sum()
                
            # run value iteration
            Q, V, n_it = value_iteration(R, P, gamma, epsilon)
            # check precision
            TQ = bellman_operator(Q, R, P, gamma)
            assert np.abs(TQ-Q).max() <= epsilon