export function QuizTimer({ elapsed }: { elapsed: number }) {
  const minutes = String(Math.floor(elapsed / 60)).padStart(2, "0");
  const seconds = String(elapsed % 60).padStart(2, "0");

  return (
    <div className="rounded-full border border-ink/10 bg-white/70 px-4 py-2 text-sm font-semibold text-ink">
      {minutes}:{seconds}
    </div>
  );
}

