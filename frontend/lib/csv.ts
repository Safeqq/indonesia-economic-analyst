export type CsvValue = string | number | boolean | null | undefined;

function escapeCsv(value: CsvValue): string {
  if (value === null || value === undefined) return "";
  const text = String(value);
  return /[",\n\r]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
}

export function toCsv(
  columns: Array<{ key: string; label: string }>,
  rows: Array<Record<string, CsvValue>>,
): string {
  const header = columns.map(({ label }) => escapeCsv(label)).join(",");
  const body = rows.map((row) =>
    columns.map(({ key }) => escapeCsv(row[key])).join(","),
  );
  return [header, ...body].join("\r\n");
}

export function downloadCsv(
  filename: string,
  columns: Array<{ key: string; label: string }>,
  rows: Array<Record<string, CsvValue>>,
): void {
  const blob = new Blob(["\uFEFF", toCsv(columns, rows)], {
    type: "text/csv;charset=utf-8",
  });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

