/**
 * Applyon Content Script (Manifest V3)
 */
let activePlan = null;

function findInputElement(field) {
  if (field.dom_selector) {
    try {
      const el = document.querySelector(field.dom_selector);
      if (el) return el;
    } catch {}
  }

  const idEl = document.getElementById(field.field_id);
  if (idEl) return idEl;

  const nameEl = document.querySelector(`[name="${field.field_id}"]`);
  if (nameEl) return nameEl;

  const labels = Array.from(document.querySelectorAll("label"));
  const normTarget = field.label.toLowerCase().replace(/[^a-z0-9]/g, "");

  for (const lbl of labels) {
    const normLbl = (lbl.textContent || "").toLowerCase().replace(/[^a-z0-9]/g, "");
    if (normLbl.includes(normTarget) || normTarget.includes(normLbl)) {
      if (lbl.htmlFor) {
        const target = document.getElementById(lbl.htmlFor);
        if (target) return target;
      }
      const childInput = lbl.querySelector("input, select, textarea");
      if (childInput) return childInput;
      if (lbl.nextElementSibling && ["INPUT", "SELECT", "TEXTAREA"].includes(lbl.nextElementSibling.tagName)) {
        return lbl.nextElementSibling;
      }
    }
  }

  return null;
}

function setInputValue(element, value) {
  if (value === null || value === undefined) return;

  if (element instanceof HTMLInputElement) {
    if (element.type === "checkbox") {
      element.checked = Boolean(value);
    } else if (element.type === "radio") {
      element.checked = element.value.toLowerCase() === String(value).toLowerCase();
    } else if (element.type !== "file") {
      element.value = String(value);
    }
  } else if (element instanceof HTMLTextAreaElement) {
    element.value = String(value);
  } else if (element instanceof HTMLSelectElement) {
    const valLower = String(value).toLowerCase();
    for (let i = 0; i < element.options.length; i++) {
      const opt = element.options[i];
      if (
        opt.value.toLowerCase() === valLower ||
        opt.text.toLowerCase().includes(valLower) ||
        valLower.includes(opt.text.toLowerCase())
      ) {
        element.selectedIndex = i;
        break;
      }
    }
  }

  element.dispatchEvent(new Event("input", { bubbles: true }));
  element.dispatchEvent(new Event("change", { bubbles: true }));
}

function attachReviewBadge(element, field) {
  const existingBadge = element.parentElement?.querySelector(".applyon-field-badge");
  if (existingBadge) existingBadge.remove();

  const badge = document.createElement("span");
  badge.className = "applyon-field-badge";
  badge.style.display = "inline-block";
  badge.style.fontSize = "11px";
  badge.style.fontWeight = "600";
  badge.style.padding = "2px 8px";
  badge.style.borderRadius = "9999px";
  badge.style.marginBottom = "4px";

  if (field.needs_review) {
    badge.style.backgroundColor = "#fef3c7";
    badge.style.color = "#92400e";
    badge.style.border = "1px solid #fcd34d";
    badge.innerText = "⚠️ Applyon: Review answer";
  } else {
    badge.style.backgroundColor = "#d1fae5";
    badge.style.color = "#065f46";
    badge.style.border = "1px solid #6ee7b7";
    badge.innerText = "✓ Applyon Verified";
  }

  element.parentElement?.insertBefore(badge, element);
}

async function executeAutofill(plan) {
  activePlan = plan;
  let filledCount = 0;

  for (const field of plan.fields) {
    if (field.value === null || field.value === undefined) continue;

    const el = findInputElement(field);
    if (el) {
      setInputValue(el, field.value);
      attachReviewBadge(el, field);
      filledCount++;
    }
  }

  console.log(`Applyon: Successfully autofilled ${filledCount} fields.`);
}

function setupSubmissionObserver() {
  const successKeywords = [
    "thank you for applying",
    "application submitted",
    "we have received your application",
    "thanks for applying",
    "application received",
  ];

  const observer = new MutationObserver(() => {
    const bodyText = (document.body.innerText || "").toLowerCase();
    for (const kw of successKeywords) {
      if (bodyText.includes(kw) && activePlan) {
        console.log("Applyon: Detected successful application submission!");
        chrome.runtime.sendMessage({
          type: "MARK_SUBMITTED",
          payload: {
            application_id: activePlan.application_id,
            proof_url: location.href,
            proof_text: kw,
          },
        });
        observer.disconnect();
        break;
      }
    }
  });

  observer.observe(document.body, { childList: true, subtree: true });
}

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "AUTOFILL_CURRENT_PAGE") {
    chrome.runtime.sendMessage(
      { type: "FETCH_FILL_PLAN", url: location.href },
      (response) => {
        if (response && response.success && response.data) {
          executeAutofill(response.data);
          sendResponse({ success: true, count: response.data.fields.length });
        } else {
          sendResponse({ success: false, error: response?.error || "Failed to fetch plan" });
        }
      }
    );
    return true;
  }
});

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", setupSubmissionObserver);
} else {
  setupSubmissionObserver();
}
