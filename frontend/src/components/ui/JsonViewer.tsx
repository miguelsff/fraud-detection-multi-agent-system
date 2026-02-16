"use client";

import { useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";

interface JsonViewerProps {
  data: unknown;
  level?: number;
}

export function JsonViewer({ data, level = 0 }: JsonViewerProps) {
  const [expanded, setExpanded] = useState(level === 0);

  if (typeof data !== "object" || data === null) {
    return <span className="text-blue-600">{JSON.stringify(data)}</span>;
  }

  const isArray = Array.isArray(data);
  const entries = isArray
    ? (data as unknown[]).map((v, i) => [i, v] as [string | number, unknown])
    : Object.entries(data as Record<string, unknown>);

  if (entries.length === 0) {
    return (
      <span className="text-slate-500">{isArray ? "[]" : "{}"}</span>
    );
  }

  return (
    <div className="font-mono text-xs">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-1 hover:bg-slate-100 rounded px-1 transition-colors"
        type="button"
      >
        {expanded ? (
          <ChevronDown className="h-3 w-3" />
        ) : (
          <ChevronRight className="h-3 w-3" />
        )}
        <span className="text-slate-500">{isArray ? "[" : "{"}</span>
        {!expanded && (
          <span className="text-slate-400">
            {entries.length} {isArray ? "items" : "keys"}...
          </span>
        )}
        {!expanded && (
          <span className="text-slate-500">{isArray ? "]" : "}"}</span>
        )}
      </button>

      {expanded && (
        <div className="ml-4 border-l border-slate-200 pl-2">
          {entries.map(([key, value]) => (
            <div key={key} className="py-0.5">
              <span className="text-purple-600">{key}:</span>{" "}
              <JsonViewer data={value} level={level + 1} />
            </div>
          ))}
        </div>
      )}

      {expanded && (
        <span className="text-slate-500">{isArray ? "]" : "}"}</span>
      )}
    </div>
  );
}
