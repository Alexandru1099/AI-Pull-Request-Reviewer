export type AppConfig = {
  name: string;
  description: string;
  apiBaseUrl: string;
};

export const appConfig: AppConfig = {
  name: "Repo-Aware AI Pull Request Reviewer",
  description:
    "A future AI assistant that deeply understands your codebase to review pull requests with full repository context.",
  apiBaseUrl:
    process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000"
};

