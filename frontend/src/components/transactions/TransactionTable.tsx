"use client";

import { useState, useMemo } from "react";
import { useRouter } from "next/navigation";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { FileQuestion, ArrowUpDown, ArrowUp, ArrowDown } from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import type { TransactionRecord, DecisionType } from "@/lib/types";

interface TransactionTableProps {
  transactions: TransactionRecord[];
}

type SortColumn = "id" | "customer_id" | "amount" | "decision" | "confidence" | "created_at";
type SortDirection = "asc" | "desc";

export function TransactionTable({ transactions }: TransactionTableProps) {
  const router = useRouter();
  const [sortColumn, setSortColumn] = useState<SortColumn>("created_at");
  const [sortDirection, setSortDirection] = useState<SortDirection>("desc");

  const handleSort = (column: SortColumn) => {
    if (sortColumn === column) {
      setSortDirection(sortDirection === "asc" ? "desc" : "asc");
    } else {
      setSortColumn(column);
      setSortDirection("asc");
    }
  };

  const sortedTransactions = useMemo(() => {
    return [...transactions].sort((a, b) => {
      let aValue: any;
      let bValue: any;

      switch (sortColumn) {
        case "id":
          aValue = a.id;
          bValue = b.id;
          break;
        case "customer_id":
          aValue = a.raw_data.customer_id;
          bValue = b.raw_data.customer_id;
          break;
        case "amount":
          aValue = a.raw_data.amount;
          bValue = b.raw_data.amount;
          break;
        case "decision":
          aValue = a.decision;
          bValue = b.decision;
          break;
        case "confidence":
          aValue = a.confidence;
          bValue = b.confidence;
          break;
        case "created_at":
          aValue = new Date(a.created_at).getTime();
          bValue = new Date(b.created_at).getTime();
          break;
      }

      if (sortDirection === "asc") {
        return aValue > bValue ? 1 : -1;
      } else {
        return aValue < bValue ? 1 : -1;
      }
    });
  }, [transactions, sortColumn, sortDirection]);

  const formatAmount = (amount: number, currency: string) => {
    const currencySymbol = currency === "PEN" ? "S/" : "$";
    const locale = currency === "PEN" ? "es-PE" : "en-US";

    return new Intl.NumberFormat(locale, {
      style: "currency",
      currency: currency === "PEN" ? "PEN" : "USD",
    }).format(amount).replace("PEN", "S/");
  };

  const truncateId = (id: string, maxLength: number = 12) => {
    return id.length > maxLength ? `${id.slice(0, maxLength)}...` : id;
  };

  const getDecisionBadgeProps = (decision: DecisionType) => {
    switch (decision) {
      case "APPROVE":
        return { variant: "default" as const, className: "bg-approve text-white hover:bg-approve/90" };
      case "CHALLENGE":
        return { variant: "secondary" as const, className: "bg-challenge text-white hover:bg-challenge/90" };
      case "BLOCK":
        return { variant: "destructive" as const };
      case "ESCALATE_TO_HUMAN":
        return { variant: "outline" as const, className: "border-escalate text-escalate" };
      default:
        return { variant: "outline" as const };
    }
  };

  const formatDecisionName = (decision: DecisionType) => {
    switch (decision) {
      case "APPROVE":
        return "Aprobado";
      case "CHALLENGE":
        return "Desafiado";
      case "BLOCK":
        return "Bloqueado";
      case "ESCALATE_TO_HUMAN":
        return "Escalado";
      default:
        return decision;
    }
  };

  const SortIcon = ({ column }: { column: SortColumn }) => {
    if (sortColumn !== column) {
      return <ArrowUpDown className="ml-2 h-4 w-4 inline opacity-50" />;
    }
    return sortDirection === "asc" ? (
      <ArrowUp className="ml-2 h-4 w-4 inline" />
    ) : (
      <ArrowDown className="ml-2 h-4 w-4 inline" />
    );
  };

  if (transactions.length === 0) {
    return (
      <div className="text-center py-12 border rounded-lg bg-muted/10">
        <FileQuestion className="mx-auto h-16 w-16 text-muted-foreground" />
        <p className="mt-4 text-lg font-medium">No se encontraron transacciones</p>
        <p className="text-muted-foreground mt-2">
          Haz clic en &quot;Analizar Nueva&quot; para procesar tu primera transacción
        </p>
      </div>
    );
  }

  return (
    <div className="border rounded-lg overflow-hidden">
      <div className="overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead
                className="cursor-pointer hover:bg-muted/50"
                onClick={() => handleSort("id")}
              >
                ID <SortIcon column="id" />
              </TableHead>
              <TableHead
                className="cursor-pointer hover:bg-muted/50"
                onClick={() => handleSort("customer_id")}
              >
                Cliente <SortIcon column="customer_id" />
              </TableHead>
              <TableHead
                className="cursor-pointer hover:bg-muted/50"
                onClick={() => handleSort("amount")}
              >
                Monto <SortIcon column="amount" />
              </TableHead>
              <TableHead>País</TableHead>
              <TableHead>Canal</TableHead>
              <TableHead
                className="cursor-pointer hover:bg-muted/50"
                onClick={() => handleSort("decision")}
              >
                Decisión <SortIcon column="decision" />
              </TableHead>
              <TableHead
                className="cursor-pointer hover:bg-muted/50"
                onClick={() => handleSort("confidence")}
              >
                Confianza <SortIcon column="confidence" />
              </TableHead>
              <TableHead
                className="cursor-pointer hover:bg-muted/50"
                onClick={() => handleSort("created_at")}
              >
                Fecha <SortIcon column="created_at" />
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {sortedTransactions.map((transaction) => {
              const badgeProps = getDecisionBadgeProps(transaction.decision);
              const confidencePercent = (transaction.confidence * 100).toFixed(1);

              return (
                <TableRow
                  key={transaction.id}
                  onClick={() => router.push(`/transactions/${transaction.transaction_id}`)}
                  className="cursor-pointer hover:bg-muted/50 transition-colors"
                >
                  <TableCell className="font-mono text-sm">
                    {truncateId(transaction.transaction_id)}
                  </TableCell>
                  <TableCell className="font-medium">
                    {transaction.raw_data.customer_id}
                  </TableCell>
                  <TableCell className="font-medium">
                    {formatAmount(transaction.raw_data.amount, transaction.raw_data.currency)}
                  </TableCell>
                  <TableCell>
                    <span className="font-mono text-sm">{transaction.raw_data.country}</span>
                  </TableCell>
                  <TableCell>
                    <span className="capitalize">{transaction.raw_data.channel}</span>
                  </TableCell>
                  <TableCell>
                    <Badge {...badgeProps}>
                      {formatDecisionName(transaction.decision)}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <span className="text-sm min-w-[3rem]">{confidencePercent}%</span>
                      <div className="w-20 h-2 bg-muted rounded-full overflow-hidden">
                        <div
                          className="h-full bg-primary transition-all"
                          style={{ width: `${confidencePercent}%` }}
                        />
                      </div>
                    </div>
                  </TableCell>
                  <TableCell className="text-muted-foreground text-sm">
                    {formatDistanceToNow(new Date(transaction.created_at), { addSuffix: true })}
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
