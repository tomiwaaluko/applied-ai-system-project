import { Progress } from "@/components/ui/progress";

export function MatchScoreGauge({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  const color = pct < 40 ? "text-red-300" : pct < 60 ? "text-amber-300" : "text-emerald-300";
  return (
    <div>
      <div className={`mb-2 text-4xl font-semibold ${color}`}>{pct}%</div>
      <Progress value={pct} />
    </div>
  );
}
