// This realm owns the JVM; the visible application owns rendering and controls.
const send = message => parent.postMessage({scope: 'theoretical-racing', ...message}, location.origin);
const describe = async error => {
  try { return String((await error?.getMessage?.()) ?? error?.message ?? error); }
  catch { return 'The Java engine failed'; }
};
try {
  send({status: 'Loading the Java runtime…'});
  await new Promise((resolve, reject) => {
    const script = document.createElement('script');
    script.src = 'https://cjrtnc.leaningtech.com/4.3/loader.js';
    script.onload = resolve;
    script.onerror = () => reject(new Error('Cannot download CheerpJ. An internet connection is required.'));
    document.head.append(script);
  });
  await cheerpjInit({version: 17, status: 'none', javaProperties: ['java.awt.headless=true', 'user.home=/files']});
  send({status: 'Loading the original racing engine…'});
  const jar = new URL('./racing.jar', location.href);
  const library = await cheerpjRunLibrary(`/app${jar.pathname}`);
  const Bridge = await library.tr.logic.BrowserBridge;
  const bridge = await new Bridge();
  const allowed = new Set(['create', 'tick', 'click', 'ok', 'undo', 'preview', 'move', 'snapshot', 'log']);
  let queue = Promise.resolve();
  addEventListener('message', event => {
    if (event.source !== parent || event.origin !== location.origin) return;
    const message = event.data;
    if (!message || message.scope !== 'theoretical-racing' || !Number.isSafeInteger(message.id)) return;
    queue = queue.then(async () => {
      try {
        if (!allowed.has(message.method) || !Array.isArray(message.args)) throw new Error('Invalid engine request');
        const raw = await bridge[message.method](...message.args);
        const result = message.method === 'log' ? raw : JSON.parse(raw);
        send({id: message.id, result});
      } catch (error) { send({id: message.id, error: await describe(error)}); }
    });
  });
  send({ready: true});
} catch (error) { send({fatal: await describe(error)}); }
