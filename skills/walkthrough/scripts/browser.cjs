'use strict';
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const {parseAction} = require('./walkthrough.cjs');
const player = require('./player.cjs');

function playwright() {
  if (process.env.WALKTHROUGH_PLAYWRIGHT) return require(process.env.WALKTHROUGH_PLAYWRIGHT);
  try { return require('playwright'); } catch (error) {
    if (error.code !== 'MODULE_NOT_FOUND') throw error;
  }
  const cache = path.join(process.env.npm_config_cache || path.join(os.homedir(), '.npm'), '_npx');
  const candidates = fs.existsSync(cache) ? fs.readdirSync(cache).map(name => path.join(cache, name, 'node_modules/playwright')).filter(p => fs.existsSync(path.join(p, 'package.json'))) : [];
  candidates.sort((a, b) => require(path.join(b, 'package.json')).version.localeCompare(require(path.join(a, 'package.json')).version, undefined, {numeric:true}));
  if (candidates.length) return require(candidates[0]);
  throw Error('Playwright not found. Set WALKTHROUGH_PLAYWRIGHT to an installed package directory; ask before installing.');
}

function baseURL(value) {
  const url = new URL(value);
  if (url.protocol !== 'http:' || !['localhost','127.0.0.1'].includes(url.hostname) || url.username || url.password) throw Error('--url must be http://localhost or http://127.0.0.1');
  return url.href;
}

async function runStep(page, step, base, index) {
  try {
    for (const source of step.do) {
      const action = parseAction(source);
      if (action.kind === 'goto') await page.goto(new URL(action.path, base).href);
      else if (action.kind === 'click') await page.locator(action.selector).click();
      else if (action.kind === 'fill') await page.locator(action.selector).fill(action.text);
      else await page.locator(action.selector).waitFor({state:'visible'});
    }
    await page.locator(step.check).waitFor({state:'attached'});
  } catch (error) {
    throw Error(`Step ${index + 1} "${step.say}" failed (check: ${step.check}): ${error.message}`);
  }
}

// A shadow root isolates panel styling from the preview. Text never becomes HTML.
function panel(state) {
  let host = document.getElementById('__walkthrough_panel');
  if (!host) {
    host = document.createElement('div'); host.id = '__walkthrough_panel';
    host.style.cssText = 'all:initial;position:fixed;right:16px;top:16px;width:340px;max-width:calc(100vw - 32px);z-index:2147483647;';
    document.documentElement.append(host); host.attachShadow({mode:'open'});
  }
  host.style.left = state.side === 'left' ? '16px' : 'auto';
  host.style.right = state.side === 'right' ? '16px' : 'auto';
  host.style.width = state.collapsed ? 'auto' : '340px';
  const root = host.shadowRoot;
  const counter = `Step ${state.index + 1} of ${state.total}`;
  const styles = `<style>
    *{box-sizing:border-box} section{font:16px/1.5 system-ui,sans-serif;color:#172033;background:#fff;border:1px solid #64748b;border-radius:12px;padding:20px;box-shadow:0 8px 32px #0005;max-height:calc(100vh - 32px);overflow:auto}
    h2{font-size:19px;margin:8px 0 12px} p{white-space:pre-wrap;margin:12px 0;overflow-wrap:anywhere} .changed{background:#fff2be;color:#503800;border-left:4px solid #ad7400;padding:10px} .status{color:#9f1239} small{color:#475569} nav{display:flex;gap:12px;margin-top:20px} button{font:inherit;padding:8px 16px;border:1px solid #475569;border-radius:6px;background:#f1f5f9;color:#172033;cursor:pointer} button:disabled{opacity:.5;cursor:default} button:focus-visible{outline:3px solid #2563eb}
    .tools{display:flex;gap:8px;margin-bottom:12px}.tools button{font-size:13px;padding:6px 10px}.tab{font:14px/1.5 system-ui,sans-serif;background:#fff;color:#172033;box-shadow:0 4px 16px #0004}
    </style>`;
  if (state.collapsed) {
    root.innerHTML = `${styles}<button class="tab" aria-expanded="false"></button>`;
    const tab = root.querySelector('button'); tab.textContent = counter;
    tab.title = 'Expand walkthrough'; tab.onclick = () => window.__walkthroughMove('expand');
    return;
  }
  root.innerHTML = `${styles}<section aria-label="Walkthrough"><div class="tools"><button id="collapse" aria-expanded="true">Collapse</button><button id="side"></button></div><small></small><h2></h2><p class="say"></p><p class="changed"></p><p class="see"></p><p class="status" role="status"></p><nav><button id="back">Back</button><button id="next">Next</button></nav></section>`;
  const set = (selector, text) => { root.querySelector(selector).textContent = text; };
  set('small', state.index < 0 ? `Introduction · ${state.total} steps` : counter);
  set('#side', state.side === 'right' ? 'Move left' : 'Move right');
  root.querySelector('#collapse').onclick = () => window.__walkthroughMove('collapse');
  root.querySelector('#side').onclick = () => window.__walkthroughMove('switch-side');
  set('h2', state.index < 0 ? 'Try this feature' : state.step.say);
  set('.say', state.index < 0 ? state.intro : '');
  set('.changed', state.step?.changed ? `What changed\n${state.step.changed}` : '');
  root.querySelector('.changed').hidden = !state.step?.changed;
  set('.see', state.step ? `What to see\n${state.step.see}` : 'Use Next to try the first step. You can also interact with the page.');
  set('.status', state.error || (state.busy ? 'Running step…' : ''));
  const back = root.querySelector('#back'), next = root.querySelector('#next');
  back.disabled = state.busy || state.index < 0;
  next.disabled = state.busy || (state.index === state.total - 1 && !state.error);
  next.textContent = state.error ? 'Retry' : state.index === state.total - 1 ? 'Complete' : 'Next';
  back.onclick = () => window.__walkthroughMove('back');
  next.onclick = () => window.__walkthroughMove(state.error ? 'retry' : 'next');
}

async function start(doc, options) {
  const base = baseURL(options.url);
  const recording = options.command === 'record';
  if (recording) fs.mkdirSync(options.out, {recursive:true});
  const browser = await playwright().chromium.launch({headless:recording});
  const context = await browser.newContext({viewport:{width:1440,height:900}, ...(recording ? {recordVideo:{dir:path.resolve(options.out),size:{width:1440,height:900}}} : {})});
  const page = await context.newPage();
  page.setDefaultTimeout(5000);
  page.setDefaultNavigationTimeout(15000);
  let state = player.initial(doc.steps.length);
  let closed = false;
  const render = async () => {
    if (!closed) await page.evaluate(panel, {...state,intro:doc.intro,step:doc.steps[state.index],busy:state.phase === 'running'});
  };
  const move = async direction => {
    const result = player.step(state,direction); state = result.state; await render();
    for (const effect of result.effects) {
      try {
        await runStep(page,doc.steps[effect.index],base,effect.index);
        state = player.step(state,'passed').state;
      } catch (error) {
        state = player.step(state,'failed',error.message).state;
        await render();
        if (recording) { await page.waitForTimeout(1200); throw error; }
      }
      await render();
    }
  };
  await page.exposeBinding('__walkthroughMove', async (_, direction) => {
    if (!recording) await move(direction);
  });
  page.on('domcontentloaded', () => render().catch(() => {}));
  page.on('close', () => { closed = true; });
  const video = recording ? page.video() : null;
  try {
    await page.goto(base); await render();
    if (recording) {
      await page.waitForTimeout(1200);
      for (let index = 0; index < doc.steps.length; index++) {
        await move('next'); await page.waitForTimeout(1800);
      }
    } else {
      console.log('Walkthrough open. Close the browser to finish. Back shows prior narration; Next replays actions.');
      await new Promise(resolve => { page.once('close', resolve); browser.once('disconnected', resolve); });
    }
  } finally {
    await context.close();
    if (video) console.log(await video.path());
    await browser.close();
  }
}
module.exports = {start, runStep, baseURL, playwright};
