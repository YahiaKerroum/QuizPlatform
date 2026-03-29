"use client";

import { useState } from "react";

import { JsonTextarea } from "@/components/admin/JsonTextarea";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Toast } from "@/components/ui/Toast";
import api from "@/lib/api";
import type { DifficultyOut } from "@/lib/types";

export default function AdminDifficultyPage() {
  const [value, setValue] = useState('{\n  "updates": []\n}');
  const [message, setMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function submitDifficultyUpdates() {
    setLoading(true);
    setMessage(null);

    try {
      const parsed = JSON.parse(value);
      const { data } = await api.post<DifficultyOut>("/admin/questions/difficulty", parsed);
      setMessage(`Updated ${data.updated} questions.`);
    } catch {
      setMessage("Difficulty update failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="space-y-6">
      <Card className="space-y-5">
        <h2 className="font-heading text-3xl text-ink">Set question difficulty</h2>
        <JsonTextarea value={value} onChange={setValue} />
        <Button variant="secondary" disabled={loading} onClick={() => void submitDifficultyUpdates()}>
          {loading ? "Updating..." : "Submit difficulty updates"}
        </Button>
      </Card>
      {message ? <Toast message={message} tone={message.includes("failed") ? "error" : "success"} /> : null}
    </section>
  );
}

