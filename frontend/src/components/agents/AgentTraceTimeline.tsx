"use client";

import { useState, useMemo } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Label } from "@/components/ui/label";
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
  Loader2,
  AlertCircle,
} from "lucide-react";
import { AgentTraceEntry, WebSocketEvent } from "@/lib/types";
import { cn } from "@/lib/utils";
import { LLMInteractionViewer } from "./LLMInteractionViewer";
import { RAGQueryViewer } from "./RAGQueryViewer";
import { JsonViewer } from "@/components/ui/JsonViewer";

interface AgentTraceTimelineProps {
  trace: AgentTraceEntry[];
  liveEvents?: WebSocketEvent[];
}

interface AgentState {
  status: "running" | "completed" | "idle";
  justCompleted?: boolean;
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
  fallback: {
    color: "bg-orange-500",
    dotColor: "bg-orange-500",
    label: "Fallback",
  },
  running: {
    color: "bg-blue-500",
    dotColor: "bg-blue-500",
    label: "Running",
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
  isLast,
  agentState
}: {
  entry: AgentTraceEntry;
  isLast: boolean;
  agentState?: AgentState;
}) {
  const [isExpanded, setIsExpanded] = useState(false);
  const isRunning = agentState?.status === "running";
  const justCompleted = agentState?.justCompleted;

  const status = isRunning ? "running" : (entry.status as keyof typeof statusConfig) || "success";
  const config = statusConfig[status];
  const agentInfo = agentConfig[entry.agent_name];
  const Icon = agentInfo?.icon || FileText;

  return (
    <div className={cn(
      "relative",
      justCompleted && "animate-in fade-in-50 duration-500"
    )}>
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
            "border-2 border-background shadow-sm transition-all",
            config.dotColor,
            isRunning && "animate-pulse"
          )}>
            {isRunning ? (
              <Loader2 className="h-4 w-4 text-white animate-spin" />
            ) : (
              <Icon className="h-4 w-4 text-white" />
            )}
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
                    status === "skipped" && "bg-gray-500/10 text-gray-700 border-gray-500/20",
                    status === "fallback" && "bg-orange-500/10 text-orange-700 border-orange-500/20"
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
                      Mostrar detalles
                    </>
                  )}
                </Button>

                <div className={cn(
                  "space-y-3 overflow-hidden transition-all duration-200",
                  isExpanded ? "max-h-[1000px] opacity-100" : "max-h-0 opacity-0"
                )}>
                  <div className="space-y-3">
                    {/* Input Summary */}
                    {entry.input_summary && (
                      <div>
                        <Label className="text-xs text-muted-foreground">Input</Label>
                        <div className="mt-1.5 bg-muted/50 p-3 rounded-md">
                          {(() => {
                            try {
                              const parsed = JSON.parse(entry.input_summary);
                              return <JsonViewer data={parsed} />;
                            } catch {
                              return (
                                <p className="text-xs text-foreground/80">
                                  {entry.input_summary}
                                </p>
                              );
                            }
                          })()}
                        </div>
                      </div>
                    )}

                    {/* Output Summary */}
                    {entry.output_summary && (
                      <div>
                        <Label className="text-xs text-muted-foreground">Output</Label>
                        <div className="mt-1.5 bg-muted/50 p-3 rounded-md">
                          {(() => {
                            try {
                              const parsed = JSON.parse(entry.output_summary);
                              return <JsonViewer data={parsed} />;
                            } catch {
                              return (
                                <p className="text-xs text-foreground/80">
                                  {entry.output_summary}
                                </p>
                              );
                            }
                          })()}
                        </div>
                      </div>
                    )}

                    {/* LLM Interaction Viewer */}
                    <LLMInteractionViewer
                      prompt={entry.llm_prompt}
                      response={entry.llm_response_raw}
                      model={entry.llm_model}
                      temperature={entry.llm_temperature}
                      tokens={entry.llm_tokens_used}
                    />

                    {/* RAG Query Viewer */}
                    <RAGQueryViewer
                      query={entry.rag_query}
                      scores={entry.rag_scores}
                    />

                    {/* Fallback Indicator */}
                    {entry.fallback_reason && (
                      <Alert variant="default" className="border-orange-500/20 bg-orange-50/50">
                        <AlertCircle className="h-4 w-4 text-orange-600" />
                        <AlertTitle className="text-orange-800">Fallback Activado</AlertTitle>
                        <AlertDescription className="text-orange-700">
                          {entry.fallback_reason}
                        </AlertDescription>
                      </Alert>
                    )}

                    {/* Error Details */}
                    {entry.error_details && (
                      <Alert variant="destructive">
                        <AlertCircle className="h-4 w-4" />
                        <AlertTitle>Error</AlertTitle>
                        <AlertDescription className="font-mono text-xs">
                          {entry.error_details}
                        </AlertDescription>
                      </Alert>
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
  isLast,
  agentStates
}: {
  phaseGroup: PhaseGroup;
  isLast: boolean;
  agentStates: Map<string, AgentState>;
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
            agentState={agentStates.get(entry.agent_name)}
          />
        ))}
      </div>
    </div>
  );
}

export function AgentTraceTimeline({ trace, liveEvents = [] }: AgentTraceTimelineProps) {
  // Calculate agent states from live events
  const agentStates = useMemo(() => {
    const states = new Map<string, AgentState>();
    const completedRecently = new Set<string>();

    // Track which agents are running or just completed
    liveEvents.forEach((event) => {
      if (event.event === "agent_started" && event.agent) {
        states.set(event.agent, { status: "running" });
      } else if (event.event === "agent_completed" && event.agent) {
        // Check if this was recently completed (within last 2 seconds)
        const eventTime = new Date(event.timestamp).getTime();
        const now = Date.now();
        const justCompleted = (now - eventTime) < 2000;

        states.set(event.agent, {
          status: "completed",
          justCompleted
        });

        if (justCompleted) {
          completedRecently.add(event.agent);
        }
      }
    });

    return states;
  }, [liveEvents]);

  const hasLiveUpdates = liveEvents.length > 0;

  if (!trace || trace.length === 0) {
    return (
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Traza de Ejecución de Agentes</CardTitle>
            {hasLiveUpdates && (
              <Badge variant="outline" className="bg-blue-500/10 text-blue-700 border-blue-500/20">
                <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                En vivo
              </Badge>
            )}
          </div>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <Clock className="h-12 w-12 text-muted-foreground/40 mb-3" />
            <p className="text-sm text-muted-foreground">
              Análisis no iniciado
            </p>
            <p className="text-xs text-muted-foreground mt-1">
              No hay datos de ejecución de agentes disponibles
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
          <div className="flex items-center gap-2">
            <CardTitle>Traza de Ejecución de Agentes</CardTitle>
            {hasLiveUpdates && (
              <Badge variant="outline" className="bg-blue-500/10 text-blue-700 border-blue-500/20 animate-pulse">
                <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                En vivo
              </Badge>
            )}
          </div>
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
            agentStates={agentStates}
          />
        ))}
      </CardContent>
    </Card>
  );
}
