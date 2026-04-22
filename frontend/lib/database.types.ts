export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[];

export type Database = {
  public: {
    Tables: {
      answers: {
        Row: {
          answered_at: string;
          chosen_answer: string;
          id: string;
          is_correct: boolean;
          question_number: number;
          quiz_id: string;
          response_time_ms: number;
          session_id: string;
        };
        Insert: {
          answered_at?: string;
          chosen_answer: string;
          id?: string;
          is_correct: boolean;
          question_number: number;
          quiz_id: string;
          response_time_ms: number;
          session_id: string;
        };
        Update: {
          answered_at?: string;
          chosen_answer?: string;
          id?: string;
          is_correct?: boolean;
          question_number?: number;
          quiz_id?: string;
          response_time_ms?: number;
          session_id?: string;
        };
        Relationships: [];
      };
      modules: {
        Row: {
          created_at: string;
          description: string | null;
          display_name: string;
          id: string;
        };
        Insert: {
          created_at?: string;
          description?: string | null;
          display_name: string;
          id: string;
        };
        Update: {
          created_at?: string;
          description?: string | null;
          display_name?: string;
          id?: string;
        };
        Relationships: [];
      };
      profiles: {
        Row: {
          created_at: string;
          email: string;
          role: string;
          user_id: string;
        };
        Insert: {
          created_at?: string;
          email: string;
          role?: string;
          user_id: string;
        };
        Update: {
          created_at?: string;
          email?: string;
          role?: string;
          user_id?: string;
        };
        Relationships: [];
      };
      questions: {
        Row: {
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
          question_image_url: string | null;
          question_number: number;
          question_text: string;
          quiz_id: string;
        };
        Insert: {
          choice_a: string;
          choice_a_image_url?: string | null;
          choice_b: string;
          choice_b_image_url?: string | null;
          choice_c?: string | null;
          choice_c_image_url?: string | null;
          choice_d?: string | null;
          choice_d_image_url?: string | null;
          choice_e?: string | null;
          choice_e_image_url?: string | null;
          choice_f?: string | null;
          choice_f_image_url?: string | null;
          correct_answer: string;
          difficulty?: string | null;
          question_image_url?: string | null;
          question_number: number;
          question_text: string;
          quiz_id: string;
        };
        Update: {
          choice_a?: string;
          choice_a_image_url?: string | null;
          choice_b?: string;
          choice_b_image_url?: string | null;
          choice_c?: string | null;
          choice_c_image_url?: string | null;
          choice_d?: string | null;
          choice_d_image_url?: string | null;
          choice_e?: string | null;
          choice_e_image_url?: string | null;
          choice_f?: string | null;
          choice_f_image_url?: string | null;
          correct_answer?: string;
          difficulty?: string | null;
          question_image_url?: string | null;
          question_number?: number;
          question_text?: string;
          quiz_id?: string;
        };
        Relationships: [
          {
            foreignKeyName: "questions_quiz_id_fkey";
            columns: ["quiz_id"];
            isOneToOne: false;
            referencedRelation: "quizzes";
            referencedColumns: ["id"];
          },
        ];
      };
      quizzes: {
        Row: {
          created_at: string;
          display_name: string;
          id: string;
          module_id: string | null;
        };
        Insert: {
          created_at?: string;
          display_name: string;
          id: string;
          module_id?: string | null;
        };
        Update: {
          created_at?: string;
          display_name?: string;
          id?: string;
          module_id?: string | null;
        };
        Relationships: [
          {
            foreignKeyName: "quizzes_module_id_fkey";
            columns: ["module_id"];
            isOneToOne: false;
            referencedRelation: "modules";
            referencedColumns: ["id"];
          },
        ];
      };
      sessions: {
        Row: {
          ended_at: string | null;
          id: string;
          quiz_id: string;
          started_at: string;
          student_id: string;
        };
        Insert: {
          ended_at?: string | null;
          id?: string;
          quiz_id: string;
          started_at?: string;
          student_id: string;
        };
        Update: {
          ended_at?: string | null;
          id?: string;
          quiz_id?: string;
          started_at?: string;
          student_id?: string;
        };
        Relationships: [
          {
            foreignKeyName: "sessions_quiz_id_fkey";
            columns: ["quiz_id"];
            isOneToOne: false;
            referencedRelation: "quizzes";
            referencedColumns: ["id"];
          },
          {
            foreignKeyName: "sessions_student_id_fkey";
            columns: ["student_id"];
            isOneToOne: false;
            referencedRelation: "students";
            referencedColumns: ["id"];
          },
        ];
      };
      students: {
        Row: {
          created_at: string;
          email: string;
          id: string;
          is_synthetic: boolean;
          password_hash: string | null;
        };
        Insert: {
          created_at?: string;
          email: string;
          id?: string;
          is_synthetic?: boolean;
          password_hash?: string | null;
        };
        Update: {
          created_at?: string;
          email?: string;
          id?: string;
          is_synthetic?: boolean;
          password_hash?: string | null;
        };
        Relationships: [];
      };
    };
    Views: Record<string, never>;
    Functions: Record<string, never>;
    Enums: Record<string, never>;
    CompositeTypes: Record<string, never>;
  };
};
