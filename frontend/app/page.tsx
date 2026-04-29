import { UploadForm } from "@/components/UploadForm";

export default function Home() {
  return (
    <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col px-6 py-10">
      <section className="mb-8 max-w-3xl">
        <p className="mb-3 text-sm font-medium uppercase tracking-[0.35em] text-emerald-300">Multi-agent career intelligence</p>
        <h1 className="text-4xl font-semibold tracking-tight text-white md:text-6xl">
          Turn any resume and job description into a precise action plan.
        </h1>
        <p className="mt-5 text-lg leading-8 text-zinc-300">
          CareerScope parses your resume, retrieves role context, scores skill gaps, and generates a 30/60/90-day roadmap plus recruiter outreach drafts.
        </p>
      </section>
      <UploadForm />
    </main>
  );
}
