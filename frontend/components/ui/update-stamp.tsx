import { Clock3 } from "lucide-react";

import { formatDateTime } from "@/lib/format";

export function UpdateStamp({ value }: { value: string | null | undefined }) {
  return (
    <span className="update-stamp">
      <Clock3 size={14} /> Diperbarui {formatDateTime(value)}
    </span>
  );
}

