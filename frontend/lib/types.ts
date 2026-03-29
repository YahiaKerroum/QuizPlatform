export interface TokenOut {
  access_token: string;
  token_type: string;
  student_id: string;
}

export interface QuestionOut {
  question_number: number;
  question_text: string;
  choice_a: string;
  choice_b: string;
  choice_c: string | null;
  choice_d: string | null;
  choice_e: string | null;
  choice_f: string | null;
}

export interface QuizSummaryOut {
  id: string;
  display_name: string;
  question_count: number;
}

export interface SessionStartOut {
  session_id: string;
  question: QuestionOut;
  question_number: number;
  total: number;
}

export interface AnswerOut {
  done: boolean;
  question: QuestionOut | null;
  question_number: number | null;
  total: number | null;
  session_id: string | null;
}

export interface QuestionResultOut {
  question_number: number;
  chosen_answer: string;
  is_correct: boolean;
  response_time_ms: number;
  difficulty: string | null;
  answered_at: string;
}

export interface ResultOut {
  total: number;
  correct: number;
  accuracy: number;
  by_difficulty: Record<string, { total: number; correct: number; accuracy: number }>;
  by_question: QuestionResultOut[];
}

export interface SessionHistoryOut {
  session_id: string;
  quiz_id: string;
  display_name: string;
  started_at: string;
  ended_at: string | null;
  total: number;
  correct: number;
  accuracy: number;
}

export interface ImportOut {
  quizzes_created: number;
  questions_inserted: number;
  questions_skipped: number;
}

export interface SyntheticStudentOut {
  email: string;
  id: string;
}

export interface SimBatchOut {
  sessions_created: number;
  answers_inserted: number;
  errors: string[];
}

export interface DifficultyOut {
  updated: number;
}
