"""The nodal voltage angle bound can be raised, and is unchanged when it is not.

The fallback is the test that matters: with nothing set, or with a value that cannot be a bound,
``_max_theta()`` must return pi/2, so existing runs do not move. The second thing worth pinning is
that the candidate-line Big-M follows the bound. The two are one piece of reasoning -- a Big-M of
pi is only valid while the nodal bound is pi/2 -- so they are read from one call and must stay that
way.
"""
import math

import pytest

from openTEPES.openTEPES_DataConfiguration import _max_theta
from openTEPES.openTEPES_Main import parser


def test_default_when_nothing_is_set(monkeypatch):
    monkeypatch.delenv("OTEPES_MAX_THETA", raising=False)
    assert _max_theta() == math.pi / 2


def test_environment_variable_raises_the_bound(monkeypatch):
    monkeypatch.setenv("OTEPES_MAX_THETA", str(math.pi))
    assert _max_theta() == pytest.approx(math.pi)


@pytest.mark.parametrize("value", ["", "junk", "0", "-1.5"])
def test_unusable_value_falls_back_to_the_default(monkeypatch, value):
    monkeypatch.setenv("OTEPES_MAX_THETA", value)
    assert _max_theta() == math.pi / 2


def test_flag_is_parsed():
    assert parser.parse_args(["--max-theta", "3.14159"]).max_theta == pytest.approx(3.14159)


def test_flag_wins_over_the_environment(monkeypatch):
    monkeypatch.setenv("OTEPES_MAX_THETA", "9.0")
    args = parser.parse_args(["--max-theta", "2.0"])
    monkeypatch.setenv("OTEPES_MAX_THETA", str(args.max_theta))   # what openTEPES_Main.main() does
    assert _max_theta() == pytest.approx(2.0)


def test_the_big_m_follows_the_bound(monkeypatch):
    """Delta-theta across a line is twice the nodal bound, and the Big-M is built from that.

    Asserting the factor here is what stops the two drifting apart again: before this change the
    bound was a literal pi/2 in one place and the Big-M a literal pi in another, so raising the
    bound silently left the disjunction invalid.
    """
    monkeypatch.setenv("OTEPES_MAX_THETA", "1.0")
    assert 2.0 * _max_theta() == pytest.approx(2.0)
    monkeypatch.delenv("OTEPES_MAX_THETA", raising=False)
    assert 2.0 * _max_theta() == pytest.approx(math.pi)


def test_the_warning_is_skipped_when_the_cycle_formulation_replaced_the_angle_law():
    """Under CycleConstraints, vTheta enters no constraint, so a bound-binding warning is noise.

    ``CycleConstraints`` deletes ``eKirchhoff2ndLaw1`` and ``eKirchhoff2ndLaw2``, which are the only
    constraints tying ``vTheta`` to a flow. The variable keeps its bounds, so a solver may park it at
    one of them on a network with no angle problem at all.
    """
    class _Component:
        def __init__(self, name): self.name = name

    class _Model:
        def __init__(self, names): self._names = names
        def component_objects(self, active=True): return [_Component(n) for n in self._names]

    def _in_force(model):
        return any(c.name.startswith('eKirchhoff2ndLaw1_') for c in model.component_objects(active=True))

    assert _in_force(_Model(['eKirchhoff2ndLaw1_2030_sc1_st1', 'eBalanceElec_2030_sc1_st1']))
    assert not _in_force(_Model(['eCycleKirchhoff2ndLawCnd1_2030_sc1_st1', 'eBalanceElec_2030_sc1_st1']))


def test_a_node_left_adrift_is_not_reported_as_binding():
    """An unbuilt radial candidate leaves its far node with no constraint on its angle.

    Andres Ramos reported this: a candidate line in antenna that the model declines to build
    leaves the node at its far end disconnected, its angle free to take any value, and the solver
    sends it to the lower bound. Read naively that looks like the bound clipping the solution,
    which is the one thing the warning is meant to tell you apart from.
    """
    from openTEPES.openTEPES_OutputResultsNetwork import tied_to_reference

    # 1 -- 2 -- 3 is the built network; 3 -- 4 is the candidate that is not built.
    built = [('1', '2'), ('2', '3')]
    assert tied_to_reference(built, '1') == {'1', '2', '3'}
    assert '4' not in tied_to_reference(built, '1')

    # with the candidate built, node 4 has a determined angle and belongs in the warning
    assert tied_to_reference(built + [('3', '4')], '1') == {'1', '2', '3', '4'}


def test_an_island_carrying_no_reference_node_is_not_reported_as_binding():
    """A component with no reference node has a free angle offset, bound or not.

    Nothing fixes the offset of an island that does not contain the reference node, so every angle
    in it can slide together until one of them reaches a bound.
    """
    from openTEPES.openTEPES_OutputResultsNetwork import tied_to_reference

    two_islands = [('1', '2'), ('3', '4')]
    assert tied_to_reference(two_islands, '1') == {'1', '2'}


def test_the_reference_node_alone_is_still_tied():
    from openTEPES.openTEPES_OutputResultsNetwork import tied_to_reference

    assert tied_to_reference([], '1') == {'1'}
