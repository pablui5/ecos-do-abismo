(function(root){
'use strict';
const DATA = {"id":"nomes","title":"O Selo dos Nomes","intro":"O sino de Valdenegro toca com vozes de pessoas desaparecidas. A Irmã Alina acredita que o Arauto está apagando seus nomes para romper o selo. Encontre o registro dos vivos, reacenda a lanterna da vigília, recupere a chave do castelo e decida o destino da cripta.","steps":[{"id":"registro","area":"vila","title":"Os nomes que restaram","objective":"Leia o registro deixado diante da casa da escriba.","c":4,"r":18,"kills":0,"gold":5,"dialogue":"Alina: Não procure apenas os mortos. O Arauto se alimenta de quem foi esquecido. Leve estes nomes ao sino e escute a resposta."},{"id":"sino","area":"vila","title":"O sino sem voz","objective":"Derrote pelo menos dois invasores e examine o sino partido.","c":6,"r":8,"kills":2,"gold":10,"dialogue":"O bronze está frio. Uma voz indica o caminho da floresta: a lanterna dos vigias ainda guarda uma chama capaz de revelar o selo."},{"id":"lanterna","area":"floresta","title":"A última chama","objective":"Derrote dois guardiões e recupere a lanterna entre as raízes.","c":6,"r":8,"kills":2,"gold":15,"dialogue":"As raízes recuam. Dentro da lanterna, uma chama branca revela a silhueta de um castelo. A chave foi levada pelo último guardião da muralha."},{"id":"chave","area":"castelo","title":"O juramento quebrado","objective":"Derrote três sentinelas e abra o relicário do castelo.","c":6,"r":8,"kills":3,"gold":20,"dialogue":"No relicário, uma chave e uma confissão: o selo prende também as almas da vila. Destruir o Arauto não decidirá o destino delas. Essa escolha será de vocês."},{"id":"selo","area":"cripta","title":"O preço de lembrar","objective":"Derrote o Arauto, aproxime-se do altar e escolha o destino do selo.","c":6,"r":2,"kills":0,"boss":true,"gold":40,"dialogue":"Os nomes retornam às paredes. A chave pode fechar a passagem, libertar os ecos ou manter a vigília. O Mestre conduz a decisão do grupo."}],"side":[{"id":"memoria","area":"vila","title":"Nenhum nome esquecido","objective":"Recupere os nomes no memorial após vencer dois invasores.","c":3,"r":5,"kills":2,"gold":10,"dialogue":"As lápides recuperam seus nomes. Uma família agradece em silêncio."},{"id":"peregrino","area":"floresta","title":"Luz para o peregrino","objective":"Reacenda o marco do caminho na floresta.","c":9,"r":14,"kills":0,"gold":15,"dialogue":"A chama mostra uma trilha segura. O peregrino consegue voltar à vila."},{"id":"estandarte","area":"castelo","title":"A promessa da guarda","objective":"Depois de vencer três sentinelas, recupere o estandarte da torre.","c":3,"r":5,"kills":3,"gold":20,"dialogue":"O estandarte é erguido uma última vez. A guarda abandona seu posto e encontra descanso."}],"endings":{"selar":{"title":"O silêncio protegido","text":"O grupo fecha a passagem. A vila está segura, mas os ecos permanecem guardados na pedra. Seus nomes nunca mais serão esquecidos."},"libertar":{"title":"Os nomes livres","text":"As almas atravessam a luz da lanterna. O selo perde sua força e o grupo assume a responsabilidade de vigiar a passagem que ficou aberta."},"vigiar":{"title":"A vigília dos vivos","text":"O grupo mantém o selo e promete voltar. Um novo juramento protege a vila, agora sustentado pela memória dos vivos."}}};
function initial(){return {active:false,step:0,completed:false,ending:null,side:{},journal:[],revision:0};}
function normalize(value){
 const s=initial();if(!value||typeof value!=='object')return s;
 s.active=value.active===true;s.step=Number.isInteger(value.step)?Math.max(0,Math.min(DATA.steps.length,value.step)):0;
 s.completed=value.completed===true&&s.step===DATA.steps.length;s.ending=Object.hasOwn(DATA.endings,value.ending)?value.ending:null;
 s.side=Object.fromEntries(DATA.side.map(q=>[q.id,['active','completed'].includes(value.side?.[q.id])?value.side[q.id]:'available']));
 s.journal=Array.isArray(value.journal)?value.journal.filter(x=>typeof x==='string').slice(-30):[];s.revision=Number.isInteger(value.revision)?Math.max(0,value.revision):0;return s;
}
function objective(state,id){return id==='main'?DATA.steps[state.step]:DATA.side.find(q=>q.id===id);}
function eligibility(state,id,e){
 if(!state.active)return 'Comece a campanha no diário.';
 const q=objective(state,id);if(!q||state.completed&&id==='main'||id!=='main'&&state.side[id]!=='active')return 'Esta missão não está ativa.';
 if(e.area!==q.area)return 'Viaje para o local indicado no diário.';
 if(e.mode!=='explore')return 'Conclua o combate antes de interagir.';
 if(!e.alive||e.down)return 'O protagonista precisa estar consciente.';
 if(!Number.isInteger(e.c)||!Number.isInteger(e.r)||Math.max(Math.abs(e.c-q.c),Math.abs(e.r-q.r))>1)return 'Aproxime-se do objetivo (até uma casa).';
 if(!Number.isFinite(e.kills)||e.kills<q.kills)return `Derrote ${q.kills} inimigos neste cenário.`;
 if(q.boss&&!e.boss)return 'O Arauto ainda protege o altar.';return '';
}
function advance(state,id,e,ending){
 const s=normalize(state),error=eligibility(s,id,e);if(error)return {error};
 const q=objective(s,id);if(q.boss&&!Object.hasOwn(DATA.endings,ending))return {error:'O Mestre precisa escolher o destino do selo.'};
 s.journal.push(q.title+': '+q.dialogue);s.revision++;
 if(id==='main'){s.step++;s.completed=s.step===DATA.steps.length;if(s.completed){s.ending=ending;s.journal.push(DATA.endings[ending].text);}}
 else s.side[id]='completed';
 return {state:s,gold:q.gold,title:q.title};
}
const api={DATA,initial,normalize,objective,eligibility,advance};if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.EcosCampaign=api;
})(typeof globalThis!=='undefined'?globalThis:this);
