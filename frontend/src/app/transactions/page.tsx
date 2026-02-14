import { getTransactions } from "@/lib/api";
import { TransactionTable } from "@/components/transactions/TransactionTable";
import { AnalyzeButton } from "@/components/transactions/AnalyzeButton";
import { Skeleton } from "@/components/ui/skeleton";
import type { TransactionRecord } from "@/lib/types";

export default async function TransactionsPage() {
  // Fetch all transactions (could add pagination later)
  let transactions: TransactionRecord[];
  let error: string | null = null;

  try {
    transactions = await getTransactions(100, 0); // Get up to 100 transactions
  } catch (err) {
    error = err instanceof Error ? err.message : "Failed to fetch transactions";
    transactions = [];
  }

  const totalCount = transactions.length;

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Transactions</h1>
          <p className="text-muted-foreground mt-1">
            {totalCount > 0 ? (
              <>
                Showing <span className="font-medium">{totalCount}</span> analyzed transaction{totalCount !== 1 ? 's' : ''}
              </>
            ) : (
              "No transactions analyzed yet"
            )}
          </p>
        </div>
        <AnalyzeButton />
      </div>

      {/* Error Alert */}
      {error && (
        <div className="bg-destructive/10 border border-destructive/20 text-destructive px-4 py-3 rounded-lg">
          <p className="font-medium">Failed to load transactions</p>
          <p className="text-sm mt-1">{error}</p>
          <p className="text-sm mt-1">Make sure the backend is running on http://localhost:8000</p>
        </div>
      )}

      {/* Transactions Table */}
      <TransactionTable transactions={transactions} />
    </div>
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
