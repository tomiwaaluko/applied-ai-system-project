import type { CareerReport, ProgressEvent, ReportSummary } from "@/lib/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function analyzeResume(file: File, jdInput: string): Promise<string> {
  const formData = new FormData();
  formData.append("resume", file);
  formData.append("jd_input", jdInput);
  const response = await fetch(`${API_URL}/api/analyze`, { method: "POST", body: formData });
  if (!response.ok) throw new Error("Analysis failed");
  return `${API_URL}/api/analyze`;
}

export async function streamAnalysis(
  file: File,
  jdInput: string,
  onEvent: (event: ProgressEvent) => void,
): Promise<string> {
  const formData = new FormData();
  formData.append("resume", file);
  formData.append("jd_input", jdInput);
  const response = await fetch(`${API_URL}/api/analyze`, { method: "POST", body: formData });
  if (!response.ok || !response.body) throw new Error("Analysis failed");

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let reportId = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const chunks = buffer.split("\n\n");
    buffer = chunks.pop() ?? "";
    for (const chunk of chunks) {
      const line = chunk.split("\n").find((item) => item.startsWith("data: "));
      if (!line) continue;
      const event = JSON.parse(line.slice(6)) as ProgressEvent;
      onEvent(event);
      if (event.report_id) reportId = event.report_id;
      if (event.status === "error") throw new Error(event.message);
    }
  }

  return reportId;
}

export async function getReport(id: string): Promise<CareerReport> {
  const res = await fetch(`${API_URL}/api/reports/${id}`, { cache: "no-store" });
  if (!res.ok) throw new Error("Report not found");
  return res.json();
}

export async function listReports(): Promise<ReportSummary[]> {
  const res = await fetch(`${API_URL}/api/reports`, { cache: "no-store" });
  return res.json();
}
