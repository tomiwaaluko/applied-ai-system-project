"use client";

import { CheckCircle2, Circle, Loader2, XCircle } from "lucide-react";
import type { ProgressEvent } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";

const steps = [
  { step: 1, agent: "parser", label: "Parse resume + JD" },
  { step: 2, agent: "retriever", label: "Retrieve role context" },
  { step: 3, agent: "gap_analyzer", label: "Analyze gaps" },
  { step: 4, agent: "roadmap_outreach", label: "Build roadmap + outreach" },
  { step: 5, agent: "report_writer", label: "Write report" },
];

export function ProgressTracker({ events }: { events: ProgressEvent[] }) {
  const latest = events.at(-1);
  const completed = new Set(events.filter((event) => event.status === "done").map((event) => event.step));
  const hasError = latest?.status === "error";
  const activeStep = hasError ? latest?.step : Math.min((latest?.step ?? 0) + 1, 5);

  return (
    <Card>
      <div className="mb-5 flex items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-semibold text-white">Analysis progress</h2>
          <p className="text-sm text-zinc-400">{latest?.message ?? "Waiting to start."}</p>
        </div>
        <Badge>{completed.size}/5 done</Badge>
      </div>
      <Progress value={(completed.size / 5) * 100} className="mb-5" />
      <div className="space-y-3">
        {steps.map((item) => {
          const event = events.find((candidate) => candidate.step === item.step && candidate.agent !== "complete");
          const done = completed.has(item.step);
          const active = activeStep === item.step && !done && !hasError;
          const error = hasError && latest?.step === item.step;
          return (
            <div key={item.step} className="flex items-center gap-3 rounded-2xl border border-white/10 bg-white/[0.03] p-3">
              {done ? <CheckCircle2 className="text-emerald-300" /> : error ? <XCircle className="text-red-300" /> : active ? <Loader2 className="animate-spin text-emerald-300" /> : <Circle className="text-zinc-600" />}
              <div className="flex-1">
                <p className="font-medium text-white">{item.label}</p>
                <p className="text-xs text-zinc-500">{event ? `${event.elapsed_seconds.toFixed(1)}s` : "Waiting"}</p>
              </div>
              <Badge className={done ? "bg-emerald-400/15 text-emerald-200" : error ? "bg-red-400/15 text-red-200" : ""}>
                {done ? "Done" : error ? "Error" : active ? "Running" : "Waiting"}
              </Badge>
            </div>
          );
        })}
      </div>
    </Card>
  );
}
