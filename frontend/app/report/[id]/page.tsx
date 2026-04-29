import { getReport } from "@/lib/api";
import { ReportDashboard } from "@/components/ReportDashboard";

export default async function ReportPage({ params }: { params: { id: string } }) {
  const report = await getReport(params.id);
  return (
    <main className="mx-auto w-full max-w-6xl flex-1 px-6 py-10">
      <ReportDashboard report={report} />
    </main>
  );
}
