"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { FileText, UploadCloud } from "lucide-react";
import { streamAnalysis } from "@/lib/api";
import type { ProgressEvent } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ProgressTracker } from "@/components/ProgressTracker";

export function UploadForm() {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [jdText, setJdText] = useState("");
  const [jdUrl, setJdUrl] = useState("");
  const [mode, setMode] = useState<"text" | "url">("text");
  const [events, setEvents] = useState<ProgressEvent[]>([]);
  const [error, setError] = useState("");
  const [running, setRunning] = useState(false);
  const invalidFile = Boolean(file && file.type !== "application/pdf");
  const jdInput = mode === "text" ? jdText : jdUrl;
  const canSubmit = Boolean(file && jdInput.trim() && !invalidFile && !running);

  async function onSubmit() {
    if (!file || !canSubmit) return;
    setRunning(true);
    setError("");
    setEvents([]);
    try {
      const reportId = await streamAnalysis(file, jdInput, (event) => {
        setEvents((current) => [...current, event]);
      });
      if (reportId) router.push(`/report/${reportId}`);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Analysis failed");
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_0.9fr]">
      <Card>
        <CardHeader>
          <CardTitle>Resume PDF</CardTitle>
          <p className="text-sm text-zinc-400">Upload the resume you want to evaluate against the target role.</p>
        </CardHeader>
        <CardContent>
          <label className={`flex min-h-72 cursor-pointer flex-col items-center justify-center rounded-3xl border-2 border-dashed p-8 text-center transition ${invalidFile ? "border-red-400 bg-red-950/20" : "border-emerald-300/40 bg-emerald-400/5 hover:bg-emerald-400/10"}`}>
            <input className="hidden" type="file" accept="application/pdf" onChange={(event) => setFile(event.target.files?.[0] ?? null)} />
            {file ? <FileText className="mb-4 h-12 w-12 text-emerald-300" /> : <UploadCloud className="mb-4 h-12 w-12 text-emerald-300" />}
            <p className="text-lg font-semibold text-white">{file?.name ?? "Drop or select a PDF"}</p>
            <p className="mt-2 text-sm text-zinc-400">{invalidFile ? "Only PDF files are accepted." : "Maximum backend validation size is 10MB."}</p>
          </label>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Target job description</CardTitle>
          <div className="flex rounded-2xl bg-zinc-900 p-1">
            <button className={`flex-1 rounded-xl px-3 py-2 text-sm ${mode === "text" ? "bg-white text-zinc-950" : "text-zinc-400"}`} onClick={() => setMode("text")}>Paste Text</button>
            <button className={`flex-1 rounded-xl px-3 py-2 text-sm ${mode === "url" ? "bg-white text-zinc-950" : "text-zinc-400"}`} onClick={() => setMode("url")}>Enter URL</button>
          </div>
        </CardHeader>
        <CardContent>
          {mode === "text" ? (
            <textarea className="min-h-56 w-full rounded-2xl border border-white/10 bg-black/30 p-4 text-sm text-white outline-none focus:border-emerald-300" placeholder="Paste the full job description here..." value={jdText} onChange={(event) => setJdText(event.target.value)} />
          ) : (
            <input className="w-full rounded-2xl border border-white/10 bg-black/30 p-4 text-sm text-white outline-none focus:border-emerald-300" placeholder="https://company.com/jobs/software-engineer" value={jdUrl} onChange={(event) => setJdUrl(event.target.value)} />
          )}
          <Button className="mt-4 w-full py-3" disabled={!canSubmit} onClick={onSubmit}>
            {running ? "Analyzing..." : "Analyze My Resume"}
          </Button>
          {error ? <p className="mt-3 rounded-xl border border-red-400/30 bg-red-950/30 p-3 text-sm text-red-100">{error}</p> : null}
        </CardContent>
      </Card>

      {events.length > 0 ? <div className="lg:col-span-2"><ProgressTracker events={events} /></div> : null}
    </div>
  );
}
