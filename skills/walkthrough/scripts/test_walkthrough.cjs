const { test } = require('node:test');
const assert = require('node:assert/strict');
const { validate, parseAction } = require('./walkthrough.cjs');
test('actions preserve CSS and fill text; reject unknown actions and external goto', () => {
  assert.deepEqual(parseAction('click #form button'), {kind:'click', selector:'#form button'});
  assert.deepEqual(parseAction('fill #name Ryan Messner'), {kind:'fill', selector:'#name', text:'Ryan Messner'});
  assert.deepEqual(parseAction('fill "#form input" "hello world"'), {kind:'fill', selector:'#form input', text:'hello world'});
  assert.deepEqual(parseAction('wait #ready'), {kind:'wait', selector:'#ready'});
  assert.deepEqual(parseAction('goto /editor'), {kind:'goto', path:'/editor'});
  for (const action of ['hover #x','goto https://example.com','goto //example.com','goto /\\\\example.com','click','fill #name']) {
    assert.throws(() => parseAction(action));
    const doc = good(); doc.steps[0].do = [action]; assert.throws(() => validate(doc));
  }
});
test('only local HTTP preview bases are accepted', () => {
  const {baseURL} = require('./browser.cjs');
  assert.equal(baseURL('http://127.0.0.1:4000'), 'http://127.0.0.1:4000/');
  assert.equal(baseURL('http://localhost:4000/app/'), 'http://localhost:4000/app/');
  for (const url of ['https://localhost:4000','http://example.com','http://localhost.evil.test','http://user:pass@localhost:4000']) assert.throws(() => baseURL(url));
});
test('check CLI validates without loading Playwright', () => {
  const fs = require('node:fs'), os = require('node:os'), path = require('node:path');
  const {spawnSync} = require('node:child_process');
  const dir = fs.mkdtempSync(path.join(os.tmpdir(),'walkthrough-check-'));
  try {
    const file = path.join(dir,'input.json');
    for (const [doc, status, message] of [[good(),0,/Valid walkthrough: 1 steps/],[{...good(),steps:[]},1,/steps/]]) {
      fs.writeFileSync(file, JSON.stringify(doc));
      const run = spawnSync(process.execPath,[path.join(__dirname,'walkthrough.cjs'),'check',file],{encoding:'utf8',env:{...process.env,WALKTHROUGH_PLAYWRIGHT:'/not-installed'}});
      assert.equal(run.status,status); assert.match(run.stdout+run.stderr,message);
    }
  } finally { fs.rmSync(dir,{recursive:true,force:true}); }
});
const good = () => ({intro:'A feature', seed:[], steps:[{say:'Open editor',changed:'',do:['goto /'],see:'Editor',check:'#editor'}]});
test('file contract rejects missing fields and empty steps', () => {
  assert.doesNotThrow(() => validate(good()));
  for (const key of ['intro','seed','steps']) {
    const doc = good(); delete doc[key]; assert.throws(() => validate(doc), new RegExp(key));
  }
  for (const key of ['say','changed','do','see','check']) {
    const doc = good(); delete doc.steps[0][key]; assert.throws(() => validate(doc), new RegExp(key));
  }
  assert.throws(() => validate({...good(), steps:[]}), /steps/);
});
