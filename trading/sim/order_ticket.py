#!/usr/bin/env python3
"""Calcula la orden exacta a partir del rango de apertura ya formado.

A las 10:00 ET, cuando el rango de 09:30-10:00 esta cerrado, le pasas el maximo y
el minimo y te devuelve las dos ordenes completas: entrada, stop, objetivo,
contratos y riesgo en dolares. No hay nada que decidir a mano.

    python3 order_ticket.py --or-high 27450 --or-low 27290
    python3 order_ticket.py --or-high 27450 --or-low 27290 --atr 550 --equity 118000

El stop y el objetivo NO son niveles que se eligen: salen del rango. El stop va al
lado opuesto del rango (mas el colchon) y el objetivo a un multiplo del riesgo.
Por eso no se pueden dar de antemano, solo una vez formado el rango.
"""

from __future__ import annotations

import argparse

TICK = 0.25


def round_tick(price: float) -> float:
    return round(price / TICK) * TICK


def ticket(
    or_high: float,
    or_low: float,
    equity: float,
    margin: float,
    point_value: float,
    target_r: float,
    risk_pct: float,
    buffer_ticks: int,
    atr: float | None,
) -> None:
    buf = buffer_ticks * TICK
    or_range = or_high - or_low

    print(f"\nRango de apertura: {or_low:,.2f} - {or_high:,.2f}  ({or_range:.2f} puntos)")

    if atr is not None and atr > 0:
        ratio = or_range / atr
        ok = 0.15 <= ratio <= 1.20
        estado = "VALIDO" if ok else "RECHAZADO por el filtro"
        print(f"Rango / ATR diario: {ratio:.2f}  ->  {estado}")
        if not ok:
            print("  El filtro rechaza la sesion. Opera 1 CONTRATO para registrar la")
            print("  sesion de cara al minimo de cualificacion, con el mismo stop.")

    max_contracts_margin = int(equity // margin)

    for side, label in ((1, "LARGO (rotura al alza)"), (-1, "CORTO (rotura a la baja)")):
        if side == 1:
            entry = round_tick(or_high + buf)
            stop = round_tick(or_low - buf)
        else:
            entry = round_tick(or_low - buf)
            stop = round_tick(or_high + buf)

        risk_points = abs(entry - stop)
        target = round_tick(entry + side * target_r * risk_points)
        risk_per_contract = risk_points * point_value

        wanted = int((equity * risk_pct / 100.0) // risk_per_contract)
        contracts = min(wanted, max_contracts_margin)
        limited = contracts < wanted

        risk_cash = contracts * risk_per_contract
        reward_cash = risk_cash * target_r
        notional = contracts * entry * point_value

        print(f"\n--- {label} ---")
        print(f"  Entrada (orden STOP):  {entry:>10,.2f}")
        print(f"  Stop de perdidas:      {stop:>10,.2f}   ({risk_points:.2f} pts, "
              f"{risk_per_contract:,.2f}$/contrato)")
        print(f"  Objetivo ({target_r:g}R):         {target:>10,.2f}   "
              f"(+{abs(target - entry):.2f} pts)")
        print(f"  Contratos:             {contracts:>10}"
              + (f"   <- limitado por margen (querias {wanted})" if limited else ""))
        print(f"  Riesgo:                {risk_cash:>10,.0f}$   "
              f"({risk_cash / equity:.1%} de la cuenta)")
        print(f"  Si acierta:            {reward_cash:>10,.0f}$   "
              f"({reward_cash / equity:+.1%})")
        print(f"  Nocional:              {notional:>10,.0f}$   "
              f"({notional / equity:.1f}x apalancamiento)")

    print("\nOperativa: las dos ordenes STOP a la vez. La que salte primero entra y")
    print("la otra se cancela. No elijas direccion: la elige el precio.")
    print("Sin entradas nuevas despues de las 12:00 ET. Todo cerrado antes de las 16:00 ET")
    print("(solo puntua el P/L realizado).")


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Orden exacta a partir del rango de apertura.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    ap.add_argument("--or-high", type=float, required=True, help="Maximo del rango de apertura")
    ap.add_argument("--or-low", type=float, required=True, help="Minimo del rango de apertura")
    ap.add_argument("--equity", type=float, default=100_000.0)
    ap.add_argument("--margin", type=float, default=1_200.0, help="Margen intradia por contrato")
    ap.add_argument("--point-value", type=float, default=2.0, help="MNQ=2, MES=5")
    ap.add_argument("--target-r", type=float, default=2.0)
    ap.add_argument("--risk-pct", type=float, default=25.0, help="Riesgo objetivo por operacion")
    ap.add_argument("--buffer-ticks", type=int, default=2)
    ap.add_argument("--atr", type=float, help="ATR(14) diario, para aplicar el filtro")
    args = ap.parse_args()

    if args.or_high <= args.or_low:
        raise SystemExit("--or-high debe ser mayor que --or-low")

    ticket(args.or_high, args.or_low, args.equity, args.margin, args.point_value,
           args.target_r, args.risk_pct, args.buffer_ticks, args.atr)


if __name__ == "__main__":
    main()
