"use client";

import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/Button";
import { clearToken } from "@/lib/auth";

export function LogoutButton({ className = "" }: { className?: string }) {
  const router = useRouter();

  function handleLogout() {
    clearToken();
    router.replace("/login");
  }

  return (
    <Button className={className} variant="ghost" onClick={handleLogout}>
      Log out
    </Button>
  );
}
