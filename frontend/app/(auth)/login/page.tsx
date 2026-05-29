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
import { loginSchema } from "@/lib/validation";

type LoginFormData = z.infer<typeof loginSchema>;

export default function LoginPage() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginFormData>({
    mode: "onTouched",
    defaultValues: {
      email: "",
      password: "",
    },
  });

  function summarizeError(err: unknown) {
    if (typeof err === "object" && err && "response" in err) {
      const detail = (err as { response?: { data?: { detail?: unknown } } }).response?.data?.detail;
      if (typeof detail === "string") {
        return detail;
      }
    }
    return "Login failed. Check your email and password.";
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError(null);

    const parsed = loginSchema.safeParse(formData);
    if (!parsed.success) {
      setError(`Login failed: ${summarizeFormError(parsed.error, "Check your email and password.")}`);
      return;
    }

    try {
      const { data: authData, error: signInError } = await supabase.auth.signInWithPassword({
        email: parsed.data.email,
        password: parsed.data.password,
      });
      if (signInError || !authData.session?.access_token) {
        throw signInError ?? new Error("Missing Supabase session.");
      }

      setTokenWithExpiry(authData.session.access_token, authData.session.expires_in ?? 3600);
      router.push("/dashboard");
    } catch (err) {
      setError(summarizeError(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-6xl items-center px-6 py-12">
      <div className="grid w-full gap-10 md:grid-cols-[1.1fr_0.9fr]">
        <section className="motion-rise space-y-6">
          <p className="text-sm font-semibold uppercase tracking-[0.28em] text-clay">Adaptive Quiz Platform</p>
          <h1 className="font-heading text-5xl text-ink md:text-6xl">Collect cleaner question-by-question learning data.</h1>
          <p className="max-w-xl text-lg leading-8 text-ink/75">
            Students answer one prompt at a time, every response is timed, and the dataset stays structured from the first quiz to the final export.
          </p>
        </section>
        <Card className="motion-rise motion-delay-1 space-y-6">
          <div>
            <h2 className="font-heading text-3xl text-ink">Sign in</h2>
            <p className="mt-2 text-sm text-ink/70">Use your student account to continue.</p>
          </div>
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
                autoComplete="current-password"
                {...register("password", {
                  required: "Password is required.",
                })}
              />
              {errors.password ? <p className="text-xs text-red-700">{errors.password.message}</p> : null}
            </div>
            <Button className="w-full" variant="secondary" disabled={isSubmitting} type="submit">
              {isSubmitting ? "Signing in..." : "Login"}
            </Button>
          </form>
          <p className="text-sm text-ink/70">
            Need an account? <Link className="font-semibold text-clay" href="/register">Register here</Link>
          </p>
        </Card>
      </div>
    </main>
  );
}
