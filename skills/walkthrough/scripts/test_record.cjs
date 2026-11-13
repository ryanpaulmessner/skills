const {test} = require('node:test');
const assert = require('node:assert/strict');
const http = require('node:http');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const {spawn} = require('node:child_process');
test('record saves video and names a missing check step with a failing exit', {skip:!process.env.WALKTHROUGH_BROWSER_TEST}, async () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(),'walkthrough-test-'));
  const server = http.createServer((req,res) => res.end('<h1 id="ready">Ready</h1>'));
  await new Promise(r => server.listen(0,'127.0.0.1',r));
  try {
    for (const [selector, expected] of [['#removed',1],['#ready',0]]) {
      const file = path.join(dir,'walkthrough.json');
      fs.writeFileSync(file,JSON.stringify({intro:'Try it',seed:[],steps:[{say:'Show saved editor',changed:'New',do:['goto /'],see:'Editor ready',check:selector}]}));
      const result = await new Promise(resolve => {
        const child = spawn(process.execPath,[path.join(__dirname,'walkthrough.cjs'),'record',file,'--url',`http://127.0.0.1:${server.address().port}`,'--out',dir]);
        let output = ''; child.stdout.on('data',b => output += b); child.stderr.on('data',b => output += b);
        child.on('close',code => resolve({code,output}));
      });
      assert.equal(result.code,expected,result.output);
      if (expected) assert.match(result.output,/Step 1 "Show saved editor" failed \(check: #removed\)/);
      const video = result.output.split('\n').find(line => line.endsWith('.webm'));
      assert.ok(video, result.output); assert.ok(fs.statSync(video).size > 0);
    }
  } finally { server.close(); fs.rmSync(dir,{recursive:true,force:true}); }
});
