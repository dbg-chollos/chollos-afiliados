#!/usr/bin/env python3
"""Elige el contrato adecuado para el concurso a partir de la lista disponible.

El criterio no es "cual sube mas". Son tres cosas medibles:

  1. VOLATILIDAD. `L* = sqrt(2 ln m)/(sigma sqrt(T))`: cuanta mas volatilidad
     tiene el subyacente, menos apalancamiento necesitas para el mismo objetivo.
  2. TOPE POR MARGEN. `nocional/margen` por contrato. Si el `L*` que necesitas
     esta por encima del tope, ese contrato no puede llevarte al objetivo.
  3. GRANULARIDAD. Si un solo contrato ya son 5x de apalancamiento sobre tu
     cuenta, no puedes ajustar el tamano: saltas de 5x a 10x sin nada en medio.
     Es la razon por la que los micros ganan a los contratos completos.

Los valores por punto son especificaciones de CME y son exactos. Las
volatilidades y los margenes son ESTIMACIONES: comprueba el margen real en las
especificaciones del contrato dentro de la cuenta del concurso y ajustalo con
--margin-scale o editando la tabla.

Uso:
    python3 instrument_selector.py --equity 100000 --days 11 --target 2
"""

from __future__ import annotations

import argparse
import math
from dataclasses import dataclass

from contest_sim import optimal_leverage


@dataclass
class Instrument:
    symbol: str
    name: str
    point_value: float   # $ por punto entero (especificacion CME, exacta)
    price: float         # ultimo precio visto
    sigma: float         # volatilidad anual estimada
    margin: float        # margen intradia estimado por contrato ($)
    tick: float          # tamano minimo de salto
    liquidity: str       # cualitativo: cuenta para el deslizamiento

    @property
    def notional(self) -> float:
        return self.price * self.point_value

    @property
    def margin_cap(self) -> float:
        return self.notional / self.margin

    @property
    def tick_value(self) -> float:
        return self.tick * self.point_value


# Precios de la lista de seguimiento del 29 jul 2026, cierre.
# Volatilidades anualizadas aproximadas del regimen actual; el crudo esta
# elevado (movio +6,56% en la sesion).
INSTRUMENTS = [
    Instrument("MNQ1!", "Micro Nasdaq-100",  2.0,    27_342.00, 0.25,  1_200, 0.25, "excelente"),
    Instrument("NQ1!",  "Nasdaq-100",       20.0,    27_342.00, 0.25, 12_000, 0.25, "excelente"),
    Instrument("MES1!", "Micro S&P 500",     5.0,     7_351.25, 0.19,    800, 0.25, "excelente"),
    Instrument("ES1!",  "S&P 500",          50.0,     7_351.25, 0.19,  8_000, 0.25, "excelente"),
    Instrument("MYM1!", "Micro Dow",         0.5,    51_765.00, 0.17,    600, 1.00, "buena"),
    Instrument("YM1!",  "Dow",               5.0,    51_765.00, 0.17,  6_000, 1.00, "buena"),
    Instrument("MCL1!", "Micro WTI",       100.0,        84.46, 0.45,    750, 0.01, "media"),
    Instrument("CL1!",  "WTI",           1_000.0,        84.46, 0.45,  7_500, 0.01, "excelente"),
    Instrument("MGC1!", "Micro Oro",        10.0,     4_036.30, 0.17,  1_000, 0.10, "buena"),
    Instrument("GC1!",  "Oro",             100.0,     4_036.30, 0.17, 10_000, 0.10, "excelente"),
    Instrument("MBT1!", "Micro Bitcoin",     0.1,    63_900.00, 0.55,  2_400, 5.00, "media"),
    Instrument("M6E1!", "Micro EUR/USD", 12_500.0,        1.1474, 0.08,   350, 0.0001, "buena"),
]


def analyse(inst: Instrument, equity: float, days: int, target: float) -> dict:
    lstar = optimal_leverage(target, inst.sigma, days)
    contracts = lstar * equity / inst.notional
    # Apalancamiento que aporta UN solo contrato: mide la granularidad.
    lev_per_contract = inst.notional / equity
    max_contracts_margin = math.floor(equity / inst.margin)
    return {
        "inst": inst,
        "lstar": lstar,
        "contracts": contracts,
        "lev_per_contract": lev_per_contract,
        "feasible": lstar <= inst.margin_cap,
        "max_contracts_margin": max_contracts_margin,
        # Con menos de ~4 contratos no puedes afinar el tamano.
        "granular": contracts >= 4,
    }


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Compara contratos disponibles para el concurso.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    ap.add_argument("--equity", type=float, default=100_000.0)
    ap.add_argument("--days", type=int, default=11)
    ap.add_argument("--target", type=float, default=2.0, help="Multiplo objetivo")
    ap.add_argument("--margin-scale", type=float, default=1.0,
                    help="Multiplica todos los margenes estimados (ajuste global)")
    args = ap.parse_args()

    rows = []
    for inst in INSTRUMENTS:
        if args.margin_scale != 1.0:
            inst = Instrument(**{**inst.__dict__, "margin": inst.margin * args.margin_scale})
        rows.append(analyse(inst, args.equity, args.days, args.target))

    print(f"\nObjetivo {args.target:g}x en {args.days} sesiones | cuenta {args.equity:,.0f}$\n")
    print(f"{'simbolo':<8} {'nocional':>10} {'vol':>6} {'L* nec.':>8} {'tope':>7} "
          f"{'contratos':>10} {'1 contr.':>9} {'$/tick':>7} {'veredicto':<28}")
    print("-" * 105)

    for r in sorted(rows, key=lambda x: (not x["feasible"], -x["inst"].sigma)):
        i = r["inst"]
        if not r["feasible"]:
            verdict = f"NO: necesita {r['lstar']:.0f}x, tope {i.margin_cap:.0f}x"
        elif not r["granular"]:
            verdict = f"granularidad mala ({r['contracts']:.1f} contr.)"
        else:
            verdict = f"viable, liquidez {i.liquidity}"
        print(f"{i.symbol:<8} {i.notional:>9,.0f}$ {i.sigma:>5.0%} {r['lstar']:>7.1f}x "
              f"{i.margin_cap:>6.1f}x {r['contracts']:>10.1f} "
              f"{r['lev_per_contract']:>8.2f}x {i.tick_value:>6.2f}$ {verdict:<28}")

    print("\nCriterios: 'tope' = nocional/margen (techo duro). '1 contr.' = apalancamiento")
    print("que aporta un solo contrato; por encima de ~1x no puedes afinar el tamano.")
    print("Volatilidades y margenes son estimaciones: verifica el margen en la cuenta.")

    best = [r for r in rows if r["feasible"] and r["granular"]]
    if best:
        # Entre los viables, el mejor es el que deja mas margen de maniobra
        # (mas holgura entre el L* necesario y el tope) con buena liquidez.
        best.sort(key=lambda r: -(r["inst"].margin_cap / r["lstar"]))
        top = best[0]
        print(f"\nMayor holgura: {top['inst'].symbol} "
              f"({top['inst'].margin_cap / top['lstar']:.1f}x de margen sobre lo necesario, "
              f"{top['contracts']:.0f} contratos)")


if __name__ == "__main__":
    main()
