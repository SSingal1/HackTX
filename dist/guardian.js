'use strict';

/* ==========================================================================
   STATE & DATA FIXTURES
   ========================================================================== */

const profiles = {
  alex: {
    name: 'Alex Morgan',
    initials: 'AM',
    label: 'Alex · no coverage',
    coverage: 0,
    cash: 7000,
    reserve: 2000
  },
  covered: {
    name: 'Jordan Lee',
    initials: 'JL',
    label: 'Jordan · covered repair',
    coverage: 1000,
    cash: 7000,
    reserve: 2000
  },
  limited: {
    name: 'Sam Rivera',
    initials: 'SR',
    label: 'Sam · limited cash',
    coverage: 0,
    cash: 2800,
    reserve: 2000
  }
};

let state = {
  profile: 'alex',
  miles: 12000,
  repair: 1800,
  reserve: 2000,
  discount: false,
  filter: 'all',
  sort: 'distance'
};

try {
  const saved = JSON.parse(localStorage.getItem('guardian-state') || 'null');
  if (saved && profiles[saved.profile]) {
    state = { ...state, ...saved };
  }
} catch {}

const allowedTabs = ['overview', 'maintenance', 'local', 'compare', 'plan'];
let currentTab = allowedTabs.includes(location.hash.slice(1))
  ? location.hash.slice(1)
  : 'overview';

const services = [
  {
    id: 'brakes',
    name: 'Brake pads & rotor service',
    short: 'Brake pads & rotors',
    detail: 'A written demo estimate for front brake pads and rotors. Have a qualified technician verify the scope and whether the work is needed.',
    timing: 'Confirmed estimate · Review with provider',
    status: 'due',
    cost: 1800,
    ico: 'brake',
    badge: 'Estimate ready'
  },
  {
    id: 'oil',
    name: 'Oil & filter service',
    short: 'Oil & filter service',
    detail: 'A routine maintenance allowance in the demo plan. Actual interval and price depend on your vehicle and service history.',
    timing: 'Planned allowance · In the next 3 months',
    status: 'due',
    cost: 90,
    ico: 'oil',
    badge: 'Planned'
  },
  {
    id: 'tires',
    name: 'Tire rotation & inspection',
    short: 'Tire rotation & inspection',
    detail: 'A routine allowance for tire rotation and inspection. This does not predict tire condition or establish safety.',
    timing: 'Planned allowance · In the next 6 months',
    status: 'due',
    cost: 60,
    ico: 'tire',
    badge: 'Planned'
  },
  {
    id: 'inspection',
    name: 'Remaining routine maintenance',
    short: 'Other routine maintenance',
    detail: 'An editable planning allowance for other routine service over 12 months. It is not a diagnosis or a model-specific service schedule.',
    timing: 'Annual allowance · Scope to verify',
    status: 'due',
    cost: 450,
    ico: 'tool',
    badge: 'Allowance'
  },
  {
    id: 'battery',
    name: 'Battery inspection',
    short: 'Battery inspection',
    detail: 'A completed synthetic service record. This item is excluded from upcoming maintenance costs.',
    timing: 'Completed · September 12, 2026',
    status: 'completed',
    cost: 0,
    ico: 'check',
    badge: 'Completed'
  }
];

const offers = [
  {
    id: 'north',
    name: 'North Loop Service Center',
    distance: 3.2,
    rating: '4.7',
    count: 218,
    price: 1750,
    offer: '$50 off a brake service',
    type: 'brakes',
    desc: 'Illustrative local provider. Verify scope, taxes, eligibility and final price directly.',
    terms: 'Demo promotion: $50 off the $1,800 brake estimate. Excludes taxes already included in this fixture. Cannot combine with the simulated coverage benefit. This is not a real business offer.'
  },
  {
    id: 'cedar',
    name: 'Cedar Park Auto Care',
    distance: 8.6,
    rating: '4.8',
    count: 164,
    price: 85,
    offer: 'Oil & filter service from $85',
    type: 'oil',
    desc: 'Illustrative local provider. Oil type, vehicle eligibility and additional fees need verification.',
    terms: 'Demo price lead for an oil and filter service. Does not reduce the brake estimate and is not automatically applied to the comparison. Not a real quote.'
  },
  {
    id: 'south',
    name: 'South Austin Tire & Service',
    distance: 11.4,
    rating: '4.6',
    count: 306,
    price: 45,
    offer: 'Tire rotation from $45',
    type: 'tires',
    desc: 'Illustrative local provider. Final service scope and vehicle compatibility require verification.',
    terms: 'Demo price lead for a tire rotation. Does not establish tire condition or replace a professional inspection. Not applied to the brake estimate. Not a real quote.'
  }
];

/* ==========================================================================
   HELPER & CALCULATION FUNCTIONS
   ========================================================================== */

function persist() {
  try {
    localStorage.setItem('guardian-state', JSON.stringify(state));
  } catch {
    toast('Browser storage is unavailable. Changes remain in this session.');
  }
}

function profile() {
  return profiles[state.profile];
}

function calc() {
  const p = profile();
  const coverage = Math.min(p.coverage, state.repair);
  const discount = state.discount && coverage === 0 ? Math.min(50, state.repair) : 0;
  const oop = Math.max(0, state.repair - coverage - discount);
  
  const fuelKeep = (state.miles / 30) * 3.5;
  const fuelReplace = (state.miles / 50) * 3.5;
  
  const keep = oop + 600 + fuelKeep;
  const replace = 2000 + 350 * 12 + 300 + fuelReplace;
  
  const keepCash = p.cash - oop;
  const replaceCash = p.cash - 2000;
  
  const keepOK = keepCash >= state.reserve;
  const replaceOK = replaceCash >= state.reserve;

  return {
    coverage,
    discount,
    oop,
    fuelKeep,
    fuelReplace,
    keep,
    replace,
    difference: replace - keep,
    keepCash,
    replaceCash,
    keepOK,
    replaceOK
  };
}

function getPlans() {
  try {
    return JSON.parse(localStorage.getItem('guardian-plans') || '[]');
  } catch {
    return [];
  }
}

function profileSelect() {
  return `
    <label class="profile-picker">
      ${icon('user')} Switch synthetic profile
      <select id="profile-select" aria-label="Select synthetic customer profile">
        ${Object.entries(profiles)
          .map(
            ([id, p]) =>
              `<option value="${id}" ${state.profile === id ? 'selected' : ''}>${p.label}</option>`
          )
          .join('')}
      </select>
    </label>
  `;
}

function recommendation(c = calc()) {
  if (!c.keepOK && !c.replaceOK) {
    return {
      title: 'Let’s verify costs before choosing a path.',
      text: `The repair and the replacement both leave less than your ${money(state.reserve)} reserve. Ask for a written second estimate and verify payment arrangements with the provider. No affordable winner is established.`,
      warning: true
    };
  }
  if (!c.keepOK) {
    return {
      title: 'The repair needs a closer affordability check.',
      text: `The repair would leave ${money(c.keepCash)} in available cash, below your ${money(state.reserve)} reserve. Review the estimate and your constraints before committing. A more expensive upgrade is not automatically a better choice.`,
      warning: true
    };
  }
  if (c.difference >= 0) {
    return {
      title: 'Keeping your Camry looks better for near-term cash flow.',
      text: `Under these assumptions, servicing costs ${money(c.difference)} less in cash over 12 months. Your ${money(c.oop)} repair leaves ${money(c.keepCash)} available, above your ${money(state.reserve)} reserve. This is a cash-flow comparison, not total economic savings.`,
      warning: false
    };
  }
  return {
    title: 'Compare the replacement quote more closely.',
    text: `The replacement uses ${money(-c.difference)} less cash in this scenario. Verify trade value, the financing term and ending equity before treating it as the lower-cost choice.`,
    warning: false
  };
}

/* ==========================================================================
   VIEW RENDERERS
   ========================================================================== */

function overview() {
  const c = calc();
  const p = profile();
  const r = recommendation(c);

  return `
    <div class="overview-top">
      <section class="card vehicle-card" aria-label="Your Toyota">
        <div class="eyebrow">YOUR TOYOTA</div>
        <h2>2020 Camry LE</h2>
        <p class="vehicle-sub">Silver · 2.5L 4-cylinder · Austin, TX</p>
        <span class="badge green">${icon('check')} Paid off</span>
        <img class="vehicle-img" src="assets/vehicle.svg" alt="Silver sedan illustration">
        <dl class="vehicle-stats">
          <div><dt>Current mileage</dt><dd>78,450 mi</dd></div>
          <div><dt>Monthly driving</dt><dd>${Math.round(state.miles / 12).toLocaleString()} mi</dd></div>
          <div><dt>Loan balance</dt><dd>$0</dd></div>
        </dl>
        ${profileSelect()}
      </section>

      <section class="card health-card">
        <div class="card-heading">
          <h2>Your service snapshot</h2>
          ${icon('shield')}
        </div>
        <div class="health-score">
          <div class="score-ring">
            <div>4<span style="font-size:11px;color:#959c9f;margin-top:5px">/5</span></div>
          </div>
          <div>
            <h3>One decision to make.</h3>
            <p>Review your brake estimate.<br>Keep routine care on track.</p>
          </div>
        </div>
        <div class="health-item">
          <span><i class="small-dot green-text"></i> Service history</span>
          <strong>Up to date</strong>
        </div>
        <div class="health-item">
          <span><i class="small-dot amber-text"></i> Repair estimate</span>
          <strong class="amber-text">Needs review</strong>
        </div>
        <p style="font-size:8px;margin-top:10px">Demo checklist completion, not a mechanical health score.</p>
      </section>
    </div>

    <div class="summary-grid">
      <section class="card summary-card">
        <div class="summary-top"><span>12-month service outlook</span>${icon('calendar')}</div>
        <div class="summary-number">${money(c.oop + 600)}</div>
        <div class="summary-foot">Repair + routine allowances</div>
      </section>

      <section class="card summary-card">
        <div class="summary-top"><span>Potential repair coverage</span>${icon('shield')}</div>
        <div class="summary-number">${money(c.coverage)}</div>
        <div class="summary-foot ${c.coverage ? 'good' : ''}">
          ${c.coverage ? 'Simulated benefit applied' : 'No coverage in this demo profile'}
        </div>
      </section>

      <section class="card summary-card">
        <div class="summary-top"><span>Keep vs. upgrade difference</span>${icon('trend')}</div>
        <div class="summary-number">${money(Math.abs(c.difference))}</div>
        <div class="summary-foot good">
          ${c.difference >= 0 ? 'Less cash to keep' : 'Less cash to replace'} over 12 months
        </div>
      </section>
    </div>

    <div class="main-columns">
      <section class="card service-card">
        <div class="card-heading">
          <h2>Coming up for your Camry</h2>
          <span class="badge">3 highlighted items</span>
        </div>
        ${services
          .slice(0, 3)
          .map(
            (s) => `
          <div class="service-row">
            <span class="service-icon">${icon(s.ico)}</span>
            <div class="service-name">
              <h3>${s.short}</h3>
              <p>${s.timing}</p>
            </div>
            <div class="service-end">
              <strong>${money(s.id === 'brakes' ? state.repair : s.cost)}</strong>
              <span>${s.badge}</span>
            </div>
          </div>`
          )
          .join('')}
        <div class="card-bottom">
          <small>Based on synthetic records and allowances</small>
          <button class="text-link" data-tab="maintenance" style="font-size:10px">
            View all ${icon('arrow')}
          </button>
        </div>
      </section>

      <section class="card insight-card">
        <div class="insight-top">
          <span class="spark">${icon('spark')}</span>
          <h2>Your Guardian insight</h2>
          <span class="badge">Demo</span>
        </div>
        <h3>${r.title}</h3>
        <p>
          ${
            c.keepOK
              ? `You’ve paid off your Camry. Your current repair estimate is ${money(state.repair)}, and your monthly driving is ${Math.round(state.miles / 12).toLocaleString()} miles. Let’s compare the real trade-offs.`
              : r.text
          }
        </p>
        <div class="insight-reason">
          ${icon(c.keepOK ? 'check' : 'info')} 
          ${c.keepOK ? 'Your reserve remains protected' : 'Your cash reserve needs attention'}
        </div>
        <button class="btn full" data-tab="compare">
          See my comparison ${icon('arrow')}
        </button>
        <div class="personal-note">
          Personalized to your demo loan, service estimate, driving and reserve. Explanations are simulated, not live Gemini output.
        </div>
      </section>
    </div>

    <section class="offer-section">
      <div class="section-title">
        <h2>A little closer. A little less.</h2>
        <button class="text-link" data-tab="local">View local offers ${icon('arrow')}</button>
      </div>
      <div class="offer-grid">
        ${offers
          .map(
            (o, i) => `
          <article class="card offer-card">
            <div class="offer-label">
              <span class="offer-category">${['BRAKE SERVICE', 'ROUTINE MAINTENANCE', 'TIRES & WHEELS'][i]}</span>
              ${icon('tag')}
            </div>
            <div class="offer-discount">${['$50 off', 'From $85', 'From $45'][i]}</div>
            <h3>${['Brake pads & rotor service', 'Oil & filter service', 'Tire rotation'][i]}</h3>
            <p>${o.name} · Demo provider</p>
            <span class="distance">${icon('pin')} ${o.distance} miles away · Austin area</span>
            <button class="text-link" data-offer="${o.id}">See demo offer ${icon('arrow')}</button>
          </article>`
          )
          .join('')}
      </div>
      <p class="offers-footnote">Illustrative offers and providers. Not retrieved live. Eligibility and final pricing require verification.</p>
    </section>
  `;
}

function maintenance() {
  const list = services.filter((x) => state.filter === 'all' || x.status === state.filter);

  return `
    <div class="view-header">
      <div>
        <h2>A clearer view of your service needs.</h2>
        <p>Confirmed estimates, planned allowances and work already done.</p>
      </div>
      <div class="chip-row">
        ${[
          ['all', 'All items'],
          ['due', 'Upcoming'],
          ['completed', 'Completed']
        ]
          .map(
            ([v, t]) => `
          <button class="chip ${state.filter === v ? 'active' : ''}" data-filter="${v}">${t}</button>`
          )
          .join('')}
      </div>
    </div>

    <div class="maintenance-layout">
      <section class="card">
        ${list
          .map(
            (s) => `
          <article class="big-service-row">
            <span class="service-icon">${icon(s.ico)}</span>
            <div>
              <h3>${s.name}</h3>
              <p>${s.timing}</p>
              <button class="text-link" data-service="${s.id}" style="font-size:10px">
                View details ${icon('arrow')}
              </button>
            </div>
            <div style="text-align:right">
              <strong>${s.status === 'completed' ? 'Completed' : money(s.id === 'brakes' ? state.repair : s.cost)}</strong>
              <div style="margin-top:9px">
                <span class="badge ${s.status === 'completed' ? 'green' : ''}">${s.badge}</span>
              </div>
            </div>
          </article>`
          )
          .join('')}
      </section>

      <aside>
        <section class="card timeline">
          <div class="card-heading">
            <h2>Your 12-month outlook</h2>
            ${icon('calendar')}
          </div>
          <div class="timeline-item">
            <small>NOW · CONFIRMED ESTIMATE</small>
            <h3>Review your brake service</h3>
            <p>${money(state.repair)} before any applicable demo benefit. Verify the work and final quote.</p>
          </div>
          <div class="timeline-item">
            <small>NEXT 3 MONTHS · PLANNED</small>
            <h3>Routine oil & filter service</h3>
            <p>$90 planning allowance. Timing requires vehicle-specific confirmation.</p>
          </div>
          <div class="timeline-item">
            <small>NEXT 6 MONTHS · PLANNED</small>
            <h3>Tire rotation & inspection</h3>
            <p>$60 planning allowance. No condition or safety prediction.</p>
          </div>
          <div class="timeline-item">
            <small>REMAINDER OF YEAR</small>
            <h3>Other routine care</h3>
            <p>$450 reserve for other service. Keep actual estimates separate.</p>
          </div>
        </section>

        <div class="evidence-banner" style="margin-top:15px">
          ${icon('info')} This is a planning view, not a diagnosis or Toyota maintenance schedule.
        </div>
        <button class="btn full" data-tab="local">
          Explore service options ${icon('arrow')}
        </button>
      </aside>
    </div>
  `;
}

function localView() {
  const c = calc();
  const sorted = [...offers].sort((a, b) =>
    state.sort === 'price' ? a.price - b.price : a.distance - b.distance
  );

  return `
    <div class="view-header">
      <div>
        <h2>Find the right care, closer to home.</h2>
        <p>Illustrative service options in Austin, Texas.</p>
      </div>
      <label class="muted" style="font-size:10px">
        Sort by 
        <select id="offer-sort" style="padding:7px;border:1px solid #ddd;border-radius:4px;margin-left:5px;font-size:10px">
          <option value="distance" ${state.sort === 'distance' ? 'selected' : ''}>Distance</option>
          <option value="price" ${state.sort === 'price' ? 'selected' : ''}>Listed demo price</option>
        </select>
      </label>
    </div>

    <div class="evidence-banner">
      ${icon('info')} Demo evidence: these providers, ratings and offers are illustrative. No live SerpApi search has been performed. Prices cover different service types and are not directly comparable.
    </div>

    <div class="providers-list">
      ${sorted
        .map(
          (o) => `
        <article class="card provider">
          <div class="provider-art">${icon('building')}</div>
          <span class="badge" style="align-self:start;margin-bottom:11px">Demo provider · Authorization unverified</span>
          <h3>${o.name}</h3>
          <p>★ ${o.rating} <span style="color:#aaa">(${o.count} simulated reviews)</span> · ${o.distance} mi</p>
          <div class="provider-price">${money(o.price)}</div>
          <p>${o.type === 'brakes' ? 'Illustrative brake price after $50 discount' : 'Illustrative starting price'}</p>
          <div class="provider-offer">${o.offer}</div>
          <button class="btn secondary" data-offer="${o.id}">View offer & terms ${icon('arrow')}</button>
        </article>`
        )
        .join('')}
    </div>

    <section class="card coverage-panel">
      <div class="card-heading">
        <h2>What could you pay for the brake service?</h2>
        <button class="text-link" data-action="coverage" style="font-size:10px">Understand coverage ${icon('arrow')}</button>
      </div>
      <p class="muted" style="font-size:11px">A transparent breakdown for ${profile().name.split(' ')[0]}’s demo profile. Taxes are included in this fixture.</p>
      
      <div class="waterfall">
        <div class="waterfall-step">
          <small>Written estimate</small>
          <strong>${money(state.repair)}</strong>
          <p>Synthetic provider estimate</p>
        </div>
        <div class="waterfall-step">
          <small>Applicable offer</small>
          <strong>−${money(c.discount)}</strong>
          <p>${c.coverage ? 'Not stacked with coverage' : state.discount ? 'Demo $50 benefit applied' : 'Optional demo offer below'}</p>
        </div>
        <div class="waterfall-step">
          <small>Simulated coverage</small>
          <strong>−${money(c.coverage)}</strong>
          <p>${c.coverage ? 'Explicit fixture, not a live claim' : 'No coverage in this profile'}</p>
        </div>
        <div class="waterfall-step final">
          <small>Estimated customer cost</small>
          <strong>${money(c.oop)}</strong>
          <p>Verify before committing</p>
        </div>
      </div>

      <label class="check-field">
        <input type="checkbox" id="apply-discount" ${state.discount ? 'checked' : ''} ${c.coverage ? 'disabled' : ''}>
        <span>Apply the illustrative $50 brake offer. It cannot be combined with the simulated coverage benefit. ${c.coverage ? 'Switch to Alex to explore this offer.' : ''}</span>
      </label>
      <button class="btn" data-tab="compare">Compare keeping vs. upgrading ${icon('arrow')}</button>
    </section>
  `;
}

function compare() {
  const c = calc();
  const r = recommendation(c);

  return `
    <div class="view-header">
      <div>
        <h2>Your next move, with the numbers.</h2>
        <p>A 12-month cash-flow comparison personalized to your demo profile.</p>
      </div>
      <button class="btn secondary small" data-action="assumptions">${icon('info')} Assumptions</button>
    </div>

    <div class="compare-top">
      <section class="card compare-card ${c.keepOK && c.difference >= 0 ? 'recommended' : ''}">
        <span class="eyebrow" style="font-size:9px;color:#858d92">KEEP & SERVICE</span>
        <span class="badge ${c.keepOK ? 'green' : 'red'}">
          ${icon(c.keepOK ? 'check' : 'info')} ${c.keepOK ? 'Within upfront reserve' : 'Below cash reserve'}
        </span>
        <h3>Your 2020 Camry LE</h3>
        <img src="assets/vehicle.svg" alt="Your current silver sedan illustration">
        <div class="price-label">Estimated 12-month cash outflow</div>
        <div class="compare-price">${money(c.keep)} <small>/ year</small></div>
        <div class="sub-cost">${money(c.keep / 12)} monthly equivalent · includes one-time repair</div>
        <ul class="cost-list">
          <li><span>Existing loan payments</span><strong>$0</strong></li>
          <li><span>Brake service after benefits</span><strong>${money(c.oop)}</strong></li>
          <li><span>Other routine maintenance</span><strong>$600</strong></li>
          <li><span>Fuel at 30 mpg</span><strong>${money(c.fuelKeep)}</strong></li>
          <li><span>Cash remaining after repair</span><strong>${money(c.keepCash)}</strong></li>
        </ul>
      </section>

      <section class="card compare-card">
        <span class="eyebrow" style="font-size:9px;color:#858d92">EXPLORE AN UPGRADE</span>
        <span class="badge ${c.replaceOK ? '' : 'red'}">
          ${c.replaceOK ? 'Synthetic financing' : 'Below cash reserve'}
        </span>
        <h3>2023 Corolla Hybrid LE</h3>
        <img src="assets/vehicle.svg" style="filter:brightness(.75) sepia(.15)" alt="Illustration of a possible replacement sedan">
        <div class="price-label">Estimated 12-month cash outflow</div>
        <div class="compare-price">${money(c.replace)} <small>/ year</small></div>
        <div class="sub-cost">${money(c.replace / 12)} monthly equivalent · includes cash due</div>
        <ul class="cost-list">
          <li><span>Cash due at purchase</span><strong>$2,000</strong></li>
          <li><span>Loan payments · $350 × 12</span><strong>$4,200</strong></li>
          <li><span>Routine maintenance</span><strong>$300</strong></li>
          <li><span>Fuel at 50 mpg</span><strong>${money(c.fuelReplace)}</strong></li>
          <li><span>Cash remaining after purchase</span><strong>${money(c.replaceCash)}</strong></li>
        </ul>
      </section>
    </div>

    <section class="card controls-panel">
      <div class="control">
        <label for="miles-range">
          Annual driving <span class="control-value" id="miles-value">${state.miles.toLocaleString()} mi</span>
        </label>
        <input type="range" id="miles-range" min="6000" max="30000" step="1000" value="${state.miles}">
        <small>Changes fuel costs on both paths.</small>
      </div>

      <div class="control">
        <label for="repair-range">
          Brake estimate <span class="control-value" id="repair-value">${money(state.repair)}</span>
        </label>
        <input type="range" id="repair-range" min="500" max="4500" step="50" value="${state.repair}">
        <small>Confirmed demo estimate before benefits.</small>
      </div>

      <div class="control">
        <label for="reserve-range">
          Cash to protect <span class="control-value" id="reserve-value">${money(state.reserve)}</span>
        </label>
        <input type="range" id="reserve-range" min="500" max="6000" step="100" value="${state.reserve}">
        <small>Your minimum cash reserve after upfront costs.</small>
      </div>
    </section>

    <div id="comparison-result" class="result-banner ${r.warning ? 'warning' : ''}">
      <span class="check-circle">${r.warning ? '!' : '✓'}</span>
      <div>
        <h3>${r.title}</h3>
        <p>${r.text}</p>
      </div>
    </div>

    <div style="display:flex;gap:12px;margin-top:20px;align-items:center;flex-wrap:wrap">
      <button class="btn" data-tab="plan">Make my next move ${icon('arrow')}</button>
      <button class="btn secondary" data-tab="local">Review service options</button>
      <span style="font-size:9px;color:#8e959b">Ending vehicle values are unknown. No total-cost winner is established.</span>
    </div>
  `;
}

function plan() {
  const c = calc();
  const r = recommendation(c);
  const plans = getPlans();

  return `
    <div class="view-header">
      <div>
        <h2>A clear next step for your Toyota.</h2>
        <p>Turn your comparison into a practical, saved service plan.</p>
      </div>
      <button class="btn secondary small" id="export-plan">${icon('download')} Export plan</button>
    </div>

    <div class="plan-grid">
      <section class="card card-pad">
        <span class="badge ${r.warning ? 'red' : 'green'}">
          ${r.warning ? 'Verify affordability' : 'Recommended next step'}
        </span>
        <h2 style="font-size:21px;line-height:1.5;margin:15px 0 10px">
          ${r.warning ? 'Get a second written estimate.' : 'Verify the repair. Keep your options clear.'}
        </h2>
        <p class="muted" style="font-size:12px">${r.text}</p>

        <div class="plan-step">
          <span class="step-number">1</span>
          <div>
            <h3>Confirm the brake-service scope</h3>
            <p>Ask which components need work, whether taxes are included and how long the estimate is valid. Have safety questions answered by a qualified technician.</p>
          </div>
        </div>

        <div class="plan-step">
          <span class="step-number">2</span>
          <div>
            <h3>${c.coverage ? 'Verify the coverage terms' : 'Ask about applicable local offers'}</h3>
            <p>
              ${
                c.coverage
                  ? `Your demo fixture provides ${money(c.coverage)}. In a real workflow, verify the covered item, deductible, limit and approval before counting on this benefit.`
                  : 'The illustrative $50 offer cannot be combined with the coverage fixture. Ask for a complete written quote before using any promotion.'
              }
            </p>
          </div>
        </div>

        <div class="plan-step">
          <span class="step-number">3</span>
          <div>
            <h3>Revisit if the written quote changes</h3>
            <p>Review this comparison if the estimate changes by $250 or more, your driving changes, or your cash needs shift. No background reminder is scheduled.</p>
          </div>
        </div>

        <label class="check-field">
          <input id="plan-consent" type="checkbox">
          <span>I understand this is a simulated inquiry. Saving does not contact a provider, submit a claim or book an appointment.</span>
        </label>
        <button id="save-plan" class="btn full" disabled>${icon('save')} Save my demo service inquiry</button>
      </section>

      <aside>
        <section class="card card-pad">
          <div class="card-heading">
            <h2>Your plan snapshot</h2>
            ${icon('file')}
          </div>
          <ul class="cost-list">
            <li><span>Demo customer</span><strong>${profile().name}</strong></li>
            <li><span>Brake service cost</span><strong>${money(c.oop)}</strong></li>
            <li><span>12-month keep cash outflow</span><strong>${money(c.keep)}</strong></li>
            <li><span>Protected reserve</span><strong>${money(state.reserve)}</strong></li>
          </ul>
          <div class="integration-note">
            Saved locally in this browser. A production version would persist the scenario and inquiry through the Snowflake SQL API.
          </div>
        </section>

        <section class="card card-pad" style="margin-top:18px">
          <div class="card-heading">
            <h2>Saved demo inquiries</h2>
            <span class="badge">${plans.length}</span>
          </div>
          ${
            plans.length
              ? plans
                  .slice(0, 4)
                  .map(
                    (x) => `
                <div class="saved-plan">
                  <strong>${escapeHTML(x.name)} · Service review</strong>
                  <p>${new Date(x.createdAt).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })} · ${money(x.cost)} customer cost</p>
                  <p>Simulated inquiry · No provider contacted</p>
                </div>`
                  )
                  .join('')
              : `<div class="empty-state">${icon('save')}<p>Your saved inquiries will appear here.</p></div>`
          }
        </section>
      </aside>
    </div>
  `;
}

/* ==========================================================================
   NAVIGATION & RENDER CONTROLLER
   ========================================================================== */

function render() {
  const funcs = { overview, maintenance, local: localView, compare, plan };
  document.getElementById('guardian-view').innerHTML = `<div class="content-view">${funcs[currentTab]()}</div>`;
  
  document.querySelectorAll('.tabnav button').forEach((b) => {
    b.classList.toggle('active', b.dataset.tab === currentTab);
    b.setAttribute('aria-current', b.dataset.tab === currentTab ? 'page' : 'false');
  });

  document.getElementById('customer-name').textContent = profile().name;
  document.getElementById('avatar').textContent = profile().initials;
  hydrateIcons();
}

function navigate(tab) {
  if (!allowedTabs.includes(tab)) return;
  if (location.hash.slice(1) !== tab) {
    location.hash = tab;
  } else {
    currentTab = tab;
    render();
  }
}

window.addEventListener('hashchange', () => {
  currentTab = allowedTabs.includes(location.hash.slice(1))
    ? location.hash.slice(1)
    : 'overview';
  render();
});

/* ==========================================================================
   MODAL & EXPORT HELPERS
   ========================================================================== */

function assumptions() {
  modal(
    'Comparison assumptions',
    `<p>This is an illustrative 12-month cash-flow comparison. It does not establish total cost of ownership or a market recommendation.</p>
    <dl>
      <div><dt>Current vehicle loan</dt><dd>Paid off · $0</dd></div>
      <div><dt>Gasoline price</dt><dd>$3.50 / gallon</dd></div>
      <div><dt>Assumed fuel efficiency</dt><dd>30 mpg / 50 mpg</dd></div>
      <div><dt>Replacement cash due</dt><dd>$2,000</dd></div>
      <div><dt>Replacement financing</dt><dd>$350 / month · 60 months</dd></div>
      <div><dt>Illustrative APR</dt><dd>8.0% · No approval implied</dd></div>
      <div><dt>Insurance & registration</dt><dd>Assumed equal</dd></div>
      <div><dt>Terminal vehicle values</dt><dd>Unknown</dd></div>
    </dl>
    <p>The replacement payment is a synthetic quote, not a rate you qualify for. An illustrative principal of about $17,261 at 8% over 60 months produces this payment; the existing vehicle’s simulated trade credit and upfront cash are assumed reflected in the quote. Actual transaction terms require verification.</p>`
  );
}

function coverageModal() {
  const c = calc();
  modal(
    'Protection that’s specific to you',
    `<span class="badge">Synthetic coverage illustration</span>
    <p style="margin-top:14px">
      ${
        c.coverage
          ? `This demo profile has an explicit benefit fixture covering up to $1,000 of the confirmed brake repair, with no deductible. The applied benefit is ${money(c.coverage)}.`
          : 'This demo profile has no applicable repair coverage. It does not represent your real protection plans.'
      }
    </p>
    <ul>
      <li>Coverage is not inferred from account tenure or vehicle age.</li>
      <li>The $50 demo special cannot stack with the coverage fixture.</li>
      <li>Real covered items, exclusions and claims require plan-specific verification.</li>
    </ul>
    <p>No live policy, warranty or claim check has been performed.</p>`
  );
}

function offerModal(id) {
  const o = offers.find((x) => x.id === id);
  if (!o) return;

  modal(
    o.offer,
    `<span class="badge">Illustrative offer · Not live search</span>
    <p style="margin-top:15px"><strong>${o.name}</strong><br>Austin area · ${o.distance} simulated miles away</p>
    <p style="margin-top:12px">${o.terms}</p>
    <dl>
      <div><dt>Evidence source</dt><dd>Synthetic demo fixture</dd></div>
      <div><dt>Provider authorization</dt><dd>Unverified</dd></div>
      <div><dt>Quote status</dt><dd>Needs verification</dd></div>
    </dl>
    ${
      o.id === 'north'
        ? `<button class="btn" id="apply-offer-modal" ${profile().coverage ? 'disabled' : ''}>${profile().coverage ? 'Cannot stack with current coverage' : 'Apply $50 demo offer'} ${icon('arrow')}</button>`
        : `<a class="btn secondary" href="https://www.google.com/maps/search/Toyota+service+Austin+TX" target="_blank" rel="noopener">Search real service providers ${icon('external')}</a>`
    }
    <p style="font-size:10px;margin-top:13px">External search opens Google Maps; it is not a SerpApi integration.</p>`
  );
}

function exportPlan() {
  const c = calc();
  const data = {
    product: 'Toyota TCO & Smart Service Guardian',
    mode: 'synthetic-demo',
    customer: profile().name,
    vehicle: '2020 Camry LE',
    createdAt: new Date().toISOString(),
    inputs: {
      annualMiles: state.miles,
      repairEstimate: state.repair,
      reserve: state.reserve,
      coverage: c.coverage,
      discount: c.discount
    },
    cashflow: {
      repairCustomerCost: c.oop,
      keep12Months: c.keep,
      replace12Months: c.replace
    },
    recommendation: recommendation(c),
    notice: 'No provider contacted. No real quote, claim or booking. Cash-flow comparison only.'
  };

  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'toyota-guardian-demo-plan.json';
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  toast('Demo plan exported as JSON.');
}

/* ==========================================================================
   GLOBAL EVENT LISTENERS
   ========================================================================== */

document.addEventListener('click', (e) => {
  const tab = e.target.closest('[data-tab]');
  if (tab) {
    e.preventDefault();
    navigate(tab.dataset.tab);
  }

  const filter = e.target.closest('[data-filter]');
  if (filter) {
    state.filter = filter.dataset.filter;
    persist();
    render();
  }

  const service = e.target.closest('[data-service]');
  if (service) {
    const s = services.find((x) => x.id === service.dataset.service);
    modal(
      s.name,
      `<span class="badge">Synthetic service record</span>
      <p style="margin-top:14px">${s.detail}</p>
      <dl>
        <div><dt>Status</dt><dd>${s.badge}</dd></div>
        <div><dt>Planning amount</dt><dd>${money(s.id === 'brakes' ? state.repair : s.cost)}</dd></div>
        <div><dt>Data source</dt><dd>Demo fixture</dd></div>
      </dl>
      <button class="btn" data-modal-go="local">Explore service options ${icon('arrow')}</button>`
    );
  }

  const offer = e.target.closest('[data-offer]');
  if (offer) offerModal(offer.dataset.offer);

  const act = e.target.closest('[data-action]');
  if (act?.dataset.action === 'coverage') coverageModal();
  if (act?.dataset.action === 'assumptions') assumptions();

  if (e.target.closest('[data-modal-go]')) {
    closeModal();
    navigate('local');
  }

  if (e.target.closest('#apply-offer-modal')) {
    state.discount = true;
    persist();
    closeModal();
    navigate('local');
    render();
    toast('Illustrative $50 offer applied. Verify terms before use.');
  }

  if (e.target.closest('#export-plan')) exportPlan();

  if (e.target.closest('#save-plan')) {
    const c = calc();
    const arr = getPlans();
    const entry = {
      id: Date.now(),
      name: profile().name,
      createdAt: new Date().toISOString(),
      cost: c.oop,
      profile: state.profile,
      inputs: { ...state },
      results: c,
      action: 'verify-service-estimate',
      simulated: true
    };

    try {
      localStorage.setItem('guardian-plans', JSON.stringify([entry, ...arr].slice(0, 20)));
      render();
      toast('Demo inquiry saved in this browser. No provider contacted.');
    } catch {
      toast('Could not save. Browser storage may be disabled.');
    }
  }
});

document.addEventListener('change', (e) => {
  if (e.target.id === 'profile-select') {
    state.profile = e.target.value;
    state.reserve = profile().reserve;
    state.discount = false;
    persist();
    render();
    toast(`Loaded ${profile().name.split(' ')[0]}’s synthetic profile.`);
  }

  if (e.target.id === 'offer-sort') {
    state.sort = e.target.value;
    persist();
    render();
  }

  if (e.target.id === 'apply-discount') {
    state.discount = e.target.checked;
    persist();
    render();
  }

  if (e.target.id === 'plan-consent') {
    document.getElementById('save-plan').disabled = !e.target.checked;
  }

  if (['miles-range', 'repair-range', 'reserve-range'].includes(e.target.id)) {
    persist();
    render();
  }
});

document.addEventListener('input', (e) => {
  const map = {
    'miles-range': 'miles',
    'repair-range': 'repair',
    'reserve-range': 'reserve'
  };

  if (map[e.target.id]) {
    state[map[e.target.id]] = Number(e.target.value);
    const c = calc();

    document.getElementById(e.target.id.replace('range', 'value')).textContent =
      e.target.id === 'miles-range'
        ? state.miles.toLocaleString() + ' mi'
        : money(Number(e.target.value));

    const r = recommendation(c);
    const banner = document.getElementById('comparison-result');
    banner.className = 'result-banner ' + (r.warning ? 'warning' : '');
    banner.innerHTML = `
      <span class="check-circle">${r.warning ? '!' : '✓'}</span>
      <div>
        <h3>${r.title}</h3>
        <p>${r.text}</p>
        <p style="margin-top:5px">Updated cash totals: keep ${money(c.keep)} · upgrade ${money(c.replace)}. Release the slider to refresh the full breakdown.</p>
      </div>
    `;
  }
});

/* ==========================================================================
   ASSISTANT CHAT PANEL (PART 2)
   ========================================================================== */

let assistantOpen = false;

function openAssistant() {
  assistantOpen = !assistantOpen;
  const root = document.getElementById('assistant-root');

  if (!assistantOpen) {
    root.innerHTML = '';
    return;
  }

  root.innerHTML = `
    <aside class="assistant-panel" aria-label="Demo Guardian assistant">
      <div class="assistant-head">
        <span class="spark">${icon('spark')}</span>
        <div>
          <h3>Your Guardian</h3>
          <p>Scripted demo · No live Gemini connection</p>
        </div>
        <button class="icon-btn" id="close-assistant" aria-label="Close assistant">${icon('close')}</button>
      </div>
      <div class="chat-log" id="chat-log" aria-live="polite">
        <div class="message">Hi ${profile().name.split(' ')[0]}. I can explain this demo’s costs or help change your annual mileage, repair estimate or cash reserve. What would you like to explore?</div>
      </div>
      <div class="chat-suggestions">
        <button data-chat="Why keep my Camry?">Why keep my Camry?</button>
        <button data-chat="What does my coverage mean?">Explain coverage</button>
        <button data-chat="Set annual mileage to 24000">Drive 24,000 mi/year</button>
      </div>
      <form class="chat-form" id="chat-form">
        <label for="chat-input" class="sr-only">Ask a demo question</label>
        <input id="chat-input" placeholder="Ask about your next move…" autocomplete="off" maxlength="400">
        <button aria-label="Send question">${icon('arrow')}</button>
      </form>
    </aside>
  `;

  document.getElementById('chat-input').focus();
}

function appendMessage(text, type = 'assistant') {
  const log = document.getElementById('chat-log');
  if (!log) return;

  const msg = document.createElement('div');
  msg.className = 'message ' + (type === 'user' ? 'user' : '');
  msg.textContent = text;
  log.appendChild(msg);
  log.scrollTop = log.scrollHeight;
}

function answerQuestion(q) {
  appendMessage(q, 'user');

  const txt = q.toLowerCase();
  const c = calc();
  let reply;

  const raw = txt.match(/\d[\d,]*/)?.[0];
  const n = raw ? Number(raw.replaceAll(',', '')) : NaN;
  let key, label, min, max;

  if (/mile|commut|driv/.test(txt) && Number.isFinite(n)) {
    key = 'miles';
    label = 'annual mileage';
    min = 6000;
    max = 30000;
  } else if (/reserve|protect|untouched/.test(txt) && Number.isFinite(n)) {
    key = 'reserve';
    label = 'cash reserve';
    min = 500;
    max = 6000;
  } else if (/repair|estimate/.test(txt) && Number.isFinite(n)) {
    key = 'repair';
    label = 'brake estimate';
    min = 500;
    max = 4500;
  }

  if (key) {
    if (n < min || n > max) {
      appendMessage(`This demo supports ${label} between ${min.toLocaleString()} and ${max.toLocaleString()}. Please choose a value in that range.`);
      return;
    }

    modal(
      'Confirm your scenario change',
      `<p>Set your ${label} to <strong>${key === 'miles' ? n.toLocaleString() + ' miles per year' : money(n)}</strong>? Both comparison paths will be recalculated. This changes only the demo.</p><button class="btn" id="confirm-chat-change">Confirm & recalculate ${icon('arrow')}</button>`
    );

    document.getElementById('confirm-chat-change').onclick = () => {
      state[key] = n;
      persist();
      closeModal();
      navigate('compare');
      render();
      appendMessage(`Updated your ${label}. ${recommendation().text}`);
    };
    return;
  }

  if (/coverage|protect|benefit/.test(txt)) {
    reply = c.coverage
      ? `Your synthetic fixture contributes ${money(c.coverage)} toward the ${money(state.repair)} brake estimate, leaving ${money(c.oop)} for you. It has no deductible in this demo and cannot stack with the $50 special. No real coverage or claim has been verified.`
      : 'This profile has no applicable coverage fixture. The repair stays in your cost estimate unless you apply the optional $50 demo offer. Switch to Jordan’s profile on Overview to see the explicit coverage example.';
  } else if (/fuel|gas|hybrid/.test(txt)) {
    reply = `At ${state.miles.toLocaleString()} miles a year and an assumed $3.50 per gallon, fuel is ${money(c.fuelKeep)} for your Camry at 30 mpg and ${money(c.fuelReplace)} for the replacement at 50 mpg. Acquisition and financing costs still matter.`;
  } else if (/book|appointment|schedule|contact/.test(txt)) {
    reply = 'This sandbox cannot book or contact a provider. Open My Next Move to save a simulated service inquiry and a checklist of questions. You can also export the demo plan.';
  } else if (/keep|upgrade|why|cost|replace|compare/.test(txt)) {
    reply = recommendation(c).text;
  } else if (/api|gemini|serp|snow/.test(txt)) {
    reply = 'This release uses scripted explanations, synthetic search results and browser-local storage. Live SerpApi, Gemini and Snowflake adapters are not connected. No API keys should be entered into this frontend.';
  } else {
    reply = 'I can explain keeping versus upgrading, fuel costs, coverage or next steps. Try “set annual mileage to 24000” or “set cash reserve to 3000” to update this demo after confirmation.';
  }

  setTimeout(() => appendMessage(reply), 250);
}

document.addEventListener('click', (e) => {
  if (e.target.closest('#assistant-toggle') || e.target.closest('#close-assistant')) {
    openAssistant();
  }
  const b = e.target.closest('[data-chat]');
  if (b) {
    answerQuestion(b.dataset.chat);
  }
});

document.addEventListener('submit', (e) => {
  if (e.target.id === 'chat-form') {
    e.preventDefault();
    const input = document.getElementById('chat-input');
    const q = input.value.trim();
    if (q) {
      input.value = '';
      answerQuestion(q);
    }
  }
});

/* ==========================================================================
   INITIAL RENDER
   ========================================================================== */

render();