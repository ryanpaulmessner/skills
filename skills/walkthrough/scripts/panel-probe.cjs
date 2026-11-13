// CLI browser-test preload: exercise the real player without production test hooks.
const assert = require('node:assert/strict');
const path = require('node:path');
// Load only Playwright here: loading browser.cjs would cache the CLI before main runs.
const pw = require(process.env.WALKTHROUGH_PLAYWRIGHT);
const launch = pw.chromium.launch.bind(pw.chromium);
pw.chromium.launch = async options => {
  const browser = await launch({...options,headless:!process.env.WALKTHROUGH_HEADED});
  const createContext = browser.newContext.bind(browser);
  browser.newContext = async options => {
    const context = await createContext(options);
    context.on('page', page => {
      (async () => {
        const panel = page.locator('#__walkthrough_panel');
        const button = name => panel.getByRole('button',{name,exact:true});
        const screenshot = async state => {
          if (process.env.WALKTHROUGH_EVIDENCE) await page.screenshot({path:path.join(process.env.WALKTHROUGH_EVIDENCE,`round1-${process.env.THEME}-${state}.png`)});
        };
        await button('Next').click();
        await page.waitForFunction(() => !document.querySelector('#__walkthrough_panel')?.shadowRoot.querySelector('#next')?.disabled);
        await button('Collapse').click();
        await button('Step 1 of 3').waitFor();
        assert.ok((await panel.boundingBox()).width < 180);
        await screenshot('collapsed');
        await page.locator('#corner').click();
        assert.equal(await page.locator('#corner').textContent(),'Clicked');
        await button('Step 1 of 3').click();
        await button('Move left').click();
        await button('Move right').waitFor();
        assert.equal((await panel.boundingBox()).x,16);
        await screenshot('left');
        await button('Collapse').click();
        // Advance while collapsed to verify the saved presentation after a full goto.
        await Promise.all([
          page.waitForEvent('domcontentloaded'),
          page.evaluate(() => { setTimeout(() => window.__walkthroughMove('next'),0); }),
        ]);
        await button('Step 2 of 3').waitFor();
        assert.equal((await panel.boundingBox()).x,16);
        await button('Step 2 of 3').click();
        await button('Back').click();
        await panel.getByText('Step 1 of 3',{exact:true}).waitFor();
        await button('Move right').waitFor();
        assert.equal((await panel.boundingBox()).x,16);
        await button('Next').click();
        await page.waitForFunction(() => !document.querySelector('#__walkthrough_panel')?.shadowRoot.querySelector('#next')?.disabled);
        await button('Move right').click();
        await button('Move left').waitFor();
        assert.equal((await panel.boundingBox()).x,1084);
        console.log('PASS collapse, expand, uncovered app control, both edges, goto, Back and Next at 1440x900');
      })().catch(error => {console.error(error);process.exitCode=1;}).finally(() => page.close());
    });
    return context;
  };
  return browser;
};
