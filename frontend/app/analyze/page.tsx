import { ProgressTracker } from "@/components/ProgressTracker";

export default function AnalyzePage() {
  return (
    <main className="mx-auto w-full max-w-4xl flex-1 px-6 py-10">
      <ProgressTracker events={[]} />
      <p className="mt-4 text-sm text-zinc-400">
        Start a new analysis from the home page. Active upload progress is streamed inline after submission and redirects here conceptually before the final report.
      </p>
    </main>
  );
}
