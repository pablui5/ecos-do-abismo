const test=require('node:test'),assert=require('node:assert/strict');
const Q=require('../public/campaign.js');
const evidence=q=>({area:q.area,mode:'explore',c:q.c,r:q.r,alive:true,down:false,kills:q.kills,boss:!!q.boss});
test('cinco etapas e três finais: recompensas e transições irrepetíveis',()=>{
 for(const ending of Object.keys(Q.DATA.endings)){
  let state=Q.normalize({active:true}),gold=0;
  for(const q of Q.DATA.steps){
   const before=JSON.stringify(state),r=Q.advance(state,'main',evidence(q),ending);
   assert.equal(r.error,undefined);assert.equal(JSON.stringify(state),before);
   state=r.state;gold+=r.gold;
   assert.ok(Q.advance(state,'main',evidence(q),ending).error);
  }
  assert.equal(gold,90);assert.equal(state.completed,true);assert.equal(state.ending,ending);assert.equal(state.revision,5);
 }
});
test('objetivos exigem local, proximidade, consciência, exploração e guardiões',()=>{
 const state=Q.normalize({active:true,step:4}),q=Q.DATA.steps[4],e=evidence(q);
 for(const invalid of [{area:'vila'},{mode:'combat'},{alive:false},{down:true},{c:0},{c:6.5},{boss:false},{kills:NaN}])
  assert.ok(Q.advance(state,'main',{...e,...invalid},'selar').error);
 assert.ok(Q.advance(state,'main',e,'inexistente').error);
 assert.ok(Q.advance(Q.initial(),'main',e,'selar').error);
});
test('secundárias independentes não se repetem nem saltam a missão principal',()=>{
 let state=Q.normalize({active:true});
 for(const q of Q.DATA.side){
  assert.ok(Q.advance(state,q.id,evidence(q)).error);
  state.side[q.id]='active';const r=Q.advance(state,q.id,evidence(q));assert.equal(r.gold,q.gold);state=r.state;
  assert.ok(Q.advance(state,q.id,evidence(q)).error);assert.equal(state.step,0);
 }
});
