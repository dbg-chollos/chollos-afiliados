/*
 * Un Supabase de mentira: implementa solo lo que usa la app, con las mismas
 * rutas y las mismas formas de respuesta. Sirve para probar el flujo entero
 * (registrarse, crear liga, unirse, sincronizar, votar) sin tocar el servidor
 * de verdad.
 */
const http = require('http');

const usuarios = new Map();   // email -> {id, email, password}
const sesiones = new Map();   // token -> userId
const refrescos = new Map();  // refresh_token -> userId
const ligas = [];             // {id, nombre, codigo, reglas, creada_por}
const miembros = [];          // {liga_id, usuario, nombre, color, unido}
const entradas = new Map();   // id -> fila
const votos = new Map();      // entrada_id|usuario -> fila
const fotos = new Map();      // ruta -> buffer

let n = 0;
const uuid = () => 'u' + (++n).toString().padStart(8, '0') + '-0000-0000-0000-000000000000';

function leerCuerpo(req) {
  return new Promise((resolve) => {
    const trozos = [];
    req.on('data', (d) => trozos.push(d));
    req.on('end', () => resolve(Buffer.concat(trozos)));
  });
}

function json(res, codigo, cuerpo) {
  const texto = cuerpo === null ? '' : JSON.stringify(cuerpo);
  res.writeHead(codigo, { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' });
  res.end(texto);
}

function usuarioDe(req) {
  const auth = req.headers.authorization || '';
  const token = auth.replace('Bearer ', '');
  return sesiones.get(token) || null;
}

function sesionPara(u) {
  const token = 'tok_' + Math.random().toString(36).slice(2);
  const refresco = 'ref_' + Math.random().toString(36).slice(2);
  sesiones.set(token, u.id);
  refrescos.set(refresco, u.id);
  return {
    access_token: token,
    refresh_token: refresco,
    expires_in: 3600,
    user: { id: u.id, email: u.email }
  };
}

const servidor = http.createServer(async (req, res) => {
  const url = new URL(req.url, 'http://x');
  const ruta = url.pathname;
  const cuerpoCrudo = await leerCuerpo(req);
  const cuerpo = (() => { try { return JSON.parse(cuerpoCrudo.toString()); } catch { return null; } })();

  if (req.method === 'OPTIONS') {
    res.writeHead(204, {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Headers': '*',
      'Access-Control-Allow-Methods': '*'
    });
    return res.end();
  }

  // --- Auth ---
  if (ruta === '/auth/v1/signup') {
    if (usuarios.has(cuerpo.email)) return json(res, 400, { message: 'User already registered' });
    if (String(cuerpo.password).length < 6) return json(res, 422, { message: 'Password should be at least 6 characters' });
    const u = { id: uuid(), email: cuerpo.email, password: cuerpo.password };
    usuarios.set(u.email, u);
    return json(res, 200, sesionPara(u));
  }

  if (ruta === '/auth/v1/token') {
    if (url.searchParams.get('grant_type') === 'refresh_token') {
      const id = refrescos.get(cuerpo.refresh_token);
      if (!id) return json(res, 400, { message: 'Invalid Refresh Token' });
      refrescos.delete(cuerpo.refresh_token); // de un solo uso, como el de verdad
      const u = [...usuarios.values()].find((x) => x.id === id);
      return json(res, 200, sesionPara(u));
    }
    const u = usuarios.get(cuerpo.email);
    if (!u || u.password !== cuerpo.password) {
      return json(res, 400, { error_description: 'Invalid login credentials' });
    }
    return json(res, 200, sesionPara(u));
  }

  if (ruta === '/auth/v1/logout') return json(res, 204, null);

  const yo = usuarioDe(req);
  if (!yo) return json(res, 401, { message: 'No autorizado' });

  const esMiembro = (ligaId) => miembros.some((m) => m.liga_id === ligaId && m.usuario === yo);

  // --- RPC ---
  if (ruta === '/rest/v1/rpc/crear_liga') {
    const liga = {
      id: uuid(), nombre: cuerpo.p_nombre, codigo: cuerpo.p_codigo.toUpperCase(),
      reglas: cuerpo.p_reglas || {}, creada_por: yo
    };
    ligas.push(liga);
    miembros.push({ liga_id: liga.id, usuario: yo, nombre: cuerpo.p_jugador, color: cuerpo.p_color, unido: new Date().toISOString() });
    return json(res, 200, liga);
  }

  if (ruta === '/rest/v1/rpc/unirse_a_liga') {
    const liga = ligas.find((l) => l.codigo === String(cuerpo.p_codigo).trim().toUpperCase());
    if (!liga) return json(res, 400, { message: 'No hay ninguna liga con ese codigo' });
    if (!esMiembro(liga.id)) {
      miembros.push({ liga_id: liga.id, usuario: yo, nombre: cuerpo.p_jugador, color: cuerpo.p_color, unido: new Date().toISOString() });
    }
    return json(res, 200, liga);
  }

  // --- Tablas ---
  if (ruta === '/rest/v1/miembros') {
    const ligaId = (url.searchParams.get('liga_id') || '').replace('eq.', '');
    if (!esMiembro(ligaId)) return json(res, 200, []);
    return json(res, 200, miembros.filter((m) => m.liga_id === ligaId));
  }

  if (ruta === '/rest/v1/entradas') {
    if (req.method === 'POST') {
      const filas = Array.isArray(cuerpo) ? cuerpo : [cuerpo];
      for (const f of filas) {
        if (f.usuario !== yo) return json(res, 403, { message: 'No puedes escribir por otro' });
        if (!esMiembro(f.liga_id)) return json(res, 403, { message: 'No eres miembro' });
        entradas.set(f.id, f);
      }
      return json(res, 201, null);
    }
    if (req.method === 'DELETE') return json(res, 204, null);
    const ligaId = (url.searchParams.get('liga_id') || '').replace('eq.', '');
    if (!esMiembro(ligaId)) return json(res, 200, []);
    return json(res, 200, [...entradas.values()].filter((e) => e.liga_id === ligaId));
  }

  if (ruta === '/rest/v1/votos') {
    if (req.method === 'POST') {
      const filas = Array.isArray(cuerpo) ? cuerpo : [cuerpo];
      for (const f of filas) {
        if (f.usuario !== yo) return json(res, 403, { message: 'No puedes votar por otro' });
        const entrada = entradas.get(f.entrada_id);
        if (!entrada) return json(res, 400, { message: 'Esa entrada no existe' });
        if (entrada.usuario === yo) return json(res, 403, { message: 'No puedes votarte a ti mismo' });
        votos.set(f.entrada_id + '|' + f.usuario, f);
      }
      return json(res, 201, null);
    }
    const filtro = url.searchParams.get('entradas.liga_id') || '';
    const ligaId = filtro.replace('eq.', '');
    const salida = [...votos.values()].filter((v) => {
      const e = entradas.get(v.entrada_id);
      return e && e.liga_id === ligaId && esMiembro(ligaId);
    });
    return json(res, 200, salida);
  }

  if (ruta === '/rest/v1/ligas') {
    if (req.method === 'PATCH') return json(res, 204, null);
    return json(res, 200, ligas.filter((l) => esMiembro(l.id)));
  }

  // --- Fotos ---
  if (ruta.startsWith('/storage/v1/object/')) {
    const ruta2 = ruta.replace('/storage/v1/object/authenticated/fotos/', '').replace('/storage/v1/object/fotos/', '');
    if (req.method === 'POST') {
      fotos.set(ruta2, cuerpoCrudo);
      return json(res, 200, { Key: ruta2 });
    }
    const dato = fotos.get(ruta2);
    if (!dato) return json(res, 404, { message: 'No existe' });
    res.writeHead(200, { 'Content-Type': 'image/jpeg', 'Access-Control-Allow-Origin': '*' });
    return res.end(dato);
  }

  return json(res, 404, { message: 'Ruta no implementada: ' + ruta });
});

servidor.listen(8910, () => console.log('Supabase de mentira en http://localhost:8910'));
