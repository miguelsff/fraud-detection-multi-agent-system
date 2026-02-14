"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from "recharts";
import { ClockIcon } from "lucide-react";

interface ProcessingTimeData {
  index: number;
  transactionId: string;
  processingTime: number;
  timestamp: string;
}

interface ProcessingTimeChartProps {
  data: ProcessingTimeData[];
  avgTime: number;
}

function formatTime(ms: number): string {
  if (ms < 1000) {
    return `${ms.toFixed(0)}ms`;
  }
  return `${(ms / 1000).toFixed(2)}s`;
}

export function ProcessingTimeChart({ data, avgTime }: ProcessingTimeChartProps) {
  const hasData = data.length > 0;

  // Calculate performance indicator
  const getPerformanceIndicator = (avgMs: number): { label: string; variant: string } => {
    if (avgMs < 5000) return { label: "Excellent", variant: "bg-green-500 text-white" };
    if (avgMs < 10000) return { label: "Acceptable", variant: "bg-amber-500 text-white" };
    return { label: "Slow", variant: "bg-red-500 text-white" };
  };

  const performance = getPerformanceIndicator(avgTime);

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>Processing Time Trend</CardTitle>
          {hasData && (
            <div className="flex items-center gap-2">
              <span className="text-sm text-muted-foreground">
                Avg: {formatTime(avgTime)}
              </span>
              <Badge className={performance.variant}>
                {performance.label}
              </Badge>
            </div>
          )}
        </div>
      </CardHeader>
      <CardContent>
        {!hasData ? (
          <div className="h-96 flex items-center justify-center">
            <div className="text-center">
              <ClockIcon className="mx-auto h-12 w-12 text-muted-foreground" />
              <p className="mt-4 text-muted-foreground">
                No processing data yet. Analyze transactions to see trends.
              </p>
            </div>
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={400}>
            <LineChart data={data}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
              <XAxis
                dataKey="index"
                label={{ value: "Transaction (most recent 50)", position: "insideBottom", offset: -5 }}
              />
              <YAxis
                label={{ value: "Time (ms)", angle: -90, position: "insideLeft" }}
              />
              <Tooltip
                content={({ active, payload }) => {
                  if (active && payload && payload.length) {
                    const data = payload[0].payload as ProcessingTimeData;
                    return (
                      <div className="bg-background border border-border rounded-lg px-3 py-2 shadow-md">
                        <p className="text-sm font-medium">{data.transactionId}</p>
                        <p className="text-sm text-muted-foreground">
                          Time: {formatTime(data.processingTime)}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {new Date(data.timestamp).toLocaleString()}
                        </p>
                      </div>
                    );
                  }
                  return null;
                }}
              />
              {/* 10s target threshold (red) */}
              <ReferenceLine
                y={10000}
                stroke="#ef4444"
                strokeDasharray="5 5"
                label={{ value: "10s target", position: "right", fill: "#ef4444" }}
              />
              {/* 5s fast threshold (green) */}
              <ReferenceLine
                y={5000}
                stroke="#22c55e"
                strokeDasharray="5 5"
                label={{ value: "5s fast", position: "right", fill: "#22c55e" }}
              />
              {/* Actual processing time line */}
              <Line
                type="monotone"
                dataKey="processingTime"
                stroke="#3b82f6"
                strokeWidth={2}
                dot={{ fill: "#3b82f6", r: 3 }}
                activeDot={{ r: 5 }}
              />
            </LineChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  );
}
