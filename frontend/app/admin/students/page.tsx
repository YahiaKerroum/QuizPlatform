"use client";

import { useState } from "react";

import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Textarea } from "@/components/ui/Input";
import { Toast } from "@/components/ui/Toast";
import api from "@/lib/api";
import type { SyntheticStudentOut } from "@/lib/types";

export default function AdminStudentsPage() {
  const [value, setValue] = useState("");
  const [students, setStudents] = useState<SyntheticStudentOut[]>([]);
  const [message, setMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function submitStudents() {
    const emails = value
      .split(/\r?\n/)
      .map((entry) => entry.trim())
      .filter(Boolean);

    if (emails.length === 0) return;

    setLoading(true);
    setMessage(null);

    try {
      const { data } = await api.post<SyntheticStudentOut[]>("/admin/students/synthetic/bulk", {
        students: emails.map((email) => ({ email })),
      });
      setStudents(data);
      setMessage(`Created ${data.length} synthetic students.`);
    } catch {
      setMessage("Could not create synthetic students.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="space-y-6">
      <Card className="space-y-5">
        <h2 className="font-heading text-3xl text-ink">Bulk synthetic students</h2>
        <Textarea
          placeholder={"sim_001@sim.local\nsim_002@sim.local"}
          value={value}
          onChange={(event) => setValue(event.target.value)}
        />
        <Button variant="secondary" disabled={loading} onClick={() => void submitStudents()}>
          {loading ? "Creating..." : "Create students"}
        </Button>
      </Card>
      {message ? <Toast message={message} tone={message.includes("Could not") ? "error" : "success"} /> : null}
      {students.length > 0 ? (
        <Card className="overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead>
              <tr className="text-ink/65">
                <th className="pb-3">Email</th>
                <th className="pb-3">UUID</th>
              </tr>
            </thead>
            <tbody>
              {students.map((student) => (
                <tr key={student.id} className="border-t border-ink/10">
                  <td className="py-3">{student.email}</td>
                  <td className="py-3">{student.id}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      ) : null}
    </section>
  );
}

