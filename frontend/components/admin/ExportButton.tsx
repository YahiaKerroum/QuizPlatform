"use client";

import { Button } from "@/components/ui/Button";

export function ExportButton() {
  return (
    <Button
      variant="secondary"
      onClick={() => {
        window.location.href = `${process.env.NEXT_PUBLIC_API_URL}/admin/export/answers`;
      }}
    >
      Download dataset CSV
    </Button>
  );
}

