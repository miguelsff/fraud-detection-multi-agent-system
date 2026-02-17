import { Suspense } from "react";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import { CheckCircle } from "lucide-react";
import { getHITLQueue } from "@/lib/api";
import { HITLQueueClient } from "./HITLQueueClient";
import { RefreshButton } from "./RefreshButton";

export const dynamic = "force-dynamic";

async function HITLContent() {
  const cases = await getHITLQueue();

  if (cases.length === 0) {
    return (
      <Alert className="border-green-500 bg-green-50">
        <CheckCircle className="h-5 w-5 text-green-600" />
        <AlertTitle className="text-green-900">Todo Despejado</AlertTitle>
        <AlertDescription className="text-green-800">
          No hay casos pendientes de revisión. Todas las transacciones escaladas han sido resueltas.
        </AlertDescription>
      </Alert>
    );
  }

  return <HITLQueueClient initialCases={cases} />;
}

function LoadingSkeleton() {
  return (
    <div className="space-y-4">
      {[1, 2, 3].map((i) => (
        <div key={i} className="border rounded-lg p-6 space-y-4">
          <div className="flex items-start justify-between">
            <div className="space-y-2 flex-1">
              <Skeleton className="h-6 w-48" />
              <Skeleton className="h-4 w-64" />
            </div>
            <Skeleton className="h-8 w-8 rounded" />
          </div>
        </div>
      ))}
    </div>
  );
}

export default function HITLPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h1 className="text-3xl font-bold">Cola de Revisión Humana</h1>
          <Suspense fallback={<Skeleton className="h-6 w-12 rounded-full" />}>
            <QueueBadge />
          </Suspense>
        </div>
        <RefreshButton />
      </div>

      <p className="text-muted-foreground">
        Revisa transacciones que requieren juicio humano debido a señales ambiguas de fraude.
      </p>

      <Suspense fallback={<LoadingSkeleton />}>
        <HITLContent />
      </Suspense>
    </div>
  );
}

async function QueueBadge() {
  const cases = await getHITLQueue();

  if (cases.length === 0) {
    return null;
  }

  return (
    <Badge variant="secondary" className="bg-violet-100 text-violet-700 border-violet-300">
      {cases.length} {cases.length === 1 ? "caso" : "casos"}
    </Badge>
  );
}
