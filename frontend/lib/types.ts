export interface TokenOut {
  access_token: string;
  token_type: string;
  student_id: string;
}

export interface AdminAccessOut {
  allowed: boolean;
  email: string;
}

export interface QuestionOut {
  question_number: number;
  question_text: string;
  question_image_url: string | null;
  choice_a: string;
  choice_a_image_url: string | null;
  choice_b: string;
  choice_b_image_url: string | null;
  choice_c: string | null;
  choice_c_image_url: string | null;
  choice_d: string | null;
  choice_d_image_url: string | null;
  choice_e: string | null;
  choice_e_image_url: string | null;
  choice_f: string | null;
  choice_f_image_url: string | null;
}

export interface AdminQuestionIn {
  question_number: number;
  question_text: string;
  question_image_url: string | null;
  choice_a: string;
  choice_a_image_url: string | null;
  choice_b: string;
  choice_b_image_url: string | null;
  choice_c: string | null;
  choice_c_image_url: string | null;
  choice_d: string | null;
  choice_d_image_url: string | null;
  choice_e: string | null;
  choice_e_image_url: string | null;
  choice_f: string | null;
  choice_f_image_url: string | null;
  correct_answer: string;
  difficulty: string | null;
}

export interface ModuleOut {
  id: string;
  display_name: string;
  description: string | null;
  quiz_count: number;
}

export interface QuizSummaryOut {
  id: string;
  display_name: string;
  module_id: string | null;
  module_display_name: string | null;
  question_count: number;
}

export interface ModuleWithQuizzesOut {
  id: string;
  display_name: string;
  description: string | null;
  quizzes: QuizSummaryOut[];
}

export interface QuizDetailOut {
  id: string;
  display_name: string;
  module_id: string | null;
  module_display_name: string | null;
  questions: QuestionOut[];
}

export interface QuizUpsertIn {
  id: string;
  display_name: string;
  module_id: string | null;
  questions: AdminQuestionIn[];
}

export interface AdminQuizDetailOut {
  id: string;
  display_name: string;
  module_id: string | null;
  module_display_name: string | null;
  questions: AdminQuestionIn[];
}

export interface SessionStartOut {
  session_id: string;
  question: QuestionOut;
  question_number: number;
  total: number;
  is_adaptive: boolean;
}

export interface AnswerOut {
  done: boolean;
  question: QuestionOut | null;
  question_number: number | null;
  total: number | null;
  session_id: string | null;
  predicted_level: "beginner" | "intermediate" | "advanced" | null;
  confidence: number | null;
}

export interface QuestionResultOut {
  question_number: number;
  question_text: string;
  question_image_url: string | null;
  chosen_answer: string;
  correct_answer: string;
  chosen_answer_text: string | null;
  chosen_answer_image_url: string | null;
  correct_answer_text: string;
  correct_answer_image_url: string | null;
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
  is_adaptive: boolean;
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
