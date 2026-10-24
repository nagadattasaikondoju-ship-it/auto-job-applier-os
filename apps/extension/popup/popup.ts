/**
 * Applyon Extension Popup Logic
 */

document.addEventListener("DOMContentLoaded", async () => {
  const atsStatus = document.getElementById("atsStatus")!;
  const jobTitle = document.getElementById("jobTitle")!;
  const companyName = document.getElementById("companyName")!;
  const autofillBtn = document.getElementById("autofillBtn")!;
  const dashboardBtn = document.getElementById("dashboardBtn")!;
  const statusMessage = document.getElementById("statusMessage")!;

  // 1. Query active tab
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab || !tab.url) {
    statusMessage.innerText = "Please open a job posting tab.";
    return;
  }

  // 2. Query fill plan to inspect ATS & job details
  chrome.runtime.sendMessage(
    { type: "FETCH_FILL_PLAN", url: tab.url },
    (response) => {
      if (response && response.success && response.data) {
        const data = response.data;
        atsStatus.innerText = data.ats_type.toUpperCase();
        jobTitle.innerText = data.job_title;
        companyName.innerText = data.company_name;

        const unresolved = data.unresolved_count;
        if (unresolved > 0) {
          statusMessage.innerText = `${data.fields.length - unresolved}/${data.fields.length} fields verified. ${unresolved} review needed.`;
        } else {
          statusMessage.innerText = `All ${data.fields.length} fields verified & ready!`;
        }
      } else {
        atsStatus.innerText = "STANDALONE";
        statusMessage.innerText = "Ready to detect form fields.";
      }
    }
  );

  // 3. Handle Autofill click
  autofillBtn.addEventListener("click", () => {
    statusMessage.innerText = "Autofilling form fields...";
    chrome.tabs.sendMessage(tab.id!, { action: "AUTOFILL_CURRENT_PAGE" }, (resp) => {
      if (resp && resp.success) {
        statusMessage.innerText = `Success! Filled ${resp.count} fields.`;
      } else {
        statusMessage.innerText = resp?.error || "Autofill completed.";
      }
    });
  });

  // 4. Handle dashboard click
  dashboardBtn.addEventListener("click", () => {
    chrome.tabs.create({ url: "http://localhost:3000" });
  });
});
