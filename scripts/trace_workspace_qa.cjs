const { spawn } = require('node:child_process');
const fs = require('node:fs/promises');
const path = require('node:path');
const os = require('node:os');

// Local visual QA only; an isolated browser profile and synthetic demo database.
async function main() {
  const output = path.resolve(__dirname, '../output/workspace-upgrade');
  await fs.mkdir(output, {recursive:true});
  const profile = await fs.mkdtemp(path.join(os.tmpdir(), 'superturiya-visual-qa-'));
  const chrome = spawn('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', [
    '--headless=new', '--disable-gpu', '--no-first-run', '--no-default-browser-check',
    '--disable-background-networking', '--disable-sync', '--metrics-recording-only',
    '--remote-debugging-pipe', `--user-data-dir=${profile}`,
  ], { stdio: ['ignore', 'ignore', 'pipe', 'pipe', 'pipe'] });
  let counter = 0, buffer = '', stderr = '';
  const pending = new Map();
  const browserErrors = [];
  chrome.stderr.on('data', b => { stderr = (stderr + b).slice(-3000); });
  chrome.stdio[4].on('data', b => {
    buffer += b.toString();
    for (;;) {
      const end = buffer.indexOf('\0');
      if (end < 0) break;
      const raw = buffer.slice(0, end); buffer = buffer.slice(end + 1);
      if (!raw) continue;
      const msg = JSON.parse(raw);
      if (msg.id && pending.has(msg.id)) {
        const p = pending.get(msg.id); pending.delete(msg.id); clearTimeout(p.timer);
        msg.error ? p.reject(new Error(JSON.stringify(msg.error))) : p.resolve(msg.result);
      } else if (msg.method === 'Runtime.exceptionThrown') {
        browserErrors.push(msg.params.exceptionDetails);
      }
    }
  });
  const send = (method, params = {}, sessionId) => new Promise((resolve, reject) => {
    const id = ++counter;
    const timer = setTimeout(() => { pending.delete(id); reject(new Error(`Timeout: ${method}; ${stderr}`)); }, 25000);
    pending.set(id, {resolve, reject, timer});
    chrome.stdio[3].write(JSON.stringify({id, method, params, ...(sessionId ? {sessionId} : {})}) + '\0');
  });
  try {
    const version = await send('Browser.getVersion');
    const {targetId} = await send('Target.createTarget', {url:'about:blank'});
    const {sessionId} = await send('Target.attachToTarget', {targetId, flatten:true});
    const call = (method, params = {}) => send(method, params, sessionId);
    await call('Page.enable'); await call('Runtime.enable');
    const evaluate = async expression => {
      const r = await call('Runtime.evaluate', {expression, returnByValue:true, awaitPromise:true});
      if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails));
      return r.result.value;
    };
    const waitFor = async expression => {
      const until = Date.now() + 12000;
      while (Date.now() < until) {
        if (await evaluate(expression)) return;
        await new Promise(r => setTimeout(r, 100));
      }
      throw new Error(`UI condition failed: ${expression}`);
    };
    const metrics = async (width,height,mobile=false) => call('Emulation.setDeviceMetricsOverride', {width,height,deviceScaleFactor:1,mobile});
    const shot = async (file, clip) => {
      await evaluate('Promise.all(document.getAnimations().filter(a => a.effect.getComputedTiming().iterations !== Infinity).map(a => a.finished.catch(() => {}))).then(() => true)');
      const r = await call('Page.captureScreenshot', {format:'png', captureBeyondViewport:!!clip, ...(clip ? {clip:{...clip,scale:1}} : {})});
      await fs.writeFile(path.join(output,file), Buffer.from(r.data,'base64'));
    };
    const report={browser:version.product,checks:[],errors:browserErrors};
    const base='http://127.0.0.1:8767';
    const click=async selector=>evaluate(`document.querySelector(${JSON.stringify(selector)}).click()`);
    const layout=async label=>{const m=await evaluate('({width:innerWidth,scrollWidth:document.documentElement.scrollWidth})');if(m.width!==m.scrollWidth)throw Error('Overflow: '+label);report.checks.push({label,...m})};
    await metrics(1440,1000);
    await call('Page.navigate',{url:base+'/traces.html'});
    await waitFor('document.querySelector("#connection").textContent === "Local workspace"');
    await click('#example');await waitFor('document.querySelector("#save-trace")');
    await shot('trace-preview-desktop.png');await layout('trace preview desktop');
    await click('#save-trace');await waitFor('document.querySelector("#export-trace")');
    await shot('trace-saved-desktop.png');const h=await evaluate('document.documentElement.scrollHeight');await shot('trace-saved-full.png',{x:0,y:0,width:1440,height:h});
    const count=await evaluate('document.querySelectorAll("[data-run]").length');
    await call('Page.reload');await waitFor('document.querySelector("[data-run]")');
    await click('[data-run]');await waitFor('document.querySelector("#export-trace")');
    report.checks.push({name:'import and persisted history after reload',passed:true});
    await click('#example');await waitFor('document.querySelector("#save-trace")');await click('#save-trace');await waitFor('document.querySelector("#notice").textContent.includes("already saved")');
    if(await evaluate('document.querySelectorAll("[data-run]").length')!==count)throw Error('Duplicate import created a second run');
    report.checks.push({name:'duplicate import opens existing snapshot',passed:true});
    const hostile={schema:'superturiya-trace-v1',agent:'<img src=x onerror="window.traceXss=true">',goal:'Inspect inert hostile text',spans:[{span_id:'one',name:'<script>window.traceXss=true</script>',kind:'tool',status:'failed',input:{authorization:'Bearer secret-synthetic-token'},output:'<img src=x onerror="window.traceXss=true">'}]};
    const imported=await evaluate(`fetch('/workspace/import',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({record:${JSON.stringify(hostile)}})}).then(r=>r.json())`);
    await click('#refresh');await waitFor(`document.querySelector('[data-run="${imported.run_id}"]')`);await click(`[data-run="${imported.run_id}"]`);await waitFor('document.querySelector("#export-trace")');
    if(await evaluate('!!window.traceXss || !!document.querySelector("#inspector img") || document.querySelector("#inspector").textContent.includes("secret-synthetic-token")'))throw Error('Hostile content or credentials leaked');
    await call('Page.navigate',{url:base+'/traces.html'});await waitFor('document.querySelector("[data-run]")');
    await metrics(390,844,true);await evaluate('Array.from(document.querySelectorAll("[data-run]")).find(b=>b.textContent.includes("example-assistant")).click()');await waitFor('document.querySelector("#export-trace")');await layout('saved trace mobile');await evaluate('document.querySelector("#inspector").scrollIntoView({behavior:"instant",block:"start"})');await shot('trace-mobile.png');
    await evaluate('document.querySelector("#search").value="no-matching-workflow";document.querySelector("#search").dispatchEvent(new Event("input"))');
    if(await evaluate('document.querySelectorAll("[data-run]").length')!==0)throw Error('Run search failed');
    await evaluate('document.querySelector(".audit").open=true');await click('#load-audit');await waitFor('document.querySelector(".audit-row")');
    report.checks.push({name:'search and persistent audit',passed:true});
    await call('Page.navigate',{url:base+'/'});await waitFor('document.querySelector("#traces-link")');
    if(await evaluate('document.querySelector("#traces-link").getAttribute("href")')!=='/traces.html')throw Error('Missing operator trace navigation');
    report.checks.push({name:'operator navigation',passed:true});
    if(browserErrors.length)throw Error('Browser exceptions were recorded');
    await fs.writeFile(path.join(output,'trace-browser-qa.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report,null,2));
  } finally { chrome.kill('SIGTERM'); }
}
main().catch(e => { console.error(e); process.exitCode=1; });
