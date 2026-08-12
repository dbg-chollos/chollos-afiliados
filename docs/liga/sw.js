/*
 * sw.js — cache para que la app abra sin cobertura (en la calle a las 4 de la
 * manana el 4G va regular). Los datos ya viven en el navegador, esto solo
 * guarda los archivos de la app.
 */
var CACHE = 'liga-v1';
var ARCHIVOS = [
  './',
  './index.html',
  './css/app.css',
  './js/reglas.js',
  './js/datos.js',
  './js/estadisticas.js',
  './js/app.js',
  './icono.svg',
  './manifest.webmanifest'
];

self.addEventListener('install', function (ev) {
  ev.waitUntil(caches.open(CACHE).then(function (c) { return c.addAll(ARCHIVOS); }));
  self.skipWaiting();
});

self.addEventListener('activate', function (ev) {
  ev.waitUntil(
    caches.keys().then(function (claves) {
      return Promise.all(claves.map(function (k) {
        return k === CACHE ? null : caches.delete(k);
      }));
    })
  );
  self.clients.claim();
});

self.addEventListener('fetch', function (ev) {
  if (ev.request.method !== 'GET') return;
  ev.respondWith(
    // Red primero para no quedarnos con una version vieja tras actualizar,
    // y cache como red de seguridad si no hay internet.
    fetch(ev.request)
      .then(function (respuesta) {
        var copia = respuesta.clone();
        caches.open(CACHE).then(function (c) { c.put(ev.request, copia); });
        return respuesta;
      })
      .catch(function () { return caches.match(ev.request); })
  );
});
