#!/usr/bin/env node
'use strict';
function validate(doc) {
  const text = (value, label, empty = false) => {
    if (typeof value !== 'string' || (!empty && !value.trim())) throw Error(`${label} must be a string${empty ? '' : ' (nonempty)'}`);
  };
  if (!doc || typeof doc !== 'object') throw Error('walkthrough must be an object');
  text(doc.intro, 'intro');
  if (!Array.isArray(doc.seed)) throw Error('seed must be a list');
  doc.seed.forEach(s => text(s, 'seed command'));
  if (!Array.isArray(doc.steps) || !doc.steps.length) throw Error('steps must be a nonempty list');
  doc.steps.forEach((step, i) => {
    if (!step || typeof step !== 'object') throw Error(`step ${i + 1} must be an object`);
    for (const key of ['say', 'changed', 'see', 'check']) text(step[key], `step ${i + 1} ${key}`, key === 'changed');
    if (!Array.isArray(step.do)) throw Error(`step ${i + 1} do must be a list`);
    step.do.forEach(parseAction);
  });
  return doc;
}
function parseAction(action) {
  if (typeof action !== 'string') throw Error('action must be a string');
  const match = /^(goto|click|fill|wait)\s+(.+)$/s.exec(action.trim());
  if (!match) throw Error(`Unknown or incomplete action: ${action}`);
  const [, kind, rest] = match;
  if (kind === 'goto') {
    if (/^[a-z][a-z0-9+.-]*:|^\/\/|[\\\s]/i.test(rest)) throw Error('goto requires a relative path');
    return {kind, path:rest};
  }
  if (kind !== 'fill') return {kind, selector:rest};
  // JSON quoting permits selectors with spaces and empty fill values.
  const fill = /^("(?:\\.|[^"\\])*"|\S+)\s+(.+)$/s.exec(rest);
  if (!fill) throw Error('fill requires a selector and text');
  const unquote = value => value.startsWith('"') ? JSON.parse(value) : value;
  return {kind, selector:unquote(fill[1]), text:unquote(fill[2])};
}
module.exports = {validate, parseAction};
async function main(args) {
  const usage = 'walkthrough check <file> | play <file> --url <base> | record <file> --url <base> --out <dir>';
  if (args.includes('--help')) { console.log(usage); return; }
  const [command, file, ...flags] = args;
  if (!['check','play','record'].includes(command) || !file) throw Error(usage);
  const options = {command};
  for (let i = 0; i < flags.length; i += 2) {
    if (!['--url','--out'].includes(flags[i]) || !flags[i + 1] || flags[i + 1].startsWith('--') || options[flags[i].slice(2)]) throw Error(usage);
    options[flags[i].slice(2)] = flags[i + 1];
  }
  if (command === 'check' && flags.length || command !== 'check' && !options.url || command === 'record' && !options.out || command === 'play' && options.out) throw Error(usage);
  const doc = validate(JSON.parse(require('node:fs').readFileSync(file,'utf8')));
  if (command === 'check') { console.log(`Valid walkthrough: ${doc.steps.length} steps`); return; }
  await require('./browser.cjs').start(doc,options);
}
if (require.main === module) main(process.argv.slice(2)).catch(error => { console.error(error.message); process.exitCode = 1; });
