"use client";

import { useMemo } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { GlobeIcon } from "lucide-react";
import type { TransactionRecord } from "@/lib/types";

interface RiskByCountryProps {
  transactions: TransactionRecord[];
}

interface CountryStats {
  country: string;
  total: number;
  avgRiskScore: number;
  blockedPercentage: number;
}

export function RiskByCountry({ transactions }: RiskByCountryProps) {
  const countryStats = useMemo<CountryStats[]>(() => {
    const map = new Map<string, { total: number; riskSum: number; blockedCount: number }>();

    transactions.forEach(t => {
      const country = t.raw_data.country || "Unknown";
      if (!map.has(country)) {
        map.set(country, { total: 0, riskSum: 0, blockedCount: 0 });
      }
      const stats = map.get(country)!;
      stats.total++;
      stats.riskSum += (1 - t.confidence);
      if (t.decision === "BLOCK") stats.blockedCount++;
    });

    return Array.from(map.values())
      .map(s => ({
        country: Array.from(map.entries()).find(([_, v]) => v === s)![0],
        total: s.total,
        avgRiskScore: (s.riskSum / s.total) * 100,
        blockedPercentage: (s.blockedCount / s.total) * 100
      }))
      .sort((a, b) => b.blockedPercentage - a.blockedPercentage)
      .slice(0, 20);
  }, [transactions]);

  const hasData = countryStats.length > 0;

  const getBlockedBadgeVariant = (percentage: number): string => {
    if (percentage >= 50) return "bg-red-500 text-white";
    if (percentage >= 25) return "bg-orange-500 text-white";
    if (percentage >= 10) return "bg-amber-500 text-white";
    return "bg-green-500 text-white";
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Risk by Country</CardTitle>
      </CardHeader>
      <CardContent>
        {!hasData ? (
          <div className="h-80 flex items-center justify-center">
            <div className="text-center">
              <GlobeIcon className="mx-auto h-12 w-12 text-muted-foreground" />
              <p className="mt-4 text-muted-foreground">
                No transactions yet. Analyze transactions to see country risk.
              </p>
            </div>
          </div>
        ) : (
          <div className="max-h-[400px] overflow-y-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Country</TableHead>
                  <TableHead className="text-right">Total</TableHead>
                  <TableHead className="text-right">Avg Risk</TableHead>
                  <TableHead className="text-right">Blocked %</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {countryStats.map((stat) => (
                  <TableRow key={stat.country}>
                    <TableCell className="font-medium">{stat.country}</TableCell>
                    <TableCell className="text-right">{stat.total}</TableCell>
                    <TableCell className="text-right">
                      {stat.avgRiskScore.toFixed(1)}%
                    </TableCell>
                    <TableCell className="text-right">
                      <Badge className={getBlockedBadgeVariant(stat.blockedPercentage)}>
                        {stat.blockedPercentage.toFixed(1)}%
                      </Badge>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
