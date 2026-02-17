import { AlertCircle } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";

export default function TransactionNotFound() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-4">
      <AlertCircle className="h-16 w-16 text-muted-foreground" />
      <h1 className="text-3xl font-bold">Transaction Not Found</h1>
      <p className="text-muted-foreground text-center max-w-md">
        The transaction you're looking for doesn't exist or hasn't been analyzed yet.
      </p>
      <Button asChild>
        <Link href="/transactions">View All Transactions</Link>
      </Button>
    </div>
  );
}
