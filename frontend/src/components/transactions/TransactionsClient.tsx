"use client";

import { TransactionTable } from "@/components/transactions/TransactionTable";
import { AnalyzeButton } from "@/components/transactions/AnalyzeButton";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useTransactions } from "@/hooks/useTransactions";
import { RefreshCw } from "lucide-react";
import type { TransactionRecord } from "@/lib/types";

interface TransactionsClientProps {
  initialTransactions: TransactionRecord[];
  refreshInterval?: number; // in seconds
}

export function TransactionsClient({
  initialTransactions,
  refreshInterval = 30,
}: TransactionsClientProps) {
  const { transactions, isLoading, error, refresh } = useTransactions({
    limit: 100,
    offset: 0,
    refreshInterval,
  });

  // Use initial data if we haven't loaded yet
  const displayTransactions = transactions.length > 0 ? transactions : initialTransactions;
  const totalCount = displayTransactions.length;

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-3xl font-bold tracking-tight">Transacciones</h1>
            {refreshInterval > 0 && (
              <Badge variant="outline" className="bg-blue-500/10 text-blue-700 border-blue-500/20">
                Auto-actualización: {refreshInterval}s
              </Badge>
            )}
          </div>
          <p className="text-muted-foreground mt-1">
            {totalCount > 0 ? (
              <>
                Mostrando <span className="font-medium">{totalCount}</span> transacción{totalCount !== 1 ? 'es' : ''} analizada{totalCount !== 1 ? 's' : ''}
              </>
            ) : (
              "No hay transacciones analizadas aún"
            )}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={refresh}
            disabled={isLoading}
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
            Actualizar
          </Button>
        </div>
      </div>

      {/* Error Alert */}
      {error && (
        <div className="bg-destructive/10 border border-destructive/20 text-destructive px-4 py-3 rounded-lg">
          <p className="font-medium">Error al cargar transacciones</p>
          <p className="text-sm mt-1">{error}</p>
          <p className="text-sm mt-1">Asegúrate de que el backend esté ejecutándose en http://localhost:8000</p>
        </div>
      )}

      {/* Transactions Table */}
      <TransactionTable transactions={displayTransactions} />
    </div>
  );
}
