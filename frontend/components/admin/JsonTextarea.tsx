"use client";

import { useMemo } from "react";

import { Textarea } from "@/components/ui/Input";

export function JsonTextarea({
  value,
  onChange,
  placeholder,
}: {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
}) {
  const validationMessage = useMemo(() => {
    if (!value.trim()) return "Paste JSON to validate it before sending.";
    try {
      JSON.parse(value);
      return "Valid JSON.";
    } catch (error) {
      return error instanceof Error ? error.message : "Invalid JSON.";
    }
  }, [value]);

  return (
    <div className="space-y-3">
      <Textarea value={value} onChange={(event) => onChange(event.target.value)} placeholder={placeholder} />
      <p className="text-sm text-ink/70">{validationMessage}</p>
    </div>
  );
}

