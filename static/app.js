(() => {
  const select = document.querySelector('#theme-select');
  const applyTheme = (mode) => { document.documentElement.dataset.theme = mode; if (select) select.value = mode; };
  applyTheme(localStorage.getItem('portfolio-theme') || 'system');
  select?.addEventListener('change', () => { localStorage.setItem('portfolio-theme', select.value); applyTheme(select.value); });

  document.querySelector('#stop-operator')?.addEventListener('click', async () => { if (!window.confirm('Stop only this local portfolio operator? Project services remain unchanged.')) return; const r = await fetch('/operator/stop', {method:'POST'}); const p = await r.json(); window.alert(p.human_message || 'The local operator is stopping.'); });

  const running = new Set(['READY','RUNNING']);
  // Standard HTML form submission is the primary action path.  The server's
  // POST/303/GET contract works with JavaScript disabled and prevents a
  // browser refresh from repeating the registered action.
  document.querySelectorAll('form.action-form').forEach((form) => form.addEventListener('submit', () => {
    const button = form.querySelector('button');
    // Defer the visual lock until after the browser has performed the native
    // form default action; disabling synchronously can cancel that submission.
    if (button) setTimeout(() => { button.disabled = true; button.textContent = 'Starting…'; }, 0);
  }));
  const execution=document.querySelector('#execution-view'); if(execution){ const id=execution.dataset.executionId; const refresh=async()=>{try{const r=await fetch(`/api/executions/${encodeURIComponent(id)}`);const p=await r.json();if(running.has(p.status))setTimeout(refresh,350);else window.location.reload();}catch(_){setTimeout(refresh,700);}}; refresh(); }
  document.querySelectorAll('form.feedback-form').forEach((form) => form.addEventListener('submit', async (event) => { event.preventDefault(); const out=document.querySelector('#feedback-result'); if(!out)return; out.textContent='Recording human feedback…'; try { const p=await (await fetch(form.action,{method:'POST',body:new URLSearchParams(new FormData(form))})).json(); out.textContent=(p.status==='RECORDED'||p.status==='ALREADY_RECORDED')?`${p.status}: human feedback was stored locally.`:`Feedback was not recorded: ${p.human_message||'input could not be accepted.'}`; } catch(_) {out.textContent='Feedback could not be recorded.';} }));
})();
