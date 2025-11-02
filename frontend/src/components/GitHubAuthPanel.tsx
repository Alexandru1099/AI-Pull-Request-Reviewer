"use client";

import { useEffect, useMemo, useState } from "react";
import {
  ChevronRight,
  Github,
  Link2,
  LoaderCircle,
  LockKeyhole,
  LogOut,
  ShieldCheck,
  X
} from "lucide-react";
import { appConfig } from "@/lib/config";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

type AuthUser = {
  id: number;
  login: string;
  name?: string | null;
  avatar_url?: string | null;
};

type AuthSessionResponse = {
  authenticated: boolean;
  status: string;
  message?: string | null;
  user?: AuthUser | null;
};

function AuthStatusBanner({
  tone,
  message
}: {
  tone: "success" | "warning" | "error";
  message: string;
}) {
  const toneClassName =
    tone === "success"
      ? "border-emerald-500/25 bg-emerald-500/[0.08] text-emerald-100"
      : tone === "warning"
        ? "border-amber-500/25 bg-amber-500/[0.08] text-amber-100"
        : "border-red-500/25 bg-red-500/[0.08] text-red-100";

  return (
    <div className={`rounded-2xl border px-4 py-3 text-sm ${toneClassName}`}>
      {message}
    </div>
  );
}

export function GitHubAuthPanel() {
  const [authState, setAuthState] = useState<AuthSessionResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isLoggingOut, setIsLoggingOut] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [flashMessage, setFlashMessage] = useState<string | null>(null);
  const [detailsOpen, setDetailsOpen] = useState(false);

  const authStatus = useMemo(() => {
    if (typeof window === "undefined") {
      return null;
    }

    const params = new URLSearchParams(window.location.search);
    if (params.get("auth") === "github_connected") {
      return {
        tone: "success" as const,
        message: "GitHub is connected and ready for authenticated repository access."
      };
    }

    const authError = params.get("auth_error");
    if (!authError) {
      return null;
    }

    if (authError === "github_oauth_denied") {
      return {
        tone: "warning" as const,
        message: "GitHub connection was canceled before completion."
      };
    }

    if (authError === "github_oauth_state_mismatch") {
      return {
        tone: "error" as const,
        message:
          "GitHub login could not be verified safely. Please start the connection again."
      };
    }

    if (authError === "github_oauth_unavailable") {
      return {
        tone: "error" as const,
        message:
          "GitHub login is not configured on the backend yet. Add the OAuth environment variables and try again."
      };
    }

    return {
      tone: "error" as const,
      message: "GitHub login did not complete successfully. Please try again."
    };
  }, []);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.has("auth") || params.has("auth_error")) {
      window.history.replaceState({}, document.title, window.location.pathname);
    }
  }, []);

  useEffect(() => {
    const loadAuthState = async () => {
      setIsLoading(true);
      setError(null);
      setFlashMessage(authStatus?.message ?? null);

      try {
        const response = await fetch(`${appConfig.apiBaseUrl}/api/auth/me`, {
          credentials: "include"
        });

        if (!response.ok) {
          setError("GitHub connection status is temporarily unavailable.");
          setAuthState({
            authenticated: false,
            status: "error",
            message: null,
            user: null
          });
          return;
        }

        const data = (await response.json()) as AuthSessionResponse;
        setAuthState(data);
      } catch {
        setError("Unable to contact the GitHub auth service right now.");
        setAuthState({
          authenticated: false,
          status: "error",
          message: null,
          user: null
        });
      } finally {
        setIsLoading(false);
      }
    };

    void loadAuthState();
  }, [authStatus]);

  const handleConnect = () => {
    setError(null);
    window.location.href = `${appConfig.apiBaseUrl}/api/auth/github/login`;
  };

  const handleLogout = async () => {
    setIsLoggingOut(true);
    setError(null);

    try {
      const response = await fetch(`${appConfig.apiBaseUrl}/api/auth/logout`, {
        method: "POST",
        credentials: "include"
      });

      if (!response.ok) {
        setError("GitHub could not be disconnected right now.");
        return;
      }

      const data = (await response.json()) as AuthSessionResponse;
      setAuthState(data);
      setFlashMessage(data.message ?? "GitHub account disconnected.");
    } catch {
      setError("GitHub could not be disconnected right now.");
    } finally {
      setIsLoggingOut(false);
    }
  };

  return (
    <>
      <Card className="border-slate-800/80 bg-slate-900/60 shadow-xl shadow-slate-950/30">
        <CardHeader className="border-b border-slate-800/80 pb-5 sm:px-6 sm:pt-6">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
            <div className="space-y-2">
              <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-500">
                Access
              </p>
              <div className="space-y-1">
                <CardTitle className="text-xl sm:text-2xl">
                  GitHub connection
                </CardTitle>
                <CardDescription className="max-w-3xl text-sm sm:text-[15px]">
                  Connect GitHub when you want the reviewer to work with private
                  repositories and pull requests using your own read access.
                </CardDescription>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Badge variant="info" className="px-3 py-1">
                Read-only access
              </Badge>
              <div className="rounded-2xl border border-slate-700/80 bg-slate-950/80 p-3 text-slate-200">
                <Github className="h-5 w-5" />
              </div>
            </div>
          </div>
        </CardHeader>

        <CardContent className="space-y-4 p-5 sm:p-6">
          {flashMessage ? (
            <AuthStatusBanner
              tone={authStatus?.tone ?? "success"}
              message={flashMessage}
            />
          ) : null}

          {error ? <AuthStatusBanner tone="error" message={error} /> : null}

          {isLoading ? (
            <div className="flex items-center gap-3 rounded-2xl border border-slate-800 bg-slate-950/50 p-4 text-sm text-slate-300">
              <LoaderCircle className="h-4 w-4 animate-spin" />
              Checking GitHub connection status...
            </div>
          ) : authState?.authenticated && authState.user ? (
            <div className="space-y-4 rounded-3xl border border-emerald-500/20 bg-emerald-500/[0.06] p-5">
              <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                <div className="flex items-center gap-4">
                  {authState.user.avatar_url ? (
                    <img
                      src={authState.user.avatar_url}
                      alt={authState.user.login}
                      className="h-14 w-14 rounded-2xl border border-slate-700 object-cover"
                    />
                  ) : (
                    <div className="flex h-14 w-14 items-center justify-center rounded-2xl border border-slate-700 bg-slate-900/80 text-slate-200">
                      <ShieldCheck className="h-5 w-5" />
                    </div>
                  )}
                  <div className="space-y-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="text-base font-semibold text-white">
                        {authState.user.name || authState.user.login}
                      </p>
                      <Badge
                        variant="default"
                        className="border-emerald-500/20 bg-emerald-500/10 px-2.5 py-1 text-emerald-100"
                      >
                        Connected
                      </Badge>
                    </div>
                    <p className="text-sm text-slate-300">@{authState.user.login}</p>
                    <p className="text-sm leading-6 text-slate-400">
                      Private pull request access is available anywhere your
                      GitHub account already has read permission.
                    </p>
                  </div>
                </div>
                <Button
                  type="button"
                  variant="outline"
                  size="lg"
                  disabled={isLoggingOut}
                  className="rounded-xl"
                  onClick={() => void handleLogout()}
                >
                  <LogOut className="mr-2 h-4 w-4" />
                  {isLoggingOut ? "Disconnecting..." : "Disconnect"}
                </Button>
              </div>

              <div className="grid gap-3 md:grid-cols-3">
                <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-400">
                    Access used
                  </p>
                  <p className="mt-3 text-sm font-medium text-slate-100">
                    Your GitHub read access
                  </p>
                </div>
                <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-400">
                    Scope
                  </p>
                  <p className="mt-3 text-sm font-medium text-slate-100">
                    Read-only identity
                  </p>
                </div>
                <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-400">
                    Token handling
                  </p>
                  <p className="mt-3 text-sm font-medium text-slate-100">
                    Server-side session only
                  </p>
                </div>
              </div>
            </div>
          ) : (
            <div className="space-y-4 rounded-3xl border border-slate-800 bg-slate-950/50 p-5">
              <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                <div className="space-y-3">
                  <p className="text-base font-semibold text-slate-100">
                    Connect GitHub for private repository access
                  </p>
                  <p className="max-w-2xl text-sm leading-6 text-slate-400">
                    Public pull requests already work without sign-in. GitHub
                    connection is only needed when you want the reviewer to
                    inspect private repositories and pull requests you can
                    already access.
                  </p>
                </div>
                <div className="flex flex-wrap gap-3">
                  <Button
                    type="button"
                    variant="outline"
                    size="lg"
                    className="rounded-xl"
                    onClick={() => setDetailsOpen(true)}
                  >
                    Why connect GitHub
                    <ChevronRight className="ml-2 h-4 w-4" />
                  </Button>
                  <Button
                    type="button"
                    size="lg"
                    className="rounded-xl px-5 text-sm font-semibold shadow-lg shadow-sky-950/40"
                    onClick={handleConnect}
                  >
                    <Link2 className="mr-2 h-4 w-4" />
                    Connect GitHub
                  </Button>
                </div>
              </div>

              <div className="grid gap-3 md:grid-cols-3">
                <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-400">
                    Why it is needed
                  </p>
                  <p className="mt-3 text-sm leading-6 text-slate-200">
                    Private pull requests and repository context require your
                    existing GitHub access.
                  </p>
                </div>
                <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-400">
                    What access is used
                  </p>
                  <p className="mt-3 text-sm leading-6 text-slate-200">
                    The app only uses read-oriented GitHub access to verify your
                    identity and read repository data.
                  </p>
                </div>
                <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-400">
                    Security model
                  </p>
                  <p className="mt-3 text-sm leading-6 text-slate-200">
                    Tokens stay server-side in an httpOnly session and are never
                    exposed to the browser UI.
                  </p>
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {detailsOpen ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 px-4 backdrop-blur-sm">
          <Card className="w-full max-w-3xl border-slate-800/90 bg-slate-900/95 shadow-2xl shadow-black/40">
            <CardHeader className="border-b border-slate-800/80 pb-5 sm:px-6 sm:pt-6">
              <div className="flex items-start justify-between gap-4">
                <div className="space-y-2">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-500">
                    GitHub access
                  </p>
                  <div className="space-y-1">
                    <CardTitle className="text-xl sm:text-2xl">
                      Why connect GitHub
                    </CardTitle>
                    <CardDescription className="max-w-2xl text-sm sm:text-[15px]">
                      GitHub connection lets the reviewer work with private pull
                      requests using the same read access you already have in
                      GitHub.
                    </CardDescription>
                  </div>
                </div>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="rounded-xl"
                  onClick={() => setDetailsOpen(false)}
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-4 p-5 sm:p-6">
              <div className="grid gap-4 md:grid-cols-3">
                <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
                  <div className="flex items-center gap-2 text-slate-200">
                    <LockKeyhole className="h-4 w-4" />
                    <p className="text-sm font-semibold">What the app uses</p>
                  </div>
                  <p className="mt-3 text-sm leading-6 text-slate-400">
                    A minimal GitHub OAuth flow to read your identity and use
                    your existing repository access for private pull requests.
                  </p>
                </div>
                <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
                  <div className="flex items-center gap-2 text-slate-200">
                    <ShieldCheck className="h-4 w-4" />
                    <p className="text-sm font-semibold">What it does not do</p>
                  </div>
                  <p className="mt-3 text-sm leading-6 text-slate-400">
                    No write actions, no repository mutations, and no token
                    exposure to the frontend.
                  </p>
                </div>
                <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
                  <div className="flex items-center gap-2 text-slate-200">
                    <Github className="h-4 w-4" />
                    <p className="text-sm font-semibold">When to connect</p>
                  </div>
                  <p className="mt-3 text-sm leading-6 text-slate-400">
                    Only when you want to analyze private repositories or when a
                    public preview indicates authenticated GitHub access is
                    required.
                  </p>
                </div>
              </div>

              <div className="rounded-3xl border border-slate-800 bg-slate-950/60 p-5">
                <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-400">
                  Access summary
                </p>
                <div className="mt-4 grid gap-3 md:grid-cols-2">
                  <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-4">
                    <p className="text-sm font-semibold text-slate-100">
                      Read-only usage
                    </p>
                    <p className="mt-2 text-sm leading-6 text-slate-400">
                      The reviewer reads pull request metadata, changed files,
                      and repository context needed for analysis.
                    </p>
                  </div>
                  <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-4">
                    <p className="text-sm font-semibold text-slate-100">
                      Server-side session handling
                    </p>
                    <p className="mt-2 text-sm leading-6 text-slate-400">
                      GitHub tokens stay in secure server-side session storage
                      behind httpOnly cookies.
                    </p>
                  </div>
                </div>
              </div>

              <div className="flex flex-col gap-3 sm:flex-row sm:justify-end">
                <Button
                  type="button"
                  variant="outline"
                  size="lg"
                  className="rounded-xl"
                  onClick={() => setDetailsOpen(false)}
                >
                  Maybe later
                </Button>
                <Button
                  type="button"
                  size="lg"
                  className="rounded-xl px-5 text-sm font-semibold shadow-lg shadow-sky-950/40"
                  onClick={handleConnect}
                >
                  <Link2 className="mr-2 h-4 w-4" />
                  Connect GitHub
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      ) : null}
    </>
  );
}
