import type { Metadata } from "next";
import { appConfig } from "@/lib/config";
import "./globals.css";

export const metadata: Metadata = {
  title: appConfig.name,
  description: appConfig.description,
  openGraph: {
    title: appConfig.name,
    description: appConfig.description,
    type: "website"
  }
};

type RootLayoutProps = {
  children: React.ReactNode;
};

export default function RootLayout({ children }: RootLayoutProps) {
  return (
    <html lang="en" className="bg-slate-950">
      <body className="min-h-screen bg-slate-950 antialiased">
        {children}
      </body>
    </html>
  );
}

