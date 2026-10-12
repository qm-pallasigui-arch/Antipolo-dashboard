// Dash tabs render as divs. Add keyboard access without changing callback values.
(() => {
  const sync = () => {
    const list = document.getElementById('w-page');
    if (!list) return;
    list.setAttribute('role', 'tablist');
    list.setAttribute('aria-label', 'Dashboard pages');
    for (const tab of list.querySelectorAll('.nav-tab')) {
      const selected = tab.classList.contains('nav-tab-selected');
      tab.setAttribute('role', 'tab');
      tab.setAttribute('aria-selected', String(selected));
      tab.tabIndex = selected ? 0 : -1;
    }
  };
  new MutationObserver(sync).observe(document.documentElement, {
    childList: true, subtree: true, attributes: true, attributeFilter: ['class']
  });
  document.addEventListener('keydown', event => {
    const tab = event.target.closest('#w-page .nav-tab');
    if (!tab) return;
    const tabs = [...document.querySelectorAll('#w-page .nav-tab')];
    let index = tabs.indexOf(tab);
    if (event.key === 'ArrowRight') index = (index + 1) % tabs.length;
    else if (event.key === 'ArrowLeft') index = (index + tabs.length - 1) % tabs.length;
    else if (event.key === 'Home') index = 0;
    else if (event.key === 'End') index = tabs.length - 1;
    else if (!['Enter', ' '].includes(event.key)) return;
    event.preventDefault();
    tabs[index].click();
    tabs[index].focus();
  });
  sync();
})();
