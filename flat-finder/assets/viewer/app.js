'use strict';
let state, map, markers, demo = false, staticDemo = false;
const $ = id => document.getElementById(id);
const prompt = 'Use $flat-finder to continue my saved rental search. Read my profile and contact history, search the matching areas, verify current source posts and availability, and show a clickable shortlist with costs, exact pins, walking-route gaps and next actions. Do not repeat sent, closed or held enquiries.';
function el(tag, cls, text) { const n = document.createElement(tag); if (cls) n.className = cls; if (text != null) n.textContent = String(text); return n; }
function add(parent, ...children) { children.forEach(c => { if(c) parent.append(c); }); return parent; }
function link(label, url, cls = '') { try { const u = new URL(url); if(u.protocol !== 'https:' || u.username || u.password) return el('span', cls, label); } catch { return el('span',cls,label); } const a=el('a',cls,label); a.href=url; a.target='_blank'; a.rel='noopener noreferrer'; return a; }
function money(n) { if(n == null) return 'Not confirmed'; try { return new Intl.NumberFormat('en-IN', {style:'currency',currency:state.profile.currency,maximumFractionDigits:0}).format(n); } catch {return `${state.profile.currency} ${n}`;} }
function date(s) { if(!s) return 'Not checked'; const d=new Date(s); return Number.isNaN(d.valueOf())?'Not checked':d.toLocaleString(undefined,{dateStyle:'medium',timeStyle:'short',timeZone:state.profile.timezone}); }
function stamp(s) { return s ? date(s) : 'Not checked'; }
function kind(s) { return ({entire_flat:'ENTIRE FLAT',female_room:'FEMALE ROOM',male_room:'MALE ROOM',private_room:'PRIVATE ROOM'})[s] || s; }
function badge(a) { return el('span',`badge ${a.state}`,({ready:'Evidence complete',provisional:'Needs verification',excluded:'Outside saved criteria',held:'Held · do not contact',closed:'Closed · do not contact'})[a.state]); }
function notify(s){ $('toast').textContent=s;$('toast').classList.remove('hidden');setTimeout(()=>$('toast').classList.add('hidden'),3000); }
async function copy(){try{await navigator.clipboard.writeText(prompt);notify('Prompt copied. Paste it into Codex.');}catch{notify('Copy the prompt from “Use in Codex”.');}}
async function load() {
  $('refresh').disabled=true;
  try {
    try { const r=await fetch('api/state',{cache:'no-store'}); if(!r.ok)throw Error(); state=await r.json(); }
    catch { const r=await fetch('demo-state.json',{cache:'no-store'}); if(!r.ok)throw Error(); state=await r.json();staticDemo=true; }
    if(!state.profile || !Array.isArray(state.listings)) throw Error();
    demo=state.profile.demo;
    renderProfile(); renderResearch(); renderListings(); renderMap();
    $('checked-at').textContent=`View assessed ${date(state.generated_at)} · source checks shown per listing`;
    if(demo){$('notice').textContent='SYNTHETIC DEMO — These properties and prices are examples, not real offers. Install the skill to research your own area.';$('notice').classList.remove('hidden');}
  }catch{ $('notice').textContent='Could not load a valid workspace. Check the local Codex server, then refresh. No search or message was sent.';$('notice').classList.remove('hidden'); }
  finally{$('refresh').disabled=false;}
}
function fact(label,value){return add(el('div'),el('span','muted',label),el('strong','',value));}
function renderProfile(){
  const p=state.profile;$('profile-name').textContent=p.name;$('profile-city').textContent=p.city;$('city-top').textContent=p.city;
  $('mode-label').textContent=demo?'Synthetic demo':'Private local workspace';$('total-pill').textContent=state.listings.length;
  $('profile-facts').replaceChildren(fact('Monthly cap',`${p.strict_monthly_limit?'Below':'Up to'} ${money(p.monthly_limit)}`),fact('Move in before',p.move_in_before),fact('Preferred radius',`${p.prefer_radius_m/1000} km`),fact('Maximum radius',`${p.max_radius_m/1000} km`));
  $('anchors').replaceChildren(...p.anchors.map(a=>add(el('div','anchor'),a.source_url?link(a.name+' ↗',a.source_url):el('span','',a.name),el('small','',a.verified?'Map point verified':'Map point unverified'))),...p.unverified_anchors.map(a=>add(el('div','anchor'),el('small','',a))));
  const c=state.counts;$('stats').replaceChildren(...[[c.ready,'Evidence complete'],[c.provisional,'Need verification'],[state.listings.filter(x=>x.contact.status==='sent'||x.contact.status==='delivered'||x.contact.status==='read').length,'Awaiting reply'],[c.held+c.closed+c.excluded,'Held / closed / excluded']].map(([n,s])=>add(el('div','stat'),el('strong','',n),el('span','',s))));
  $('prompt-text').textContent=prompt;
  if(demo && staticDemo){$('download-skill').classList.remove('hidden');$('copy-prompt').classList.add('hidden');}
}
function filtered(){
 const query=$('search').value.toLowerCase(),k=$('kind').value,s=$('status').value;
 const rows=state.listings.filter(x=> (k==='all'||(k==='room'?x.kind!=='entire_flat':x.kind===k)) && (s==='all'||(s==='active'?['ready','provisional'].includes(x.assessment.state):x.assessment.state===s)) && [x.title,x.area,x.notes].join(' ').toLowerCase().includes(query));
 if($('sort').value==='cost')rows.sort((a,b)=>(a.assessment.monthly_total??Infinity)-(b.assessment.monthly_total??Infinity));
 if($('sort').value==='distance')rows.sort((a,b)=>(a.assessment.radius_m??Infinity)-(b.assessment.radius_m??Infinity));
 return rows;
}
function renderListings(){
 const rows=filtered();$('visible-count').textContent=`${rows.length} shown · ${state.listings.length} saved`;$('empty').classList.toggle('hidden',!!rows.length);
 $('listing-list').replaceChildren(...rows.map(x=>{
   const a=x.assessment,card=el('article','listing');
   const title=add(el('div'),el('span','kind-tag',kind(x.kind)),add(el('div','listing-name'),link(x.title,x.source_url)),el('div','listing-meta',`${x.area} · ${x.source_platform}`));
   const cost=add(el('div'),add(el('div','cost'),el('span','',money(a.monthly_total)),el('small','',' / mo')),el('div','secondary','Rent + maintenance'),el('div','secondary',`Deposit ${money(x.deposit)}`));
   const status=add(el('div'),badge(a),el('div','state-note',a.radius_m==null?'Property point not verified':`${a.radius_m.toLocaleString()} m radius · walk ${x.walk?.status==='verified'&&x.walk?.exact_entrance?'recorded; see evidence':'unverified'}`),el('div','state-note',`Contact: ${x.contact.status}${x.contact.status==='none'?' yet':''}`));
   const open=el('button','details-btn','↗');open.setAttribute('aria-label',`View details for ${x.title}`);open.onclick=()=>detail(x);
   return add(card,title,cost,status,open);
 }));
 if(markers)drawMarkers(rows);
}
function detail(x){
 const a=x.assessment,c=x.contact,body=$('detail-content'),p=state.profile;
 body.replaceChildren(el('p','eyebrow',kind(x.kind)),el('h2','',x.title),el('p','muted',x.area),badge(a));
 const dl=el('dl');for(const [k,v] of [['Monthly rent',money(x.rent)],['Maintenance',x.maintenance_included?'Included in stated rent':money(x.maintenance)],['Rent + maintenance',money(a.monthly_total)],['Deposit',money(x.deposit)],['Brokerage',money(x.brokerage)],['Setup cost',money(x.setup_cost)],['Furnishing',x.furnishing],['Advertised availability',x.advertised_availability],['Source last checked',stamp(x.source_checked_at)],['Provider availability',x.availability.status],['Availability confirmation',stamp(x.availability.confirmed_at)],['Point precision',x.coordinates?.precision||'Not verified']])add(dl,el('dt','',k),el('dd','',v));body.append(dl);
 add(body,el('h3','','Commute evidence'),el('p','',a.radius_m==null?'No verified radius measurement.':`${a.radius_m} m in a straight line to ${a.nearest_anchor}. This is not walking distance.`));
 if(x.walk)add(body,el('p','',`${x.walk.metres??'?'} m / ${x.walk.minutes??'?'} min — ${x.walk.status}; ${x.walk.exact_entrance?'actual entrance checked':'actual entrance not checked'}. ${x.walk.restriction_note}`));
 add(body,el('h3','','What still needs checking'));const ul=el('ul');[...a.reasons,...a.gaps].forEach(t=>ul.append(el('li','',t)));body.append(ul);
 add(body,el('h3','','Conversation state'),el('p','',`${c.status.toUpperCase()}. ${a.next_action}.`));
 if(c.phone)add(body,el('p','',`Published contact: ${c.phone}. Role: ${c.role}. ${c.recipient_verified?'Recipient identity recorded as verified.':'Recipient identity is NOT verified.'}`));
 if(c.evidence_note)add(body,el('p','',c.evidence_note));
 if(x.notes)add(body,el('h3','','Source notes'),el('p','',x.notes));
 const links=el('div','detail-links');add(links,link(demo?'Example source (not a real offer) ↗':'Open source ↗',x.source_url,'button dark'));
 if(x.coordinates?.source_url)add(links,link('Property pin ↗',x.coordinates.source_url,'button subtle'));
 if(x.walk?.source_url)add(links,link('Route evidence ↗',x.walk.source_url,'button subtle'));
 if(c.provenance_url)add(links,link('Contact provenance ↗',c.provenance_url,'button subtle'));
 // No automatic outreach or wa.me links: exact live account/history checks happen
 // in Codex under the user's existing authority, outside this read-only viewer.
 body.append(links);$('details').showModal();
}
function renderMap(){
 if(!window.L){$('map-fallback').classList.remove('hidden');return;}
 if(!map){map=L.map('map',{scrollWheelZoom:false});L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'}).addTo(map);markers=L.layerGroup().addTo(map);}
 drawMarkers(filtered());
 const points=[...state.profile.anchors.filter(a=>a.verified),...state.listings.filter(x=>x.coordinates).map(x=>x.coordinates)];
 if(points.length)map.fitBounds(points.map(p=>[p.lat,p.lng]),{padding:[48,48],maxZoom:15});else map.setView([20,0],2);
}
function drawMarkers(rows){
 markers.clearLayers();
 state.profile.anchors.filter(a=>a.verified).forEach(a=>{
  L.circle([a.lat,a.lng],{radius:state.profile.max_radius_m,color:'#607a57',weight:1,fillOpacity:.025}).addTo(markers);
  L.circle([a.lat,a.lng],{radius:state.profile.prefer_radius_m,color:'#607a57',weight:1,dashArray:'4 6',fillOpacity:.035}).addTo(markers);
  const label=el('span','',a.name);L.circleMarker([a.lat,a.lng],{radius:8,color:'#fff',weight:2,fillColor:'#142821',fillOpacity:1}).bindTooltip(label).addTo(markers);
 });
 rows.filter(x=>x.coordinates).forEach(x=>{
  const a=x.assessment,label=el('span','',`${x.title} · ${money(a.monthly_total)}`);
  const marker=L.circleMarker([x.coordinates.lat,x.coordinates.lng],{radius:7,color:'#fff',weight:2,fillColor:['held','closed','excluded'].includes(a.state)?'#9a9286':'#428459',fillOpacity:1}).bindTooltip(label).on('click',()=>detail(x));marker.addTo(markers);
 });
}
function renderResearch(){
 $('access-list').replaceChildren(...(state.access.length?state.access.map(a=>add(el('article','log-entry'),el('h3','',`${a.channel} · ${a.state}`),el('p','',a.detail),el('time','',stamp(a.checked_at)))):[el('p','muted','Access has not been checked by this workspace.')]));
 $('events').replaceChildren(...(state.events.length?state.events.map(e=>add(el('article','log-entry'),el('time','',stamp(e.at)),el('h3','',e.title),el('p','',e.detail),e.source_url?link('Evidence ↗',e.source_url):null)):[el('p','muted','No research entries have been imported yet.')]));
}
for(const id of ['search','kind','status','sort'])$(id).addEventListener(id==='search'?'input':'change',()=>{if(state)renderListings();});
document.querySelectorAll('[data-view]').forEach(b=>b.onclick=()=>{document.querySelectorAll('[data-view]').forEach(n=>n.classList.toggle('active',n===b));document.querySelectorAll('.view').forEach(v=>v.classList.toggle('hidden',v.id!==b.dataset.view+'-view'));if(map&&b.dataset.view==='shortlist')map.invalidateSize();});
$('refresh').onclick=load;$('copy-prompt').onclick=copy;$('guide-copy').onclick=copy;$('close-detail').onclick=()=>$('details').close();
load();
