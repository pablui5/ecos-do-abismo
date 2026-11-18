// Exercise the actual scene builders with the game's Three.js version, without a GPU.
const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path'),assert=require('node:assert/strict');
if(!process.argv[2])throw new Error('Informe o Three.js r128 local (.cjs).');
const THREE=require(path.resolve(process.argv[2])),Q=require('../public/campaign.js');
let code=fs.readFileSync(path.join(__dirname,'../public/index.html'),'utf8').match(/<script>([\s\S]*?)<\/script>/)[1];
code=code.replace('boot();',`
 for(const key of ['skin','cloth','leather','metal','chain','bone','fur','floor','floorE','rock','wall','glow','ring','shaft','membrane','spider','rune','runeE','web'])TX[key]=new THREE.Texture();
 scene=new THREE.Scene();scene.background=new THREE.Color();scene.fog=new THREE.FogExp2();
 globalThis.probe={rebuildRegion,regionMap,REGIONS,G,W3,scene,walk0};
`);
const ctx={THREE,window:{EcosDirection:require('../public/direction-rules.js'),EcosCampaign:Q,EcosCavern:require('../public/cavern.js')},document:{hidden:false,documentElement:{dataset:{}}},localStorage:{getItem:()=>null},matchMedia:()=>({matches:false}),performance:{now:()=>0},setTimeout:()=>0,setInterval:()=>0,requestAnimationFrame:()=>0,console,URL,Blob};
vm.createContext(ctx);vm.runInContext(code,ctx);
const {rebuildRegion,REGIONS,scene,walk0,W3}=ctx.probe;
let sizes={};
for(let pass=0;pass<3;pass++)for(const area of Object.keys(REGIONS)){
 const previous=[...scene.children];
 rebuildRegion(area);scene.updateMatrixWorld(true);
 scene.traverse(o=>{
  assert.ok(o.matrixWorld.elements.every(Number.isFinite),area);
  if(o.isInstancedMesh)assert.ok(o.instanceMatrix.array.every(Number.isFinite),area+' instance');
  if(o.name==='Fundação rochosa da cripta'){
   const matrix=new THREE.Matrix4(),point=new THREE.Vector3(),positions=o.geometry.getAttribute('position');
   for(let i=0;i<o.count;i++){o.getMatrixAt(i,matrix);for(let j=0;j<positions.count;j++)assert.ok(point.fromBufferAttribute(positions,j).applyMatrix4(matrix).y<-.05,'Foundation must not protrude through the floor');}
  }
 });
 assert.ok(previous.every(o=>o.parent===null),'Travel must detach the previous world');
 assert.equal(scene.children.length,W3.worldNodes.length,'Only the current world remains');sizes[area]=scene.children.length;
 assert.equal(W3.highlights.length,260);
 const reached=new Set(['5,21']),queue=[[5,21]];
 for(let i=0;i<queue.length;i++){const[c,r]=queue[i];for(const[dc,dr]of[[1,0],[-1,0],[0,1],[0,-1]]){const x=c+dc,y=r+dr,k=x+','+y;if(walk0(x,y)&&!reached.has(k)){reached.add(k);queue.push([x,y]);}}}
 for(const q of [...Q.DATA.steps,...Q.DATA.side].filter(q=>q.area===area))assert.ok(reached.has(q.c+','+q.r),area+' inaccessible quest '+q.id);
 for(const[k,c,r]of REGIONS[area].foes)assert.ok(reached.has(c+','+r),area+' inaccessible enemy '+k);
}
console.log(JSON.stringify({travelPasses:3,regions:4,finiteTransforms:true,reachableObjectives:8,worldNodes:sizes}));
