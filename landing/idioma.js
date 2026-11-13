// Opens the page in the visitor's language: Spanish when any language their browser prefers is Spanish, English
// otherwise. Once they choose one with the link at the top, that one wins, in this browser only; nothing is sent
// anywhere. Search engines get each page as it is, so that both can be found.
(() => {
  const esta = document.documentElement.lang === 'en' ? 'en' : 'es';
  const otra = document.querySelector('link[rel="alternate"][hreflang]');
  if (!otra) return;
  const CLAVE = 'rocola-idioma';
  const leer = () => {
    try {
      return localStorage.getItem(CLAVE);
    } catch {
      return null;
    }
  };
  const guardar = (valor) => {
    try {
      localStorage.setItem(CLAVE, valor);
    } catch {
      // Private windows may refuse: coming from the other page still counts as a choice.
    }
  };
  // The link at the top is the selector: what it leads to is what the visitor chose.
  document.addEventListener('click', (evento) => {
    const enlace = evento.target.closest && evento.target.closest('a[hreflang]');
    if (enlace) guardar(enlace.getAttribute('hreflang'));
  });
  if (/bot|crawl|spider|slurp|preview/i.test(navigator.userAgent)) return;

  const direccion = (url) => url.origin + url.pathname.replace(/index\.html$/, '');
  const laOtra = new URL(otra.getAttribute('href'), location.href);
  let vieneDeLaOtra = false;
  try {
    vieneDeLaOtra = direccion(new URL(document.referrer)) === direccion(laOtra);
  } catch {
    // No page before this one.
  }
  const preferidos = navigator.languages && navigator.languages.length ? navigator.languages : [navigator.language || ''];
  const delNavegador = preferidos.some((idioma) => String(idioma).toLowerCase().split(/[-_]/)[0] === 'es') ? 'es' : 'en';
  const elegido = leer();
  // Each page goes to the other only for what this one is not, so the two never send the visitor back and forth.
  const quiere = elegido === 'es' || elegido === 'en' ? elegido : vieneDeLaOtra ? esta : delNavegador;
  if (quiere !== esta && otra.getAttribute('hreflang') === quiere) location.replace(laOtra.href + location.hash);
})();
