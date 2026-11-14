-- Cadastro manual da IA do bot (provedor, chave e modelo)
-- Rodar no SQL Editor do Supabase

create table if not exists public.ai_config (
  id text not null default 'global'::text,
  base_url text not null,
  api_key text not null,
  model text not null,
  created_at timestamp with time zone null default now(),
  updated_at timestamp with time zone null default now(),
  constraint ai_config_pkey primary key (id)
) TABLESPACE pg_default;

-- Sem RLS, igual às demais tabelas do bot (a chave do Supabase precisa
-- conseguir gravar a config da IA; com RLS ligado o insert é bloqueado)
alter table public.ai_config disable row level security;
