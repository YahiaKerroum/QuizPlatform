type Segment =
  | { type: "text"; value: string }
  | { type: "code"; value: string };

const CODE_MARKERS = [
  "#include",
  "int main",
  "printf(",
  "scanf(",
  "for (",
  "while (",
  "if (",
  "switch (",
  "enum {",
  "return ",
  "{",
  "};",
] as const;

function normalizeText(value: string) {
  return value.replace(/\r\n?/g, "\n").trim();
}

function looksLikeCode(value: string) {
  const score = CODE_MARKERS.reduce(
    (total, marker) => total + (value.includes(marker) ? 1 : 0),
    0,
  );
  return (
    score >= 2 ||
    (/[{};]/.test(value) &&
      /(#include|return|printf|scanf|\bint\b|\bchar\b|\bfloat\b|\bdouble\b|\bfor\b|\bwhile\b|\bif\b|=)/.test(value))
  );
}

function findCodeStart(value: string) {
  const markers = ["#include", "int main", "for (", "while (", "if (", "switch (", "enum {", "printf(", "scanf("];
  const indexes = markers
    .map((marker) => value.indexOf(marker))
    .filter((index) => index >= 0);
  if (indexes.length === 0) return -1;
  return Math.min(...indexes);
}

function formatInlineCode(value: string) {
  if (value.includes("\n")) {
    return value;
  }

  return value
    .replace(/\s*(#include\b)/g, "\n$1")
    .replace(/\s*{\s*/g, " {\n")
    .replace(/\s*}\s*/g, "\n}\n")
    .replace(/;\s+/g, ";\n")
    .replace(/\s+else\s+/g, "\nelse ")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

function parseFencedCode(value: string): Segment[] {
  const parts = value.split("```");
  return parts
    .map((part, index) => {
      const trimmed = part.trim();
      if (!trimmed) return null;
      if (index % 2 === 1) {
        return {
          type: "code" as const,
          value: trimmed.replace(/^[a-zA-Z0-9_-]+\n/, ""),
        };
      }
      return { type: "text" as const, value: trimmed };
    })
    .filter((segment): segment is Segment => segment !== null);
}

function parseSegments(value: string): Segment[] {
  const normalized = normalizeText(value);
  if (!normalized) return [];

  if (normalized.includes("```")) {
    return parseFencedCode(normalized);
  }

  const codeStart = findCodeStart(normalized);
  if (codeStart > 0) {
    const intro = normalized.slice(0, codeStart).trim();
    const code = normalized.slice(codeStart).trim();

    if (intro && looksLikeCode(code)) {
      return [
        { type: "text", value: intro },
        { type: "code", value: formatInlineCode(code) },
      ];
    }
  }

  if (looksLikeCode(normalized)) {
    return [{ type: "code", value: formatInlineCode(normalized) }];
  }

  return [{ type: "text", value: normalized }];
}

export function RichContent({
  text,
  imageUrl,
  imageAlt,
  inverted = false,
  compact = false,
}: {
  text: string | null | undefined;
  imageUrl?: string | null;
  imageAlt: string;
  inverted?: boolean;
  compact?: boolean;
}) {
  const segments = text ? parseSegments(text) : [];
  const codeClassName = inverted
    ? "border-white/20 bg-white/10 text-white"
    : "border-ink/10 bg-ink/5 text-ink";
  const textClassName = inverted ? "text-white" : "text-ink";
  const imageClassName = compact
    ? "max-h-40 w-auto rounded-2xl border border-ink/10 object-contain"
    : "max-h-80 w-auto rounded-[1.5rem] border border-ink/10 object-contain";

  if (segments.length === 0 && !imageUrl) {
    return null;
  }

  return (
    <div className={compact ? "space-y-2" : "space-y-4"}>
      {segments.map((segment, index) =>
        segment.type === "code" ? (
          <pre
            key={`${segment.type}-${index}`}
            className={`overflow-x-auto rounded-2xl border px-4 py-3 font-mono text-sm leading-6 whitespace-pre-wrap ${codeClassName}`}
          >
            <code>{segment.value}</code>
          </pre>
        ) : (
          <p
            key={`${segment.type}-${index}`}
            className={`whitespace-pre-wrap ${compact ? "text-sm leading-6" : "text-base leading-7"} ${textClassName}`}
          >
            {segment.value}
          </p>
        ),
      )}
      {imageUrl ? (
        <img
          src={imageUrl}
          alt={imageAlt}
          loading="lazy"
          className={imageClassName}
        />
      ) : null}
    </div>
  );
}
