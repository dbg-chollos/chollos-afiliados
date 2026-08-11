# La Liga — app privada de la liga de ligues

App para llevar la cuenta entre vosotros: cada entrada que haces, cómo acaba,
cuántos puntos vale, quién va ganando, y campeón del día / de la semana / del mes.

No hay servidor, no hay cuentas y no se sube nada a internet: **todo se guarda
en el navegador del móvil que la usa**. Coste 0€, igual que el resto del repo.

---

## Cómo abrirla

**Opción rápida (probarla en el ordenador):** doble clic en `liga/index.html`.
Funciona todo menos instalarla como app.

**Opción buena (usarla en el móvil):**

```bash
python scripts/servir_liga.py
```

Te imprime dos direcciones. Abre desde el móvil la que empieza por `192.168…`
(tenéis que estar en el mismo wifi), y en el navegador: menú → *Añadir a
pantalla de inicio*. A partir de ahí se abre como una app normal, con su icono,
a pantalla completa y sin necesitar cobertura.

> Ojo: si la abres con el ordenador apagado no funcionará, porque la sirve tu
> ordenador. Para tenerla siempre disponible en el móvil hace falta subirla a
> algún hosting — está explicado abajo, en "Lo que falta".

---

## Cómo se registra una entrada

Cuatro toques, en este orden. Cada paso se queda resumido arriba y se puede
cambiar tocándolo.

1. **¿Te ha rechazado?** → Sí / No
2. **¿Fue de fiesta?** → De fiesta / Fuera de fiesta
3. **Si fue de fiesta, ¿dónde?** → Discoteca / DJ · sala
4. **Si no te rechazó, ¿cómo acabó?** → Más lío / Lío / Pico / Amigos / Nada
5. **Si acabó en lío o más lío**, puedes añadir su Instagram para que la voten
   los demás (ver abajo)

Arriba se puede cambiar la fecha, por si apuntas al día siguiente lo de anoche.

---

## Puntos

| Resultado | En discoteca | Fuera de discoteca |
|---|---:|---:|
| 🔥 Más lío | 5 | 10 |
| 💋 Lío | 2 | 3 |
| 😙 Pico | 1 | 2 |
| 🤝 Amigos | 0,5 | 1 |
| 🚪 Nada / ❌ Rechazo | 0 | 0 |

Dos cosas que tú no llegaste a decidir y he tenido que rellenar yo. **Las dos se
cambian en Ajustes sin tocar código**, así que decididlas entre vosotros:

- **El "pico" no lo puntuaste.** Lo he puesto entre "lío" y "amigos": 2 fuera y
  1 dentro. Queda una escalera limpia 10 / 3 / 2 / 1 fuera y 5 / 2 / 1 / 0,5 dentro.
- **"DJ · sala" cuenta como discoteca** por defecto (o sea, puntúa como "dentro").
  Si para vosotros una sala con DJ es tan difícil como la calle, desactivad la
  casilla en Ajustes y pasará a puntuar como "fuera".

Un rechazo nunca puntúa, pero **sí cuenta** para el contador de 100: es parte
del mérito llegar antes.

---

## Las clasificaciones

La app calcula cuatro tablas:

- **Puntos** — la suma de todo lo anterior.
- **Ritmo** — entradas por día. Quien ya ha llegado a 100 aparece siempre por
  delante de quien no, ordenados por fecha de llegada: gana quien llegó antes.
  A quien va por el camino le muestra cuántos días le quedarían a ese ritmo.
- **Nota** — media de lo que los demás han puntuado a sus fotos (del 1 al 10).
  Nadie se vota a sí mismo y el propio voto nunca cuenta en su media.
- **General** — mezcla de las tres. Cada eje se convierte a 0–100 comparándolo
  con el mejor de la liga y se suman con pesos (por defecto 50 % puntos,
  25 % ritmo, 25 % nota, editable en Ajustes). Tocando un jugador ves el
  desglose, para que nadie discuta la tabla sin datos.

**La liga acaba cuando *todos* llegan a 100.** Si tú llegas antes, puedes seguir
apuntando: se guarda y se ve en tu historial marcado como *fuera de liga*, pero
no suma puntos ni cambia tus estadísticas de esta liga. La cifra de 100 se
cambia en Ajustes.

**Campeones**: día, semana (de lunes a domingo) y mes se calculan por puntos
hechos dentro de ese periodo, con el historial de los últimos 12. Empate a
puntos → más entradas → mejor nota.

---

## Jugar entre varios

Ahora mismo no hay servidor compartido, así que hay dos formas:

**A. Un móvil para todos.** Arriba a la derecha se cambia de jugador. Cada uno
apunta lo suyo y vota lo de los demás en el mismo dispositivo. Es lo más
cómodo si soléis salir juntos.

**B. Cada uno en su móvil.** Cada uno apunta lo suyo y, cuando queráis
actualizar la clasificación, en Ajustes:

1. Cada uno le da a **Exportar** (en modo enlace ya va todo lo necesario para
   votar; *Exportar con fotos* solo hace falta si usáis el modo foto).
2. Mandáis el archivo `.json` al grupo.
3. Cada uno importa los de los demás con **Importar y fusionar** (no pisa lo
   tuyo: solo añade lo que le falta).

*Importar y reemplazar* es para cuando cambias de móvil: borra lo de ese
dispositivo y pone lo del archivo.

---

## Cosas que conviene saber

- **Haced copias.** Si borras los datos de navegación del móvil o desinstalas
  la app, la liga se va con ellos. Exportad de vez en cuando.
- **Nada sale del móvil.** Ni entradas, ni enlaces, ni fotos. No se suben al
  repo ni a la web de chollos. Solo viajan si tú exportas y mandas el archivo.
- **Espacio.** El navegador da unos 5 MB. En modo enlace no ocupa
  prácticamente nada. En modo foto se reducen a 640 px y se comprimen (~40 KB
  cada una), así que caben de sobra, y en Ajustes ves lo que llevas ocupado. Si
  se llena, la entrada se guarda igual y solo se pierde la foto, avisando.

---

## Cómo se valora a la pava (y por qué así)

En Ajustes → *Fotos y valoraciones* hay tres modos:

| Modo | Qué guarda la app |
|---|---|
| **Solo el enlace de Instagram** (por defecto) | El `@usuario` y nada más. Al votar, se abre su perfil en Instagram y vuelves a puntuar. **Cero imágenes guardadas.** |
| **Guardar la foto en el móvil** | Una copia reducida, solo en ese dispositivo. |
| **Sin fotos ni enlaces** | Nada. Solo puntos, la tabla de notas se queda vacía. |

El modo enlace viene puesto por defecto a propósito, y te explico por qué:

Que una foto sea pública en su Instagram **no la convierte en libre**. Lo que sí
os cubre bastante es que esto sea uso privado: mientras se quede entre vosotros
y no se publique en ningún sitio, cae en la excepción de "actividad
exclusivamente personal o doméstica" del RGPD (art. 2.2.c). Lo que se sale de
ahí es que se escape — y una copia guardada es algo que se puede filtrar,
perder con el móvil o reenviar sin pensar; un enlace, no. Con el modo enlace la
app nunca tiene una imagen suya: solo apunta a lo que ella misma publicó.

Si aun así usáis el modo foto, en Ajustes tenéis un botón para **borrar todas
las fotos guardadas** sin perder puntos ni notas, y *Exportar con fotos* avisa
antes de meterlas en el archivo.

Sea cual sea el modo: **una entrada cuenta y puntúa igual sin nada adjunto**,
lo único que pierdes es la nota de consenso. La app tampoco guarda nombres.

---

## Lo que falta (siguientes pasos posibles)

1. **Que esté siempre en el móvil sin depender de tu ordenador.** Subirla a un
   hosting gratis (Netlify, Vercel). Como los datos son locales, sigue sin
   costar nada. Lo que **no** recomiendo es publicarla en el GitHub Pages que ya
   tienes: es público y cualquiera con la URL entraría.
2. **Liga compartida de verdad** (que veas al momento lo que apuntan los otros y
   voten sin pasarse archivos). Eso sí necesita una base de datos: con Supabase
   en su plan gratis es un fin de semana de trabajo. Con el modo enlace se
   compartirían solo `@usuarios` y puntos, que es justo lo que hace que esa
   opción sea razonable; subir imágenes a un servidor ya sería otra historia y
   te lo desaconsejo.
3. Ideas sueltas: rachas, motes/apodos para cada entrada, mapa de sitios,
   histórico de ligas anteriores, exportar la clasificación como imagen para el
   grupo.

Dime cuál te interesa y lo montamos.

---

## Para tocar el código

```
liga/
  index.html            todas las pantallas
  css/app.css           estilos
  js/reglas.js          puntos y vocabulario  ← toca aquí para cambiar reglas
  js/estadisticas.js    clasificaciones y campeones
  js/datos.js           guardar, cargar, exportar, importar, fotos
  js/app.js             pantallas y navegación
  pruebas.js            comprobaciones de las cuentas
  sw.js                 cache para funcionar sin cobertura
```

Comprobar que las cuentas siguen cuadrando después de tocar algo:

```bash
node liga/pruebas.js
```
