# The Leap — herramientas para el concurso de trading de TradingView

Paquete para la edición del 20 de julio al 14 de agosto de 2026 (futuros de CME,
100.000 $ de papel, premios para los 250 primeros por P/L realizado).

```
trading/
├── PLAN_TORNEO.md              El plan y las matemáticas. Empieza por aquí.
├── pine/
│   ├── leap_orb_mnq.pine       Estrategia ORB con dimensionamiento de torneo
│   └── leap_risk_panel.pine    Panel: cuánto arriesgar hoy según tu posición
└── sim/
    ├── contest_sim.py          Monte Carlo: probabilidad de acabar en premio
    ├── instrument_selector.py  Qué contrato de tu lista sirve, y cuál no
    ├── order_ticket.py         La orden exacta a partir del rango de apertura
    ├── orb_backtest.py         Backtest ORB sobre CSV de TradingView
    └── tests/                  22 comprobaciones, incluidas las anti-sesgo
```

## Instalación

```bash
pip install numpy pandas
```

## Uso

**1. ¿Cuánto riesgo maximiza mi probabilidad de premio?**

```bash
python3 sim/contest_sim.py --days 11 --margin 1200 --compare-policies
```

Ajusta `--margin` al margen intradía real de tu cuenta: es el parámetro que
decide si el apalancamiento óptimo está a tu alcance. Los cortes de premio son
suposiciones; corrígelos con `--cut` y `--prize` mirando la clasificación en vivo.

**2. ¿Qué contrato debo operar?**

```bash
python3 sim/instrument_selector.py --equity 100000 --days 11 --target 2
```

Cruza volatilidad (baja el `L*` necesario), tope por margen (techo duro) y
granularidad (con 4 contratos no puedes afinar el tamaño). Descarta lo que no
puede llevarte al objetivo por mucho que acierte la dirección.

**3. ¿Cuál es mi orden de hoy?** (a las 10:00 ET, con el rango ya formado)

```bash
python3 sim/order_ticket.py --or-high 27450 --or-low 27290 --atr 550
```

Devuelve entrada, stop, objetivo, contratos y riesgo en dólares para las dos
direcciones. El stop y el objetivo no se eligen: salen del rango de apertura.

**4. ¿Funciona la estrategia sobre datos reales?**

Exporta el histórico desde TradingView (gráfico de MNQ1! en 5 min → exportar
datos) y pásalo al backtest:

```bash
python3 sim/orb_backtest.py --csv MNQ_5m.csv --or-minutes 15 --target-r 2
python3 sim/orb_backtest.py --csv MNQ_5m.csv --grid     # barrido de parámetros
```

No se descarga nada de internet (Yahoo Finance está bloqueado en muchos entornos,
y el dato de TradingView del contrato real es mejor de todas formas).

**5. Encadenar las dos cosas** — el backtest estima tu Sharpe y tu volatilidad
reales, y el Monte Carlo los usa en vez de los supuestos:

```bash
python3 sim/orb_backtest.py --csv MNQ_5m.csv --out trades.csv
python3 sim/contest_sim.py --from-trades trades.csv --days 11
```

**6. Validar sin datos** (comprueba que la maquinaria no hace trampas):

```bash
python3 sim/orb_backtest.py --synthetic 300
python3 -m unittest discover -s sim/tests
```

## Sobre los tests

Dos de ellos son el guardarraíl importante:

- `test_no_edge_on_random_data`: un sistema de rupturas sobre un paseo aleatorio
  no puede ganar dinero. Si ese test se pone en verde con esperanza claramente
  positiva, hay un sesgo nuevo en el backtest. Ya cazó dos durante el desarrollo:
  un ATR sin desplazar (filtraba sesiones sabiendo cómo acababan) y un muestreo
  intrabarra demasiado grueso (perdía toques del stop, que está más cerca que el
  objetivo, e inventaba +0,18R de ventaja inexistente).
- `test_gap_through_stop_pays_the_open`: si una barra abre pasado el stop, la
  pérdida tiene que ser mayor que 1R. Un backtest que rellena siempre al precio
  del stop borra toda la cola izquierda.

## Advertencia

El dimensionamiento de este paquete asume varianza alta **a propósito**, porque
en un concurso de papel perder la cuenta no cuesta nada y los premios van por
ranking. Las políticas de la tabla implican entre un 5% y un 40% de probabilidad
de destruir la cuenta. No trasladar a dinero real. El razonamiento completo, con
la derivación, está en `PLAN_TORNEO.md`.
