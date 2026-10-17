#!/usr/bin/env python3
"""Backtest de ruptura del rango de apertura (ORB) sobre futuros de micro indices.

Pensado para MNQ1! / MES1! en barras de 5 minutos. La logica es la misma que
implementa `trading/pine/leap_orb_mnq.pine`, para que lo que veas aqui y lo que
veas en TradingView sean el mismo sistema.

Reglas:
  1. Se define el rango de apertura (OR) con los primeros N minutos de la sesion
     regular (09:30 ET por defecto).
  2. Se coloca una orden stop por encima del maximo del OR y otra por debajo del
     minimo. La primera que salta entra; la otra se cancela.
  3. Stop de perdidas en el lado opuesto del OR (o a K*ATR, configurable).
  4. Objetivo a R multiplos del riesgo, con opcion de trailing por ATR.
  5. Todo se cierra antes del final de la sesion: el concurso solo puntua el P/L
     REALIZADO, asi que una posicion abierta y ganadora no vale nada.

Datos de entrada: CSV exportado de TradingView (boton de exportar en el chart).
Se esperan columnas time/open/high/low/close; los nombres se normalizan solos.
Yahoo Finance esta bloqueado en muchos entornos, asi que no se descarga nada:
o pasas un CSV, o usas --synthetic para validar la maquinaria.

Uso:
    python3 orb_backtest.py --csv MNQ_5m.csv --or-minutes 15 --target-r 2
    python3 orb_backtest.py --synthetic 400 --seed 3
    python3 orb_backtest.py --csv MNQ_5m.csv --grid       # barrido de parametros
"""

from __future__ import annotations

import argparse
import math
from dataclasses import dataclass, replace
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

NY = ZoneInfo("America/New_York")


# --------------------------------------------------------------------------- #
# Configuracion
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class Params:
    or_minutes: int = 15
    session_start: str = "09:30"
    session_end: str = "16:00"
    # Hora limite para abrir posiciones nuevas (ET). Despues solo se gestiona.
    entry_cutoff: str = "12:00"
    # Colchon sobre el extremo del OR, en ticks, para evitar rupturas falsas.
    buffer_ticks: int = 2
    stop_mode: str = "or"  # "or" = lado opuesto del rango | "atr" = K*ATR
    atr_stop_mult: float = 1.0
    target_r: float = 2.0
    # Trailing por ATR una vez alcanzado este multiplo de R (0 = desactivado).
    trail_after_r: float = 0.0
    trail_atr_mult: float = 1.5
    max_trades_per_day: int = 1
    # Filtro de rango: solo operar si el OR mide entre estos multiplos del ATR.
    min_or_atr: float = 0.15
    max_or_atr: float = 1.20
    long_only: bool = False
    tick_size: float = 0.25
    point_value: float = 2.0  # MNQ
    slippage_ticks: float = 1.0
    commission_rt: float = 1.04  # ida y vuelta por contrato, MNQ en TradeStation


@dataclass
class Trade:
    date: str
    side: int  # +1 largo, -1 corto
    entry_time: pd.Timestamp
    entry: float
    stop: float
    exit_time: pd.Timestamp
    exit: float
    reason: str
    risk_points: float
    pnl_points: float

    @property
    def r_multiple(self) -> float:
        return self.pnl_points / self.risk_points if self.risk_points > 0 else 0.0


# --------------------------------------------------------------------------- #
# Carga de datos
# --------------------------------------------------------------------------- #

def load_csv(path: str) -> pd.DataFrame:
    """Lee un CSV de TradingView y devuelve barras indexadas en hora de NY."""
    df = pd.read_csv(path)
    df.columns = [c.strip().lower() for c in df.columns]

    time_col = next((c for c in ("time", "date", "datetime", "timestamp") if c in df), None)
    if time_col is None:
        raise ValueError(f"{path}: no encuentro columna de tiempo en {list(df.columns)}")

    raw = df[time_col]
    if pd.api.types.is_numeric_dtype(raw):
        # TradingView exporta epoch en segundos.
        idx = pd.to_datetime(raw, unit="s", utc=True)
    else:
        idx = pd.to_datetime(raw, utc=True, format="mixed")

    missing = [c for c in ("open", "high", "low", "close") if c not in df.columns]
    if missing:
        raise ValueError(f"{path}: faltan columnas {missing}")

    out = df[["open", "high", "low", "close"]].astype(float)
    out.index = idx.dt.tz_convert(NY)
    out = out[~out.index.duplicated(keep="last")].sort_index()
    return out


def synthetic_bars(
    n_days: int,
    seed: int = 0,
    start_price: float = 25_000.0,
    bar_minutes: int = 5,
    sub_steps: int = 240,
) -> pd.DataFrame:
    """Genera barras de 5m con un paseo aleatorio, para validar la maquinaria.

    Un ORB sobre un paseo aleatorio debe dar esperanza ~0 antes de costes y
    negativa despues. Si el backtest devuelve algo mejor que eso, hay un bug o
    un sesgo de mirada al futuro.

    `sub_steps` importa mas de lo que parece: con pocos sub-pasos el maximo y el
    minimo de cada barra quedan infra-estimados, y como el stop esta mas cerca
    que el objetivo se pierden mas toques de stop que de objetivo. Eso inventa
    una esperanza positiva sobre datos aleatorios que no existe. Con 240
    sub-pasos (1,25 s por paso en barras de 5 min) el artefacto es despreciable:
    la esperanza medida cae de +0,18R a +0,00R.
    Las barras reales no tienen este problema: su maximo y minimo son los
    extremos verdaderos del recorrido.
    """
    rng = np.random.default_rng(seed)
    bars_per_day = int((6.5 * 60) // bar_minutes)
    sigma_bar = 0.20 / math.sqrt(252 * bars_per_day)  # 20% anual

    rows, index = [], []
    price = start_price
    # Se construye el indice en hora local ingenua y se localiza al final:
    # sumar Timedelta(days=1) a un timestamp con zona es aritmetica absoluta y
    # desplazaria la hora de apertura al cambiar el horario de verano.
    day = pd.Timestamp("2025-01-02 09:30")
    made = 0
    while made < n_days:
        if day.weekday() >= 5:
            day += pd.Timedelta(days=1)
            continue
        # Hueco de apertura.
        price *= math.exp(rng.normal(0, sigma_bar * 3))
        for b in range(bars_per_day):
            step = sigma_bar / math.sqrt(sub_steps)
            sub = price * np.exp(np.cumsum(rng.normal(0, step, sub_steps)))
            o, c = price, float(sub[-1])
            rows.append((o, float(max(o, sub.max())), float(min(o, sub.min())), c))
            index.append(day + pd.Timedelta(minutes=bar_minutes * b))
            price = c
        made += 1
        day += pd.Timedelta(days=1)

    df = pd.DataFrame(rows, columns=["open", "high", "low", "close"], index=pd.DatetimeIndex(index))
    df.index = df.index.tz_localize(NY)
    return df.round(2)


# --------------------------------------------------------------------------- #
# Backtest
# --------------------------------------------------------------------------- #

def _daily_atr(daily: pd.DataFrame, length: int = 14) -> pd.Series:
    """ATR diario clasico (Wilder simplificado a media movil)."""
    prev_close = daily["close"].shift(1)
    tr = pd.concat(
        [
            daily["high"] - daily["low"],
            (daily["high"] - prev_close).abs(),
            (daily["low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.rolling(length, min_periods=2).mean()


def backtest(bars: pd.DataFrame, p: Params) -> list[Trade]:
    """Recorre las sesiones y devuelve la lista de operaciones."""
    session = bars.between_time(p.session_start, p.session_end)
    if session.empty:
        raise ValueError(
            "No hay barras en la sesion indicada. Comprueba la zona horaria del CSV "
            f"(se esperan datos que cubran {p.session_start}-{p.session_end} ET)."
        )

    daily = session.resample("1D").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last"}
    ).dropna()
    # shift(1) es obligatorio: el ATR de hoy incluye el rango de hoy, y filtrar
    # con el equivale a elegir las sesiones sabiendo ya como han acabado. Sin
    # este desplazamiento el sistema "gana" incluso sobre datos aleatorios.
    atr = _daily_atr(daily).shift(1)

    tick = p.tick_size
    buffer = p.buffer_ticks * tick
    slip = p.slippage_ticks * tick
    commission_points = p.commission_rt / p.point_value

    trades: list[Trade] = []
    for day, chunk in session.groupby(session.index.normalize()):
        atr_val = atr.get(day, np.nan)
        if not np.isfinite(atr_val) or atr_val <= 0:
            continue  # sin ATR todavia (primeras sesiones)

        or_end = day + pd.Timedelta(
            hours=int(p.session_start[:2]),
            minutes=int(p.session_start[3:]) + p.or_minutes,
        )
        opening = chunk[chunk.index < or_end]
        rest = chunk[chunk.index >= or_end]
        if opening.empty or len(rest) < 2:
            continue

        or_high, or_low = float(opening["high"].max()), float(opening["low"].min())
        or_range = or_high - or_low
        if or_range <= 0:
            continue
        # Filtro de calidad del rango: ni plano ni ya agotado.
        if not (p.min_or_atr <= or_range / atr_val <= p.max_or_atr):
            continue

        cutoff = day + pd.Timedelta(
            hours=int(p.entry_cutoff[:2]), minutes=int(p.entry_cutoff[3:])
        )
        long_trigger, short_trigger = or_high + buffer, or_low - buffer

        n_trades = 0
        position: dict | None = None
        last_ts, last_close = rest.index[-1], float(rest["close"].iloc[-1])

        for ts, bar in rest.iterrows():
            open_, high, low, close = (
                float(bar["open"]), float(bar["high"]), float(bar["low"]), float(bar["close"])
            )

            if position is None:
                if n_trades >= p.max_trades_per_day or ts >= cutoff:
                    continue
                side = 0
                # Si la barra ABRE ya pasado el nivel, una orden stop real se
                # ejecuta en la apertura, no en el nivel. Asumir el nivel es el
                # sesgo clasico de los backtests de ORB: regala los huecos.
                if high >= long_trigger:
                    side, entry = 1, max(long_trigger, open_) + slip
                elif low <= short_trigger and not p.long_only:
                    side, entry = -1, min(short_trigger, open_) - slip
                if side == 0:
                    continue

                if p.stop_mode == "atr":
                    stop = entry - side * p.atr_stop_mult * atr_val
                else:
                    stop = (or_low if side == 1 else or_high) - side * buffer
                risk = abs(entry - stop)
                if risk < tick:
                    continue
                position = {
                    "side": side,
                    "entry": entry,
                    "stop": stop,
                    "risk": risk,
                    "target": entry + side * p.target_r * risk,
                    "entry_ts": ts,
                    "peak": entry,
                    "trailing": False,
                }
                n_trades += 1
                # La barra de entrada puede tocar stop u objetivo. Se asume el
                # peor caso (stop primero): sin datos de tick no hay forma de
                # saber el orden, y el sesgo optimista es el error tipico.
                if (side == 1 and low <= position["stop"]) or (
                    side == -1 and high >= position["stop"]
                ):
                    exit_px = position["stop"] - side * slip
                    trades.append(_close(position, ts, exit_px, "stop", commission_points))
                    position = None
                continue

            side, stop, target = position["side"], position["stop"], position["target"]

            # Trailing: solo se activa tras alcanzar trail_after_r a favor.
            if p.trail_after_r > 0:
                excursion = side * (close - position["entry"]) / position["risk"]
                if excursion >= p.trail_after_r:
                    position["trailing"] = True
                if position["trailing"]:
                    position["peak"] = (
                        max(position["peak"], high) if side == 1 else min(position["peak"], low)
                    )
                    trail = position["peak"] - side * p.trail_atr_mult * atr_val
                    stop = max(stop, trail) if side == 1 else min(stop, trail)
                    position["stop"] = stop

            hit_stop = low <= stop if side == 1 else high >= stop
            hit_target = (high >= target if side == 1 else low <= target) and (
                p.trail_after_r == 0 or not position["trailing"]
            )

            if hit_stop and hit_target:
                # Ambos en la misma barra: se cuenta el stop (peor caso).
                hit_target = False
            if hit_stop:
                # Mismo criterio que en la entrada: si la barra abre pasado el
                # stop, el relleno es la apertura. Es justo la cola izquierda
                # que un backtest ingenuo se inventa que no existe.
                gapped = min(stop, open_) if side == 1 else max(stop, open_)
                trades.append(
                    _close(position, ts, gapped - side * slip, "stop", commission_points)
                )
                position = None
            elif hit_target:
                trades.append(_close(position, ts, target, "objetivo", commission_points))
                position = None

        if position is not None:
            # Cierre forzado al final de la sesion: solo cuenta lo realizado.
            trades.append(
                _close(
                    position,
                    last_ts,
                    last_close - position["side"] * slip,
                    "cierre sesion",
                    commission_points,
                )
            )

    return trades


def _close(pos: dict, ts, exit_px: float, reason: str, commission_points: float) -> Trade:
    side = pos["side"]
    pnl = side * (exit_px - pos["entry"]) - commission_points
    return Trade(
        date=str(pos["entry_ts"].date()),
        side=side,
        entry_time=pos["entry_ts"],
        entry=pos["entry"],
        stop=pos["stop"],
        exit_time=ts,
        exit=exit_px,
        reason=reason,
        risk_points=pos["risk"],
        pnl_points=pnl,
    )


# --------------------------------------------------------------------------- #
# Estadisticas
# --------------------------------------------------------------------------- #

def stats(trades: list[Trade], risk_pct: float = 0.01) -> dict:
    """Metricas del sistema. `risk_pct` define la escala de la curva de equity."""
    if not trades:
        return {"n": 0}

    r = np.array([t.r_multiple for t in trades])
    wins, losses = r[r > 0], r[r <= 0]

    equity = np.cumprod(1.0 + risk_pct * r)
    peak = np.maximum.accumulate(equity)
    max_dd = float(np.max((peak - equity) / peak)) if len(equity) else 0.0

    by_day: dict[str, float] = {}
    for t in trades:
        by_day[t.date] = by_day.get(t.date, 0.0) + t.r_multiple
    daily = np.array(list(by_day.values()))
    sd = float(np.std(daily, ddof=1)) if len(daily) > 1 else 0.0

    return {
        "n": len(trades),
        "sesiones": len(by_day),
        "win_rate": float(np.mean(r > 0)),
        "avg_r": float(np.mean(r)),
        "avg_win_r": float(np.mean(wins)) if len(wins) else 0.0,
        "avg_loss_r": float(np.mean(losses)) if len(losses) else 0.0,
        "expectancy_r": float(np.mean(r)),
        "profit_factor": (
            float(wins.sum() / abs(losses.sum())) if len(losses) and losses.sum() != 0 else math.inf
        ),
        "total_r": float(r.sum()),
        "max_dd_pct": max_dd,
        "equity_final": float(equity[-1]),
        # Sharpe anualizado de la curva a `risk_pct` por operacion.
        "sharpe_annual": (
            float(np.mean(daily) * risk_pct / (sd * risk_pct) * math.sqrt(252)) if sd > 0 else 0.0
        ),
        "vol_annual": float(sd * risk_pct * math.sqrt(252)),
    }


def print_stats(s: dict, label: str = "") -> None:
    if s.get("n", 0) == 0:
        print(f"{label}: sin operaciones")
        return
    print(f"\n=== RESULTADOS {label} ===")
    print(f"Operaciones: {s['n']} en {s['sesiones']} sesiones")
    print(f"Acierto: {s['win_rate']:.1%} | media {s['avg_r']:+.3f}R "
          f"(ganadora {s['avg_win_r']:+.2f}R / perdedora {s['avg_loss_r']:+.2f}R)")
    print(f"Profit factor: {s['profit_factor']:.2f} | total {s['total_r']:+.1f}R")
    print(f"A 1% de riesgo por operacion: equity x{s['equity_final']:.3f}, "
          f"maximo drawdown {s['max_dd_pct']:.1%}")
    print(f"Sharpe anual {s['sharpe_annual']:.2f} | vol anual {s['vol_annual']:.1%}")


def save_trades(trades: list[Trade], path: str) -> None:
    rows = [
        {
            "date": t.date,
            "side": "largo" if t.side == 1 else "corto",
            "entry_time": t.entry_time.isoformat(),
            "entry": round(t.entry, 2),
            "stop": round(t.stop, 2),
            "exit_time": t.exit_time.isoformat(),
            "exit": round(t.exit, 2),
            "reason": t.reason,
            "risk_points": round(t.risk_points, 2),
            "pnl_points": round(t.pnl_points, 2),
            "r_multiple": round(t.r_multiple, 4),
        }
        for t in trades
    ]
    pd.DataFrame(rows).to_csv(path, index=False)
    print(f"\nOperaciones guardadas en {path}")
    print(f"Alimenta el Monte Carlo con: python3 contest_sim.py --from-trades {path} --days 11")


def run_grid(bars: pd.DataFrame, base: Params) -> None:
    """Barrido de parametros. Ojo: cuanto mas fino el barrido, mas sobreajuste."""
    print("\n=== BARRIDO DE PARAMETROS ===")
    print(f"{'OR min':>7} {'target R':>9} {'stop':>5} {'n':>5} {'acierto':>8} "
          f"{'media R':>9} {'total R':>9} {'Sharpe':>7}")
    combos = []
    for or_min in (5, 15, 30, 60):
        for target_r in (1.0, 2.0, 3.0, 0.0):
            for stop_mode in ("or", "atr"):
                p = replace(base, or_minutes=or_min, stop_mode=stop_mode,
                            target_r=target_r if target_r > 0 else 99.0,
                            trail_after_r=1.0 if target_r == 0 else 0.0)
                s = stats(backtest(bars, p))
                if s.get("n", 0) == 0:
                    continue
                label = "trail" if target_r == 0 else f"{target_r:.0f}"
                combos.append((s["total_r"], or_min, label, stop_mode, s))
                print(f"{or_min:>7} {label:>9} {stop_mode:>5} {s['n']:>5} "
                      f"{s['win_rate']:>7.1%} {s['avg_r']:>+8.3f} {s['total_r']:>+8.1f} "
                      f"{s['sharpe_annual']:>7.2f}")
    if combos:
        best = max(combos)
        print(f"\nMejor por R total: OR {best[1]}min, objetivo {best[2]}, stop {best[3]}")
        print("Recuerda: el mejor de un barrido esta sobreajustado por construccion. "
              "Valida fuera de muestra antes de creerte el numero.")


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Backtest ORB para MNQ/MES.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--csv", help="CSV exportado de TradingView (5m, MNQ1!)")
    src.add_argument("--synthetic", type=int, help="Numero de sesiones sinteticas")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--or-minutes", type=int, default=15)
    ap.add_argument("--target-r", type=float, default=2.0)
    ap.add_argument("--stop-mode", choices=("or", "atr"), default="or")
    ap.add_argument("--atr-stop-mult", type=float, default=1.0)
    ap.add_argument("--trail-after-r", type=float, default=0.0)
    ap.add_argument("--max-trades", type=int, default=1)
    ap.add_argument("--entry-cutoff", default="12:00")
    ap.add_argument("--long-only", action="store_true")
    ap.add_argument("--point-value", type=float, default=2.0, help="MNQ=2, MES=5")
    ap.add_argument("--slippage-ticks", type=float, default=1.0)
    ap.add_argument("--commission-rt", type=float, default=1.04)
    ap.add_argument("--out", default="trades.csv")
    ap.add_argument("--grid", action="store_true", help="Barrido de parametros")
    args = ap.parse_args()

    bars = synthetic_bars(args.synthetic, args.seed) if args.synthetic else load_csv(args.csv)
    label = f"sinteticos ({args.synthetic} sesiones)" if args.synthetic else args.csv
    print(f"Barras: {len(bars)} | {bars.index[0]} -> {bars.index[-1]}")

    p = Params(
        or_minutes=args.or_minutes,
        target_r=args.target_r,
        stop_mode=args.stop_mode,
        atr_stop_mult=args.atr_stop_mult,
        trail_after_r=args.trail_after_r,
        max_trades_per_day=args.max_trades,
        entry_cutoff=args.entry_cutoff,
        long_only=args.long_only,
        point_value=args.point_value,
        slippage_ticks=args.slippage_ticks,
        commission_rt=args.commission_rt,
    )

    if args.grid:
        run_grid(bars, p)
        return

    trades = backtest(bars, p)
    print_stats(stats(trades), label)
    if trades:
        save_trades(trades, args.out)
    if args.synthetic:
        print("\nDatos aleatorios: la esperanza DEBE rondar el coste de operar. "
              "Si sale muy positiva, sospecha de un sesgo en el backtest.")


if __name__ == "__main__":
    main()
