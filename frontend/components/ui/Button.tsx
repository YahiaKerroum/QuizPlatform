import { ButtonHTMLAttributes } from "react";

type ButtonVariant = "primary" | "secondary" | "ghost";

const styles: Record<ButtonVariant, string> = {
  primary: "bg-ink text-sand hover:bg-black",
  secondary: "bg-clay text-white hover:bg-[#be5d2f]",
  ghost: "border border-ink/20 bg-transparent text-ink hover:bg-ink/5",
};

export function Button({
  className = "",
  variant = "primary",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: ButtonVariant }) {
  return (
    <button
      className={`rounded-full px-5 py-3 text-sm font-semibold transition disabled:cursor-not-allowed disabled:opacity-60 ${styles[variant]} ${className}`}
      {...props}
    />
  );
}

