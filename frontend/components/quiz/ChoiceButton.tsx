export function ChoiceButton({
  letter,
  text,
  selected,
  disabled,
  onSelect,
}: {
  letter: string;
  text: string;
  selected: boolean;
  disabled: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onSelect}
      disabled={disabled}
      className={`flex w-full items-start gap-4 rounded-[1.75rem] border px-5 py-4 text-left transition ${
        selected
          ? "border-clay bg-clay text-white"
          : "border-ink/10 bg-white/85 text-ink hover:border-clay/40 hover:bg-white"
      } disabled:cursor-not-allowed disabled:opacity-70`}
    >
      <span className={`mt-0.5 inline-flex h-8 w-8 items-center justify-center rounded-full text-xs font-semibold ${selected ? "bg-white/20" : "bg-ink/8"}`}>
        {letter.toUpperCase()}
      </span>
      <span className="text-base leading-7">{text}</span>
    </button>
  );
}

