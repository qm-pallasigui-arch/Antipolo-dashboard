/* Presentation only: accessible native table sorting and password visibility. */
document.addEventListener('click', function (event) {
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
