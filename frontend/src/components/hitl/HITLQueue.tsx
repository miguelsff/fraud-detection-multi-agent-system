"use client";

import { useState } from "react";
import Link from "next/link";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { ChevronDown, ChevronUp, ExternalLink, AlertTriangle } from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { HITLReviewForm } from "./HITLReviewForm";
import type { HITLCase, TransactionAnalysisDetail } from "@/lib/types";
import { getTransactionDetail } from "@/lib/api";

interface HITLQueueProps {
  cases: HITLCase[];
  onCaseResolved: (caseId: number) => void;
}

interface CaseCardProps {
  hitlCase: HITLCase;
  onResolved: () => void;
}

function CaseCard({ hitlCase, onResolved }: CaseCardProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [detailData, setDetailData] = useState<TransactionAnalysisDetail | null>(null);
  const [isLoadingDetail, setIsLoadingDetail] = useState(false);

  const handleToggle = async (open: boolean) => {
    setIsOpen(open);

    // Load transaction detail when expanding for the first time
    if (open && !detailData && !isLoadingDetail) {
      setIsLoadingDetail(true);
      try {
        const detail = await getTransactionDetail(hitlCase.transaction_id);
        setDetailData(detail);
      } catch (err) {
        console.error("Failed to load transaction detail:", err);
      } finally {
        setIsLoadingDetail(false);
      }
    }
  };

  const formatAmount = (amount: number, currency: string) => {
    const currencySymbol = currency === "PEN" ? "S/" : "$";
    return `${currencySymbol}${amount.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  const getRiskBadgeColor = (score: number) => {
    if (score >= 80) return "bg-red-500 text-white";
    if (score >= 60) return "bg-orange-500 text-white";
    if (score >= 40) return "bg-yellow-500 text-black";
    return "bg-green-500 text-white";
  };

  const transaction = detailData?.transaction;
  const evidence = detailData?.evidence;
  const debate = detailData?.debate;
  const explanation = detailData?.explanation;

  return (
    <Collapsible open={isOpen} onOpenChange={handleToggle}>
      <Card className="border-l-4 border-l-violet-500 hover:shadow-md transition-shadow">
        <CollapsibleTrigger asChild>
          <CardHeader className="cursor-pointer">
            <div className="flex items-start justify-between">
              <div className="space-y-1">
                <CardTitle className="text-lg flex items-center gap-2">
                  <span className="font-mono">{hitlCase.transaction_id}</span>
                  <Badge variant="outline" className="border-violet-500 text-violet-700">
                    ESCALATE_TO_HUMAN
                  </Badge>
                </CardTitle>
                <CardDescription className="flex items-center gap-4 text-sm">
                  {transaction && (
                    <>
                      <span className="font-semibold text-foreground">
                        {formatAmount(transaction.amount, transaction.currency)}
                      </span>
                      {evidence && (
                        <Badge className={getRiskBadgeColor(evidence.composite_risk_score)}>
                          Risk: {evidence.composite_risk_score.toFixed(0)}
                        </Badge>
                      )}
                      <span className="text-muted-foreground">
                        {formatDistanceToNow(new Date(hitlCase.created_at), { addSuffix: true })}
                      </span>
                    </>
                  )}
                </CardDescription>
              </div>
              <div className="flex items-center gap-2">
                <Link href={`/transactions/${hitlCase.transaction_id}`}>
                  <Button variant="ghost" size="sm" onClick={(e) => e.stopPropagation()}>
                    <ExternalLink className="h-4 w-4" />
                  </Button>
                </Link>
                {isOpen ? (
                  <ChevronUp className="h-5 w-5 text-muted-foreground" />
                ) : (
                  <ChevronDown className="h-5 w-5 text-muted-foreground" />
                )}
              </div>
            </div>
          </CardHeader>
        </CollapsibleTrigger>

        <CollapsibleContent>
          <CardContent className="space-y-4">
            {isLoadingDetail ? (
              <div className="text-center py-8 text-muted-foreground">
                Cargando detalles de la transacción...
              </div>
            ) : detailData ? (
              <>
                {/* Detected Signals */}
                {evidence && evidence.all_signals.length > 0 && (
                  <div className="space-y-2">
                    <h4 className="text-sm font-semibold text-muted-foreground">
                      Señales Detectadas
                    </h4>
                    <div className="flex flex-wrap gap-2">
                      {evidence.all_signals.map((signal: string, idx: number) => (
                        <Badge key={idx} variant="secondary" className="text-xs">
                          {signal}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}

                {/* Key Factors */}
                {explanation && (
                  <div className="space-y-2">
                    <h4 className="text-sm font-semibold text-muted-foreground">
                      Resumen de Explicación
                    </h4>
                    <p className="text-sm text-foreground bg-muted/50 p-3 rounded">
                      {explanation.customer_explanation}
                    </p>
                  </div>
                )}

                {/* Debate Arguments */}
                {debate && (
                  <div className="grid gap-3 sm:grid-cols-2">
                    {/* Pro-Fraud Argument */}
                    <div className="space-y-2 border rounded-lg p-3 bg-red-50 border-red-200">
                      <div className="flex items-center justify-between">
                        <h4 className="text-sm font-semibold text-red-900">
                          Agente Pro-Fraude
                        </h4>
                        <Badge variant="outline" className="text-xs border-red-400">
                          {(debate.pro_fraud_confidence * 100).toFixed(0)}% confianza
                        </Badge>
                      </div>
                      <p className="text-xs text-red-800 line-clamp-4">
                        {debate.pro_fraud_argument}
                      </p>
                    </div>

                    {/* Pro-Customer Argument */}
                    <div className="space-y-2 border rounded-lg p-3 bg-green-50 border-green-200">
                      <div className="flex items-center justify-between">
                        <h4 className="text-sm font-semibold text-green-900">
                          Agente Pro-Cliente
                        </h4>
                        <Badge variant="outline" className="text-xs border-green-400">
                          {(debate.pro_customer_confidence * 100).toFixed(0)}% confianza
                        </Badge>
                      </div>
                      <p className="text-xs text-green-800 line-clamp-4">
                        {debate.pro_customer_argument}
                      </p>
                    </div>
                  </div>
                )}

                {/* Arbiter Rationale */}
                <div className="space-y-2 bg-violet-50 border border-violet-200 rounded-lg p-3">
                  <div className="flex items-center gap-2">
                    <AlertTriangle className="h-4 w-4 text-violet-700" />
                    <h4 className="text-sm font-semibold text-violet-900">
                      Por Qué Fue Escalado
                    </h4>
                  </div>
                  <p className="text-xs text-violet-800">
                    El árbitro no pudo tomar una decisión confiable
                    {detailData.confidence && ` (${(detailData.confidence * 100).toFixed(0)}% de confianza)`}.
                    Este caso requiere juicio humano para resolver la ambigüedad entre los argumentos presentados.
                  </p>
                </div>

                {/* Review Form */}
                <HITLReviewForm caseId={hitlCase.id} onResolved={onResolved} />
              </>
            ) : (
              <div className="text-center py-8 text-muted-foreground">
                Error al cargar detalles de la transacción
              </div>
            )}
          </CardContent>
        </CollapsibleContent>
      </Card>
    </Collapsible>
  );
}

export function HITLQueue({ cases, onCaseResolved }: HITLQueueProps) {
  const handleCaseResolved = (caseId: number) => {
    onCaseResolved(caseId);
  };

  return (
    <div className="space-y-4">
      {cases.map((hitlCase) => (
        <CaseCard
          key={hitlCase.id}
          hitlCase={hitlCase}
          onResolved={() => handleCaseResolved(hitlCase.id)}
        />
      ))}
    </div>
  );
}
