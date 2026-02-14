"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { BarChart3Icon } from "lucide-react";
import type { DecisionType } from "@/lib/types";
import { DECISION_COLORS } from "@/lib/types";

interface DecisionBreakdownChartProps {
  breakdown: Record<DecisionType, number>;
}

export function DecisionBreakdownChart({ breakdown }: DecisionBreakdownChartProps) {
  // Transform breakdown object into array format for recharts
  const chartData = [
    { name: "Approved", value: breakdown.APPROVE, fill: DECISION_COLORS.APPROVE },
    { name: "Challenged", value: breakdown.CHALLENGE, fill: DECISION_COLORS.CHALLENGE },
    { name: "Blocked", value: breakdown.BLOCK, fill: DECISION_COLORS.BLOCK },
    { name: "Escalated", value: breakdown.ESCALATE_TO_HUMAN, fill: DECISION_COLORS.ESCALATE_TO_HUMAN }
  ];

  const hasData = chartData.some(item => item.value > 0);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Decision Breakdown</CardTitle>
      </CardHeader>
      <CardContent>
        {!hasData ? (
          <div className="h-96 flex items-center justify-center">
            <div className="text-center">
              <BarChart3Icon className="mx-auto h-12 w-12 text-muted-foreground" />
              <p className="mt-4 text-muted-foreground">
                No decisions yet. Analyze transactions to see breakdown.
              </p>
            </div>
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={400}>
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
              <XAxis dataKey="name" />
              <YAxis />
              <Tooltip />
              <Bar dataKey="value" radius={[8, 8, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  );
}
