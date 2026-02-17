"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Scale,
  AlertTriangle,
  UserCheck,
  ArrowRight,
  ArrowLeft,
  Minus,
  Gavel,
} from "lucide-react";
import { DebateArguments, DecisionType } from "@/lib/types";
import { cn } from "@/lib/utils";

interface DebateViewProps {
  debate: DebateArguments;
  decision: {
    decision: DecisionType;
    confidence: number;
    reasoning?: string;
  };
}

export function DebateView({ debate, decision }: DebateViewProps) {
  if (!debate) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Scale className="h-5 w-5" />
            Debate Adversarial
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <Scale className="h-12 w-12 text-muted-foreground/40 mb-3" />
            <p className="text-sm text-muted-foreground">
              Debate no disponible
            </p>
            <p className="text-xs text-muted-foreground mt-1">
              No se generaron argumentos de debate para esta transacción
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  const fraudConfidence = Math.round(debate.pro_fraud_confidence * 100);
  const customerConfidence = Math.round(debate.pro_customer_confidence * 100);

  // Determine winner based on decision
  const getWinner = () => {
    if (decision.decision === "BLOCK" || decision.decision === "CHALLENGE") {
      return "fraud"; // Pro-fraud prevailed
    } else if (decision.decision === "APPROVE") {
      return "customer"; // Pro-customer prevailed
    } else {
      return "tie"; // ESCALATE_TO_HUMAN - both sides have merit
    }
  };

  const winner = getWinner();

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Scale className="h-5 w-5" />
          Debate Adversarial
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Main Debate - Two Column Layout */}
        <div className="grid gap-6 md:grid-cols-[1fr,auto,1fr] items-start">
          {/* LEFT: Pro-Fraud Column */}
          <div
            className={cn(
              "space-y-4 p-5 rounded-lg border-2 transition-all duration-300 animate-in fade-in-50 slide-in-from-left-5",
              winner === "fraud"
                ? "border-red-500 bg-red-50/80 dark:bg-red-950/40 shadow-lg"
                : "border-red-200 dark:border-red-900 bg-red-50/50 dark:bg-red-950/20"
            )}
          >
            {/* Header */}
            <div className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-red-600 dark:text-red-400" />
              <h4 className="font-bold text-red-700 dark:text-red-300">
                ⚠️ Caso de Fraude
              </h4>
            </div>

            {/* Argument */}
            <ScrollArea className="max-h-48">
              <p className="text-sm text-foreground/80 leading-relaxed pr-4">
                {debate.pro_fraud_argument}
              </p>
            </ScrollArea>

            {/* Confidence Bar */}
            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="text-red-600 dark:text-red-400 font-medium">
                  Confianza
                </span>
                <span className="font-bold text-red-700 dark:text-red-300">
                  {fraudConfidence}%
                </span>
              </div>
              <Progress
                value={fraudConfidence}
                className="h-2.5 bg-red-100 dark:bg-red-950/50 [&>div]:bg-red-500"
              />
            </div>

            {/* Evidence Cited */}
            {debate.pro_fraud_evidence.length > 0 && (
              <div className="space-y-2 pt-3 border-t border-red-200 dark:border-red-900">
                <p className="text-xs font-semibold text-red-700 dark:text-red-400 uppercase tracking-wide">
                  Evidencia Citada
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {debate.pro_fraud_evidence.map((item, idx) => (
                    <Badge
                      key={idx}
                      variant="outline"
                      className="bg-red-500/10 text-red-700 dark:text-red-300 border-red-500/30 text-xs"
                    >
                      {item}
                    </Badge>
                  ))}
                </div>
              </div>
            )}

            {/* Winner Indicator */}
            {winner === "fraud" && (
              <div className="pt-3 border-t border-red-300 dark:border-red-800">
                <Badge className="bg-red-500 text-white">
                  ✓ Prevaleció en Decisión
                </Badge>
              </div>
            )}
          </div>

          {/* CENTER: VS Indicator */}
          <div className="hidden md:flex flex-col items-center justify-center gap-3 py-8">
            <div className="relative">
              <Scale className="h-8 w-8 text-muted-foreground" />
              {winner === "fraud" && (
                <ArrowLeft className="h-5 w-5 text-red-500 absolute -left-6 top-1.5 animate-pulse" />
              )}
              {winner === "customer" && (
                <ArrowRight className="h-5 w-5 text-green-500 absolute -right-6 top-1.5 animate-pulse" />
              )}
              {winner === "tie" && (
                <Minus className="h-5 w-5 text-violet-500 absolute -bottom-5 left-1.5 animate-pulse" />
              )}
            </div>
            <span className="text-xs font-bold text-muted-foreground uppercase tracking-wider">
              vs
            </span>
          </div>

          {/* RIGHT: Pro-Customer Column */}
          <div
            className={cn(
              "space-y-4 p-5 rounded-lg border-2 transition-all duration-300 animate-in fade-in-50 slide-in-from-right-5 delay-75",
              winner === "customer"
                ? "border-green-500 bg-green-50/80 dark:bg-green-950/40 shadow-lg"
                : "border-green-200 dark:border-green-900 bg-green-50/50 dark:bg-green-950/20"
            )}
          >
            {/* Header */}
            <div className="flex items-center gap-2">
              <UserCheck className="h-5 w-5 text-green-600 dark:text-green-400" />
              <h4 className="font-bold text-green-700 dark:text-green-300">
                ✅ Caso de Legitimidad
              </h4>
            </div>

            {/* Argument */}
            <ScrollArea className="max-h-48">
              <p className="text-sm text-foreground/80 leading-relaxed pr-4">
                {debate.pro_customer_argument}
              </p>
            </ScrollArea>

            {/* Confidence Bar */}
            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="text-green-600 dark:text-green-400 font-medium">
                  Confianza
                </span>
                <span className="font-bold text-green-700 dark:text-green-300">
                  {customerConfidence}%
                </span>
              </div>
              <Progress
                value={customerConfidence}
                className="h-2.5 bg-green-100 dark:bg-green-950/50 [&>div]:bg-green-500"
              />
            </div>

            {/* Evidence Cited */}
            {debate.pro_customer_evidence.length > 0 && (
              <div className="space-y-2 pt-3 border-t border-green-200 dark:border-green-900">
                <p className="text-xs font-semibold text-green-700 dark:text-green-400 uppercase tracking-wide">
                  Evidencia Citada
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {debate.pro_customer_evidence.map((item, idx) => (
                    <Badge
                      key={idx}
                      variant="outline"
                      className="bg-green-500/10 text-green-700 dark:text-green-300 border-green-500/30 text-xs"
                    >
                      {item}
                    </Badge>
                  ))}
                </div>
              </div>
            )}

            {/* Winner Indicator */}
            {winner === "customer" && (
              <div className="pt-3 border-t border-green-300 dark:border-green-800">
                <Badge className="bg-green-500 text-white">
                  ✓ Prevaleció en Decisión
                </Badge>
              </div>
            )}
          </div>
        </div>

        {/* Tie Indicator (for ESCALATE) */}
        {winner === "tie" && (
          <div className="text-center p-4 bg-violet-50 dark:bg-violet-950/20 border-2 border-violet-200 dark:border-violet-900 rounded-lg animate-in fade-in-50 delay-150">
            <Badge variant="outline" className="bg-violet-500/10 text-violet-700 dark:text-violet-300 border-violet-500/30">
              ⚖️ Argumentos Balanceados - Escalado a Revisión Humana
            </Badge>
          </div>
        )}

        {/* Arbiter's Verdict */}
        <div className="pt-4 border-t animate-in fade-in-50 delay-200">
          <div className="bg-muted/50 rounded-lg p-4 space-y-3">
            <div className="flex items-center gap-2">
              <Gavel className="h-5 w-5 text-foreground" />
              <h4 className="font-semibold text-foreground">
                Veredicto del Árbitro
              </h4>
            </div>
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <span className="text-sm text-muted-foreground">Decisión:</span>
                <Badge
                  variant="outline"
                  className={cn(
                    "font-semibold",
                    decision.decision === "APPROVE" && "bg-green-500/10 text-green-700 border-green-500/20",
                    decision.decision === "CHALLENGE" && "bg-amber-500/10 text-amber-700 border-amber-500/20",
                    decision.decision === "BLOCK" && "bg-red-500/10 text-red-700 border-red-500/20",
                    decision.decision === "ESCALATE_TO_HUMAN" && "bg-violet-500/10 text-violet-700 border-violet-500/20"
                  )}
                >
                  {decision.decision}
                </Badge>
                <span className="text-sm text-muted-foreground">
                  (Confianza: {Math.round(decision.confidence * 100)}%)
                </span>
              </div>
              {decision.reasoning && (
                <p className="text-sm text-foreground/80 leading-relaxed italic">
                  "{decision.reasoning}"
                </p>
              )}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
