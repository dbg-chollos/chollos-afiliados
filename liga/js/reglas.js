/*
 * reglas.js — motor de puntuacion de la liga.
 *
 * Aqui vive TODO lo que decide cuantos puntos vale cada entrada. Esta separado
 * a proposito del resto de la app: si algun dia cambiais las reglas entre
 * vosotros, se toca solo este archivo (o los ajustes de la app, que escriben
 * encima de estos valores por defecto).
 *
 * No usa nada del navegador, asi que se puede probar con node:
 *   node liga/js/reglas.test.js
 */
(function (global) {
  'use strict';

  // --- Vocabulario de una entrada -------------------------------------------

  // Resultado de la interaccion, de mas a menos.
  var RESULTADOS = [
    { id: 'mas_lio', etiqueta: 'Mas lio', emoji: '🔥' },
    { id: 'lio', etiqueta: 'Lio', emoji: '💋' },
    { id: 'pico', etiqueta: 'Pico', emoji: '😙' },
    { id: 'amigos', etiqueta: 'Amigos', emoji: '🤝' },
    { id: 'nada', etiqueta: 'Nada', emoji: '🚪' }
  ];

  // Donde ha pasado. Solo se pregunta si la entrada fue "de fiesta".
  var LUGARES = [
    { id: 'discoteca', etiqueta: 'Discoteca', emoji: '🪩' },
    { id: 'dj', etiqueta: 'DJ / sala', emoji: '🎧' }
  ];

  // Resultados que permiten adjuntar algo para que lo valoren los demas.
  var RESULTADOS_CON_FOTO = ['lio', 'mas_lio'];

  // Como se le ensena la pava al resto para que la puntue.
  var MODOS_FOTO = [
    {
      id: 'enlace',
      etiqueta: 'Solo el enlace de Instagram',
      detalle: 'No se guarda ninguna imagen: se guarda el @usuario y al votar se abre su perfil.'
    },
    {
      id: 'local',
      etiqueta: 'Guardar la foto en el movil',
      detalle: 'Se guarda una copia reducida en este dispositivo. Mas comodo, pero es una copia que puede acabar donde no debe.'
    },
    {
      id: 'ninguna',
      etiqueta: 'Sin fotos ni enlaces',
      detalle: 'Solo puntos. Nadie valora a nadie y la tabla de notas se queda vacia.'
    }
  ];

  // --- Reglas por defecto ---------------------------------------------------

  var REGLAS_DEFECTO = {
    // La liga termina cuando todos llegan a esta cifra de entradas.
    limiteLiga: 100,

    // Por defecto, enlace: es lo que menos rastro deja.
    modoFoto: 'enlace',

    // "Fuera de discoteca" puntua mas que "en discoteca" porque tiene mas merito.
    // Una sala con DJ cuenta como discoteca salvo que lo cambieis aqui.
    djCuentaComoDiscoteca: true,

    // Puntos por resultado, segun el ambiente.
    puntos: {
      mas_lio: { dentro: 5, fuera: 10 },
      lio: { dentro: 2, fuera: 3 },
      pico: { dentro: 1, fuera: 2 },
      amigos: { dentro: 0.5, fuera: 1 },
      nada: { dentro: 0, fuera: 0 }
    },

    // Votos minimos (de los demas) para que la nota de una entrada cuente
    // en la media del jugador.
    votosMinimos: 1,

    // Peso de cada eje en la clasificacion general. No hace falta que sumen 100,
    // se normalizan solos.
    pesos: { puntos: 50, ritmo: 25, nota: 25 }
  };

  // --- Calculo --------------------------------------------------------------

  /**
   * ¿Esta entrada cuenta como "en discoteca"?
   * Fuera de fiesta (calle, dia, gimnasio, curro...) siempre es "fuera".
   */
  function esDentro(entrada, reglas) {
    if (!entrada.fiesta) return false;
    if (entrada.lugar === 'discoteca') return true;
    if (entrada.lugar === 'dj') return !!reglas.djCuentaComoDiscoteca;
    return false;
  }

  /** Puntos que vale una entrada suelta. */
  function puntosDeEntrada(entrada, reglas) {
    if (entrada.rechazo) return 0;
    var tabla = reglas.puntos[entrada.resultado];
    if (!tabla) return 0;
    return esDentro(entrada, reglas) ? tabla.dentro : tabla.fuera;
  }

  /** ¿Se puede adjuntar algo a esta entrada para que la voten? */
  function admiteFoto(entrada) {
    return !entrada.rechazo && RESULTADOS_CON_FOTO.indexOf(entrada.resultado) !== -1;
  }

  /** ¿Hay algo que ensenar al resto — foto guardada o enlace a su perfil? */
  function tieneMaterial(entrada) {
    return !!(entrada.tieneFoto || entrada.perfil);
  }

  /**
   * Normaliza lo que se escriba en el campo de Instagram: "@pepita",
   * "pepita", "instagram.com/pepita" o la URL entera acaban igual.
   * Devuelve null si no se parece a un usuario de Instagram.
   */
  function perfilInstagram(texto) {
    if (!texto) return null;
    var limpio = String(texto).trim();
    if (!limpio) return null;
    limpio = limpio.replace(/^https?:\/\//i, '')
      .replace(/^(www\.)?instagram\.com\//i, '')
      .replace(/^@/, '')
      .split(/[/?#]/)[0]
      .trim();
    if (!/^[A-Za-z0-9._]{1,30}$/.test(limpio)) return null;
    return { usuario: limpio, url: 'https://www.instagram.com/' + limpio + '/' };
  }

  /**
   * Nota de consenso de una entrada: media de los votos de los DEMAS.
   * Devuelve null si todavia no hay votos suficientes.
   */
  function notaDeEntrada(votosDeEntrada, jugadorDuenyo, reglas) {
    var valores = [];
    for (var votante in votosDeEntrada) {
      if (!Object.prototype.hasOwnProperty.call(votosDeEntrada, votante)) continue;
      if (votante === jugadorDuenyo) continue; // uno no se vota a si mismo
      var v = Number(votosDeEntrada[votante]);
      if (v >= 1 && v <= 10) valores.push(v);
    }
    if (valores.length < (reglas.votosMinimos || 1)) return null;
    var suma = valores.reduce(function (a, b) { return a + b; }, 0);
    return { nota: suma / valores.length, votos: valores.length };
  }

  /** Redondeo a 2 decimales, para que 0.1+0.2 no salga feo por pantalla. */
  function redondea(n) {
    return Math.round(n * 100) / 100;
  }

  var api = {
    RESULTADOS: RESULTADOS,
    LUGARES: LUGARES,
    RESULTADOS_CON_FOTO: RESULTADOS_CON_FOTO,
    MODOS_FOTO: MODOS_FOTO,
    REGLAS_DEFECTO: REGLAS_DEFECTO,
    esDentro: esDentro,
    puntosDeEntrada: puntosDeEntrada,
    admiteFoto: admiteFoto,
    tieneMaterial: tieneMaterial,
    perfilInstagram: perfilInstagram,
    notaDeEntrada: notaDeEntrada,
    redondea: redondea
  };

  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  global.Reglas = api;
})(typeof window !== 'undefined' ? window : globalThis);
