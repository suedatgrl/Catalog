// "Daha fazla göster": sonraki sayfanın kartlarını sayfayı yenilemeden ekler.
const more = document.getElementById('more');
if (more) {
  more.addEventListener('click', async () => {
    const next = Number(more.dataset.page) + 1;
    const url = new URL(location.href);
    url.searchParams.set('sayfa', next);
    more.disabled = true;
    more.textContent = 'Yükleniyor…';
    try {
      const res = await fetch(url, { headers: { 'X-Requested-With': 'fetch' } });
      if (!res.ok) throw new Error(res.status);
      document.getElementById('grid').insertAdjacentHTML('beforeend', await res.text());
      more.dataset.page = next;
      if (next >= Number(more.dataset.pages)) more.parentElement.remove();
      else { more.disabled = false; more.textContent = 'Daha fazla göster'; }
    } catch (e) {
      more.disabled = false;
      more.textContent = 'Yüklenemedi — tekrar deneyin';
    }
  });
}

// Ürün galerisi: kaydırdıkça alttaki noktaları güncelle.
const slides = document.getElementById('slides');
const dots = document.getElementById('dots');
if (slides && dots) {
  slides.addEventListener('scroll', () => {
    const i = Math.round(slides.scrollLeft / slides.clientWidth);
    [...dots.children].forEach((d, n) => d.classList.toggle('on', n === i));
  }, { passive: true });
}

// Paylaş: telefonda paylaşım menüsü, yoksa bağlantıyı kopyala.
const share = document.getElementById('share');
if (share) {
  share.addEventListener('click', async () => {
    const data = { title: share.dataset.title, url: share.dataset.url };
    try {
      if (navigator.share) await navigator.share(data);
      else {
        await navigator.clipboard.writeText(data.url);
        share.textContent = 'Bağlantı kopyalandı';
        setTimeout(() => (share.textContent = 'Paylaş'), 2000);
      }
    } catch (e) { /* kullanıcı vazgeçti */ }
  });
}
