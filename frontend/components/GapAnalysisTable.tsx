import type { GapAnalysis } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

export function GapAnalysisTable({ analysis }: { analysis: GapAnalysis }) {
  const colors: Record<string, string> = {
    missing: "bg-red-400/15 text-red-200",
    partial: "bg-amber-400/15 text-amber-200",
    strong: "bg-emerald-400/15 text-emerald-200",
  };
  return (
    <Card>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Skill</TableHead>
            <TableHead>Gap Type</TableHead>
            <TableHead>Confidence</TableHead>
            <TableHead>Evidence</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {analysis.skill_gaps.map((gap) => (
            <TableRow key={`${gap.skill}-${gap.gap_type}`}>
              <TableCell className="font-medium text-white">{gap.skill}</TableCell>
              <TableCell><Badge className={colors[gap.gap_type] ?? ""}>{gap.gap_type}</Badge></TableCell>
              <TableCell>{Math.round(gap.confidence * 100)}%</TableCell>
              <TableCell>{gap.evidence}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
      <details className="mt-5 rounded-2xl border border-white/10 bg-black/20 p-4">
        <summary className="cursor-pointer text-sm font-medium text-zinc-300">Reasoning trace</summary>
        <p className="mt-3 text-sm leading-6 text-zinc-400">{analysis.reasoning_trace}</p>
      </details>
    </Card>
  );
}
