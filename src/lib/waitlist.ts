export interface WaitlistEntry {
  email: string;
  timestamp: string;
  source?: string;
}

export async function submitToWaitlist(email: string, source: string = "hero"): Promise<{ success: boolean; message: string }> {
  // Simulate network latency
  await new Promise((resolve) => setTimeout(resolve, 800));

  try {
    if (typeof window !== "undefined") {
      const existing: WaitlistEntry[] = JSON.parse(localStorage.getItem("applyon_waitlist") || "[]");
      const alreadySubscribed = existing.some((item) => item.email.toLowerCase() === email.toLowerCase());

      if (alreadySubscribed) {
        return {
          success: true,
          message: "You're already on the priority waitlist! We'll be in touch soon.",
        };
      }

      existing.push({
        email,
        timestamp: new Date().toISOString(),
        source,
      });

      localStorage.setItem("applyon_waitlist", JSON.stringify(existing));
    }

    return {
      success: true,
      message: "You're in! We'll email you soon with early access.",
    };
  } catch (err) {
    console.error("Waitlist error:", err);
    return {
      success: false,
      message: "Something went wrong. Please try again.",
    };
  }
}
