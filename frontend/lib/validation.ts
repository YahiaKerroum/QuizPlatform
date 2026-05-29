import { z } from "zod";

const emailSchema = z.string().trim().min(1, "Email is required.").email("Enter a valid email address.");
const passwordSchema = z
  .string()
  .min(8, "Password must be at least 8 characters.")
  .max(128, "Password must be 128 characters or less.");

export const loginSchema = z.object({
  email: emailSchema,
  password: z.string().min(1, "Password is required."),
});

export const registerSchema = z.object({
  email: emailSchema,
  password: passwordSchema,
});

export const simulationSchema = z.object({
  students: z.array(z.unknown()),
});

export const moduleSchema = z.object({
  id: z.string().trim().min(1, "Module id is required."),
  display_name: z.string().trim().min(1, "Module display name is required."),
  description: z.string().trim().optional(),
});

export const questionSchema = z.object({
  question_number: z.number().int().positive("Question number must be positive."),
  question_text: z.string().trim().min(1, "Question text is required."),
  question_image_url: z.string().trim().nullable().optional(),
  choice_a: z.string().trim().min(1, "Choice A is required."),
  choice_a_image_url: z.string().trim().nullable().optional(),
  choice_b: z.string().trim().min(1, "Choice B is required."),
  choice_b_image_url: z.string().trim().nullable().optional(),
  choice_c: z.string().trim().nullable().optional(),
  choice_c_image_url: z.string().trim().nullable().optional(),
  choice_d: z.string().trim().nullable().optional(),
  choice_d_image_url: z.string().trim().nullable().optional(),
  choice_e: z.string().trim().nullable().optional(),
  choice_e_image_url: z.string().trim().nullable().optional(),
  choice_f: z.string().trim().nullable().optional(),
  choice_f_image_url: z.string().trim().nullable().optional(),
  correct_answer: z.enum(["a", "b", "c", "d", "e", "f"]),
  difficulty: z.enum(["easy", "medium", "hard"]).nullable().optional(),
});

export const quizSchema = z.object({
  id: z.string().trim().min(1, "Quiz id is required."),
  display_name: z.string().trim().min(1, "Quiz display name is required."),
  module_id: z.string().trim().nullable().optional(),
  questions: z.array(questionSchema).min(1, "At least one question is required."),
});

export const syntheticStudentsSchema = z.object({
  students: z
    .array(
      z.object({
        email: emailSchema,
      }),
    )
    .min(1, "Enter at least one student email."),
});

export const profileRoleSchema = z.object({
  email: emailSchema,
  role: z.enum(["student", "admin"]),
});

export const difficultyUpdatesSchema = z.object({
  updates: z.array(
    z.object({
      quiz_id: z.string().trim().min(1, "Quiz id is required."),
      question_number: z.number().int().positive("Question number must be positive."),
      difficulty: z.string().trim().nullable().optional(),
    }),
  ),
});

export const importFileSchema = z.object({
  fileName: z.string().min(1, "Please select a CSV or JSON file."),
});

export const jsonTextSchema = z.object({
  jsonText: z.string().min(1, "Paste JSON before submitting.").refine((value) => {
    try {
      JSON.parse(value);
      return true;
    } catch {
      return false;
    }
  }, "Enter valid JSON before submitting."),
});
