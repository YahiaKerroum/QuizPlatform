import { forwardRef, InputHTMLAttributes, TextareaHTMLAttributes } from "react";

export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(function Input(props, ref) {
  return (
    <input
      ref={ref}
      className="w-full rounded-3xl border border-ink/15 bg-white/82 px-4 py-3 text-sm text-ink outline-none transition duration-300 ease-out placeholder:text-ink/40 hover:border-ink/25 hover:shadow-[0_10px_20px_rgba(58,43,36,0.05)] focus:-translate-y-0.5 focus:border-clay focus:shadow-[0_16px_32px_rgba(217,111,61,0.12)]"
      {...props}
    />
  );
});

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaHTMLAttributes<HTMLTextAreaElement>>(function Textarea(
  props,
  ref,
) {
  return (
    <textarea
      ref={ref}
      className="min-h-40 w-full rounded-3xl border border-ink/15 bg-white/82 px-4 py-3 text-sm text-ink outline-none transition duration-300 ease-out placeholder:text-ink/40 hover:border-ink/25 hover:shadow-[0_10px_20px_rgba(58,43,36,0.05)] focus:-translate-y-0.5 focus:border-clay focus:shadow-[0_16px_32px_rgba(217,111,61,0.12)]"
      {...props}
    />
  );
});
