-- Create profiles table for Supabase-authenticated users and role-based access.

CREATE TABLE IF NOT EXISTS public.profiles (
    user_id UUID PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    role TEXT NOT NULL DEFAULT 'student' CHECK (role IN ('student', 'admin')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS profiles_self_select ON public.profiles;
DROP POLICY IF EXISTS profiles_self_insert ON public.profiles;

CREATE POLICY profiles_self_select
ON public.profiles
FOR SELECT
TO authenticated
USING (lower(email) = lower(auth.email()));

CREATE POLICY profiles_self_insert
ON public.profiles
FOR INSERT
TO authenticated
WITH CHECK (lower(email) = lower(auth.email()));
