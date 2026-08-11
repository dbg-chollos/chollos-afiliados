/*
 * datos.js — guardar y recuperar la liga.
 *
 * Todo se guarda en el navegador del movil/ordenador (localStorage). No hay
 * servidor, no hay cuenta, no se sube nada a internet. Las fotos van en claves
 * aparte para que el estado principal siga siendo pequeno y rapido de leer.
 */
(function (global) {
  'use strict';

  var CLAVE = 'liga.estado.v1';
  var CLAVE_FOTO = 'liga.foto.';
  var VERSION = 1;

  var COLORES = ['#e5484d', '#3e63dd', '#30a46c', '#f76b15', '#8e4ec6', '#0d9488', '#d6409f', '#a18072'];

  /**
   * Normalmente escribimos en localStorage. Pero hay sitios donde el navegador
   * no deja: navegacion privada, cookies bloqueadas, o la app abierta dentro de
   * otra pagina. Ahi tirar de memoria es feo (al cerrar se pierde) pero es
   * mucho mejor que reventar a la primera entrada.
   */
  var almacen = (function () {
    try {
      var prueba = '__liga_prueba__';
      localStorage.setItem(prueba, '1');
      localStorage.removeItem(prueba);
      return { permanente: true, api: localStorage };
    } catch (err) {
      var memoria = {};
      return {
        permanente: false,
        api: {
          getItem: function (k) {
            return Object.prototype.hasOwnProperty.call(memoria, k) ? memoria[k] : null;
          },
          setItem: function (k, v) { memoria[k] = String(v); },
          removeItem: function (k) { delete memoria[k]; },
          key: function (i) { return Object.keys(memoria)[i]; },
          get length() { return Object.keys(memoria).length; }
        }
      };
    }
  })();

  /** ¿Se esta guardando de verdad, o solo hasta que se cierre la pestana? */
  function guardadoPermanente() { return almacen.permanente; }

  function id() {
    return Date.now().toString(36) + Math.random().toString(36).slice(2, 8);
  }

  function estadoInicial() {
    return {
      version: VERSION,
      liga: { nombre: 'La Liga', creada: new Date().toISOString() },
      reglas: JSON.parse(JSON.stringify(global.Reglas.REGLAS_DEFECTO)),
      jugadores: [],
      entradas: [],
      votos: {},
      yo: null
    };
  }

  /**
   * Rellena lo que falte tras un cambio de version o un import a medias.
   * Mejor esto que reventar con "undefined is not an object" a mitad de fiesta.
   */
  function normaliza(estado) {
    var base = estadoInicial();
    if (!estado || typeof estado !== 'object') return base;

    estado.version = VERSION;
    estado.liga = estado.liga || base.liga;
    estado.jugadores = Array.isArray(estado.jugadores) ? estado.jugadores : [];
    estado.entradas = Array.isArray(estado.entradas) ? estado.entradas : [];
    estado.votos = estado.votos && typeof estado.votos === 'object' ? estado.votos : {};

    var reglas = estado.reglas || {};
    var defecto = base.reglas;
    estado.reglas = {
      limiteLiga: Number(reglas.limiteLiga) > 0 ? Number(reglas.limiteLiga) : defecto.limiteLiga,
      djCuentaComoDiscoteca: reglas.djCuentaComoDiscoteca !== undefined
        ? !!reglas.djCuentaComoDiscoteca
        : defecto.djCuentaComoDiscoteca,
      modoFoto: ['enlace', 'local', 'ninguna'].indexOf(reglas.modoFoto) !== -1
        ? reglas.modoFoto
        : defecto.modoFoto,
      puntos: Object.assign({}, defecto.puntos, reglas.puntos || {}),
      votosMinimos: Number(reglas.votosMinimos) > 0 ? Number(reglas.votosMinimos) : defecto.votosMinimos,
      pesos: Object.assign({}, defecto.pesos, reglas.pesos || {})
    };

    // Un "yo" que apunta a un jugador borrado deja la app en un limbo raro.
    var existe = estado.jugadores.some(function (j) { return j.id === estado.yo; });
    if (!existe) estado.yo = estado.jugadores.length ? estado.jugadores[0].id : null;

    return estado;
  }

  function cargar() {
    try {
      var crudo = almacen.api.getItem(CLAVE);
      if (!crudo) return estadoInicial();
      return normaliza(JSON.parse(crudo));
    } catch (err) {
      console.error('No se pudo leer la liga guardada:', err);
      return estadoInicial();
    }
  }

  function guardar(estado) {
    try {
      almacen.api.setItem(CLAVE, JSON.stringify(estado));
      return { ok: true };
    } catch (err) {
      return { ok: false, error: err };
    }
  }

  // --- Fotos ----------------------------------------------------------------

  function guardarFoto(entradaId, dataUrl) {
    try {
      almacen.api.setItem(CLAVE_FOTO + entradaId, dataUrl);
      return { ok: true };
    } catch (err) {
      // Cuota llena: es el fallo mas probable de toda la app.
      return { ok: false, error: err };
    }
  }

  function leerFoto(entradaId) {
    try {
      return almacen.api.getItem(CLAVE_FOTO + entradaId);
    } catch (err) {
      return null;
    }
  }

  function borrarFoto(entradaId) {
    try {
      almacen.api.removeItem(CLAVE_FOTO + entradaId);
    } catch (err) { /* da igual */ }
  }

  function espacioUsado() {
    var total = 0;
    try {
      for (var i = 0; i < almacen.api.length; i++) {
        var k = almacen.api.key(i);
        if (k && k.indexOf('liga.') === 0) total += (almacen.api.getItem(k) || '').length;
      }
    } catch (err) { /* nada */ }
    return total * 2; // UTF-16: ~2 bytes por caracter
  }

  /**
   * Reduce y comprime la foto antes de guardarla. Una foto de movil son 3-5 MB
   * y el navegador solo deja unos 5 MB en total, asi que sin esto la app se
   * llena con cuatro fotos.
   */
  function comprimirImagen(file, ladoMaximo, calidad, callback) {
    ladoMaximo = ladoMaximo || 640;
    calidad = calidad || 0.6;
    var lector = new FileReader();
    lector.onload = function () {
      var img = new Image();
      img.onload = function () {
        var escala = Math.min(1, ladoMaximo / Math.max(img.width, img.height));
        var ancho = Math.round(img.width * escala);
        var alto = Math.round(img.height * escala);
        var canvas = document.createElement('canvas');
        canvas.width = ancho;
        canvas.height = alto;
        canvas.getContext('2d').drawImage(img, 0, 0, ancho, alto);
        try {
          callback(null, canvas.toDataURL('image/jpeg', calidad));
        } catch (err) {
          callback(err);
        }
      };
      img.onerror = function () { callback(new Error('No se pudo leer la imagen')); };
      img.src = lector.result;
    };
    lector.onerror = function () { callback(new Error('No se pudo abrir el archivo')); };
    lector.readAsDataURL(file);
  }

  // --- Exportar / importar --------------------------------------------------

  /**
   * Copia de seguridad completa. `conFotos` la hace mucho mas grande, pero es
   * la unica forma de mover la liga entera a otro movil.
   */
  function exportar(estado, conFotos) {
    var copia = JSON.parse(JSON.stringify(estado));
    copia.exportado = new Date().toISOString();
    if (conFotos) {
      copia.fotos = {};
      estado.entradas.forEach(function (e) {
        if (!e.tieneFoto) return;
        var foto = leerFoto(e.id);
        if (foto) copia.fotos[e.id] = foto;
      });
    }
    return copia;
  }

  /**
   * Importa un fichero exportado. Modo "reemplazar" pisa todo; modo "fusionar"
   * anade jugadores/entradas/votos que no existan (util para juntar lo que ha
   * registrado cada uno en su movil).
   */
  function importar(estadoActual, datos, modo) {
    if (!datos || typeof datos !== 'object') throw new Error('El archivo no tiene el formato esperado');

    var fotos = datos.fotos || {};
    delete datos.fotos;

    var resultado;
    if (modo === 'fusionar') {
      resultado = normaliza(JSON.parse(JSON.stringify(estadoActual)));

      var idsJugador = {};
      resultado.jugadores.forEach(function (j) { idsJugador[j.id] = true; });
      (datos.jugadores || []).forEach(function (j) {
        if (!idsJugador[j.id]) { resultado.jugadores.push(j); idsJugador[j.id] = true; }
      });

      var idsEntrada = {};
      resultado.entradas.forEach(function (e) { idsEntrada[e.id] = true; });
      (datos.entradas || []).forEach(function (e) {
        if (!idsEntrada[e.id]) { resultado.entradas.push(e); idsEntrada[e.id] = true; }
      });

      Object.keys(datos.votos || {}).forEach(function (entradaId) {
        resultado.votos[entradaId] = Object.assign({}, datos.votos[entradaId], resultado.votos[entradaId]);
      });
    } else {
      resultado = normaliza(datos);
    }

    var fallos = 0;
    Object.keys(fotos).forEach(function (entradaId) {
      if (!guardarFoto(entradaId, fotos[entradaId]).ok) fallos++;
    });

    return { estado: resultado, fotosFallidas: fallos };
  }

  /**
   * Borra las imagenes guardadas pero deja las entradas, los puntos y los
   * votos como estan. Es la salida rapida si os arrepentis de tener copias.
   */
  function borrarTodasLasFotos(estado) {
    var borradas = 0;
    estado.entradas.forEach(function (e) {
      if (!e.tieneFoto) return;
      borrarFoto(e.id);
      e.tieneFoto = false;
      borradas++;
    });
    return borradas;
  }

  function borrarTodo() {
    var claves = [];
    for (var i = 0; i < almacen.api.length; i++) {
      var k = almacen.api.key(i);
      if (k && k.indexOf('liga.') === 0) claves.push(k);
    }
    claves.forEach(function (k) { almacen.api.removeItem(k); });
  }

  var api = {
    CLAVE: CLAVE,
    COLORES: COLORES,
    id: id,
    estadoInicial: estadoInicial,
    normaliza: normaliza,
    cargar: cargar,
    guardar: guardar,
    guardadoPermanente: guardadoPermanente,
    guardarFoto: guardarFoto,
    leerFoto: leerFoto,
    borrarFoto: borrarFoto,
    espacioUsado: espacioUsado,
    comprimirImagen: comprimirImagen,
    exportar: exportar,
    importar: importar,
    borrarTodasLasFotos: borrarTodasLasFotos,
    borrarTodo: borrarTodo
  };

  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  global.Datos = api;
})(typeof window !== 'undefined' ? window : globalThis);
