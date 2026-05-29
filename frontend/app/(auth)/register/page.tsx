"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Toast } from "@/components/ui/Toast";
import { setTokenWithExpiry } from "@/lib/auth";
import { summarizeFormError } from "@/lib/form";
import { supabase } from "@/lib/supabase";
import { registerSchema } from "@/lib/validation";

type RegisterFormData = z.infer<typeof registerSchema>;

export default function RegisterPage() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    watch,
    formState: { errors, isSubmitting, isValid },
  } = useForm<RegisterFormData>({
    mode: "onChange",
    defaultValues: {
      email: "",
      password: "",
    },
  });

  const email = watch("email") ?? "";
  const password = watch("password") ?? "";
  const normalizedEmail = email.trim();
  const emailIsValid = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(normalizedEmail);
  const passwordMinLength = password.length >= 8;
  const passwordMaxLength = password.length <= 128;

  function summarizeError(err: unknown) {
    if (typeof err === "object" && err && "response" in err) {
      const detail = (err as { response?: { data?: { detail?: unknown } } }).response?.data?.detail;
      if (typeof detail === "string") {
        return detail;
      }
    }
    return "Registration failed. Make sure the email is unique and the password is at least 8 characters.";
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    setSuccess(null);

    const parsed = registerSchema.safeParse(formData);
    if (!parsed.success) {
      setError(`Registration failed: ${summarizeFormError(parsed.error, "Please try again.")}`);
      return;
    }

    try {
      const { data: authData, error: signUpError } = await supabase.auth.signUp({
        email: parsed.data.email,
        password: parsed.data.password,
      });
      if (signUpError) {
        throw signUpError;
      }

      if (authData.session?.access_token) {
        setTokenWithExpiry(authData.session.access_token, authData.session.expires_in ?? 3600);
        router.push("/dashboard");
        return;
      }

      const { data: signInData, error: signInError } = await supabase.auth.signInWithPassword({
        email: parsed.data.email,
        password: parsed.data.password,
      });
      if (signInError || !signInData.session?.access_token) {
        throw signInError ?? new Error("Missing Supabase session.");
      }

      setTokenWithExpiry(signInData.session.access_token, signInData.session.expires_in ?? 3600);
      router.push("/dashboard");
    } catch (err) {
      setError(summarizeError(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-3xl items-center px-6 py-12">
      <Card className="motion-rise mx-auto w-full max-w-xl space-y-6">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.28em] text-clay">Create account</p>
          <h1 className="mt-3 font-heading text-4xl text-ink">Register as a real student user</h1>
        </div>
        {success ? <Toast message={success} tone="success" /> : null}
        {error ? <Toast message={error} tone="error" /> : null}
        <form className="space-y-4" onSubmit={handleSubmit(onSubmit)}>
          <div className="space-y-2">
            <Input
              type="email"
              placeholder="Email address"
              autoComplete="email"
              {...register("email", {
                required: "Email is required.",
                pattern: {
                  value: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
                  message: "Enter a valid email address.",
                },
              })}
            />
            {errors.email ? <p className="text-xs text-red-700">{errors.email.message}</p> : null}
          </div>
          <div className="space-y-2">
            <Input
              type="password"
              placeholder="Password"
              autoComplete="new-password"
              {...register("password", {
                required: "Password is required.",
                minLength: {
                  value: 8,
                  message: "Password must be at least 8 characters.",
                },
                maxLength: {
                  value: 128,
                  message: "Password must be 128 characters or less.",
                },
              })}
            />
            {errors.password ? <p className="text-xs text-red-700">{errors.password.message}</p> : null}
          </div>
          <div className="rounded-2xl border border-ink/10 bg-ivory px-4 py-3 text-sm text-ink/80">
            <p className="font-semibold text-ink">Registration requirements</p>
            <ul className="mt-2 space-y-1">
              <li>{emailIsValid ? "✓" : "•"} Use a valid email address</li>
              <li>{passwordMinLength ? "✓" : "•"} Password must be at least 8 characters</li>
              <li>{passwordMaxLength ? "✓" : "•"} Password must be 128 characters or less</li>
            </ul>
            <p className="mt-2 text-xs text-ink/65">Supabase may still enforce additional password rules configured in project settings.</p>
          </div>
          <Button className="w-full" variant="secondary" disabled={isSubmitting || !isValid} type="submit">
            {isSubmitting ? "Creating account..." : "Register"}
          </Button>
        </form>
        <p className="text-sm text-ink/70">
          Already registered? <Link className="font-semibold text-clay" href="/login">Back to login</Link>
        </p>
      </Card>
    </main>
  );
}
