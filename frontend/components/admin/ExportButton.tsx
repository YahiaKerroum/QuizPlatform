"use client";

import { useState } from "react";

import { Button } from "@/components/ui/Button";

export function ExportButton() {
  const [loading, setLoading] = useState(false);

  async function handleDownload() {
    const baseUrl = process.env.NEXT_PUBLIC_API_URL;
    if (!baseUrl) {
      return;
    }

    setLoading(true);

    try {
      const response = await fetch(`${baseUrl}/admin/export/answers`);
      if (!response.ok) {
        throw new Error("Export failed.");
      }

      const blob = await response.blob();
      const downloadUrl = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = downloadUrl;
      link.download = "responses.csv";
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(downloadUrl);
    } finally {
      setLoading(false);
    }
  }

  return (
    <Button variant="secondary" disabled={loading} onClick={() => void handleDownload()}>
      {loading ? "Preparing CSV..." : "Download dataset CSV"}
    </Button>
  );
}
