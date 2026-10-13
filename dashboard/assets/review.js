// Keep keyboard review inside the explicit Confirm/Cancel dialog.
(() => {
  let opened = false;
  let previousFocus = null;
  let selectionAnchor = null;
  let pendingDestination = null;
  const sectionIds = ['w-step-worksheets', 'w-fact-panel', 'w-review-extra'];
  let observedNav = null;
  const measureNav = () => {
    const dialog = document.querySelector('.review-dialog');
    const nav = dialog?.querySelector('.review-section-nav');
    if (!nav || !dialog) return;
    const clearance = `${Math.ceil(nav.getBoundingClientRect().height) + 16}px`;
    if (dialog.style.getPropertyValue('--review-nav-clearance') !== clearance)
      dialog.style.setProperty('--review-nav-clearance', clearance);
  };
  const navObserver = new ResizeObserver(measureNav);
  const reveal = target => {
    for (let node = target; node; node = node.parentElement) {
      if (node.tagName === 'DETAILS') node.open = true;
    }
    measureNav();
    const focus = target.querySelector('summary, h3') || target;
    // Summaries retain their native keyboard tab stop.
    if (focus.tagName !== 'SUMMARY') focus.tabIndex = -1;
    focus.focus({preventScroll: true});
    target.scrollIntoView({block: 'start'});
  };
  const sync = () => {
    const modal = document.getElementById('w-modal');
    if (!modal) return;
    const visible = getComputedStyle(modal).display !== 'none';
    if (visible) {
      const nav = modal.querySelector('.review-section-nav');
      if (nav !== observedNav) {
        navObserver.disconnect();
        if (nav) navObserver.observe(nav);
        observedNav = nav;
      }
      const sourceLink = nav?.querySelector('[data-review-target="w-fact-panel"]');
      if (sourceLink) sourceLink.hidden = getComputedStyle(document.getElementById('w-fact-panel')).display === 'none';
      measureNav();
      if (!opened) {
        sectionIds.forEach((id, index) => { document.getElementById(id).open = index === 0; });
      }
    }
    if (visible && selectionAnchor) {
      const card = modal.querySelector(`[data-worksheet-index="${selectionAnchor.index}"]`);
      if (card && card.innerText !== selectionAnchor.text) {
        const anchor = selectionAnchor;
        selectionAnchor = null;
        requestAnimationFrame(() => {
          modal.querySelector('.review-dialog').scrollTop += card.getBoundingClientRect().top - anchor.top;
          card.querySelector(`input[value="${anchor.value}"]`)?.focus({preventScroll: true});
        });
      }
    }
    if (pendingDestination) {
      const target = document.getElementById(pendingDestination);
      if (target && target.getClientRects().length &&
          (pendingDestination !== 'w-fact-panel' || (visible && target.querySelector('#w-facts')?.children.length))) {
        pendingDestination = null;
        requestAnimationFrame(() => {
          reveal(target);
        });
      }
    }
    if (visible === opened) return;
    opened = visible;
    document.body.style.overflow = visible ? 'hidden' : '';
    for (const sibling of modal.parentElement.children) {
      if (sibling !== modal) sibling.inert = visible;
    }
    if (visible) {
      modal.querySelector('.review-dialog').scrollTop = 0;
      previousFocus = document.activeElement;
      document.getElementById('w-modal-title')?.focus();
    } else {
      selectionAnchor = null;
      if (previousFocus?.isConnected) previousFocus.focus();
    }
  };
  new MutationObserver(sync).observe(document.documentElement, {childList: true, subtree: true, attributes: true, attributeFilter: ['style']});
  document.addEventListener('change', event => {
    const choice = event.target.closest('.worksheet-choice input');
    if (!choice) return;
    const card = choice.closest('[data-worksheet-index]');
    selectionAnchor = {index: card.dataset.worksheetIndex, top: card.getBoundingClientRect().top,
                       text: card.innerText, value: choice.value};
  }, true);
  // Check summaries are prepared with the dataset, so expanding is local/instant.
  document.addEventListener('click', event => {
    const shortcut = event.target.closest('[data-app-action]');
    if (shortcut && window.dash_clientside?.set_props) {
      event.preventDefault();
      const source = shortcut.dataset.appAction === 'source';
      pendingDestination = source ? 'w-fact-panel' : 'w-upload';
      window.dash_clientside.set_props('w-page', {value: 'Data'});
      if (source) document.getElementById('w-edit-facts')?.click();
      sync();
      return;
    }
    const link = event.target.closest('[data-review-target]');
    if (!link) return;
    const target = document.getElementById(link.dataset.reviewTarget);
    if (!target) return;
    event.preventDefault();
    reveal(target);
  });
  document.addEventListener('keydown', event => {
    if (!opened || event.key !== 'Tab') return;
    const modal = document.getElementById('w-modal');
    const items = [...modal.querySelectorAll('button, input, select, textarea, summary, a[href], [tabindex="0"]')]
      .filter(el => !el.disabled && el.getClientRects().length);
    if (!items.length) return;
    const first = items[0], last = items[items.length - 1];
    if (event.shiftKey && (document.activeElement === first || document.activeElement.id === 'w-modal-title')) {
      event.preventDefault(); last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault(); first.focus();
    }
  });
})();
