"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  ChevronDown,
  ChevronUp,
  Clock,
  Search,
  TrendingUp,
  BookOpen,
  Shield,
  Layers,
  AlertTriangle,
  UserCheck,
  Scale,
  FileText,
  Zap,
} from "lucide-react";
import { AgentTraceEntry } from "@/lib/types";
import { cn } from "@/lib/utils";

interface AgentTraceTimelineProps {
  trace: AgentTraceEntry[];
}

const statusConfig = {
  success: {
    color: "bg-green-500",
    dotColor: "bg-green-500",
    label: "Success",
  },
  error: {
    color: "bg-red-500",
    dotColor: "bg-red-500",
    label: "Error",
  },
  timeout: {
    color: "bg-amber-500",
    dotColor: "bg-amber-500",
    label: "Timeout",
  },
  skipped: {
    color: "bg-gray-400",
    dotColor: "bg-gray-400",
    label: "Skipped",
  },
};

const agentConfig: Record<string, { icon: any; phase: number }> = {
  TransactionContext: { icon: Search, phase: 1 },
  BehavioralPattern: { icon: TrendingUp, phase: 1 },
  PolicyRAG: { icon: BookOpen, phase: 1 },
  ExternalThreat: { icon: Shield, phase: 1 },
  EvidenceAggregation: { icon: Layers, phase: 2 },
  ProFraud: { icon: AlertTriangle, phase: 3 },
  ProCustomer: { icon: UserCheck, phase: 3 },
  DecisionArbiter: { icon: Scale, phase: 4 },
  Explainability: { icon: FileText, phase: 5 },
};

const phaseConfig = [
  { id: 1, name: "Fase 1 — Recolección", isParallel: true, color: "border-blue-500" },
  { id: 2, name: "Fase 2 — Consolidación", isParallel: false, color: "border-purple-500" },
  { id: 3, name: "Fase 3 — Deliberación", isParallel: true, color: "border-orange-500" },
  { id: 4, name: "Fase 4 — Decisión", isParallel: false, color: "border-green-500" },
  { id: 5, name: "Fase 5 — Explicación", isParallel: false, color: "border-gray-500" },
];

interface PhaseGroup {
  phase: number;
  entries: AgentTraceEntry[];
}

function groupByPhase(trace: AgentTraceEntry[]): PhaseGroup[] {
  const groups = new Map<number, AgentTraceEntry[]>();

  trace.forEach((entry) => {
    const config = agentConfig[entry.agent_name];
    const phase = config?.phase || 0;

    if (!groups.has(phase)) {
      groups.set(phase, []);
    }
    groups.get(phase)!.push(entry);
  });

  return Array.from(groups.entries())
    .map(([phase, entries]) => ({ phase, entries }))
    .sort((a, b) => a.phase - b.phase);
}

function AgentTraceItem({
  entry,
  isLast
}: {
  entry: AgentTraceEntry;
  isLast: boolean;
}) {
  const [isExpanded, setIsExpanded] = useState(false);
  const status = (entry.status as keyof typeof statusConfig) || "success";
  const config = statusConfig[status];
  const agentInfo = agentConfig[entry.agent_name];
  const Icon = agentInfo?.icon || FileText;

  return (
    <div className="relative">
      {/* Timeline connector line */}
      {!isLast && (
        <div className="absolute left-4 top-10 bottom-0 w-0.5 bg-border" />
      )}

      {/* Timeline entry */}
      <div className="relative flex items-start gap-4 pb-6">
        {/* Timeline dot with icon */}
        <div className="relative flex-shrink-0">
          <div className={cn(
            "h-8 w-8 rounded-full flex items-center justify-center",
            "border-2 border-background shadow-sm",
            config.dotColor
          )}>
            <Icon className="h-4 w-4 text-white" />
          </div>
        </div>

        {/* Content Card */}
        <div className="flex-1 min-w-0">
          <div className="bg-card border rounded-lg p-3 space-y-2 transition-all">
            {/* Header */}
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-2 flex-wrap min-w-0">
                <span className="font-semibold text-sm truncate">
                  {entry.agent_name}
                </span>
                <Badge
                  variant="outline"
                  className={cn(
                    "text-xs flex-shrink-0",
                    status === "success" && "bg-green-500/10 text-green-700 border-green-500/20",
                    status === "error" && "bg-red-500/10 text-red-700 border-red-500/20",
                    status === "timeout" && "bg-amber-500/10 text-amber-700 border-amber-500/20",
                    status === "skipped" && "bg-gray-500/10 text-gray-700 border-gray-500/20"
                  )}
                >
                  {config.label}
                </Badge>
              </div>
              <div className="flex items-center gap-1.5 text-xs text-muted-foreground flex-shrink-0">
                <Clock className="h-3 w-3" />
                <span className="font-mono">{entry.duration_ms}ms</span>
              </div>
            </div>

            {/* Collapsible details */}
            {(entry.input_summary || entry.output_summary) && (
              <div className="space-y-2">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setIsExpanded(!isExpanded)}
                  className="h-7 text-xs px-2 -ml-2 hover:bg-muted"
                >
                  {isExpanded ? (
                    <>
                      <ChevronUp className="mr-1 h-3 w-3" />
                      Ocultar detalles
                    </>
                  ) : (
                    <>
                      <ChevronDown className="mr-1 h-3 w-3" />
                      Ver detalles
                    </>
                  )}
                </Button>

                <div className={cn(
                  "space-y-3 overflow-hidden transition-all duration-200",
                  isExpanded ? "max-h-96 opacity-100" : "max-h-0 opacity-0"
                )}>
                  <div className="bg-muted/50 p-3 rounded-md text-xs space-y-3">
                    {entry.input_summary && (
                      <div>
                        <p className="font-medium mb-1.5 text-muted-foreground uppercase tracking-wide">
                          Input
                        </p>
                        <p className="text-foreground/80 leading-relaxed">
                          {entry.input_summary}
                        </p>
                      </div>
                    )}
                    {entry.output_summary && (
                      <div>
                        <p className="font-medium mb-1.5 text-muted-foreground uppercase tracking-wide">
                          Output
                        </p>
                        <p className="text-foreground/80 leading-relaxed">
                          {entry.output_summary}
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function PhaseSection({
  phaseGroup,
  isLast
}: {
  phaseGroup: PhaseGroup;
  isLast: boolean;
}) {
  const phaseInfo = phaseConfig.find(p => p.id === phaseGroup.phase);
  const phaseName = phaseInfo?.name || `Fase ${phaseGroup.phase}`;
  const isParallel = phaseInfo?.isParallel || false;
  const phaseColor = phaseInfo?.color || "border-gray-500";

  return (
    <div className="space-y-4">
      {/* Phase Header */}
      <div className={cn(
        "flex items-center gap-2 border-l-4 pl-3 py-1.5",
        phaseColor
      )}>
        <h3 className="text-sm font-semibold text-foreground">
          {phaseName}
        </h3>
        {isParallel && (
          <Badge variant="outline" className="text-xs bg-blue-500/10 text-blue-700 border-blue-500/20">
            <Zap className="h-3 w-3 mr-1" />
            Paralelo
          </Badge>
        )}
        <span className="text-xs text-muted-foreground">
          ({phaseGroup.entries.length} agente{phaseGroup.entries.length !== 1 ? 's' : ''})
        </span>
      </div>

      {/* Phase Entries */}
      <div className="ml-0">
        {phaseGroup.entries.map((entry, idx) => (
          <AgentTraceItem
            key={`${entry.agent_name}-${idx}`}
            entry={entry}
            isLast={isLast && idx === phaseGroup.entries.length - 1}
          />
        ))}
      </div>
    </div>
  );
}

export function AgentTraceTimeline({ trace }: AgentTraceTimelineProps) {
  if (!trace || trace.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Agent Execution Trace</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <Clock className="h-12 w-12 text-muted-foreground/40 mb-3" />
            <p className="text-sm text-muted-foreground">
              Analysis not started
            </p>
            <p className="text-xs text-muted-foreground mt-1">
              No agent execution data available
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  const phaseGroups = groupByPhase(trace);
  const totalDuration = trace.reduce((sum, entry) => sum + entry.duration_ms, 0);

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>Agent Execution Trace</CardTitle>
          <div className="flex items-center gap-2 text-sm font-medium">
            <Clock className="h-4 w-4 text-muted-foreground" />
            <span className="text-muted-foreground">Total:</span>
            <span className="font-mono">{totalDuration}ms</span>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        {phaseGroups.map((group, idx) => (
          <PhaseSection
            key={group.phase}
            phaseGroup={group}
            isLast={idx === phaseGroups.length - 1}
          />
        ))}
      </CardContent>
    </Card>
  );
}
