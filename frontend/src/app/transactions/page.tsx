import { getTransactions } from "@/lib/api";
import { TransactionsClient } from "@/components/transactions/TransactionsClient";
import { Skeleton } from "@/components/ui/skeleton";
import type { TransactionRecord } from "@/lib/types";

export default async function TransactionsPage() {
  // Fetch initial transactions on server
  let initialTransactions: TransactionRecord[];

  try {
    initialTransactions = await getTransactions(100, 0);
  } catch (err) {
    initialTransactions = [];
  }

  return (
    <TransactionsClient
      initialTransactions={initialTransactions}
      refreshInterval={30} // Auto-refresh every 30 seconds
    />
  );
}

// Loading skeleton for Suspense boundary
export function TransactionsLoading() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <Skeleton className="h-9 w-48" />
          <Skeleton className="h-5 w-64 mt-2" />
        </div>
        <Skeleton className="h-10 w-32" />
      </div>
      <div className="border rounded-lg p-8">
        <div className="space-y-4">
          <Skeleton className="h-12 w-full" />
          <Skeleton className="h-12 w-full" />
          <Skeleton className="h-12 w-full" />
          <Skeleton className="h-12 w-full" />
          <Skeleton className="h-12 w-full" />
        </div>
      </div>
    </div>
  );
}
