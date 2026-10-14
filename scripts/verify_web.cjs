// Verifikasi perhitungan dan interaksi pada model DOM. Bukan tes layout browser.
const fs=require('node:fs'), path=require('node:path'), vm=require('node:vm'), assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..'), html=fs.readFileSync(path.join(root,'index.html'),'utf8');
const raw=JSON.parse(html.match(/<script id="dataset" type="application\/json">([\s\S]*?)<\/script>/)[1]);
const A=require('./analytics.js'),all=A.enrich(raw),near=(a,b)=>assert.ok(Math.abs(a-b)<1e-9,`${a} != ${b}`);
assert.equal(all.length,38);assert.equal(new Set(all.map(r=>r.kabupaten_kota)).size,38);
const s=A.summary(all);assert.equal(s.sekolah,25521);assert.equal(s.guru,294886);assert.equal(s.murid,4282023);
near(s.ipm,76.06447368421051);near(s.rls,8.941315789473686);near(s.rasio,4282023/294886);near(A.corr(all),0.97963430749045);
const cities=A.filter(all,{type:'Kota',min:0,max:100});assert.equal(cities.length,9);near(A.summary(cities).ipm,82.42);
assert.equal(A.filter(all,{min:0,max:100,search:'  sUrAbAyA  '}).length,1);
assert.equal(A.filter(all,{min:90,max:100}).length,0);assert.equal(A.summary([]).rasio,null);
assert.equal(A.summary(all,'sd').murid,2488748);assert.equal(A.summary(all,'smp').guru,79928);assert.equal(A.summary(all,'sma').sekolah,1511);
assert.equal(A.corr(all.slice(0,2)),null);assert.equal(A.corr(all.map(r=>({...r,ipm:70}))),null);
assert.equal(A.measures({...all[0],guru_sd:0},'sd').rasio,null);
const csv=A.csv(cities,'sma');assert.equal(csv.split('\r\n').length,10);assert.ok(csv.includes('"sma"'));assert.ok(csv.startsWith('\ufeff'));
console.log('PASS: cakupan, total, rasio gabungan, korelasi, filter, jenjang, penyebut nol, CSV.');

class Element{
  constructor(id,tag='DIV'){this.id=id;this.tagName=tag;this.value='';this.hidden=false;this.disabled=false;this.innerHTML='';this.textContent='';this.dataset={};this.listeners={};this.attrs={};this.tabIndex=0;}
  addEventListener(event,fn){(this.listeners[event]??=[]).push(fn);}
  fire(event='change',data={}){const e={target:this,key:'',preventDefault(){},...data};for(const fn of this.listeners[event]??[])fn(e);}
  setAttribute(k,v){this.attrs[k]=v;}focus(){this.focused=true;}click(){this.fire('click');}remove(){}closest(){return null;}matches(){return false;}
}
const elements=new Map();for(const m of html.matchAll(/<([a-z]+)[^>]*\bid="([^"]+)"[^>]*>/g)) {assert.ok(!elements.has(m[2]),'duplicate id '+m[2]);elements.set(m[2],new Element(m[2],m[1].toUpperCase()));}
const get=id=>{assert.ok(elements.has(id),'missing '+id);return elements.get(id);};
for(const [id,v] of Object.entries({type:'semua',level:'semua',min:'0',max:'100',metric:'ipm','table-sort':'nama'}))get(id).value=v;
get('dataset').textContent=JSON.stringify(raw);
const tabs=new Element('tabs'),body=new Element('body');body.append=()=>{};body.classList={values:new Set(),toggle(k,v){if(v)this.values.add(k);else this.values.delete(k);}};
const tabButtons=[0,1,2,3].map(i=>{const e=get('tab-'+i);e.dataset.tab=String(i);return e;});
const document={getElementById:get,querySelectorAll:q=>q==='[data-tab]'?tabButtons:[],querySelector:q=>q==='.tabs'?tabs:null,body,addEventListener(){},createElement:tag=>new Element('',tag.toUpperCase())};
const sandbox={document,JatimAnalytics:A,Intl,Number,String,Math,JSON,console,Blob,URL:{createObjectURL:()=> 'blob:test',revokeObjectURL(){}},setTimeout:fn=>fn()};
vm.runInNewContext(fs.readFileSync(path.join(__dirname,'dashboard.js'),'utf8'),sandbox);
assert.ok(get('overview').innerHTML.includes('4.282.023'));assert.equal(get('pane-0').hidden,false);
get('type').value='Kota';get('type').fire();assert.ok(get('context').innerHTML.includes('<b>9</b>'));
get('level').value='sd';get('level').fire();assert.ok(get('overview').innerHTML.includes('SD'));
get('search').value='Tidak Ada Wilayah';get('search').fire('input');assert.equal(get('empty').hidden,false);assert.equal(get('download').disabled,true);
get('tab-2').click();assert.equal(get('empty').hidden,true);assert.equal(get('pane-2').hidden,false);assert.ok(get('comparison').innerHTML.includes('Kota Surabaya'));
get('compare-b').value='Kota Surabaya';get('compare-b').fire();assert.ok(get('comparison').innerHTML.includes('daerah yang sama'));
get('reset').click();assert.ok(get('context').innerHTML.includes('<b>38</b>'));assert.equal(get('level').value,'semua');
get('min').value='95';get('max').value='70';get('min').fire();assert.equal(Number(get('max').value),95);
get('max').value='-5';get('max').fire();assert.equal(Number(get('min').value),0);assert.equal(Number(get('max').value),0);
get('reset').click();get('demo').click();assert.equal(get('demo').attrs['aria-pressed'],'true');assert.ok(body.classList.values.has('presentation'));
get('tab-0').click();get('next').click();assert.equal(get('pane-1').hidden,false);get('prev').click();assert.equal(get('pane-0').hidden,false);
get('demo').click();assert.equal(get('demo').attrs['aria-pressed'],'false');
tabs.fire('keydown',{key:'End'});assert.equal(get('pane-3').hidden,false);assert.equal(get('tab-3').tabIndex,0);
get('download').click();
console.log('PASS: perubahan filter, hasil kosong, perbandingan independen, reset, rentang IPM, navigasi, presentasi, unduh.');
assert.ok(!/src="https?:|href="https?:[^>]*stylesheet/.test(html));
assert.ok(!html.includes('INLINE_DATA'));assert.ok(!html.includes('INLINE_CSS'));
console.log('PASS: index.html mandiri, tanpa aset eksternal wajib. Layout browser belum diuji.');
