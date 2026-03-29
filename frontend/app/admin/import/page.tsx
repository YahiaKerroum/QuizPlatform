"use client";

import { useState } from "react";

import { FileUpload } from "@/components/admin/FileUpload";
import { JsonTextarea } from "@/components/admin/JsonTextarea";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Toast } from "@/components/ui/Toast";
import api from "@/lib/api";
import type { ImportOut } from "@/lib/types";

export default function AdminImportPage() {
  const [file, setFile] = useState<File | null>(null);
  const [jsonText, setJsonText] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  function summarizeError(error: unknown) {
    if (typeof error === "object" && error && "response" in error) {
      const detail = (error as { response?: { data?: { detail?: unknown } } }).response?.data?.detail;
      if (typeof detail === "string") {
        return detail;
      }
    }
    return "Import failed.";
  }

  async function uploadForm(form: FormData) {
    setLoading(true);
    setMessage(null);

    try {
      const { data } = await api.post<ImportOut>("/admin/import", form, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setMessage(
        `Created ${data.quizzes_created} quizzes. Inserted ${data.questions_inserted} questions. Skipped ${data.questions_skipped} duplicates.`,
      );
      setFile(null);
      setJsonText("");
    } catch (error) {
      setMessage(summarizeError(error));
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="grid gap-6">
      <Card className="space-y-5">
        <h2 className="font-heading text-3xl text-ink">Import file</h2>
        <FileUpload file={file} onChange={setFile} />
        <Button
          variant="secondary"
          disabled={!file || loading}
          onClick={() => {
            if (!file) return;
            const form = new FormData();
            form.append("file", file);
            void uploadForm(form);
          }}
        >
          {loading ? "Uploading..." : "Upload file"}
        </Button>
      </Card>
      <Card className="space-y-5">
        <h2 className="font-heading text-3xl text-ink">Paste JSON</h2>
        <JsonTextarea value={jsonText} onChange={setJsonText} placeholder='[{"quiz_id":"c-interview", ...}]' />
        <Button
          variant="secondary"
          disabled={loading || !jsonText.trim()}
          onClick={() => {
            const blob = new Blob([jsonText], { type: "application/json" });
            const form = new FormData();
            form.append("file", blob, "import.json");
            void uploadForm(form);
          }}
        >
          {loading ? "Uploading..." : "Submit JSON"}
        </Button>
      </Card>
      {message ? <Toast message={message} tone={message.toLowerCase().includes("failed") ? "error" : "success"} /> : null}
    </section>
  );
}
