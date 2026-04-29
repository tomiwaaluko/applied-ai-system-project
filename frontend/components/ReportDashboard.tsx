import type { CareerReport } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Tabs } from "@/components/ui/tabs";
import { GapAnalysisTable } from "@/components/GapAnalysisTable";
import { MatchScoreGauge } from "@/components/MatchScoreGauge";
import { OutreachCards } from "@/components/OutreachCards";
import { RoadmapTimeline } from "@/components/RoadmapTimeline";

export function ReportDashboard({ report }: { report: CareerReport }) {
  return (
    <div className="space-y-6">
      <Card>
        <div className="grid gap-5 md:grid-cols-[1.4fr_0.8fr_0.8fr_0.8fr]">
          <div>
            <Badge>{report.jd.industry}</Badge>
            <h1 className="mt-3 text-3xl font-semibold text-white">{report.resume.name ?? "Candidate"}</h1>
            <p className="mt-2 text-zinc-400">Target role: {report.jd.role_title}</p>
          </div>
          <MatchScoreGauge score={report.gap_analysis.match_score} />
          <div>
            <p className="text-sm text-zinc-400">Critical gaps</p>
            <p className="text-4xl font-semibold text-white">{report.gap_analysis.critical_gaps.length}</p>
          </div>
          <div>
            <p className="text-sm text-zinc-400">Confidence</p>
            <p className="text-4xl font-semibold text-white">{Math.round(report.gap_analysis.confidence * 100)}%</p>
          </div>
        </div>
      </Card>
      <Tabs
        tabs={[
          { value: "gaps", label: "Gap Analysis", content: <GapAnalysisTable analysis={report.gap_analysis} /> },
          { value: "roadmap", label: "Roadmap", content: <RoadmapTimeline roadmap={report.roadmap} /> },
          { value: "outreach", label: "Outreach", content: <OutreachCards outreach={report.outreach} /> },
        ]}
      />
    </div>
  );
}
