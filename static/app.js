(() => {
  const select = document.querySelector('#theme-select');
  const applyTheme = (mode) => { document.documentElement.dataset.theme = mode; if (select) select.value = mode; };
  applyTheme(localStorage.getItem('portfolio-theme') || 'system');
  select?.addEventListener('change', () => { localStorage.setItem('portfolio-theme', select.value); applyTheme(select.value); });

  document.querySelector('#stop-operator')?.addEventListener('click', async () => { if (!window.confirm('Stop only this local portfolio operator? Project services remain unchanged.')) return; const r = await fetch('/operator/stop', {method:'POST'}); const p = await r.json(); window.alert(p.human_message || 'The local operator is stopping.'); });

  const running = new Set(['ACCEPTED', 'READY', 'RUNNING']);
  const terminal = new Set(['PASS', 'FAIL', 'BLOCKED', 'CANCELLED', 'ERROR', 'UNKNOWN_ERROR', 'NOT_APPLICABLE']);
  // Standard HTML form submission is the primary action path.  The server's
  // POST/303/GET contract works with JavaScript disabled and prevents a
  // browser refresh from repeating the registered action.
  const resetTransientActionControls = () => document.querySelectorAll('form.action-form button[data-original-label]').forEach((button) => {
    button.disabled = false;
    button.textContent = button.dataset.originalLabel;
  });
  window.addEventListener('pageshow', resetTransientActionControls);
  document.querySelectorAll('form.action-form').forEach((form) => form.addEventListener('submit', () => {
    const button = form.querySelector('button');
    // Defer the visual lock until after the browser has performed the native
    // form default action; disabling synchronously can cancel that submission.
    if (button) setTimeout(() => { button.disabled = true; button.textContent = 'Starting…'; }, 0);
  }));
  const execution = document.querySelector('#execution-view');
  if (document.body.dataset.page === 'execution' && execution) {
    const id = document.body.dataset.executionId || execution.dataset.executionId;
    let timer = null;
    let controller = null;
    let failures = 0;
    let stopped = false;
    let inFlight = false;
    const text = (selector, value) => { const node = document.querySelector(selector); if (node && value !== undefined && value !== null) node.textContent = String(value); };
    const connection = document.querySelector('#execution-connection');
    const retry = document.querySelector('#execution-retry-status');
    const stop = () => { stopped = true; if (timer) window.clearTimeout(timer); if (controller) controller.abort(); };
    const patch = (record) => {
      text('#execution-status', record.status);
      text('#execution-human-summary', record.human_summary);
      text('#execution-technical-summary', record.technical_summary);
      text('#execution-evidence', record.evidence_reference || 'NOT_CHECKED');
      text('#execution-receipt', `${record.receipt_reference || 'NOT_CHECKED'} · integrity ${record.receipt_integrity || 'NOT_CHECKED'}`);
      text('#execution-exit-code', record.exit_code === null || record.exit_code === undefined ? 'NOT_APPLICABLE' : record.exit_code);
      if (Array.isArray(record.stages)) text('#execution-stages', record.stages.map((stage) => `${stage.stage} (${stage.status})`).join(' → '));
    };
    const schedule = (delay) => { if (!stopped) timer = window.setTimeout(poll, delay); };
    const poll = async () => {
      if (stopped || !id || inFlight) return;
      inFlight = true;
      controller = new AbortController();
      try {
        const response = await fetch(`/api/executions/${encodeURIComponent(id)}`, { signal: controller.signal, headers: { Accept: 'application/json' } });
        if (!response.ok) throw new Error(`status ${response.status}`);
        const record = await response.json();
        failures = 0;
        patch(record);
        if (terminal.has(record.status)) { stop(); return; }
        if (connection) connection.textContent = 'Checking local operation status…';
        schedule(1000);
      } catch (error) {
        if (stopped || error.name === 'AbortError') return;
        failures += 1;
        if (failures >= 3) {
          if (connection) connection.textContent = 'STATUS_UNAVAILABLE. Connection to the local operator was interrupted.';
          if (retry) retry.hidden = false;
          return;
        }
        if (connection) connection.textContent = 'Connection to local operator was interrupted. Retrying status check…';
        schedule(Math.min(2000, 700 * failures));
      } finally {
        inFlight = false;
      }
    };
    retry?.addEventListener('click', () => { failures = 0; retry.hidden = true; if (connection) connection.textContent = 'Retrying local status check…'; poll(); });
    window.addEventListener('visibilitychange', () => {
      if (document.visibilityState === 'visible' && !stopped && !terminal.has(document.querySelector('#execution-status')?.textContent?.trim())) poll();
    });
    window.addEventListener('pagehide', stop, { once: true });
    const initialStatus = execution.querySelector('#execution-status')?.textContent?.trim();
    if (!terminal.has(initialStatus)) poll();
  }
  document.querySelectorAll('form.feedback-form').forEach((form) => form.addEventListener('submit', async (event) => { event.preventDefault(); const out=document.querySelector('#feedback-result'); if(!out)return; out.textContent='Recording human feedback…'; try { const p=await (await fetch(form.action,{method:'POST',body:new URLSearchParams(new FormData(form))})).json(); out.textContent=(p.status==='RECORDED'||p.status==='ALREADY_RECORDED')?`${p.status}: human feedback was stored locally.`:`Feedback was not recorded: ${p.human_message||'input could not be accepted.'}`; } catch(_) {out.textContent='Feedback could not be recorded.';} }));
})();
