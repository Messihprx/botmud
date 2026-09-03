-- ============================================================
-- MIGRAÇÃO: Remover recruiter_name redundante de recruitments
-- O nome do recrutador agora é obtido via JOIN com a tabela recruiters
-- ============================================================

-- 1. Criar VIEW com JOIN automático (para consultas)
CREATE OR REPLACE VIEW public.recruitments_view AS
SELECT
    r.id,
    r.registro_id,
    r.recruiter_id,
    COALESCE(rec.recruiter_name, 'Sem registro') AS recruiter_name,
    r.recruit_id,
    r.recruit_roblox_name,
    r.recruit_roblox_nick,
    r.recruit_age,
    r.recruit_discord_nick,
    r.gender,
    r.platform,
    r.recruit_image,
    r.saidas_count,
    r.created_at
FROM public.recruitments r
LEFT JOIN public.recruiters rec ON r.recruiter_id = rec.recruiter_id;

-- 2. Remover a coluna recruiter_name da tabela recruitments
-- (execute SOMENTE após confirmar que a VIEW está funcionando)
ALTER TABLE public.recruitments DROP COLUMN IF EXISTS recruiter_name;

-- ============================================================
-- PRONTO! Agora:
-- - Use "recruitments_view" para consultas (SELECT)
-- - Use "recruitments" para INSERT/UPDATE/DELETE (sem recruiter_name)
-- ============================================================
