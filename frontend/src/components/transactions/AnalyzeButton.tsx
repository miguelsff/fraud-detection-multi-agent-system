"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { PlusCircle, Loader2 } from "lucide-react";
import { analyzeTransaction } from "@/lib/api";
import type { Transaction, CustomerBehavior } from "@/lib/types";

// Test scenarios from synthetic_data.json
const SCENARIOS = {
  APPROVE: {
    name: "APROBAR - Transacción Normal",
    transaction: {
      transaction_id: "T-1003",
      customer_id: "C-503",
      amount: 250.00,
      currency: "PEN",
      country: "PE",
      channel: "web",
      device_id: "D-03",
      timestamp: "2025-01-15T14:30:00Z",
      merchant_id: "M-150"
    },
    customerBehavior: {
      customer_id: "C-503",
      usual_amount_avg: 500.00,
      usual_hours: "08:00-22:00",
      usual_countries: ["PE"],
      usual_devices: ["D-03", "D-04"]
    }
  },
  CHALLENGE: {
    name: "DESAFIAR - Monto Alto + Fuera de Horario",
    transaction: {
      transaction_id: "T-1001",
      customer_id: "C-501",
      amount: 1800.00,
      currency: "PEN",
      country: "PE",
      channel: "web",
      device_id: "D-01",
      timestamp: "2025-01-15T03:15:00Z",
      merchant_id: "M-200"
    },
    customerBehavior: {
      customer_id: "C-501",
      usual_amount_avg: 500.00,
      usual_hours: "08:00-22:00",
      usual_countries: ["PE"],
      usual_devices: ["D-01", "D-02"]
    }
  },
  BLOCK: {
    name: "BLOQUEAR - Múltiples Factores de Riesgo",
    transaction: {
      transaction_id: "T-1002",
      customer_id: "C-502",
      amount: 8500.00,
      currency: "USD",
      country: "KP",
      channel: "mobile",
      device_id: "D-99",
      timestamp: "2025-01-15T02:00:00Z",
      merchant_id: "M-305"
    },
    customerBehavior: {
      customer_id: "C-502",
      usual_amount_avg: 500.00,
      usual_hours: "08:00-22:00",
      usual_countries: ["PE", "CL"],
      usual_devices: ["D-03"]
    }
  },
  ESCALATE_TO_HUMAN: {
    name: "ESCALAR - Señales Contradictorias",
    transaction: {
      transaction_id: "T-1004",
      customer_id: "C-504",
      amount: 1500.00,
      currency: "USD",
      country: "PK",
      channel: "app",
      device_id: "D-01",
      timestamp: "2025-01-15T00:00:00Z",
      merchant_id: "M-280"
    },
    customerBehavior: {
      customer_id: "C-504",
      usual_amount_avg: 500.00,
      usual_hours: "08:00-22:00",
      usual_countries: ["PE"],
      usual_devices: ["D-01"]
    }
  }
} as const;

export function AnalyzeButton() {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<any>(null);

  const [transactionJson, setTransactionJson] = useState("");
  const [customerBehaviorJson, setCustomerBehaviorJson] = useState("");

  const loadScenario = (scenarioKey: keyof typeof SCENARIOS) => {
    const scenario = SCENARIOS[scenarioKey];

    // Generate unique transaction_id: T-{timestamp}-{random}
    const uniqueId = `T-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`;

    // Clone transaction with unique ID
    const transactionWithUniqueId = {
      ...scenario.transaction,
      transaction_id: uniqueId,
    };

    setTransactionJson(JSON.stringify(transactionWithUniqueId, null, 2));
    setCustomerBehaviorJson(JSON.stringify(scenario.customerBehavior, null, 2));
    setError(null); // Clear any previous error
    setResult(null); // Clear any previous result
  };

  const handleAnalyze = async () => {
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      // Parse JSON inputs
      const transaction: Transaction = JSON.parse(transactionJson);
      const customerBehavior: CustomerBehavior = JSON.parse(customerBehaviorJson);

      // Validate required fields
      if (!transaction.transaction_id || !transaction.customer_id || !transaction.amount) {
        throw new Error("La transacción debe tener transaction_id, customer_id y amount");
      }

      if (!customerBehavior.customer_id) {
        throw new Error("El comportamiento del cliente debe tener customer_id");
      }

      // Call API
      const decision = await analyzeTransaction(transaction, customerBehavior);
      setResult(decision);

      // Redirect to detail page and clean up
      setTimeout(() => {
        router.push(`/transactions/${transaction.transaction_id}`);
        router.refresh();
        setOpen(false);
        // Clean fields for next use
        setTransactionJson("");
        setCustomerBehaviorJson("");
        setResult(null);
        setError(null);
      }, 500);

    } catch (err) {
      if (err instanceof SyntaxError) {
        setError("Formato JSON inválido. Por favor verifica tu entrada.");
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("Error al analizar la transacción. Por favor intenta de nuevo.");
      }
    } finally {
      setLoading(false);
    }
  };

  const handleOpenChange = (newOpen: boolean) => {
    if (!loading) {
      setOpen(newOpen);
      if (!newOpen) {
        // Reset state when closing
        setError(null);
        setResult(null);
      }
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild>
        <Button>
          <PlusCircle className="mr-2 h-4 w-4" />
          Analizar Nueva
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Analizar Nueva Transacción</DialogTitle>
          <DialogDescription>
            Envía una transacción para análisis de detección de fraude. Usa preconfigurados rápidos o ingresa JSON personalizado.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Scenario Preset Buttons */}
          <div className="space-y-3">
            <Label className="text-sm font-medium">Escenarios de Prueba Rápidos</Label>
            <div className="grid grid-cols-2 gap-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => loadScenario("APPROVE")}
                disabled={loading || !!result}
                className="justify-start text-left h-auto py-2"
              >
                <div className="flex items-center gap-2 w-full">
                  <div className="w-2 h-2 rounded-full bg-approve flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <div className="font-medium text-xs">APROBAR</div>
                    <div className="text-xs text-muted-foreground truncate">
                      Transacción normal
                    </div>
                  </div>
                </div>
              </Button>

              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => loadScenario("CHALLENGE")}
                disabled={loading || !!result}
                className="justify-start text-left h-auto py-2"
              >
                <div className="flex items-center gap-2 w-full">
                  <div className="w-2 h-2 rounded-full bg-challenge flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <div className="font-medium text-xs">DESAFIAR</div>
                    <div className="text-xs text-muted-foreground truncate">
                      Monto alto + fuera de horario
                    </div>
                  </div>
                </div>
              </Button>

              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => loadScenario("BLOCK")}
                disabled={loading || !!result}
                className="justify-start text-left h-auto py-2"
              >
                <div className="flex items-center gap-2 w-full">
                  <div className="w-2 h-2 rounded-full bg-block flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <div className="font-medium text-xs">BLOQUEAR</div>
                    <div className="text-xs text-muted-foreground truncate">
                      Múltiples factores de riesgo
                    </div>
                  </div>
                </div>
              </Button>

              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => loadScenario("ESCALATE_TO_HUMAN")}
                disabled={loading || !!result}
                className="justify-start text-left h-auto py-2"
              >
                <div className="flex items-center gap-2 w-full">
                  <div className="w-2 h-2 rounded-full bg-escalate flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <div className="font-medium text-xs">ESCALAR</div>
                    <div className="text-xs text-muted-foreground truncate">
                      Señales ambiguas
                    </div>
                  </div>
                </div>
              </Button>
            </div>
          </div>

          {/* Transaction JSON */}
          <div className="space-y-2">
            <Label htmlFor="transaction">Datos de Transacción (JSON)</Label>
            <Textarea
              id="transaction"
              value={transactionJson}
              onChange={(e) => setTransactionJson(e.target.value)}
              placeholder="Ingresa el JSON de la transacción"
              className="font-mono text-sm min-h-[200px]"
              disabled={loading || !!result}
            />
          </div>

          {/* Customer Behavior JSON */}
          <div className="space-y-2">
            <Label htmlFor="customer-behavior">Comportamiento del Cliente (JSON)</Label>
            <Textarea
              id="customer-behavior"
              value={customerBehaviorJson}
              onChange={(e) => setCustomerBehaviorJson(e.target.value)}
              placeholder="Ingresa el JSON del comportamiento del cliente"
              className="font-mono text-sm min-h-[150px]"
              disabled={loading || !!result}
            />
          </div>

          {/* Error Message */}
          {error && (
            <div className="bg-destructive/10 border border-destructive/20 text-destructive px-4 py-3 rounded-lg">
              <p className="font-medium">Error</p>
              <p className="text-sm mt-1">{error}</p>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => handleOpenChange(false)}
            disabled={loading}
          >
            Cancelar
          </Button>
          <Button
            onClick={handleAnalyze}
            disabled={loading || !!result}
          >
            {loading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Analizando...
              </>
            ) : (
              "Analizar"
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
