const assert=require('node:assert/strict');
const {test}=require('node:test');
const fs=require('node:fs'),vm=require('node:vm');
const D=require('../public/direction-rules.js');
test('tensão tem limite e eventos não prolongam o efeito',()=>{
  let s=D.tension();for(let i=0;i<3;i++)s=D.expose(s,false);
  assert.deepEqual(s,{level:3,turns:2,grace:0});
  s=D.turnEnd(s);assert.equal(s.turns,1);
  for(let i=0;i<20;i++)s=D.expose(s,false);
  assert.equal(s.turns,1);s=D.turnEnd(s);
  assert.deepEqual(s,{level:1,turns:0,grace:2});
  assert.deepEqual(D.expose(s,false),s);
  s=D.turnEnd(D.turnEnd(s));assert.equal(D.expose(s,false).level,2);
});
test('resistir não aumenta tensão e respirar encerra penalidade',()=>{
  const s={level:2,turns:0,grace:0};assert.deepEqual(D.expose(s,true),s);
  assert.deepEqual(D.recover({level:3,turns:2}),{level:2,turns:0,grace:2});
  assert.equal(D.recover(D.tension()).level,0);
});
test('dados antigos, valores extremos e campos narrativos',()=>{
  assert.deepEqual(D.tension(),{level:0,turns:0,grace:0});
  assert.deepEqual(D.tension({level:999,turns:Infinity,grace:-2}),{level:3,turns:0,grace:0});
  const p=D.personality({quest:'a'.repeat(900),secret:'',status:'invalid',origin:4});
  assert.equal(p.quest.length,600);assert.equal(p.status,'pending');assert.equal(p.origin,'');
});
test('o script integrado pode ser analisado pelo JavaScript',()=>{
  const html=fs.readFileSync(require.resolve('../public/index.html'),'utf8');
  const scripts=[...html.matchAll(/<script>([\s\S]*?)<\/script>/g)];
  assert.equal(scripts.length,1);new vm.Script(scripts[0][1]);
});
