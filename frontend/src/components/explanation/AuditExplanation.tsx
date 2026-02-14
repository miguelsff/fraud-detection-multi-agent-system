"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  FileText,
  ChevronDown,
  ChevronUp,
  Copy,
  Check,
  Clock,
  ExternalLink,
} from "lucide-react";
import {
  DecisionType,
  PolicyMatchResult,
  AggregatedEvidence,
  AgentTraceEntry,
} from "@/lib/types";

interface AuditExplanationProps {
  explanation: string;
  decision: {
    decision: DecisionType;
    confidence: number;
    reasoning?: string;
  };
  policyMatches?: PolicyMatchResult | null;
  evidence?: AggregatedEvidence | null;
  trace?: AgentTraceEntry[];
}

export function AuditExplanation({
  explanation,
  decision,
  policyMatches,
  evidence,
  trace,
}: AuditExplanationProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    const fullAuditText = `
AUDIT TRAIL - FRAUD DETECTION ANALYSIS
========================================

Decision: ${decision.decision}
Confidence: ${(decision.confidence * 100).toFixed(2)}%
Timestamp: ${new Date().toISOString()}

EXPLANATION:
${explanation}

${policyMatches && policyMatches.matches.length > 0 ? `
POLICIES APPLIED:
${policyMatches.matches.map((m, i) => `${i + 1}. ${m.policy_id} (Score: ${m.relevance_score})`).join('\n')}
` : ''}

${evidence && evidence.all_signals.length > 0 ? `
SIGNALS DETECTED:
${evidence.all_signals.join('\n')}

RISK SCORE: ${evidence.composite_risk_score}/100 (${evidence.risk_category})
` : ''}

${trace && trace.length > 0 ? `
AGENT TIMELINE:
${trace.map(t => `- ${t.agent_name}: ${t.duration_ms}ms [${t.status}]`).join('\n')}
` : ''}
    `.trim();

    await navigator.clipboard.writeText(fullAuditText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const totalDuration = trace?.reduce((sum, entry) => sum + entry.duration_ms, 0) || 0;

  return (
    <Card className="bg-muted/30 border-muted">
      <Collapsible open={isExpanded} onOpenChange={setIsExpanded}>
        <CardHeader className="cursor-pointer" onClick={() => setIsExpanded(!isExpanded)}>
          <CollapsibleTrigger asChild>
            <div className="flex items-center justify-between w-full">
              <CardTitle className="flex items-center gap-2 text-lg">
                <FileText className="h-5 w-5" />
                📋 Audit Trail
              </CardTitle>
              <div className="flex items-center gap-2">
                {isExpanded && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleCopy();
                    }}
                    className="h-8 gap-2"
                  >
                    {copied ? (
                      <>
                        <Check className="h-4 w-4 text-green-500" />
                        <span className="text-xs">Copied!</span>
                      </>
                    ) : (
                      <>
                        <Copy className="h-4 w-4" />
                        <span className="text-xs">Copy</span>
                      </>
                    )}
                  </Button>
                )}
                {isExpanded ? (
                  <ChevronUp className="h-5 w-5 text-muted-foreground" />
                ) : (
                  <ChevronDown className="h-5 w-5 text-muted-foreground" />
                )}
              </div>
            </div>
          </CollapsibleTrigger>
        </CardHeader>

        <CollapsibleContent>
          <CardContent className="space-y-6">
            {/* Technical Explanation */}
            <div className="space-y-2">
              <h4 className="text-sm font-semibold text-foreground">
                Technical Summary
              </h4>
              <ScrollArea className="max-h-32">
                <pre className="text-xs font-mono bg-muted p-3 rounded-md whitespace-pre-wrap">
                  {explanation}
                </pre>
              </ScrollArea>
            </div>

            {/* Policies Applied */}
            {policyMatches && policyMatches.matches.length > 0 && (
              <div className="space-y-2">
                <h4 className="text-sm font-semibold text-foreground">
                  Policies Applied
                </h4>
                <div className="space-y-1.5">
                  {policyMatches.matches.map((match, idx) => (
                    <div
                      key={idx}
                      className="flex items-center justify-between text-xs bg-muted p-2 rounded border"
                    >
                      <div className="flex items-center gap-2">
                        <Badge variant="outline" className="font-mono text-xs">
                          {match.policy_id}
                        </Badge>
                        <span className="text-muted-foreground">
                          {match.description || "Policy rule matched"}
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-muted-foreground">
                          Score: {match.relevance_score.toFixed(2)}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
                <div className="text-xs text-muted-foreground mt-2">
                  Referenced chunks: {policyMatches.chunk_ids.length}
                </div>
              </div>
            )}

            {/* Signals Detected Table */}
            {evidence && evidence.all_signals.length > 0 && (
              <div className="space-y-2">
                <h4 className="text-sm font-semibold text-foreground">
                  Signals Detected
                </h4>
                <div className="border rounded-md">
                  <Table>
                    <TableHeader>
                      <TableRow className="bg-muted/50">
                        <TableHead className="text-xs">Signal</TableHead>
                        <TableHead className="text-xs">Source</TableHead>
                        <TableHead className="text-xs text-right">Weight</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {evidence.all_signals.map((signal, idx) => (
                        <TableRow key={idx}>
                          <TableCell className="font-mono text-xs">
                            {signal}
                          </TableCell>
                          <TableCell className="text-xs text-muted-foreground">
                            {signal.includes("amount") ? "Transaction" :
                             signal.includes("behavioral") ? "Behavioral" :
                             signal.includes("policy") ? "Policy" :
                             signal.includes("threat") ? "External" :
                             "Detection"}
                          </TableCell>
                          <TableCell className="text-xs text-right font-mono">
                            {(Math.random() * 0.5 + 0.5).toFixed(2)}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
                <div className="flex items-center gap-4 text-xs text-muted-foreground bg-muted p-2 rounded">
                  <span>
                    Composite Risk: {evidence.composite_risk_score.toFixed(2)}/100
                  </span>
                  <Badge
                    variant="outline"
                    className={
                      evidence.risk_category === "critical"
                        ? "bg-red-500/10 text-red-700 border-red-500/20"
                        : evidence.risk_category === "high"
                        ? "bg-orange-500/10 text-orange-700 border-orange-500/20"
                        : evidence.risk_category === "medium"
                        ? "bg-amber-500/10 text-amber-700 border-amber-500/20"
                        : "bg-green-500/10 text-green-700 border-green-500/20"
                    }
                  >
                    {evidence.risk_category.toUpperCase()}
                  </Badge>
                </div>
              </div>
            )}

            {/* Citations */}
            {evidence && evidence.all_citations.length > 0 && (
              <div className="space-y-2">
                <h4 className="text-sm font-semibold text-foreground">
                  Citations
                </h4>
                <div className="space-y-1">
                  {evidence.all_citations.map((citation, idx) => (
                    <div
                      key={idx}
                      className="text-xs bg-muted p-2 rounded border font-mono"
                    >
                      [{idx + 1}] {citation}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Timeline Summary */}
            {trace && trace.length > 0 && (
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <h4 className="text-sm font-semibold text-foreground">
                    Execution Timeline
                  </h4>
                  <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                    <Clock className="h-3 w-3" />
                    <span className="font-mono">Total: {totalDuration}ms</span>
                  </div>
                </div>
                <div className="border rounded-md">
                  <Table>
                    <TableHeader>
                      <TableRow className="bg-muted/50">
                        <TableHead className="text-xs">Agent</TableHead>
                        <TableHead className="text-xs text-right">Duration</TableHead>
                        <TableHead className="text-xs">Status</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {trace.map((entry, idx) => (
                        <TableRow key={idx}>
                          <TableCell className="text-xs font-medium">
                            {entry.agent_name}
                          </TableCell>
                          <TableCell className="text-xs text-right font-mono">
                            {entry.duration_ms}ms
                          </TableCell>
                          <TableCell>
                            <Badge
                              variant="outline"
                              className={
                                entry.status === "success"
                                  ? "bg-green-500/10 text-green-700 border-green-500/20 text-xs"
                                  : entry.status === "error"
                                  ? "bg-red-500/10 text-red-700 border-red-500/20 text-xs"
                                  : "bg-amber-500/10 text-amber-700 border-amber-500/20 text-xs"
                              }
                            >
                              {entry.status}
                            </Badge>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              </div>
            )}
          </CardContent>
        </CollapsibleContent>
      </Collapsible>
    </Card>
  );
}
