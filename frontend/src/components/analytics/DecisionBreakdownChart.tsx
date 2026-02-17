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
    { name: "Aprobado", value: breakdown.APPROVE, fill: DECISION_COLORS.APPROVE },
    { name: "Desafiado", value: breakdown.CHALLENGE, fill: DECISION_COLORS.CHALLENGE },
    { name: "Bloqueado", value: breakdown.BLOCK, fill: DECISION_COLORS.BLOCK },
    { name: "Escalado", value: breakdown.ESCALATE_TO_HUMAN, fill: DECISION_COLORS.ESCALATE_TO_HUMAN }
  ];

  const hasData = chartData.some(item => item.value > 0);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Desglose de Decisiones</CardTitle>
      </CardHeader>
      <CardContent>
        {!hasData ? (
          <div className="h-96 flex items-center justify-center">
            <div className="text-center">
              <BarChart3Icon className="mx-auto h-12 w-12 text-muted-foreground" />
              <p className="mt-4 text-muted-foreground">
                No hay decisiones aún. Analiza transacciones para ver el desglose.
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
