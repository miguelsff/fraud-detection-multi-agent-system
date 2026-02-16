"use client";

import { Policy } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Edit, Trash2 } from "lucide-react";

interface PolicyCardProps {
  policy: Policy;
  onEdit: (policy: Policy) => void;
  onDelete: (policy: Policy) => void;
}

const ACTION_COLORS = {
  APPROVE: "bg-green-100 text-green-800 border-green-300",
  CHALLENGE: "bg-amber-100 text-amber-800 border-amber-300",
  BLOCK: "bg-red-100 text-red-800 border-red-300",
  ESCALATE_TO_HUMAN: "bg-violet-100 text-violet-800 border-violet-300",
} as const;

const SEVERITY_COLORS = {
  LOW: "bg-blue-100 text-blue-800 border-blue-300",
  MEDIUM: "bg-yellow-100 text-yellow-800 border-yellow-300",
  HIGH: "bg-orange-100 text-orange-800 border-orange-300",
  CRITICAL: "bg-red-100 text-red-800 border-red-300",
} as const;

export function PolicyCard({ policy, onEdit, onDelete }: PolicyCardProps) {
  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardHeader>
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <CardTitle className="text-lg font-semibold">
              {policy.policy_id}
            </CardTitle>
            <CardDescription className="mt-1 font-medium">
              {policy.title}
            </CardDescription>
          </div>
          <div className="flex gap-2">
            <Badge
              variant="outline"
              className={ACTION_COLORS[policy.action_recommended]}
            >
              {policy.action_recommended}
            </Badge>
            <Badge
              variant="outline"
              className={SEVERITY_COLORS[policy.severity]}
            >
              {policy.severity}
            </Badge>
          </div>
        </div>
      </CardHeader>

      <CardContent>
        <p className="text-sm text-muted-foreground line-clamp-3">
          {policy.description}
        </p>

        <div className="mt-4 space-y-2">
          <div>
            <p className="text-xs font-medium text-muted-foreground">
              Criterios ({policy.criteria.length})
            </p>
            <p className="text-xs text-muted-foreground line-clamp-2">
              {policy.criteria.join(" • ")}
            </p>
          </div>

          <div>
            <p className="text-xs font-medium text-muted-foreground">
              Umbrales ({policy.thresholds.length})
            </p>
            <p className="text-xs text-muted-foreground line-clamp-2">
              {policy.thresholds.join(" • ")}
            </p>
          </div>
        </div>
      </CardContent>

      <CardFooter className="flex gap-2 justify-end border-t pt-4">
        <Button
          variant="outline"
          size="sm"
          onClick={() => onEdit(policy)}
          className="gap-2"
        >
          <Edit className="h-4 w-4" />
          Editar
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={() => onDelete(policy)}
          className="gap-2 text-red-600 hover:text-red-700 hover:bg-red-50"
        >
          <Trash2 className="h-4 w-4" />
          Eliminar
        </Button>
      </CardFooter>
    </Card>
  );
}
