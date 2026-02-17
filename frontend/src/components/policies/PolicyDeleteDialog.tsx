"use client";

import { Policy } from "@/lib/types";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";

interface PolicyDeleteDialogProps {
  policy: Policy | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onConfirm: () => void;
}

export function PolicyDeleteDialog({
  policy,
  open,
  onOpenChange,
  onConfirm,
}: PolicyDeleteDialogProps) {
  if (!policy) return null;

  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Eliminar Política</AlertDialogTitle>
          <AlertDialogDescription className="space-y-2">
            <p>
              ¿Está seguro de que desea eliminar esta política? Esta acción no se puede deshacer.
            </p>
            <div className="mt-4 p-3 bg-muted rounded-md">
              <p className="font-medium text-sm text-foreground">
                {policy.policy_id}: {policy.title}
              </p>
              <p className="text-xs text-muted-foreground mt-1">
                Acción: {policy.action_recommended} • Severidad:{" "}
                {policy.severity}
              </p>
            </div>
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Cancelar</AlertDialogCancel>
          <AlertDialogAction
            onClick={onConfirm}
            className="bg-red-600 hover:bg-red-700 focus:ring-red-600"
          >
            Eliminar Política
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
