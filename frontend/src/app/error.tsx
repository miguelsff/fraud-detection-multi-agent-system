"use client";

import { useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { AlertTriangle, RefreshCw, Home } from "lucide-react";
import Link from "next/link";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Log error to console in development
    console.error("Application error:", error);
  }, [error]);

  return (
    <div className="flex items-center justify-center min-h-[calc(100vh-8rem)]">
      <Card className="max-w-lg w-full">
        <CardHeader>
          <div className="flex items-center gap-3">
            <div className="p-2 bg-destructive/10 rounded-full">
              <AlertTriangle className="h-6 w-6 text-destructive" />
            </div>
            <CardTitle>Something went wrong</CardTitle>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-muted-foreground">
            An unexpected error occurred while loading this page. This could be due to a network issue,
            server problem, or a bug in the application.
          </p>

          {/* Error Details (only in development) */}
          {process.env.NODE_ENV === "development" && (
            <div className="bg-muted p-4 rounded-lg">
              <p className="text-sm font-mono text-destructive break-all">
                {error.message}
              </p>
              {error.digest && (
                <p className="text-xs text-muted-foreground mt-2">
                  Error ID: {error.digest}
                </p>
              )}
            </div>
          )}

          <div className="bg-blue-50 dark:bg-blue-950/20 border border-blue-200 dark:border-blue-900 p-4 rounded-lg">
            <p className="text-sm text-blue-900 dark:text-blue-100">
              <strong>What you can try:</strong>
            </p>
            <ul className="text-sm text-blue-800 dark:text-blue-200 mt-2 space-y-1 list-disc list-inside">
              <li>Refresh the page using the button below</li>
              <li>Check your internet connection</li>
              <li>Verify the backend is running (http://localhost:8000)</li>
              <li>Return to the dashboard and try again</li>
            </ul>
          </div>
        </CardContent>
        <CardFooter className="flex gap-3">
          <Button
            variant="outline"
            className="flex-1"
            onClick={reset}
          >
            <RefreshCw className="mr-2 h-4 w-4" />
            Try Again
          </Button>
          <Button className="flex-1" asChild>
            <Link href="/">
              <Home className="mr-2 h-4 w-4" />
              Go Home
            </Link>
          </Button>
        </CardFooter>
      </Card>
    </div>
  );
}
