"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Toast } from "@/components/ui/Toast";
import { setToken } from "@/lib/auth";
import api from "@/lib/api";
import type { TokenOut } from "@/lib/types";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

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

    try {
      const { data } = await api.post<TokenOut>("/auth/login", { email, password });
      setToken(data.access_token);
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
          <form className="space-y-4" onSubmit={handleSubmit}>
            <Input type="email" placeholder="Email address" value={email} onChange={(event) => setEmail(event.target.value)} />
            <Input type="password" placeholder="Password" value={password} onChange={(event) => setPassword(event.target.value)} />
            <Button className="w-full" variant="secondary" disabled={loading} type="submit">
              {loading ? "Signing in..." : "Login"}
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
