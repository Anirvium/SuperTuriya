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
    const report={browser:version.product,flows:[],layouts:[],errors:browserErrors};
    const publicBase='http://127.0.0.1:8787';
    const operatorBase='http://127.0.0.1:8766';
    async function layout(label){const result=await evaluate('({width:innerWidth,scrollWidth:document.documentElement.scrollWidth,height:document.documentElement.scrollHeight})');report.layouts.push({label,...result});if(result.scrollWidth>result.width || (label.includes('mobile') && result.width!==390))throw new Error('Horizontal overflow: '+label);return result;}
    async function click(selector){await evaluate(`document.querySelector(${JSON.stringify(selector)}).click()`);}
    await metrics(1440,1000);
    await call('Page.navigate',{url:publicBase});
    await waitFor('document.querySelector(".hero h1") && document.readyState === "complete"');
    await shot('website-desktop.png');
    const homeLayout=await layout('homepage desktop');
    await shot('website-full.png',{x:0,y:0,width:1440,height:homeLayout.height});
    await click('[data-capability="governance"]');
    await waitFor('document.querySelector("#cap-title").textContent === "The final say stays with you."');
    await click('[data-contact]');
    await waitFor('document.querySelector("#contact-dialog").open');
    await click('#close-dialog');
    report.flows.push({name:'marketing tabs and contact dialog',passed:true});
    await call('Page.navigate',{url:publicBase+'/demo/'});
    await waitFor('document.querySelector("#investigate")');
    await shot('playground-start.png');
    for(const id of ['eval-001','eval-002','eval-003','eval-004','eval-005','eval-006','eval-007','eval-008','eval-009','eval-010','eval-011','eval-012']){
      await evaluate(`document.querySelector('#all-case-select').value='${id}';document.querySelector('#all-case-select').dispatchEvent(new Event('change'))`);
      await click('#investigate');
      await waitFor('document.querySelector("#approve-replay")');
      await click('#compare-candidates');
      await waitFor('document.querySelector(".guidance-box")');
      await click('#approve-replay');
      await waitFor('document.querySelector("#activate-lesson")');
      const enabled=await evaluate('!document.querySelector("#activate-lesson").disabled');
      if(enabled!==(id!=='eval-012'))throw new Error('Unexpected verification outcome '+id);
      if(id==='eval-006'){
        const demoLayout=await layout('playground desktop');
        await shot('playground-verified.png',{x:0,y:0,width:1440,height:demoLayout.height});
        await click('[data-view="evidence"]');
        await shot('playground-evidence.png');
        await click('[data-view="walkthrough"]');
      }
      if(enabled){
        await click('#activate-lesson');
        const before=await evaluate('document.querySelector("#confirm-activation").disabled');
        if(!before)throw new Error('Activation enabled before explicit review');
        await click('#activation-consent');await click('#confirm-activation');
        await waitFor('document.querySelector("#revoke-policy")');
        await click('#revoke-policy');
        await waitFor('document.querySelector(".activation-bar b").textContent === "Lesson revoked."');
      }else{
        const blockedLayout=await layout('blocked playground');
        await shot('playground-blocked.png',{x:0,y:0,width:1440,height:blockedLayout.height});
      }
      report.flows.push({case:id,activationEnabled:enabled,passed:true});
    }
    await call('Page.navigate',{url:operatorBase});
    await waitFor('document.querySelector("#session-pill").textContent === "Local operator"');
    await click('#investigate');await waitFor('document.querySelector("#approve-replay")');
    await click('#compare-candidates');await waitFor('document.querySelector(".guidance-box")');
    await click('#approve-replay');await waitFor('document.querySelector("#activate-lesson") && !document.querySelector("#activate-lesson").disabled');
    await click('#activate-lesson');await click('#activation-consent');await click('#confirm-activation');
    await waitFor('document.querySelector("#revoke-policy")');
    await shot('operator-active.png');
    await click('#revoke-policy');await waitFor('document.querySelector(".activation-bar b").textContent === "Lesson revoked."');
    await click('[data-case="eval-012"]');await click('#investigate');await waitFor('document.querySelector("#approve-replay")');
    await click('#approve-replay');await waitFor('document.querySelector("#activate-lesson")?.disabled');
    report.flows.push({name:'Python operator investigate, compare, replay, activate, revoke, blocked case',passed:true});
    await metrics(390,844,true);
    await call('Page.navigate',{url:publicBase});await waitFor('document.querySelector(".hero h1") && document.readyState === "complete"');
    const mobile=await layout('homepage mobile');await shot('website-mobile.png');await shot('website-mobile-full.png',{x:0,y:0,width:390,height:mobile.height});
    await click('#menu-toggle');await waitFor('document.querySelector("#navigation").classList.contains("open")');
    await click('#menu-toggle');
    await call('Page.navigate',{url:publicBase+'/demo/'});await waitFor('document.querySelector("#investigate")');
    await click('#investigate');await waitFor('document.querySelector("#approve-replay")');await click('#approve-replay');await waitFor('document.querySelector("#activate-lesson")');
    const mobileDemo=await layout('playground mobile');await shot('playground-mobile.png');await shot('playground-mobile-full.png',{x:0,y:0,width:390,height:mobileDemo.height});
    await call('Page.navigate',{url:publicBase+'/docs/'});await waitFor('document.querySelector(".docs-main") && document.readyState === "complete"');await layout('docs mobile');
    await metrics(1200,630);await call('Page.navigate',{url:publicBase+'/social-card.html'});await waitFor('document.querySelector(".social-canvas") && document.readyState === "complete"');
    const social=await call('Page.captureScreenshot',{format:'png'});await fs.writeFile(path.resolve(__dirname,'../sites/superturiya/dist/assets/social-preview.png'),Buffer.from(social.data,'base64'));
    await fs.writeFile(path.join(output,'browser-qa.json'),JSON.stringify(report,null,2));
    console.log(JSON.stringify(report,null,2));
  } finally {
    chrome.kill('SIGTERM');
  }
}
main().catch(e => { console.error(e); process.exitCode=1; });
