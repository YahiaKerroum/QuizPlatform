import { InputHTMLAttributes, TextareaHTMLAttributes } from "react";

export function Input(props: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className="w-full rounded-3xl border border-ink/15 bg-white/80 px-4 py-3 text-sm text-ink outline-none transition focus:border-clay"
      {...props}
    />
  );
}

export function Textarea(props: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      className="min-h-40 w-full rounded-3xl border border-ink/15 bg-white/80 px-4 py-3 text-sm text-ink outline-none transition focus:border-clay"
      {...props}
    />
  );
}

