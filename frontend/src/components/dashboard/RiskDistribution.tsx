"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { PieChart, Pie, Cell, Legend, Tooltip, ResponsiveContainer } from "recharts";
import { PieChartIcon } from "lucide-react";
import type { DecisionType as DecisionTypeFromTypes } from "@/lib/types";
import { DECISION_COLORS } from "@/lib/types";

interface RiskDistributionProps {
  breakdown: Record<DecisionTypeFromTypes, number>;
}

export function RiskDistribution({ breakdown }: RiskDistributionProps) {
  // Transform data for recharts
  const chartData = [
    { name: "Aprobado", value: breakdown.APPROVE, color: DECISION_COLORS.APPROVE },
    { name: "Desafiado", value: breakdown.CHALLENGE, color: DECISION_COLORS.CHALLENGE },
    { name: "Bloqueado", value: breakdown.BLOCK, color: DECISION_COLORS.BLOCK },
    { name: "Escalado", value: breakdown.ESCALATE_TO_HUMAN, color: DECISION_COLORS.ESCALATE_TO_HUMAN }
  ].filter(item => item.value > 0); // Only show categories with data

  const hasData = chartData.length > 0;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Distribución de Riesgo</CardTitle>
      </CardHeader>
      <CardContent>
        {!hasData ? (
          <div className="h-64 flex items-center justify-center">
            <div className="text-center">
              <PieChartIcon className="mx-auto h-12 w-12 text-muted-foreground" />
              <p className="mt-4 text-muted-foreground">
                Ejecuta un análisis para ver la distribución
              </p>
            </div>
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={chartData}
                cx="50%"
                cy="50%"
                innerRadius="60%"
                outerRadius="80%"
                dataKey="value"
                label={(entry) => `${entry.name}: ${entry.value}`}
              >
                {chartData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip />
              <Legend
                verticalAlign="bottom"
                height={36}
                formatter={(value, entry: any) => `${value}: ${entry.payload.value}`}
              />
            </PieChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  );
}
