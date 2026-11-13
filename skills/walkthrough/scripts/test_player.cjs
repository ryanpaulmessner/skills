const {test} = require('node:test');
const assert = require('node:assert/strict');
const {initial,step} = require('./player.cjs');
test('collapse and edge persist through steps, failures, retries and Back', () => {
  let state = initial(2);
  assert.equal(state.collapsed,false); assert.equal(state.side,'right');
  for (const event of ['collapse','switch-side','next','passed','next','failed','retry','passed','back']) {
    const result = step(state,event,'missing'); state = result.state;
    assert.equal(state.collapsed,true);
    assert.equal(state.side,event === 'collapse' ? 'right' : 'left');
    if (['collapse','switch-side'].includes(event)) assert.deepEqual(result.effects,[]);
  }
  state = step(state,'expand').state; assert.equal(state.collapsed,false);
  state = step(state,'switch-side').state; assert.equal(state.side,'right');
  state = step(state,'next').state;
  state = step(state,'collapse').state; assert.equal(state.phase,'running'); assert.equal(state.collapsed,true);
  state = step(state,'switch-side').state; assert.equal(state.side,'left');
});
test('player guards duplicate Next, retries failures, completes and revisits narration', () => {
  let state = initial(1);
  let result = step(state,'next');
  assert.deepEqual(result.effects,[{type:'run',index:0}]);
  state = result.state;
  assert.deepEqual(step(state,'next'),{state,effects:[]});
  assert.deepEqual(step(state,'back'),{state,effects:[]});
  state = step(state,'failed','missing #ready').state;
  assert.equal(state.error,'missing #ready');
  assert.deepEqual(step(state,'next'),{state,effects:[]});
  result = step(state,'retry'); assert.deepEqual(result.effects,[{type:'run',index:0}]);
  state = step(result.state,'passed').state; assert.equal(state.phase,'complete');
  assert.deepEqual(step(state,'next'),{state,effects:[]});
  result = step(state,'back'); assert.equal(result.state.index,-1); assert.deepEqual(result.effects,[]);
});
