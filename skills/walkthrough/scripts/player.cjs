'use strict';
const transitions = {
  ready: {next:'advance', back:'back'},
  running: {passed:'passed', failed:'failed'},
  failed: {retry:'retry', back:'back'},
  complete: {back:'back'},
};
const presentation = {
  collapsed: {false: {collapse:true}, true: {expand:false}},
  side: {right: {'switch-side':'left'}, left: {'switch-side':'right'}},
};
function initial(total) { return {phase:'ready', index:-1, total, error:'', collapsed:false, side:'right'}; }
function step(state, event, error = '') {
  for (const [field, table] of Object.entries(presentation)) {
    const value = table[state[field]]?.[event];
    if (value !== undefined) return {state:{...state,[field]:value},effects:[]};
  }
  const action = transitions[state.phase]?.[event];
  if (!action) return {state,effects:[]};
  if (action === 'back') return {state:{...state,phase:'ready',index:Math.max(-1,state.index-1),error:''},effects:[]};
  if (action === 'advance' || action === 'retry') {
    const index = state.index + (action === 'advance' ? 1 : 0);
    if (index >= state.total) return {state,effects:[]};
    return {state:{...state,phase:'running',index,error:''},effects:[{type:'run',index}]};
  }
  if (action === 'failed') return {state:{...state,phase:'failed',error},effects:[]};
  return {state:{...state,phase:state.index === state.total-1 ? 'complete' : 'ready',error:''},effects:[]};
}
module.exports = {initial,step,transitions};
