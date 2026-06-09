-- ============================================================
-- Row Level Security policies for QuizPlatform
-- Run this in the Supabase SQL editor (or as a migration).
-- The service-role key bypasses all RLS automatically,
-- so admin routes are unaffected.
-- ============================================================

-- ── Enable RLS on every table ───────────────────────────────
ALTER TABLE students  ENABLE ROW LEVEL SECURITY;
ALTER TABLE profiles  ENABLE ROW LEVEL SECURITY;
ALTER TABLE modules   ENABLE ROW LEVEL SECURITY;
ALTER TABLE quizzes   ENABLE ROW LEVEL SECURITY;
ALTER TABLE questions ENABLE ROW LEVEL SECURITY;
ALTER TABLE sessions  ENABLE ROW LEVEL SECURITY;
ALTER TABLE answers   ENABLE ROW LEVEL SECURITY;

-- ── Helper: resolve the current user's student row ──────────
-- auth.uid()  → profiles.user_id  → profiles.email  → students.id
-- We use this pattern in the policies below.

-- ── modules / quizzes / questions: readable by all authenticated users ──
CREATE POLICY "modules_read_authenticated"
  ON modules FOR SELECT TO authenticated
  USING (true);

CREATE POLICY "quizzes_read_authenticated"
  ON quizzes FOR SELECT TO authenticated
  USING (true);

CREATE POLICY "questions_read_authenticated"
  ON questions FOR SELECT TO authenticated
  USING (true);

-- ── profiles: each user sees only their own row ─────────────
CREATE POLICY "profiles_own"
  ON profiles FOR ALL TO authenticated
  USING  (user_id = auth.uid())
  WITH CHECK (user_id = auth.uid());

-- ── students: each user sees only their own row ─────────────
CREATE POLICY "students_own_read"
  ON students FOR SELECT TO authenticated
  USING (
    email IN (
      SELECT email FROM profiles WHERE user_id = auth.uid()
    )
  );

-- ── sessions: students can only see / insert their own ──────
CREATE POLICY "sessions_own"
  ON sessions FOR ALL TO authenticated
  USING (
    student_id IN (
      SELECT s.id FROM students s
      JOIN profiles p ON p.email = s.email
      WHERE p.user_id = auth.uid()
    )
  )
  WITH CHECK (
    student_id IN (
      SELECT s.id FROM students s
      JOIN profiles p ON p.email = s.email
      WHERE p.user_id = auth.uid()
    )
  );

-- ── answers: students can only see / insert answers for their own sessions ──
CREATE POLICY "answers_own"
  ON answers FOR ALL TO authenticated
  USING (
    session_id IN (
      SELECT sess.id FROM sessions sess
      JOIN students s   ON s.id   = sess.student_id
      JOIN profiles p   ON p.email = s.email
      WHERE p.user_id = auth.uid()
    )
  )
  WITH CHECK (
    session_id IN (
      SELECT sess.id FROM sessions sess
      JOIN students s   ON s.id   = sess.student_id
      JOIN profiles p   ON p.email = s.email
      WHERE p.user_id = auth.uid()
    )
  );
