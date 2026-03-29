import { ExportButton } from "@/components/admin/ExportButton";
import { Card } from "@/components/ui/Card";

export default function AdminExportPage() {
  return (
    <Card className="space-y-5">
      <h2 className="font-heading text-3xl text-ink">Export dataset</h2>
      <p className="text-sm text-ink/70">
        Download the full answers dataset as a CSV stream for the ML workflow.
      </p>
      <ExportButton />
    </Card>
  );
}
