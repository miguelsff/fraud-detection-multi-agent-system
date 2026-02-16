import { getPolicies } from "@/lib/api";
import PoliciesClient from "@/components/policies/PoliciesClient";

export const dynamic = "force-dynamic";

export default async function PoliciesPage() {
  const policies = await getPolicies();

  return (
    <div className="container mx-auto py-8 px-4">
      <div className="mb-8">
        <h1 className="text-3xl font-bold tracking-tight">Políticas de Fraude</h1>
        <p className="text-muted-foreground mt-2">
          Gestione las políticas y reglas de detección de fraude. Las políticas se
          sincronizan automáticamente con la base de datos vectorial para análisis en tiempo real.
        </p>
      </div>
      <PoliciesClient initialPolicies={policies} />
    </div>
  );
}
