import { GitHubAuthPanel } from "@/components/GitHubAuthPanel";
import { PrPreviewForm } from "@/components/PrPreviewForm";
import { appConfig } from "@/lib/config";
import { Badge } from "@/components/ui/badge";

export default function HomePage() {
  return (
    <main className="min-h-screen bg-slate-950">
      <div className="mx-auto flex max-w-7xl flex-col gap-10 px-4 py-8 sm:px-6 sm:py-12 lg:px-8 xl:px-10">
        <header className="relative overflow-hidden rounded-[32px] border border-slate-800/80 bg-slate-900/60 px-6 py-8 shadow-2xl shadow-slate-950/30 sm:px-8 sm:py-10">
          <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-sky-400/50 to-transparent" />
          <div className="absolute -right-16 top-0 h-48 w-48 rounded-full bg-sky-500/10 blur-3xl" />
          <div className="absolute left-0 top-16 h-40 w-40 rounded-full bg-cyan-400/5 blur-3xl" />

          <div className="relative flex flex-col gap-4">
            <Badge variant="info" className="w-fit px-3 py-1">
              Internal tooling · Demo safe
            </Badge>
            <div className="space-y-3">
              <h1 className="max-w-4xl text-4xl font-semibold tracking-tight text-slate-50 sm:text-5xl">
                {appConfig.name}
              </h1>
              <p className="max-w-3xl text-base leading-7 text-slate-300 sm:text-lg">
                {appConfig.description}
              </p>
            </div>
          </div>
        </header>

        <section>
          <GitHubAuthPanel />
        </section>

        <section className="pb-8">
          <PrPreviewForm />
        </section>
      </div>
    </main>
  );
}
