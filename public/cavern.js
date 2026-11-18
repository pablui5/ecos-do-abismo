(function(root){
'use strict';
// Decorative geology stays outside the tactical map. Its seed never consumes combat dice.
function build({THREE,scene,rockTexture,glowTexture}){
 let seed=0x5e10ab15;
 const random=()=>{seed=(Math.imul(seed,1664525)+1013904223)>>>0;return seed/4294967296;};
 const group=new THREE.Group();group.name='Caverna do Selo';scene.add(group);
 const walls=[],details=new THREE.Group(),ripples=[];details.name='Detalhes da caverna';group.add(details);
 const rock=new THREE.IcosahedronGeometry(1,2),positions=rock.getAttribute('position'),colors=[];
 for(let i=0;i<positions.count;i++){
  const x=positions.getX(i),y=positions.getY(i),z=positions.getZ(i);
  const r=1+.12*Math.sin(x*9+y*4)*Math.cos(z*7)+.06*Math.sin(y*17+z*3);
  positions.setXYZ(i,x*r,y*r,z*r);
  const shade=.70+.14*Math.sin(y*19+x*3)+.06*Math.cos(z*11);
  colors.push(shade,shade*.97,shade*.9);
 }
 rock.setAttribute('color',new THREE.Float32BufferAttribute(colors,3));rock.computeVertexNormals();
 const matrix=new THREE.Object3D();
 const stoneMaterial=()=>new THREE.MeshStandardMaterial({map:rockTexture,color:0x8a8c83,vertexColors:true,roughness:.77,metalness:.06,transparent:true});
 const instances=(parent,geometry,material,transforms,name)=>{
  const mesh=new THREE.InstancedMesh(geometry,material,transforms.length);mesh.name=name;
  transforms.forEach((t,i)=>{matrix.position.set(...t.p);matrix.scale.set(...t.s);matrix.rotation.set(...(t.r||[0,0,0]));matrix.updateMatrix();mesh.setMatrixAt(i,matrix.matrix);});
  mesh.instanceMatrix.needsUpdate=true;mesh.receiveShadow=true;
  // r128 cannot cull individual instances; the bounds of the template are insufficient.
  mesh.frustumCulled=false;parent.add(mesh);return mesh;
 };
 const spike=new THREE.CylinderGeometry(.015,1,1,9,7),sp=spike.getAttribute('position');
 for(let i=0;i<sp.count;i++){
  const x=sp.getX(i),y=sp.getY(i),z=sp.getZ(i),r=1+.12*Math.sin(y*27+x*5+z*3);
  sp.setXYZ(i,x*r+.06*Math.sin(y*4),y,z*r);
 }
 spike.computeVertexNormals();
 for(const side of [-1,1]){
  const wall=new THREE.Group();wall.position.set(side*15,0,-2);group.add(wall);
  const mat=stoneMaterial(),blocks=[],teeth=[];
  for(let row=0;row<6;row++)for(let col=0;col<12;col++){
   blocks.push({p:[side*(random()*2.2),-21+row*6.1+random(),-25+col*4.2],s:[3.1+random(),4.5+random()*2,3.5+random()],r:[random()*.3,random()*.8,side*(random()-.5)*.22]});
  }
  for(let i=0;i<24;i++){
   const length=1.4+random()*4.2;
   teeth.push({p:[-side*(3+random()*1.5),i%2?8+length/2:-4-length/2,-22+i*1.9],s:[.22+random()*.45,length,.26+random()*.5],r:[i%2?Math.PI:0,random()*3,.12*(random()-.5)]});
  }
  instances(wall,rock,mat,blocks,'Parede estratificada');instances(wall,spike,mat,teeth,'Estalactites e estalagmites');
  wall.userData.normal=new THREE.Vector3(-side,0,0);wall.userData.mats=[mat];wall.userData.fadeOpacity=.025;walls.push(wall);
 }
 const back=new THREE.Group();back.position.set(0,0,-29);group.add(back);
 const backMat=stoneMaterial(),backBlocks=[];
 for(let row=0;row<5;row++)for(let col=0;col<9;col++)backBlocks.push({p:[-20+col*5,-16+row*7,random()*2],s:[4.2,5+random()*2,3+random()],r:[.1,random()*.4,0]});
 instances(back,rock,backMat,backBlocks,'Fundo da gruta');back.userData.normal=new THREE.Vector3(0,0,1);back.userData.mats=[backMat];back.userData.fadeOpacity=.025;walls.push(back);
 const stone=stoneMaterial(),rubble=[],outcrops=[];
 for(const side of [-1,1]){
  for(let i=0;i<18;i++)rubble.push({p:[side*(8.65+random()*.4),.06,5.6+i*.55],s:[.15+random()*.18,.08+random()*.12,.18+random()*.2],r:[0,random()*6,0]});
  for(let i=0;i<7;i++)outcrops.push({p:[side*(10.4+random()),-.6+random()*.4,5.5+i*1.6],s:[1.25,1.2+random(),1.1],r:[random()*.2,random(),random()*.2]});
 }
 instances(details,rock,stone,rubble,'Cascalho nas bordas');instances(group,rock,stone,outcrops,'Rocha envolvendo a cripta');
 const foundation=[];
 for(let layer=0;layer<4;layer++)for(let i=0;i<7;i++)foundation.push({p:[(i-3)*(2.1-layer*.24),-3.5-layer*2.8,10.4+(i%2?-.8:.8)],s:[1.8-layer*.15,2.3,4.7-layer*.7],r:[.07*(random()-.5),random()*.2,random()*.15]});
 instances(group,rock,stone,foundation,'Fundação rochosa da cripta');
 const cracks=[];
 for(let i=0;i<16;i++){
  let x=-7+random()*14,z=6+random()*8.5;
  for(let j=0;j<4;j++){const nx=x+(random()-.5)*.45,nz=z+random()*.27;cracks.push(x,.019,z,nx,.019,nz);x=nx;z=nz;}
 }
 const crackGeo=new THREE.BufferGeometry();crackGeo.setAttribute('position',new THREE.Float32BufferAttribute(cracks,3));
 details.add(new THREE.LineSegments(crackGeo,new THREE.LineBasicMaterial({color:0x17201c,transparent:true,opacity:.65})));
 const stainMat=new THREE.MeshStandardMaterial({color:0x2b3527,roughness:.98,transparent:true,opacity:.28,depthWrite:false});
 const stains=[];for(let i=0;i<16;i++)stains.push({p:[(i%2?-1:1)*(5.8+random()),.014,6+random()*9],s:[.3+random()*.5,.15+random()*.2,1],r:[-Math.PI/2,0,random()*3]});
 instances(details,new THREE.CircleGeometry(1,12),stainMat,stains,'Umidade e musgo entre as lajes');
 const wet=new THREE.MeshStandardMaterial({color:0x263836,roughness:.14,metalness:.35,transparent:true,opacity:.64,depthWrite:false});
 const outline=new THREE.Shape();
 for(let i=0;i<=32;i++){const a=i*Math.PI/16,r=.84+.10*Math.sin(a*3)+.06*Math.cos(a*7),x=Math.cos(a)*r,y=Math.sin(a)*r;if(!i)outline.moveTo(x,y);else outline.lineTo(x,y);}
 const poolGeo=new THREE.ShapeGeometry(outline,24);
 for(const [x,z,sx,sz] of [[-5.1,13.6,1.15,.45],[4.9,9.5,.9,.5],[-1.7,6.4,.65,.3],[1.1,-3,.65,.3]]){
  const pool=new THREE.Mesh(poolGeo,wet);pool.rotation.x=-Math.PI/2;pool.position.set(x,.017,z);pool.scale.set(sx,sz,1);group.add(pool);
  const ring=new THREE.Mesh(new THREE.RingGeometry(.15,.165,24),new THREE.MeshBasicMaterial({color:0x7d9a9c,transparent:true,opacity:.12,depthWrite:false,side:THREE.DoubleSide}));
  ring.rotation.x=-Math.PI/2;ring.position.set(x,.022,z);ring.userData.phase=random();details.add(ring);ripples.push(ring);
 }
 // Mineral seams are deliberately dim: they frame the abyss without lighting the board blue.
 const mineral=new THREE.MeshStandardMaterial({color:0x8a9e92,emissive:0x284b43,emissiveIntensity:.3,roughness:.42,metalness:.12});
 const veins=[];
 for(const side of [-1,1])for(let i=0;i<10;i++)veins.push({p:[side*(11.2+random()),-2-random()*9,4-i*2.3],s:[.07,.45+random()*.8,.09],r:[0,random()*3,side*.4]});
 instances(details,spike,mineral,veins,'Veios minerais');
 // An abandoned expedition: broken wheels, a lantern and a rope at the inaccessible edge.
 const wood=new THREE.MeshStandardMaterial({color:0x493a2c,roughness:.96}),iron=new THREE.MeshStandardMaterial({color:0x615d50,roughness:.65,metalness:.65});
 const camp=new THREE.Group();camp.position.set(-9.1,.05,13.2);group.add(camp);
 for(let i=0;i<4;i++){const plank=new THREE.Mesh(new THREE.BoxGeometry(.09,.08,.85),wood);plank.position.set((i-1.5)*.13,.08,i*.05);plank.rotation.y=.25;camp.add(plank);}
 const wheel=new THREE.Mesh(new THREE.TorusGeometry(.34,.045,7,18,Math.PI*1.55),iron);wheel.rotation.set(.4,.2,.6);wheel.position.set(.04,.35,-.2);camp.add(wheel);
 const lamp=new THREE.Mesh(new THREE.CylinderGeometry(.1,.13,.28,8),iron);lamp.position.set(.25,.16,.8);camp.add(lamp);
 const glow=new THREE.Sprite(new THREE.SpriteMaterial({map:glowTexture,color:0xf3b46b,transparent:true,opacity:.55,depthWrite:false}));glow.position.set(.25,.26,.8);glow.scale.set(.5,.5,1);camp.add(glow);
 const ropePoints=[new THREE.Vector3(-8.6,.12,6),new THREE.Vector3(-9.3,-.4,5.6),new THREE.Vector3(-9.8,-2.2,5.3),new THREE.Vector3(-9.5,-5.6,5.1)];
 details.add(new THREE.Mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3(ropePoints),16,.035,5,false),wood));
 return {group,walls,details,ripples};
}
const api={build};if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.EcosCavern=api;
})(typeof globalThis!=='undefined'?globalThis:this);
