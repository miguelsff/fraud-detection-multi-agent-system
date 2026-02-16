"use client";

import { Policy } from "@/lib/types";
import { PolicyCard } from "./PolicyCard";
import { Button } from "@/components/ui/button";
import { Plus, FileText } from "lucide-react";

interface PolicyListProps {
  policies: Policy[];
  onCreateNew: () => void;
  onEdit: (policy: Policy) => void;
  onDelete: (policy: Policy) => void;
}

export function PolicyList({
  policies,
  onCreateNew,
  onEdit,
  onDelete,
}: PolicyListProps) {
  if (policies.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <div className="rounded-full bg-muted p-6 mb-4">
          <FileText className="h-12 w-12 text-muted-foreground" />
        </div>
        <h3 className="text-lg font-semibold mb-2">No se encontraron políticas</h3>
        <p className="text-sm text-muted-foreground mb-6 max-w-md">
          Comience creando su primera política de detección de fraude. Las políticas
          definen reglas y umbrales para identificar transacciones sospechosas.
        </p>
        <Button onClick={onCreateNew} className="gap-2">
          <Plus className="h-4 w-4" />
          Crear Primera Política
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header with Create button */}
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-muted-foreground">
            {policies.length} {policies.length === 1 ? "política" : "políticas"}{" "}
            encontradas
          </p>
        </div>
        <Button onClick={onCreateNew} className="gap-2">
          <Plus className="h-4 w-4" />
          Crear Política
        </Button>
      </div>

      {/* Policy grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {policies.map((policy) => (
          <PolicyCard
            key={policy.policy_id}
            policy={policy}
            onEdit={onEdit}
            onDelete={onDelete}
          />
        ))}
      </div>
    </div>
  );
}
