const numberFormatter = new Intl.NumberFormat("id-ID", {
  maximumFractionDigits: 2,
});

const compactFormatter = new Intl.NumberFormat("id-ID", {
  notation: "compact",
  maximumFractionDigits: 2,
});

const dateFormatter = new Intl.DateTimeFormat("id-ID", {
  day: "numeric",
  month: "short",
  year: "numeric",
  timeZone: "UTC",
});

const dateTimeFormatter = new Intl.DateTimeFormat("id-ID", {
  day: "numeric",
  month: "short",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  timeZone: "Asia/Jakarta",
});

const sourceNames: Record<string, string> = {
  world_bank: "World Bank",
  bps: "BPS",
  bank_indonesia: "Bank Indonesia",
};

export function formatNumber(value: number | null | undefined): string {
  return value === null || value === undefined ? "—" : numberFormatter.format(value);
}

export function formatValue(
  value: number | null | undefined,
  unit?: string | null,
  compact = false,
): string {
  if (value === null || value === undefined) return "—";
  const normalized = unit?.toLowerCase() ?? "";
  const formatted = compact ? compactFormatter.format(value) : numberFormatter.format(value);

  if (normalized.includes("percent")) return `${formatted}%`;
  if (normalized.includes("current usd")) return `US$${formatted}`;
  if (normalized.includes("idr per usd")) return `Rp${formatted}/USD`;
  if (normalized === "people") return compactFormatter.format(value);
  return formatted;
}

export function formatSigned(
  value: number | null | undefined,
  suffix = "",
): string {
  if (value === null || value === undefined) return "Belum tersedia";
  const prefix = value > 0 ? "+" : "";
  return `${prefix}${numberFormatter.format(value)}${suffix}`;
}

export function formatDate(value: string | null | undefined): string {
  return value ? dateFormatter.format(new Date(`${value.slice(0, 10)}T00:00:00Z`)) : "—";
}

export function formatDateTime(value: string | null | undefined): string {
  return value ? `${dateTimeFormatter.format(new Date(value))} WIB` : "—";
}

export function sourceName(code: string): string {
  return sourceNames[code] ?? code.replaceAll("_", " ");
}

export function frequencyName(frequency: string): string {
  const names: Record<string, string> = {
    daily: "Harian",
    monthly: "Bulanan",
    quarterly: "Triwulanan",
    annual: "Tahunan",
  };
  return names[frequency] ?? frequency;
}

export function qualityCheckName(value: string): string {
  return value
    .replace(/^check_/, "")
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

