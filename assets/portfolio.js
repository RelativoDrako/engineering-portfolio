(() => {
  'use strict';

  /* --------------------------------------------------------------------------
     PROJECT RECONCILIATION REGISTRY
     All metrics, hashes, and outcomes are grounded in validated repository evidence.
     NP01: c23fd11dedfe81ba8e1c529197e782abffcb4acd
     NP02: 287d718a323e2b979d622c8671414a4574e1e538
     NP03: 55d9c6afaed7b5351f1a60e7eee6ceb33550132 (40 chars)
     NP04: 5d5dc8f787d397bcde097a83a09e0cb7a6b7d971
  -------------------------------------------------------------------------- */

  const projects = [
    {
      id: 'NP01',
      name: 'Industrial Resilience OT Lab',
      domain: 'OT / Industrial Resilience',
      problem: 'A synthetic industrial process demonstrates how control software detects faults, enters a controlled degraded state, recovers explicitly and preserves verifiable evidence of what occurred.',
      result: '3 injected faults · 12-state trace · 15/15 scenario checks · replay PASS',
      commit: 'c23fd11dedfe81ba8e1c529197e782abffcb4acd',
      run: '20260915T075000Z_np01_canonical',
      replay_digest: 'fff4d86e23321ff0945ac2e7b7c55b5d9e1925d277ad791db9baab5a5238f496',
      limit: 'Synthetic local lab; not production control or functional-safety certification.',
      repo: 'https://github.com/RelativoDrako/industrial-resilience-ot-lab',
      why: 'Makes failure handling, degraded state entry, and recovery behavior inspectable rather than implicit.',
      test_summary: '11 passed',
      test_categories: [
        { category: 'State transitions & fault recovery logic', count: 3, file: 'tests/test_state_machine.py' },
        { category: 'Modbus TCP & MQTT edge transport contracts', count: 2, file: 'tests/test_transport.py' },
        { category: 'Deterministic replay & digest verification', count: 2, file: 'tests/test_replay.py' },
        { category: 'Operational run contract & receipt verification', count: 2, file: 'tests/test_operational_run_contract.py' },
        { category: 'Project structure & greenfield boundary checks', count: 2, file: 'tests/test_project_contract.py' }
      ],
      failure_behavior: 'Three distinct fault injections demonstrate controlled resilience: (1) STALE_SENSOR freezes telemetry, triggering degraded mode and safe output clamp; (2) COMMUNICATION_LOSS detects transport heartbeat timeout, holding failsafe interlocks; (3) INVALID_STATE_OR_VALUE detects out-of-bounds telemetry, asserts safety interlocks, and shifts the cell to FAULT. In all cases, recovery requires explicit verification before returning to steady-state RUNNING.',
      faults: [
        { id: 'FAULT_01', type: 'STALE_SENSOR', trigger: 'Level sensor telemetry freezes at constant value', behavior: 'Enters DEGRADED mode, clamps inflow valve, logs telemetry anomaly', recovery: 'Detects fresh telemetry heartbeat, verifies sensor delta, resumes RUNNING' },
        { id: 'FAULT_02', type: 'COMMUNICATION_LOSS', trigger: 'Edge collector transport drops heartbeat', behavior: 'Enters DEGRADED mode, holds failsafe state, maintains local buffer', recovery: 'Re-establishes transport session, verifies heartbeat before RUNNING' },
        { id: 'FAULT_03', type: 'INVALID_STATE_OR_VALUE', trigger: 'Out-of-range sensor value violates physical bounds', behavior: 'Enters FAULT state, halts transfer pump, asserts safety interlock', recovery: 'Requires explicit reset transition through RECOVERY after clearing interlock' }
      ],
      state_trace: [
        { step: 1, state: 'IDLE', desc: 'System initialized, safety interlocks verified' },
        { step: 2, state: 'FILL', desc: 'Inflow active, primary tank filling' },
        { step: 3, state: 'TRANSFER', desc: 'Transfer pump engaged to secondary tank' },
        { step: 4, state: 'RUNNING', desc: 'Steady-state operation reached' },
        { step: 5, state: 'DEGRADED', desc: 'Fault 01 (STALE_SENSOR) active; degraded mode entered' },
        { step: 6, state: 'RECOVERY', desc: 'Fault 01 cleared; guided recovery initiated' },
        { step: 7, state: 'RUNNING', desc: 'Normal operation restored' },
        { step: 8, state: 'RECOVERY', desc: 'Fault 02 (COMMUNICATION_LOSS) recovery cycle' },
        { step: 9, state: 'RUNNING', desc: 'Transport verified, steady-state resumed' },
        { step: 10, state: 'FAULT', desc: 'Fault 03 (INVALID_STATE_OR_VALUE); interlock trip' },
        { step: 11, state: 'RECOVERY', desc: 'Fault 03 reset; interlock verified clean' },
        { step: 12, state: 'RUNNING', desc: 'Final verified steady-state' }
      ]
    },
    {
      id: 'NP02',
      name: 'Governed Data & Analytics',
      domain: 'Data Architecture / Analytics Governance',
      problem: 'Imperfect source records are checked against contract rules and quality controls before they are allowed into trusted analytics.',
      result: '28 accepted · 2 quarantined · 3 rejected · quality, lineage and KPI PASS',
      commit: '287d718a323e2b979d622c8671414a4574e1e538',
      run: '20260915T075000Z_np02_canonical',
      limit: 'Bounded synthetic pipeline; not enterprise-scale production data engineering.',
      repo: 'https://github.com/RelativoDrako/governed-data-analytics',
      why: 'Questionable information is preserved in quarantine for review instead of silently contaminating trusted analytics or being discarded without a trace.',
      test_summary: '12 passed',
      test_categories: [
        { category: 'Contract schema enforcement', count: 2, file: 'tests/test_contracts.py' },
        { category: 'Domain models & Pydantic validation', count: 2, file: 'tests/test_models.py' },
        { category: 'Operational run contract, receipts & replay', count: 5, file: 'tests/test_operational_run_contract.py' },
        { category: 'Pipeline admission, quarantine & lineage logic', count: 2, file: 'tests/test_pipeline_contracts.py' },
        { category: 'SQL transformation & schema assertions', count: 1, file: 'tests/test_sql_contracts.py' }
      ],
      failure_behavior: 'Incoming batches contain intentional schema and referential anomalies. The pipeline applies a strict tri-disposition gate: 28 conforming records are ACCEPTED into curated PostgreSQL tables; 2 records with non-fatal data defects (duplicate event ID and unknown foreign key) are preserved in a QUARANTINE table with error metadata for operator investigation; 3 structurally invalid records (unparsable values, missing required fields, schema changes) are REJECTED at ingestion.',
      disposition: [
        { status: 'ACCEPTED', count: 28, badge: 'badge-success', desc: 'Satisfied contract schemas and referential integrity; loaded into curated dimensions and facts' },
        { status: 'QUARANTINED', count: 2, badge: 'badge-warning', desc: 'Preserved in quarantine store with validation errors (duplicate event, unknown foreign key) for audit' },
        { status: 'REJECTED', count: 3, badge: 'badge-danger', desc: 'Fatal contract violations (missing required fields, invalid domain values, schema divergence)' }
      ],
      quality_rules: [
        { rule: 'completeness', desc: 'Missing required fields', bad_count: 1, denom: 13, status: 'PASS (flagged fixture)' },
        { rule: 'uniqueness', desc: 'Duplicate identifiers', bad_count: 1, denom: 13, status: 'PASS (flagged fixture)' },
        { rule: 'referential_integrity', desc: 'Unknown foreign keys', bad_count: 1, denom: 13, status: 'PASS (flagged fixture)' },
        { rule: 'validity', desc: 'Invalid domain values', bad_count: 1, denom: 13, status: 'PASS (flagged fixture)' },
        { rule: 'duplicate_detection', desc: 'Duplicate record hashes', bad_count: 1, denom: 13, status: 'PASS (flagged fixture)' },
        { rule: 'curated_fk_integrity', desc: 'Zero orphan curated foreign keys in production tables', bad_count: 0, denom: 8, status: 'PASS (0 errors)' }
      ],
      kpis: [
        { name: 'Average Resolution Time', value: '27.43 hours', target: '< 48 hours' },
        { name: 'Closure Rate', value: '87.5%', target: '> 80%' },
        { name: 'Total Service Cost', value: '$3,815.00', target: 'Illustrative cost' },
        { name: 'Curated Service Events', value: '8 events', target: '100% clean curated' }
      ]
    },
    {
      id: 'NP03',
      name: 'Governed AI Assurance',
      domain: 'AI Assurance / Evidence Governance',
      problem: 'An evidence-grounded evaluation harness ensures that query responses are grounded in verified citations and abstains when evidence is insufficient or contradictory.',
      result: '6 cases · 2 supported · 3 human review · 1 abstain · false support 0',
      commit: '55d9c6afaed7b5351f1a60e7eee6ceb33550132',
      run: '20260915T075000Z_np03_canonical',
      replay_digest: 'd6ee210d5d4c3c24f587198398cefb2938c547a37d157d3346dc29499f31726d',
      limit: 'Small synthetic corpus (9 docs, 10 chunks) and local, run-scoped evaluation; no generalized model-quality claim.',
      repo: 'https://github.com/RelativoDrako/governed-ai-assurance',
      why: 'Abstention and escalation to human review are treated as controlled safety outcomes rather than system failures.',
      test_summary: '17 passed',
      test_categories: [
        { category: 'Ground truth evaluation logic & scoring', count: 2, file: 'tests/test_evaluation.py' },
        { category: 'Corpus manifest integrity & SHA-256 hashing', count: 2, file: 'tests/test_manifest.py' },
        { category: 'Operational run contract & replay receipts', count: 3, file: 'tests/test_operational_run_contract.py' },
        { category: 'Project boundaries & claim verification', count: 2, file: 'tests/test_project_contract.py' },
        { category: 'Deterministic replay verification', count: 1, file: 'tests/test_replay.py' },
        { category: 'Lexical TF-IDF cosine retrieval', count: 3, file: 'tests/test_retrieval.py' },
        { category: 'Tri-state classification & false-support rules', count: 4, file: 'tests/test_validation.py' }
      ],
      failure_behavior: 'When retrieved evidence is incomplete, absent, or conflicting, the assurance harness prevents ungrounded answers. In CASE-003, where the topic (energy savings) is completely absent, the system strictly ABSTAINS. In CASE-002 and CASE-005, where retrieved source revisions state contradictory facts (alarm ownership and sampling intervals), the system routes to HUMAN_REVIEW_REQUIRED. In CASE-004, where top-k retrieval covers only 50% of required facts, the system also escalates to human review. Zero unsupported claims cross the SUPPORTED boundary.',
      cases: [
        { id: 'CASE-001', type: 'Supported Query', query: 'What permits a pump restart in the synthetic transfer cell?', required_ids: 'DOC-001::SEC-001', coverage: '1.0', outcome: 'SUPPORTED', reviewer: 'N/A (Autonomous Pass)', reason: 'Single stable document chunk unambiguously answers query.' },
        { id: 'CASE-002', type: 'Ambiguous Query', query: 'Which component records the alarm acknowledgement?', required_ids: 'DOC-002, DOC-003', coverage: '1.0', outcome: 'HUMAN_REVIEW_REQUIRED', reviewer: 'ABSTAIN', reason: 'Two synthetic document revisions assign ownership differently; reviewer must resolve revision conflict.' },
        { id: 'CASE-003', type: 'Unsupported Query', query: 'What is the annual energy saving percentage for the cell?', required_ids: 'None', coverage: '0.0', outcome: 'ABSTAIN', reviewer: 'N/A (Correct Abstention)', reason: 'Synthetic corpus contains zero energy-saving claims; system strictly abstains.' },
        { id: 'CASE-004', type: 'Partial Evidence', query: 'What are the three transfer recovery actions?', required_ids: 'DOC-008, DOC-009', coverage: '0.5', outcome: 'HUMAN_REVIEW_REQUIRED', reviewer: 'ABSTAIN', reason: 'Top-1 retrieval returned partial coverage; routed to human review.' },
        { id: 'CASE-005', type: 'Conflicting Evidence', query: 'What is the level sensor sampling interval?', required_ids: 'DOC-004, DOC-005', coverage: '1.0', outcome: 'HUMAN_REVIEW_REQUIRED', reviewer: 'ABSTAIN', reason: 'Revisions state conflicting sampling intervals without precedence rule.' },
        { id: 'CASE-006', type: 'Duplicate Evidence', query: 'What is the maximum operating tank level?', required_ids: 'DOC-006', coverage: '1.0', outcome: 'SUPPORTED', reviewer: 'N/A (Autonomous Pass)', reason: 'Duplicate evidence chunk deduplicated without altering claim.' }
      ]
    },
    {
      id: 'NP04',
      name: 'Architecture Decision Workbench',
      domain: 'Architecture / Delivery Decision Reasoning',
      problem: 'Three architecture alternatives are evaluated against 18 requirements, assumptions, and cost constraints to produce a traceable decision record with sensitivity replay.',
      result: '18 requirements · 3 options · 54 fit-gap relationships · baseline OPTION_C',
      commit: '5d5dc8f787d397bcde097a83a09e0cb7a6b7d971',
      run: '20260915T075000Z_np04_canonical',
      limit: 'Synthetic advisory scenario with illustrative, non-binding costs; no procurement or budget authority.',
      repo: 'https://github.com/RelativoDrako/architecture-decision-workbench',
      why: 'The recommendation is transparently traceable to explicit assumptions and responds dynamically to sensitivity changes rather than being a static, hardcoded choice.',
      test_summary: '9 passed',
      test_categories: [
        { category: 'Operational run schema & replay receipts', count: 3, file: 'tests/test_operational_run_contract.py' },
        { category: 'Requirements fit-gap analysis & scoring', count: 3, file: 'tests/test_workbench.py' },
        { category: 'Sensitivity replay (ASM-002, ASM-005)', count: 2, file: 'tests/test_workbench.py' },
        { category: 'Verification matrix mapping', count: 1, file: 'tests/test_workbench.py' }
      ],
      failure_behavior: 'When foundational assumptions change, architecture recommendations must adapt predictably. Under ASM-002 (connectivity degrades further), OPTION_C is retained because lower WAN reliability reinforces the necessity of edge buffering. Under ASM-005 (CAPEX budget reduced from 180k to 140k), OPTION_C becomes infeasible due to dual-infrastructure costs, causing the recommendation to shift defensibly to OPTION_B (pure edge).',
      options: [
        { id: 'OPTION_A', name: 'Cloud-Centric Architecture', summary: 'Centralized cloud ingestion and analytics; vulnerable to WAN interruptions; lowest edge hardware footprint.', capex: '95,000 cost units', opex: 'High', autonomy: 'Low (depends on WAN)' },
        { id: 'OPTION_B', name: 'Edge-Centric Architecture', summary: 'Autonomous local processing at plant sites; resilient to WAN outages; higher distributed maintenance.', capex: '135,000 cost units', opex: 'Medium', autonomy: 'High' },
        { id: 'OPTION_C', name: 'Hybrid Edge-Assisted Architecture', summary: 'Local edge buffering with upstream synchronization; selected baseline balancing autonomy and centralized reporting.', capex: '165,000 cost units', opex: 'Balanced', autonomy: 'High' }
      ],
      assumptions: {
        'Baseline': { selected: 'OPTION_C', desc: 'Standard WAN availability, 180,000 CAPEX envelope. Highest weighted balance across autonomy, latency, and centralized reporting.' },
        'ASM-002': { selected: 'OPTION_C (UNCHANGED)', desc: 'Connectivity reliability decreases. Unchanged decision: Lower WAN reliability reinforces the architectural requirement for local edge buffering and ordered replay.' },
        'ASM-005': { selected: 'OPTION_B (DECISION CHANGED)', desc: 'CAPEX envelope reduced from 180,000 to 140,000 cost units. Changed decision: Option C (165k) is excluded by the cost boundary; Option B (135k edge-centric) is the next-best feasible alternative.' }
      }
    }
  ];

  const byId = Object.fromEntries(projects.map(p => [p.id, p]));

  /* --------------------------------------------------------------------------
     EXPLANATORY & REASONING LAYER (OBSERVATION → EVIDENCE → CONCLUSION)
  -------------------------------------------------------------------------- */
  const reasoning = {
    NP01: {
      observation: 'Three injected faults produced a 12-state trace; all 15 scenario checks and replay passed.',
      evidence: 'Fault introduction, degraded/fault transitions, controlled recovery, validation checks, and replay.',
      interpretation: 'The bounded controller did not treat a fault as a hidden correction: its recovery path remained observable and repeatable.',
      conclusion: 'This scenario demonstrates controlled recovery under represented faults.',
      change: 'Different fault conditions or failed validation checks would change this bounded conclusion.',
      boundary: 'It does not prove production control performance or functional-safety certification.',
      takeaway: 'The project demonstrates a reviewable resilience pattern: detect, enter a controlled state, recover explicitly and validate the result.',
      technical: 'The SQLite journal is execution evidence; replay checks the represented state and recovery sequence.'
    },
    NP02: {
      observation: '28 records were accepted, 2 quarantined and 3 rejected; quality, lineage and KPI checks passed.',
      evidence: 'Source manifest, contract checks, disposition counts, quality results, lineage state and KPI outputs.',
      interpretation: 'Not every incoming record was treated as trusted. Questionable information was retained for review rather than silently entering analytics.',
      conclusion: 'The bounded pipeline demonstrates governed movement from imperfect source data to analytics.',
      change: 'A changed contract, validation result or lineage failure would change this conclusion.',
      boundary: 'It does not prove enterprise-scale or production data-engineering operation.',
      takeaway: 'The project demonstrates that useful analytics can remain traceable when admission, quality and lineage checks are explicit.',
      technical: 'PostgreSQL is the structured authority; quarantine is a disposition for review, not an automatic repair.'
    },
    NP03: {
      observation: 'In six bounded cases, 2 were supported, 3 required human review, 1 abstained and false support was 0.',
      evidence: 'Fixed evaluation cases, evidence coverage and citation validation, duplicate/conflict handling, tri-state outcomes and replay.',
      interpretation: 'No unsupported case crossed the represented SUPPORTED decision boundary; incomplete or conflicting evidence was routed conservatively.',
      conclusion: 'The bounded assurance scenario demonstrates conservative evidence-grounded decision behavior.',
      change: 'A failed citation or coverage rule, or a false-support case, would change this conclusion.',
      boundary: 'It does not establish generalized model accuracy or autonomous decision authority.',
      takeaway: 'The project demonstrates that abstention and human review can be intentional assurance outcomes when evidence is inadequate.',
      technical: 'The lexical baseline remains runnable without a model runtime; human review remains interpretation authority.'
    },
    NP04: {
      observation: '18 requirements were compared across 3 options, producing 54 fit-gap relationships and 54 traceability paths. Baseline selected OPTION_C; ASM-005 changes it to OPTION_B.',
      evidence: 'Requirements, constraints, explicit assumptions, fit-gap matrix, feasibility, risk and verification mapping, ADR and sensitivity replay.',
      interpretation: 'The recommendation is traceable to represented assumptions. Changing the CAPEX assumption changes the decision in this synthetic scenario.',
      conclusion: 'The workbench demonstrates traceable architecture decision-making under explicit assumptions.',
      change: 'A different connectivity, cost or autonomy assumption can alter the recommendation.',
      boundary: 'It does not prove procurement authority, budget authority or a real-client architecture decision.',
      takeaway: 'The project demonstrates a defensible decision path: requirements and assumptions lead to trade-offs, validation needs and an advisory recommendation.',
      technical: 'Costs are illustrative and non-binding; sensitivity replay records why an option remains or changes.'
    }
  };

  /* --------------------------------------------------------------------------
     DOM UTILITIES
  -------------------------------------------------------------------------- */
  const $ = (selector, node = document) => node.querySelector(selector);
  const escape = value => String(value ?? '').replace(/[&<>"']/g, c => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;'
  }[c]));

  /* --------------------------------------------------------------------------
     THEME MANAGEMENT
  -------------------------------------------------------------------------- */
  const themeSelect = $('#theme-select');
  const applyTheme = mode => {
    document.documentElement.dataset.theme = mode;
    if (themeSelect) themeSelect.value = mode;
  };

  const savedTheme = localStorage.getItem('portfolio-theme') || 'system';
  applyTheme(savedTheme);

  if (themeSelect) {
    themeSelect.addEventListener('change', () => {
      const mode = themeSelect.value;
      localStorage.setItem('portfolio-theme', mode);
      applyTheme(mode);
    });
  }

  /* --------------------------------------------------------------------------
     VIEW ROUTING
  -------------------------------------------------------------------------- */
  const navLinks = document.querySelectorAll('nav a[data-view-link]');
  const showView = view => {
    document.querySelectorAll('.view').forEach(section => {
      const active = section.id === view;
      section.hidden = !active;
      section.classList.toggle('active', active);
    });
    navLinks.forEach(link => {
      link.classList.toggle('active-link', link.dataset.viewLink === view);
    });
  };

  const route = () => {
    const hash = (location.hash || '#portfolio').slice(1);
    const valid = ['portfolio', 'evidence', 'about'].includes(hash) ? hash : 'portfolio';
    showView(valid);
  };

  window.addEventListener('hashchange', route);
  navLinks.forEach(link => link.addEventListener('click', event => {
    event.preventDefault();
    const view = link.dataset.viewLink;
    history.pushState(null, '', `#${view}`);
    showView(view);
  }));
  route();

  /* --------------------------------------------------------------------------
     RENDER PORTFOLIO VIEW (PROJECT CARDS)
  -------------------------------------------------------------------------- */
  const projectCardsContainer = $('#project-cards');
  if (projectCardsContainer) {
    projectCardsContainer.innerHTML = projects.map(p => `
      <article class="project-card">
        <p class="eyebrow">${escape(p.id)} · ${escape(p.domain)}</p>
        <h3>${escape(p.name)}</h3>
        <p>${escape(p.problem)}</p>
        <p class="result"><strong>Validated:</strong> ${escape(p.result)}</p>
        <div class="badge-row">
          <span class="badge badge-success">Validation: PASS</span>
          <span class="badge badge-accent">${escape(p.test_summary)}</span>
          <span class="badge badge-neutral">Local-first</span>
        </div>
        <div class="card-actions">
          <button type="button" data-project="${p.id}">Explore project</button>
          <a href="${p.repo}" target="_blank" rel="noopener noreferrer">GitHub ↗</a>
        </div>
      </article>
    `).join('');
  }

  /* --------------------------------------------------------------------------
     RENDER EVIDENCE VIEW (DEEP EXPLANATORY CARDS)
  -------------------------------------------------------------------------- */
  const evidenceCardsContainer = $('#evidence-cards');
  if (evidenceCardsContainer) {
    evidenceCardsContainer.innerHTML = projects.map(p => {
      const r = reasoning[p.id];
      return `
        <article class="evidence-card">
          <p class="eyebrow">${escape(p.id)} · Reasoning &amp; Provenance</p>
          <h2>${escape(p.name)}</h2>
          <p><strong>Observation:</strong> ${escape(r.observation)}</p>
          <p><strong>Evidence:</strong> ${escape(r.evidence)}</p>
          <p><strong>Interpretation:</strong> ${escape(r.interpretation)}</p>
          <p><strong>Conclusion:</strong> ${escape(r.conclusion)}</p>
          <p class="context-limit"><strong>Could change:</strong> ${escape(r.change)}</p>
          <p class="context-limit"><strong>Does not prove:</strong> ${escape(r.boundary)}</p>
          <details>
            <summary>Technical specifications &amp; test suite</summary>
            <p>${escape(r.technical)}</p>
            <dl>
              <dt>Validated commit</dt><dd><code>${escape(p.commit)}</code></dd>
              <dt>Canonical run</dt><dd><code>${escape(p.run)}</code></dd>
              <dt>Test suite</dt><dd>${escape(p.test_summary)}</dd>
              <dt>Replay</dt><dd><span class="badge badge-success">PASS (deterministic)</span></dd>
            </dl>
            <div class="table-wrapper">
              <table class="data-table">
                <thead><tr><th>Test category</th><th>Tests</th><th>Source test file</th></tr></thead>
                <tbody>
                  ${p.test_categories.map(tc => `<tr><td>${escape(tc.category)}</td><td>${tc.count}</td><td><code>${escape(tc.file)}</code></td></tr>`).join('')}
                </tbody>
              </table>
            </div>
          </details>
          <div class="card-actions" style="margin-top: 1rem;">
            <button type="button" data-project="${p.id}">Open full review</button>
            <a href="${p.repo}" target="_blank" rel="noopener noreferrer">View repository ↗</a>
          </div>
        </article>
      `;
    }).join('');
  }

  /* --------------------------------------------------------------------------
     INTERACTIVE PROJECT MODAL (DEEP REVIEW)
  -------------------------------------------------------------------------- */
  const dialog = $('#project-dialog');
  const detail = $('#project-detail');

  const renderExplorerMarkup = p => {
    if (p.id === 'NP01') {
      return `
        <section class="replay">
          <p class="eyebrow">Deterministic execution trace</p>
          <h2>12-State transition &amp; fault trace</h2>
          <p>Replays the validated sequence through normal operation, fault injection, degraded operation, and guided recovery. No project code is executed by this browser.</p>
          <div class="table-wrapper">
            <table class="data-table">
              <thead><tr><th>Step</th><th>Observed state</th><th>Operation / Fault description</th></tr></thead>
              <tbody>
                ${p.state_trace.map(st => `
                  <tr>
                    <td><strong>#${st.step}</strong></td>
                    <td><span class="badge ${st.state === 'FAULT' ? 'badge-danger' : st.state === 'DEGRADED' ? 'badge-warning' : st.state === 'RECOVERY' ? 'badge-accent' : 'badge-success'}">${st.state}</span></td>
                    <td>${escape(st.desc)}</td>
                  </tr>
                `).join('')}
              </tbody>
            </table>
          </div>
          <div class="replay-result">
            <strong>Validation outcome:</strong> 15 of 15 scenario assertions passed. Replay digest verified: <code>${p.replay_digest}</code>.
          </div>
        </section>
      `;
    }

    if (p.id === 'NP02') {
      return `
        <section class="replay">
          <p class="eyebrow">Data governance &amp; quality controls</p>
          <h2>Admission disposition &amp; quality execution</h2>
          <p>The pipeline enforces a strict 3-way admission gate. Questionable data is quarantined with error metadata for operator inspection instead of silently contaminating analytics.</p>
          <div class="table-wrapper">
            <table class="data-table">
              <thead><tr><th>Disposition</th><th>Count</th><th>Gate policy &amp; destination</th></tr></thead>
              <tbody>
                ${p.disposition.map(d => `
                  <tr>
                    <td><span class="badge ${d.badge}">${d.status}</span></td>
                    <td><strong>${d.count}</strong></td>
                    <td>${escape(d.desc)}</td>
                  </tr>
                `).join('')}
              </tbody>
            </table>
          </div>
          <h3 style="margin: 1.2rem 0 0.5rem; font-size: 1rem; color: var(--text-bright);">Quality rule validation report</h3>
          <div class="table-wrapper">
            <table class="data-table">
              <thead><tr><th>Quality rule</th><th>Defects detected</th><th>Tested scope</th><th>Execution status</th></tr></thead>
              <tbody>
                ${p.quality_rules.map(qr => `
                  <tr>
                    <td><code>${escape(qr.rule)}</code></td>
                    <td>${qr.bad_count} / ${qr.denom}</td>
                    <td>${escape(qr.desc)}</td>
                    <td><span class="badge badge-success">${escape(qr.status)}</span></td>
                  </tr>
                `).join('')}
              </tbody>
            </table>
          </div>
          <div class="replay-result">
            <strong>Analytics KPIs computed:</strong> Average resolution ${p.kpis[0].value} · Closure rate ${p.kpis[1].value} · Service events ${p.kpis[3].value} · Curated foreign-key integrity: 0 orphan links.
          </div>
        </section>
      `;
    }

    if (p.id === 'NP03') {
      return `
        <section class="replay">
          <p class="eyebrow">AI assurance evaluation matrix</p>
          <h2>6-Case evidence-grounding evaluation</h2>
          <p>Every query is evaluated against synthetic ground truth documents. Abstention and human review are intentional safety outcomes when citations are missing, partial, or contradictory.</p>
          <div class="table-wrapper">
            <table class="data-table">
              <thead><tr><th>Case ID</th><th>Scenario / Query</th><th>Required evidence</th><th>Assurance outcome</th><th>Review decision</th><th>Reason</th></tr></thead>
              <tbody>
                ${p.cases.map(c => `
                  <tr>
                    <td><strong>${escape(c.id)}</strong></td>
                    <td>${escape(c.query)}</td>
                    <td><code>${escape(c.required_ids)}</code></td>
                    <td><span class="badge ${c.outcome === 'SUPPORTED' ? 'badge-success' : c.outcome === 'ABSTAIN' ? 'badge-danger' : 'badge-warning'}">${escape(c.outcome)}</span></td>
                    <td>${escape(c.reviewer)}</td>
                    <td style="font-size: 0.82rem;">${escape(c.reason)}</td>
                  </tr>
                `).join('')}
              </tbody>
            </table>
          </div>
          <div class="replay-result">
            <strong>Assurance summary:</strong> 2 SUPPORTED · 3 HUMAN_REVIEW_REQUIRED · 1 ABSTAIN · False support: 0 cases. Replay digest verified: <code>${p.replay_digest}</code>.
          </div>
        </section>
      `;
    }

    if (p.id === 'NP04') {
      return `
        <section class="replay">
          <p class="eyebrow">Architecture decision sensitivity replay</p>
          <h2>Requirements fit-gap &amp; assumption simulator</h2>
          <p>Three alternatives were evaluated across 18 requirements (54 fit-gap evaluations). Select an assumption below to replay how the recommendation responds dynamically.</p>
          <div class="interactive-controls">
            <button type="button" data-assumption="Baseline" class="active-control">Baseline</button>
            <button type="button" data-assumption="ASM-002">ASM-002 (WAN Degrades)</button>
            <button type="button" data-assumption="ASM-005">ASM-005 (CAPEX Cut)</button>
          </div>
          <div id="assumption-result" class="replay-result">
            <strong>Selected recommendation:</strong> ${escape(p.assumptions.Baseline.selected)}<br>
            <span style="color: var(--muted); font-size: 0.9rem;">${escape(p.assumptions.Baseline.desc)}</span>
          </div>
          <h3 style="margin: 1.2rem 0 0.5rem; font-size: 1rem; color: var(--text-bright);">Compared alternatives overview</h3>
          <div class="table-wrapper">
            <table class="data-table">
              <thead><tr><th>Option</th><th>Architecture summary</th><th>CAPEX envelope</th><th>Operational autonomy</th></tr></thead>
              <tbody>
                ${p.options.map(opt => `
                  <tr>
                    <td><strong>${escape(opt.id)}</strong> (${escape(opt.name)})</td>
                    <td>${escape(opt.summary)}</td>
                    <td><code>${escape(opt.capex)}</code></td>
                    <td>${escape(opt.autonomy)}</td>
                  </tr>
                `).join('')}
              </tbody>
            </table>
          </div>
        </section>
      `;
    }
    return '';
  };

  const openProject = id => {
    const p = byId[id];
    const r = reasoning[id];
    if (!p || !r) return;

    detail.innerHTML = `
      <div class="dialog-header">
        <div>
          <p class="eyebrow">${escape(p.id)} · ${escape(p.domain)}</p>
          <h1 id="dialog-title" style="margin: 0.1rem 0 0.4rem; font-size: 1.8rem; color: var(--text-bright);">${escape(p.name)}</h1>
          <p class="lead" style="margin: 0; font-size: 1.05rem;">${escape(p.problem)}</p>
        </div>
        <button class="dialog-close" type="button" aria-label="Close project review">×</button>
      </div>

      <section class="facts-panel">
        <p class="eyebrow">Executive context</p>
        <h2>What happened &amp; why it matters</h2>
        <p><strong>Demonstrated:</strong> ${escape(p.result)}</p>
        <p><strong>Why it matters:</strong> ${escape(p.why)}</p>
        <p class="context-limit"><strong>Boundary:</strong> ${escape(p.limit)}</p>
      </section>

      <section class="failure-panel">
        <p class="eyebrow" style="color: var(--warning);">Failure handling &amp; edge case behavior</p>
        <h2>Controlled failure &amp; degraded operation</h2>
        <p>${escape(p.failure_behavior)}</p>
      </section>

      ${renderExplorerMarkup(p)}

      <section class="reasoning-panel">
        <p class="eyebrow">Evidence → Reasoning → Conclusion</p>
        <h2>Why this conclusion follows</h2>
        <dl>
          <dt>Observation</dt><dd>${escape(r.observation)}</dd>
          <dt>Evidence</dt><dd>${escape(r.evidence)}</dd>
          <dt>Interpretation</dt><dd>${escape(r.interpretation)}</dd>
          <dt>Conclusion</dt><dd>${escape(r.conclusion)}</dd>
          <dt>What could change</dt><dd>${escape(r.change)}</dd>
          <dt>What it does NOT prove</dt><dd>${escape(r.boundary)}</dd>
        </dl>
      </section>

      <section class="evidence-panel">
        <p class="eyebrow">Professional synthesis</p>
        <h2>Engineering takeaway</h2>
        <p>${escape(r.takeaway)}</p>
        <details>
          <summary>Technical reviewer specifications &amp; test suite</summary>
          <p>${escape(r.technical)}</p>
          <dl>
            <dt>Validated commit</dt><dd><code>${escape(p.commit)}</code></dd>
            <dt>Canonical run ID</dt><dd><code>${escape(p.run)}</code></dd>
            <dt>Test suite summary</dt><dd><span class="badge badge-success">${escape(p.test_summary)}</span></dd>
            <dt>Deterministic replay</dt><dd><span class="badge badge-success">PASS</span></dd>
          </dl>
          <div class="table-wrapper">
            <table class="data-table">
              <thead><tr><th>Test category</th><th>Tests</th><th>File</th></tr></thead>
              <tbody>
                ${p.test_categories.map(tc => `<tr><td>${escape(tc.category)}</td><td>${tc.count}</td><td><code>${escape(tc.file)}</code></td></tr>`).join('')}
              </tbody>
            </table>
          </div>
        </details>
        <div class="card-actions" style="margin-top: 1.2rem;">
          <a href="${p.repo}" target="_blank" rel="noopener noreferrer">View project repository on GitHub ↗</a>
        </div>
      </section>
    `;

    dialog.showModal();

    // Dialog close button
    const closeBtn = detail.querySelector('.dialog-close');
    if (closeBtn) closeBtn.addEventListener('click', () => dialog.close());

    // NP04 interactive assumption controls
    if (p.id === 'NP04') {
      const controls = detail.querySelectorAll('[data-assumption]');
      const resultBox = detail.querySelector('#assumption-result');
      controls.forEach(btn => btn.addEventListener('click', () => {
        controls.forEach(b => b.classList.remove('active-control'));
        btn.classList.add('active-control');
        const key = btn.dataset.assumption;
        const item = p.assumptions[key];
        if (resultBox && item) {
          resultBox.innerHTML = `
            <strong>Selected recommendation:</strong> ${escape(item.selected)}<br>
            <span style="color: var(--muted); font-size: 0.9rem;">${escape(item.desc)}</span>
          `;
        }
      }));
    }
  };

  // Open dialog on button click
  document.addEventListener('click', event => {
    const btn = event.target.closest('button[data-project]');
    if (btn) openProject(btn.dataset.project);
  });

  // Close dialog on backdrop click
  if (dialog) {
    dialog.addEventListener('click', event => {
      if (event.target === dialog) dialog.close();
    });
  }
})();
