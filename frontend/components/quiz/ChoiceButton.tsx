import { RichContent } from "@/components/content/RichContent";

export function ChoiceButton({
  letter,
  text,
  imageUrl,
  selected,
  disabled,
  onSelect,
}: {
  letter: string;
  text: string;
  imageUrl: string | null;
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
      <div className="min-w-0 flex-1">
        <RichContent
          text={text}
          imageUrl={imageUrl}
          imageAlt={`Choice ${letter.toUpperCase()}`}
          inverted={selected}
          compact
        />
      </div>
    </button>
  );
}
