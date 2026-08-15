/*
 * nube.js — hablar con Supabase.
 *
 * Todo va por fetch contra la API de Supabase, sin librerias: la app no carga
 * nada de internet y sigue funcionando de un archivo suelto.
 *
 * Dos ideas que conviene tener claras al leer esto:
 *
 * 1. La app sigue siendo local. Se apunta en el movil y se guarda ahi; la nube
 *    es una copia comun que se sincroniza cuando hay internet. Si estas en el
 *    garito sin cobertura, apuntas igual y sube luego.
 *
 * 2. Se entra con correo y contrasena, sin nada por correo electronico. Las dos
 *    alternativas se descartaron por lo mismo: el plan gratuito de Supabase
 *    manda muy pocos correos por hora, asi que si cuatro amigos se registran la
 *    misma noche, los ultimos se quedan esperando un correo que no llega. Y un
 *    enlace magico, ademas, abriria el navegador en vez de la app instalada.
 *
 *    Para que esto funcione hay que desactivar "Confirm email" en el panel
 *    (Authentication -> Sign In / Providers -> Email).
 */
(function (global) {
  'use strict';

  var CLAVE_SESION = 'liga.sesion.v1';
  var CLAVE_VINCULO = 'liga.nube.v1';

  function config() {
    return global.ConfigNube || { URL: '', CLAVE_PUBLICA: '' };
  }

  /** ¿Hay servidor configurado? Si no, la app va en modo local y ya esta. */
  function configurada() {
    var c = config();
    return !!(c.URL && c.CLAVE_PUBLICA);
  }

  function url(camino) {
    return config().URL.replace(/\/+$/, '') + camino;
  }

  // --- Sesion ---------------------------------------------------------------

  var sesion = null;

  function leerGuardado(clave) {
    try {
      var crudo = localStorage.getItem(clave);
      return crudo ? JSON.parse(crudo) : null;
    } catch (err) {
      return null;
    }
  }

  function escribirGuardado(clave, valor) {
    try {
      if (valor === null) localStorage.removeItem(clave);
      else localStorage.setItem(clave, JSON.stringify(valor));
    } catch (err) { /* sin almacenamiento: la sesion dura lo que la pestana */ }
  }

  function cargarSesion() {
    if (!sesion) sesion = leerGuardado(CLAVE_SESION);
    return sesion;
  }

  function guardarSesion(datos) {
    sesion = datos;
    escribirGuardado(CLAVE_SESION, datos);
  }

  function usuario() {
    var s = cargarSesion();
    return s && s.user ? s.user : null;
  }

  function conectado() {
    return !!cargarSesion();
  }

  /** El vinculo con una liga concreta: su id, su codigo y su nombre. */
  function vinculo() {
    return leerGuardado(CLAVE_VINCULO);
  }

  function guardarVinculo(datos) {
    escribirGuardado(CLAVE_VINCULO, datos);
  }

  // --- Peticiones -----------------------------------------------------------

  function cabeceras(conSesion) {
    var h = {
      apikey: config().CLAVE_PUBLICA,
      'Content-Type': 'application/json'
    };
    var s = conSesion !== false && cargarSesion();
    if (s && s.access_token) h.Authorization = 'Bearer ' + s.access_token;
    return h;
  }

  function mensajeDeError(cuerpo, respuesta) {
    if (cuerpo && typeof cuerpo === 'object') {
      var texto = cuerpo.message || cuerpo.error_description || cuerpo.msg ||
        cuerpo.error || cuerpo.hint;
      if (texto) return texto;
    }
    return 'Error ' + respuesta.status;
  }

  function pedir(camino, opciones) {
    opciones = opciones || {};
    return fetch(url(camino), {
      method: opciones.method || 'GET',
      headers: Object.assign(cabeceras(opciones.conSesion), opciones.headers || {}),
      body: opciones.body === undefined ? undefined : JSON.stringify(opciones.body)
    }).then(function (respuesta) {
      var vacia = respuesta.status === 204 || respuesta.status === 205;
      return (vacia ? Promise.resolve(null) : respuesta.text().then(function (t) {
        try { return t ? JSON.parse(t) : null; } catch (err) { return t; }
      })).then(function (cuerpo) {
        if (respuesta.ok) return cuerpo;
        var error = new Error(mensajeDeError(cuerpo, respuesta));
        error.status = respuesta.status;
        throw error;
      });
    });
  }

  /**
   * Como pedir(), pero si la sesion ha caducado la renueva y reintenta una vez.
   * Los tokens duran una hora; sin esto habria que volver a entrar cada rato.
   */
  function pedirConSesion(camino, opciones) {
    return pedir(camino, opciones).catch(function (err) {
      if (err.status !== 401 || !cargarSesion()) throw err;
      return renovar().then(function () { return pedir(camino, opciones); });
    });
  }

  function renovar() {
    var s = cargarSesion();
    if (!s || !s.refresh_token) return Promise.reject(new Error('No hay sesion'));
    return pedir('/auth/v1/token?grant_type=refresh_token', {
      method: 'POST',
      conSesion: false,
      body: { refresh_token: s.refresh_token }
    }).then(function (datos) {
      guardarSesion(datos);
      return datos;
    }).catch(function (err) {
      // Si ni renovando entra, la sesion esta muerta: mejor pedir el correo otra vez.
      guardarSesion(null);
      throw err;
    });
  }

  // --- Entrar y salir -------------------------------------------------------

  function limpiaCorreo(email) {
    return String(email || '').trim().toLowerCase();
  }

  /**
   * Traduce los mensajes de Supabase, que vienen en ingles y de tecnico.
   * Alguien que se registra a las cuatro de la manana no merece leer
   * "Invalid login credentials".
   */
  function enCristiano(err) {
    var texto = (err && err.message ? err.message : '').toLowerCase();
    if (texto.indexOf('invalid login credentials') !== -1) {
      return new Error('El correo o la contrasena no son correctos');
    }
    if (texto.indexOf('already registered') !== -1 || texto.indexOf('already exists') !== -1) {
      return new Error('Ese correo ya tiene cuenta: entra en vez de registrarte');
    }
    if (texto.indexOf('password should be') !== -1 || texto.indexOf('at least') !== -1) {
      return new Error('La contrasena tiene que tener 6 caracteres o mas');
    }
    if (texto.indexOf('email not confirmed') !== -1) {
      return new Error('Falta desactivar "Confirm email" en el panel de Supabase');
    }
    if (texto.indexOf('failed to fetch') !== -1 || texto.indexOf('networkerror') !== -1) {
      return new Error('Sin conexion. Se guarda en el movil y sube cuando vuelvas a tener internet');
    }
    return err;
  }

  function guardarYDevolver(datos) {
    if (!datos || !datos.access_token) {
      throw new Error('El servidor no ha devuelto una sesion');
    }
    guardarSesion(datos);
    return datos;
  }

  /** Crear cuenta. Sin "Confirm email" activo, entra directamente. */
  function registrarse(email, contrasena) {
    return pedir('/auth/v1/signup', {
      method: 'POST',
      conSesion: false,
      body: { email: limpiaCorreo(email), password: String(contrasena) }
    }).then(guardarYDevolver).catch(function (err) { throw enCristiano(err); });
  }

  function entrar(email, contrasena) {
    return pedir('/auth/v1/token?grant_type=password', {
      method: 'POST',
      conSesion: false,
      body: { email: limpiaCorreo(email), password: String(contrasena) }
    }).then(guardarYDevolver).catch(function (err) { throw enCristiano(err); });
  }

  function salir() {
    var s = cargarSesion();
    guardarSesion(null);
    guardarVinculo(null);
    if (!s) return Promise.resolve();
    return pedir('/auth/v1/logout', { method: 'POST' }).catch(function () { /* da igual */ });
  }

  // --- Ligas ----------------------------------------------------------------

  function codigoNuevo() {
    // Sin vocales ni caracteres que se confundan (0/O, 1/I): se dicta en voz alta.
    var letras = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
    var codigo = '';
    for (var i = 0; i < 5; i++) {
      codigo += letras[Math.floor(Math.random() * letras.length)];
    }
    return 'LIGA-' + codigo;
  }

  function crearLiga(nombre, jugador, color, reglas) {
    var codigo = codigoNuevo();
    return pedirConSesion('/rest/v1/rpc/crear_liga', {
      method: 'POST',
      body: {
        p_nombre: nombre,
        p_codigo: codigo,
        p_jugador: jugador,
        p_color: color || '#e5484d',
        p_reglas: reglas || {}
      }
    }).then(function (liga) {
      guardarVinculo({ id: liga.id, codigo: liga.codigo, nombre: liga.nombre });
      return liga;
    });
  }

  function unirse(codigo, jugador, color) {
    return pedirConSesion('/rest/v1/rpc/unirse_a_liga', {
      method: 'POST',
      body: { p_codigo: codigo, p_jugador: jugador, p_color: color || '#3e63dd' }
    }).then(function (liga) {
      guardarVinculo({ id: liga.id, codigo: liga.codigo, nombre: liga.nombre });
      return liga;
    });
  }

  // --- Fotos ----------------------------------------------------------------

  function dataUrlABlob(dataUrl) {
    var partes = dataUrl.split(',');
    var tipo = (partes[0].match(/:(.*?);/) || [])[1] || 'image/jpeg';
    var binario = atob(partes[1]);
    var bytes = new Uint8Array(binario.length);
    for (var i = 0; i < binario.length; i++) bytes[i] = binario.charCodeAt(i);
    return new Blob([bytes], { type: tipo });
  }

  function subirFoto(ligaId, entradaId, dataUrl) {
    var ruta = ligaId + '/' + entradaId + '.jpg';
    var s = cargarSesion();
    return fetch(url('/storage/v1/object/' + ruta.replace(/^/, 'fotos/')), {
      method: 'POST',
      headers: {
        apikey: config().CLAVE_PUBLICA,
        Authorization: 'Bearer ' + (s ? s.access_token : ''),
        'Content-Type': 'image/jpeg',
        'x-upsert': 'true'
      },
      body: dataUrlABlob(dataUrl)
    }).then(function (r) {
      if (!r.ok) return r.text().then(function (t) { throw new Error('No se pudo subir la foto: ' + t); });
      return ruta;
    });
  }

  function descargarFoto(ruta) {
    var s = cargarSesion();
    return fetch(url('/storage/v1/object/authenticated/fotos/' + ruta), {
      headers: {
        apikey: config().CLAVE_PUBLICA,
        Authorization: 'Bearer ' + (s ? s.access_token : '')
      }
    }).then(function (r) {
      if (!r.ok) throw new Error('No se pudo bajar la foto');
      return r.blob();
    }).then(function (blob) {
      return new Promise(function (resolve, reject) {
        var lector = new FileReader();
        lector.onload = function () { resolve(lector.result); };
        lector.onerror = function () { reject(new Error('Foto ilegible')); };
        lector.readAsDataURL(blob);
      });
    });
  }

  // --- Leer y escribir la liga ---------------------------------------------

  function miembros(ligaId) {
    return pedirConSesion('/rest/v1/miembros?select=*&liga_id=eq.' + encodeURIComponent(ligaId));
  }

  function entradas(ligaId) {
    return pedirConSesion('/rest/v1/entradas?select=*&liga_id=eq.' +
      encodeURIComponent(ligaId) + '&order=fecha.asc');
  }

  /**
   * Los votos no llevan liga_id: cuelgan de la entrada. PostgREST permite
   * filtrar por la tabla relacionada con !inner, que es justo lo que hace falta.
   */
  function votos(ligaId) {
    return pedirConSesion('/rest/v1/votos?select=entrada_id,usuario,nota,entradas!inner(liga_id)' +
      '&entradas.liga_id=eq.' + encodeURIComponent(ligaId));
  }

  /** Upsert: repetir el envio de algo ya subido no duplica ni falla. */
  function guardarFilas(tabla, filas) {
    if (!filas.length) return Promise.resolve([]);
    return pedirConSesion('/rest/v1/' + tabla, {
      method: 'POST',
      headers: { Prefer: 'resolution=merge-duplicates,return=minimal' },
      body: filas
    });
  }

  function borrarEntrada(id) {
    return pedirConSesion('/rest/v1/entradas?id=eq.' + encodeURIComponent(id), {
      method: 'DELETE',
      headers: { Prefer: 'return=minimal' }
    });
  }

  function guardarReglas(ligaId, reglas) {
    return pedirConSesion('/rest/v1/ligas?id=eq.' + encodeURIComponent(ligaId), {
      method: 'PATCH',
      headers: { Prefer: 'return=minimal' },
      body: { reglas: reglas }
    });
  }

  function miLiga() {
    return pedirConSesion('/rest/v1/ligas?select=*').then(function (filas) {
      return filas && filas.length ? filas[0] : null;
    });
  }

  var api = {
    configurada: configurada,
    conectado: conectado,
    usuario: usuario,
    vinculo: vinculo,
    guardarVinculo: guardarVinculo,
    registrarse: registrarse,
    entrar: entrar,
    salir: salir,
    crearLiga: crearLiga,
    unirse: unirse,
    subirFoto: subirFoto,
    descargarFoto: descargarFoto,
    miembros: miembros,
    entradas: entradas,
    votos: votos,
    guardarFilas: guardarFilas,
    borrarEntrada: borrarEntrada,
    guardarReglas: guardarReglas,
    miLiga: miLiga,
    pedir: pedirConSesion
  };

  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  global.Nube = api;
})(typeof window !== 'undefined' ? window : globalThis);
