import { ChoiceButton } from "@/components/quiz/ChoiceButton";
import { Card } from "@/components/ui/Card";
import type { QuestionOut } from "@/lib/types";

const letters = ["a", "b", "c", "d", "e", "f"] as const;

export function QuestionCard({
  question,
  selected,
  disabled,
  onSelect,
}: {
  question: QuestionOut;
  selected: string | null;
  disabled: boolean;
  onSelect: (letter: string) => void;
}) {
  const entries = letters
    .map((letter) => ({
      letter,
      text: question[`choice_${letter}` as keyof QuestionOut] as string | null,
    }))
    .filter((entry) => Boolean(entry.text));

  return (
    <Card className="space-y-6">
      <div className="space-y-3">
        <p className="text-xs font-semibold uppercase tracking-[0.28em] text-clay">Current prompt</p>
        <h2 className="font-heading text-2xl text-ink md:text-3xl">{question.question_text}</h2>
      </div>
      <div className="space-y-3">
        {entries.map((entry) => (
          <ChoiceButton
            key={entry.letter}
            letter={entry.letter}
            text={entry.text as string}
            selected={selected === entry.letter}
            disabled={disabled}
            onSelect={() => onSelect(entry.letter)}
          />
        ))}
      </div>
    </Card>
  );
}

