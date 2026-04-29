import Link from "next/link";
import { listReports } from "@/lib/api";
import { Card } from "@/components/ui/card";

export default async function ReportsPage() {
  const reports = await listReports().catch(() => []);
  return (
    <main className="mx-auto w-full max-w-5xl flex-1 px-6 py-10">
      <h1 className="mb-6 text-3xl font-semibold text-white">Recent reports</h1>
      <div className="grid gap-4">
        {reports.map((report) => (
          <Link key={report.id} href={`/report/${report.id}`}>
            <Card className="transition hover:border-emerald-300/40">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="font-semibold text-white">{report.role_title ?? "Untitled role"}</p>
                  <p className="text-sm text-zinc-400">{report.created_at}</p>
                </div>
                <p className="text-2xl font-semibold text-emerald-300">{Math.round((report.match_score ?? 0) * 100)}%</p>
              </div>
            </Card>
          </Link>
        ))}
        {reports.length === 0 ? <Card><p className="text-zinc-300">No reports found yet.</p></Card> : null}
      </div>
    </main>
  );
}
