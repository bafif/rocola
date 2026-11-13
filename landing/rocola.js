// The marquee fills the screen when the page opens and clears as the visitor scrolls: it shrinks, rises and fades
// while the bar at the top takes its place. The sections come in as they reach the screen. With reduced motion the
// page stays still and everything is visible from the start.
(() => {
  const root = document.documentElement;
  if (matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  root.classList.add('anima');

  const hero = document.querySelector('.hero');
  let pending = false;
  const measure = () => {
    pending = false;
    const run = Math.max(1, hero.offsetHeight - innerHeight);
    const p = Math.min(1, Math.max(0, scrollY / run));
    root.style.setProperty('--p', p.toFixed(4));
    root.classList.toggle('con-barra', p > 0.55);
  };
  addEventListener('scroll', () => {
    if (!pending) {
      pending = true;
      requestAnimationFrame(measure);
    }
  }, { passive: true });
  addEventListener('resize', measure);
  measure();

  const seen = new IntersectionObserver((entries) => {
    for (const entry of entries) {
      if (entry.isIntersecting) {
        entry.target.classList.add('visto');
        seen.unobserve(entry.target);
      }
    }
  }, { threshold: 0.12, rootMargin: '0px 0px -40px 0px' });
  document.querySelectorAll('.aparece').forEach((el) => seen.observe(el));
})();
