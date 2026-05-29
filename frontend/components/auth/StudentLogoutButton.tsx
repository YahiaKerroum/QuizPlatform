"use client";

import { useRouter } from "next/navigation";

import { clearToken } from "@/lib/auth";

export function StudentLogoutButton() {
  const router = useRouter();

  return (
    <button
      type="button"
      className="rounded-full border border-ink/10 bg-white/70 px-4 py-2 text-sm font-semibold text-ink transition hover:border-clay"
      onClick={() => {
        clearToken();
        router.push("/login");
        router.refresh();
      }}
    >
      Logout
    </button>
  );
}
