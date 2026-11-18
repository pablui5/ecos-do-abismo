/* Regras sem DOM: as preferências sensoriais nunca alteram a dificuldade. */
(function(root){
  'use strict';
  const integer = (n, min, max, fallback=min) => Number.isFinite(Number(n)) ? Math.max(min, Math.min(max, Math.floor(Number(n)))) : fallback;
  const fields = {origin:'Origem', motivation:'Motivação', fear:'Medo pessoal', bonds:'Vínculos', secret:'Segredo (compartilhado com a mesa)', quest:'Proposta de missão pessoal'};
  function personality(value={}){
    value=value && typeof value==='object'?value:{};
    const out = {};
    for (const key of Object.keys(fields)) out[key] = typeof value[key] === 'string' ? value[key].trim().slice(0, 600) : '';
    out.status = ['pending','approved','completed'].includes(value.status) ? value.status : 'pending';
    return out;
  }
  function tension(value={}){ value=value && typeof value==='object'?value:{}; return {level:integer(value.level,0,3), turns:integer(value.turns,0,2), grace:integer(value.grace,0,2)}; }
  function expose(value, success){
    const s = tension(value);
    // Não renova um efeito em andamento; há dois turnos de proteção depois dele.
    if (success || s.turns || s.grace) return s;
    s.level = Math.min(3, s.level + 1);
    if (s.level === 3) s.turns = 2;
    return s;
  }
  function recover(value){ const s=tension(value); return {level:Math.max(0,s.level-1), turns:0, grace:2}; }
  function turnEnd(value){
    const s=tension(value);
    if (s.turns){ s.turns--; if (!s.turns){ s.level=1; s.grace=2; } }
    else if (s.grace) s.grace--;
    return s;
  }
  const api = {integer,fields,personality,tension,expose,recover,turnEnd};
  if (typeof module !== 'undefined' && module.exports) module.exports=api;
  else root.EcosDirection=api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
