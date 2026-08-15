/*
 * estadisticas.js — de la lista de entradas a las clasificaciones.
 *
 * Todo lo que se ve en la pestaña "Clasificacion" y en "Campeones" sale de
 * aqui. Funciones puras: entra el estado, sale un objeto. Sin tocar el DOM.
 */
(function (global) {
  'use strict';

  var R = global.Reglas || (typeof require !== 'undefined' ? require('./reglas.js') : null);

  var DIA_MS = 24 * 60 * 60 * 1000;

  // --- Fechas ---------------------------------------------------------------

  function aFecha(valor) {
    return valor instanceof Date ? valor : new Date(valor);
  }

  /** Clave de dia local: "2026-08-11". */
  function claveDia(valor) {
    var d = aFecha(valor);
    var m = String(d.getMonth() + 1).padStart(2, '0');
    var dd = String(d.getDate()).padStart(2, '0');
    return d.getFullYear() + '-' + m + '-' + dd;
  }

  /** Lunes de la semana de esa fecha, a las 00:00. */
  function inicioSemana(valor) {
    var d = aFecha(valor);
    d = new Date(d.getFullYear(), d.getMonth(), d.getDate());
    var dow = (d.getDay() + 6) % 7; // 0 = lunes
    d.setDate(d.getDate() - dow);
    return d;
  }

  function claveSemana(valor) {
    return 'S' + claveDia(inicioSemana(valor));
  }

  function claveMes(valor) {
    var d = aFecha(valor);
    return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0');
  }

  function clavePeriodo(periodo, valor) {
    if (periodo === 'dia') return claveDia(valor);
    if (periodo === 'semana') return claveSemana(valor);
    if (periodo === 'mes') return claveMes(valor);
    return 'total';
  }

  /** Cuando deja de contar un periodo: el instante en que empieza el siguiente. */
  function finDePeriodo(periodo, valor) {
    var d = aFecha(valor);
    if (periodo === 'dia') {
      return new Date(d.getFullYear(), d.getMonth(), d.getDate() + 1);
    }
    if (periodo === 'semana') {
      var lunes = inicioSemana(d);
      return new Date(lunes.getFullYear(), lunes.getMonth(), lunes.getDate() + 7);
    }
    return new Date(d.getFullYear(), d.getMonth() + 1, 1);
  }

  /** ¿Ya ha terminado ese periodo? Solo entonces se cobra el bonus. */
  function periodoCerrado(periodo, valor, ahora) {
    return finDePeriodo(periodo, valor) <= (ahora || new Date());
  }

  /** Dias enteros entre dos fechas (minimo 1, para no dividir por cero). */
  function diasEntre(desde, hasta) {
    var a = new Date(aFecha(desde).getFullYear(), aFecha(desde).getMonth(), aFecha(desde).getDate());
    var b = new Date(aFecha(hasta).getFullYear(), aFecha(hasta).getMonth(), aFecha(hasta).getDate());
    return Math.max(1, Math.round((b - a) / DIA_MS) + 1);
  }

  // --- Entradas -------------------------------------------------------------

  function porFecha(a, b) {
    return new Date(a.fecha) - new Date(b.fecha);
  }

  function entradasDe(estado, jugadorId) {
    return estado.entradas
      .filter(function (e) { return e.jugadorId === jugadorId; })
      .sort(porFecha);
  }

  /**
   * Las que cuentan para ESTA liga: las `limiteLiga` primeras de cada jugador.
   * El resto se siguen guardando (y se ven en el historial) pero no puntuan,
   * que es justo lo que pidio la regla: si llegas a 100 antes que los demas
   * puedes seguir metiendo, pero ya no suma.
   */
  function entradasEnLiga(estado, jugadorId) {
    return entradasDe(estado, jugadorId).slice(0, estado.reglas.limiteLiga);
  }

  function notaEntrada(estado, entrada) {
    var votos = estado.votos[entrada.id] || {};
    return R.notaDeEntrada(votos, entrada.jugadorId, estado.reglas);
  }

  // --- Bonus por ganar dias, semanas y meses --------------------------------

  /**
   * Puntos extra de cada jugador por los periodos que ha ganado.
   *
   * Solo cuentan los periodos ya cerrados. Mientras la semana esta en marcha
   * el titulo cambia de manos cada noche, y sumar el bonus sobre la marcha
   * haria que la clasificacion general bailase sin que nadie entienda por que.
   * En la pestana de Campeones se ve quien lo lleva de momento.
   *
   * El campeon se decide solo con los puntos de las entradas: si el bonus
   * contase para elegir campeon, se estaria premiando a si mismo.
   */
  function tablaDeBonus(estado, ahora) {
    var premios = estado.reglas.bonus || {};
    var total = {};
    estado.jugadores.forEach(function (j) { total[j.id] = 0; });

    ['dia', 'semana', 'mes'].forEach(function (periodo) {
      var premio = Number(premios[periodo]) || 0;
      if (!premio) return;

      var fechasPorClave = {};
      estado.entradas.forEach(function (e) {
        fechasPorClave[clavePeriodo(periodo, e.fecha)] = e.fecha;
      });

      Object.keys(fechasPorClave).forEach(function (clave) {
        var fecha = fechasPorClave[clave];
        if (!periodoCerrado(periodo, fecha, ahora)) return;
        var campeon = campeonDe(estado, periodo, fecha).campeon;
        // Sin puntos no hay titulo: una noche de solo rechazos no la gana nadie.
        if (!campeon || campeon.puntos <= 0) return;
        total[campeon.jugador.id] = (total[campeon.jugador.id] || 0) + premio;
      });
    });

    return total;
  }

  // --- Resumen por jugador --------------------------------------------------

  function resumenJugador(estado, jugador, bonusPrecalculado) {
    var todas = entradasDe(estado, jugador.id);
    var enLiga = todas.slice(0, estado.reglas.limiteLiga);
    var reglas = estado.reglas;

    var puntos = 0;
    var rechazos = 0;
    var porResultado = { mas_lio: 0, lio: 0, pico: 0, amigos: 0, nada: 0 };
    var dentro = 0;
    var notas = [];

    enLiga.forEach(function (e) {
      puntos += R.puntosDeEntrada(e, reglas);
      if (e.rechazo) rechazos++;
      else if (porResultado[e.resultado] !== undefined) porResultado[e.resultado]++;
      if (R.esDentro(e, reglas)) dentro++;
      var n = notaEntrada(estado, e);
      if (n) notas.push(n.nota);
    });

    var primera = enLiga.length ? enLiga[0].fecha : null;
    var ultima = enLiga.length ? enLiga[enLiga.length - 1].fecha : null;
    var completada = enLiga.length >= reglas.limiteLiga;
    // Para el ritmo, un jugador que ya termino se congela el dia que llego a
    // la cifra: si no, bajaria de ritmo por estar quieto y eso no tendria sentido.
    var hasta = completada ? ultima : new Date();
    var dias = primera ? diasEntre(primera, hasta) : 0;

    var media = notas.length
      ? notas.reduce(function (a, b) { return a + b; }, 0) / notas.length
      : null;

    var ligadas = porResultado.lio + porResultado.mas_lio;

    var bonus = bonusPrecalculado
      ? (bonusPrecalculado[jugador.id] || 0)
      : (tablaDeBonus(estado)[jugador.id] || 0);

    return {
      jugador: jugador,
      entradasTotales: todas.length,
      entradas: enLiga.length,
      extras: Math.max(0, todas.length - enLiga.length),
      rechazos: rechazos,
      porResultado: porResultado,
      dentro: dentro,
      fuera: enLiga.length - dentro,
      puntosDeEntradas: R.redondea(puntos),
      bonus: R.redondea(bonus),
      puntos: R.redondea(puntos + bonus),
      nota: media === null ? null : R.redondea(media),
      notasContadas: notas.length,
      ritmo: dias ? R.redondea(enLiga.length / dias) : 0,
      dias: dias,
      primera: primera,
      ultima: ultima,
      completada: completada,
      fechaFinal: completada ? ultima : null,
      progreso: reglas.limiteLiga ? enLiga.length / reglas.limiteLiga : 0,
      // % de entradas que acaban en lio o mas lio
      efectividad: enLiga.length ? R.redondea((ligadas / enLiga.length) * 100) : 0,
      // Dias que le quedarian para llegar a la cifra al ritmo actual
      diasRestantes: (function () {
        if (completada) return 0;
        var faltan = reglas.limiteLiga - enLiga.length;
        var ritmo = dias ? enLiga.length / dias : 0;
        return ritmo > 0 ? Math.ceil(faltan / ritmo) : null;
      })()
    };
  }

  function resumenes(estado) {
    // Una sola pasada de bonus para todos: recorrer semanas y meses por cada
    // jugador seria hacer el mismo trabajo tantas veces como jugadores haya.
    var bonus = tablaDeBonus(estado);
    return estado.jugadores.map(function (j) { return resumenJugador(estado, j, bonus); });
  }

  // --- Clasificaciones ------------------------------------------------------

  /** Ordena de mayor a menor por un campo, dejando los null al final. */
  function ordenaPor(lista, campo) {
    return lista.slice().sort(function (a, b) {
      var va = a[campo], vb = b[campo];
      if (va === null && vb === null) return 0;
      if (va === null) return 1;
      if (vb === null) return -1;
      if (vb !== va) return vb - va;
      return b.puntos - a.puntos;
    });
  }

  /**
   * Ranking de ritmo: gana quien llega antes a la cifra. Los que ya han
   * terminado van siempre por delante, ordenados por fecha de llegada; los
   * demas, por entradas al dia.
   */
  function rankingRitmo(lista) {
    return lista.slice().sort(function (a, b) {
      if (a.completada !== b.completada) return a.completada ? -1 : 1;
      if (a.completada && b.completada) return new Date(a.fechaFinal) - new Date(b.fechaFinal);
      if (b.ritmo !== a.ritmo) return b.ritmo - a.ritmo;
      return b.entradas - a.entradas;
    });
  }

  /** Convierte un valor a 0-100 respecto al mejor de la liga. */
  function normaliza(valor, maximo) {
    if (valor === null || !maximo || maximo <= 0) return 0;
    return Math.max(0, Math.min(100, (valor / maximo) * 100));
  }

  /**
   * Clasificacion general: mezcla los tres ejes (puntos, ritmo y nota) con los
   * pesos configurados. Se devuelve el desglose para que se pueda ver por que
   * cada uno esta donde esta — si no, nadie se cree la tabla.
   */
  function clasificacionGeneral(estado) {
    var lista = resumenes(estado);
    if (!lista.length) return [];

    var pesos = estado.reglas.pesos || R.REGLAS_DEFECTO.pesos;
    var sumaPesos = (pesos.puntos || 0) + (pesos.ritmo || 0) + (pesos.nota || 0);
    if (sumaPesos <= 0) sumaPesos = 1;

    var maxPuntos = Math.max.apply(null, lista.map(function (r) { return r.puntos; }).concat([0]));
    var maxRitmo = Math.max.apply(null, lista.map(function (r) { return r.ritmo; }).concat([0]));
    var maxNota = Math.max.apply(null, lista.map(function (r) { return r.nota || 0; }).concat([0]));

    var conIndice = lista.map(function (r) {
      var ejes = {
        puntos: normaliza(r.puntos, maxPuntos),
        ritmo: normaliza(r.ritmo, maxRitmo),
        nota: normaliza(r.nota, maxNota)
      };
      var indice =
        (ejes.puntos * (pesos.puntos || 0) +
          ejes.ritmo * (pesos.ritmo || 0) +
          ejes.nota * (pesos.nota || 0)) / sumaPesos;
      r.ejes = {
        puntos: R.redondea(ejes.puntos),
        ritmo: R.redondea(ejes.ritmo),
        nota: R.redondea(ejes.nota)
      };
      r.indice = R.redondea(indice);
      return r;
    });

    return conIndice.sort(function (a, b) {
      if (b.indice !== a.indice) return b.indice - a.indice;
      return b.puntos - a.puntos;
    });
  }

  function clasificaciones(estado) {
    var general = clasificacionGeneral(estado);
    return {
      general: general,
      puntos: ordenaPor(general, 'puntos'),
      ritmo: rankingRitmo(general),
      nota: ordenaPor(general, 'nota')
    };
  }

  // --- Campeones ------------------------------------------------------------

  /**
   * Campeon de un periodo (dia / semana / mes): quien mas puntos ha hecho con
   * las entradas de ese periodo. Desempate: mas entradas, y luego mejor nota.
   */
  function campeonDe(estado, periodo, referencia) {
    var clave = clavePeriodo(periodo, referencia || new Date());
    var porJugador = {};

    estado.jugadores.forEach(function (j) {
      porJugador[j.id] = { jugador: j, puntos: 0, entradas: 0, notas: [] };
    });

    estado.jugadores.forEach(function (j) {
      entradasEnLiga(estado, j.id).forEach(function (e) {
        if (clavePeriodo(periodo, e.fecha) !== clave) return;
        var acc = porJugador[j.id];
        acc.puntos += R.puntosDeEntrada(e, estado.reglas);
        acc.entradas++;
        var n = notaEntrada(estado, e);
        if (n) acc.notas.push(n.nota);
      });
    });

    var lista = Object.keys(porJugador)
      .map(function (id) {
        var a = porJugador[id];
        a.puntos = R.redondea(a.puntos);
        a.nota = a.notas.length
          ? R.redondea(a.notas.reduce(function (x, y) { return x + y; }, 0) / a.notas.length)
          : null;
        return a;
      })
      .filter(function (a) { return a.entradas > 0; })
      .sort(function (a, b) {
        if (b.puntos !== a.puntos) return b.puntos - a.puntos;
        if (b.entradas !== a.entradas) return b.entradas - a.entradas;
        return (b.nota || 0) - (a.nota || 0);
      });

    return { periodo: periodo, clave: clave, tabla: lista, campeon: lista[0] || null };
  }

  /** Los ultimos N periodos con actividad, del mas reciente al mas antiguo. */
  function historialCampeones(estado, periodo, limite) {
    var claves = {};
    estado.entradas.forEach(function (e) {
      claves[clavePeriodo(periodo, e.fecha)] = e.fecha;
    });
    return Object.keys(claves)
      .sort()
      .reverse()
      .slice(0, limite || 12)
      .map(function (k) {
        var resultado = campeonDe(estado, periodo, claves[k]);
        resultado.fecha = claves[k];
        resultado.cerrado = periodoCerrado(periodo, claves[k]);
        return resultado;
      });
  }

  /**
   * Estado de la liga: si todos han llegado a la cifra, hay campeon.
   */
  function estadoLiga(estado) {
    var lista = clasificacionGeneral(estado);
    var conEntradas = lista.filter(function (r) { return r.entradasTotales > 0; });
    var terminada = conEntradas.length > 0 &&
      lista.length > 0 &&
      lista.every(function (r) { return r.completada; });
    return {
      terminada: terminada,
      campeon: terminada ? lista[0] : null,
      limite: estado.reglas.limiteLiga,
      lider: lista[0] || null
    };
  }

  // --- Entradas pendientes de votar ----------------------------------------

  /** Entradas de los demas (con foto o con enlace) que `jugadorId` no ha puntuado. */
  function pendientesDeVotar(estado, jugadorId) {
    return estado.entradas
      .filter(function (e) {
        if (e.jugadorId === jugadorId) return false;
        if (!R.tieneMaterial(e)) return false;
        var votos = estado.votos[e.id] || {};
        return votos[jugadorId] === undefined;
      })
      .sort(porFecha)
      .reverse();
  }

  var api = {
    claveDia: claveDia,
    claveSemana: claveSemana,
    claveMes: claveMes,
    clavePeriodo: clavePeriodo,
    inicioSemana: inicioSemana,
    finDePeriodo: finDePeriodo,
    periodoCerrado: periodoCerrado,
    tablaDeBonus: tablaDeBonus,
    diasEntre: diasEntre,
    entradasDe: entradasDe,
    entradasEnLiga: entradasEnLiga,
    notaEntrada: notaEntrada,
    resumenJugador: resumenJugador,
    resumenes: resumenes,
    clasificaciones: clasificaciones,
    clasificacionGeneral: clasificacionGeneral,
    campeonDe: campeonDe,
    historialCampeones: historialCampeones,
    estadoLiga: estadoLiga,
    pendientesDeVotar: pendientesDeVotar
  };

  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  global.Estadisticas = api;
})(typeof window !== 'undefined' ? window : globalThis);
