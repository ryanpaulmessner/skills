const {test} = require('node:test');
const assert = require('node:assert/strict');
const http = require('node:http');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const {spawn} = require('node:child_process');
const {playwright} = require('./browser.cjs');
test('panel collapses, changes edges and retains presentation across navigation', {skip:!process.env.WALKTHROUGH_BROWSER_TEST}, async () => {
  const pw = playwright();
  const packageFile = Object.values(require.cache).find(module => module.exports === pw).filename;
  const dir = fs.mkdtempSync(path.join(os.tmpdir(),'walkthrough-panel-'));
  const server = http.createServer((req,res) => res.end('<h1 id="ready">Ready</h1><button id="corner" style="position:fixed;right:20px;top:150px" onclick="this.textContent=\'Clicked\'">App control</button>'));
  await new Promise(resolve => server.listen(0,'127.0.0.1',resolve));
  try {
    const file = path.join(dir,'walkthrough.json');
    fs.writeFileSync(file,JSON.stringify({intro:'Preview',seed:[],steps:Array.from({length:3},(_,i) => ({say:`Step ${i+1}`,changed:'New controls',do:['goto /'],see:'Ready',check:'#ready'}))}));
    const result = await new Promise(resolve => {
      const child = spawn(process.execPath,['--require',path.join(__dirname,'panel-probe.cjs'),path.join(__dirname,'walkthrough.cjs'),'play',file,'--url',`http://127.0.0.1:${server.address().port}`],{env:{...process.env,WALKTHROUGH_PLAYWRIGHT:packageFile}});
      let output = ''; child.stdout.on('data',b => output += b); child.stderr.on('data',b => output += b);
      child.on('close',code => resolve({code,output}));
    });
    assert.equal(result.code,0,result.output); assert.match(result.output,/PASS collapse/);
  } finally {server.close(); fs.rmSync(dir,{recursive:true,force:true});}
});
