"use client";

import { useState } from "react";
import { Policy, PolicyCreate, PolicyUpdate } from "@/lib/types";
import {
  createPolicy,
  updatePolicy,
  deletePolicy,
  getPolicies,
} from "@/lib/api";
import { PolicyList } from "./PolicyList";
import { PolicyForm } from "./PolicyForm";
import { PolicyDeleteDialog } from "./PolicyDeleteDialog";
import { useToast } from "@/hooks/use-toast";

interface PoliciesClientProps {
  initialPolicies: Policy[];
}

export default function PoliciesClient({
  initialPolicies,
}: PoliciesClientProps) {
  const [policies, setPolicies] = useState<Policy[]>(initialPolicies);
  const [formOpen, setFormOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [editingPolicy, setEditingPolicy] = useState<Policy | null>(null);
  const [deletingPolicy, setDeletingPolicy] = useState<Policy | null>(null);
  const { toast } = useToast();

  // Refresh policies from server
  const refreshPolicies = async () => {
    try {
      const updated = await getPolicies();
      setPolicies(updated);
    } catch (error) {
      console.error("Failed to refresh policies:", error);
      toast({
        title: "Error",
        description: "Error al actualizar las políticas",
        variant: "destructive",
      });
    }
  };

  // Handle create new policy
  const handleCreateNew = () => {
    setEditingPolicy(null);
    setFormOpen(true);
  };

  // Handle edit policy
  const handleEdit = (policy: Policy) => {
    setEditingPolicy(policy);
    setFormOpen(true);
  };

  // Handle delete policy (show confirmation)
  const handleDelete = (policy: Policy) => {
    setDeletingPolicy(policy);
    setDeleteDialogOpen(true);
  };

  // Handle form submission (create or update)
  const handleFormSubmit = async (policyData: PolicyCreate) => {
    try {
      if (editingPolicy) {
        // Update existing policy
        const updates: PolicyUpdate = {
          title: policyData.title,
          description: policyData.description,
          criteria: policyData.criteria,
          thresholds: policyData.thresholds,
          action_recommended: policyData.action_recommended,
          severity: policyData.severity,
        };

        await updatePolicy(editingPolicy.policy_id, updates);

        toast({
          title: "Política actualizada",
          description: `${policyData.policy_id} se ha actualizado exitosamente`,
        });
      } else {
        // Create new policy
        await createPolicy(policyData);

        toast({
          title: "Política creada",
          description: `${policyData.policy_id} se ha creado exitosamente`,
        });
      }

      // Refresh the policy list
      await refreshPolicies();
    } catch (error) {
      const errorMessage =
        error instanceof Error ? error.message : "Unknown error occurred";

      toast({
        title: editingPolicy ? "Error al actualizar" : "Error al crear",
        description: errorMessage,
        variant: "destructive",
      });

      throw error; // Re-throw to prevent form from closing
    }
  };

  // Handle delete confirmation
  const handleDeleteConfirm = async () => {
    if (!deletingPolicy) return;

    try {
      await deletePolicy(deletingPolicy.policy_id);

      toast({
        title: "Política eliminada",
        description: `${deletingPolicy.policy_id} se ha eliminado exitosamente`,
      });

      // Close dialog and refresh
      setDeleteDialogOpen(false);
      setDeletingPolicy(null);
      await refreshPolicies();
    } catch (error) {
      const errorMessage =
        error instanceof Error ? error.message : "Failed to delete policy";

      toast({
        title: "Error al eliminar",
        description: errorMessage,
        variant: "destructive",
      });
    }
  };

  return (
    <>
      <PolicyList
        policies={policies}
        onCreateNew={handleCreateNew}
        onEdit={handleEdit}
        onDelete={handleDelete}
      />

      <PolicyForm
        policy={editingPolicy}
        open={formOpen}
        onOpenChange={setFormOpen}
        onSubmit={handleFormSubmit}
      />

      <PolicyDeleteDialog
        policy={deletingPolicy}
        open={deleteDialogOpen}
        onOpenChange={setDeleteDialogOpen}
        onConfirm={handleDeleteConfirm}
      />
    </>
  );
}
