/*
 * app.js — pantallas, navegacion y el asistente de registro.
 *
 * La logica de puntos esta en reglas.js y la de clasificaciones en
 * estadisticas.js. Aqui solo se pinta y se recogen los toques del usuario.
 */
(function () {
  'use strict';

  var R = window.Reglas;
  var D = window.Datos;
  var E = window.Estadisticas;

  var estado = D.cargar();
  var vistaActual = 'registrar';
  var tablaActual = 'general';
  var periodoActual = 'dia';

  // Entrada a medio rellenar. No se guarda hasta el ultimo paso.
  var borrador = nuevoBorrador();

  // --- Utilidades -----------------------------------------------------------

  function $(sel) { return document.querySelector(sel); }
  function $$(sel) { return Array.prototype.slice.call(document.querySelectorAll(sel)); }

  function esc(txt) {
    return String(txt === null || txt === undefined ? '' : txt)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  function hoyISO() {
    var d = new Date();
    return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');
  }

  function jugador(id) {
    for (var i = 0; i < estado.jugadores.length; i++) {
      if (estado.jugadores[i].id === id) return estado.jugadores[i];
    }
    return null;
  }

  function nombreDe(id) {
    var j = jugador(id);
    return j ? j.nombre : '¿?';
  }

  function punto(j) {
    return '<span class="punto" style="background:' + esc(j ? j.color : '#666') + '"></span>';
  }

  function etiquetaResultado(id) {
    for (var i = 0; i < R.RESULTADOS.length; i++) {
      if (R.RESULTADOS[i].id === id) return R.RESULTADOS[i];
    }
    return { id: id, etiqueta: id, emoji: '' };
  }

  function fechaCorta(iso) {
    var d = new Date(iso);
    return String(d.getDate()).padStart(2, '0') + '/' + String(d.getMonth() + 1).padStart(2, '0');
  }

  function fechaLarga(iso) {
    return new Date(iso).toLocaleDateString('es-ES', { day: 'numeric', month: 'long', year: 'numeric' });
  }

  var temporizadorAviso = null;
  function aviso(texto) {
    var caja = $('#aviso-flotante');
    caja.textContent = texto;
    caja.hidden = false;
    clearTimeout(temporizadorAviso);
    temporizadorAviso = setTimeout(function () { caja.hidden = true; }, 2800);
  }

  function persistir() {
    var res = D.guardar(estado);
    if (!res.ok) {
      aviso('No se pudo guardar: memoria del navegador llena. Exporta y borra alguna foto.');
    }
  }

  function abrirModal(html) {
    $('#modal-contenido').innerHTML = html;
    $('#modal').hidden = false;
  }
  function cerrarModal() { $('#modal').hidden = true; }

  // --- Navegacion -----------------------------------------------------------

  function irA(vista) {
    vistaActual = vista;
    $$('.vista').forEach(function (v) { v.classList.remove('activa'); });
    var destino = $('#vista-' + vista);
    if (destino) destino.classList.add('activa');
    $$('.nav-btn').forEach(function (b) {
      b.classList.toggle('activo', b.dataset.vista === vista);
    });
    window.scrollTo(0, 0);
    pintar();
  }

  function hayJugadores() { return estado.jugadores.length > 0; }

  function pintar() {
    if (!hayJugadores()) {
      $$('.vista').forEach(function (v) { v.classList.remove('activa'); });
      $('#vista-inicio').classList.add('activa');
      $('#navegacion').style.display = 'none';
      pintarInicio();
      return;
    }
    $('#navegacion').style.display = 'flex';
    $('#vista-inicio').classList.remove('activa');
    if (!$('#vista-' + vistaActual).classList.contains('activa')) {
      $('#vista-' + vistaActual).classList.add('activa');
    }

    pintarCabecera();
    if (vistaActual === 'registrar') pintarRegistrar();
    if (vistaActual === 'clasificacion') pintarClasificacion();
    if (vistaActual === 'votar') pintarVotar();
    if (vistaActual === 'campeones') pintarCampeones();
    if (vistaActual === 'ajustes') pintarAjustes();
  }

  // --- Cabecera -------------------------------------------------------------

  function pintarCabecera() {
    $('#titulo-liga').textContent = estado.liga.nombre || 'La Liga';

    var yo = jugador(estado.yo);
    $('#btn-yo').innerHTML = punto(yo) + esc(yo ? yo.nombre : 'Elegir');

    var pendientes = estado.yo ? E.pendientesDeVotar(estado, estado.yo).length : 0;
    var badge = $('#nav-badge');
    badge.hidden = pendientes === 0;
    badge.textContent = pendientes;

    var liga = E.estadoLiga(estado);
    var texto;
    if (liga.terminada && liga.campeon) {
      texto = '🏆 Liga terminada. Campeon: <strong>' + esc(liga.campeon.jugador.nombre) + '</strong>';
    } else if (yo) {
      var r = E.resumenJugador(estado, yo);
      texto = r.entradas + ' / ' + estado.reglas.limiteLiga + ' entradas · <strong>' +
        r.puntos + ' pts</strong>' +
        (r.extras ? ' · ' + r.extras + ' fuera de liga' : '');
    } else {
      texto = 'Elige quien eres arriba a la derecha.';
    }
    $('#barra-liga').innerHTML = texto;
  }

  // --- Alta inicial ---------------------------------------------------------

  var jugadoresIniciales = [];

  function pintarInicio() {
    var ul = $('#inicio-lista');
    ul.innerHTML = jugadoresIniciales.map(function (n, i) {
      return '<li>' + '<span class="punto" style="background:' + D.COLORES[i % D.COLORES.length] + '"></span>' +
        '<span class="nombre">' + esc(n) + '</span>' +
        '<button data-quitar="' + i + '" type="button">Quitar</button></li>';
    }).join('') || '<li class="vacio">Todavia no hay nadie</li>';
    $('#inicio-empezar').disabled = jugadoresIniciales.length === 0;
  }

  function conectarInicio() {
    function añadir() {
      var input = $('#inicio-jugador');
      var nombre = input.value.trim();
      if (!nombre) return;
      jugadoresIniciales.push(nombre);
      input.value = '';
      input.focus();
      pintarInicio();
    }
    $('#inicio-añadir').addEventListener('click', añadir);
    $('#inicio-jugador').addEventListener('keydown', function (ev) {
      if (ev.key === 'Enter') { ev.preventDefault(); añadir(); }
    });
    $('#inicio-lista').addEventListener('click', function (ev) {
      var i = ev.target.dataset.quitar;
      if (i === undefined) return;
      jugadoresIniciales.splice(Number(i), 1);
      pintarInicio();
    });
    $('#inicio-empezar').addEventListener('click', function () {
      var nombreLiga = $('#inicio-nombre-liga').value.trim();
      if (nombreLiga) estado.liga.nombre = nombreLiga;
      jugadoresIniciales.forEach(function (nombre, i) {
        estado.jugadores.push({
          id: D.id(),
          nombre: nombre,
          color: D.COLORES[i % D.COLORES.length],
          creado: new Date().toISOString()
        });
      });
      estado.yo = estado.jugadores[0].id;
      persistir();
      jugadoresIniciales = [];
      irA('registrar');
    });
  }

  // --- Registrar ------------------------------------------------------------

  function nuevoBorrador() {
    return {
      fecha: hoyISO(),
      rechazo: null,
      fiesta: null,
      lugar: null,
      resultado: null,
      foto: null,
      perfil: ''
    };
  }

  function opcion(valor, emoji, etiqueta, pista) {
    return '<button class="opcion" type="button" data-valor="' + esc(valor) + '">' +
      '<span class="emoji">' + emoji + '</span>' +
      '<span>' + esc(etiqueta) + '</span>' +
      (pista ? '<span class="puntos-pista">' + esc(pista) + '</span>' : '') +
      '</button>';
  }

  function resuelto(campo, etiqueta, valor) {
    return '<button class="resuelto" type="button" data-cambiar="' + campo + '">' +
      '<span><span class="etiqueta">' + esc(etiqueta) + '</span><br><span class="valor">' + esc(valor) + '</span></span>' +
      '<span class="cambiar">cambiar</span></button>';
  }

  function bloquePaso(titulo, contenido, campo) {
    return '<div class="paso" data-campo="' + campo + '">' +
      '<div class="paso-titulo">' + esc(titulo) + '</div>' + contenido + '</div>';
  }

  /** Entrada tal y como quedaria con lo que lleva marcado el borrador. */
  function entradaProvisional() {
    return {
      rechazo: !!borrador.rechazo,
      fiesta: !!borrador.fiesta,
      lugar: borrador.lugar,
      resultado: borrador.resultado || 'nada'
    };
  }

  function pintarRegistrar() {
    $('#reg-fecha').value = borrador.fecha;

    var html = '';
    var b = borrador;

    // 1. Rechazo
    if (b.rechazo === null) {
      html += bloquePaso('¿Te ha rechazado?', '<div class="opciones">' +
        opcion('no', '✅', 'No me ha rechazado') +
        opcion('si', '❌', 'Me ha rechazado') +
        '</div>', 'rechazo');
      $('#reg-pasos').innerHTML = html;
      conectarPasos();
      return pintarHistorialPropio();
    }
    html += resuelto('rechazo', 'Rechazo', b.rechazo ? 'Me ha rechazado' : 'No me ha rechazado');

    // 2. Fiesta
    if (b.fiesta === null) {
      html += bloquePaso('¿Fue de fiesta?', '<div class="opciones">' +
        opcion('si', '🎉', 'De fiesta') +
        opcion('no', '☀️', 'Fuera de fiesta') +
        '</div>', 'fiesta');
      $('#reg-pasos').innerHTML = html;
      conectarPasos();
      return pintarHistorialPropio();
    }
    html += resuelto('fiesta', 'Ambiente', b.fiesta ? 'De fiesta' : 'Fuera de fiesta');

    // 3. Lugar (solo si fue de fiesta)
    if (b.fiesta) {
      if (!b.lugar) {
        html += bloquePaso('¿Donde?', '<div class="opciones">' +
          R.LUGARES.map(function (l) { return opcion(l.id, l.emoji, l.etiqueta); }).join('') +
          '</div>', 'lugar');
        $('#reg-pasos').innerHTML = html;
        conectarPasos();
        return pintarHistorialPropio();
      }
      var lug = R.LUGARES.filter(function (l) { return l.id === b.lugar; })[0];
      html += resuelto('lugar', 'Sitio', lug ? lug.etiqueta : b.lugar);
    }

    // 4. Resultado (si no hubo rechazo)
    if (!b.rechazo) {
      if (!b.resultado) {
        var dentro = R.esDentro({ fiesta: b.fiesta, lugar: b.lugar }, estado.reglas);
        html += bloquePaso('¿Como acabo?', '<div class="opciones tres">' +
          R.RESULTADOS.map(function (res) {
            var tabla = estado.reglas.puntos[res.id];
            var pts = tabla ? (dentro ? tabla.dentro : tabla.fuera) : 0;
            return opcion(res.id, res.emoji, res.etiqueta, pts + ' pts');
          }).join('') + '</div>', 'resultado');
        $('#reg-pasos').innerHTML = html;
        conectarPasos();
        return pintarHistorialPropio();
      }
      html += resuelto('resultado', 'Resultado', etiquetaResultado(b.resultado).etiqueta);
    }

    // 5. Que se les ensena a los demas para que la voten (solo lio y mas lio)
    var provisional = entradaProvisional();
    if (R.admiteFoto(provisional) && estado.reglas.modoFoto !== 'ninguna') {
      if (estado.reglas.modoFoto === 'enlace') {
        var perfil = R.perfilInstagram(b.perfil);
        html += bloquePaso('Su Instagram, para que la voten (opcional)',
          '<div class="zona-foto">' +
          '<input type="text" id="reg-perfil" placeholder="@usuario" autocomplete="off" ' +
          'autocapitalize="off" spellcheck="false" value="' + esc(b.perfil || '') + '">' +
          (b.perfil && !perfil ? '<p class="ayuda" style="color:#ff8a8d">Eso no parece un usuario de Instagram.</p>' : '') +
          (perfil ? '<p class="ayuda">Se guardara <strong>@' + esc(perfil.usuario) + '</strong>. Al votar se abre su perfil; ' +
            'la app no guarda ninguna imagen.</p>'
            : '<p class="ayuda">Solo se guarda el usuario, no la foto. Sin esto la entrada cuenta igual, ' +
              'pero nadie podra ponerle nota.</p>') +
          '</div>', 'foto');
      } else {
        html += bloquePaso('Foto para que la voten (opcional)',
          '<div class="zona-foto">' +
          (b.foto ? '<img src="' + b.foto + '" alt="">' : '') +
          '<input type="file" id="reg-foto" accept="image/*" hidden>' +
          '<button class="btn btn-secundario" type="button" id="reg-foto-btn">' +
          (b.foto ? 'Cambiar foto' : 'Elegir foto') + '</button>' +
          (b.foto ? ' <button class="btn btn-secundario" type="button" id="reg-foto-quitar">Quitar</button>' : '') +
          '<p class="ayuda">Queda una copia guardada en este movil, reducida. Sin foto la entrada ' +
          'cuenta igual, pero nadie podra ponerle nota.</p>' +
          '</div>', 'foto');
      }
    }

    // 6. Resumen y guardar
    var puntos = R.puntosDeEntrada(provisional, estado.reglas);
    var yo = jugador(estado.yo);
    var resumenYo = yo ? E.resumenJugador(estado, yo) : null;
    var fueraDeLiga = resumenYo && resumenYo.entradas >= estado.reglas.limiteLiga;

    html += '<div class="resumen-puntos">' +
      '<div class="cifra">' + R.redondea(puntos) + ' pts</div>' +
      '<div class="detalle">' +
      (b.rechazo ? 'Rechazo' : etiquetaResultado(b.resultado).etiqueta) + ' · ' +
      (R.esDentro(provisional, estado.reglas) ? 'en discoteca' : 'fuera de discoteca') +
      '</div>' +
      (fueraDeLiga ? '<div class="detalle" style="color:#ff8a8d">Ya has llegado a ' +
        estado.reglas.limiteLiga + ': esta entrada se guarda pero no puntua en esta liga.</div>' : '') +
      '</div>';

    html += '<button class="btn btn-principal ancho" type="button" id="reg-guardar">Guardar entrada</button>';
    html += '<button class="btn ancho" type="button" id="reg-cancelar">Empezar de cero</button>';

    $('#reg-pasos').innerHTML = html;
    conectarPasos();
    pintarHistorialPropio();
  }

  /** Al cambiar un paso hay que olvidar los siguientes: si ya no es de fiesta,
   *  el sitio que habia elegido antes no vale. */
  function reiniciarDesde(campo) {
    var orden = ['rechazo', 'fiesta', 'lugar', 'resultado', 'foto'];
    var desde = orden.indexOf(campo);
    if (desde < 0) return;
    orden.slice(desde).forEach(function (c) { borrador[c] = null; });
    if (desde <= orden.indexOf('foto')) borrador.perfil = '';
  }

  function conectarPasos() {
    $$('#reg-pasos .opcion').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var campo = btn.closest('.paso').dataset.campo;
        var valor = btn.dataset.valor;
        if (campo === 'rechazo') {
          borrador.rechazo = valor === 'si';
          if (borrador.rechazo) borrador.resultado = 'nada';
        } else if (campo === 'fiesta') {
          borrador.fiesta = valor === 'si';
          if (!borrador.fiesta) borrador.lugar = null;
        } else if (campo === 'lugar') {
          borrador.lugar = valor;
        } else if (campo === 'resultado') {
          borrador.resultado = valor;
        }
        pintarRegistrar();
      });
    });

    $$('#reg-pasos .resuelto').forEach(function (btn) {
      btn.addEventListener('click', function () {
        reiniciarDesde(btn.dataset.cambiar);
        pintarRegistrar();
      });
    });

    var botonFoto = $('#reg-foto-btn');
    if (botonFoto) {
      botonFoto.addEventListener('click', function () { $('#reg-foto').click(); });
      $('#reg-foto').addEventListener('change', function (ev) {
        var file = ev.target.files && ev.target.files[0];
        if (!file) return;
        D.comprimirImagen(file, 640, 0.6, function (err, dataUrl) {
          if (err) { aviso('No se pudo procesar la foto'); return; }
          borrador.foto = dataUrl;
          pintarRegistrar();
        });
      });
    }
    var campoPerfil = $('#reg-perfil');
    if (campoPerfil) {
      // Solo se guarda al escribir; repintar en cada tecla robaria el foco.
      campoPerfil.addEventListener('input', function () { borrador.perfil = this.value; });
      campoPerfil.addEventListener('change', function () {
        borrador.perfil = this.value;
        pintarRegistrar();
      });
    }

    var quitarFoto = $('#reg-foto-quitar');
    if (quitarFoto) {
      quitarFoto.addEventListener('click', function () { borrador.foto = null; pintarRegistrar(); });
    }

    var guardar = $('#reg-guardar');
    if (guardar) guardar.addEventListener('click', guardarEntrada);

    var cancelar = $('#reg-cancelar');
    if (cancelar) cancelar.addEventListener('click', function () {
      borrador = nuevoBorrador();
      pintarRegistrar();
    });
  }

  function fechaCompleta(dia) {
    if (dia === hoyISO()) return new Date().toISOString();
    // Para dias pasados no sabemos la hora: las 22:00 es lo mas parecido a la verdad.
    return new Date(dia + 'T22:00:00').toISOString();
  }

  function guardarEntrada() {
    if (!estado.yo) { aviso('Elige primero quien eres'); return; }

    var entrada = {
      id: D.id(),
      jugadorId: estado.yo,
      fecha: fechaCompleta(borrador.fecha),
      rechazo: !!borrador.rechazo,
      fiesta: !!borrador.fiesta,
      lugar: borrador.fiesta ? borrador.lugar : null,
      resultado: borrador.rechazo ? 'nada' : borrador.resultado,
      tieneFoto: false,
      perfil: null
    };

    if (R.admiteFoto(entrada) && estado.reglas.modoFoto === 'enlace') {
      var perfil = R.perfilInstagram(borrador.perfil);
      if (perfil) entrada.perfil = perfil.usuario;
    }

    if (borrador.foto && R.admiteFoto(entrada) && estado.reglas.modoFoto === 'local') {
      var res = D.guardarFoto(entrada.id, borrador.foto);
      if (res.ok) {
        entrada.tieneFoto = true;
      } else {
        aviso('La entrada se guarda, pero la foto no cabe: memoria del navegador llena.');
      }
    }

    estado.entradas.push(entrada);
    persistir();

    var puntos = R.puntosDeEntrada(entrada, estado.reglas);
    borrador = nuevoBorrador();
    aviso('Apuntada. ' + R.redondea(puntos) + ' pts');
    pintar();
  }

  function pintarHistorialPropio() {
    var yo = jugador(estado.yo);
    if (!yo) return;
    var resumen = E.resumenJugador(estado, yo);
    $('#reg-contador').textContent = resumen.entradas + ' / ' + estado.reglas.limiteLiga +
      (resumen.extras ? ' (+' + resumen.extras + ')' : '');

    var todas = E.entradasDe(estado, yo.id);
    var limite = estado.reglas.limiteLiga;
    var ultimas = todas.slice().reverse().slice(0, 12);

    $('#reg-historial').innerHTML = ultimas.map(function (e) {
      var indice = todas.indexOf(e);
      var fuera = indice >= limite;
      var res = etiquetaResultado(e.resultado);
      var titulo = e.rechazo ? '❌ Rechazo' : res.emoji + ' ' + res.etiqueta;
      var sitio = e.fiesta
        ? (e.lugar === 'dj' ? 'DJ / sala' : 'Discoteca')
        : 'Fuera de fiesta';
      var nota = E.notaEntrada(estado, e);
      return '<li' + (fuera ? ' class="fuera-liga"' : '') + '>' +
        '<div class="info">' +
        '<div class="titulo">' + titulo + (e.tieneFoto ? ' 📷' : '') +
        (e.perfil ? ' <span class="apagado">@' + esc(e.perfil) + '</span>' : '') + '</div>' +
        '<div class="meta">' + fechaCorta(e.fecha) + ' · ' + sitio +
        (nota ? ' · nota ' + R.redondea(nota.nota) + ' (' + nota.votos + ')' : '') +
        (fuera ? ' · fuera de liga' : '') +
        '</div></div>' +
        '<div class="pts">' + (fuera ? '—' : R.redondea(R.puntosDeEntrada(e, estado.reglas))) + '</div>' +
        '<button class="borrar" data-borrar="' + e.id + '" type="button" aria-label="Borrar">🗑</button>' +
        '</li>';
    }).join('') || '<li class="vacio">Todavia no has apuntado nada</li>';

    $$('#reg-historial [data-borrar]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        if (!confirm('¿Borrar esta entrada?')) return;
        borrarEntrada(btn.dataset.borrar);
      });
    });
  }

  function borrarEntrada(id) {
    estado.entradas = estado.entradas.filter(function (e) { return e.id !== id; });
    delete estado.votos[id];
    D.borrarFoto(id);
    persistir();
    aviso('Entrada borrada');
    pintar();
  }

  // --- Clasificacion --------------------------------------------------------

  var EXPLICACIONES = {
    general: 'Mezcla de los tres ejes con los pesos de Ajustes. Toca un jugador para ver el desglose.',
    puntos: 'Suma de puntos de las entradas que cuentan para la liga.',
    ritmo: 'Quien llega antes a la cifra. Los que ya han terminado van primero, por fecha de llegada.',
    nota: 'Media de las notas que le han puesto los demas a sus fotos.'
  };

  function pintarClasificacion() {
    $('#clasificacion-explicacion').textContent = EXPLICACIONES[tablaActual];
    var tablas = E.clasificaciones(estado);
    var lista = tablas[tablaActual] || [];

    var columnas = {
      general: [{ t: 'Indice', f: function (r) { return r.indice; } },
                { t: 'Pts', f: function (r) { return r.puntos; } }],
      puntos: [{ t: 'Pts', f: function (r) { return r.puntos; }, destacado: true },
               { t: 'Entradas', f: function (r) { return r.entradas; } }],
      ritmo: [{ t: 'Entr./dia', f: function (r) { return r.ritmo; }, destacado: true },
              { t: 'Progreso', f: function (r) { return r.entradas + '/' + estado.reglas.limiteLiga; } }],
      nota: [{ t: 'Nota', f: function (r) { return r.nota === null ? '—' : r.nota; }, destacado: true },
             { t: 'Votadas', f: function (r) { return r.notasContadas; } }]
    }[tablaActual];

    var html = '<div class="tarjeta"><table class="tabla"><thead><tr><th class="pos"></th><th>Jugador</th>' +
      columnas.map(function (c) { return '<th class="num">' + c.t + '</th>'; }).join('') +
      '</tr></thead><tbody>';

    if (!lista.length) {
      html += '<tr><td colspan="4" class="vacio">Sin datos todavia</td></tr>';
    }

    lista.forEach(function (r, i) {
      html += '<tr class="fila-clic' + (r.jugador.id === estado.yo ? ' yo' : '') + '" data-jugador="' + r.jugador.id + '">' +
        '<td class="pos">' + (i + 1) + '</td>' +
        '<td><div class="jug">' + punto(r.jugador) + '<span>' + esc(r.jugador.nombre) +
        (r.completada ? ' 🏁' : '') + '</span></div>' +
        '<div class="barra"><i style="width:' + Math.min(100, r.progreso * 100) + '%;background:' + esc(r.jugador.color) + '"></i></div></td>' +
        columnas.map(function (c) {
          return '<td class="num' + (c.destacado ? ' destacado' : '') + '">' + esc(c.f(r)) + '</td>';
        }).join('') +
        '</tr>';
    });

    html += '</tbody></table></div>';

    var liga = E.estadoLiga(estado);
    if (liga.terminada && liga.campeon) {
      html = '<div class="podio"><div class="corona">🏆</div>' +
        '<div class="nombre">' + esc(liga.campeon.jugador.nombre) + '</div>' +
        '<div class="detalle">Campeon de ' + esc(estado.liga.nombre) + ' · indice ' + liga.campeon.indice + '</div></div>' + html;
    }

    $('#clasificacion-tabla').innerHTML = html;

    $$('#clasificacion-tabla [data-jugador]').forEach(function (fila) {
      fila.addEventListener('click', function () { abrirDetalleJugador(fila.dataset.jugador); });
    });
  }

  function abrirDetalleJugador(id) {
    var j = jugador(id);
    if (!j) return;
    var r = E.resumenJugador(estado, j);
    var general = E.clasificacionGeneral(estado);
    var conIndice = general.filter(function (x) { return x.jugador.id === id; })[0] || r;

    function caja(k, v) {
      return '<div class="detalle-caja"><div class="k">' + esc(k) + '</div><div class="v">' + esc(v) + '</div></div>';
    }

    var html = '<h2>' + punto(j) + ' ' + esc(j.nombre) + '</h2>' +
      '<div class="detalle-grid">' +
      caja('Puntos', r.puntos) +
      caja('Entradas', r.entradas + '/' + estado.reglas.limiteLiga) +
      caja('Nota media', r.nota === null ? '—' : r.nota) +
      caja('Entradas/dia', r.ritmo) +
      caja('Rechazos', r.rechazos) +
      caja('Efectividad', r.efectividad + '%') +
      '</div>' +
      '<table class="tabla"><tbody>' +
      R.RESULTADOS.map(function (res) {
        return '<tr><td>' + res.emoji + ' ' + esc(res.etiqueta) + '</td><td class="num">' +
          (r.porResultado[res.id] || 0) + '</td></tr>';
      }).join('') +
      '<tr><td>🪩 En discoteca</td><td class="num">' + r.dentro + '</td></tr>' +
      '<tr><td>🌙 Fuera de discoteca</td><td class="num">' + r.fuera + '</td></tr>' +
      (r.extras ? '<tr><td>Fuera de liga (pasadas de ' + estado.reglas.limiteLiga + ')</td><td class="num">' + r.extras + '</td></tr>' : '') +
      '</tbody></table>' +
      '<p class="ayuda">Indice general ' + (conIndice.indice !== undefined ? conIndice.indice : '—') +
      (conIndice.ejes ? ' · puntos ' + conIndice.ejes.puntos + ' / ritmo ' + conIndice.ejes.ritmo + ' / nota ' + conIndice.ejes.nota : '') + '</p>' +
      (r.completada
        ? '<p class="ayuda">Llego a ' + estado.reglas.limiteLiga + ' el ' + esc(fechaLarga(r.fechaFinal)) + '.</p>'
        : (r.diasRestantes !== null
          ? '<p class="ayuda">A este ritmo llegaria a ' + estado.reglas.limiteLiga + ' en ' + r.diasRestantes + ' dias.</p>'
          : ''));

    abrirModal(html);
  }

  // --- Votar ----------------------------------------------------------------

  function pintarVotar() {
    if (!estado.yo) return;
    var pendientes = E.pendientesDeVotar(estado, estado.yo);

    $('#votar-pendientes').innerHTML = pendientes.length
      ? pendientes.map(tarjetaVoto).join('')
      : '<div class="tarjeta"><div class="vacio">Nada pendiente de votar</div></div>';

    $$('#votar-pendientes .nota-btn').forEach(function (btn) {
      btn.addEventListener('click', function () {
        votar(btn.dataset.entrada, Number(btn.dataset.nota));
      });
    });

    var votadas = estado.entradas.filter(function (e) {
      var v = estado.votos[e.id] || {};
      return v[estado.yo] !== undefined;
    }).sort(function (a, b) { return new Date(b.fecha) - new Date(a.fecha); });

    $('#votar-hechas').innerHTML = votadas.length
      ? '<ul class="lista-entradas">' + votadas.map(function (e) {
        var mio = estado.votos[e.id][estado.yo];
        var consenso = E.notaEntrada(estado, e);
        var foto = e.tieneFoto ? D.leerFoto(e.id) : null;
        var perfil = e.perfil ? R.perfilInstagram(e.perfil) : null;
        return '<li>' +
          (foto ? '<img class="mini-foto" src="' + foto + '" alt="">' : '') +
          '<div class="info"><div class="titulo">' + esc(nombreDe(e.jugadorId)) +
          (perfil ? ' <a href="' + esc(perfil.url) + '" target="_blank" rel="noopener noreferrer">@' +
            esc(perfil.usuario) + '</a>' : '') + '</div>' +
          '<div class="meta">' + fechaCorta(e.fecha) + ' · tu nota ' + mio +
          (consenso ? ' · consenso ' + R.redondea(consenso.nota) + ' (' + consenso.votos + ' votos)' : '') +
          '</div></div>' +
          '<button class="borrar" data-desvotar="' + e.id + '" type="button">↺</button>' +
          '</li>';
      }).join('') + '</ul>'
      : '<div class="vacio">Todavia no has votado nada</div>';

    $$('#votar-hechas [data-desvotar]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var id = btn.dataset.desvotar;
        if (estado.votos[id]) delete estado.votos[id][estado.yo];
        persistir();
        pintar();
      });
    });
  }

  function tarjetaVoto(e) {
    var foto = e.tieneFoto ? D.leerFoto(e.id) : null;
    var perfil = e.perfil ? R.perfilInstagram(e.perfil) : null;
    var res = etiquetaResultado(e.resultado);
    var sitio = e.fiesta ? (e.lugar === 'dj' ? 'DJ / sala' : 'Discoteca') : 'Fuera de fiesta';
    var notas = '';
    for (var n = 1; n <= 10; n++) {
      notas += '<button class="nota-btn" type="button" data-entrada="' + e.id + '" data-nota="' + n + '">' + n + '</button>';
    }

    var cabecera;
    if (foto) {
      cabecera = '<img src="' + foto + '" alt="Foto subida por ' + esc(nombreDe(e.jugadorId)) + '">';
    } else if (perfil) {
      cabecera = '<a class="btn btn-secundario ancho enlace-perfil" target="_blank" rel="noopener noreferrer" ' +
        'href="' + esc(perfil.url) + '">📷 Abrir @' + esc(perfil.usuario) + ' en Instagram</a>';
    } else {
      cabecera = '<div class="vacio">Esta entrada no tiene nada que ver</div>';
    }

    return '<div class="voto-tarjeta">' + cabecera +
      '<div class="fila-cabecera"><h3>' + esc(nombreDe(e.jugadorId)) + ' · ' + res.emoji + ' ' + esc(res.etiqueta) + '</h3>' +
      '<span class="contador">' + fechaCorta(e.fecha) + '</span></div>' +
      '<div class="meta apagado">' + sitio + '</div>' +
      '<div class="notas">' + notas + '</div>' +
      '</div>';
  }

  function votar(entradaId, nota) {
    if (!estado.votos[entradaId]) estado.votos[entradaId] = {};
    estado.votos[entradaId][estado.yo] = nota;
    persistir();
    aviso('Votado: ' + nota);
    pintar();
  }

  // --- Campeones ------------------------------------------------------------

  function etiquetaPeriodo(periodo, clave) {
    if (periodo === 'dia') {
      var d = new Date(clave + 'T12:00:00');
      return d.toLocaleDateString('es-ES', { weekday: 'long', day: 'numeric', month: 'short' });
    }
    if (periodo === 'semana') {
      var ini = new Date(clave.slice(1) + 'T12:00:00');
      var fin = new Date(ini.getTime() + 6 * 86400000);
      return 'Semana ' + ini.getDate() + '/' + (ini.getMonth() + 1) + ' – ' + fin.getDate() + '/' + (fin.getMonth() + 1);
    }
    var m = new Date(clave + '-01T12:00:00');
    return m.toLocaleDateString('es-ES', { month: 'long', year: 'numeric' });
  }

  function pintarCampeones() {
    var actual = E.campeonDe(estado, periodoActual, new Date());
    var titulo = { dia: 'Campeon de hoy', semana: 'Campeon de esta semana', mes: 'Campeon de este mes' }[periodoActual];

    if (actual.campeon) {
      $('#campeon-actual').innerHTML = '<div class="podio">' +
        '<div class="corona">👑</div>' +
        '<div class="nombre">' + esc(actual.campeon.jugador.nombre) + '</div>' +
        '<div class="detalle">' + esc(titulo) + ' · ' + actual.campeon.puntos + ' pts · ' +
        actual.campeon.entradas + ' entradas' +
        (actual.campeon.nota !== null ? ' · nota ' + actual.campeon.nota : '') + '</div>' +
        '</div>' +
        '<div class="tarjeta"><h2>Ahora mismo</h2><table class="tabla"><tbody>' +
        actual.tabla.map(function (a, i) {
          return '<tr' + (a.jugador.id === estado.yo ? ' class="yo"' : '') + '><td class="pos">' + (i + 1) + '</td>' +
            '<td><div class="jug">' + punto(a.jugador) + esc(a.jugador.nombre) + '</div></td>' +
            '<td class="num destacado">' + a.puntos + '</td>' +
            '<td class="num">' + a.entradas + '</td></tr>';
        }).join('') + '</tbody></table></div>';
    } else {
      $('#campeon-actual').innerHTML = '<div class="tarjeta"><div class="vacio">' +
        'Sin entradas en este periodo todavia. El titulo esta libre.</div></div>';
    }

    var historial = E.historialCampeones(estado, periodoActual, 12);
    $('#campeones-historial').innerHTML = historial.length
      ? historial.map(function (h) {
        if (!h.campeon) return '';
        return '<div class="periodo-bloque">' +
          '<div class="fecha">' + esc(etiquetaPeriodo(h.periodo, h.clave)) + '</div>' +
          '<div class="linea">' + punto(h.campeon.jugador) + '<strong>' + esc(h.campeon.jugador.nombre) + '</strong>' +
          '<span class="apagado">' + h.campeon.puntos + ' pts · ' + h.campeon.entradas + ' entradas</span></div>' +
          '</div>';
      }).join('')
      : '<div class="vacio">Sin historial todavia</div>';
  }

  // --- Ajustes --------------------------------------------------------------

  function pintarAjustes() {
    $('#aj-nombre-liga').value = estado.liga.nombre || '';
    $('#aj-limite').value = estado.reglas.limiteLiga;
    $('#aj-dj').checked = !!estado.reglas.djCuentaComoDiscoteca;
    $('#aj-peso-puntos').value = estado.reglas.pesos.puntos;
    $('#aj-peso-ritmo').value = estado.reglas.pesos.ritmo;
    $('#aj-peso-nota').value = estado.reglas.pesos.nota;
    $('#aj-votos-min').value = estado.reglas.votosMinimos;

    $('#aj-jugadores').innerHTML = estado.jugadores.map(function (j) {
      var r = E.resumenJugador(estado, j);
      return '<li>' + punto(j) +
        '<span class="nombre">' + esc(j.nombre) +
        (j.id === estado.yo ? ' <span class="apagado">(tu)</span>' : '') +
        '<br><span class="apagado" style="font-size:.76rem">' + r.entradas + ' entradas · ' + r.puntos + ' pts</span></span>' +
        '<button data-renombrar="' + j.id + '" type="button">Renombrar</button>' +
        '<button data-eliminar="' + j.id + '" type="button">Eliminar</button>' +
        '</li>';
    }).join('') || '<li class="vacio">Sin jugadores</li>';

    $('#aj-modo-foto').innerHTML = R.MODOS_FOTO.map(function (m) {
      return '<label class="opcion-lista' + (estado.reglas.modoFoto === m.id ? ' elegida' : '') + '">' +
        '<input type="radio" name="modo-foto" value="' + m.id + '"' +
        (estado.reglas.modoFoto === m.id ? ' checked' : '') + '>' +
        '<span><strong>' + esc(m.etiqueta) + '</strong><br>' +
        '<span class="ayuda">' + esc(m.detalle) + '</span></span></label>';
    }).join('');

    var conFotos = estado.entradas.filter(function (e) { return e.tieneFoto; }).length;
    $('#aj-borrar-fotos').disabled = conFotos === 0;
    $('#aj-borrar-fotos').textContent = conFotos
      ? 'Borrar las ' + conFotos + ' fotos guardadas (los puntos y las notas se quedan)'
      : 'No hay ninguna foto guardada en este dispositivo';

    $('#aj-tabla-puntos').innerHTML = R.RESULTADOS.map(function (res) {
      var p = estado.reglas.puntos[res.id] || { dentro: 0, fuera: 0 };
      return '<tr><td>' + res.emoji + ' ' + esc(res.etiqueta) + '</td>' +
        '<td class="num"><input type="number" step="0.5" data-punto="' + res.id + '" data-donde="dentro" value="' + p.dentro + '"></td>' +
        '<td class="num"><input type="number" step="0.5" data-punto="' + res.id + '" data-donde="fuera" value="' + p.fuera + '"></td></tr>';
    }).join('');

    var kb = Math.round(D.espacioUsado() / 1024);
    $('#aj-espacio').textContent = 'Ocupado ahora mismo: ' + (kb > 1024 ? (kb / 1024).toFixed(1) + ' MB' : kb + ' KB') +
      '. El navegador suele dejar unos 5 MB.';

    conectarAjustesDinamicos();
  }

  function conectarAjustesDinamicos() {
    $$('#aj-jugadores [data-renombrar]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var j = jugador(btn.dataset.renombrar);
        var nuevo = prompt('Nuevo nombre', j.nombre);
        if (!nuevo || !nuevo.trim()) return;
        j.nombre = nuevo.trim();
        persistir();
        pintar();
      });
    });

    $$('#aj-jugadores [data-eliminar]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var id = btn.dataset.eliminar;
        var j = jugador(id);
        var suyas = E.entradasDe(estado, id).length;
        if (!confirm('Eliminar a ' + j.nombre + ' y sus ' + suyas + ' entradas. ¿Seguro?')) return;
        E.entradasDe(estado, id).forEach(function (e) {
          D.borrarFoto(e.id);
          delete estado.votos[e.id];
        });
        estado.entradas = estado.entradas.filter(function (e) { return e.jugadorId !== id; });
        Object.keys(estado.votos).forEach(function (k) { delete estado.votos[k][id]; });
        estado.jugadores = estado.jugadores.filter(function (x) { return x.id !== id; });
        if (estado.yo === id) estado.yo = estado.jugadores.length ? estado.jugadores[0].id : null;
        persistir();
        pintar();
      });
    });

    $$('#aj-modo-foto input').forEach(function (radio) {
      radio.addEventListener('change', function () {
        if (!radio.checked) return;
        estado.reglas.modoFoto = radio.value;
        borrador = nuevoBorrador();
        persistir();
        pintarAjustes();
        aviso(radio.value === 'enlace' ? 'Se guardara solo el @usuario'
          : radio.value === 'local' ? 'Se guardaran copias de las fotos en este movil'
          : 'Sin fotos ni enlaces');
      });
    });

    $$('#aj-tabla-puntos input').forEach(function (input) {
      input.addEventListener('change', function () {
        var valor = Number(input.value);
        if (isNaN(valor)) return;
        estado.reglas.puntos[input.dataset.punto][input.dataset.donde] = valor;
        persistir();
        aviso('Puntuacion actualizada');
      });
    });
  }

  function conectarAjustes() {
    $('#aj-nombre-liga').addEventListener('change', function () {
      estado.liga.nombre = this.value.trim() || 'La Liga';
      persistir();
      pintarCabecera();
    });

    $('#aj-limite').addEventListener('change', function () {
      var v = Math.max(1, Math.round(Number(this.value) || 100));
      estado.reglas.limiteLiga = v;
      this.value = v;
      persistir();
      pintarCabecera();
      aviso('Liga a ' + v + ' mujeres');
    });

    $('#aj-dj').addEventListener('change', function () {
      estado.reglas.djCuentaComoDiscoteca = this.checked;
      persistir();
      aviso(this.checked ? 'El DJ cuenta como discoteca' : 'El DJ ya no cuenta como discoteca');
    });

    [['#aj-peso-puntos', 'puntos'], ['#aj-peso-ritmo', 'ritmo'], ['#aj-peso-nota', 'nota']].forEach(function (par) {
      $(par[0]).addEventListener('change', function () {
        estado.reglas.pesos[par[1]] = Math.max(0, Number(this.value) || 0);
        persistir();
      });
    });

    $('#aj-votos-min').addEventListener('change', function () {
      estado.reglas.votosMinimos = Math.max(1, Math.round(Number(this.value) || 1));
      this.value = estado.reglas.votosMinimos;
      persistir();
    });

    $('#aj-añadir-jugador').addEventListener('click', añadirJugador);
    $('#aj-nuevo-jugador').addEventListener('keydown', function (ev) {
      if (ev.key === 'Enter') { ev.preventDefault(); añadirJugador(); }
    });

    $('#aj-exportar').addEventListener('click', function () { descargar(false); });
    $('#aj-exportar-fotos').addEventListener('click', function () {
      if (!confirm('El archivo llevara dentro las fotos guardadas. Una vez lo mandes ' +
        'dejas de controlar donde acaba. ¿Seguro?')) return;
      descargar(true);
    });

    var modoImportacion = 'fusionar';
    $('#aj-importar-fusion').addEventListener('click', function () {
      modoImportacion = 'fusionar';
      $('#aj-archivo').click();
    });
    $('#aj-importar-reemplazo').addEventListener('click', function () {
      if (!confirm('Esto borra la liga de este dispositivo y pone la del archivo. ¿Seguro?')) return;
      modoImportacion = 'reemplazar';
      $('#aj-archivo').click();
    });

    $('#aj-archivo').addEventListener('change', function (ev) {
      var file = ev.target.files && ev.target.files[0];
      ev.target.value = '';
      if (!file) return;
      var lector = new FileReader();
      lector.onload = function () {
        try {
          var datos = JSON.parse(lector.result);
          var res = D.importar(estado, datos, modoImportacion);
          estado = res.estado;
          persistir();
          aviso(res.fotosFallidas
            ? 'Importado, pero ' + res.fotosFallidas + ' fotos no cupieron'
            : 'Liga importada');
          pintar();
        } catch (err) {
          aviso('Archivo no valido: ' + err.message);
        }
      };
      lector.readAsText(file);
    });

    $('#aj-borrar-fotos').addEventListener('click', function () {
      if (!confirm('Se borran las imagenes guardadas en este movil. Las entradas, los ' +
        'puntos y las notas ya puestas se quedan. ¿Seguro?')) return;
      var borradas = D.borrarTodasLasFotos(estado);
      persistir();
      aviso(borradas + ' fotos borradas de este dispositivo');
      pintar();
    });

    $('#aj-borrar').addEventListener('click', function () {
      if (!confirm('Se borra TODO: jugadores, entradas, fotos y votos. ¿Seguro?')) return;
      if (!confirm('Ultima oportunidad. ¿Exportaste antes? Esto no se puede deshacer.')) return;
      D.borrarTodo();
      estado = D.estadoInicial();
      jugadoresIniciales = [];
      aviso('Liga borrada');
      pintar();
    });
  }

  function añadirJugador() {
    var input = $('#aj-nuevo-jugador');
    var nombre = input.value.trim();
    if (!nombre) return;
    estado.jugadores.push({
      id: D.id(),
      nombre: nombre,
      color: D.COLORES[estado.jugadores.length % D.COLORES.length],
      creado: new Date().toISOString()
    });
    if (!estado.yo) estado.yo = estado.jugadores[0].id;
    input.value = '';
    persistir();
    pintar();
  }

  function descargar(conFotos) {
    var datos = D.exportar(estado, conFotos);
    var blob = new Blob([JSON.stringify(datos)], { type: 'application/json' });
    var url = URL.createObjectURL(blob);
    var a = document.createElement('a');
    a.href = url;
    a.download = 'liga-' + hoyISO() + (conFotos ? '-con-fotos' : '') + '.json';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
    aviso('Copia descargada');
  }

  // --- Selector de jugador --------------------------------------------------

  function abrirSelectorJugador() {
    var html = '<h2>¿Quien esta usando la app?</h2>' +
      '<p class="ayuda">Lo que registres se apunta a este jugador. Si pasais el movil, cambiadlo aqui.</p>' +
      '<ul class="lista-jugadores">' +
      estado.jugadores.map(function (j) {
        return '<li>' + punto(j) + '<span class="nombre">' + esc(j.nombre) + '</span>' +
          '<button data-soy="' + j.id + '" type="button">' +
          (j.id === estado.yo ? 'Actual' : 'Soy yo') + '</button></li>';
      }).join('') + '</ul>';
    abrirModal(html);
    $$('#modal-contenido [data-soy]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        estado.yo = btn.dataset.soy;
        borrador = nuevoBorrador();
        persistir();
        cerrarModal();
        pintar();
      });
    });
  }

  // --- Arranque -------------------------------------------------------------

  function conectar() {
    conectarInicio();
    conectarAjustes();

    $$('.nav-btn').forEach(function (b) {
      b.addEventListener('click', function () { irA(b.dataset.vista); });
    });

    $('#btn-yo').addEventListener('click', abrirSelectorJugador);
    $('#modal-cerrar').addEventListener('click', cerrarModal);
    $('#modal').addEventListener('click', function (ev) {
      if (ev.target === $('#modal')) cerrarModal();
    });

    $('#tabs-clasificacion').addEventListener('click', function (ev) {
      var tab = ev.target.closest('.tab');
      if (!tab) return;
      tablaActual = tab.dataset.tabla;
      $$('#tabs-clasificacion .tab').forEach(function (t) { t.classList.toggle('activo', t === tab); });
      pintarClasificacion();
    });

    $('#tabs-campeones').addEventListener('click', function (ev) {
      var tab = ev.target.closest('.tab');
      if (!tab) return;
      periodoActual = tab.dataset.periodo;
      $$('#tabs-campeones .tab').forEach(function (t) { t.classList.toggle('activo', t === tab); });
      pintarCampeones();
    });

    $('#reg-fecha').addEventListener('change', function () {
      borrador.fecha = this.value || hoyISO();
    });

    // Si abren la app en otra pestana y registran algo, que esta se entere.
    window.addEventListener('storage', function (ev) {
      if (ev.key !== D.CLAVE) return;
      estado = D.cargar();
      pintar();
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    $('#reg-fecha').value = hoyISO();
    conectar();
    pintar();

    if (!D.guardadoPermanente()) {
      var banda = $('#aviso-temporal');
      banda.innerHTML = '⚠️ <strong>Aqui no se guarda nada al cerrar.</strong> Este navegador ' +
        'no deja guardar datos (navegacion privada, cookies bloqueadas o la app abierta dentro ' +
        'de otra pagina). Puedes trastear todo lo que quieras, pero al cerrar la pestana se ' +
        'pierde. Para usarla de verdad, abrela como app en el movil.';
      banda.hidden = false;
    }

    // Solo en la version de varios archivos: la de archivo unico no lleva
    // manifiesto ni sw.js al lado, y pedirlos daria un 404 en la consola.
    var esInstalable = !!document.querySelector('link[rel="manifest"]');
    if (esInstalable && 'serviceWorker' in navigator && location.protocol.indexOf('http') === 0) {
      navigator.serviceWorker.register('sw.js').catch(function () { /* sin modo offline, no pasa nada */ });
    }
  });
})();
