"use client";

import { useRouter } from "next/navigation";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { formatDistanceToNow } from "date-fns";
import { FileQuestion } from "lucide-react";
import type { TransactionRecord, DecisionType } from "@/lib/types";

interface RecentDecisionsProps {
  transactions: TransactionRecord[];
}

export function RecentDecisions({ transactions }: RecentDecisionsProps) {
  const router = useRouter();

  const handleRowClick = (transactionId: string) => {
    router.push(`/transactions/${transactionId}`);
  };

  const formatAmount = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD'
    }).format(amount);
  };

  const truncateId = (id: string) => {
    return id.length > 12 ? `${id.slice(0, 12)}...` : id;
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
        return "Approved";
      case "CHALLENGE":
        return "Challenged";
      case "BLOCK":
        return "Blocked";
      case "ESCALATE_TO_HUMAN":
        return "Escalated";
      default:
        return decision;
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Recent Decisions</CardTitle>
      </CardHeader>
      <CardContent>
        {transactions.length === 0 ? (
          <div className="text-center py-12">
            <FileQuestion className="mx-auto h-12 w-12 text-muted-foreground" />
            <p className="mt-4 text-muted-foreground">
              No transactions analyzed yet
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Transaction ID</TableHead>
                  <TableHead>Amount</TableHead>
                  <TableHead>Decision</TableHead>
                  <TableHead>Confidence</TableHead>
                  <TableHead>Time</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {transactions.map((transaction) => {
                  const badgeProps = getDecisionBadgeProps(transaction.decision);
                  const confidencePercent = (transaction.confidence * 100).toFixed(1);

                  return (
                    <TableRow
                      key={transaction.transaction_id}
                      onClick={() => handleRowClick(transaction.transaction_id)}
                      className="cursor-pointer hover:bg-muted/50 transition-colors"
                    >
                      <TableCell className="font-mono text-sm">
                        {truncateId(transaction.transaction_id)}
                      </TableCell>
                      <TableCell className="font-medium">
                        {formatAmount(transaction.raw_data.amount)}
                      </TableCell>
                      <TableCell>
                        <Badge {...badgeProps}>
                          {formatDecisionName(transaction.decision)}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <span className="text-sm">{confidencePercent}%</span>
                          <div className="w-16 h-2 bg-muted rounded-full overflow-hidden">
                            <div
                              className="h-full bg-primary transition-all"
                              style={{ width: `${confidencePercent}%` }}
                            />
                          </div>
                        </div>
                      </TableCell>
                      <TableCell className="text-muted-foreground text-sm">
                        {formatDistanceToNow(new Date(transaction.analyzed_at), { addSuffix: true })}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
