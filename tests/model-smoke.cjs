const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const path=require('node:path');
if(!process.argv[2])throw new Error('Informe o caminho local do Three.js r128 (.cjs).');
const THREE=require(path.resolve(process.argv[2]));
let code=fs.readFileSync(path.join(__dirname,'../public/index.html'),'utf8').match(/<script>([\s\S]*?)<\/script>/)[1];
code=code.replace('boot();','for(const key of ["skin","cloth","leather","metal","chain","bone","fur"])TX[key]=new THREE.Texture();globalThis.probe={buildHumanoid,heroModelOpts,defaultParty,WEAPON_LIST,animateUnit,SET};');
const ctx={THREE,window:{EcosDirection:require('../public/direction-rules.js'),EcosCampaign:require('../public/campaign.js')},document:{hidden:false},localStorage:{getItem:()=>null},matchMedia:()=>({matches:false}),performance:{now:()=>0},setTimeout:()=>0,setInterval:()=>0,requestAnimationFrame:()=>0,console,URL,Blob};
vm.createContext(ctx);vm.runInContext(code,ctx);
const {probe}=ctx;let models=0,maxGap=0;let worst=[];
for(const def of probe.defaultParty())for(const weapon of probe.WEAPON_LIST){
  const m=probe.buildHumanoid(probe.heroModelOpts(def,weapon,null));
  const u={m,phase:0,kindKey:'hero',side:'hero',anim:{name:'idle',t:0},conds:{}};
  for(const name of ['idle','walk','attack','cast','guard','hit','death','thrust','shoot','swap','interact']){
    u.anim={name,t:0};
    for(let i=0;i<30;i++)probe.animateUnit(u,1/60,i/60);
    m.root.updateMatrixWorld(true);
    m.root.traverse(o=>assert.ok(o.matrixWorld.elements.every(Number.isFinite),`${weapon.id} ${name}`));
    if(m.J.supportGrip&&!['death','interact'].includes(name)){
      const gap=m.J.handL.getWorldPosition(new THREE.Vector3()).distanceTo(m.J.supportGrip.getWorldPosition(new THREE.Vector3()));
      if(gap>maxGap){maxGap=gap;worst=[def.cls,weapon.id,name,gap];}
    }
  }
  m.root.traverse(o=>{o.geometry?.dispose();if(o.material)o.material.dispose();});models++;
}
assert.ok(maxGap<1e-5,'A mão de apoio deve alcançar o ponto do cabo.');
console.log(JSON.stringify({models,finiteTransforms:true,maxSupportHandGap:maxGap,worst}));
