import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Activity, TrendingUp, TrendingDown, UserCheck, Zap } from "lucide-react";
import type { AnalyticsSummary } from "@/lib/types";

interface StatsCardsProps {
  analytics: AnalyticsSummary;
}

export function StatsCards({ analytics }: StatsCardsProps) {
  const confidencePercent = (analytics.avg_confidence * 100).toFixed(1);
  const escalationPercent = (analytics.escalation_rate * 100).toFixed(1);
  const processingTime = analytics.avg_processing_time_ms.toFixed(0);

  // Color and interpretation logic
  const getConfidenceColor = (conf: number): string => {
    if (conf > 0.8) return "text-approve";
    if (conf > 0.6) return "text-challenge";
    return "text-block";
  };

  const getConfidenceInterpretation = (conf: number): string => {
    if (conf > 0.8) return "Excelente";
    if (conf > 0.6) return "Bueno";
    return "Requiere revisión";
  };

  const getProcessingColor = (ms: number): string => {
    if (ms < 5000) return "text-approve";
    if (ms < 10000) return "text-challenge";
    return "text-block";
  };

  const getProcessingLabel = (ms: number): string => {
    if (ms < 5000) return "Rápido";
    if (ms < 10000) return "Aceptable";
    return "Lento";
  };

  const confidenceColor = getConfidenceColor(analytics.avg_confidence);
  const ConfidenceIcon = analytics.avg_confidence > 0.7 ? TrendingUp : TrendingDown;
  const processingColor = getProcessingColor(analytics.avg_processing_time_ms);

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      {/* Card 1: Total Analyzed */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Total Analizadas</CardTitle>
          <Activity className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{analytics.total_analyzed.toLocaleString()}</div>
          <p className="text-xs text-muted-foreground mt-1">
            Transacciones procesadas
          </p>
        </CardContent>
      </Card>

      {/* Card 2: Avg Confidence */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Confianza Promedio</CardTitle>
          <ConfidenceIcon className={`h-4 w-4 ${confidenceColor}`} />
        </CardHeader>
        <CardContent>
          <div className={`text-2xl font-bold ${confidenceColor}`}>
            {confidencePercent}%
          </div>
          <p className="text-xs text-muted-foreground mt-1">
            {getConfidenceInterpretation(analytics.avg_confidence)}
          </p>
        </CardContent>
      </Card>

      {/* Card 3: Escalation Rate */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Tasa de Escalamiento</CardTitle>
          <UserCheck className="h-4 w-4 text-escalate" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold text-escalate">
            {escalationPercent}%
          </div>
          <p className="text-xs text-muted-foreground mt-1">
            Casos que requieren revisión humana
          </p>
        </CardContent>
      </Card>

      {/* Card 4: Avg Processing Time */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Tiempo de Procesamiento</CardTitle>
          <Zap className={`h-4 w-4 ${processingColor}`} />
        </CardHeader>
        <CardContent>
          <div className={`text-2xl font-bold ${processingColor}`}>
            {processingTime} ms
          </div>
          <p className="text-xs text-muted-foreground mt-1">
            {getProcessingLabel(analytics.avg_processing_time_ms)}
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
