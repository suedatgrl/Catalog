// Müşteri sayfası davranışları. Satır içi betik yok (CSP).

// ---- Fotoğraf akışı: her kartı bilinen oranına göre en kısa sütuna yerleştirir ----
const cols = () => (innerWidth >= 1100 ? 4 : innerWidth >= 700 ? 3 : 2);

function watchImages(root) {
  // Henüz yüklenmemiş fotoğraflar yumuşakça belirir; yüklenmiş olanlara dokunulmaz.
  root.querySelectorAll('img.fade').forEach((img) => {
    if (img.complete) return;
    img.classList.add('pending');
    const done = () => img.classList.remove('pending');
    img.addEventListener('load', done, { once: true });
    img.addEventListener('error', done, { once: true });
  });
}

function masonry(root) {
  const items = [...root.children];
  let columns = [], heights = [], count = 0;
  // Kartın göreli yüksekliği: fotoğraf (1/oran) + yazı bloğu
  const weight = (el) => 1 / (parseFloat(el.dataset.ratio) || 0.8) + 0.36;

  function place(el) {
    const i = heights.indexOf(Math.min(...heights));
    columns[i].appendChild(el);
    heights[i] += weight(el);
  }
  function build() {
    count = cols();
    columns = Array.from({ length: count }, () => {
      const c = document.createElement('div');
      c.className = 'col';
      return c;
    });
    heights = Array(count).fill(0);
    root.replaceChildren(...columns);
    root.classList.add('js');
    items.forEach(place);
  }
  build();
  addEventListener('resize', () => { if (cols() !== count) build(); });
  return {
    add(nodes) {
      nodes.forEach((n) => { items.push(n); place(n); });
    },
  };
}

const instances = new Map();
document.querySelectorAll('[data-masonry]').forEach((root) => {
  watchImages(root);
  instances.set(root, masonry(root));
});
watchImages(document);

// ---- "Daha fazla göster": sonraki sayfanın kartlarını sayfayı yenilemeden ekler ----
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
      const tpl = document.createElement('template');
      tpl.innerHTML = await res.text();
      const nodes = [...tpl.content.children];
      const grid = document.getElementById('grid');
      nodes.forEach((n) => watchImages(n));
      instances.get(grid).add(nodes);
      more.dataset.page = next;
      if (next >= Number(more.dataset.pages)) more.parentElement.remove();
      else { more.disabled = false; more.textContent = 'Daha fazla göster'; }
    } catch (e) {
      more.disabled = false;
      more.textContent = 'Yüklenemedi — tekrar deneyin';
    }
  });
}

// ---- Ürün galerisi: kaydırdıkça alttaki noktaları güncelle ----
const slides = document.getElementById('slides');
const dots = document.getElementById('dots');
if (slides && dots) {
  slides.addEventListener('scroll', () => {
    const i = Math.round(slides.scrollLeft / slides.clientWidth);
    [...dots.children].forEach((d, n) => d.classList.toggle('on', n === i));
  }, { passive: true });
}

// ---- Paylaş: telefonda paylaşım menüsü, yoksa bağlantıyı kopyala ----
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
