import { connection } from "next/server";
import { Suspense } from "react";

async function Connection() {
  await connection();
  return null;
}

/**
 * Cache Components: marks a route with runtime params (e.g. /jobs/[id]) as intentionally dynamic,
 * so the static shell still prerenders while route metadata streams in.
 */
export function DynamicMarker() {
  return (
    <Suspense>
      <Connection />
    </Suspense>
  );
}
