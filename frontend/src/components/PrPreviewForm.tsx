"use client";

import type { FormEvent, ReactNode } from "react";
import { useEffect, useState } from "react";
import {
  AlertOctagon,
  Bot,
  Clock3,
  FileCode2,
  Gauge,
  GitPullRequestArrow,
  Lightbulb,
  Radar,
  ShieldCheck,
  Sparkles,
  TriangleAlert
} from "lucide-react";
import { appConfig } from "@/lib/config";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";

type PreviewResponse = {
  owner: string;
  repo: string;
  pull_number: number;
  title?: string | null;
  state?: string | null;
  author?: string | null;
  changed_files_count: number | null;
  access_required: boolean;
  reason?: "private_repo" | "insufficient_permissions" | "not_found" | null;
  message?: string | null;
  authenticated: boolean;
};

type ParsedLine = {
  type: "added" | "removed" | "context";
  content: string;
};

type ParsedHunk = {
  old_start: number;
  old_count: number;
  new_start: number;
  new_count: number;
  lines: ParsedLine[];
};

type ParsedFile = {
  path: string;
  status: string;
  additions: number;
  deletions: number;
  patch: string | null;
  parsed_hunks: ParsedHunk[];
};

type ParsedDiffResponse = {
  owner: string;
  repo: string;
  pull_number: number;
  files: ParsedFile[];
};

type ReviewIssue = {
  severity: string;
  category: string;
  title: string;
  file: string;
  line: number | null;
  explanation: string;
  suggestion: string;
  evidence: string[];
};

type ReviewAnalysis = {
  summary: string;
  quality_score: number;
  critical_count: number;
  warning_count: number;
  suggestion_count: number;
  issues: ReviewIssue[];
  analysis_metadata?: ReviewAnalysisMetadata | null;
};

type EvaluationLabel = "correct" | "false_positive";

type ReviewAnalysisMetadata = {
  model?: string | null;
  latency_ms?: number | null;
  prompt_tokens?: number | null;
  completion_tokens?: number | null;
  total_tokens?: number | null;
  token_usage?: ReviewTokenUsage | null;
  pr?: ReviewPullRequestMetadata | null;
  retrieval?: ReviewRetrievalMetadata | null;
  context_chunks: number;
  review_mode: string;
  timestamp: string;
};

type ReviewPullRequestMetadata = {
  repository: string;
  pr_number: number;
  author: string;
  files_changed: number;
  additions: number;
  deletions: number;
};

type ReviewTokenUsage = {
  prompt_tokens?: number | null;
  completion_tokens?: number | null;
  total_tokens?: number | null;
  estimated_cost?: number | null;
};

type ReviewRetrievalMetadata = {
  chunks_used: number;
  top_files: ReviewRetrievedFile[];
};

type ReviewRetrievedFile = {
  path: string;
  similarity?: number | null;
};

type EvaluationMetrics = {
  total_issues: number;
  correct_issues: number;
  false_positives: number;
  total_expected?: number | null;
  precision?: number | null;
  recall?: number | null;
  f1_score?: number | null;
};

type ErrorState = {
  message: string;
};

type MetricCardProps = {
  label: string;
  value: number | string;
  tone: "score" | "critical" | "warning" | "suggestion";
  icon: ReactNode;
  suffix?: string;
};

type SectionHeadingProps = {
  eyebrow: string;
  title: string;
  description?: string;
  action?: ReactNode;
};

function getSeverityVariant(severity: string) {
  if (severity === "critical") return "critical";
  if (severity === "warning") return "warning";
  return "info";
}

function MetricCard({ label, value, tone, icon, suffix }: MetricCardProps) {
  const toneClassName =
    tone === "score"
      ? "border-sky-500/30 bg-sky-500/[0.08] text-sky-100 shadow-sky-950/40"
      : tone === "critical"
        ? "border-red-500/30 bg-red-500/[0.08] text-red-100 shadow-red-950/40"
        : tone === "warning"
          ? "border-amber-500/30 bg-amber-500/[0.08] text-amber-100 shadow-amber-950/40"
          : "border-cyan-500/30 bg-cyan-500/[0.08] text-cyan-100 shadow-cyan-950/40";

  return (
    <Card className={`border shadow-xl ${toneClassName}`}>
      <CardContent className="flex items-start justify-between gap-4 p-5 sm:p-6">
        <div className="space-y-3">
          <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-400">
            {label}
          </p>
          <div className="flex items-end gap-2">
            <span className="text-4xl font-semibold tracking-tight text-white sm:text-5xl">
              {value}
            </span>
            {suffix ? (
              <span className="pb-1 text-sm font-medium text-slate-400">
                {suffix}
              </span>
            ) : null}
          </div>
        </div>
        <div className="rounded-2xl border border-white/10 bg-white/5 p-3 text-slate-100">
          {icon}
        </div>
      </CardContent>
    </Card>
  );
}

function SectionHeading({
  eyebrow,
  title,
  description,
  action
}: SectionHeadingProps) {
  return (
    <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
      <div className="space-y-2">
        <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-500">
          {eyebrow}
        </p>
        <div className="space-y-1">
          <h2 className="text-xl font-semibold tracking-tight text-slate-50 sm:text-2xl">
            {title}
          </h2>
          {description ? (
            <p className="max-w-3xl text-sm leading-6 text-slate-400 sm:text-[15px]">
              {description}
            </p>
          ) : null}
        </div>
      </div>
      {action ? <div className="flex flex-wrap gap-3">{action}</div> : null}
    </div>
  );
}

function formatMetricValue(value: number | null | undefined) {
  if (typeof value !== "number" || Number.isNaN(value)) {
    return "N/A";
  }

  return new Intl.NumberFormat("en-US").format(value);
}

function formatUsdCost(value: number | null | undefined) {
  if (typeof value !== "number" || Number.isNaN(value)) {
    return "N/A";
  }

  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 4,
    maximumFractionDigits: 6
  }).format(value);
}

function formatTimestamp(value: string | null | undefined) {
  if (!value) {
    return "N/A";
  }

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return "N/A";
  }

  return new Intl.DateTimeFormat("en-US", {
    year: "numeric",
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit"
  }).format(parsed);
}

function formatSimilarity(value: number | null | undefined) {
  if (typeof value !== "number" || Number.isNaN(value)) {
    return "N/A";
  }

  return value.toFixed(2);
}

export function PrPreviewForm() {
  const [prUrl, setPrUrl] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [preview, setPreview] = useState<PreviewResponse | null>(null);
  const [error, setError] = useState<ErrorState | null>(null);
  const [isLoadingDiff, setIsLoadingDiff] = useState(false);
  const [parsedDiff, setParsedDiff] = useState<ParsedDiffResponse | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysis, setAnalysis] = useState<ReviewAnalysis | null>(null);
  const [selectedIssueIndex, setSelectedIssueIndex] = useState<number | null>(
    null
  );
  const [evaluationMetrics, setEvaluationMetrics] =
    useState<EvaluationMetrics | null>(null);
  const [issueEvaluations, setIssueEvaluations] = useState<
    Record<string, EvaluationLabel>
  >({});
  const [activeEvaluationKey, setActiveEvaluationKey] = useState<string | null>(
    null
  );

  const selectedIssue =
    selectedIssueIndex === null ? null : analysis?.issues[selectedIssueIndex];
  const firstHunk = parsedDiff?.files[0]?.parsed_hunks[0] ?? null;

  useEffect(() => {
    const loadEvaluationMetrics = async () => {
      try {
        const response = await fetch(
          `${appConfig.apiBaseUrl}/api/review/evaluations/metrics`
        );

        if (!response.ok) {
          return;
        }

        const data = (await response.json()) as EvaluationMetrics;
        setEvaluationMetrics(data);
      } catch {
        // Keep the dashboard resilient if metrics are temporarily unavailable.
      }
    };

    void loadEvaluationMetrics();
  }, []);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setIsSubmitting(true);
    setError(null);
    setPreview(null);
    setParsedDiff(null);
    setAnalysis(null);
    setSelectedIssueIndex(null);
    setIssueEvaluations({});

    try {
      const response = await fetch(
        `${appConfig.apiBaseUrl}/api/review/pr-preview`,
        {
          method: "POST",
          credentials: "include",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify({ pr_url: prUrl })
        }
      );

      if (!response.ok) {
        const data = (await response.json().catch(() => null)) as
          | { detail?: string | { msg?: string }[] }
          | null;

        const detail =
          typeof data?.detail === "string"
            ? data.detail
            : Array.isArray(data?.detail) && data.detail[0]?.msg
              ? data.detail[0].msg
              : "Failed to fetch PR preview.";

        setError({ message: detail });
        return;
      }

      const data = (await response.json()) as PreviewResponse;
      setPreview(data);
      setParsedDiff(null);
    } catch {
      setError({
        message: "Unexpected error while contacting the preview service."
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleLoadDiff = async () => {
    if (!preview) return;
    setIsLoadingDiff(true);
    setError(null);

    try {
      const response = await fetch(
        `${appConfig.apiBaseUrl}/api/review/parse-diff`,
        {
          method: "POST",
          credentials: "include",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify({ pr_url: prUrl })
        }
      );

      if (!response.ok) {
        const data = (await response.json().catch(() => null)) as
          | { detail?: string }
          | null;
        const detail =
          (data && typeof data.detail === "string" && data.detail) ||
          "Failed to parse diff for this pull request.";
        setError({ message: detail });
        return;
      }

      const data = (await response.json()) as ParsedDiffResponse;
      setParsedDiff(data);
    } catch {
      setError({
        message: "Unexpected error while requesting the parsed diff."
      });
    } finally {
      setIsLoadingDiff(false);
    }
  };

  const handleAnalyze = async () => {
    if (!preview) return;
    setIsAnalyzing(true);
    setError(null);
    setAnalysis(null);
    setSelectedIssueIndex(null);
    setIssueEvaluations({});

    try {
      const response = await fetch(
        `${appConfig.apiBaseUrl}/api/review/analyze`,
        {
          method: "POST",
          credentials: "include",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify({ pr_url: prUrl })
        }
      );

      if (!response.ok) {
        const data = (await response.json().catch(() => null)) as
          | { detail?: string }
          | null;
        const detail =
          (data && typeof data.detail === "string" && data.detail) ||
          "Failed to analyze this pull request.";
        setError({ message: detail });
        return;
      }

      const data = (await response.json()) as ReviewAnalysis;
      setAnalysis(data);
      setSelectedIssueIndex(data.issues.length > 0 ? 0 : null);
    } catch {
      setError({
        message: "Unexpected error while running the mocked analysis."
      });
    } finally {
      setIsAnalyzing(false);
    }
  };

  const getIssueKey = (issue: ReviewIssue) =>
    [
      issue.file,
      issue.line ?? "none",
      issue.category,
      issue.severity,
      issue.title
    ].join("::");

  const formatPercent = (value: number | null | undefined) => {
    if (typeof value !== "number" || Number.isNaN(value)) {
      return "N/A";
    }

    return `${(value * 100).toFixed(1)}%`;
  };

  const handleEvaluateIssue = async (
    issue: ReviewIssue,
    label: EvaluationLabel
  ) => {
    const issueKey = getIssueKey(issue);
    setActiveEvaluationKey(issueKey);
    setError(null);

    try {
      const response = await fetch(
        `${appConfig.apiBaseUrl}/api/review/evaluations/issues`,
        {
          method: "POST",
          credentials: "include",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify({
            pr_url: prUrl,
            issue_key: issueKey,
            severity: issue.severity,
            category: issue.category,
            title: issue.title,
            file: issue.file,
            line: issue.line,
            label
          })
        }
      );

      if (!response.ok) {
        const data = (await response.json().catch(() => null)) as
          | { detail?: string }
          | null;
        setError({
          message:
            (data && typeof data.detail === "string" && data.detail) ||
            "Failed to record evaluation feedback."
        });
        return;
      }

      const data = (await response.json()) as {
        issue_key: string;
        label: EvaluationLabel;
        metrics: EvaluationMetrics;
      };

      setIssueEvaluations((current) => ({
        ...current,
        [data.issue_key]: data.label
      }));
      setEvaluationMetrics(data.metrics);
    } catch {
      setError({
        message: "Unexpected error while saving issue evaluation."
      });
    } finally {
      setActiveEvaluationKey(null);
    }
  };

  return (
    <div className="space-y-8 sm:space-y-10">
      <Card className="overflow-hidden border-slate-800/80 bg-slate-900/60 shadow-2xl shadow-slate-950/40">
        <CardHeader className="border-b border-slate-800/80 pb-5 sm:px-6 sm:pt-6">
          <SectionHeading
            eyebrow="PR Input"
            title="Load a pull request for repository-aware analysis"
            description="Paste any public GitHub pull request URL to inspect metadata, parse the diff, and run the current review pipeline."
          />
        </CardHeader>
        <CardContent className="p-5 sm:p-6">
          <form onSubmit={handleSubmit} className="space-y-5">
            <label className="block space-y-3">
              <span className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-400">
                Public GitHub PR URL
              </span>
              <input
                type="url"
                required
                placeholder="https://github.com/owner/repo/pull/123"
                value={prUrl}
                onChange={(e) => setPrUrl(e.target.value)}
                className="w-full rounded-2xl border border-slate-700/80 bg-slate-950/80 px-5 py-4 text-base text-slate-50 outline-none transition focus:border-sky-500 focus:ring-4 focus:ring-sky-500/20"
              />
            </label>

            <div className="flex flex-col gap-3 border-t border-slate-800/80 pt-5 sm:flex-row sm:items-center sm:justify-between">
              <p className="max-w-2xl text-sm leading-6 text-slate-400">
                Preview loads repository metadata first. Diff parsing and AI
                analysis remain opt-in actions after the PR is resolved.
              </p>
              <Button
                type="submit"
                size="lg"
                disabled={isSubmitting}
                className="rounded-xl px-5 text-sm font-semibold shadow-lg shadow-sky-950/40"
              >
                {isSubmitting ? "Fetching preview…" : "Preview pull request"}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      {error ? (
        <Card className="border-red-500/40 bg-red-950/30 shadow-lg shadow-red-950/20">
          <CardContent className="flex gap-4 p-5 sm:p-6">
            <div className="mt-0.5 rounded-xl border border-red-500/30 bg-red-500/10 p-2 text-red-200">
              <AlertOctagon className="h-5 w-5" />
            </div>
            <div className="space-y-1">
              <p className="text-sm font-semibold text-red-100">
                Unable to preview pull request
              </p>
              <p className="text-sm leading-6 text-red-200/85">
                {error.message}
              </p>
            </div>
          </CardContent>
        </Card>
      ) : null}

      {preview ? (
        <section className="space-y-8 sm:space-y-10">
          {preview.access_required || preview.reason === "not_found" ? (
            <Card className="border-amber-500/25 bg-amber-500/[0.06] shadow-xl shadow-amber-950/20">
              <CardHeader className="border-b border-amber-500/15 pb-5 sm:px-6 sm:pt-6">
                <SectionHeading
                  eyebrow="Access"
                  title={
                    preview.reason === "insufficient_permissions"
                      ? "GitHub access needs adjustment"
                      : preview.reason === "not_found"
                        ? "Pull request could not be located"
                        : "GitHub connection required"
                  }
                  description={preview.message ?? undefined}
                  action={
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge
                        variant="default"
                        className="border-slate-700 bg-slate-950/70 px-3 py-1 text-slate-100"
                      >
                        {preview.owner}/{preview.repo}
                      </Badge>
                      <Badge
                        variant="warning"
                        className="px-3 py-1"
                      >
                        PR #{preview.pull_number}
                      </Badge>
                    </div>
                  }
                />
              </CardHeader>
              <CardContent className="p-5 sm:p-6">
                <div className="flex flex-col gap-4 rounded-3xl border border-slate-800 bg-slate-950/50 p-5 sm:flex-row sm:items-center sm:justify-between">
                  <div className="space-y-2">
                    <p className="text-sm font-semibold text-slate-100">
                      {preview.reason === "insufficient_permissions"
                        ? "This GitHub account is connected, but it does not currently have access to this repository."
                        : preview.reason === "not_found"
                          ? "The repository is reachable, but this pull request was not found."
                          : "This pull request appears to require authenticated GitHub access before analysis can continue."}
                    </p>
                    <p className="max-w-2xl text-sm leading-6 text-slate-400">
                      {preview.reason === "private_repo"
                        ? "Connect GitHub to confirm your access and let the reviewer use the same read permissions you already have."
                        : preview.reason === "insufficient_permissions"
                          ? "Try a GitHub account that can view this repository, or ask a repository maintainer to grant access."
                          : "Check the pull request URL and try again."}
                    </p>
                  </div>
                  {!preview.authenticated && preview.reason === "private_repo" ? (
                    <Button
                      type="button"
                      size="lg"
                      className="rounded-xl px-5 text-sm font-semibold shadow-lg shadow-sky-950/40"
                      onClick={() => {
                        window.location.href = `${appConfig.apiBaseUrl}/api/auth/github/login`;
                      }}
                    >
                      Connect GitHub to continue
                    </Button>
                  ) : null}
                </div>
              </CardContent>
            </Card>
          ) : (
            <Card className="border-emerald-500/25 bg-emerald-500/[0.06] shadow-xl shadow-emerald-950/20">
              <CardHeader className="border-b border-emerald-500/15 pb-5 sm:px-6 sm:pt-6">
                <SectionHeading
                  eyebrow="PR Metadata"
                  title={preview.title ?? "Pull request preview"}
                  description={`${preview.owner}/${preview.repo} · Pull Request #${preview.pull_number}`}
                  action={
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge
                        variant="default"
                        className="border-emerald-400/20 bg-emerald-500/10 px-3 py-1 text-emerald-100"
                      >
                        <GitPullRequestArrow className="mr-1.5 h-3.5 w-3.5" />
                        PR #{preview.pull_number}
                      </Badge>
                      <Badge
                        variant="default"
                        className="border-slate-700 bg-slate-950/70 px-3 py-1 text-slate-100"
                      >
                        {preview.state ?? "unknown"}
                      </Badge>
                    </div>
                  }
                />
              </CardHeader>
              <CardContent className="grid gap-4 p-5 sm:grid-cols-3 sm:p-6">
                <div className="rounded-2xl border border-emerald-400/15 bg-slate-950/35 p-5">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-emerald-200/75">
                    Repository
                  </p>
                  <p className="mt-3 text-lg font-semibold text-white">
                    {preview.owner}/{preview.repo}
                  </p>
                </div>
                <div className="rounded-2xl border border-emerald-400/15 bg-slate-950/35 p-5">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-emerald-200/75">
                    Author
                  </p>
                  <p className="mt-3 text-lg font-semibold text-white">
                    {preview.author ?? "N/A"}
                  </p>
                </div>
                <div className="rounded-2xl border border-emerald-400/15 bg-slate-950/35 p-5">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-emerald-200/75">
                    Changed Files
                  </p>
                  <p className="mt-3 text-lg font-semibold text-white">
                    {preview.changed_files_count ?? "N/A"}
                  </p>
                </div>
              </CardContent>
            </Card>
          )}

          {!preview.access_required && preview.reason !== "not_found" ? (
          <Card className="border-slate-800/80 bg-slate-900/60 shadow-xl shadow-slate-950/30">
            <CardHeader className="border-b border-slate-800/80 pb-5 sm:px-6 sm:pt-6">
              <SectionHeading
                eyebrow="Workflow"
                title="Inspect diff data and run review analysis"
                description="Use the parsed diff preview for a quick structural check, then open the AI review workspace."
                action={
                  <>
                    <Button
                      type="button"
                      size="lg"
                      variant="secondary"
                      onClick={handleLoadDiff}
                      disabled={isLoadingDiff}
                      className="rounded-xl border border-emerald-500/20 bg-emerald-500/10 px-5 text-emerald-100 hover:bg-emerald-500/20"
                    >
                      {isLoadingDiff ? "Loading parsed diff…" : "Load parsed diff"}
                    </Button>
                    <Button
                      type="button"
                      size="lg"
                      onClick={handleAnalyze}
                      disabled={isAnalyzing}
                      className="rounded-xl bg-sky-500 px-5 text-slate-950 shadow-lg shadow-sky-950/40 hover:bg-sky-400"
                    >
                      {isAnalyzing ? "Running mocked analysis…" : "Run mocked analysis"}
                    </Button>
                  </>
                }
              />
            </CardHeader>

            {parsedDiff ? (
              <CardContent className="grid gap-6 p-5 xl:grid-cols-[minmax(0,0.95fr)_minmax(0,1.3fr)] sm:p-6">
                <div className="space-y-4 rounded-3xl border border-slate-800/80 bg-slate-950/60 p-5">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-400">
                        Changed Files
                      </p>
                      <p className="mt-2 text-2xl font-semibold tracking-tight text-white">
                        {parsedDiff.files.length}
                      </p>
                    </div>
                    <div className="rounded-2xl border border-slate-700/70 bg-slate-900/80 p-3 text-slate-200">
                      <FileCode2 className="h-5 w-5" />
                    </div>
                  </div>

                  <div className="max-h-[24rem] space-y-2 overflow-y-auto pr-1">
                    {parsedDiff.files.map((file) => (
                      <div
                        key={file.path}
                        className="rounded-2xl border border-slate-800 bg-slate-900/70 p-4"
                      >
                        <p className="font-mono text-sm text-slate-100">
                          {file.path}
                        </p>
                        <div className="mt-3 flex flex-wrap gap-2 text-xs text-slate-300">
                          <span className="rounded-full border border-slate-700 bg-slate-950/80 px-2.5 py-1">
                            {file.status}
                          </span>
                          <span className="rounded-full border border-emerald-500/20 bg-emerald-500/10 px-2.5 py-1 text-emerald-200">
                            +{file.additions}
                          </span>
                          <span className="rounded-full border border-red-500/20 bg-red-500/10 px-2.5 py-1 text-red-200">
                            -{file.deletions}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="rounded-3xl border border-slate-800/80 bg-slate-950/60 p-5 sm:p-6">
                  <div className="flex items-center justify-between gap-3">
                    <div className="space-y-1">
                      <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-400">
                        Code Evidence
                      </p>
                      <p className="text-lg font-semibold tracking-tight text-white">
                        {parsedDiff.files[0]?.path
                          ? `Preview of ${parsedDiff.files[0].path}`
                          : "No parsed hunk available"}
                      </p>
                    </div>
                    <Badge variant="info" className="px-3 py-1">
                      First parsed hunk
                    </Badge>
                  </div>

                  {firstHunk ? (
                    <div className="mt-5 overflow-hidden rounded-3xl border border-slate-800 bg-slate-950 shadow-inner shadow-black/30">
                      <div className="flex items-center justify-between border-b border-slate-800 px-4 py-3 text-xs text-slate-400">
                        <span className="font-medium">
                          Parsed hunk with syntax-style line groups
                        </span>
                        <span className="font-mono">
                          -{firstHunk.old_start},{firstHunk.old_count} / +
                          {firstHunk.new_start},{firstHunk.new_count}
                        </span>
                      </div>
                      <pre className="max-h-[24rem] overflow-auto px-5 py-5 font-mono text-[13px] leading-6 text-slate-100">
                        {firstHunk.lines.map((line, index) => {
                          const prefix =
                            line.type === "added"
                              ? "+"
                              : line.type === "removed"
                                ? "-"
                                : " ";

                          return (
                            <div
                              key={index}
                              className={
                                line.type === "added"
                                  ? "text-emerald-300"
                                  : line.type === "removed"
                                    ? "text-red-300"
                                    : "text-slate-300"
                              }
                            >
                              {prefix}
                              {line.content}
                            </div>
                          );
                        })}
                      </pre>
                    </div>
                  ) : (
                    <div className="mt-5 rounded-3xl border border-dashed border-slate-700 bg-slate-950/70 p-8 text-sm text-slate-400">
                      No parsed hunk is available for the first changed file.
                    </div>
                  )}
                </div>
              </CardContent>
            ) : null}
          </Card>
          ) : null}

          {analysis ? (
            <section className="space-y-6 sm:space-y-8">
              <SectionHeading
                eyebrow="Review Summary"
                title="Repository-aware review workspace"
                description={analysis.summary}
              />

              <div className="grid gap-4 md:grid-cols-2 2xl:grid-cols-4">
                <MetricCard
                  label="Score"
                  value={analysis.quality_score}
                  suffix="/100"
                  tone="score"
                  icon={<ShieldCheck className="h-5 w-5" />}
                />
                <MetricCard
                  label="Critical"
                  value={analysis.critical_count}
                  tone="critical"
                  icon={<AlertOctagon className="h-5 w-5" />}
                />
                <MetricCard
                  label="Warnings"
                  value={analysis.warning_count}
                  tone="warning"
                  icon={<TriangleAlert className="h-5 w-5" />}
                />
                <MetricCard
                  label="Suggestions"
                  value={analysis.suggestion_count}
                  tone="suggestion"
                  icon={<Lightbulb className="h-5 w-5" />}
                />
              </div>

              <Card className="border-slate-800/80 bg-slate-900/60 shadow-lg shadow-slate-950/20">
                <CardHeader className="border-b border-slate-800/80 pb-4 sm:px-6 sm:pt-6">
                  <div className="space-y-1">
                    <CardTitle className="text-base">Pull Request</CardTitle>
                    <CardDescription className="text-sm">
                      Source context for the analyzed change set.
                    </CardDescription>
                  </div>
                </CardHeader>
                <CardContent className="grid gap-3 p-5 sm:grid-cols-2 xl:grid-cols-6 sm:p-6">
                  <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4 xl:col-span-2">
                    <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-400">
                      Repository
                    </p>
                    <p className="mt-3 font-mono text-sm text-slate-100">
                      {analysis.analysis_metadata?.pr?.repository ?? "N/A"}
                    </p>
                  </div>
                  <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
                    <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-400">
                      PR Number
                    </p>
                    <p className="mt-3 text-right font-mono text-lg font-semibold text-slate-100">
                      {formatMetricValue(analysis.analysis_metadata?.pr?.pr_number)}
                    </p>
                  </div>
                  <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
                    <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-400">
                      Author
                    </p>
                    <p className="mt-3 text-right font-mono text-sm text-slate-100">
                      {analysis.analysis_metadata?.pr?.author ?? "N/A"}
                    </p>
                  </div>
                  <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
                    <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-400">
                      Files Changed
                    </p>
                    <p className="mt-3 text-right font-mono text-lg font-semibold text-slate-100">
                      {formatMetricValue(
                        analysis.analysis_metadata?.pr?.files_changed
                      )}
                    </p>
                  </div>
                  <div className="rounded-2xl border border-emerald-500/20 bg-emerald-500/[0.08] p-4">
                    <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-emerald-200/80">
                      Additions
                    </p>
                    <p className="mt-3 text-right font-mono text-lg font-semibold text-emerald-100">
                      {analysis.analysis_metadata?.pr?.additions != null
                        ? `+${formatMetricValue(
                            analysis.analysis_metadata.pr.additions
                          )}`
                        : "N/A"}
                    </p>
                  </div>
                  <div className="rounded-2xl border border-red-500/20 bg-red-500/[0.08] p-4">
                    <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-red-200/80">
                      Deletions
                    </p>
                    <p className="mt-3 text-right font-mono text-lg font-semibold text-red-100">
                      {analysis.analysis_metadata?.pr?.deletions != null
                        ? `-${formatMetricValue(
                            analysis.analysis_metadata.pr.deletions
                          )}`
                        : "N/A"}
                    </p>
                  </div>
                </CardContent>
              </Card>

              <Card className="border-slate-800/80 bg-slate-900/60 shadow-lg shadow-slate-950/20">
                <CardHeader className="border-b border-slate-800/80 pb-4 sm:px-6 sm:pt-6">
                  <div className="space-y-1">
                    <CardTitle className="text-base">
                      Repository Context
                    </CardTitle>
                    <CardDescription className="text-sm">
                      Repository files retrieved to enrich the AI review.
                    </CardDescription>
                  </div>
                </CardHeader>
                <CardContent className="space-y-4 p-5 sm:p-6">
                  <div className="grid gap-3 sm:grid-cols-[minmax(0,180px)_1fr]">
                    <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
                      <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-400">
                        Chunks Used
                      </p>
                      <p className="mt-3 text-right font-mono text-lg font-semibold text-slate-100">
                        {formatMetricValue(
                          analysis.analysis_metadata?.retrieval?.chunks_used ??
                            analysis.analysis_metadata?.context_chunks
                        )}
                      </p>
                    </div>
                    <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
                      <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-400">
                        Top Retrieved Files
                      </p>
                      {analysis.analysis_metadata?.retrieval?.top_files?.length ? (
                        <div className="mt-3 max-h-48 space-y-2 overflow-y-auto pr-1">
                          {analysis.analysis_metadata.retrieval.top_files.map(
                            (file, index) => (
                              <div
                                key={`${file.path}-${index}`}
                                className="flex items-center justify-between gap-3 rounded-xl border border-slate-800 bg-slate-900/70 px-3 py-2"
                              >
                                <span className="truncate font-mono text-sm text-slate-200">
                                  {file.path}
                                </span>
                                <Badge
                                  variant="default"
                                  className="shrink-0 border-slate-700 bg-slate-950/80 px-2.5 py-1 font-mono text-slate-200"
                                >
                                  {formatSimilarity(file.similarity)}
                                </Badge>
                              </div>
                            )
                          )}
                        </div>
                      ) : (
                        <p className="mt-3 text-sm text-slate-400">
                          No retrieval context metadata is available for this
                          review.
                        </p>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card className="border-slate-800/80 bg-slate-900/60 shadow-lg shadow-slate-950/20">
                <CardHeader className="border-b border-slate-800/80 pb-4 sm:px-6 sm:pt-6">
                  <div className="flex items-start justify-between gap-3">
                    <div className="space-y-1">
                      <CardTitle className="text-base">
                        AI Observability
                      </CardTitle>
                      <CardDescription className="text-sm">
                        Runtime metadata for the latest review call.
                      </CardDescription>
                    </div>
                    <div className="rounded-2xl border border-slate-700/80 bg-slate-950/80 p-3 text-slate-200">
                      <Radar className="h-4 w-4" />
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="grid gap-3 p-5 sm:grid-cols-2 lg:grid-cols-4 sm:p-6">
                  <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
                    <div className="flex items-center gap-2 text-slate-400">
                      <Bot className="h-4 w-4" />
                      <p className="text-[11px] font-semibold uppercase tracking-[0.24em]">
                        Model
                      </p>
                    </div>
                    <p className="mt-3 font-mono text-sm text-slate-100">
                      {analysis.analysis_metadata?.model ?? "N/A"}
                    </p>
                  </div>
                  <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
                    <div className="flex items-center gap-2 text-slate-400">
                      <Clock3 className="h-4 w-4" />
                      <p className="text-[11px] font-semibold uppercase tracking-[0.24em]">
                        Latency
                      </p>
                    </div>
                    <p className="mt-3 font-mono text-sm text-slate-100">
                      {analysis.analysis_metadata?.latency_ms != null
                        ? `${formatMetricValue(analysis.analysis_metadata.latency_ms)} ms`
                        : "N/A"}
                    </p>
                  </div>
                  <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
                    <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-400">
                      Response Size
                    </p>
                    <div className="mt-3 space-y-2 font-mono text-sm text-slate-100">
                      <div className="flex items-center justify-between gap-3">
                        <span className="text-slate-400">Total tokens</span>
                        <span>
                          {formatMetricValue(
                            analysis.analysis_metadata?.total_tokens
                          )}
                        </span>
                      </div>
                      <div className="flex items-center justify-between gap-3 border-t border-slate-800 pt-2">
                        <span className="text-slate-400">Timestamp</span>
                        <span className="text-right text-xs">
                          {formatTimestamp(analysis.analysis_metadata?.timestamp)}
                        </span>
                      </div>
                    </div>
                  </div>
                  <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
                    <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-400">
                      Execution
                    </p>
                    <div className="mt-3 space-y-2 font-mono text-sm text-slate-100">
                      <div className="flex items-center justify-between gap-3">
                        <span className="text-slate-400">Context</span>
                        <span>
                          {formatMetricValue(
                            analysis.analysis_metadata?.context_chunks
                          )}
                        </span>
                      </div>
                      <div className="flex items-center justify-between gap-3">
                        <span className="text-slate-400">Mode</span>
                        <span>{analysis.analysis_metadata?.review_mode ?? "N/A"}</span>
                      </div>
                      <div className="flex items-center justify-between gap-3 border-t border-slate-800 pt-2">
                        <span className="text-slate-400">Status</span>
                        <span>
                          {analysis.analysis_metadata?.model ? "Live LLM" : "Fallback"}
                        </span>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card className="border-slate-800/80 bg-slate-900/60 shadow-lg shadow-slate-950/20">
                <CardHeader className="border-b border-slate-800/80 pb-4 sm:px-6 sm:pt-6">
                  <div className="space-y-1">
                    <CardTitle className="text-base">Token Usage</CardTitle>
                    <CardDescription className="text-sm">
                      OpenAI token consumption and estimated request cost.
                    </CardDescription>
                  </div>
                </CardHeader>
                <CardContent className="grid gap-3 p-5 sm:grid-cols-2 xl:grid-cols-4 sm:p-6">
                  <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
                    <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-400">
                      Prompt Tokens
                    </p>
                    <p className="mt-3 text-right font-mono text-lg font-semibold text-slate-100">
                      {formatMetricValue(
                        analysis.analysis_metadata?.token_usage?.prompt_tokens ??
                          analysis.analysis_metadata?.prompt_tokens
                      )}
                    </p>
                  </div>
                  <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
                    <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-400">
                      Completion Tokens
                    </p>
                    <p className="mt-3 text-right font-mono text-lg font-semibold text-slate-100">
                      {formatMetricValue(
                        analysis.analysis_metadata?.token_usage
                          ?.completion_tokens ??
                          analysis.analysis_metadata?.completion_tokens
                      )}
                    </p>
                  </div>
                  <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
                    <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-400">
                      Total Tokens
                    </p>
                    <p className="mt-3 text-right font-mono text-lg font-semibold text-slate-100">
                      {formatMetricValue(
                        analysis.analysis_metadata?.token_usage?.total_tokens ??
                          analysis.analysis_metadata?.total_tokens
                      )}
                    </p>
                  </div>
                  <div className="rounded-2xl border border-emerald-500/20 bg-emerald-500/[0.08] p-4 shadow-inner shadow-emerald-950/20">
                    <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-emerald-200/80">
                      Estimated Cost
                    </p>
                    <p className="mt-3 text-right font-mono text-lg font-semibold text-emerald-100">
                      {formatUsdCost(
                        analysis.analysis_metadata?.token_usage?.estimated_cost
                      )}
                    </p>
                  </div>
                </CardContent>
              </Card>

              <Card className="border-slate-800/80 bg-slate-900/60 shadow-lg shadow-slate-950/20">
                <CardHeader className="border-b border-slate-800/80 pb-4 sm:px-6 sm:pt-6">
                  <div className="flex items-start justify-between gap-3">
                    <div className="space-y-1">
                      <CardTitle className="text-base">
                        Evaluation Metrics
                      </CardTitle>
                      <CardDescription className="text-sm">
                        User-labeled issue quality metrics for review output.
                      </CardDescription>
                    </div>
                    <div className="rounded-2xl border border-slate-700/80 bg-slate-950/80 p-3 text-slate-200">
                      <Gauge className="h-4 w-4" />
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="grid gap-3 p-5 sm:grid-cols-2 xl:grid-cols-6 sm:p-6">
                  <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
                    <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-400">
                      Issues Detected
                    </p>
                    <p className="mt-3 text-right font-mono text-lg font-semibold text-slate-100">
                      {formatMetricValue(evaluationMetrics?.total_issues ?? 0)}
                    </p>
                  </div>
                  <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
                    <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-400">
                      Correct
                    </p>
                    <p className="mt-3 text-right font-mono text-lg font-semibold text-emerald-100">
                      {formatMetricValue(evaluationMetrics?.correct_issues ?? 0)}
                    </p>
                  </div>
                  <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
                    <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-400">
                      False Positives
                    </p>
                    <p className="mt-3 text-right font-mono text-lg font-semibold text-red-100">
                      {formatMetricValue(
                        evaluationMetrics?.false_positives ?? 0
                      )}
                    </p>
                  </div>
                  <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
                    <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-400">
                      Precision
                    </p>
                    <p className="mt-3 text-right font-mono text-lg font-semibold text-slate-100">
                      {formatPercent(evaluationMetrics?.precision)}
                    </p>
                  </div>
                  <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
                    <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-400">
                      Recall
                    </p>
                    <p className="mt-3 text-right font-mono text-lg font-semibold text-slate-100">
                      {formatPercent(evaluationMetrics?.recall)}
                    </p>
                  </div>
                  <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
                    <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-400">
                      F1 Score
                    </p>
                    <p className="mt-3 text-right font-mono text-lg font-semibold text-slate-100">
                      {formatPercent(evaluationMetrics?.f1_score)}
                    </p>
                  </div>
                </CardContent>
              </Card>

              {analysis.issues.length === 0 ? (
                <Card className="border-slate-800/80 bg-slate-900/60">
                  <CardContent className="flex items-center gap-4 p-6">
                    <div className="rounded-2xl border border-cyan-500/20 bg-cyan-500/10 p-3 text-cyan-100">
                      <Sparkles className="h-5 w-5" />
                    </div>
                    <div>
                      <p className="text-base font-semibold text-slate-50">
                        No issues detected
                      </p>
                      <p className="mt-1 text-sm leading-6 text-slate-400">
                        The current heuristics did not surface actionable review
                        items for this pull request.
                      </p>
                    </div>
                  </CardContent>
                </Card>
              ) : (
                <div className="grid gap-6 xl:grid-cols-[minmax(0,0.8fr)_minmax(0,1.2fr)]">
                  <Card className="border-slate-800/80 bg-slate-900/60 shadow-xl shadow-slate-950/30">
                    <CardHeader className="border-b border-slate-800/80 pb-4 sm:px-6 sm:pt-6">
                      <div className="space-y-1">
                        <CardTitle className="text-lg">Issues List</CardTitle>
                        <CardDescription className="text-sm">
                          Select an item to inspect the explanation, suggested
                          fix, and code evidence.
                        </CardDescription>
                      </div>
                    </CardHeader>
                    <CardContent className="p-3 sm:p-4">
                      <div className="max-h-[48rem] space-y-3 overflow-y-auto pr-1">
                        {analysis.issues.map((issue, index) => {
                          const isSelected = selectedIssueIndex === index;
                          const issueKey = getIssueKey(issue);
                          const evaluationLabel = issueEvaluations[issueKey];
                          const isEvaluating = activeEvaluationKey === issueKey;

                          return (
                            <button
                              key={`${issue.file}-${issue.title}-${index}`}
                              type="button"
                              onClick={() => setSelectedIssueIndex(index)}
                              className={`w-full rounded-3xl border p-4 text-left transition ${
                                isSelected
                                  ? "border-sky-500/40 bg-sky-500/[0.08] shadow-lg shadow-sky-950/20"
                                  : "border-slate-800 bg-slate-950/40 hover:border-slate-700 hover:bg-slate-950/70"
                              }`}
                            >
                              <div className="flex flex-wrap items-start justify-between gap-3">
                                <div className="space-y-3">
                                  <div className="flex flex-wrap items-center gap-2">
                                    <Badge
                                      variant={getSeverityVariant(issue.severity)}
                                      className="px-2.5 py-1"
                                    >
                                      {issue.severity}
                                    </Badge>
                                    <span className="text-xs font-medium uppercase tracking-[0.18em] text-slate-500">
                                      {issue.category}
                                    </span>
                                    {evaluationLabel ? (
                                      <Badge
                                        variant={
                                          evaluationLabel === "correct"
                                            ? "info"
                                            : "warning"
                                        }
                                        className="px-2.5 py-1"
                                      >
                                        {evaluationLabel === "correct"
                                          ? "Marked correct"
                                          : "Marked false positive"}
                                      </Badge>
                                    ) : null}
                                  </div>
                                  <div className="space-y-1">
                                    <p className="text-sm font-semibold text-slate-50">
                                      {issue.title}
                                    </p>
                                    <p className="text-sm text-slate-400">
                                      {issue.file}
                                      {issue.line ? `:${issue.line}` : ""}
                                    </p>
                                  </div>
                                  <div className="flex flex-wrap gap-2">
                                    <Button
                                      type="button"
                                      size="sm"
                                      variant={
                                        evaluationLabel === "correct"
                                          ? "default"
                                          : "outline"
                                      }
                                      disabled={isEvaluating}
                                      className="rounded-lg"
                                      onClick={(event) => {
                                        event.stopPropagation();
                                        void handleEvaluateIssue(issue, "correct");
                                      }}
                                    >
                                      Mark correct
                                    </Button>
                                    <Button
                                      type="button"
                                      size="sm"
                                      variant={
                                        evaluationLabel === "false_positive"
                                          ? "destructive"
                                          : "outline"
                                      }
                                      disabled={isEvaluating}
                                      className="rounded-lg"
                                      onClick={(event) => {
                                        event.stopPropagation();
                                        void handleEvaluateIssue(
                                          issue,
                                          "false_positive"
                                        );
                                      }}
                                    >
                                      Mark false positive
                                    </Button>
                                  </div>
                                </div>
                                <span className="text-xs text-slate-500">
                                  {isSelected ? "Selected" : "Open"}
                                </span>
                              </div>
                            </button>
                          );
                        })}
                      </div>
                    </CardContent>
                  </Card>

                  <div className="space-y-6">
                    <Card className="border-slate-800/80 bg-slate-900/60 shadow-xl shadow-slate-950/30">
                      <CardHeader className="border-b border-slate-800/80 pb-4 sm:px-6 sm:pt-6">
                        <div className="flex flex-wrap items-start justify-between gap-3">
                          <div className="space-y-2">
                            <CardTitle className="text-lg">
                              Selected Issue Details
                            </CardTitle>
                            <CardDescription className="text-sm">
                              Explanation and recommended remediation for the
                              active finding.
                            </CardDescription>
                          </div>
                          {selectedIssue ? (
                            <Badge
                              variant={getSeverityVariant(selectedIssue.severity)}
                              className="px-3 py-1"
                            >
                              {selectedIssue.severity}
                            </Badge>
                          ) : null}
                        </div>
                      </CardHeader>
                      <CardContent className="space-y-6 p-5 sm:p-6">
                        {selectedIssue ? (
                          <>
                            <div className="space-y-3">
                              <div className="space-y-2">
                                <p className="text-2xl font-semibold tracking-tight text-white">
                                  {selectedIssue.title}
                                </p>
                                <div className="flex flex-wrap items-center gap-2 text-sm text-slate-400">
                                  <span className="rounded-full border border-slate-700 bg-slate-950/80 px-3 py-1 font-medium text-slate-200">
                                    {selectedIssue.category}
                                  </span>
                                  <span className="font-mono">
                                    {selectedIssue.file}
                                    {selectedIssue.line
                                      ? `:${selectedIssue.line}`
                                      : ""}
                                  </span>
                                </div>
                              </div>
                              <p className="max-w-3xl text-[15px] leading-7 text-slate-300">
                                {selectedIssue.explanation}
                              </p>
                              <div className="flex flex-wrap gap-2">
                                <Button
                                  type="button"
                                  size="sm"
                                  variant={
                                    issueEvaluations[getIssueKey(selectedIssue)] ===
                                    "correct"
                                      ? "default"
                                      : "outline"
                                  }
                                  disabled={
                                    activeEvaluationKey === getIssueKey(selectedIssue)
                                  }
                                  className="rounded-lg"
                                  onClick={() =>
                                    void handleEvaluateIssue(
                                      selectedIssue,
                                      "correct"
                                    )
                                  }
                                >
                                  Mark correct
                                </Button>
                                <Button
                                  type="button"
                                  size="sm"
                                  variant={
                                    issueEvaluations[getIssueKey(selectedIssue)] ===
                                    "false_positive"
                                      ? "destructive"
                                      : "outline"
                                  }
                                  disabled={
                                    activeEvaluationKey === getIssueKey(selectedIssue)
                                  }
                                  className="rounded-lg"
                                  onClick={() =>
                                    void handleEvaluateIssue(
                                      selectedIssue,
                                      "false_positive"
                                    )
                                  }
                                >
                                  Mark false positive
                                </Button>
                              </div>
                            </div>

                            <div className="rounded-3xl border border-slate-800 bg-slate-950/50 p-5">
                              <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-400">
                                Suggested Fix
                              </p>
                              <p className="mt-3 text-[15px] leading-7 text-slate-200">
                                {selectedIssue.suggestion}
                              </p>
                            </div>
                          </>
                        ) : (
                          <div className="rounded-3xl border border-dashed border-slate-700 bg-slate-950/60 p-8 text-sm text-slate-400">
                            Select an issue from the list to inspect its full
                            review details.
                          </div>
                        )}
                      </CardContent>
                    </Card>

                    <Card className="border-slate-800/80 bg-slate-900/60 shadow-xl shadow-slate-950/30">
                      <CardHeader className="border-b border-slate-800/80 pb-4 sm:px-6 sm:pt-6">
                        <div className="space-y-1">
                          <CardTitle className="text-lg">Code Evidence</CardTitle>
                          <CardDescription className="text-sm">
                            Supporting snippets are isolated in a dedicated
                            scrollable panel for easier review.
                          </CardDescription>
                        </div>
                      </CardHeader>
                      <CardContent className="p-5 sm:p-6">
                        {selectedIssue?.evidence.length ? (
                          <div className="overflow-hidden rounded-3xl border border-slate-800 bg-slate-950 shadow-inner shadow-black/30">
                            <div className="border-b border-slate-800 px-4 py-3 text-xs font-medium text-slate-400">
                              Evidence snippets
                            </div>
                            <pre className="max-h-[26rem] overflow-auto px-5 py-5 font-mono text-[13px] leading-6 text-slate-100">
                              {selectedIssue.evidence.join("\n")}
                            </pre>
                          </div>
                        ) : (
                          <div className="rounded-3xl border border-dashed border-slate-700 bg-slate-950/60 p-8 text-sm text-slate-400">
                            No evidence snippets are attached to the selected
                            issue.
                          </div>
                        )}
                      </CardContent>
                    </Card>
                  </div>
                </div>
              )}
            </section>
          ) : null}
        </section>
      ) : null}
    </div>
  );
}
