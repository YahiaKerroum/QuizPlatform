-- Persist the adaptive-quiz predicted level and confidence on the session row
-- itself, instead of only ever handing it to the client and relying on
-- sessionStorage to carry it across to the result page.

ALTER TABLE public.sessions
    ADD COLUMN IF NOT EXISTS predicted_level TEXT CHECK (predicted_level IN ('beginner', 'intermediate', 'advanced')),
    ADD COLUMN IF NOT EXISTS confidence REAL CHECK (confidence IS NULL OR (confidence >= 0 AND confidence <= 1));
