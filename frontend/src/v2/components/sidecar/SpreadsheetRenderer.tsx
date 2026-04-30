import { ArrowDownIcon, ArrowUpIcon, ChevronsUpDownIcon } from "lucide-react";
import { useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface SpreadsheetRendererProps {
  body: string;
  className?: string;
}

interface SortState {
  column: string;
  direction: "asc" | "desc";
}

type Row = Record<string, string>;

export function SpreadsheetRenderer({ body, className }: SpreadsheetRendererProps) {
  const [sort, setSort] = useState<SortState | null>(null);
  const rows = useMemo(() => parseRows(body), [body]);
  const columns = useMemo(() => collectColumns(rows), [rows]);
  const sortedRows = useMemo(() => sortRows(rows, sort), [rows, sort]);

  if (rows.length === 0 || columns.length === 0) {
    return (
      <div
        className={cn(
          "flex h-full items-center justify-center text-muted-foreground text-sm",
          className,
        )}
        data-testid="spreadsheet-renderer"
      >
        No rows to display.
      </div>
    );
  }

  const toggleSort = (column: string) => {
    setSort((current) => {
      if (current?.column !== column) return { column, direction: "asc" };
      if (current.direction === "asc") return { column, direction: "desc" };
      return null;
    });
  };

  return (
    <div className={cn("h-full overflow-auto", className)} data-testid="spreadsheet-renderer">
      <table className="min-w-full border-collapse text-left text-sm">
        <thead className="sticky top-0 z-10 bg-background">
          <tr>
            {columns.map((column) => (
              <th
                className="border-border border-b bg-muted px-2 py-2 font-semibold"
                key={column}
                scope="col"
              >
                <Button
                  className="h-auto min-h-0 max-w-full justify-start gap-1 px-1 py-0 text-left text-xs"
                  onClick={() => toggleSort(column)}
                  type="button"
                  variant="ghost"
                >
                  <span className="truncate">{column}</span>
                  <SortIcon active={sort?.column === column} direction={sort?.direction} />
                </Button>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sortedRows.map((row, rowIndex) => (
            <tr className="odd:bg-card even:bg-muted/30" key={`${rowIndex}-${columns[0]}`}>
              {columns.map((column) => (
                <td className="border-border border-b px-3 py-2 align-top" key={column}>
                  {row[column] ?? ""}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function SortIcon({
  active,
  direction,
}: {
  active: boolean;
  direction?: "asc" | "desc";
}) {
  if (!active) return <ChevronsUpDownIcon aria-hidden className="size-3" />;
  if (direction === "desc") return <ArrowDownIcon aria-hidden className="size-3" />;
  return <ArrowUpIcon aria-hidden className="size-3" />;
}

function parseRows(body: string): Row[] {
  try {
    const delimiter = body.includes("\t") ? "\t" : ",";
    const [headerRow, ...dataRows] = parseDelimitedRows(body, delimiter).filter((row) =>
      row.some((cell) => cell.trim()),
    );
    if (!headerRow) return [];

    const headers = headerRow.map((header) => header.trim());
    return dataRows.map((row) =>
      Object.fromEntries(
        headers.map((header, index) => [header, row[index]?.trim() ?? ""]),
      ),
    );
  } catch {
    return [];
  }
}

function parseDelimitedRows(body: string, delimiter: string): string[][] {
  const rows: string[][] = [];
  let row: string[] = [];
  let cell = "";
  let inQuotes = false;

  for (let index = 0; index < body.length; index += 1) {
    const char = body[index];
    const nextChar = body[index + 1];

    if (char === '"' && inQuotes && nextChar === '"') {
      cell += '"';
      index += 1;
      continue;
    }

    if (char === '"') {
      inQuotes = !inQuotes;
      continue;
    }

    if (char === delimiter && !inQuotes) {
      row.push(cell);
      cell = "";
      continue;
    }

    if ((char === "\n" || char === "\r") && !inQuotes) {
      if (char === "\r" && nextChar === "\n") index += 1;
      row.push(cell);
      rows.push(row);
      row = [];
      cell = "";
      continue;
    }

    cell += char;
  }

  row.push(cell);
  rows.push(row);
  return rows;
}

function collectColumns(rows: Row[]): string[] {
  const seen = new Set<string>();
  for (const row of rows) {
    for (const column of Object.keys(row)) {
      seen.add(column);
    }
  }
  return [...seen];
}

function sortRows(rows: Row[], sort: SortState | null): Row[] {
  if (!sort) return rows;
  return [...rows].sort((left, right) => {
    const leftValue = left[sort.column] ?? "";
    const rightValue = right[sort.column] ?? "";
    return compareValues(leftValue, rightValue) * (sort.direction === "asc" ? 1 : -1);
  });
}

function compareValues(left: string, right: string): number {
  const leftNumber = Number(left);
  const rightNumber = Number(right);
  if (Number.isFinite(leftNumber) && Number.isFinite(rightNumber)) {
    return leftNumber - rightNumber;
  }
  return left.localeCompare(right, undefined, { numeric: true, sensitivity: "base" });
}
