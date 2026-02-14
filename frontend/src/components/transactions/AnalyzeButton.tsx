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

// Example data from synthetic_data.json for pre-filling
const EXAMPLE_TRANSACTION = {
  transaction_id: "T-9001",
  customer_id: "C-501",
  amount: 1800.00,
  currency: "PEN",
  country: "PE",
  channel: "web",
  device_id: "D-01",
  timestamp: new Date().toISOString(),
  merchant_id: "M-200"
};

const EXAMPLE_CUSTOMER_BEHAVIOR = {
  customer_id: "C-501",
  usual_amount_avg: 500.00,
  usual_hours: "08:00-22:00",
  usual_countries: ["PE"],
  usual_devices: ["D-01", "D-02"]
};

export function AnalyzeButton() {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<any>(null);

  const [transactionJson, setTransactionJson] = useState(
    JSON.stringify(EXAMPLE_TRANSACTION, null, 2)
  );
  const [customerBehaviorJson, setCustomerBehaviorJson] = useState(
    JSON.stringify(EXAMPLE_CUSTOMER_BEHAVIOR, null, 2)
  );

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
        throw new Error("Transaction must have transaction_id, customer_id, and amount");
      }

      if (!customerBehavior.customer_id) {
        throw new Error("Customer behavior must have customer_id");
      }

      // Call API
      const decision = await analyzeTransaction(transaction, customerBehavior);
      setResult(decision);

      // Wait a moment to show result, then redirect
      setTimeout(() => {
        router.push(`/transactions/${transaction.transaction_id}`);
        router.refresh();
        setOpen(false);
      }, 2000);

    } catch (err) {
      if (err instanceof SyntaxError) {
        setError("Invalid JSON format. Please check your input.");
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("Failed to analyze transaction. Please try again.");
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
          Analyze New
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Analyze New Transaction</DialogTitle>
          <DialogDescription>
            Submit a transaction for fraud detection analysis. Pre-filled with example data.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Transaction JSON */}
          <div className="space-y-2">
            <Label htmlFor="transaction">Transaction Data (JSON)</Label>
            <Textarea
              id="transaction"
              value={transactionJson}
              onChange={(e) => setTransactionJson(e.target.value)}
              placeholder="Enter transaction JSON"
              className="font-mono text-sm min-h-[200px]"
              disabled={loading || !!result}
            />
          </div>

          {/* Customer Behavior JSON */}
          <div className="space-y-2">
            <Label htmlFor="customer-behavior">Customer Behavior (JSON)</Label>
            <Textarea
              id="customer-behavior"
              value={customerBehaviorJson}
              onChange={(e) => setCustomerBehaviorJson(e.target.value)}
              placeholder="Enter customer behavior JSON"
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

          {/* Success Result */}
          {result && (
            <div className="bg-approve/10 border border-approve/20 text-approve px-4 py-3 rounded-lg">
              <p className="font-medium">Analysis Complete!</p>
              <div className="text-sm mt-2 space-y-1">
                <p><strong>Decision:</strong> {result.decision}</p>
                <p><strong>Confidence:</strong> {(result.confidence * 100).toFixed(1)}%</p>
                <p className="text-muted-foreground mt-2">Redirecting to detail page...</p>
              </div>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => handleOpenChange(false)}
            disabled={loading}
          >
            Cancel
          </Button>
          <Button
            onClick={handleAnalyze}
            disabled={loading || !!result}
          >
            {loading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Analyzing...
              </>
            ) : (
              "Analyze"
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
