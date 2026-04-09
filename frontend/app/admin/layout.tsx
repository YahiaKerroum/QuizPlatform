"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";

import { AdminLogoutButton } from "@/components/admin/AdminLogoutButton";
import api from "@/lib/api";
import type { AdminAccessOut } from "@/lib/types";

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
  const pathname = usePathname();
  const [checkingAccess, setCheckingAccess] = useState(true);

  useEffect(() => {
    let active = true;

    async function verifyAdminAccess() {
      try {
        await api.get<AdminAccessOut>("/auth/admin/status");
        if (active) {
          setCheckingAccess(false);
        }
      } catch {
        if (!active) return;
        router.replace("/dashboard");
      }
    }

    void verifyAdminAccess();

    return () => {
      active = false;
    };
  }, [router]);

  if (checkingAccess) {
    return (
      <main className="mx-auto max-w-6xl px-6 py-10">
        <p className="text-sm font-semibold uppercase tracking-[0.28em] text-clay">Admin</p>
        <p className="mt-4 text-sm text-ink/70">Checking admin access...</p>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-6xl px-6 py-10">
      <div className="mb-8 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div className="space-y-4">
          <p className="text-sm font-semibold uppercase tracking-[0.28em] text-clay">Admin</p>
          <h1 className="font-heading text-5xl text-ink">Manage modules, quizzes, imports, synthetic data, and exports.</h1>
        </div>
        <AdminLogoutButton />
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
      </nav>
      {children}
    </main>
  );
}
