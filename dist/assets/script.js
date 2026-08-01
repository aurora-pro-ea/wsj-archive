(function () {
  const body = document.body;
  const theme = document.getElementById('theme-toggle');
  const search = document.getElementById('site-search');
  const panel = document.getElementById('search-panel');
  const results = document.getElementById('search-results');
  const meta = document.getElementById('search-meta');
  const progress = document.getElementById('reading-progress');
  let indexPromise;

  function loadIndex() {
    if (!indexPromise) indexPromise = fetch('/search-index.json').then(r => r.json());
    return indexPromise;
  }
  function renderResults(items, query) {
    if (!panel || !results || !meta) return;
    panel.hidden = !query;
    if (!query) return;
    meta.textContent = items.length ? `找到 ${items.length} 篇相关文章` : '没有找到匹配文章';
    results.innerHTML = items.slice(0, 30).map(item => `
      <a class="search-result" href="${item.url}">
        <small>${item.date} · ${item.year}年</small>
        <strong>${escapeHtml(item.title)}</strong>
        <span>${escapeHtml(item.excerpt)}</span>
      </a>`).join('');
  }
  function escapeHtml(value) { return String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
  if (search) {
    search.addEventListener('input', async () => {
      const query = search.value.trim().toLowerCase();
      if (query.length < 2) { renderResults([], ''); return; }
      const items = await loadIndex();
      const found = items.filter(item => `${item.title} ${item.search} ${item.date}`.toLowerCase().includes(query));
      renderResults(found, query);
    });
    search.addEventListener('keydown', event => { if (event.key === 'Escape') { search.value = ''; renderResults([], ''); search.blur(); } });
  }
  if (theme) {
    const saved = localStorage.getItem('wsj-theme');
    if (saved === 'dark') { body.classList.add('dark'); theme.textContent = '☀'; }
    theme.addEventListener('click', () => { body.classList.toggle('dark'); const dark = body.classList.contains('dark'); localStorage.setItem('wsj-theme', dark ? 'dark' : 'light'); theme.textContent = dark ? '☀' : '☾'; });
  }
  const menu = document.getElementById('menu-toggle');
  if (menu) menu.addEventListener('click', () => document.body.classList.toggle('menu-open'));
  function updateProgress() {
    if (!progress || document.body.classList.contains('no-reading-progress')) return;
    const scrollable = document.documentElement.scrollHeight - window.innerHeight;
    progress.style.width = `${scrollable > 0 ? Math.min(100, window.scrollY / scrollable * 100) : 0}%`;
  }
  window.addEventListener('scroll', updateProgress, {passive: true});
  updateProgress();
})();
