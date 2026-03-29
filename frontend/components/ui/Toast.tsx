export function Toast({
  message,
  tone = "info",
}: {
  message: string;
  tone?: "info" | "success" | "error";
}) {
  const classes =
    tone === "success"
      ? "border-pine/30 bg-pine/10 text-pine"
      : tone === "error"
        ? "border-red-300 bg-red-50 text-red-700"
        : "border-ink/15 bg-white/80 text-ink";

  return <div className={`motion-rise rounded-3xl border px-4 py-3 text-sm shadow-[0_16px_30px_rgba(58,43,36,0.08)] ${classes}`}>{message}</div>;
}
