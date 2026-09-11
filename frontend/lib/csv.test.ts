import { describe, expect, it } from "vitest";

import { toCsv } from "@/lib/csv";

describe("toCsv", () => {
  it("menjaga urutan kolom dan meng-escape koma, kutip, serta nilai kosong", () => {
    const csv = toCsv(
      [
        { key: "name", label: "Nama wilayah" },
        { key: "note", label: "Catatan" },
        { key: "value", label: "Nilai" },
      ],
      [{ name: "Jakarta, DKI", note: 'Data "resmi"', value: null }],
    );

    expect(csv).toBe(
      'Nama wilayah,Catatan,Nilai\r\n"Jakarta, DKI","Data ""resmi""",',
    );
  });
});

