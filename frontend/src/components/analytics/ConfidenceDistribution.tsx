"use client";

import { useMemo } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { TrendingUpIcon } from "lucide-react";
import type { TransactionRecord } from "@/lib/types";

interface ConfidenceDistributionProps {
  transactions: TransactionRecord[];
}

export function ConfidenceDistribution({ transactions }: ConfidenceDistributionProps) {
  // Calculate confidence buckets
  const buckets = useMemo(() => {
    const ranges = [
      { label: "0-20%", min: 0, max: 0.2 },
      { label: "20-40%", min: 0.2, max: 0.4 },
      { label: "40-60%", min: 0.4, max: 0.6 },
      { label: "60-80%", min: 0.6, max: 0.8 },
      { label: "80-100%", min: 0.8, max: 1.01 }
    ];

    return ranges.map(range => ({
      bucket: range.label,
      count: transactions.filter(t =>
        t.confidence >= range.min && t.confidence < range.max
      ).length
    }));
  }, [transactions]);

  const hasData = transactions.length > 0;
  const isLimitedData = transactions.length < 10;

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>Confidence Distribution</CardTitle>
          {isLimitedData && hasData && (
            <Badge variant="outline" className="bg-amber-500/10 text-amber-600 border-amber-500/20">
              Limited data
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent>
        {!hasData ? (
          <div className="h-80 flex items-center justify-center">
            <div className="text-center">
              <TrendingUpIcon className="mx-auto h-12 w-12 text-muted-foreground" />
              <p className="mt-4 text-muted-foreground">
                No transactions yet. Analyze transactions to see distribution.
              </p>
            </div>
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={320}>
            <AreaChart data={buckets}>
              <defs>
                <linearGradient id="colorCount" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.8}/>
                  <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0.1}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
              <XAxis dataKey="bucket" />
              <YAxis />
              <Tooltip
                content={({ active, payload }) => {
                  if (active && payload && payload.length) {
                    return (
                      <div className="bg-background border border-border rounded-lg px-3 py-2 shadow-md">
                        <p className="text-sm font-medium">{payload[0].payload.bucket}</p>
                        <p className="text-sm text-muted-foreground">
                          Transactions: {payload[0].value}
                        </p>
                      </div>
                    );
                  }
                  return null;
                }}
              />
              <Area
                type="monotone"
                dataKey="count"
                stroke="#8b5cf6"
                strokeWidth={2}
                fillOpacity={1}
                fill="url(#colorCount)"
              />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  );
}
