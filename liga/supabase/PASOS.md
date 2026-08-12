# Poner la liga en común — lo que tienes que hacer tú

Son unos 10 minutos y no hay que saber programar. Todo lo que viene aquí es
gratis: el plan que vamos a usar de Supabase no pide tarjeta.

Yo no puedo hacer estos pasos por ti porque hay que crear una cuenta con tu
correo, y eso requiere ser tú.

---

## 1. Crear la cuenta y el proyecto (3 min)

1. Entra en **[supabase.com](https://supabase.com)** → *Start your project*.
2. Regístrate (lo más rápido es *Continue with GitHub*, que ya tienes cuenta).
3. *New project* y rellena:
   - **Name**: `la-liga`
   - **Database Password**: pulsa *Generate a password* y **guárdala** en las
     notas del móvil. No la vas a necesitar para esto, pero perderla es un lío
     si algún día hace falta.
   - **Region**: `West EU (Ireland)` o `Central EU (Frankfurt)` — cuanto más
     cerca, más rápido va.
   - **Plan**: Free.
4. Dale a *Create new project* y espera un par de minutos a que termine de
   montarse.

---

## 2. Crear las tablas (2 min)

1. En el menú de la izquierda: **SQL Editor** → *New query*.
2. Abre el archivo `liga/supabase/esquema.sql` de este repo, copia **todo** su
   contenido y pégalo ahí.
3. Pulsa **Run** (o Ctrl+Enter).

Tiene que salir *Success. No rows returned*. Si sale algo en rojo, mándame el
mensaje tal cual y lo miro.

Eso crea las tablas, el sitio donde van las fotos y —lo importante— las reglas
de acceso: quien no tenga el código de la liga no puede leer nada de ella, y no
porque la app se lo impida, sino porque la base de datos lo rechaza.

---

## 3. Dejar que se pueda entrar con el correo (1 min)

1. Menú de la izquierda: **Authentication** → *Providers*.
2. Comprueba que **Email** está activado (viene así de serie).
3. En **Authentication → Sign In / Providers → Email**, deja activado
   *Enable Email provider*. No hace falta contraseña: cada uno entrará con un
   enlace que le llega al correo.

> Supabase manda esos correos gratis pero con un límite bajo por hora. Para
> cuatro amigos que entran una vez, de sobra.

---

## 4. Pasarme los dos valores (1 min)

1. Menú de la izquierda: **Project Settings** (la rueda dentada) → **API**.
2. Copia estos dos:
   - **Project URL** — algo como `https://abcdefgh.supabase.co`
   - **anon public** — una clave larguísima que empieza por `eyJ...`
3. Pégamelos en el chat, o mételos tú mismo en `liga/js/config.js`.

### Lo único que importa de seguridad aquí

En esa misma página hay una tercera clave, **`service_role`**. Esa **no me la
pases, ni la pongas en ningún archivo, ni se la mandes a nadie**: se salta todas
las reglas de acceso y quien la tenga puede leer y borrar lo que quiera.

La `anon public` sí es para ir dentro de la app — está diseñada para eso. Sin
iniciar sesión no da acceso a nada, y quien inicia sesión solo ve las ligas en
las que está.

---

## 5. A partir de ahí ya sigo yo

Con esos dos valores termino de conectar la app y la probamos. El resultado
será:

- Cada uno entra una vez con su correo, desde su móvil.
- El primero crea la liga y le sale un **código** (algo tipo `LIGA-4F2K`).
- Los demás meten ese código y ya están dentro.
- A partir de ahí, lo que apunte cualquiera lo ven todos, y las fotos aparecen
  solas en la pestaña de Votar sin pasarse nada por WhatsApp.
- Si te quedas sin cobertura, sigues apuntando: se guarda en el móvil y sube
  cuando vuelvas a tener internet.

---

## Lo que cambia respecto a ahora

Merece la pena que lo sepas antes de dar el paso: hasta ahora **nada** salía de
vuestros móviles. Con esto, las entradas, los puntos y **las fotos** pasan a
estar también en un servidor, en tu cuenta de Supabase.

Sigue siendo privado — solo entra quien tenga el código, y las fotos van en un
sitio cerrado sin dirección pública —, pero ya no es lo mismo que tenerlo solo
en el bolsillo. Si en algún momento quieres cortar por lo sano, desde tu panel
de Supabase puedes borrar el proyecto entero y no queda nada.
