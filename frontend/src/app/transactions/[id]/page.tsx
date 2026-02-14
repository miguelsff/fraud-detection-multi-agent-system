import { notFound } from "next/navigation";
import { getTransactionDetail, getTransactionTrace } from "@/lib/api";
import { TransactionDetailClient } from "@/components/transactions/TransactionDetailClient";

interface TransactionDetailPageProps {
  params: Promise<{ id: string }>;
}

export default async function TransactionDetailPage({
  params
}: TransactionDetailPageProps) {
  const { id: transactionId } = await params;

  let detail, trace;
  let error: string | null = null;

  try {
    // Parallel data fetching
    [detail, trace] = await Promise.all([
      getTransactionDetail(transactionId),
      getTransactionTrace(transactionId),
    ]);
  } catch (err: any) {
    if (err?.status === 404) {
      notFound();
    }
    error = err?.message || "Failed to load transaction";
  }

  if (error || !detail || !trace) {
    return (
      <div className="space-y-4">
        <h1 className="text-3xl font-bold">Error Loading Transaction</h1>
        <p className="text-muted-foreground">{error}</p>
      </div>
    );
  }

  return (
    <TransactionDetailClient
      transactionId={transactionId}
      detail={detail}
      trace={trace}
    />
  );
}
