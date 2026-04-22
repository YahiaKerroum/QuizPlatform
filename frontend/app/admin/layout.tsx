"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { LogoutButton } from "@/components/auth/LogoutButton";
import { Toast } from "@/components/ui/Toast";
import api from "@/lib/api";
import type { AuthMeOut } from "@/lib/types";

const links = [
  { href: "/admin/catalog", label: "Catalog" },
  { href: "/admin/import", label: "Import" },
  { href: "/admin/students", label: "Students" },
  { href: "/admin/simulate", label: "Simulate" },
  { href: "/admin/difficulty", label: "Difficulty" },
  { href: "/admin/export", label: "Export" },
];

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [checkingAccess, setCheckingAccess] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function checkAccess() {
      try {
        const { data } = await api.get<AuthMeOut>("/auth/me");
        if (!data.is_admin) {
          router.replace("/dashboard");
          return;
        }
      } catch {
        setError("Could not verify admin access.");
      } finally {
        setCheckingAccess(false);
      }
    }

    void checkAccess();
  }, [router]);

  if (checkingAccess) {
    return (
      <main className="mx-auto max-w-6xl px-6 py-10">
        <p className="text-sm text-ink/70">Checking admin access...</p>
      </main>
    );
  }

  if (error) {
    return (
      <main className="mx-auto max-w-6xl px-6 py-10">
        <Toast message={error} tone="error" />
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-6xl px-6 py-10">
      <div className="mb-8 space-y-4">
        <p className="text-sm font-semibold uppercase tracking-[0.28em] text-clay">Admin</p>
        <h1 className="font-heading text-5xl text-ink">Manage modules, quizzes, imports, synthetic data, and exports.</h1>
      </div>
      <nav className="mb-8 flex flex-wrap gap-3">
        {links.map((link) => (
          <Link
            key={link.href}
            href={link.href}
            className="rounded-full border border-ink/10 bg-white/70 px-4 py-2 text-sm font-semibold text-ink transition hover:border-clay"
          >
            {link.label}
          </Link>
        ))}
        <LogoutButton className="ml-auto" />
      </nav>
      <p className="mb-6 text-xs text-ink/65">Admin access is role-based and controlled from profile roles.</p>
      {children}
    </main>
  );
}
