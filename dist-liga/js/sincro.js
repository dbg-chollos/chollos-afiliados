/*
 * sincro.js — juntar lo del movil con lo del servidor.
 *
 * La app sigue siendo local: se apunta en el movil y se guarda ahi al momento,
 * con o sin cobertura. Esto solo sube lo que falta y baja lo de los demas.
 *
 * Todo se identifica por el id que genera el propio movil, asi que subir dos
 * veces lo mismo no duplica nada. Eso permite sincronizar a lo bruto cada vez
 * en vez de llevar la cuenta de lo que ya se envio, que es donde suelen estar
 * los fallos raros.
 */
(function (global) {
  'use strict';

  var N = global.Nube;
  var D = global.Datos;
  var E = global.Estadisticas;

  /** ¿Esta la app enlazada a una liga del servidor? */
  function enNube() {
    return !!(N && N.configurada() && N.conectado() && N.vinculo());
  }

  function miId() {
    var u = N.usuario();
    return u ? u.id : null;
  }

  // --- Traduccion entre lo de aqui y lo de alla -----------------------------

  function aServidor(entrada, ligaId) {
    return {
      id: entrada.id,
      liga_id: ligaId,
      usuario: entrada.jugadorId,
      fecha: new Date(entrada.fecha).toISOString(),
      rechazo: !!entrada.rechazo,
      fiesta: !!entrada.fiesta,
      lugar: entrada.lugar || null,
      resultado: entrada.resultado,
      foto: entrada.fotoNube || null,
      perfil: entrada.perfil || null
    };
  }

  function aLocal(fila) {
    return {
      id: fila.id,
      jugadorId: fila.usuario,
      fecha: fila.fecha,
      rechazo: !!fila.rechazo,
      fiesta: !!fila.fiesta,
      lugar: fila.lugar,
      resultado: fila.resultado,
      perfil: fila.perfil || null,
      fotoNube: fila.foto || null,
      // Si la foto esta en el servidor pero todavia no en este movil, se baja
      // solo cuando haga falta verla (al ir a votar).
      tieneFoto: !!D.leerFoto(fila.id)
    };
  }

  // --- Enlazar ---------------------------------------------------------------

  /**
   * Pasa la liga de este movil a la nube. Las entradas propias se conservan y
   * cambian de dueno al usuario de verdad; los jugadores inventados a mano
   * desaparecen, porque a partir de ahora los jugadores son quienes entran.
   */
  function adoptarLiga(estado, liga) {
    var yo = miId();
    var anterior = estado.yo;

    estado.entradas.forEach(function (e) {
      if (e.jugadorId === anterior) e.jugadorId = yo;
    });

    Object.keys(estado.votos).forEach(function (entradaId) {
      var votos = estado.votos[entradaId];
      if (votos[anterior] !== undefined) {
        votos[yo] = votos[anterior];
        delete votos[anterior];
      }
    });

    // Fuera lo que no sea de nadie real: los jugadores llegan de los miembros.
    estado.entradas = estado.entradas.filter(function (e) { return e.jugadorId === yo; });
    estado.jugadores = [];
    estado.yo = yo;
    estado.liga.nombre = liga.nombre;

    return estado;
  }

  // --- Sincronizar ----------------------------------------------------------

  function fusionaMiembros(estado, filas) {
    estado.jugadores = filas.map(function (m) {
      return { id: m.usuario, nombre: m.nombre, color: m.color, creado: m.unido };
    });
    var existe = estado.jugadores.some(function (j) { return j.id === estado.yo; });
    if (!existe && estado.jugadores.length) estado.yo = miId() || estado.jugadores[0].id;
  }

  function fusionaEntradas(estado, filas) {
    var porId = {};
    estado.entradas.forEach(function (e) { porId[e.id] = e; });

    filas.forEach(function (fila) {
      var local = porId[fila.id];
      if (!local) {
        estado.entradas.push(aLocal(fila));
        return;
      }
      // Lo que manda el servidor sobre lo que ya hay: el otro pudo corregirla.
      local.fotoNube = fila.foto || local.fotoNube || null;
      local.perfil = fila.perfil || local.perfil || null;
      local.resultado = fila.resultado;
      local.rechazo = !!fila.rechazo;
      local.fiesta = !!fila.fiesta;
      local.lugar = fila.lugar;
    });
  }

  function fusionaVotos(estado, filas) {
    filas.forEach(function (fila) {
      if (!estado.votos[fila.entrada_id]) estado.votos[fila.entrada_id] = {};
      estado.votos[fila.entrada_id][fila.usuario] = fila.nota;
    });
  }

  /**
   * Las reglas son de la liga, no del movil. Si cada uno tuviera las suyas,
   * el mismo lio valdria distinto en cada telefono y cada uno veria una
   * clasificacion diferente sin entender por que. Manda la liga: las escribe
   * quien la creo y las demas se las bajan.
   */
  function fusionaReglas(estado, liga) {
    if (!liga) return;
    estado.liga.creadaPor = liga.creada_por;
    var reglas = liga.reglas;
    if (!reglas || typeof reglas !== 'object' || !Object.keys(reglas).length) return;

    var base = D.normaliza({
      jugadores: [], entradas: [], votos: {}, reglas: reglas
    }).reglas;
    // El modo de foto sigue siendo cosa de cada uno: es sobre su propio movil.
    base.modoFoto = estado.reglas.modoFoto;
    base.modoFotoElegido = estado.reglas.modoFotoElegido;
    estado.reglas = base;
  }

  /** ¿Es quien creo la liga? Solo esa persona puede cambiar las reglas. */
  function soyElJefe(estado) {
    return !!(estado.liga && estado.liga.creadaPor && estado.liga.creadaPor === miId());
  }

  function misEntradas(estado) {
    var yo = miId();
    return estado.entradas.filter(function (e) { return e.jugadorId === yo; });
  }

  /** Sube las fotos que aun estan solo en este movil y anota su ruta. */
  function subirFotosPendientes(estado, ligaId) {
    var pendientes = misEntradas(estado).filter(function (e) {
      return e.tieneFoto && !e.fotoNube;
    });
    return pendientes.reduce(function (cadena, entrada) {
      return cadena.then(function () {
        var dataUrl = D.leerFoto(entrada.id);
        if (!dataUrl) return null;
        return N.subirFoto(ligaId, entrada.id, dataUrl).then(function (ruta) {
          entrada.fotoNube = ruta;
        }).catch(function (err) {
          // Una foto que no sube no puede tumbar la sincronizacion entera.
          console.warn('No se pudo subir la foto de', entrada.id, err);
        });
      });
    }, Promise.resolve());
  }

  /**
   * Baja solo las fotos que hacen falta para votar ahora mismo. Bajarlas todas
   * llenaria la memoria del navegador, que son unos 5 MB contados.
   */
  function bajarFotosParaVotar(estado) {
    var yo = miId();
    var pendientes = estado.entradas.filter(function (e) {
      if (e.jugadorId === yo || !e.fotoNube || e.tieneFoto) return false;
      var votos = estado.votos[e.id] || {};
      return votos[yo] === undefined;
    }).slice(0, 20);

    return pendientes.reduce(function (cadena, entrada) {
      return cadena.then(function () {
        return N.descargarFoto(entrada.fotoNube).then(function (dataUrl) {
          if (D.guardarFoto(entrada.id, dataUrl).ok) entrada.tieneFoto = true;
        }).catch(function (err) {
          console.warn('No se pudo bajar la foto de', entrada.id, err);
        });
      });
    }, Promise.resolve());
  }

  function misVotos(estado) {
    var yo = miId();
    var filas = [];
    Object.keys(estado.votos).forEach(function (entradaId) {
      var nota = estado.votos[entradaId][yo];
      if (nota >= 1 && nota <= 10) {
        filas.push({ entrada_id: entradaId, usuario: yo, nota: nota });
      }
    });
    return filas;
  }

  /**
   * Una pasada completa: subir lo mio, bajar lo de todos, guardar.
   * Devuelve un resumen para poder decir algo util por pantalla.
   */
  function sincronizar(estado) {
    if (!enNube()) return Promise.resolve({ omitido: true });

    var ligaId = N.vinculo().id;
    var resumen = { subidas: 0, bajadas: 0 };

    return subirFotosPendientes(estado, ligaId)
      .then(function () {
        var mias = misEntradas(estado).map(function (e) { return aServidor(e, ligaId); });
        resumen.subidas = mias.length;
        return N.guardarFilas('entradas', mias);
      })
      .then(function () { return N.guardarFilas('votos', misVotos(estado)); })
      .then(function () { return N.miLiga(); })
      .then(function (liga) { fusionaReglas(estado, liga); })
      .then(function () { return N.miembros(ligaId); })
      .then(function (filas) { fusionaMiembros(estado, filas || []); })
      .then(function () { return N.entradas(ligaId); })
      .then(function (filas) {
        resumen.bajadas = (filas || []).length;
        fusionaEntradas(estado, filas || []);
      })
      .then(function () { return N.votos(ligaId); })
      .then(function (filas) { fusionaVotos(estado, filas || []); })
      .then(function () { return bajarFotosParaVotar(estado); })
      .then(function () {
        D.guardar(estado);
        return resumen;
      });
  }

  /** Sube las reglas a la liga. Solo cuela si eres quien la creo. */
  function publicarReglas(estado) {
    if (!enNube() || !soyElJefe(estado)) return Promise.resolve();
    return N.guardarReglas(N.vinculo().id, estado.reglas);
  }

  var api = {
    enNube: enNube,
    miId: miId,
    soyElJefe: soyElJefe,
    publicarReglas: publicarReglas,
    adoptarLiga: adoptarLiga,
    sincronizar: sincronizar,
    aServidor: aServidor,
    aLocal: aLocal
  };

  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  global.Sincro = api;
})(typeof window !== 'undefined' ? window : globalThis);
