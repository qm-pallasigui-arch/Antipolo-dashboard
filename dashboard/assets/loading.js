// Tie the blocking confirmation screen to Dash's callback lifecycle.
// Other dataset operations retain their inline progress messages.
(() => {
  let confirming = false;
  let started = false;
  let previousFocus = null;
  document.addEventListener('click', event => {
    if (event.target.closest('#w-activate:not(:disabled)')) confirming = true;
  }, true);
  const sync = () => {
    const overlay = document.getElementById('w-applying');
    const dialog = document.querySelector('#w-modal .review-dialog');
    const progress = document.getElementById('w-review-progress');
    if (!overlay || !dialog || !progress) return;
    const running = Boolean(progress.textContent.trim());
    if (confirming && running && !started) {
      started = true;
      previousFocus = document.activeElement;
      overlay.hidden = false;
      overlay.tabIndex = -1;
      overlay.focus();
      dialog.inert = true;
      dialog.setAttribute('aria-busy', 'true');
    } else if (started && !running) {
      confirming = false;
      started = false;
      overlay.hidden = true;
      dialog.inert = false;
      dialog.removeAttribute('aria-busy');
      if (previousFocus?.isConnected && previousFocus.getClientRects().length) previousFocus.focus();
    }
  };
  new MutationObserver(sync).observe(document.documentElement, {childList: true, characterData: true, subtree: true});
  document.addEventListener('keydown', event => {
    if (started && event.key === 'Tab') {
      event.preventDefault();
      event.stopImmediatePropagation();
    }
  }, true);
})();
