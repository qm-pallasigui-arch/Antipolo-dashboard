/* Progressive enhancement: sorting, password visibility and form feedback. */
document.addEventListener('click', function (event) {
  const signout = event.target.closest('.m-account-menu a[href="/logout"]');
  if (signout && !event.ctrlKey && !event.metaKey && !event.shiftKey && event.button === 0) {
    event.preventDefault();
    if (signout.getAttribute('aria-busy') === 'true') return;
    signout.setAttribute('aria-busy', 'true');
    signout.textContent = 'Signing out…';
    // Obtain the existing CSRF-protected form; GET itself never signs out.
    fetch('/logout', {credentials: 'same-origin'}).then(response => {
      if (!response.ok) throw new Error('Sign-out form unavailable');
      return response.text();
    }).then(text => {
      const page = new DOMParser().parseFromString(text, 'text/html');
      const token = page.querySelector('input[name=csrf]');
      if (!token) throw new Error('Sign-out form unavailable');
      const form = document.createElement('form');
      form.method = 'post'; form.action = '/logout'; form.hidden = true;
      form.appendChild(token); document.body.appendChild(form); form.submit();
    }).catch(() => window.location.assign('/logout'));
  }
  const button = event.target.closest('.m-sort-button');
  if (button) {
    const table = button.closest('table'), header = button.closest('th');
    const index = Number(button.dataset.column), ascending = header.getAttribute('aria-sort') !== 'ascending';
    const numeric = button.dataset.sortKind === 'number';
    const rows = Array.from(table.tBodies[0].rows);
    rows.sort((a, b) => {
      const av = a.cells[index].dataset.sortValue, bv = b.cells[index].dataset.sortValue;
      if (av === '') return bv === '' ? 0 : 1;
      if (bv === '') return -1;
      const order = numeric ? Number(av) - Number(bv) : av.localeCompare(bv);
      return ascending ? order : -order;
    });
    table.querySelectorAll('th').forEach(th => th.setAttribute('aria-sort', 'none'));
    header.setAttribute('aria-sort', ascending ? 'ascending' : 'descending');
    rows.forEach(row => table.tBodies[0].appendChild(row));
  }
  const toggle = event.target.closest('[data-password-toggle]');
  if (toggle) {
    const input = document.getElementById(toggle.dataset.passwordToggle);
    const reveal = input.type === 'password';
    input.type = reveal ? 'text' : 'password';
    toggle.textContent = reveal ? 'Hide password' : 'Show password';
    toggle.setAttribute('aria-pressed', String(reveal));
  }
});

document.addEventListener('change', function (event) {
  const form = event.target.closest('[data-dirty-form]');
  if (!form) return;
  const changed = Array.from(form.querySelectorAll('select')).some(select =>
    select.value !== Array.from(select.options).find(option => option.defaultSelected).value);
  form.querySelector('button').disabled = !changed;
});

document.addEventListener('submit', function (event) {
  const form = event.target.closest('[data-busy-form]');
  if (!form) return;
  if (form.dataset.submitting === 'true') {
    event.preventDefault();
    return;
  }
  form.dataset.submitting = 'true';
  form.setAttribute('aria-busy', 'true');
  const button = form.querySelector('button[type=submit]');
  button.dataset.originalLabel = button.textContent;
  button.textContent = button.dataset.busyLabel;
  button.disabled = true;
  form.querySelector('[data-form-status]').textContent = button.dataset.busyLabel;
});

window.addEventListener('pageshow', function () {
  document.querySelectorAll('[data-busy-form]').forEach(form => {
    delete form.dataset.submitting;
    form.removeAttribute('aria-busy');
    const button = form.querySelector('button[type=submit]');
    if (button.dataset.originalLabel) button.textContent = button.dataset.originalLabel;
    button.disabled = false;
    form.querySelector('[data-form-status]').textContent = '';
  });
});

['keydown', 'keyup'].forEach(type => document.addEventListener(type, function (event) {
  if (event.target.id === 'login-password') {
    document.getElementById('caps-lock').hidden = !event.getModifierState('CapsLock');
  }
}));
document.addEventListener('focusout', function (event) {
  if (event.target.id === 'login-password') document.getElementById('caps-lock').hidden = true;
});

// Dash DataTable exposes sorting as a clickable span; make that existing control
// keyboard operable without replacing its native sorting or data model.
function labelTableSortControls() {
  document.querySelectorAll('.m-paged-table .column-header--sort').forEach(control => {
    const header = control.closest('th');
    const label = header.querySelector('.column-header-name').textContent;
    control.setAttribute('role', 'button');
    control.setAttribute('tabindex', '0');
    control.setAttribute('aria-label', 'Sort by ' + label);
    const icon = control.querySelector('svg');
    const direction = icon && icon.getAttribute('data-icon');
    header.setAttribute('aria-sort', direction === 'sort-up' ? 'ascending' : direction === 'sort-down' ? 'descending' : 'none');
  });
}
document.addEventListener('keydown', function (event) {
  const control = event.target.closest('.m-paged-table .column-header--sort');
  if (control && (event.key === 'Enter' || event.key === ' ')) {
    event.preventDefault();
    control.click();
  }
});
function watchTableSortControls() {
  labelTableSortControls();
  new MutationObserver(labelTableSortControls).observe(document.body, {childList: true, subtree: true, attributes: true, attributeFilter: ['data-icon']});
}
if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', watchTableSortControls);
else watchTableSortControls();

// Shared navigation enhancement for Dash and Flask; links also work without JS.
function monthlyMenu(open) {
  const shell = document.querySelector('.m-shell');
  if (!shell) return;
  shell.classList.toggle('m-menu-open', open);
  const toggle = document.getElementById('m-menu-toggle');
  toggle.setAttribute('aria-expanded', String(open));
  shell.querySelector('.m-workspace').inert = open;
  if (open) document.getElementById('m-menu-close').focus();
  else toggle.focus();
  window.dispatchEvent(new Event('resize'));
}
document.addEventListener('click', event => {
  if (event.target.closest('#m-menu-toggle')) monthlyMenu(true);
  if (event.target.closest('#m-menu-close')) monthlyMenu(false);
  const link = event.target.closest('.m-sidebar-link, #m-notifications-link');
  if (link && document.getElementById('m-page') && !event.ctrlKey && !event.metaKey && !event.shiftKey && event.button === 0) {
    event.preventDefault();
    if (document.querySelector('.m-menu-open')) monthlyMenu(false);
    window.history.pushState({}, '', link.href);
    window.dispatchEvent(new PopStateEvent('popstate'));
  }
});
document.addEventListener('keydown', event => {
  const shell = document.querySelector('.m-menu-open');
  if (!shell) return;
  if (event.key === 'Escape') { event.preventDefault(); monthlyMenu(false); }
  if (event.key === 'Tab') {
    const items = shell.querySelectorAll('#m-sidebar button, #m-sidebar a');
    const first = items[0], last = items[items.length - 1];
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
    else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
  }
});
function monthlyCurrentPage() {
  const page = new URLSearchParams(location.search).get('module') || 'Dashboard';
  document.querySelectorAll('.m-sidebar-link, #m-notifications-link').forEach(link => {
    const active = location.pathname === '/' && new URL(link.href).searchParams.get('module') === page;
    if (active) link.setAttribute('aria-current', 'page'); else link.removeAttribute('aria-current');
  });
}
window.addEventListener('popstate', monthlyCurrentPage);
// Focus the new heading once navigation has rendered both heading and content.
// Polls, filters and downloads do not request focus changes.
let monthlyPendingPage = null;
window.addEventListener('popstate', () => {
  monthlyPendingPage = new URLSearchParams(location.search).get('module') || 'Dashboard';
  monthlyNavigationFocus();
});
function monthlyNavigationFocus() {
  if (!monthlyPendingPage) return;
  const heading = document.querySelector('#m-heading h1');
  const content = document.querySelector('#m-content [data-page]');
  if (heading && content && heading.textContent === monthlyPendingPage && content.dataset.page === monthlyPendingPage) {
    monthlyPendingPage = null;
    heading.focus();
  }
}
new MutationObserver(monthlyNavigationFocus).observe(document.body, {childList:true, subtree:true});
// Do not interrupt someone who starts another task while navigation is loading.
document.addEventListener('pointerdown', event => {
  if (event.target.closest('main input, main select, main textarea, main button')) monthlyPendingPage = null;
});
window.addEventListener('resize', () => {
  if (innerWidth >= 1200 && document.querySelector('.m-menu-open')) monthlyMenu(false);
});
new MutationObserver(monthlyCurrentPage).observe(document.body, {childList:true, subtree:true});

// Stick notification filters only when the full panel fits the viewport.
// CSS supplies the spacing and responsive breakpoint; no inline styling.
let monthlyFilterPanel;
function monthlyFilterFits() {
  if (!monthlyFilterPanel) return;
  const gap = parseFloat(getComputedStyle(document.querySelector('.monthly-app')).getPropertyValue('--space-4'));
  monthlyFilterPanel.classList.toggle('m-sticky-fits', monthlyFilterPanel.offsetHeight > 0 && monthlyFilterPanel.offsetHeight + gap * 2 < innerHeight);
}
const monthlyFilterResize = new ResizeObserver(monthlyFilterFits);
function monthlyWatchFilters() {
  const panel = document.getElementById('m-notification-controls');
  if (panel && panel !== monthlyFilterPanel) {
    monthlyFilterResize.disconnect();
    monthlyFilterPanel = panel;
    monthlyFilterResize.observe(panel);
  }
}
new MutationObserver(monthlyWatchFilters).observe(document.body, {childList:true, subtree:true});
window.addEventListener('resize', monthlyFilterFits);
monthlyWatchFilters();
