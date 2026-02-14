"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import {
  Transaction,
  CustomerBehavior,
  TransactionSignals,
  BehavioralSignals,
} from "@/lib/types";
import { cn } from "@/lib/utils";

interface TransactionDetailCardProps {
  transaction: Transaction;
  customerBehavior: CustomerBehavior | null;
  transactionSignals: TransactionSignals | null;
  behavioralSignals: BehavioralSignals | null;
}

export function TransactionDetailCard({
  transaction,
  customerBehavior,
  transactionSignals,
  behavioralSignals,
}: TransactionDetailCardProps) {
  // Determine highlighting based on signals
  const isAmountHigh = (transactionSignals?.amount_ratio || 0) > 2.5;
  const isOffHours = transactionSignals?.is_off_hours || false;
  const isForeign = transactionSignals?.is_foreign || false;
  const isUnknownDevice = transactionSignals?.is_unknown_device || false;
  const channelRisk = transactionSignals?.channel_risk || "low";

  const formatCurrency = (amount: number, currency: string) => {
    const symbol = currency === "PEN" ? "S/" : "$";
    return `${symbol} ${amount.toFixed(2)}`;
  };

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleString("en-US", {
      dateStyle: "medium",
      timeStyle: "short",
    });
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Transaction Details</CardTitle>
      </CardHeader>
      <CardContent>
        <Tabs defaultValue="transaction" className="w-full">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="transaction">Transaction Info</TabsTrigger>
            <TabsTrigger value="customer">Customer Profile</TabsTrigger>
          </TabsList>

          <TabsContent value="transaction" className="space-y-4 mt-4">
            <div className="grid grid-cols-2 gap-4">
              {/* Transaction ID */}
              <div className="space-y-1">
                <p className="text-sm text-muted-foreground">Transaction ID</p>
                <p className="text-sm font-mono font-semibold">
                  {transaction.transaction_id}
                </p>
              </div>

              {/* Customer ID */}
              <div className="space-y-1">
                <p className="text-sm text-muted-foreground">Customer ID</p>
                <p className="text-sm font-mono font-semibold">
                  {transaction.customer_id}
                </p>
              </div>

              {/* Amount */}
              <div className="space-y-1">
                <p className="text-sm text-muted-foreground">Amount</p>
                <p
                  className={cn(
                    "text-sm font-semibold",
                    isAmountHigh && "text-red-600 dark:text-red-400"
                  )}
                >
                  {formatCurrency(transaction.amount, transaction.currency)}
                  {isAmountHigh && (
                    <Badge variant="destructive" className="ml-2 text-xs">
                      High Amount
                    </Badge>
                  )}
                </p>
              </div>

              {/* Timestamp */}
              <div className="space-y-1">
                <p className="text-sm text-muted-foreground">Timestamp</p>
                <p
                  className={cn(
                    "text-sm font-semibold",
                    isOffHours && "text-amber-600 dark:text-amber-400"
                  )}
                >
                  {formatTimestamp(transaction.timestamp)}
                  {isOffHours && (
                    <Badge
                      variant="outline"
                      className="ml-2 text-xs bg-amber-500/10 text-amber-700 border-amber-500/20"
                    >
                      Off Hours
                    </Badge>
                  )}
                </p>
              </div>

              {/* Country */}
              <div className="space-y-1">
                <p className="text-sm text-muted-foreground">Country</p>
                <p
                  className={cn(
                    "text-sm font-semibold",
                    isForeign && "text-amber-600 dark:text-amber-400"
                  )}
                >
                  {transaction.country}
                  {isForeign && (
                    <Badge
                      variant="outline"
                      className="ml-2 text-xs bg-amber-500/10 text-amber-700 border-amber-500/20"
                    >
                      Foreign
                    </Badge>
                  )}
                </p>
              </div>

              {/* Channel */}
              <div className="space-y-1">
                <p className="text-sm text-muted-foreground">Channel</p>
                <p
                  className={cn(
                    "text-sm font-semibold capitalize",
                    channelRisk === "high" && "text-red-600 dark:text-red-400",
                    channelRisk === "medium" &&
                      "text-amber-600 dark:text-amber-400"
                  )}
                >
                  {transaction.channel}
                  {channelRisk === "high" && (
                    <Badge variant="destructive" className="ml-2 text-xs">
                      High Risk
                    </Badge>
                  )}
                  {channelRisk === "medium" && (
                    <Badge
                      variant="outline"
                      className="ml-2 text-xs bg-amber-500/10 text-amber-700 border-amber-500/20"
                    >
                      Medium Risk
                    </Badge>
                  )}
                </p>
              </div>

              {/* Device ID */}
              <div className="space-y-1">
                <p className="text-sm text-muted-foreground">Device ID</p>
                <p
                  className={cn(
                    "text-sm font-mono font-semibold",
                    isUnknownDevice && "text-amber-600 dark:text-amber-400"
                  )}
                >
                  {transaction.device_id}
                  {isUnknownDevice && (
                    <Badge
                      variant="outline"
                      className="ml-2 text-xs bg-amber-500/10 text-amber-700 border-amber-500/20"
                    >
                      Unknown
                    </Badge>
                  )}
                </p>
              </div>

              {/* Merchant ID */}
              <div className="space-y-1">
                <p className="text-sm text-muted-foreground">Merchant ID</p>
                <p className="text-sm font-mono font-semibold">
                  {transaction.merchant_id}
                </p>
              </div>
            </div>

            {/* Flags */}
            {transactionSignals && transactionSignals.flags.length > 0 && (
              <div className="space-y-2 pt-4 border-t">
                <p className="text-sm text-muted-foreground">Detected Flags</p>
                <div className="flex flex-wrap gap-2">
                  {transactionSignals.flags.map((flag, idx) => (
                    <Badge key={idx} variant="outline" className="text-xs">
                      {flag}
                    </Badge>
                  ))}
                </div>
              </div>
            )}
          </TabsContent>

          <TabsContent value="customer" className="space-y-4 mt-4">
            {customerBehavior ? (
              <div className="grid grid-cols-2 gap-4">
                {/* Customer ID */}
                <div className="space-y-1">
                  <p className="text-sm text-muted-foreground">Customer ID</p>
                  <p className="text-sm font-mono font-semibold">
                    {customerBehavior.customer_id}
                  </p>
                </div>

                {/* Usual Amount */}
                <div className="space-y-1">
                  <p className="text-sm text-muted-foreground">
                    Usual Amount (Avg)
                  </p>
                  <p className="text-sm font-semibold">
                    {formatCurrency(
                      customerBehavior.usual_amount_avg,
                      transaction.currency
                    )}
                  </p>
                </div>

                {/* Usual Hours */}
                <div className="space-y-1">
                  <p className="text-sm text-muted-foreground">Usual Hours</p>
                  <p className="text-sm font-semibold">
                    {customerBehavior.usual_hours}
                  </p>
                </div>

                {/* Usual Countries */}
                <div className="space-y-1">
                  <p className="text-sm text-muted-foreground">
                    Usual Countries
                  </p>
                  <div className="flex flex-wrap gap-1">
                    {customerBehavior.usual_countries.map((country, idx) => (
                      <Badge key={idx} variant="secondary" className="text-xs">
                        {country}
                      </Badge>
                    ))}
                  </div>
                </div>

                {/* Usual Devices */}
                <div className="col-span-2 space-y-1">
                  <p className="text-sm text-muted-foreground">
                    Usual Devices
                  </p>
                  <div className="flex flex-wrap gap-1">
                    {customerBehavior.usual_devices.map((device, idx) => (
                      <Badge
                        key={idx}
                        variant="secondary"
                        className="text-xs font-mono"
                      >
                        {device}
                      </Badge>
                    ))}
                  </div>
                </div>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">
                No customer behavior data available
              </p>
            )}
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}
