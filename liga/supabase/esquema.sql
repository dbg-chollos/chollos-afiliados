-- =============================================================================
-- La Liga — base de datos en Supabase
--
-- Pega este archivo entero en Supabase → SQL Editor → New query → Run.
-- Se puede volver a ejecutar sin miedo: no borra nada de lo que ya haya.
--
-- La idea: cada liga tiene un codigo secreto. Quien lo tiene puede unirse;
-- quien no, no ve absolutamente nada. Eso lo garantiza Postgres (RLS), no la
-- app: aunque alguien se ponga a llamar a la API a mano, no puede leer una
-- liga en la que no esta.
-- =============================================================================

create extension if not exists pgcrypto;

-- --- Tablas ------------------------------------------------------------------

create table if not exists public.ligas (
  id         uuid primary key default gen_random_uuid(),
  nombre     text not null,
  codigo     text not null unique,
  reglas     jsonb not null default '{}'::jsonb,
  creada_por uuid not null references auth.users (id) on delete cascade,
  creada     timestamptz not null default now()
);

create table if not exists public.miembros (
  liga_id uuid not null references public.ligas (id) on delete cascade,
  usuario uuid not null references auth.users (id) on delete cascade,
  nombre  text not null,
  color   text not null default '#e5484d',
  unido   timestamptz not null default now(),
  primary key (liga_id, usuario)
);

-- El id lo genera la propia app (el mismo que ya usa en el movil), asi se
-- puede sincronizar sin duplicar lo que se apunto sin cobertura.
create table if not exists public.entradas (
  id        text primary key,
  liga_id   uuid not null references public.ligas (id) on delete cascade,
  usuario   uuid not null references auth.users (id) on delete cascade,
  fecha     timestamptz not null,
  rechazo   boolean not null default false,
  fiesta    boolean not null default false,
  lugar     text,
  resultado text not null,
  foto      text,   -- ruta dentro del bucket 'fotos', o null
  perfil    text,   -- @usuario de Instagram, o null
  creada    timestamptz not null default now()
);

create index if not exists entradas_liga_fecha on public.entradas (liga_id, fecha);

create table if not exists public.votos (
  entrada_id text not null references public.entradas (id) on delete cascade,
  usuario    uuid not null references auth.users (id) on delete cascade,
  nota       smallint not null check (nota between 1 and 10),
  puesto     timestamptz not null default now(),
  primary key (entrada_id, usuario)
);

-- --- Quien es miembro de que ------------------------------------------------

-- Se consulta desde las politicas de abajo. Va como SECURITY DEFINER para que
-- no se muerda la cola: si preguntase por 'miembros' con RLS puesta, para
-- comprobar si puedes leer 'miembros' habria que leer 'miembros'.
create or replace function public.es_miembro(p_liga uuid)
returns boolean
language sql
security definer
stable
set search_path = public
as $$
  select exists (
    select 1 from public.miembros
    where liga_id = p_liga and usuario = auth.uid()
  );
$$;

-- --- Crear y unirse ----------------------------------------------------------

-- Crear una liga y quedarse dentro, en un solo paso.
create or replace function public.crear_liga(
  p_nombre  text,
  p_codigo  text,
  p_jugador text,
  p_color   text default '#e5484d',
  p_reglas  jsonb default '{}'::jsonb
)
returns public.ligas
language plpgsql
security definer
set search_path = public
as $$
declare
  nueva public.ligas;
begin
  if auth.uid() is null then
    raise exception 'Hay que iniciar sesion antes de crear una liga';
  end if;

  insert into public.ligas (nombre, codigo, reglas, creada_por)
  values (p_nombre, upper(trim(p_codigo)), coalesce(p_reglas, '{}'::jsonb), auth.uid())
  returning * into nueva;

  insert into public.miembros (liga_id, usuario, nombre, color)
  values (nueva.id, auth.uid(), p_jugador, p_color);

  return nueva;
end;
$$;

-- Unirse con el codigo. Es la unica forma de entrar: sin el codigo no hay
-- manera de averiguar siquiera que esa liga existe.
create or replace function public.unirse_a_liga(
  p_codigo  text,
  p_jugador text,
  p_color   text default '#3e63dd'
)
returns public.ligas
language plpgsql
security definer
set search_path = public
as $$
declare
  destino public.ligas;
begin
  if auth.uid() is null then
    raise exception 'Hay que iniciar sesion antes de unirse';
  end if;

  select * into destino from public.ligas where codigo = upper(trim(p_codigo));
  if destino.id is null then
    raise exception 'No hay ninguna liga con ese codigo';
  end if;

  insert into public.miembros (liga_id, usuario, nombre, color)
  values (destino.id, auth.uid(), p_jugador, p_color)
  on conflict (liga_id, usuario) do update set nombre = excluded.nombre;

  return destino;
end;
$$;

-- --- Permisos (RLS) ----------------------------------------------------------

alter table public.ligas    enable row level security;
alter table public.miembros enable row level security;
alter table public.entradas enable row level security;
alter table public.votos    enable row level security;

drop policy if exists ligas_leer on public.ligas;
create policy ligas_leer on public.ligas
  for select using (public.es_miembro(id));

-- Las reglas (puntos, limite, pesos) las puede tocar quien creo la liga.
drop policy if exists ligas_editar on public.ligas;
create policy ligas_editar on public.ligas
  for update using (creada_por = auth.uid()) with check (creada_por = auth.uid());

drop policy if exists miembros_leer on public.miembros;
create policy miembros_leer on public.miembros
  for select using (public.es_miembro(liga_id));

-- Cada uno puede cambiar su propio nombre o color, el de los demas no.
drop policy if exists miembros_editar on public.miembros;
create policy miembros_editar on public.miembros
  for update using (usuario = auth.uid()) with check (usuario = auth.uid());

drop policy if exists entradas_leer on public.entradas;
create policy entradas_leer on public.entradas
  for select using (public.es_miembro(liga_id));

drop policy if exists entradas_crear on public.entradas;
create policy entradas_crear on public.entradas
  for insert with check (usuario = auth.uid() and public.es_miembro(liga_id));

drop policy if exists entradas_editar on public.entradas;
create policy entradas_editar on public.entradas
  for update using (usuario = auth.uid()) with check (usuario = auth.uid());

drop policy if exists entradas_borrar on public.entradas;
create policy entradas_borrar on public.entradas
  for delete using (usuario = auth.uid());

drop policy if exists votos_leer on public.votos;
create policy votos_leer on public.votos
  for select using (
    exists (
      select 1 from public.entradas e
      where e.id = votos.entrada_id and public.es_miembro(e.liga_id)
    )
  );

-- Se puede votar lo de los demas, no lo propio.
drop policy if exists votos_poner on public.votos;
create policy votos_poner on public.votos
  for insert with check (
    usuario = auth.uid()
    and exists (
      select 1 from public.entradas e
      where e.id = votos.entrada_id
        and public.es_miembro(e.liga_id)
        and e.usuario <> auth.uid()
    )
  );

drop policy if exists votos_cambiar on public.votos;
create policy votos_cambiar on public.votos
  for update using (usuario = auth.uid()) with check (usuario = auth.uid());

drop policy if exists votos_quitar on public.votos;
create policy votos_quitar on public.votos
  for delete using (usuario = auth.uid());

-- --- Fotos -------------------------------------------------------------------

-- Bucket privado: las fotos no tienen URL publica, se piden con la sesion.
insert into storage.buckets (id, name, public)
values ('fotos', 'fotos', false)
on conflict (id) do nothing;

-- Las fotos se guardan como  <liga_id>/<entrada_id>.jpg , asi la carpeta dice
-- a que liga pertenece cada una y se puede comprobar sin consultar nada mas.
drop policy if exists fotos_leer on storage.objects;
create policy fotos_leer on storage.objects
  for select using (
    bucket_id = 'fotos'
    and public.es_miembro(((storage.foldername(name))[1])::uuid)
  );

drop policy if exists fotos_subir on storage.objects;
create policy fotos_subir on storage.objects
  for insert with check (
    bucket_id = 'fotos'
    and owner = auth.uid()
    and public.es_miembro(((storage.foldername(name))[1])::uuid)
  );

drop policy if exists fotos_borrar on storage.objects;
create policy fotos_borrar on storage.objects
  for delete using (bucket_id = 'fotos' and owner = auth.uid());

-- --- Permisos de ejecucion ---------------------------------------------------

grant execute on function public.crear_liga(text, text, text, text, jsonb) to authenticated;
grant execute on function public.unirse_a_liga(text, text, text) to authenticated;
grant execute on function public.es_miembro(uuid) to authenticated;
