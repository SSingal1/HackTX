'use strict';

const iconPaths = {
  arrow: 'M4 10h12m-5-5 5 5-5 5',
  search: 'm14 14 4 4M16 9A7 7 0 1 1 2 9a7 7 0 0 1 14 0',
  user: 'M15 6a5 5 0 1 1-10 0 5 5 0 0 1 10 0ZM2 20v-2a8 8 0 0 1 16 0v2',
  menu: 'M3 5h14M3 10h14M3 15h14',
  grid: 'M2 2h6v6H2zM12 2h6v6h-6zM2 12h6v6H2zM12 12h6v6h-6z',
  card: 'M2 4h16v12H2zM2 8h16M5 12h3',
  file: 'M5 2h8l4 4v12H3V2h2m7 0v5h5M6 11h8M6 14h6',
  shield: 'm10 2 7 3v5c0 4-4 7-7 9-3-2-7-5-7-9V5zM7 10l2 2 4-4',
  guardian: 'm10 2 7 3v5c0 4-4 7-7 9-3-2-7-5-7-9V5zM6 11h3l2-4 2 6 2-2',
  tool: 'm12 3-3 3 3 3 3-3 2 1a6 6 0 0 1-7 6l-6 6-3-3 6-6a6 6 0 0 1 5-8z',
  pin: 'M16 8c0 5-6 10-6 10S4 13 4 8a6 6 0 0 1 12 0ZM12 8a2 2 0 1 1-4 0 2 2 0 0 1 4 0',
  headset: 'M3 11V9a7 7 0 0 1 14 0v6M3 10H1v6h4v-6H3Zm14 0h2v6h-4v-6h2Zm0 6v2h-6',
  lock: 'M5 9V6a5 5 0 0 1 10 0v3M3 9h14v10H3z',
  spark: 'm10 1 2.5 6.5L19 10l-6.5 2.5L10 19l-2.5-6.5L1 10l6.5-2.5z',
  car: 'm3 8 2-5h10l2 5M2 8h16v7H2zM4 15v3m12-3v3M5 11h1m8 0h1',
  calendar: 'M3 4h14v14H3zM3 8h14M6 2v4m8-4v4M6 11h2m3 0h2m-7 3h2',
  clock: 'M18 10a8 8 0 1 1-16 0 8 8 0 0 1 16 0ZM10 5v5l3 2',
  dollar: 'M10 1v18M15 5c-1-2-8-2-8 1 0 4 8 2 8 6 0 4-7 4-10 1',
  trend: 'm2 15 6-6 4 3 6-8m-5 0h5v5',
  check: 'm4 10 4 4 8-8',
  tag: 'M2 2h7l9 9-7 7-9-9zM6 6h.1',
  tire: 'M18 10a8 8 0 1 1-16 0 8 8 0 0 1 16 0ZM14 10a4 4 0 1 1-8 0 4 4 0 0 1 8 0',
  oil: 'm3 7 9-3 4 7-9 3zM6 5 4 2m13 9c-2 2-3 4-3 5a2 2 0 0 0 4 0c0-1-1-3-1-5',
  brake: 'M17 10a7 7 0 1 1-14 0 7 7 0 0 1 14 0ZM10 5v6m0 3h.1',
  info: 'M18 10a8 8 0 1 1-16 0 8 8 0 0 1 16 0ZM10 9v5m0-8h.1',
  close: 'm5 5 10 10M15 5 5 15',
  save: 'M3 2h12l3 3v13H2V2h1Zm3 0v6h8V2M6 18v-6h8v6',
  external: 'M11 2h7v7m0-7-9 9M8 3H2v15h15v-6',
  download: 'M10 2v11m-4-4 4 4 4-4M3 14v4h14v-4',
  building: 'M4 18V3h12v15M1 18h18M7 6h1m4 0h1M7 9h1m4 0h1M8 18v-5h4v5',
  fuel: 'M3 3h8v15H2V3h1Zm0 6h8m2-4 3 3v7c0 2 3 2 3 0V8l-3-3'
};

function icon(name) {
  return `<svg class="icon" viewBox="0 0 20 20" aria-hidden="true"><path d="${iconPaths[name] || iconPaths.info}"/></svg>`;
}

function hydrateIcons(root = document) {
  root.querySelectorAll('[data-icon]').forEach((el) => {
    const n = el.dataset.icon;
    delete el.dataset.icon;
    el.insertAdjacentHTML('afterbegin', icon(n));
  });
}

function money(value) {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0
  }).format(value);
}

function escapeHTML(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;'
  }[c]));
}

function brand() {
  return `<a class="brand" href="index.html" aria-label="Toyota Financial Services sandbox home"><svg class="brand-mark" viewBox="0 0 60 43" aria-hidden="true"><ellipse cx="30" cy="22" rx="26" ry="16"/><ellipse cx="30" cy="22" rx="10" ry="16"/><ellipse cx="30" cy="15" rx="20" ry="7"/></svg><div class="brand-type">TOYOTA<span>Financial Services</span></div></a>`;
}

document.getElementById('site-header').innerHTML = `
  <div class="demo-ribbon"><span class="demo-dot"></span><b>HACKATHON SANDBOX</b><span>Independent prototype · Synthetic data · No real account access</span></div>
  <header class="site-header">
    <div class="header-main">
      ${brand()}
      <nav class="header-nav" aria-label="Main navigation">
        <a href="index.html#account" data-nav="account">My Account</a>
        <a href="#protection" data-nav="protection">Voluntary Protection</a>
        <a href="#planning" data-nav="planning">Planning Tools</a>
        <a href="#financing" data-nav="financing">Explore Financing</a>
        <a href="#lease" data-nav="lease">End of Lease</a>
      </nav>
      <div class="header-tools">
        <button class="icon-btn" id="search-toggle" aria-label="Search sandbox">${icon('search')}</button>
        <a href="guardian.html" class="btn small dark">${icon('user')} Demo account</a>
        <button class="icon-btn mobile-menu" id="mobile-toggle" aria-label="Open navigation" aria-expanded="false">${icon('menu')}</button>
      </div>
    </div>
    <div id="nav-panel"></div>
  </header>
`;

const footerEl = document.getElementById('site-footer');
if (footerEl) {
  footerEl.innerHTML = `
    <footer class="footer">
      <div class="footer-grid">
        <div>
          ${brand()}
          <p style="margin-top:18px">Helping you move forward with confidence.</p>
        </div>
        <div>
          <h4>TFS Resources</h4>
          <a href="https://www.toyotafinancial.com/us/en/contact_us.html" target="_blank" rel="noopener">Contact Toyota Financial Services ↗</a>
          <a href="https://www.toyotafinancial.com/us/en/planning_tools/faq.html" target="_blank" rel="noopener">Official FAQs ↗</a>
          <a href="guardian.html">Smart Service Guardian</a>
        </div>
        <div>
          <h4>Explore Toyota</h4>
          <a href="https://www.toyota.com" target="_blank" rel="noopener">Toyota.com ↗</a>
          <a href="guardian.html#local">Explore demo service offers</a>
          <a href="guardian.html#compare">Compare ownership costs</a>
        </div>
        <div>
          <h4>About this sandbox</h4>
          <a href="#about" data-action="about">Prototype information</a>
          <a href="#privacy" data-action="privacy">Demo data & privacy</a>
          <a href="guardian.html#plan">My saved demo plan</a>
        </div>
      </div>
      <div class="footer-bottom">
        Independent hackathon prototype. Toyota and Toyota Financial Services trademarks belong to their respective owners. This sandbox is not affiliated with or endorsed by Toyota or TFS. It does not collect credentials, process payments, submit claims, or make bookings. Illustrative service data and financing are not offers.
      </div>
    </footer>
  `;
}

const navContents = {
  protection: ['Voluntary Protection', 'Vehicle service agreements', 'Prepaid maintenance', 'Tire & wheel protection'],
  planning: ['Planning Tools', 'Ownership cost comparison', 'My maintenance', 'Service discovery'],
  financing: ['Explore Financing', 'Keep vs. upgrade', 'Understand demo financing'],
  lease: ['End of Lease', 'Lease resources on Toyota Financial Services'],
  account: ['My Account', 'Open demo account', 'Smart Service Guardian']
};

let toastTimer;

function toast(msg) {
  const el = document.getElementById('toast-root');
  el.innerHTML = `<div class="toast" role="status">${escapeHTML(msg)}</div>`;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => (el.innerHTML = ''), 4000);
}

let modalPrevious;

function modal(title, content) {
  modalPrevious = document.activeElement;
  document.getElementById('overlay-root').innerHTML = `
    <div class="modal-backdrop">
      <section class="modal" role="dialog" aria-modal="true" aria-label="${escapeHTML(title)}">
        <div class="modal-head">
          <h2>${escapeHTML(title)}</h2>
          <button class="icon-btn" data-close-modal aria-label="Close dialog">${icon('close')}</button>
        </div>
        ${content}
      </section>
    </div>
  `;
  document.querySelector('[data-close-modal]').focus();
  document.body.style.overflow = 'hidden';
}

function closeModal() {
  document.getElementById('overlay-root').innerHTML = '';
  document.body.style.overflow = '';
  modalPrevious?.focus();
}

function commonAction(action) {
  if (action === 'about') {
    modal(
      'About this prototype',
      `<p>A two-page, TFS-inspired hackathon sandbox built with HTML, CSS and JavaScript. Smart Service Guardian demonstrates a personalized service dashboard, local offer discovery, cost comparisons and a saved next step.</p><div class="integration-note">SerpApi, Gemini and Snowflake are architectural integration targets. This release uses deterministic demo data and browser-local storage. No live API calls or approvals are represented.</div><a class="btn" href="guardian.html">Explore Guardian ${icon('arrow')}</a>`
    );
  } else if (action === 'privacy') {
    modal(
      'Your demo data',
      `<p>No real customer credentials or financial information are requested. Saved demo plans and profile settings stay in this browser. Do not enter private account details.</p><button class="btn secondary" id="clear-storage">Clear saved demo data</button>`
    );
  } else if (action === 'support') {
    modal(
      'How can we help?',
      `<p>This sandbox cannot access your real TFS account. For this demo, explore maintenance details or use the Guardian assistant to understand the illustrative calculations.</p><a class="btn secondary" href="https://www.toyotafinancial.com/us/en/contact_us.html" target="_blank" rel="noopener">Official TFS contact information ${icon('external')}</a>`
    );
  } else if (action === 'payments') {
    modal(
      'Demo account payments',
      `<p>Payments are outside this sandbox. No banking information is collected and no payment can be made.</p><a class="btn" href="guardian.html#compare">Explore ownership costs ${icon('arrow')}</a>`
    );
  } else if (action === 'account') {
    modal(
      'Alex’s demo account',
      `<p>This is a synthetic customer profile used for the hackathon. The 2020 Camry is paid off; remaining balance and monthly loan payment are both $0.</p><a class="btn" href="guardian.html">Open Smart Service Guardian ${icon('arrow')}</a>`
    );
  }
}

document.addEventListener('click', (e) => {
  const nav = e.target.closest('[data-nav]');
  if (nav) {
    e.preventDefault();
    const key = nav.dataset.nav;
    const data = navContents[key];
    document.getElementById('nav-panel').innerHTML = `
      <div class="menu-panel">
        <h3>${data[0]}</h3>
        ${data
          .slice(1)
          .map(
            (x, i) => `
          <a href="${
            key === 'lease'
              ? 'https://www.toyotafinancial.com/us/en/planning_tools/end_of_lease_options.html'
              : key === 'planning' && i === 1
              ? 'guardian.html#maintenance'
              : key === 'planning' && i === 2
              ? 'guardian.html#local'
              : 'guardian.html'
          }" ${key === 'lease' ? 'target="_blank" rel="noopener"' : ''}>${x} ↗</a>`
          )
          .join('')}
      </div>
    `;
    return;
  }

  if (e.target.closest('#mobile-toggle')) {
    const btn = document.getElementById('mobile-toggle');
    const open = btn.getAttribute('aria-expanded') === 'true';
    btn.setAttribute('aria-expanded', String(!open));
    document.getElementById('nav-panel').innerHTML = open
      ? ''
      : `<nav class="menu-panel">
          <a href="index.html">Home</a>
          <a href="guardian.html">My demo account</a>
          <a href="guardian.html#maintenance">Maintenance</a>
          <a href="guardian.html#local">Service offers</a>
          <a href="guardian.html#compare">Keep vs. upgrade</a>
        </nav>`;
    return;
  }

  if (e.target.closest('#search-toggle')) {
    const root = document.getElementById('nav-panel');
    root.innerHTML = `
      <div class="search-panel">
        <label for="site-search" class="sr-only">Search sandbox pages</label>
        <input id="site-search" placeholder="What can we help you with?">
        <div class="search-results">
          <a href="guardian.html">Smart Service Guardian →</a>
          <a href="guardian.html#maintenance">Maintenance and service history →</a>
          <a href="guardian.html#compare">Keep vs. upgrade comparison →</a>
        </div>
      </div>
    `;
    document.getElementById('site-search').focus();
    return;
  }

  if (e.target.closest('[data-close-modal]') || e.target.classList.contains('modal-backdrop')) {
    closeModal();
  }

  const action = e.target.closest('[data-action]');
  if (action && action.dataset.action !== 'coverage') {
    e.preventDefault();
    commonAction(action.dataset.action);
  }

  if (e.target.closest('#clear-storage')) {
    localStorage.removeItem('guardian-plans');
    localStorage.removeItem('guardian-state');
    closeModal();
    toast('Demo data cleared. Reloading your profile.');
    setTimeout(() => location.reload(), 600);
  }

  if (!e.target.closest('.site-header')) {
    document.getElementById('nav-panel').innerHTML = '';
  }
});

document.addEventListener('input', (e) => {
  if (e.target.id === 'site-search') {
    const q = e.target.value.toLowerCase();
    document.querySelectorAll('.search-results a').forEach(
      (a) => (a.hidden = !a.textContent.toLowerCase().includes(q))
    );
  }
});

document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    closeModal();
    document.getElementById('nav-panel').innerHTML = '';
  }
  if (e.key === 'Tab') {
    const box = document.querySelector('.modal');
    if (box) {
      const els = [...box.querySelectorAll('button,a[href],input,select,textarea')].filter(
        (x) => !x.disabled
      );
      if (e.shiftKey && document.activeElement === els[0]) {
        e.preventDefault();
        els.at(-1).focus();
      } else if (!e.shiftKey && document.activeElement === els.at(-1)) {
        e.preventDefault();
        els[0].focus();
      }
    }
  }
});

hydrateIcons();