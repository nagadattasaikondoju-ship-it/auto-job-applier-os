"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check } from "lucide-react";
import { toast } from "sonner";
import { Badge, Button, Card, CardHeader, ErrorState, PageHeader, ProgressBar, Skeleton } from "@/components/app/ui";
import { api } from "@/lib/api/endpoints";
import { formatDate, humanize } from "@/lib/format";
import { cn } from "@/lib/utils";

const PLAN_ORDER = ["free", "starter", "pro", "elite"];

export default function BillingPage() {
  const queryClient = useQueryClient();
  const balance = useQuery({ queryKey: ["credits"], queryFn: api.billing.balance });
  const plans = useQuery({ queryKey: ["plans"], queryFn: api.billing.plans, staleTime: 3_600_000 });
  const ledger = useQuery({ queryKey: ["ledger", 1], queryFn: () => api.billing.ledger(1) });

  const order = useMutation({
    mutationFn: (planId: string) => api.billing.createOrder(planId),
    onSuccess: (o) => {
      if (o.gateway === "sandbox") {
        toast.info("Payments are in sandbox mode. Razorpay checkout will open here once it's connected.");
      }
    },
    onError: (e) => toast.error(e.message),
  });

  const topup = useMutation({
    mutationFn: () => api.billing.topupDemo(10, "apply"),
    onSuccess: () => {
      toast.success("Added 10 demo apply credits.");
      void queryClient.invalidateQueries({ queryKey: ["credits"] });
      void queryClient.invalidateQueries({ queryKey: ["ledger"] });
    },
    onError: (e) => toast.error(e.message),
  });

  const b = balance.data;
  const daily = b && typeof b.daily_limit === "object" ? b.daily_limit : null;

  return (
    <>
      <PageHeader title="Plan & credits" description="Credits are reserved when work starts and only charged when it succeeds." />

      {balance.isError ? (
        <Card className="mb-6">
          <ErrorState error={balance.error} onRetry={() => balance.refetch()} />
        </Card>
      ) : (
        <div className="grid gap-3 sm:grid-cols-3 mb-8">
          {balance.isPending ? (
            Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-32 rounded-app-xl" />)
          ) : (
            <>
              <Card className="p-5">
                <p className="text-app-muted">Current plan</p>
                <p className="mt-2 font-display text-3xl">{b!.plan_name}</p>
                {daily && (
                  <p className="mt-1 text-xs text-app-muted">
                    Up to <span className="font-mono">{daily.limit ?? "—"}</span> applications a day
                  </p>
                )}
              </Card>
              <Card className="p-5">
                <p className="text-app-muted">Apply credits</p>
                <p className="mt-2 font-mono text-3xl">{b!.apply_credits.available}</p>
                <p className="mt-1 text-xs text-app-muted">
                  {b!.apply_credits.held > 0 ? `${b!.apply_credits.held} reserved for work in progress` : "Used when an application is filled or submitted"}
                </p>
              </Card>
              <Card className="p-5">
                <p className="text-app-muted">AI credits</p>
                <p className="mt-2 font-mono text-3xl">{b!.ai_credits.available}</p>
                <p className="mt-1 text-xs text-app-muted">Used for tailored resumes, cover letters and answers</p>
              </Card>
            </>
          )}
        </div>
      )}

      {daily && typeof daily.used === "number" && typeof daily.limit === "number" && (
        <Card className="mb-8 p-5">
          <div className="flex justify-between text-sm">
            <span>Applications today</span>
            <span className="font-mono">
              {daily.used} / {daily.limit}
            </span>
          </div>
          <div className="mt-2">
            <ProgressBar value={(daily.used / Math.max(1, daily.limit)) * 100} label="Daily applications used" />
          </div>
        </Card>
      )}

      <section aria-labelledby="plans-title" className="mb-8">
        <h2 id="plans-title" className="mb-3 text-base font-medium">
          Plans
        </h2>
        {plans.isPending ? (
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-72 rounded-app-xl" />
            ))}
          </div>
        ) : plans.isError ? (
          <Card>
            <ErrorState error={plans.error} onRetry={() => plans.refetch()} />
          </Card>
        ) : (
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            {PLAN_ORDER.filter((id) => plans.data.plans[id]).map((id) => {
              const plan = plans.data.plans[id];
              const current = b?.plan === id;
              return (
                <Card key={id} className={cn("p-5 flex flex-col", current && "border-app-ink")}>
                  <div className="flex items-center justify-between">
                    <p className="font-medium">{plan.name}</p>
                    {current && <Badge tone="success">Current</Badge>}
                    {id === "pro" && !current && <Badge>Most popular</Badge>}
                  </div>
                  <p className="mt-3">
                    <span className="font-display text-4xl">₹{plan.price_inr.toLocaleString("en-IN")}</span>
                    <span className="text-app-muted"> /month</span>
                  </p>
                  <ul className="mt-4 flex flex-1 flex-col gap-2 text-app-ink-2">
                    <li className="flex gap-2">
                      <Check className="mt-0.5 size-4 shrink-0 text-app-accent" aria-hidden="true" />
                      {plan.monthly_apply_credits} apply · {plan.monthly_ai_credits} AI credits a month
                    </li>
                    <li className="flex gap-2">
                      <Check className="mt-0.5 size-4 shrink-0 text-app-accent" aria-hidden="true" />
                      Up to {plan.daily_application_limit} applications a day
                    </li>
                    {plan.features.map((f) => (
                      <li key={f} className="flex gap-2">
                        <Check className="mt-0.5 size-4 shrink-0 text-app-accent" aria-hidden="true" />
                        {f}
                      </li>
                    ))}
                  </ul>
                  <Button
                    className="mt-5 w-full"
                    variant={current ? "secondary" : id === "pro" ? "primary" : "secondary"}
                    disabled={current || plan.price_inr === 0}
                    loading={order.isPending && order.variables === id}
                    onClick={() => order.mutate(id)}
                  >
                    {current ? "Your plan" : plan.price_inr === 0 ? "Free" : `Upgrade to ${plan.name}`}
                  </Button>
                </Card>
              );
            })}
          </div>
        )}
      </section>

      <Card as="section" aria-labelledby="ledger-title">
        <CardHeader
          id="ledger-title"
          title="Credit history"
          action={
            process.env.NODE_ENV === "development" && (
              <Button variant="ghost" size="sm" onClick={() => topup.mutate()} loading={topup.isPending}>
                Add 10 demo credits
              </Button>
            )
          }
        />
        {ledger.isPending ? (
          <div className="px-5 pb-5">
            <Skeleton className="h-24" />
          </div>
        ) : ledger.isError ? (
          <ErrorState error={ledger.error} onRetry={() => ledger.refetch()} />
        ) : ledger.data.items.length === 0 ? (
          <p className="px-5 pb-5 text-app-muted">No credit activity yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <caption className="sr-only">Credit history</caption>
              <thead className="border-y border-app-border bg-app-bg text-xs text-app-muted">
                <tr>
                  <th scope="col" className="px-5 py-2.5 font-medium">Date</th>
                  <th scope="col" className="px-5 py-2.5 font-medium">What</th>
                  <th scope="col" className="px-5 py-2.5 font-medium">Type</th>
                  <th scope="col" className="px-5 py-2.5 font-medium text-right">Amount</th>
                  <th scope="col" className="px-5 py-2.5 font-medium text-right">Balance</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-app-border">
                {ledger.data.items.map((e) => (
                  <tr key={e.id}>
                    <td className="px-5 py-3 text-app-ink-2 whitespace-nowrap">{formatDate(e.created_at)}</td>
                    <td className="px-5 py-3">{humanize(e.reason)}</td>
                    <td className="px-5 py-3 text-app-ink-2 capitalize">{e.credit_type}</td>
                    <td className={cn("px-5 py-3 text-right font-mono", e.amount < 0 ? "text-app-ink" : "text-app-accent")}>
                      {e.amount > 0 ? `+${e.amount}` : e.amount}
                    </td>
                    <td className="px-5 py-3 text-right font-mono text-app-ink-2">{e.balance_after}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </>
  );
}
