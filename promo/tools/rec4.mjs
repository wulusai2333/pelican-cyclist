/* ---------------------------------------------------------------------------
 * 宣传视频录制器 v4 —— 实时 screencast 抓帧（最终采用方案）
 *
 * 为什么：
 *  本机 swiftshader 软件渲染 1080p 只有 ~8fps，而 Page.captureScreenshot 每次要
 *  ~0.8s（且期间页面仍在推进仿真），逐帧"冻结时钟"步进拿不到可用帧率。
 *  页面主循环里 rdt = min(0.05, 真实帧间隔)，只要渲染低于 20fps，每渲染一帧
 *  仿真就恰好推进 0.05s —— 也就是说：**每抓到一帧 = 0.05s 仿真**，天然均匀。
 *  于是按真实时间抓帧、每帧给 1/20s 的时长，即可得到 20fps、速度与真实一致的成片，
 *  HUD 也如实显示 22.3km/h。
 *  交互按墙钟驱动（仿真速度约为真实时间的 0.4 倍，故成片时间 × 2.5 = 墙钟时间）。
 *
 * 每个镜头独立加载页面：一是避免长驻进程被回收，二是单段仿真位移远小于
 * 一圈赛程（赛道 278m，起点 s=8，跑到 u<du 会触发页面自身的一个崩溃缺陷），
 * 分段录制同时规避了那个缺陷。
 *
 * 用法: node rec.mjs list | <segment-id>
 * ------------------------------------------------------------------------- */
import { CDP } from './cdp.mjs';
import { mkdirSync, writeFileSync, appendFileSync, existsSync, readdirSync } from 'node:fs';

const FPS_OUT = 20;                 // 每帧 = 0.05s 仿真
const WALL_PER_VIDEO = 2.9;         // 仿真约为真实时间的 0.4 倍
const READY = '!!(document.getElementById("load") && document.getElementById("load").classList.contains("hide"))';
const PAGE = 'file:///F:/Game/ComfyUI/pelican-cyclist/index.html';
const wait = ms => new Promise(r => setTimeout(r, ms));
const log = m => { const s = `[${new Date().toISOString().slice(11, 19)}] ${m}`; try { appendFileSync('progress.log', s + '\n'); } catch { } console.log(s); };
process.on('uncaughtException', e => { log('UNCAUGHT ' + (e && e.stack || e)); process.exit(1); });
process.on('unhandledRejection', e => { log('REJECTED ' + (e && e.stack || e)); process.exit(1); });

const SEGS = [
  { id: 's1-chase', dur: 7, url: 'nohud=1&tod=15.4', desc: '跟随视角开篇' },
  {
    id: 's2-orbit', dur: 6, url: 'nohud=1&tod=15.4', desc: '拖拽绕车环视',
    actions: [{ t: 0.5, type: 'drag', from: [1180, 640], to: [610, 470], hold: 4.4 }],
  },
  { id: 's3-legs', dur: 8, url: 'nohud=1&tod=15.6&speed=1.25&cam=1.5708,0.085,2.95,1.06,36', desc: '侧视特写·蹬踏(1/5 慢动作)' },
  { id: 's4-low', dur: 6, url: 'nohud=1&tod=16.1&view=low', desc: '低机位跟拍' },
  {
    id: 's5-sunset', dur: 7, url: 'tod=15.4&cam=1.30,0.14,3.9,1.10,40', desc: '拖动时刻滑块：白天→日落',
    actions: [{ t: 0.8, type: 'dragSlider', sel: '#ui-time', from: 15.4, to: 18.15, hold: 5.2 }],
  },
  {
    id: 's6-honk', dur: 6, url: 'tod=17.0&cam=0.95,0.11,2.75,1.26,40', desc: '鸣叫：喉囊充气',
    actions: [{ t: 1.2, type: 'click', sel: '#ui-honk' }, { t: 3.8, type: 'click', sel: '#ui-honk' }],
  },
  { id: 's7-cine', dur: 6, url: 'nohud=1&tod=18.35&view=cine', desc: '电影机位：暮色→星空' },
  { id: 's8-outro', dur: 4, url: 'nohud=1&tod=20.4&cam=1.5708,0.10,3.1,1.05,38', desc: '结尾定格', still: true },
];

const MODE = process.argv[2] || 'list';
if (MODE === 'list') {
  for (const s of SEGS) console.log(`${s.id.padEnd(10)} ${String(Math.round((s.still ? 1 : s.dur * FPS_OUT))).padStart(4)}frames ${s.dur}s  ${s.desc}`);
  process.exit(0);
}
const seg = SEGS.find(s => s.id === MODE);
if (!seg) { console.error('unknown segment: ' + MODE); process.exit(1); }

const c = await CDP.attach();
await c.send('Emulation.setDeviceMetricsOverride', { width: 1920, height: 1080, deviceScaleFactor: 1, mobile: false });

async function ready(timeoutMs = 60000) {
  const t0 = Date.now();
  while (Date.now() - t0 < timeoutMs) {
    try { if (await c.evalJS(READY)) return true; } catch { }
    await wait(400);
  }
  return false;
}
async function mouse(type, x, y) {
  await c.send('Input.dispatchMouseEvent', {
    type, x: Math.round(x), y: Math.round(y), button: 'left',
    buttons: type === 'mouseReleased' ? 0 : 1, clickCount: 1,
  });
}
const evalSafe = code => c.evalJS(code).catch(() => null);
const click = sel => evalSafe(`document.querySelector(${JSON.stringify(sel)})?.click()`);
const setRange = (sel, v) => evalSafe(
  `(()=>{const e=document.querySelector(${JSON.stringify(sel)});if(!e)return 0;e.value=${JSON.stringify(String(v))};` +
  `e.dispatchEvent(new Event('input',{bubbles:true}));return 1;})()`);
const crashed = () => evalSafe('(()=>{const e=document.getElementById("err");return e&&e.classList.contains("show")?(document.getElementById("err-msg").textContent||"err").slice(0,70):"";})()');

/* ------------------------------ 加载页面 ------------------------------ */
const dir = `frames/${seg.id}`;
mkdirSync(dir, { recursive: true });
for (const f of (existsSync(dir) ? readdirSync(dir) : [])) { try { writeFileSync(`${dir}/.keep`, ''); } catch { } }
await c.send('Page.navigate', { url: `${PAGE}?${seg.url}` });
await wait(600);
if (!await ready()) { log('页面未就绪'); process.exit(1); }
await wait(2500);                                   // 等相机阻尼收敛
log(`[${seg.id}] ${seg.desc} 目标 ${seg.still ? 1 : Math.round(seg.dur * FPS_OUT)} 帧`);

/* ------------------------------ screencast 抓帧 ------------------------------ */
let frames = 0;
const target = seg.still ? 1 : Math.round(seg.dur * FPS_OUT);
const t0 = Date.now();
let lastFrameAt = Date.now();
c.on('Page.screencastFrame', p => {
  lastFrameAt = Date.now();
  if (frames < target) {
    try { writeFileSync(`${dir}/f${String(frames).padStart(5, '0')}.jpg`, Buffer.from(p.data, 'base64')); } catch { }
    frames++;
  }
  c.send('Page.screencastFrameAck', { sessionId: p.sessionId }).catch(() => { });
});
await c.send('Page.startScreencast', { format: 'jpeg', quality: 88, maxWidth: 1920, maxHeight: 1080, everyNthFrame: 1 });

/* ------------------------------ 交互调度（按成片时间） ------------------------------ */
const acts = (seg.actions || []).map(a => ({ a, done: false }));
let drag = null;
const started = Date.now();
while (frames < target) {
  const videoT = frames / FPS_OUT;                  // 当前成片时间
  const wallT = (Date.now() - started) / 1000;      // 已经过的墙钟时间
  if (wallT > seg.dur * WALL_PER_VIDEO + 25) { log('超时退出'); break; }
  for (const it of acts) {
    if (it.done || videoT < it.a.t) continue;
    it.done = true;
    const a = it.a;
    if (a.type === 'dragSlider') { await setRange(a.sel, a.from); drag = { kind: 'slider', a, t0: videoT, dur: a.hold || 3 }; }
    if (a.type === 'click') await click(a.sel);
    if (a.type === 'drag') { await mouse('mousePressed', a.from[0], a.from[1]); drag = { kind: 'mouse', a, t0: videoT, dur: a.hold || 3 }; }
  }
  if (drag) {
    const k = Math.min(1, (videoT - drag.t0) / drag.dur);
    const e = k < 0.5 ? 2 * k * k : 1 - Math.pow(-2 * k + 2, 2) / 2;
    if (drag.kind === 'mouse') {
      await mouse('mouseMoved', drag.a.from[0] + (drag.a.to[0] - drag.a.from[0]) * e,
        drag.a.from[1] + (drag.a.to[1] - drag.a.from[1]) * e);
    } else {
      await setRange(drag.a.sel, drag.a.from + (drag.a.to - drag.a.from) * e);
    }
    if (k >= 1) {
      if (drag.kind === 'mouse') await mouse('mouseReleased', drag.a.to[0], drag.a.to[1]);
      drag = null;
    }
  }
  if (Date.now() - lastFrameAt > 4000) { const e = await crashed(); log('抓帧停滞: ' + (e || '无错误信息')); break; }
  if (frames % 40 === 0) log(`  ${seg.id} ${frames}/${target}`);
  await wait(60);
}
if (drag && drag.kind === 'mouse') await mouse('mouseReleased', drag.a.to[0], drag.a.to[1]);
await c.send('Page.stopScreencast').catch(() => { });

const secs = (Date.now() - started) / 1000;
log(`[${seg.id}] 抓到 ${frames} 帧，用时 ${secs.toFixed(1)}s（${(frames / secs).toFixed(1)} fps 抓帧率）`);
writeFileSync(`${dir}/meta.json`, JSON.stringify({
  id: seg.id, frames, dt: seg.still ? seg.dur : 1 / FPS_OUT, desc: seg.desc, still: !!seg.still,
}));
process.exit(frames > 0 ? 0 : 1);
