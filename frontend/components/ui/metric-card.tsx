import { ArrowDownRight, ArrowUpRight, Minus } from "lucide-react";

interface MetricCardProps {
  label: string;
  value: string;
  change?: string;
  changeValue?: number | null;
  period: string;
  source: string;
  tone?: "teal" | "amber" | "violet" | "blue";
}

export function MetricCard({
  label,
  value,
  change,
  changeValue,
  period,
  source,
  tone = "teal",
}: MetricCardProps) {
  const ChangeIcon =
    changeValue === null || changeValue === undefined || changeValue === 0
      ? Minus
      : changeValue > 0
        ? ArrowUpRight
        : ArrowDownRight;

  return (
    <article className={`metric-card metric-${tone}`}>
      <div className="metric-topline"><span>{label}</span><i /></div>
      <strong className="metric-value">{value}</strong>
      <div className="metric-detail">
        <span
          className={
            change === undefined
              ? "change-neutral"
              : changeValue && changeValue < 0
                ? "change-down"
                : "change-up"
          }
        >
          {change === undefined ? null : <ChangeIcon size={15} />}
          {change ?? "Snapshot terpilih"}
        </span>
        <span>{period}</span>
      </div>
      <div className="metric-source">Sumber: {source}</div>
    </article>
  );
}
