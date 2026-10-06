// Keep keyboard review inside the explicit Confirm/Cancel dialog.
(() => {
  let opened = false;
  let previousFocus = null;
  let reviewKey = '';
  const sync = () => {
    const modal = document.getElementById('w-modal');
    if (!modal) return;
    const visible = getComputedStyle(modal).display !== 'none';
    const preview = modal.querySelector('.before-after');
    const nextKey = preview ? preview.innerText : '';
    if (visible && nextKey && nextKey !== reviewKey) {
      modal.querySelector('.review-dialog').scrollTop = 0;
    }
    reviewKey = visible ? nextKey : '';
    if (visible === opened) return;
    opened = visible;
    document.body.style.overflow = visible ? 'hidden' : '';
    for (const sibling of modal.parentElement.children) {
      if (sibling !== modal) sibling.inert = visible;
    }
    if (visible) {
      previousFocus = document.activeElement;
      document.getElementById('w-modal-title')?.focus();
    } else if (previousFocus?.isConnected) previousFocus.focus();
  };
  new MutationObserver(sync).observe(document.documentElement, {childList: true, subtree: true, attributes: true, attributeFilter: ['style']});
  // Native <details> toggles do not publish Dash prop changes themselves.
  // Notify Dash so expensive check tables can be loaded only on expansion.
  document.addEventListener('toggle', event => {
    if (event.target.id === 'w-review-extra' && window.dash_clientside?.set_props) {
      window.dash_clientside.set_props('w-review-extra', {open: event.target.open});
    }
  }, true);
  document.addEventListener('keydown', event => {
    if (!opened || event.key !== 'Tab') return;
    const modal = document.getElementById('w-modal');
    const items = [...modal.querySelectorAll('button, input, select, textarea, summary, [tabindex="0"]')]
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
