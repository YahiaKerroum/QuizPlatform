-- Elo ratings for students (per module) and items -- see
-- backend/services/elo_service.py. Already included in backend/schema.sql;
-- this is the incremental delta for an existing database.

CREATE TABLE IF NOT EXISTS public.student_ratings (
    student_id UUID NOT NULL REFERENCES public.students(id) ON DELETE CASCADE,
    module_id TEXT NOT NULL REFERENCES public.modules(id) ON DELETE CASCADE,
    rating REAL NOT NULL DEFAULT 1200,
    n_answers INT NOT NULL DEFAULT 0,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (student_id, module_id)
);

CREATE TABLE IF NOT EXISTS public.item_ratings (
    quiz_id TEXT NOT NULL,
    question_number INT NOT NULL,
    rating REAL NOT NULL DEFAULT 1200,
    n_answers INT NOT NULL DEFAULT 0,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (quiz_id, question_number),
    FOREIGN KEY (quiz_id, question_number) REFERENCES public.questions(quiz_id, question_number) ON DELETE CASCADE
);

ALTER TABLE public.student_ratings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.item_ratings ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS student_ratings_self_select ON public.student_ratings;
CREATE POLICY student_ratings_self_select
    ON public.student_ratings FOR SELECT TO authenticated
    USING (
        student_id IN (SELECT s.id FROM public.students s WHERE lower(s.email) = lower(auth.email()))
    );

DROP POLICY IF EXISTS item_ratings_read_authenticated ON public.item_ratings;
CREATE POLICY item_ratings_read_authenticated
    ON public.item_ratings FOR SELECT TO authenticated USING (true);
