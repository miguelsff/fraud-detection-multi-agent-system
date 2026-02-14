import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { FileQuestion, Home, ArrowLeft } from "lucide-react";

export default function NotFound() {
  return (
    <div className="flex items-center justify-center min-h-[calc(100vh-8rem)]">
      <Card className="max-w-md w-full">
        <CardContent className="pt-6">
          <div className="flex flex-col items-center text-center space-y-6">
            {/* Icon */}
            <div className="relative">
              <div className="absolute inset-0 animate-ping opacity-20">
                <FileQuestion className="h-24 w-24 text-muted-foreground" />
              </div>
              <FileQuestion className="h-24 w-24 text-muted-foreground relative" />
            </div>

            {/* Title */}
            <div className="space-y-2">
              <h1 className="text-4xl font-bold tracking-tight">404</h1>
              <h2 className="text-xl font-semibold">Page Not Found</h2>
              <p className="text-muted-foreground">
                The page you're looking for doesn't exist or has been moved.
              </p>
            </div>

            {/* Actions */}
            <div className="flex flex-col sm:flex-row gap-3 w-full">
              <Button
                variant="outline"
                className="flex-1"
                asChild
              >
                <Link href="javascript:history.back()">
                  <ArrowLeft className="mr-2 h-4 w-4" />
                  Go Back
                </Link>
              </Button>
              <Button className="flex-1" asChild>
                <Link href="/">
                  <Home className="mr-2 h-4 w-4" />
                  Dashboard
                </Link>
              </Button>
            </div>

            {/* Quick Links */}
            <div className="pt-4 border-t w-full">
              <p className="text-sm text-muted-foreground mb-3">Quick links:</p>
              <div className="flex flex-col gap-2 text-sm">
                <Link
                  href="/transactions"
                  className="text-primary hover:underline"
                >
                  View Transactions
                </Link>
                <Link
                  href="/analytics"
                  className="text-primary hover:underline"
                >
                  Analytics Dashboard
                </Link>
                <Link
                  href="/hitl"
                  className="text-primary hover:underline"
                >
                  HITL Queue
                </Link>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
