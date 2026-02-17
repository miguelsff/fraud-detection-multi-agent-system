"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Mail, Copy, Check, CheckCircle2 } from "lucide-react";
import { DecisionType } from "@/lib/types";

interface CustomerExplanationProps {
  explanation: string;
  decision: {
    decision: DecisionType;
    confidence: number;
    reasoning?: string;
  };
}

export function CustomerExplanation({
  explanation,
  decision,
}: CustomerExplanationProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(explanation);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // Extract key factors from explanation (simplified - in production, this would come from backend)
  const keyFactors = [
    "Monto de transacción revisado",
    "Patrón de compra analizado",
    "Verificación de seguridad completada",
  ];

  // Recommended actions based on decision
  const getRecommendedActions = () => {
    switch (decision.decision) {
      case "APPROVE":
        return [
          "Transacción aprobada y procesada",
          "No se requiere acción adicional",
          "Recibo enviado a tu correo",
        ];
      case "CHALLENGE":
        return [
          "Verificación adicional requerida",
          "Revisa tu correo para código de verificación",
          "Completa la verificación en 24 horas",
        ];
      case "BLOCK":
        return [
          "Transacción bloqueada por seguridad",
          "Contacta a soporte para asistencia",
          "Revisa tu actividad reciente",
        ];
      case "ESCALATE_TO_HUMAN":
        return [
          "Transacción bajo revisión",
          "Serás contactado en 2 horas",
          "No se requiere acción en este momento",
        ];
      default:
        return [];
    }
  };

  const actions = getRecommendedActions();

  return (
    <Card className="border-blue-200 dark:border-blue-900 bg-blue-50/50 dark:bg-blue-950/20">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-lg text-blue-900 dark:text-blue-100">
            <Mail className="h-5 w-5" />
            📧 Notificación al Cliente
          </CardTitle>
          <Button
            variant="ghost"
            size="sm"
            onClick={handleCopy}
            className="h-8 gap-2"
          >
            {copied ? (
              <>
                <Check className="h-4 w-4 text-green-500" />
                <span className="text-xs">Copiado</span>
              </>
            ) : (
              <>
                <Copy className="h-4 w-4" />
                <span className="text-xs">Copiar</span>
              </>
            )}
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Main Explanation */}
        <div className="prose prose-sm dark:prose-invert max-w-none">
          <p className="text-sm text-foreground/90 leading-relaxed">
            {explanation}
          </p>
        </div>

        {/* Key Factors */}
        <div className="space-y-2">
          <h4 className="text-sm font-semibold text-blue-900 dark:text-blue-100">
            Factores Clave Revisados:
          </h4>
          <ol className="space-y-1.5 ml-4">
            {keyFactors.map((factor, idx) => (
              <li
                key={idx}
                className="text-sm text-foreground/80 list-decimal marker:text-blue-500 marker:font-semibold"
              >
                {factor}
              </li>
            ))}
          </ol>
        </div>

        {/* Recommended Actions */}
        {actions.length > 0 && (
          <div className="space-y-2 pt-3 border-t border-blue-200 dark:border-blue-900">
            <h4 className="text-sm font-semibold text-blue-900 dark:text-blue-100">
              Próximos Pasos:
            </h4>
            <div className="space-y-2">
              {actions.map((action, idx) => (
                <div
                  key={idx}
                  className="flex items-start gap-2 text-sm text-foreground/80"
                >
                  <CheckCircle2 className="h-4 w-4 text-blue-500 mt-0.5 flex-shrink-0" />
                  <span>{action}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Decision Badge */}
        <div className="pt-3 border-t border-blue-200 dark:border-blue-900">
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground">Estado:</span>
            <Badge
              variant="outline"
              className="bg-blue-500/10 text-blue-700 dark:text-blue-300 border-blue-500/20"
            >
              {decision.decision}
            </Badge>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
