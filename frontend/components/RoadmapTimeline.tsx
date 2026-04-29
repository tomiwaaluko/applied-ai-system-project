import type { Roadmap, RoadmapItem } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";

function Column({ title, items }: { title: string; items: RoadmapItem[] }) {
  return (
    <div>
      <h3 className="mb-3 text-lg font-semibold text-white">{title}</h3>
      <div className="space-y-3">
        {items.map((item, index) => (
          <Card key={`${item.timeframe}-${index}`} className="p-4">
            <label className="flex gap-3">
              <input type="checkbox" className="mt-1 h-4 w-4 accent-emerald-400" />
              <span>
                <span className="block font-medium text-white">{item.action}</span>
                <span className="mt-2 block text-sm text-zinc-400">{item.rationale}</span>
                <span className="mt-2 block text-xs text-emerald-200">{item.resource ?? "Resource TBD"}</span>
              </span>
            </label>
          </Card>
        ))}
      </div>
    </div>
  );
}

export function RoadmapTimeline({ roadmap }: { roadmap: Roadmap }) {
  return (
    <div className="space-y-6">
      <div className="grid gap-4 lg:grid-cols-3">
        <Column title="30 Days" items={roadmap.thirty_day} />
        <Column title="60 Days" items={roadmap.sixty_day} />
        <Column title="90 Days" items={roadmap.ninety_day} />
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        {roadmap.project_ideas.map((project, index) => {
          const skills = (project.skills_addressed ?? project.critical_gaps_addressed ?? []) as string[];
          return (
            <Card key={String(project.title ?? index)}>
              <h3 className="text-lg font-semibold text-white">{String(project.title ?? "Project idea")}</h3>
              <p className="mt-2 text-sm leading-6 text-zinc-400">{String(project.description ?? "")}</p>
              <div className="mt-4 flex flex-wrap gap-2">{skills.map((skill) => <Badge key={skill}>{skill}</Badge>)}</div>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
