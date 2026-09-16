document.addEventListener("DOMContentLoaded", () => {
  const stopButton = document.querySelector("#stop-operator");
  if (stopButton) {
    stopButton.addEventListener("click", async () => {
      if (!window.confirm("Stop only this local portfolio operator? Project services will remain unchanged.")) return;
      stopButton.disabled = true;
      try {
        const response = await fetch("/operator/stop", { method: "POST" });
        const payload = await response.json();
        window.alert(payload.meaning || payload.reason || "The local operator is stopping.");
      } catch (error) {
        window.alert(`The local operator could not confirm shutdown: ${error}`);
      }
    });
  }

  document.querySelectorAll("form[data-destructive='true']").forEach((form) => {
    form.addEventListener("submit", (event) => {
      if (!window.confirm("This action removes local runtime resources. Continue?")) {
        event.preventDefault();
        return;
      }
      const confirmation = form.querySelector("input[name='confirm']");
      if (confirmation) confirmation.value = "true";
    });
  });

  document.querySelectorAll("form.action-form").forEach((form) => {
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const panel = document.querySelector("#operation-result");
      const button = form.querySelector("button");
      if (!panel || !button) return;
      panel.hidden = false;
      panel.innerHTML = "<h2>Operation</h2><p><strong>Status:</strong> RUNNING</p><p>Starting the registered project action…</p>";
      button.disabled = true;
      try {
        const response = await fetch(form.action, { method: "POST", body: new FormData(form) });
        const result = await response.json();
        const details = result.technical_details || {};
        const technical = [details.stdout, details.stderr].filter(Boolean).join("\n");
        panel.replaceChildren();
        const heading = document.createElement("h2");
        heading.textContent = "Operation result";
        panel.appendChild(heading);
        [
          ["Project", result.project_id || "UNKNOWN"],
          ["Action", result.action || "UNKNOWN"],
          ["Status", result.status || "UNKNOWN"],
          ["What happened", result.result_summary || result.reason || "No summary was returned."],
          ["Meaning", result.meaning || "Review the operation result."],
          ["Evidence", result.evidence_reference || "No evidence reference returned."],
          ["Next useful action", result.next_action || "Review the project surface."]
        ].forEach(([label, value]) => {
          const line = document.createElement("p");
          const key = document.createElement("strong");
          key.textContent = `${label}: `;
          line.append(key, document.createTextNode(value));
          panel.appendChild(line);
        });
        if (technical) {
          const details = document.createElement("details");
          const summary = document.createElement("summary");
          summary.textContent = "Technical details";
          const pre = document.createElement("pre");
          pre.textContent = technical;
          details.append(summary, pre);
          panel.appendChild(details);
        }
      } catch (error) {
        panel.innerHTML = `<h2>Operation result</h2><p><strong>Status:</strong> FAIL</p><p>Unable to contact the local operator surface: ${error}</p>`;
      } finally {
        button.disabled = false;
      }
    });
  });

  document.querySelectorAll("form.feedback-form").forEach((form) => {
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const result = document.querySelector("#feedback-result");
      if (!result) return;
      result.textContent = "Recording HUMAN feedback…";
      try {
        const response = await fetch(form.action, { method: "POST", body: new FormData(form) });
        const payload = await response.json();
        result.textContent = payload.status === "RECORDED" || payload.status === "ALREADY_RECORDED"
          ? `${payload.status}: HUMAN feedback was stored locally. It does not change project evidence or trigger retraining.`
          : `Feedback was not recorded: ${payload.reason || "unknown reason"}`;
      } catch (error) {
        result.textContent = `Feedback could not be recorded: ${error}`;
      }
    });
  });
});
