/*
 * pruebas.js — comprobaciones de las reglas y las clasificaciones.
 *
 *   node liga/pruebas.js
 *
 * Sin dependencias: si la salida acaba en "TODO OK", las cuentas cuadran.
 */
'use strict';

var R = require('./js/reglas.js');
var E = require('./js/estadisticas.js');

var fallos = 0;
var total = 0;

function comprueba(titulo, real, esperado) {
  total++;
  var a = JSON.stringify(real);
  var b = JSON.stringify(esperado);
  if (a === b) {
    console.log('  ok  ' + titulo);
  } else {
    fallos++;
    console.log('FALLO ' + titulo + '\n      esperado ' + b + '\n      obtenido ' + a);
  }
}

function reglas(extra) {
  return Object.assign(JSON.parse(JSON.stringify(R.REGLAS_DEFECTO)), extra || {});
}

function entrada(opciones) {
  return Object.assign({
    id: 'e' + Math.random().toString(36).slice(2),
    jugadorId: 'a',
    fecha: '2026-08-01T22:00:00.000Z',
    rechazo: false,
    fiesta: false,
    lugar: null,
    resultado: 'nada',
    tieneFoto: false
  }, opciones);
}

// --- Puntos ---------------------------------------------------------------

console.log('\nPuntos por entrada');

comprueba('mas lio fuera de discoteca = 10',
  R.puntosDeEntrada(entrada({ resultado: 'mas_lio' }), reglas()), 10);

comprueba('mas lio en discoteca = 5',
  R.puntosDeEntrada(entrada({ resultado: 'mas_lio', fiesta: true, lugar: 'discoteca' }), reglas()), 5);

comprueba('lio fuera = 3',
  R.puntosDeEntrada(entrada({ resultado: 'lio' }), reglas()), 3);

comprueba('lio en discoteca = 2',
  R.puntosDeEntrada(entrada({ resultado: 'lio', fiesta: true, lugar: 'discoteca' }), reglas()), 2);

comprueba('amigos fuera = 1',
  R.puntosDeEntrada(entrada({ resultado: 'amigos' }), reglas()), 1);

comprueba('amigos en discoteca = 0.5',
  R.puntosDeEntrada(entrada({ resultado: 'amigos', fiesta: true, lugar: 'discoteca' }), reglas()), 0.5);

comprueba('un rechazo nunca puntua',
  R.puntosDeEntrada(entrada({ resultado: 'mas_lio', rechazo: true }), reglas()), 0);

comprueba('de fiesta pero no en discoteca (DJ) con la regla desactivada puntua como fuera',
  R.puntosDeEntrada(entrada({ resultado: 'lio', fiesta: true, lugar: 'dj' }),
    reglas({ djCuentaComoDiscoteca: false })), 3);

comprueba('con la regla activada, el DJ cuenta como discoteca',
  R.puntosDeEntrada(entrada({ resultado: 'lio', fiesta: true, lugar: 'dj' }),
    reglas({ djCuentaComoDiscoteca: true })), 2);

comprueba('solo lio y mas lio admiten foto',
  [
    R.admiteFoto(entrada({ resultado: 'mas_lio' })),
    R.admiteFoto(entrada({ resultado: 'lio' })),
    R.admiteFoto(entrada({ resultado: 'pico' })),
    R.admiteFoto(entrada({ resultado: 'lio', rechazo: true }))
  ],
  [true, true, false, false]);

// --- Notas ----------------------------------------------------------------

console.log('\nNotas de consenso');

comprueba('la media excluye el voto del propio jugador',
  R.notaDeEntrada({ a: 10, b: 6, c: 8 }, 'a', reglas()), { nota: 7, votos: 2 });

comprueba('sin votos suficientes no hay nota',
  R.notaDeEntrada({ a: 10 }, 'a', reglas({ votosMinimos: 1 })), null);

comprueba('se ignoran votos fuera de 1-10',
  R.notaDeEntrada({ b: 11, c: 0, d: 7 }, 'a', reglas()), { nota: 7, votos: 1 });

// --- Estado de ejemplo ----------------------------------------------------

function estadoDemo() {
  return {
    version: 1,
    liga: { nombre: 'Test', creada: '2026-08-01T00:00:00.000Z' },
    reglas: reglas({ limiteLiga: 3 }),
    jugadores: [
      { id: 'a', nombre: 'Ana', color: '#f00' },
      { id: 'b', nombre: 'Bruno', color: '#00f' }
    ],
    entradas: [
      // Ana: 3 que cuentan + 1 pasada del limite
      entrada({ id: 'a1', jugadorId: 'a', fecha: '2026-08-01T22:00:00.000Z', resultado: 'mas_lio', tieneFoto: true }),
      entrada({ id: 'a2', jugadorId: 'a', fecha: '2026-08-02T22:00:00.000Z', rechazo: true }),
      entrada({ id: 'a3', jugadorId: 'a', fecha: '2026-08-03T22:00:00.000Z', resultado: 'lio', fiesta: true, lugar: 'discoteca' }),
      entrada({ id: 'a4', jugadorId: 'a', fecha: '2026-08-04T22:00:00.000Z', resultado: 'mas_lio' }),
      // Bruno: 2
      entrada({ id: 'b1', jugadorId: 'b', fecha: '2026-08-01T22:00:00.000Z', resultado: 'amigos' }),
      entrada({ id: 'b2', jugadorId: 'b', fecha: '2026-08-02T22:00:00.000Z', resultado: 'lio', tieneFoto: true })
    ],
    votos: {
      a1: { b: 9 },
      b2: { a: 6 }
    },
    yo: 'a'
  };
}

console.log('\nClasificaciones');

var demo = estadoDemo();

comprueba('solo cuentan las 3 primeras entradas de Ana (10 + 0 + 2)',
  E.resumenJugador(demo, demo.jugadores[0]).puntos, 12);

comprueba('la cuarta entrada de Ana queda fuera de la liga',
  E.resumenJugador(demo, demo.jugadores[0]).extras, 1);

comprueba('Ana ha completado la liga y Bruno no',
  [E.resumenJugador(demo, demo.jugadores[0]).completada,
   E.resumenJugador(demo, demo.jugadores[1]).completada],
  [true, false]);

comprueba('el ritmo de Ana se congela el dia que llego (3 entradas en 3 dias)',
  E.resumenJugador(demo, demo.jugadores[0]).ritmo, 1);

comprueba('la nota de Ana sale del voto de Bruno',
  E.resumenJugador(demo, demo.jugadores[0]).nota, 9);

comprueba('Ana lidera la tabla de puntos',
  E.clasificaciones(demo).puntos.map(function (r) { return r.jugador.id; }), ['a', 'b']);

comprueba('en ritmo va primero quien ya ha terminado',
  E.clasificaciones(demo).ritmo[0].jugador.id, 'a');

comprueba('la liga no ha terminado porque Bruno no ha llegado',
  E.estadoLiga(demo).terminada, false);

comprueba('campeon del dia 1 de agosto: Ana (10 pts frente a 1)',
  E.campeonDe(demo, 'dia', '2026-08-01T22:00:00.000Z').campeon.jugador.id, 'a');

comprueba('campeon del dia 2: Bruno (Ana solo tuvo un rechazo)',
  E.campeonDe(demo, 'dia', '2026-08-02T22:00:00.000Z').campeon.jugador.id, 'b');

comprueba('el mes de agosto lo lidera Ana',
  E.campeonDe(demo, 'mes', '2026-08-02T22:00:00.000Z').campeon.puntos, 12);

comprueba('a Bruno le queda por votar la foto de Ana ya votada: ninguna',
  E.pendientesDeVotar(demo, 'b').map(function (e) { return e.id; }), []);

comprueba('a Ana no le queda nada por votar (ya voto b2)',
  E.pendientesDeVotar(demo, 'a').map(function (e) { return e.id; }), []);

var sinVotar = estadoDemo();
sinVotar.votos = {};
comprueba('sin votos, cada uno tiene pendiente la foto del otro',
  [E.pendientesDeVotar(sinVotar, 'a').map(function (e) { return e.id; }),
   E.pendientesDeVotar(sinVotar, 'b').map(function (e) { return e.id; })],
  [['b2'], ['a1']]);

var terminada = estadoDemo();
terminada.reglas.limiteLiga = 2;
comprueba('con el limite en 2, la liga termina y gana el del mejor indice',
  [E.estadoLiga(terminada).terminada, E.estadoLiga(terminada).campeon.jugador.id],
  [true, 'a']);

console.log('\nSemanas y meses');

comprueba('la semana empieza en lunes',
  E.claveSemana('2026-08-06T12:00:00') === E.claveSemana('2026-08-03T12:00:00'), true);

comprueba('el domingo pertenece a la semana que empezo el lunes anterior',
  E.claveSemana('2026-08-09T12:00:00') === E.claveSemana('2026-08-03T12:00:00'), true);

comprueba('el lunes siguiente ya es otra semana',
  E.claveSemana('2026-08-10T12:00:00') === E.claveSemana('2026-08-03T12:00:00'), false);

// --- Resultado ------------------------------------------------------------

console.log('\n' + (fallos ? fallos + ' FALLOS de ' + total : 'TODO OK (' + total + ' comprobaciones)') + '\n');
process.exit(fallos ? 1 : 0);
