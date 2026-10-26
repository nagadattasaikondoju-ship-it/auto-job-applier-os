"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { toast } from "sonner";
import { EMPTY_PREFERENCES, PREFERENCE_STEPS, type PrefValue } from "@/components/app/preferences-form";
import { Button, Card, ErrorState, PageHeader, Spinner } from "@/components/app/ui";
import { api } from "@/lib/api/endpoints";
import type { Preferences } from "@/lib/api/types";

export default function PreferencesPage() {
  const prefs = useQuery({ queryKey: ["preferences"], queryFn: api.preferences.get });
  if (prefs.isPending) return <Spinner label="Loading your preferences" />;
  if (prefs.isError) return <ErrorState error={prefs.error} onRetry={() => prefs.refetch()} />;
  return <PreferencesEditor initial={prefs.data} />;
}

function PreferencesEditor({ initial }: { initial: Preferences }) {
  const queryClient = useQueryClient();
  const { exists: _exists, ...rest } = initial;
  void _exists;
  const [v, setV] = useState<PrefValue>({ ...EMPTY_PREFERENCES, ...rest });
  const set = <K extends keyof PrefValue>(k: K, val: PrefValue[K]) => setV((s) => ({ ...s, [k]: val }));

  const save = useMutation({
    mutationFn: () => api.preferences.save(v),
    onSuccess: () => {
      toast.success("Preferences saved. Searching for jobs that match.");
      api.jobs.discover().catch(() => undefined);
      api.matches.refresh().catch(() => undefined);
      void queryClient.invalidateQueries({ queryKey: ["preferences"] });
      void queryClient.invalidateQueries({ queryKey: ["jobs"] });
      void queryClient.invalidateQueries({ queryKey: ["matches"] });
      void queryClient.invalidateQueries({ queryKey: ["autopilot"] });
    },
    onError: (e) => toast.error(e.message),
  });

  const invalid = PREFERENCE_STEPS.find((s) => !s.valid(v));

  return (
    <>
      <PageHeader
        title="Job preferences"
        description="What you want. Applyon uses this to search job sources, score matches and decide what to apply to."
        actions={
          <Button onClick={() => save.mutate()} loading={save.isPending} disabled={Boolean(invalid)}>
            Save preferences
          </Button>
        }
      />
      {invalid && (
        <p role="alert" className="mb-4 rounded-app-lg bg-app-surface px-4 py-3">
          Please answer: {invalid.title}
        </p>
      )}
      <form
        className="flex flex-col gap-5"
        onSubmit={(e) => {
          e.preventDefault();
          if (!invalid) save.mutate();
        }}
      >
        {PREFERENCE_STEPS.map((step) => (
          <Card as="section" key={step.id} aria-labelledby={`pref-${step.id}`} className="p-5 sm:p-6">
            <h2 id={`pref-${step.id}`} className="text-base font-medium">
              {step.title}
            </h2>
            <p className="mt-1 mb-4 text-app-muted">{step.description}</p>
            {step.render(v, set)}
          </Card>
        ))}
        <div className="flex justify-end">
          <Button type="submit" loading={save.isPending} disabled={Boolean(invalid)}>
            Save preferences
          </Button>
        </div>
      </form>
    </>
  );
}
