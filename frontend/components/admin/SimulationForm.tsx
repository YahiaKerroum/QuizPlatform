import { Button } from "@/components/ui/Button";

export function SimulationForm({
  disabled,
  onSubmit,
}: {
  disabled: boolean;
  onSubmit: () => void;
}) {
  return (
    <Button variant="secondary" disabled={disabled} onClick={onSubmit}>
      {disabled ? "Running..." : "Run batch simulation"}
    </Button>
  );
}

