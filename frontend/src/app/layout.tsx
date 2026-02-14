import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Sidebar } from "@/components/layout/Sidebar";
import { Header } from "@/components/layout/Header";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
});

export const metadata: Metadata = {
  title: "FraudGuard - Multi-Agent Fraud Detection",
  description: "Advanced fraud detection system powered by multi-agent AI architecture",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${inter.variable} font-sans antialiased`}>
        {/* Fixed Sidebar (desktop only) */}
        <Sidebar />

        {/* Main content area with offset for sidebar */}
        <div className="lg:pl-60">
          {/* Sticky Header */}
          <Header />

          {/* Page content */}
          <main className="p-6">
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
