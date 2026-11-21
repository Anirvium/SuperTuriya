const { spawn } = require('node:child_process');
const fs = require('node:fs/promises');
const path = require('node:path');
const os = require('node:os');

// Local visual QA only; an isolated browser profile and synthetic demo database.
async function main() {
  const output = path.resolve(__dirname, '../output/public-launch');
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
    const report={browser:version.product,public_url:'https://superturiya.piyushunt.chatgpt.site',checks:[],errors:browserErrors};
    await metrics(1440,1000);
    await call('Page.navigate',{url:report.public_url});
    await waitFor('document.querySelector(".hero h1") && document.readyState === "complete"');
    report.checks.push({page:'homepage',title:await evaluate('document.title'),contentPolicy:await evaluate("!!document.querySelector('meta[http-equiv=\"Content-Security-Policy\"]')")});
    await shot('live-website-desktop.png');
    await call('Page.navigate',{url:report.public_url+'/demo/'});
    await waitFor('document.querySelector("#investigate")');
    const caseCount=await evaluate('document.querySelectorAll("#all-case-select option").length');
    if(caseCount!==12)throw new Error('Public evidence bundle did not load');
    await evaluate('document.querySelector("#investigate").click()');
    await waitFor('document.querySelector("#approve-replay")');
    await evaluate('document.querySelector("#approve-replay").click()');
    await waitFor('document.querySelector("#activate-lesson") && !document.querySelector("#activate-lesson").disabled');
    report.checks.push({page:'public playground',caseCount,verifiedRepair:true});
    await shot('live-playground.png');
    await evaluate("document.querySelector('[data-case=\"eval-012\"]').click(); document.querySelector(\"#investigate\").click()");
    await waitFor('document.querySelector("#approve-replay")');
    await evaluate('document.querySelector("#approve-replay").click()');
    await waitFor('document.querySelector("#activate-lesson")?.disabled');
    report.checks.push({page:'public playground',blockedRepair:true});
    await metrics(390,844,true);
    await call('Page.navigate',{url:report.public_url});
    await waitFor('document.querySelector(".hero h1") && document.readyState === "complete"');
    await shot('live-website-mobile.png');
    const mobile=await evaluate('({width:innerWidth,scrollWidth:document.documentElement.scrollWidth})');
    if(mobile.width!==390||mobile.scrollWidth!==390)throw new Error('Mobile overflow');
    report.checks.push({page:'public mobile homepage',...mobile});
    await call('Page.navigate',{url:report.public_url+'/docs/'});
    await waitFor('document.querySelector(".docs-main") && document.readyState === "complete"');
    report.checks.push({page:'public field guide',loaded:true});
    await metrics(1440,1000);
    await call('Page.navigate',{url:'http://127.0.0.1:8765/'});
    await waitFor('document.querySelector("#session-pill").textContent === "Local operator"');
    await evaluate('document.querySelector("#investigate").click()');await waitFor('document.querySelector("#approve-replay")');
    await evaluate('document.querySelector("#approve-replay").click()');await waitFor('document.querySelector("#activate-lesson") && !document.querySelector("#activate-lesson").disabled');
    await evaluate('document.querySelector("#activate-lesson").click();document.querySelector("#activation-consent").click();document.querySelector("#confirm-activation").click()');
    await waitFor('document.querySelector("#revoke-policy")');
    await evaluate('document.querySelector("#revoke-policy").click()');await waitFor('document.querySelector(".activation-bar b").textContent === "Lesson revoked."');
    report.checks.push({page:'latest local Python operator',approvalReplayActivationRevocation:true});
    await fs.writeFile(path.join(output,'deployed-browser-qa.json'),JSON.stringify(report,null,2));
    console.log(JSON.stringify(report,null,2));
  } finally {
    chrome.kill('SIGTERM');
  }
}
main().catch(e => { console.error(e); process.exitCode=1; });
