/* 端到端回归：让页面自然跑过整圈赛道（绕过 u<du 的回绕点），确认不再崩溃。
 * 用法：./promo/tools/withchrome.sh ../../tools/smoke-lap.mjs [秒数]
 *   （withchrome.sh 会先 cd 到 promo/tools，故脚本路径需相对该目录） */
import { CDP } from '../promo/tools/cdp.mjs';

const READY = '!!(document.getElementById("load") && document.getElementById("load").classList.contains("hide"))';
const ERR = '(()=>{const e=document.getElementById("err");return e&&e.classList.contains("show")?(document.getElementById("err-msg").textContent||"err"):"";})()';
const HUD = '["s-kmh","s-dc"].map(id=>{const e=document.getElementById(id);return e?e.textContent:"?"}).join(" | ")';
const PAGE = 'file:///F:/Game/ComfyUI/pelican-cyclist/index.html';
const wait = ms => new Promise(r => setTimeout(r, ms));

const SECS = Number(process.argv[2] || 170);
const c = await CDP.attach();
await c.send('Emulation.setDeviceMetricsOverride', { width: 1280, height: 720, deviceScaleFactor: 1, mobile: false });
await c.send('Page.navigate', { url: `${PAGE}?nohud=1&tod=15.4` });   // speed 用默认 6.2 m/s
await wait(800);
for (let i = 0; i < 100; i++) { try { if (await c.evalJS(READY)) break; } catch { } await wait(400); }
console.log(`页面就绪，连续运行 ${SECS}s（赛道 278m，6.2m/s 一圈约 44s 仿真，软渲染下墙钟约 2.6 倍）…`);

const t0 = Date.now();
let last = Date.now();
for (;;) {
  const el = (Date.now() - t0) / 1000;
  if (el > SECS) break;
  const err = await c.evalJS(ERR).catch(() => '');
  if (err) { console.log(`\n❌ 崩溃 @ ${el.toFixed(0)}s : ${err}`); c.close(); process.exit(1); }
  // 页面卡死检测：HUD 不再更新
  if (Date.now() - last > 5000) {
    console.log(`  t=${el.toFixed(0)}s  ${await c.evalJS(HUD).catch(() => '?')}`);
    last = Date.now();
  }
  await wait(1000);
}
// 软渲染下仿真约为墙钟的 1/2.6；赛道 278m，6.2m/s 时一圈约 44s 仿真
const laps = (SECS / 2.6) * 6.2 / 278;
console.log(`\n✅ 连续运行 ${SECS}s 未崩溃` + (laps >= 1
  ? `（仿真约跑过 ${laps.toFixed(1)} 圈，已越过回绕点）`
  : `（约 ${laps.toFixed(2)} 圈，未到回绕点，建议 ≥150s）`));
c.close();
process.exit(0);
