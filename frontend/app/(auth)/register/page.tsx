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

export default function RegisterPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const { data } = await api.post<TokenOut>("/auth/register", { email, password });
      setToken(data.access_token);
      router.push("/dashboard");
    } catch {
      setError("Registration failed. Make sure the email is unique and the password is at least 8 characters.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-3xl items-center px-6 py-12">
      <Card className="mx-auto w-full max-w-xl space-y-6">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.28em] text-clay">Create account</p>
          <h1 className="mt-3 font-heading text-4xl text-ink">Register as a real student user</h1>
        </div>
        {error ? <Toast message={error} tone="error" /> : null}
        <form className="space-y-4" onSubmit={handleSubmit}>
          <Input type="email" placeholder="Email address" value={email} onChange={(event) => setEmail(event.target.value)} />
          <Input type="password" placeholder="Password" value={password} onChange={(event) => setPassword(event.target.value)} />
          <Button className="w-full" variant="secondary" disabled={loading} type="submit">
            {loading ? "Creating account..." : "Register"}
          </Button>
        </form>
        <p className="text-sm text-ink/70">
          Already registered? <Link className="font-semibold text-clay" href="/login">Back to login</Link>
        </p>
      </Card>
    </main>
  );
}

