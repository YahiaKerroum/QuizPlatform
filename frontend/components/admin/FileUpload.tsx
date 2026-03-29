export function FileUpload({
  file,
  onChange,
}: {
  file: File | null;
  onChange: (file: File | null) => void;
}) {
  return (
    <label className="flex cursor-pointer flex-col items-center justify-center rounded-[2rem] border border-dashed border-ink/20 bg-white/70 px-6 py-10 text-center">
      <span className="font-heading text-xl text-ink">Drop a CSV or JSON file here</span>
      <span className="mt-2 text-sm text-ink/65">or click to choose a file from your machine</span>
      <span className="mt-3 text-sm font-semibold text-clay">
        {file ? `Selected: ${file.name}` : "No file selected yet"}
      </span>
      <input
        type="file"
        accept=".csv,.json,application/json,text/csv"
        className="hidden"
        onChange={(event) => onChange(event.target.files?.[0] ?? null)}
      />
    </label>
  );
}
