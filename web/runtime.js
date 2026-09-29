// Dedicated worker: never import this file as a document script.
// The original Java algorithms, including their threads, live in this realm.
const send = message => self.postMessage({scope: 'theoretical-racing', ...message});
// This build's engine identity and its jar, named after it: stamped into the
// published copy by web/scripts/engine_identity.py. A page of one deploy thus
// never loads another deploy's jar from a cache under the same URL (review,
// 2026-09-29).
const ENGINE_BUILD = '__ENGINE_BUILD__';
const ENGINE_JAR = '__ENGINE_JAR__';
const describe = async error => {
  try { return String((await error?.getMessage?.()) ?? error?.message ?? error); }
  catch { return 'The Java engine failed'; }
};
self.addEventListener('unhandledrejection', event => {
  event.preventDefault();
  describe(event.reason).then(fatal => send({fatal}));
});
(async () => {
  if (ENGINE_BUILD.startsWith('__') || ENGINE_JAR.startsWith('__'))
    throw new Error('This worker is an unbuilt source file. Build the site with web/build.sh.');
  const jar = new URL('./' + ENGINE_JAR, self.location.href);
  send({status: 'Checking the game download…'});
  const probe = await fetch(jar, {headers: {Range: 'bytes=0-0'}});
  await probe.body?.cancel();
  // A page cached from an earlier deploy names a jar the site no longer has.
  if (probe.status === 404) throw new Error('This page belongs to an earlier version of the site. Reload the page to race.');
  if (probe.status !== 206) throw new Error('The web host must support HTTP byte-range requests. For local play, use python3 web/serve.py.');
  send({status: 'Downloading the Java runtime…'});
  importScripts('https://cjrtnc.leaningtech.com/4.3/loader.js');
  send({status: 'Starting Java in a background worker…'});
  await cheerpjInit({
    version: 17, status: 'none',
    overrideDocumentBase: new URL('./', self.location.href).href,
    // The engine's map caches persist in IndexedDB; the bridge prunes them.
    javaProperties: ['java.awt.headless=true', 'user.home=/files', 'tr.pruneReachCache=true'],
    preloadProgress: (done, total) => send({progress: {
      phase: 'Loading runtime resources', done, total, unit: 'resources', kind: 'runtime'
    }}),
    natives: {
      // Read-only telemetry. Never call back into a referee, change a score,
      // interrupt a search or return a value used in game decisions.
      Java_tr_browser_Progress_report: (_lib, phase, done, total, pass, stage, stages, complete, cached) => {
        send({progress: {phase, done, total, pass, stage, stages, complete, cached, kind: 'preparation', unit: total > 0 ? 'scan' : 'states explored'}});
      }
    }
  });
  send({status: 'Loading the original racing engine…'});
  const library = await cheerpjRunLibrary(`/app${jar.pathname}`);
  const Bridge = await library.tr.logic.BrowserBridge;
  const bridge = await new Bridge();
  // The jar's own identity must match (a jar too old to report one does not):
  // refuse before the first race, not midway through.
  let built = null;
  try { built = String(await bridge.build()); } catch { /* a jar without build() */ }
  if (built !== ENGINE_BUILD)
    throw new Error('This page and its game engine come from different versions of the site. Reload the page to race.');
  const allowed = new Set(['create', 'tick', 'click', 'ok', 'undo', 'preview', 'move', 'snapshot', 'readiness', 'log']);
  let queue = Promise.resolve();
  self.addEventListener('message', ({data: message}) => {
    if (!message || message.scope !== 'theoretical-racing' || !Number.isSafeInteger(message.id) || message.id <= 0) return;
    queue = queue.then(async () => {
      try {
        if (!allowed.has(message.method) || !Array.isArray(message.args)) throw new Error('Invalid engine request');
        const raw = await bridge[message.method](...message.args);
        send({id: message.id, result: message.method === 'log' ? raw : JSON.parse(raw)});
      } catch (error) { send({id: message.id, error: await describe(error)}); }
    });
  });
  send({ready: true});
})().catch(async error => send({fatal: await describe(error)}));
