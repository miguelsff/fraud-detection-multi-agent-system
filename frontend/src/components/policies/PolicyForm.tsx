"use client";

import { useState, useEffect } from "react";
import { Policy, PolicyCreate, PolicyAction, PolicySeverity } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

interface PolicyFormProps {
  policy?: Policy | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit: (policy: PolicyCreate) => Promise<void>;
}

export function PolicyForm({
  policy,
  open,
  onOpenChange,
  onSubmit,
}: PolicyFormProps) {
  const isEdit = !!policy;

  // Form state
  const [policyId, setPolicyId] = useState("");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [criteriaText, setCriteriaText] = useState("");
  const [thresholdsText, setThresholdsText] = useState("");
  const [actionRecommended, setActionRecommended] = useState<PolicyAction>("CHALLENGE");
  const [severity, setSeverity] = useState<PolicySeverity>("MEDIUM");
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Populate form when editing
  useEffect(() => {
    if (policy) {
      setPolicyId(policy.policy_id);
      setTitle(policy.title);
      setDescription(policy.description);
      setCriteriaText(policy.criteria.join("\n"));
      setThresholdsText(policy.thresholds.join("\n"));
      setActionRecommended(policy.action_recommended);
      setSeverity(policy.severity);
    } else {
      // Reset form for create
      setPolicyId("");
      setTitle("");
      setDescription("");
      setCriteriaText("");
      setThresholdsText("");
      setActionRecommended("CHALLENGE");
      setSeverity("MEDIUM");
    }
  }, [policy, open]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);

    try {
      // Convert textarea content to arrays (split by newlines, filter empty)
      const criteria = criteriaText
        .split("\n")
        .map((line) => line.trim())
        .filter((line) => line.length > 0);

      const thresholds = thresholdsText
        .split("\n")
        .map((line) => line.trim())
        .filter((line) => line.length > 0);

      const policyData: PolicyCreate = {
        policy_id: policyId,
        title,
        description,
        criteria,
        thresholds,
        action_recommended: actionRecommended,
        severity,
      };

      await onSubmit(policyData);
      onOpenChange(false);
    } catch (error) {
      console.error("Form submission error:", error);
      // Error handling is done in parent component via toast
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>
            {isEdit ? "Editar Política" : "Crear Nueva Política"}
          </DialogTitle>
          <DialogDescription>
            {isEdit
              ? "Actualice los detalles de la política a continuación"
              : "Complete los detalles para crear una nueva política de detección de fraude"}
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Policy ID */}
          <div className="space-y-2">
            <Label htmlFor="policy_id">
              ID de Política <span className="text-red-500">*</span>
            </Label>
            <Input
              id="policy_id"
              value={policyId}
              onChange={(e) => setPolicyId(e.target.value)}
              placeholder="FP-01"
              pattern="^FP-\d{2}$"
              required
              disabled={isEdit}
              className={isEdit ? "bg-muted" : ""}
            />
            <p className="text-xs text-muted-foreground">
              Formato: FP-XX (ej., FP-01, FP-15)
            </p>
          </div>

          {/* Title */}
          <div className="space-y-2">
            <Label htmlFor="title">
              Título <span className="text-red-500">*</span>
            </Label>
            <Input
              id="title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Título de la política"
              minLength={5}
              maxLength={200}
              required
            />
          </div>

          {/* Description */}
          <div className="space-y-2">
            <Label htmlFor="description">
              Descripción <span className="text-red-500">*</span>
            </Label>
            <Textarea
              id="description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Descripción detallada de la política..."
              rows={4}
              minLength={10}
              required
            />
          </div>

          {/* Criteria */}
          <div className="space-y-2">
            <Label htmlFor="criteria">
              Criterios <span className="text-red-500">*</span>
            </Label>
            <Textarea
              id="criteria"
              value={criteriaText}
              onChange={(e) => setCriteriaText(e.target.value)}
              placeholder="Ingrese un criterio por línea&#10;Ejemplo:&#10;Monto de transacción > 3x promedio&#10;Transacción desde país desconocido"
              rows={5}
              required
            />
            <p className="text-xs text-muted-foreground">
              Ingrese un criterio por línea
            </p>
          </div>

          {/* Thresholds */}
          <div className="space-y-2">
            <Label htmlFor="thresholds">
              Umbrales <span className="text-red-500">*</span>
            </Label>
            <Textarea
              id="thresholds"
              value={thresholdsText}
              onChange={(e) => setThresholdsText(e.target.value)}
              placeholder="Ingrese un umbral por línea&#10;Ejemplo:&#10;Monto > $1000: CHALLENGE&#10;Monto > $5000: BLOCK"
              rows={5}
              required
            />
            <p className="text-xs text-muted-foreground">
              Ingrese un umbral por línea
            </p>
          </div>

          {/* Action and Severity in a row */}
          <div className="grid grid-cols-2 gap-4">
            {/* Action Recommended */}
            <div className="space-y-2">
              <Label htmlFor="action">
                Acción Recomendada <span className="text-red-500">*</span>
              </Label>
              <Select
                value={actionRecommended}
                onValueChange={(value) =>
                  setActionRecommended(value as PolicyAction)
                }
              >
                <SelectTrigger id="action">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="APPROVE">APROBAR</SelectItem>
                  <SelectItem value="CHALLENGE">DESAFIAR</SelectItem>
                  <SelectItem value="BLOCK">BLOQUEAR</SelectItem>
                  <SelectItem value="ESCALATE_TO_HUMAN">
                    ESCALAR A HUMANO
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Severity */}
            <div className="space-y-2">
              <Label htmlFor="severity">
                Severidad <span className="text-red-500">*</span>
              </Label>
              <Select
                value={severity}
                onValueChange={(value) => setSeverity(value as PolicySeverity)}
              >
                <SelectTrigger id="severity">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="LOW">BAJA</SelectItem>
                  <SelectItem value="MEDIUM">MEDIA</SelectItem>
                  <SelectItem value="HIGH">ALTA</SelectItem>
                  <SelectItem value="CRITICAL">CRÍTICA</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={isSubmitting}
            >
              Cancelar
            </Button>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting
                ? isEdit
                  ? "Actualizando..."
                  : "Creando..."
                : isEdit
                  ? "Actualizar Política"
                  : "Crear Política"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
