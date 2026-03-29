"use client";

import { useState } from "react";

import { JsonTextarea } from "@/components/admin/JsonTextarea";
import { SimulationForm } from "@/components/admin/SimulationForm";
import { Card } from "@/components/ui/Card";
import { Toast } from "@/components/ui/Toast";
import api from "@/lib/api";
import type { SimBatchOut } from "@/lib/types";

export default function AdminSimulatePage() {
  const [value, setValue] = useState('{\n  "students": []\n}');
  const [result, setResult] = useState<SimBatchOut | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function submitSimulation() {
    setLoading(true);
    setMessage(null);

    try {
      const parsed = JSON.parse(value);
      const { data } = await api.post<SimBatchOut>("/admin/simulate/batch", parsed);
      setResult(data);
      setMessage("Simulation completed.");
    } catch {
      setMessage("Simulation failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="space-y-6">
      <Card className="space-y-5">
        <h2 className="font-heading text-3xl text-ink">Run batch simulation</h2>
        <JsonTextarea value={value} onChange={setValue} />
        <SimulationForm disabled={loading} onSubmit={() => void submitSimulation()} />
      </Card>
      {message ? <Toast message={message} tone={message.includes("failed") ? "error" : "success"} /> : null}
      {result ? (
        <Card className="space-y-2">
          <p>Sessions created: {result.sessions_created}</p>
          <p>Answers inserted: {result.answers_inserted}</p>
          <p>Errors: {result.errors.length}</p>
        </Card>
      ) : null}
    </section>
  );
}

