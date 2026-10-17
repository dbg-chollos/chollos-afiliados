"""Comprobaciones del backtest ORB.

El test que de verdad importa es `test_no_edge_on_random_data`: un sistema de
rupturas sobre un paseo aleatorio NO puede ganar dinero. Si alguna vez pasa a
verde con esperanza claramente positiva, hay un sesgo nuevo en el backtest
(mirada al futuro, rellenos regalados o extremos intrabarra mal muestreados).

    python3 -m unittest discover -s trading/sim/tests -v
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from orb_backtest import (  # noqa: E402
    NY,
    Params,
    backtest,
    stats,
    synthetic_bars,
)


def pooled_r(seeds: range, params: Params, days: int = 250, **kw) -> np.ndarray:
    out: list[float] = []
    for s in seeds:
        out += [t.r_multiple for t in backtest(synthetic_bars(days, seed=s, **kw), params)]
    return np.array(out)


class TestSyntheticData(unittest.TestCase):
    def test_session_bounds_survive_dst(self):
        """Las sesiones deben empezar siempre a las 09:30 ET, invierno o verano."""
        bars = synthetic_bars(300, seed=1, sub_steps=4)
        times = bars.index.strftime("%H:%M")
        self.assertEqual(sorted(set(times))[0], "09:30")
        self.assertEqual(sorted(set(times))[-1], "15:55")
        # Y debe haber datos a ambos lados del cambio de hora.
        offsets = {ts.utcoffset() for ts in bars.index}
        self.assertEqual(len(offsets), 2)

    def test_ohlc_coherent(self):
        bars = synthetic_bars(20, seed=2, sub_steps=8)
        self.assertTrue((bars["high"] >= bars[["open", "close"]].max(axis=1) - 1e-9).all())
        self.assertTrue((bars["low"] <= bars[["open", "close"]].min(axis=1) + 1e-9).all())


class TestNoLookahead(unittest.TestCase):
    NO_COST = Params(slippage_ticks=0.0, commission_rt=0.0)

    def test_no_edge_on_random_data(self):
        """Esperanza indistinguible de cero sobre un paseo aleatorio sin costes."""
        r = pooled_r(range(12), self.NO_COST, sub_steps=240)
        se = r.std(ddof=1) / np.sqrt(len(r))
        t_stat = r.mean() / se
        self.assertGreater(len(r), 1_500, "muestra insuficiente para concluir")
        self.assertLess(
            abs(t_stat), 2.6,
            f"sesgo detectado: media {r.mean():+.4f}R, t={t_stat:+.2f}. "
            "El backtest esta ganando sobre datos aleatorios.",
        )

    def test_intrabar_undersampling_creates_fake_edge(self):
        """Documenta el artefacto: pocos sub-pasos inventan ventaja."""
        coarse = pooled_r(range(8), self.NO_COST, sub_steps=4)
        fine = pooled_r(range(8), self.NO_COST, sub_steps=240)
        self.assertGreater(coarse.mean(), fine.mean() + 0.05)

    def test_costs_make_expectancy_worse(self):
        with_costs = pooled_r(range(8), Params(), sub_steps=240)
        without = pooled_r(range(8), self.NO_COST, sub_steps=240)
        self.assertLess(with_costs.mean(), without.mean())


class TestFills(unittest.TestCase):
    """Rellenos con hueco: si la barra abre pasado el nivel, se paga la apertura."""

    def _bars(self, rows: list[tuple[str, float, float, float, float]]) -> pd.DataFrame:
        idx = pd.DatetimeIndex([pd.Timestamp(f"2025-03-10 {t}") for t, *_ in rows])
        df = pd.DataFrame(
            [r[1:] for r in rows], columns=["open", "high", "low", "close"], index=idx
        )
        df.index = df.index.tz_localize(NY)
        return df

    def _session(self, day_rows):
        """Construye varias sesiones para que el ATR tenga historia."""
        frames = []
        for d in range(1, 20):
            idx = pd.date_range(f"2025-03-{d:02d} 09:30", periods=78, freq="5min")
            base = 100.0 + d
            df = pd.DataFrame(
                {"open": base, "high": base + 2, "low": base - 2, "close": base},
                index=idx,
            )
            frames.append(df)
        last = day_rows.copy()
        frames.append(last)
        out = pd.concat(frames)
        out.index = out.index.tz_localize(NY) if out.index.tz is None else out.index
        return out

    def test_gap_through_stop_pays_the_open(self):
        """Un hueco por debajo del stop debe producir una perdida mayor que 1R."""
        day = pd.date_range("2025-03-25 09:30", periods=78, freq="5min")
        o = np.full(78, 120.0)
        h = np.full(78, 120.0)
        low = np.full(78, 120.0)
        c = np.full(78, 120.0)
        # Rango de apertura 09:30-09:45 entre 118 y 122.
        h[0:3] = 122.0
        low[0:3] = 118.0
        # Ruptura al alza en la cuarta barra.
        h[3] = 123.0
        o[3] = 121.0
        c[3] = 122.5
        low[3] = 121.0
        # Hueco brutal a la baja: abre en 100, muy por debajo del stop (117,5).
        o[4] = 100.0
        h[4] = 100.0
        low[4] = 99.0
        c[4] = 99.5
        o[5:], h[5:], low[5:], c[5:] = 99.5, 99.5, 99.5, 99.5
        frame = pd.DataFrame({"open": o, "high": h, "low": low, "close": c}, index=day)
        bars = self._session(frame)

        p = Params(or_minutes=15, tick_size=0.25, buffer_ticks=0, slippage_ticks=0,
                   commission_rt=0.0, min_or_atr=0.0, max_or_atr=99.0, stop_mode="or")
        trades = [t for t in backtest(bars, p) if t.date == "2025-03-25"]
        self.assertEqual(len(trades), 1)
        trade = trades[0]
        self.assertEqual(trade.reason, "stop")
        self.assertAlmostEqual(trade.exit, 100.0, places=6)
        self.assertLess(trade.r_multiple, -1.5,
                        "el hueco debe costar mas de 1R, no exactamente 1R")


class TestStats(unittest.TestCase):
    def test_stats_empty(self):
        self.assertEqual(stats([])["n"], 0)

    def test_stats_consistent(self):
        trades = backtest(synthetic_bars(120, seed=4, sub_steps=60), Params())
        s = stats(trades)
        self.assertEqual(s["n"], len(trades))
        self.assertGreaterEqual(s["win_rate"], 0.0)
        self.assertLessEqual(s["win_rate"], 1.0)
        self.assertGreaterEqual(s["max_dd_pct"], 0.0)


if __name__ == "__main__":
    unittest.main()
