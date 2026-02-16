import { Bot } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";

interface LLMInteractionProps {
  prompt: string | null | undefined;
  response: string | null | undefined;
  model: string | null | undefined;
  temperature: number | null | undefined;
  tokens: number | null | undefined;
}

export function LLMInteractionViewer({
  prompt,
  response,
  model,
  temperature,
  tokens,
}: LLMInteractionProps) {
  if (!prompt) return null;

  return (
    <Card className="mt-3 border-purple-200 bg-purple-50/50">
      <CardHeader>
        <div className="flex items-center gap-2">
          <Bot className="h-4 w-4 text-purple-600" />
          <CardTitle className="text-sm">Interacción LLM</CardTitle>
          {model && (
            <Badge variant="outline" className="ml-auto">
              {model}
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {/* Prompt */}
        <div>
          <Label className="text-xs text-muted-foreground">Prompt Enviado</Label>
          <pre className="mt-1 rounded-md bg-slate-900 p-3 text-xs text-slate-50 overflow-x-auto max-h-96 overflow-y-auto">
            {prompt}
          </pre>
        </div>

        {/* Response */}
        {response && (
          <div>
            <Label className="text-xs text-muted-foreground">
              Respuesta Bruta
            </Label>
            <pre className="mt-1 rounded-md bg-slate-900 p-3 text-xs text-slate-50 overflow-x-auto max-h-96 overflow-y-auto">
              {response}
            </pre>
          </div>
        )}

        {/* Metadata */}
        <div className="flex gap-4 text-xs text-muted-foreground">
          {temperature !== null && temperature !== undefined && (
            <span>Temperature: {temperature}</span>
          )}
          {tokens && <span>Tokens: {tokens.toLocaleString()}</span>}
        </div>
      </CardContent>
    </Card>
  );
}
