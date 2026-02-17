"use client";

import { useState } from "react";
import { HITLQueue } from "@/components/hitl/HITLQueue";
import type { HITLCase } from "@/lib/types";

interface HITLQueueClientProps {
  initialCases: HITLCase[];
}

export function HITLQueueClient({ initialCases }: HITLQueueClientProps) {
  const [cases, setCases] = useState<HITLCase[]>(initialCases);

  const handleCaseResolved = (caseId: number) => {
    // Remove the resolved case from the list
    setCases((prevCases) => prevCases.filter((c) => c.id !== caseId));
  };

  if (cases.length === 0) {
    // If all cases have been resolved during this session
    return (
      <div className="text-center py-12 border rounded-lg bg-green-50 border-green-200">
        <p className="text-lg font-medium text-green-900">All cases resolved!</p>
        <p className="text-muted-foreground mt-2">
          Refresh the page to check for new escalated cases.
        </p>
      </div>
    );
  }

  return <HITLQueue cases={cases} onCaseResolved={handleCaseResolved} />;
}
