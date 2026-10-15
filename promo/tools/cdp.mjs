// 极简 CDP 客户端：用 Node 内置 WebSocket 驱动无头 Chrome
export class CDP {
  constructor(ws) { this.ws = ws; this.id = 0; this.pending = new Map(); this.handlers = new Map();
    ws.addEventListener('message', ev => {
      const m = JSON.parse(ev.data);
      if (m.id && this.pending.has(m.id)) { const { res, rej } = this.pending.get(m.id); this.pending.delete(m.id);
        m.error ? rej(new Error(JSON.stringify(m.error))) : res(m.result); }
      else if (m.method && this.handlers.has(m.method)) this.handlers.get(m.method)(m.params);
    });
  }
  // 无头 Chrome 可能同时暴露 about:blank 与真实页面；且 9222 常被其它程序占用，
  // 因此这里按 URL 精确选中场景页，并用独立端口 9333。
  static async attach(port = 9333, match = t => t.type === 'page' && /pelican-cyclist\/index\.html/.test(t.url)) {
    let targets;
    for (let i = 0; i < 60; i++) {
      try { targets = await (await fetch(`http://127.0.0.1:${port}/json`)).json(); if (targets.some(match)) break; } catch {}
      await new Promise(r => setTimeout(r, 500));
    }
    const t = targets.find(match);
    if (!t) throw new Error('no target');
    const ws = new WebSocket(t.webSocketDebuggerUrl);
    await new Promise((res, rej) => { ws.addEventListener('open', res); ws.addEventListener('error', rej); });
    const c = new CDP(ws);
    await c.send('Page.enable'); await c.send('Runtime.enable');
    return c;
  }
  on(method, fn) { this.handlers.set(method, fn); return this; }
  once(method, timeout = 30000) {
    return new Promise((res, rej) => {
      const t = setTimeout(() => { this.handlers.delete(method); rej(new Error('wait ' + method + ' timeout')); }, timeout);
      this.handlers.set(method, p => { clearTimeout(t); this.handlers.delete(method); res(p); });
    });
  }
  send(method, params = {}) {
    const id = ++this.id;
    return new Promise((res, rej) => { this.pending.set(id, { res, rej });
      this.ws.send(JSON.stringify({ id, method, params }));
      setTimeout(() => { if (this.pending.has(id)) { this.pending.delete(id); rej(new Error('timeout ' + method)); } }, 60000); });
  }
  async evalJS(expression) {
    const r = await this.send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true });
    if (r.exceptionDetails) throw new Error(r.exceptionDetails.text + ' ' + JSON.stringify(r.exceptionDetails.exception?.description || ''));
    return r.result.value;
  }
  async shot(path, quality = 88) {
    const r = await this.send('Page.captureScreenshot', { format: 'jpeg', quality, captureBeyondViewport: false });
    const { writeFileSync } = await import('node:fs');
    writeFileSync(path, Buffer.from(r.data, 'base64'));
  }
  close() { try { this.ws.close(); } catch {} }
}
