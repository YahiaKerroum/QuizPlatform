import { Button } from "@/components/ui/Button";

type SimulationFormProps = {
  disabled: boolean;
  onSubmit: () => void;
  error?: string | null;
};

export function SimulationForm({ disabled, onSubmit, error }: SimulationFormProps) {
  return (
    <div className="space-y-3">
      <Button variant="secondary" disabled={disabled} onClick={onSubmit}>
        {disabled ? "Running..." : "Run batch simulation"}
      </Button>
      {error ? <p className="text-sm text-red-700">{error}</p> : null}
    </div>
  );
}
