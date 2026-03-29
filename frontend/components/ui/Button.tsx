import { ButtonHTMLAttributes } from "react";

type ButtonVariant = "primary" | "secondary" | "ghost";

const styles: Record<ButtonVariant, string> = {
  primary:
    "bg-ink text-sand shadow-[0_12px_28px_rgba(58,43,36,0.22)] hover:-translate-y-0.5 hover:bg-black hover:shadow-[0_18px_36px_rgba(58,43,36,0.28)]",
  secondary:
    "bg-clay text-white shadow-[0_14px_32px_rgba(217,111,61,0.28)] hover:-translate-y-0.5 hover:bg-[#be5d2f] hover:shadow-[0_20px_38px_rgba(217,111,61,0.32)]",
  ghost:
    "border border-ink/20 bg-transparent text-ink hover:-translate-y-0.5 hover:bg-ink/5 hover:shadow-[0_10px_20px_rgba(58,43,36,0.08)]",
};

export function Button({
  className = "",
  variant = "primary",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: ButtonVariant }) {
  return (
    <button
      className={`surface-sheen rounded-full px-5 py-3 text-sm font-semibold transition duration-300 ease-out disabled:cursor-not-allowed disabled:opacity-60 disabled:hover:translate-y-0 ${styles[variant]} ${className}`}
      {...props}
    />
  );
}
