"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Loader2, CheckCircle, AlertCircle } from "lucide-react";
import { resolveHITLCase } from "@/lib/api";

interface HITLReviewFormProps {
  caseId: number;
  onResolved: () => void;
}

export function HITLReviewForm({ caseId, onResolved }: HITLReviewFormProps) {
  const [resolution, setResolution] = useState<"APPROVE" | "BLOCK" | "">("");
  const [reason, setReason] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!resolution) {
      setError("Please select a decision");
      return;
    }

    if (!reason.trim()) {
      setError("Please provide a reason for your decision");
      return;
    }

    setError(null);
    setIsLoading(true);

    try {
      await resolveHITLCase(caseId, resolution as "APPROVE" | "BLOCK", reason);
      setSuccess(true);

      // Wait a moment to show success message, then notify parent
      setTimeout(() => {
        onResolved();
      }, 1000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to submit decision");
    } finally {
      setIsLoading(false);
    }
  };

  if (success) {
    return (
      <Alert className="border-green-500 bg-green-50">
        <CheckCircle className="h-4 w-4 text-green-600" />
        <AlertDescription className="text-green-800">
          Decision submitted successfully
        </AlertDescription>
      </Alert>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4 pt-4 border-t">
      <div className="space-y-2">
        <Label htmlFor="resolution">Decision</Label>
        <Select
          value={resolution}
          onValueChange={(value) => setResolution(value as "APPROVE" | "BLOCK")}
        >
          <SelectTrigger id="resolution">
            <SelectValue placeholder="Select decision..." />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="APPROVE">
              <span className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-green-500" />
                Approve Transaction
              </span>
            </SelectItem>
            <SelectItem value="BLOCK">
              <span className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-red-500" />
                Block Transaction
              </span>
            </SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-2">
        <Label htmlFor="reason">Reason for Decision</Label>
        <Textarea
          id="reason"
          placeholder="Explain your decision rationale..."
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          className="min-h-[100px]"
          required
        />
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <Button
        type="submit"
        disabled={isLoading || !resolution || !reason.trim()}
        className="w-full"
      >
        {isLoading ? (
          <>
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            Submitting Decision...
          </>
        ) : (
          "Submit Decision"
        )}
      </Button>
    </form>
  );
}
