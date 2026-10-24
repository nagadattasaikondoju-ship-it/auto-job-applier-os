/**
 * Applyon Chrome Extension Background Service Worker (Manifest V3)
 * Handles auth storage, API requests to backend, and message passing.
 */

const DEFAULT_API_BASE = "http://localhost:8000";

interface StorageData {
  authToken?: string;
  apiBaseUrl?: string;
}

// Get configured API base URL or fallback to localhost
async function getApiBase(): Promise<string> {
  const data: StorageData = await chrome.storage.local.get(["apiBaseUrl"]);
  return data.apiBaseUrl || DEFAULT_API_BASE;
}

// Get JWT token from chrome storage
async function getAuthToken(): Promise<string | null> {
  const data: StorageData = await chrome.storage.local.get(["authToken"]);
  return data.authToken || null;
}

// Set extension action badge
function updateBadge(text: string, color: string = "#4f46e5") {
  chrome.action.setBadgeText({ text });
  chrome.action.setBadgeBackgroundColor({ color });
}

chrome.runtime.onInstalled.addListener(() => {
  console.log("Applyon Extension installed successfully.");
  chrome.storage.local.set({ apiBaseUrl: DEFAULT_API_BASE });
});

// Message listener for popup and content script requests
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  const handleAsync = async () => {
    try {
      const apiBase = await getApiBase();
      const token = await getAuthToken();
      const headers: Record<string, string> = {
        "Content-Type": "application/json",
      };
      if (token) {
        headers["Authorization"] = `Bearer ${token}`;
      } else {
        // Fallback to dev user in local development
        headers["X-Dev-User-Id"] = "dev-user-123";
      }

      if (message.type === "FETCH_FILL_PLAN") {
        const resp = await fetch(
          `${apiBase}/v1/extension/fill-plan?url=${encodeURIComponent(message.url)}`,
          { headers }
        );
        if (!resp.ok) {
          throw new Error(`Failed to fetch fill plan: ${resp.statusText}`);
        }
        const data = await resp.json();

        // Update badge with unresolved fields count
        if (data.unresolved_count > 0) {
          updateBadge(`${data.unresolved_count}`, "#f59e0b");
        } else {
          updateBadge("OK", "#10b981");
        }

        return { success: true, data };
      }

      if (message.type === "MARK_SUBMITTED") {
        const resp = await fetch(`${apiBase}/v1/extension/mark-submitted`, {
          method: "POST",
          headers,
          body: JSON.stringify(message.payload),
        });
        const data = await resp.json();
        updateBadge("DONE", "#10b981");
        return { success: true, data };
      }

      if (message.type === "SET_AUTH") {
        await chrome.storage.local.set({ authToken: message.token });
        return { success: true };
      }

      if (message.type === "GET_AUTH_STATUS") {
        return { authenticated: Boolean(token), token };
      }

      return { success: false, error: "Unknown message type" };
    } catch (err: any) {
      console.error("Background error:", err);
      return { success: false, error: err.message || "Unknown error" };
    }
  };

  handleAsync().then(sendResponse);
  return true; // Keep message port open for async response
});
