"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bell } from "lucide-react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Button, Card, EmptyState, ErrorState, PageHeader, SkeletonList } from "@/components/app/ui";
import { api } from "@/lib/api/endpoints";
import type { Notification } from "@/lib/api/types";
import { timeAgo } from "@/lib/format";
import { cn } from "@/lib/utils";

/** Where a notification should take you, based on the ids it carries. */
function targetFor(n: Notification): string | null {
  const d = n.data ?? {};
  if (typeof d.application_id === "string") return `/applications/${d.application_id}`;
  if (typeof d.job_id === "string") return `/jobs/${d.job_id}`;
  if (n.type.includes("review")) return "/review";
  return null;
}

export default function NotificationsPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const list = useQuery({ queryKey: ["notifications", "all"], queryFn: () => api.notifications.list(false) });

  const refresh = () => void queryClient.invalidateQueries({ queryKey: ["notifications"] });

  const markRead = useMutation({ mutationFn: (id: string) => api.notifications.read(id), onSuccess: refresh });
  const markAll = useMutation({
    mutationFn: api.notifications.readAll,
    onSuccess: (r) => {
      toast.success(`Marked ${r.marked_read_count} as read.`);
      refresh();
    },
    onError: (e) => toast.error(e.message),
  });

  return (
    <>
      <PageHeader
        title="Notifications"
        actions={
          (list.data?.unread_count ?? 0) > 0 && (
            <Button variant="secondary" onClick={() => markAll.mutate()} loading={markAll.isPending}>
              Mark all as read
            </Button>
          )
        }
      />
      {list.isPending ? (
        <SkeletonList rows={5} />
      ) : list.isError ? (
        <Card>
          <ErrorState error={list.error} onRetry={() => list.refetch()} />
        </Card>
      ) : list.data.items.length === 0 ? (
        <Card>
          <EmptyState icon={Bell} title="No notifications" description="We'll let you know when applications are ready or need you." />
        </Card>
      ) : (
        <Card>
          <ul className="divide-y divide-app-border">
            {list.data.items.map((n) => {
              const target = targetFor(n);
              const unread = !n.read_at;
              return (
                <li key={n.id}>
                  <button
                    type="button"
                    onClick={() => {
                      if (unread) markRead.mutate(n.id);
                      if (target) router.push(target);
                    }}
                    className={cn(
                      "flex w-full gap-3 px-5 py-4 text-left transition-colors hover:bg-app-bg outline-none focus-visible:bg-app-bg focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-app-accent",
                      !target && !unread && "cursor-default"
                    )}
                  >
                    <span
                      className={cn("mt-1.5 size-2 shrink-0 rounded-full", unread ? "bg-app-accent" : "bg-transparent")}
                      aria-hidden="true"
                    />
                    <span className="min-w-0 flex-1">
                      <span className={cn("block", unread ? "font-medium text-app-ink" : "text-app-ink-2")}>
                        {n.title}
                        {unread && <span className="sr-only"> (unread)</span>}
                      </span>
                      {n.body && <span className="block text-app-muted">{n.body}</span>}
                    </span>
                    <span className="shrink-0 text-xs text-app-subtle">{timeAgo(n.created_at)}</span>
                  </button>
                </li>
              );
            })}
          </ul>
        </Card>
      )}
    </>
  );
}
