import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { AlertTriangle } from "lucide-react";
import {
  DecisionType,
  AggregatedEvidence,
  TransactionSignals,
} from "@/lib/types";

interface DecisionCardProps {
  decision: DecisionType;
  confidence: number;
  evidence: AggregatedEvidence | null;
  signals: TransactionSignals | null;
}

const decisionConfig = {
  APPROVE: {
    label: "Aprobado",
    color: "bg-green-500/10 text-green-700 border-green-500/20",
  },
  CHALLENGE: {
    label: "Desafiado",
    color: "bg-amber-500/10 text-amber-700 border-amber-500/20",
  },
  BLOCK: {
    label: "Bloqueado",
    color: "bg-red-500/10 text-red-700 border-red-500/20",
  },
  ESCALATE_TO_HUMAN: {
    label: "Escalado",
    color: "bg-violet-500/10 text-violet-700 border-violet-500/20",
  },
};

const riskCategoryConfig = {
  critical: "bg-red-500/10 text-red-700 border-red-500/20",
  high: "bg-orange-500/10 text-orange-700 border-orange-500/20",
  medium: "bg-amber-500/10 text-amber-700 border-amber-500/20",
  low: "bg-green-500/10 text-green-700 border-green-500/20",
};

export function DecisionCard({
  decision,
  confidence,
  evidence,
  signals,
}: DecisionCardProps) {
  const config = decisionConfig[decision];
  const confidencePercent = Math.round(confidence * 100);
  const riskScore = evidence?.composite_risk_score || 0;
  const riskCategory = evidence?.risk_category || "low";
  const keySignals = evidence?.all_signals.slice(0, 5) || [];

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">Decisión</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Decision Badge */}
        <div className="flex flex-col items-center space-y-2">
          <Badge
            variant="outline"
            className={`${config.color} text-base px-4 py-2 font-semibold`}
          >
            {config.label}
          </Badge>
        </div>

        {/* Escalation Alert */}
        {decision === "ESCALATE_TO_HUMAN" && (
          <div className="flex items-center gap-2 text-sm text-amber-600 bg-amber-50 dark:bg-amber-950/20 p-3 rounded-md border border-amber-200 dark:border-amber-900">
            <AlertTriangle className="h-4 w-4 flex-shrink-0" />
            <span>Pendiente de revisión humana</span>
          </div>
        )}

        {/* Confidence */}
        <div className="space-y-2">
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">Confianza</span>
            <span className="font-semibold">{confidencePercent}%</span>
          </div>
          <Progress value={confidencePercent} className="h-2" />
        </div>

        {/* Risk Score */}
        {evidence && (
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Puntuación de Riesgo</span>
              <span className="font-semibold">{riskScore.toFixed(1)}</span>
            </div>
            <div className="flex items-center gap-2">
              <Progress value={riskScore} className="h-2 flex-1" />
              <Badge
                variant="outline"
                className={`${riskCategoryConfig[riskCategory as keyof typeof riskCategoryConfig]} text-xs capitalize`}
              >
                {riskCategory}
              </Badge>
            </div>
          </div>
        )}

        {/* Key Signals */}
        {keySignals.length > 0 && (
          <div className="space-y-2">
            <h4 className="text-sm font-medium text-muted-foreground">
              Señales Clave
            </h4>
            <ul className="space-y-1">
              {keySignals.map((signal, idx) => (
                <li key={idx} className="text-xs text-muted-foreground flex items-start gap-1.5">
                  <span className="text-primary mt-0.5">•</span>
                  <span>{signal}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
