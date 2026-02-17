import { Database } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

interface RAGQueryViewerProps {
  query: string | null | undefined;
  scores: Record<string, number> | null | undefined;
}

export function RAGQueryViewer({ query, scores }: RAGQueryViewerProps) {
  if (!query) return null;

  return (
    <Card className="mt-3 border-blue-200 bg-blue-50/50">
      <CardHeader>
        <div className="flex items-center gap-2">
          <Database className="h-4 w-4 text-blue-600" />
          <CardTitle className="text-sm">Consulta RAG</CardTitle>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <div>
          <Label className="text-xs text-muted-foreground">Query</Label>
          <p className="mt-1 text-sm">{query}</p>
        </div>

        {scores && Object.keys(scores).length > 0 && (
          <div>
            <Label className="text-xs text-muted-foreground">
              Scores de Recuperación
            </Label>
            <Table className="mt-2">
              <TableHeader>
                <TableRow>
                  <TableHead>Chunk ID</TableHead>
                  <TableHead className="text-right">Similitud</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {Object.entries(scores)
                  .sort(([, a], [, b]) => b - a)
                  .map(([chunkId, score]) => (
                    <TableRow key={chunkId}>
                      <TableCell className="font-mono text-xs">
                        {chunkId}
                      </TableCell>
                      <TableCell className="text-right">
                        {score.toFixed(3)}
                      </TableCell>
                    </TableRow>
                  ))}
              </TableBody>
            </Table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
