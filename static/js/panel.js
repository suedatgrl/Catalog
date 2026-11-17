// Panel davranışları. Satır içi onclick/onsubmit yerine veri öznitelikleri kullanılır;
// böylece Content-Security-Policy satır içi betiğe izin vermek zorunda kalmaz.
//   data-confirm="Mesaj"   → buton/bağlantı/form göndermeden önce onay sorar
//   data-autosubmit        → seçim değişince formu gönderir
//   data-print             → tıklayınca yazdırma penceresini açar
document.addEventListener('click', (e) => {
  const el = e.target.closest('[data-confirm]');
  if (el && el.tagName !== 'FORM' && !confirm(el.dataset.confirm)) {
    e.preventDefault();
    return;
  }
  if (e.target.closest('[data-print]')) window.print();
});

document.addEventListener('submit', (e) => {
  const msg = e.target.dataset && e.target.dataset.confirm;
  if (msg && !confirm(msg)) e.preventDefault();
});

document.addEventListener('change', (e) => {
  if (e.target.matches('[data-autosubmit]')) e.target.form.submit();
});
