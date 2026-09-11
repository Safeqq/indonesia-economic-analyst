"use client";

import { Download } from "lucide-react";

export function ExportButton({
  onClick,
  disabled = false,
  label = "Export CSV",
}: {
  onClick: () => void;
  disabled?: boolean;
  label?: string;
}) {
  return (
    <button
      className="button button-secondary"
      type="button"
      onClick={onClick}
      disabled={disabled}
    >
      <Download size={16} /> {label}
    </button>
  );
}

