import type { Metadata } from "next";
import "./globals.css";
import { AppProvider } from "../lib/state";
import { Shell } from "../components/Shell";

export const metadata: Metadata = {
  title: "CHIMERA — Cyber Incident Correlation",
  description: "Reconstruct multi-stage attacks from distributed telemetry without ML hallucinations.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <AppProvider>
          <Shell>{children}</Shell>
        </AppProvider>
      </body>
    </html>
  );
}
