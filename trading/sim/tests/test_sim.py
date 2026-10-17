"""Comprobaciones del simulador de torneo.

    python3 -m unittest discover -s trading/sim/tests -v
"""

from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from contest_sim import (  # noqa: E402
    ContestSpec,
    Policy,
    PrizeTier,
    StrategySpec,
    kelly_leverage,
    optimal_leverage,
    prob_target_analytic,
    prob_target_at_optimum,
    simulate,
)


class TestOptimalLeverage(unittest.TestCase):
    """L* = sqrt(2 ln m)/(sigma sqrt(T)) debe coincidir con el argmax numerico."""

    def test_matches_numeric_argmax(self):
        sigma, days = 0.20, 12
        for target in (1.5, 2.0, 5.0, 10.0):
            for sharpe in (-0.5, 0.0, 1.0, 3.0):
                grid = np.linspace(0.1, 200.0, 40_000)
                probs = [
                    prob_target_analytic(target, sharpe, sigma, days, lev) for lev in grid
                ]
                numeric = grid[int(np.argmax(probs))]
                closed = optimal_leverage(target, sigma, days)
                self.assertAlmostEqual(
                    numeric,
                    closed,
                    delta=0.05 * closed,
                    msg=f"target={target} sharpe={sharpe}",
                )

    def test_independent_of_drift(self):
        """El optimo no depende del edge: solo del objetivo, la vol y el plazo."""
        a = optimal_leverage(3.0, 0.20, 12)
        b = optimal_leverage(3.0, 0.20, 12)
        self.assertEqual(a, b)
        # Y la probabilidad en el optimo si depende del Sharpe, monotonamente.
        probs = [prob_target_at_optimum(3.0, s, 12) for s in (-1.0, 0.0, 1.0, 2.0, 4.0)]
        self.assertEqual(probs, sorted(probs))

    def test_prob_at_optimum_matches_formula(self):
        sigma, days, sharpe, target = 0.25, 16, 1.5, 4.0
        lev = optimal_leverage(target, sigma, days)
        self.assertAlmostEqual(
            prob_target_analytic(target, sharpe, sigma, days, lev),
            prob_target_at_optimum(target, sharpe, days),
            places=9,
        )

    def test_scaling(self):
        """Mas plazo o mas vol => menos apalancamiento necesario."""
        self.assertLess(optimal_leverage(2.0, 0.20, 24), optimal_leverage(2.0, 0.20, 12))
        self.assertLess(optimal_leverage(2.0, 0.40, 12), optimal_leverage(2.0, 0.20, 12))
        self.assertGreater(optimal_leverage(5.0, 0.20, 12), optimal_leverage(2.0, 0.20, 12))

    def test_kelly(self):
        self.assertAlmostEqual(kelly_leverage(1.0, 0.20), 5.0)


class TestMarginCap(unittest.TestCase):
    def test_cap_is_notional_over_margin(self):
        # MNQ a 25.000 con 2.500 $ de margen: 50.000/2.500 = 20x.
        spec = ContestSpec(price=25_000.0, point_value=2.0, margin_per_contract=2_500.0)
        self.assertAlmostEqual(spec.notional_per_contract, 50_000.0)
        self.assertAlmostEqual(spec.margin_leverage_cap, 20.0)
        self.assertAlmostEqual(spec.effective_leverage_cap, 20.0)

    def test_cap_independent_of_equity(self):
        big = ContestSpec(equity0=1_000_000.0, margin_per_contract=2_500.0)
        small = ContestSpec(equity0=10_000.0, margin_per_contract=2_500.0)
        self.assertAlmostEqual(big.margin_leverage_cap, small.margin_leverage_cap)

    def test_self_imposed_cap_wins_when_lower(self):
        spec = ContestSpec(margin_per_contract=2_500.0, max_leverage_cap=8.0)
        self.assertAlmostEqual(spec.effective_leverage_cap, 8.0)


class TestMonteCarlo(unittest.TestCase):
    TIERS = [PrizeTier("corte", 0.60, 200.0)]

    def _contest(self, **kw):
        # Sin tope de margen ni ruina para poder comparar con la formula.
        defaults = dict(days=12, margin_per_contract=0.0, max_leverage_cap=1e9,
                        ruin_fraction=0.0)
        defaults.update(kw)
        return ContestSpec(**defaults)

    def test_matches_analytic_without_ruin(self):
        """Con shocks casi normales y sin ruina, el MC debe seguir la formula."""
        contest = self._contest()
        strat = StrategySpec(sharpe_annual=1.0, sigma_annual=0.20, tail_df=200.0)
        for lev in (2.0, 5.0, 10.0):
            res = simulate(
                Policy(f"{lev}x", "static", leverage=lev),
                contest, strat, self.TIERS, n_paths=200_000, seed=11,
            )
            analytic = prob_target_analytic(1.6, 1.0, 0.20, contest.days, lev)
            self.assertAlmostEqual(res.prob_reach(1.6), analytic, delta=0.02,
                                   msg=f"lev={lev}")

    def test_ruin_monotone_in_leverage(self):
        contest = ContestSpec(days=12, margin_per_contract=0.0, max_leverage_cap=1e9,
                              ruin_fraction=0.10)
        strat = StrategySpec(sharpe_annual=0.5, sigma_annual=0.25)
        ruins = [
            simulate(Policy(f"{lev}x", "static", leverage=lev), contest, strat,
                     self.TIERS, n_paths=40_000, seed=3).prob_ruin
            for lev in (1.0, 10.0, 25.0, 50.0)
        ]
        self.assertEqual(ruins, sorted(ruins))
        self.assertLess(ruins[0], 0.01)

    def test_high_variance_beats_timid_for_far_target(self):
        """Objetivo lejano y edge pobre: la apuesta audaz gana. Es el resultado
        de Dubins-Savage y la razon de ser de todo este plan."""
        contest = self._contest(days=12)
        strat = StrategySpec(sharpe_annual=0.5, sigma_annual=0.20)
        timid = simulate(Policy("1x", "static", leverage=1.0), contest, strat,
                         self.TIERS, n_paths=60_000, seed=5)
        bold = simulate(Policy("20x", "static", leverage=20.0), contest, strat,
                        self.TIERS, n_paths=60_000, seed=5)
        self.assertGreater(bold.prob_reach(6.0), timid.prob_reach(6.0))
        # Y al contrario: si el objetivo es solo conservar el capital, el
        # apalancamiento alto lo destruye (la penalizacion -L^2 sigma^2/2).
        self.assertGreater(timid.prob_reach(1.0), bold.prob_reach(1.0))

    def test_expected_prize_accumulates_nested_tiers(self):
        contest = self._contest()
        strat = StrategySpec(sharpe_annual=1.0, sigma_annual=0.20)
        # return_needed es una fraccion: 1.0 = +100% = multiplo 2x.
        tiers = [PrizeTier("a", 0.0, 100.0), PrizeTier("b", 1.0, 1_000.0)]
        res = simulate(Policy("5x", "static", leverage=5.0), contest, strat, tiers,
                       n_paths=20_000, seed=9)
        expected = 100.0 * res.prob_reach(1.0) + 900.0 * res.prob_reach(2.0)
        self.assertAlmostEqual(res.expected_prize(), expected, places=6)

    def test_empirical_bootstrap_is_used(self):
        contest = self._contest(days=5)
        daily = np.full(200, 0.01)  # +1% garantizado por sesion a 1x
        strat = StrategySpec(empirical_daily=daily)
        res = simulate(Policy("1x", "static", leverage=1.0), contest, strat,
                       self.TIERS, n_paths=1_000, seed=1)
        self.assertAlmostEqual(res.median_multiple, 1.01**5, places=6)

    def test_adaptive_deleverages_once_target_reached(self):
        """La politica adaptativa debe proteger el puesto, no seguir apostando."""
        contest = self._contest(days=10)
        strat = StrategySpec(sharpe_annual=1.0, sigma_annual=0.20)
        policy = Policy("adaptativa 2x", "adaptive", target_multiple=2.0,
                        protect_leverage=0.25)
        self.assertAlmostEqual(policy.leverage_for(2.5, 5, strat, contest), 0.25)
        behind = policy.leverage_for(1.0, 5, strat, contest)
        further_behind = policy.leverage_for(0.5, 5, strat, contest)
        self.assertGreater(further_behind, behind)
        # Menos dias restantes con el mismo hueco => mas agresivo.
        self.assertGreater(
            policy.leverage_for(1.0, 2, strat, contest),
            policy.leverage_for(1.0, 8, strat, contest),
        )


if __name__ == "__main__":
    unittest.main()
