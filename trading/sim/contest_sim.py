#!/usr/bin/env python3
"""Simulador de torneo para The Leap (concurso de paper trading de TradingView).

Responde a la unica pregunta que importa en un concurso con premios por ranking:
cuanto riesgo hay que asumir para maximizar la probabilidad de acabar en premio.

El modelo:

  - La cuenta empieza con `equity0` y hay `days` sesiones habiles restantes.
  - La estrategia sin apalancar tiene un Sharpe anualizado `S` y una volatilidad
    anualizada `sigma`. Aplicar apalancamiento L multiplica ambas: media L*mu,
    volatilidad L*sigma. Ese es el unico mando de control real.
  - El premio depende del ranking, no del beneficio absoluto, asi que el pago es
    convexo: una funcion escalonada sobre la rentabilidad final. Perder el 100%
    de una cuenta de papel cuesta exactamente lo mismo que perder el 5%.

Resultado analitico central (ver PLAN_TORNEO.md para la derivacion): si el log de
la equity es un browniano con deriva, la probabilidad de alcanzar un multiplo
objetivo `m` antes del cierre se maximiza con

    L* = sqrt(2 * ln m) / (sigma * sqrt(T))

y esa probabilidad maxima vale

    P* = Phi(S * sqrt(T) - sqrt(2 * ln m))

L* NO depende de la deriva: tu edge cambia la probabilidad que consigues, no lo
agresivo que te conviene ser. El Monte Carlo de este script anade lo que la
formula ignora: ruina discreta, colas gruesas, limite de margen y politicas de
riesgo que cambian dia a dia segun vas por delante o por detras del corte.

Uso rapido:

    python3 contest_sim.py --days 12
    python3 contest_sim.py --days 12 --sharpe 0 --targets 1.5 2 3 5
    python3 contest_sim.py --days 12 --compare-policies
    python3 contest_sim.py --days 12 --from-trades trades_mnq.csv
"""

from __future__ import annotations

import argparse
import csv
import math
from dataclasses import dataclass, field

import numpy as np

TRADING_DAYS_YEAR = 252.0


# --------------------------------------------------------------------------- #
# Resultados analiticos (browniano geometrico, sin barrera de ruina)
# --------------------------------------------------------------------------- #

def optimal_leverage(target: float, sigma_annual: float, days: float) -> float:
    """Apalancamiento que maximiza P(equity_final >= target * equity_inicial).

    L* = sqrt(2 ln m) / (sigma sqrt(T)). Independiente de la deriva.
    """
    if target <= 1.0:
        return 0.0
    horizon = days / TRADING_DAYS_YEAR
    return math.sqrt(2.0 * math.log(target)) / (sigma_annual * math.sqrt(horizon))


def prob_target_analytic(
    target: float,
    sharpe: float,
    sigma_annual: float,
    days: float,
    leverage: float,
) -> float:
    """P(alcanzar el multiplo objetivo al cierre) para un apalancamiento dado.

    log-equity ~ N((L mu - L^2 sigma^2 / 2) T, L^2 sigma^2 T).
    """
    if target <= 0.0:
        return 1.0
    if leverage <= 0.0:
        return 1.0 if target <= 1.0 else 0.0
    horizon = days / TRADING_DAYS_YEAR
    mu = sharpe * sigma_annual
    drift = (leverage * mu - 0.5 * leverage**2 * sigma_annual**2) * horizon
    vol = leverage * sigma_annual * math.sqrt(horizon)
    z = (drift - math.log(target)) / vol
    return 0.5 * math.erfc(-z / math.sqrt(2.0))


def prob_target_at_optimum(target: float, sharpe: float, days: float) -> float:
    """P* = Phi(S sqrt(T) - sqrt(2 ln m)), el techo alcanzable con L = L*."""
    if target <= 1.0:
        return 1.0
    horizon = days / TRADING_DAYS_YEAR
    z = sharpe * math.sqrt(horizon) - math.sqrt(2.0 * math.log(target))
    return 0.5 * math.erfc(-z / math.sqrt(2.0))


def kelly_leverage(sharpe: float, sigma_annual: float) -> float:
    """Kelly para lognormal: L = mu / sigma^2 = S / sigma. Maximiza crecimiento."""
    return sharpe / sigma_annual if sigma_annual > 0 else 0.0


# --------------------------------------------------------------------------- #
# Configuracion del concurso y de la estrategia
# --------------------------------------------------------------------------- #

@dataclass
class ContestSpec:
    """Parametros del concurso y del vehiculo operado."""

    equity0: float = 100_000.0
    days: int = 12
    # MNQ (Micro E-mini Nasdaq-100): 2 $ por punto, tick 0.25 = 0.50 $.
    point_value: float = 2.0
    margin_per_contract: float = 2_500.0
    # Nivel del indice, para calcular el nocional por contrato.
    price: float = 25_000.0
    # Nivel de equity por debajo del cual la cuenta esta muerta a efectos de
    # concurso (margin call / imposible recuperar).
    ruin_fraction: float = 0.10
    # Tope de apalancamiento que te impones tu (aparte del limite de margen).
    max_leverage_cap: float = 40.0
    # Distancia media del stop como fraccion del precio (0.003 = 0.30%).
    # Convierte "riesgo por operacion" en "apalancamiento nocional".
    stop_pct: float = 0.003
    # Escala de referencia de "1x" en modo empirico: 1% de la equity por trade.
    risk_unit: float = 0.01

    @property
    def notional_per_contract(self) -> float:
        return self.price * self.point_value

    @property
    def margin_leverage_cap(self) -> float:
        """Apalancamiento maximo que sostiene el margen.

        Con margen `m` por contrato y nocional `n` por contrato, el maximo de
        contratos es equity/m y el nocional total equity*n/m: el tope es n/m y
        no depende del tamano de la cuenta. Para MNQ a 25.000 con 2.500 $ de
        margen son 20x.
        """
        if self.margin_per_contract <= 0:
            return math.inf
        return self.notional_per_contract / self.margin_per_contract

    @property
    def effective_leverage_cap(self) -> float:
        return min(self.max_leverage_cap, self.margin_leverage_cap)

    @property
    def risk_leverage_cap(self) -> float:
        """Tope en unidades de riesgo por operacion (modo empirico).

        Una operacion que arriesga una fraccion `r` de la cuenta con un stop a
        `stop_pct` del precio mueve un nocional de r/stop_pct veces la cuenta.
        El margen exige r/stop_pct <= n/m, o sea r <= (n/m)*stop_pct. Dividido
        por risk_unit da el multiplo de "1x" permitido: con stop del 0,30% y
        tope de 20x, el maximo es 6% de riesgo por operacion.
        """
        cap_risk_frac = self.margin_leverage_cap * self.stop_pct
        return min(self.max_leverage_cap, cap_risk_frac / self.risk_unit)

    def cap_for(self, empirical: bool) -> float:
        """Tope aplicable segun el modo de simulacion."""
        return self.risk_leverage_cap if empirical else self.effective_leverage_cap


@dataclass
class StrategySpec:
    """Estadisticas de la estrategia SIN apalancar (a 1x)."""

    sharpe_annual: float = 1.0
    sigma_annual: float = 0.20
    # Grados de libertad de la t de Student para las colas. df alto -> normal.
    tail_df: float = 4.0
    # Retornos diarios sin apalancar tomados de un backtest real (opcional).
    empirical_daily: np.ndarray | None = None


@dataclass
class PrizeTier:
    """Un escalon de premio: cuanta rentabilidad hace falta y cuanto paga."""

    name: str
    return_needed: float  # 0.60 = +60%
    prize_usd: float

    @property
    def target_multiple(self) -> float:
        return 1.0 + self.return_needed


# Cortes POR DEFECTO: son SUPOSICIONES, no datos oficiales. TradingView no
# publica el beneficio del participante numero 250. Estan calibrados a la vista
# de ediciones pasadas de The Leap y hay que ajustarlos con --cut/--prize segun
# lo que veas en la clasificacion en vivo.
DEFAULT_TIERS = [
    PrizeTier("top-250 (corte de premio)", 0.60, 200.0),
    PrizeTier("top-50", 2.00, 500.0),
    PrizeTier("top-10", 5.00, 1_500.0),
    PrizeTier("top-3", 10.00, 5_000.0),
]


# --------------------------------------------------------------------------- #
# Politicas de riesgo
# --------------------------------------------------------------------------- #

@dataclass
class Policy:
    """Como se decide el apalancamiento cada dia."""

    name: str
    kind: str  # "static" | "adaptive" | "kelly"
    leverage: float = 1.0
    target_multiple: float = 2.0
    # Apalancamiento al que se baja una vez el objetivo ya esta conseguido.
    protect_leverage: float = 0.5

    def leverage_for(
        self,
        equity_multiple: float,
        days_left: int,
        strat: StrategySpec,
        contest: ContestSpec,
        empirical: bool = False,
    ) -> float:
        if self.kind == "static":
            lev = self.leverage
        elif self.kind == "kelly":
            lev = kelly_leverage(strat.sharpe_annual, strat.sigma_annual)
        elif self.kind == "adaptive":
            # Recalcula L* sobre el hueco que queda y el tiempo que queda.
            # Ir por detras del objetivo => mas agresivo (bold play).
            # Estar por delante => proteger el puesto (timid play).
            if equity_multiple >= self.target_multiple:
                lev = self.protect_leverage
            else:
                remaining = self.target_multiple / max(equity_multiple, 1e-9)
                lev = optimal_leverage(remaining, strat.sigma_annual, max(days_left, 1))
        else:  # pragma: no cover - kind validado en el parser
            raise ValueError(f"politica desconocida: {self.kind}")
        return float(np.clip(lev, 0.0, contest.cap_for(empirical)))


# --------------------------------------------------------------------------- #
# Motor Monte Carlo
# --------------------------------------------------------------------------- #

@dataclass
class SimResult:
    policy: str
    final_multiple: np.ndarray
    ruined: np.ndarray
    mean_leverage: float
    tiers: list[PrizeTier] = field(default_factory=list)

    def prob_reach(self, target_multiple: float) -> float:
        return float(np.mean(self.final_multiple >= target_multiple))

    @property
    def prob_ruin(self) -> float:
        return float(np.mean(self.ruined))

    @property
    def median_multiple(self) -> float:
        return float(np.median(self.final_multiple))

    def expected_prize(self) -> float:
        """E[premio] = suma de (premio marginal del escalon) * P(alcanzarlo).

        Los escalones son anidados: quien llega a top-3 tambien cobra los de
        abajo, asi que el valor esperado se acumula por diferencias.
        """
        tiers = sorted(self.tiers, key=lambda t: t.return_needed)
        total = 0.0
        prev_prize = 0.0
        for tier in tiers:
            total += (tier.prize_usd - prev_prize) * self.prob_reach(tier.target_multiple)
            prev_prize = tier.prize_usd
        return total


def _daily_shocks(
    rng: np.random.Generator, strat: StrategySpec, n_paths: int, days: int
) -> np.ndarray:
    """Retornos diarios sin apalancar, con colas gruesas o bootstrap empirico."""
    if strat.empirical_daily is not None and len(strat.empirical_daily) > 0:
        return rng.choice(strat.empirical_daily, size=(n_paths, days), replace=True)

    sigma_d = strat.sigma_annual / math.sqrt(TRADING_DAYS_YEAR)
    mu_d = strat.sharpe_annual * strat.sigma_annual / TRADING_DAYS_YEAR
    df = strat.tail_df
    if df > 2.0:
        raw = rng.standard_t(df, size=(n_paths, days))
        raw /= math.sqrt(df / (df - 2.0))  # normaliza a varianza 1
    else:
        raw = rng.standard_normal(size=(n_paths, days))
    return mu_d + sigma_d * raw


def simulate(
    policy: Policy,
    contest: ContestSpec,
    strat: StrategySpec,
    tiers: list[PrizeTier],
    n_paths: int = 200_000,
    seed: int = 7,
) -> SimResult:
    """Simula n_paths recorridos del concurso bajo una politica de riesgo."""
    rng = np.random.default_rng(seed)
    shocks = _daily_shocks(rng, strat, n_paths, contest.days)
    empirical = strat.empirical_daily is not None and len(strat.empirical_daily) > 0
    cap = contest.cap_for(empirical)

    multiple = np.ones(n_paths)
    alive = np.ones(n_paths, dtype=bool)
    lev_sum = 0.0
    lev_count = 0

    for day in range(contest.days):
        days_left = contest.days - day
        if policy.kind == "adaptive":
            # Vectorizado a mano: L depende de la equity de cada recorrido.
            gap = policy.target_multiple / np.maximum(multiple, 1e-9)
            horizon = max(days_left, 1) / TRADING_DAYS_YEAR
            with np.errstate(invalid="ignore"):
                lev = np.sqrt(2.0 * np.log(np.maximum(gap, 1.0 + 1e-12))) / (
                    strat.sigma_annual * math.sqrt(horizon)
                )
            lev = np.where(multiple >= policy.target_multiple, policy.protect_leverage, lev)
        else:
            lev = np.full(
                n_paths,
                policy.leverage_for(1.0, days_left, strat, contest, empirical),
                dtype=float,
            )

        # El margen y el tope propio acotan el apalancamiento efectivo.
        lev = np.clip(lev, 0.0, cap)
        lev = np.where(alive, lev, 0.0)
        lev_sum += float(lev[alive].sum()) if alive.any() else 0.0
        lev_count += int(alive.sum())

        multiple = multiple * (1.0 + lev * shocks[:, day])
        multiple = np.maximum(multiple, 0.0)
        alive &= multiple > contest.ruin_fraction

    return SimResult(
        policy=policy.name,
        final_multiple=multiple,
        ruined=~alive,
        mean_leverage=(lev_sum / lev_count) if lev_count else 0.0,
        tiers=tiers,
    )


# --------------------------------------------------------------------------- #
# Carga de operaciones de un backtest
# --------------------------------------------------------------------------- #

def load_daily_returns(path: str) -> np.ndarray:
    """Lee trades de orb_backtest.py y agrega a retornos diarios sin apalancar.

    Espera columnas `date` y `r_multiple` (resultado en multiplos de riesgo).
    El retorno diario a 1x se define como r_multiple * risk_unit, con
    risk_unit = 1% de la equity, que es la escala de referencia de "1x".
    """
    risk_unit = 0.01
    by_day: dict[str, float] = {}
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            day = row["date"]
            by_day[day] = by_day.get(day, 0.0) + float(row["r_multiple"]) * risk_unit
    if not by_day:
        raise ValueError(f"{path} no contiene operaciones")
    return np.array(list(by_day.values()), dtype=float)


# --------------------------------------------------------------------------- #
# Informes
# --------------------------------------------------------------------------- #

def report_analytic(contest: ContestSpec, strat: StrategySpec, targets: list[float]) -> None:
    print("\n=== APALANCAMIENTO OPTIMO POR OBJETIVO (formula cerrada) ===")
    print(
        f"Horizonte: {contest.days} sesiones | Sharpe anual sin apalancar: "
        f"{strat.sharpe_annual:.2f} | Vol anual: {strat.sigma_annual:.0%}"
    )
    print(f"{'objetivo':>10} {'L* optimo':>11} {'P* maxima':>11} {'P a 1x':>9} {'P a Kelly':>10}")
    kelly = kelly_leverage(strat.sharpe_annual, strat.sigma_annual)
    for m in targets:
        lstar = optimal_leverage(m, strat.sigma_annual, contest.days)
        pstar = prob_target_at_optimum(m, strat.sharpe_annual, contest.days)
        p1 = prob_target_analytic(m, strat.sharpe_annual, strat.sigma_annual, contest.days, 1.0)
        pk = prob_target_analytic(m, strat.sharpe_annual, strat.sigma_annual, contest.days, kelly)
        print(f"{m:>9.2f}x {lstar:>10.1f}x {pstar:>10.2%} {p1:>8.2%} {pk:>9.2%}")
    print(f"Kelly (maximiza crecimiento, no ranking): {kelly:.1f}x")


def report_requirements(
    contest: ContestSpec, strat: StrategySpec, targets: list[float]
) -> None:
    """Traduce L* a lo que hay que teclear de verdad en la orden.

    Un L* de 28x no dice nada por si solo. Lo que importa es: cuantos contratos
    son, cuanto hay que arriesgar por operacion con el stop que usas, y cuanta
    oscilacion diaria de la cuenta implica.
    """
    print("\n=== QUE SIGNIFICA ESO EN LA PRACTICA ===")
    sigma_d = strat.sigma_annual / math.sqrt(TRADING_DAYS_YEAR)
    print(
        f"Stop medio: {contest.stop_pct:.2%} del precio | vol diaria del subyacente: "
        f"{sigma_d:.2%} | cuenta: {contest.equity0:,.0f}$"
    )
    print(
        f"{'objetivo':>9} {'%/dia':>8} {'L*':>7} {'contratos':>10} "
        f"{'riesgo/trade':>13} {'vol diaria cuenta':>18} {'viable?':>9}"
    )
    for m in targets:
        lstar = optimal_leverage(m, strat.sigma_annual, contest.days)
        daily_needed = math.exp(math.log(m) / contest.days) - 1.0
        contracts = lstar * contest.equity0 / contest.notional_per_contract
        risk_per_trade = lstar * contest.stop_pct
        equity_vol = lstar * sigma_d
        viable = "si" if lstar <= contest.margin_leverage_cap else "NO (margen)"
        print(
            f"{m:>8.2f}x {daily_needed:>7.2%} {lstar:>6.1f}x {contracts:>9.0f} "
            f"{risk_per_trade:>12.1%} {equity_vol:>17.1%} {viable:>9}"
        )
    print(
        f"Tope por margen: {contest.margin_leverage_cap:.1f}x nocional "
        f"= {contest.risk_leverage_cap * contest.risk_unit:.1%} de riesgo por "
        f"operacion con ese stop."
    )


def report_sim(results: list[SimResult], contest: ContestSpec) -> None:
    print("\n=== MONTE CARLO (colas gruesas, ruina discreta, tope de margen) ===")
    tiers = results[0].tiers
    header = f"{'politica':<26} {'L medio':>8} {'mediana':>9} {'ruina':>7}"
    for tier in tiers:
        header += f" {tier.name.split(' ')[0]:>9}"
    header += f" {'E[premio]':>11}"
    print(header)
    for res in results:
        line = (
            f"{res.policy:<26} {res.mean_leverage:>7.1f}x {res.median_multiple:>8.2f}x "
            f"{res.prob_ruin:>6.1%}"
        )
        for tier in tiers:
            line += f" {res.prob_reach(tier.target_multiple):>8.2%}"
        line += f" {res.expected_prize():>10.0f}$"
        print(line)
    print(
        f"\nRuina = equity por debajo del {contest.ruin_fraction:.0%} inicial. "
        "Los cortes de premio son suposiciones (--cut/--prize)."
    )


def build_tiers(cuts: list[float] | None, prizes: list[float] | None) -> list[PrizeTier]:
    if not cuts:
        return list(DEFAULT_TIERS)
    if not prizes or len(prizes) != len(cuts):
        raise SystemExit("--prize debe tener el mismo numero de valores que --cut")
    return [
        PrizeTier(f"corte-{i + 1}", cut, prize)
        for i, (cut, prize) in enumerate(zip(cuts, prizes))
    ]


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Simulador de The Leap: cuanto riesgo maximiza la probabilidad de premio.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    ap.add_argument("--equity", type=float, default=100_000.0, help="Saldo inicial de papel")
    ap.add_argument("--days", type=int, default=12, help="Sesiones habiles restantes")
    ap.add_argument("--sharpe", type=float, default=1.0, help="Sharpe anual sin apalancar")
    ap.add_argument("--sigma", type=float, default=0.20, help="Vol anual sin apalancar")
    ap.add_argument("--tail-df", type=float, default=4.0, help="Grados de libertad de la t")
    ap.add_argument("--margin", type=float, default=2_500.0, help="Margen por contrato (MNQ)")
    ap.add_argument("--price", type=float, default=25_000.0, help="Nivel del indice (NQ)")
    ap.add_argument("--point-value", type=float, default=2.0, help="$ por punto (MNQ=2, MES=5)")
    ap.add_argument("--max-leverage", type=float, default=40.0, help="Tope de apalancamiento propio")
    ap.add_argument("--stop-pct", type=float, default=0.003, help="Stop medio como % del precio")
    ap.add_argument("--ruin-fraction", type=float, default=0.10, help="Nivel de cuenta muerta")
    ap.add_argument(
        "--targets",
        type=float,
        nargs="+",
        default=[1.5, 2.0, 3.0, 6.0, 11.0],
        help="Multiplos objetivo para la tabla analitica",
    )
    ap.add_argument(
        "--leverages",
        type=float,
        nargs="+",
        default=[1.0, 5.0, 10.0, 20.0, 30.0],
        help="Apalancamientos estaticos a simular",
    )
    ap.add_argument("--cut", type=float, nargs="+", help="Rentabilidad necesaria por escalon")
    ap.add_argument("--prize", type=float, nargs="+", help="Premio en $ por escalon")
    ap.add_argument("--paths", type=int, default=200_000, help="Recorridos Monte Carlo")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument(
        "--compare-policies",
        action="store_true",
        help="Anade la politica adaptativa (bold cuando vas por detras)",
    )
    ap.add_argument("--from-trades", help="CSV de trades de orb_backtest.py para bootstrap")
    args = ap.parse_args()

    contest = ContestSpec(
        equity0=args.equity,
        days=args.days,
        point_value=args.point_value,
        margin_per_contract=args.margin,
        price=args.price,
        ruin_fraction=args.ruin_fraction,
        max_leverage_cap=args.max_leverage,
        stop_pct=args.stop_pct,
    )
    print(
        f"Nocional por contrato: {contest.notional_per_contract:,.0f}$ | "
        f"tope por margen: {contest.margin_leverage_cap:.1f}x | "
        f"tope efectivo: {contest.effective_leverage_cap:.1f}x "
        f"({contest.equity0 / contest.margin_per_contract:.0f} contratos con la cuenta entera)"
    )
    empirical = load_daily_returns(args.from_trades) if args.from_trades else None
    if empirical is not None:
        # Reajusta Sharpe/vol a lo que dice el backtest, para que la parte
        # analitica y la simulada hablen del mismo sistema.
        mu_d, sd_d = float(np.mean(empirical)), float(np.std(empirical, ddof=1))
        args.sharpe = (mu_d / sd_d) * math.sqrt(TRADING_DAYS_YEAR) if sd_d > 0 else 0.0
        args.sigma = sd_d * math.sqrt(TRADING_DAYS_YEAR)
        print(
            f"Bootstrap desde {args.from_trades}: {len(empirical)} sesiones, "
            f"Sharpe anual {args.sharpe:.2f}, vol anual {args.sigma:.0%}"
        )

    strat = StrategySpec(
        sharpe_annual=args.sharpe,
        sigma_annual=args.sigma,
        tail_df=args.tail_df,
        empirical_daily=empirical,
    )
    tiers = build_tiers(args.cut, args.prize)

    report_analytic(contest, strat, args.targets)
    report_requirements(contest, strat, args.targets)

    policies = [Policy(f"estatico {lev:g}x", "static", leverage=lev) for lev in args.leverages]
    policies.insert(0, Policy("Kelly (crecimiento)", "kelly"))
    if args.compare_policies:
        for target in (2.0, 6.0, 11.0):
            policies.append(
                Policy(
                    f"adaptativo objetivo {target:g}x",
                    "adaptive",
                    target_multiple=target,
                    protect_leverage=0.5,
                )
            )

    results = [simulate(p, contest, strat, tiers, args.paths, args.seed) for p in policies]
    report_sim(results, contest)

    best = max(results, key=lambda r: r.expected_prize())
    print(f"\nMayor E[premio] con esta parametrizacion: {best.policy}")


if __name__ == "__main__":
    main()
