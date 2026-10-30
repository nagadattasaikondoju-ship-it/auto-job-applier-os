"use client";

import { useEffect } from "react";
import { wakeApi } from "@/lib/api/client";

/** Starts waking the API as soon as any page loads, so it's ready by the time the user signs in. */
export function WakeApi() {
  useEffect(() => wakeApi(), []);
  return null;
}
