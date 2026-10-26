import { Skeleton } from "@/components/app/ui";

// Suspense fallback for every page in the app shell (also required for pages that read route params).
export default function Loading() {
  return (
    <div className="flex flex-col gap-4" role="status" aria-label="Loading">
      <Skeleton className="h-10 w-64" />
      <Skeleton className="h-5 w-96 max-w-full" />
      <Skeleton className="mt-4 h-64 w-full rounded-app-xl" />
    </div>
  );
}
