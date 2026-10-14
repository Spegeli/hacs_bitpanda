var Se=globalThis,Ce=Se.ShadowRoot&&(Se.ShadyCSS===void 0||Se.ShadyCSS.nativeShadow)&&"adoptedStyleSheets"in Document.prototype&&"replace"in CSSStyleSheet.prototype,ht=Symbol(),Bt=new WeakMap,he=class{constructor(e,t,s){if(this._$cssResult$=!0,s!==ht)throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");this.cssText=e,this.t=t}get styleSheet(){let e=this.o,t=this.t;if(Ce&&e===void 0){let s=t!==void 0&&t.length===1;s&&(e=Bt.get(t)),e===void 0&&((this.o=e=new CSSStyleSheet).replaceSync(this.cssText),s&&Bt.set(t,e))}return e}toString(){return this.cssText}},Ft=o=>new he(typeof o=="string"?o:o+"",void 0,ht),me=(o,...e)=>{let t=o.length===1?o[0]:e.reduce((s,n,r)=>s+(i=>{if(i._$cssResult$===!0)return i.cssText;if(typeof i=="number")return i;throw Error("Value passed to 'css' function must be a 'css' function result: "+i+". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.")})(n)+o[r+1],o[0]);return new he(t,o,ht)},Vt=(o,e)=>{if(Ce)o.adoptedStyleSheets=e.map(t=>t instanceof CSSStyleSheet?t:t.styleSheet);else for(let t of e){let s=document.createElement("style"),n=Se.litNonce;n!==void 0&&s.setAttribute("nonce",n),s.textContent=t.cssText,o.appendChild(s)}},mt=Ce?o=>o:o=>o instanceof CSSStyleSheet?(e=>{let t="";for(let s of e.cssRules)t+=s.cssText;return Ft(t)})(o):o;var{is:co,defineProperty:po,getOwnPropertyDescriptor:uo,getOwnPropertyNames:ho,getOwnPropertySymbols:mo,getPrototypeOf:_o}=Object,Te=globalThis,qt=Te.trustedTypes,fo=qt?qt.emptyScript:"",go=Te.reactiveElementPolyfillSupport,_e=(o,e)=>o,_t={toAttribute(o,e){switch(e){case Boolean:o=o?fo:null;break;case Object:case Array:o=o==null?o:JSON.stringify(o)}return o},fromAttribute(o,e){let t=o;switch(e){case Boolean:t=o!==null;break;case Number:t=o===null?null:Number(o);break;case Object:case Array:try{t=JSON.parse(o)}catch{t=null}}return t}},Kt=(o,e)=>!co(o,e),Gt={attribute:!0,type:String,converter:_t,reflect:!1,useDefault:!1,hasChanged:Kt};Symbol.metadata??=Symbol("metadata"),Te.litPropertyMetadata??=new WeakMap;var I=class extends HTMLElement{static addInitializer(e){this._$Ei(),(this.l??=[]).push(e)}static get observedAttributes(){return this.finalize(),this._$Eh&&[...this._$Eh.keys()]}static createProperty(e,t=Gt){if(t.state&&(t.attribute=!1),this._$Ei(),this.prototype.hasOwnProperty(e)&&((t=Object.create(t)).wrapped=!0),this.elementProperties.set(e,t),!t.noAccessor){let s=Symbol(),n=this.getPropertyDescriptor(e,s,t);n!==void 0&&po(this.prototype,e,n)}}static getPropertyDescriptor(e,t,s){let{get:n,set:r}=uo(this.prototype,e)??{get(){return this[t]},set(i){this[t]=i}};return{get:n,set(i){let l=n?.call(this);r?.call(this,i),this.requestUpdate(e,l,s)},configurable:!0,enumerable:!0}}static getPropertyOptions(e){return this.elementProperties.get(e)??Gt}static _$Ei(){if(this.hasOwnProperty(_e("elementProperties")))return;let e=_o(this);e.finalize(),e.l!==void 0&&(this.l=[...e.l]),this.elementProperties=new Map(e.elementProperties)}static finalize(){if(this.hasOwnProperty(_e("finalized")))return;if(this.finalized=!0,this._$Ei(),this.hasOwnProperty(_e("properties"))){let t=this.properties,s=[...ho(t),...mo(t)];for(let n of s)this.createProperty(n,t[n])}let e=this[Symbol.metadata];if(e!==null){let t=litPropertyMetadata.get(e);if(t!==void 0)for(let[s,n]of t)this.elementProperties.set(s,n)}this._$Eh=new Map;for(let[t,s]of this.elementProperties){let n=this._$Eu(t,s);n!==void 0&&this._$Eh.set(n,t)}this.elementStyles=this.finalizeStyles(this.styles)}static finalizeStyles(e){let t=[];if(Array.isArray(e)){let s=new Set(e.flat(1/0).reverse());for(let n of s)t.unshift(mt(n))}else e!==void 0&&t.push(mt(e));return t}static _$Eu(e,t){let s=t.attribute;return s===!1?void 0:typeof s=="string"?s:typeof e=="string"?e.toLowerCase():void 0}constructor(){super(),this._$Ep=void 0,this.isUpdatePending=!1,this.hasUpdated=!1,this._$Em=null,this._$Ev()}_$Ev(){this._$ES=new Promise(e=>this.enableUpdating=e),this._$AL=new Map,this._$E_(),this.requestUpdate(),this.constructor.l?.forEach(e=>e(this))}addController(e){(this._$EO??=new Set).add(e),this.renderRoot!==void 0&&this.isConnected&&e.hostConnected?.()}removeController(e){this._$EO?.delete(e)}_$E_(){let e=new Map,t=this.constructor.elementProperties;for(let s of t.keys())this.hasOwnProperty(s)&&(e.set(s,this[s]),delete this[s]);e.size>0&&(this._$Ep=e)}createRenderRoot(){let e=this.shadowRoot??this.attachShadow(this.constructor.shadowRootOptions);return Vt(e,this.constructor.elementStyles),e}connectedCallback(){this.renderRoot??=this.createRenderRoot(),this.enableUpdating(!0),this._$EO?.forEach(e=>e.hostConnected?.())}enableUpdating(e){}disconnectedCallback(){this._$EO?.forEach(e=>e.hostDisconnected?.())}attributeChangedCallback(e,t,s){this._$AK(e,s)}_$ET(e,t){let s=this.constructor.elementProperties.get(e),n=this.constructor._$Eu(e,s);if(n!==void 0&&s.reflect===!0){let r=(s.converter?.toAttribute!==void 0?s.converter:_t).toAttribute(t,s.type);this._$Em=e,r==null?this.removeAttribute(n):this.setAttribute(n,r),this._$Em=null}}_$AK(e,t){let s=this.constructor,n=s._$Eh.get(e);if(n!==void 0&&this._$Em!==n){let r=s.getPropertyOptions(n),i=typeof r.converter=="function"?{fromAttribute:r.converter}:r.converter?.fromAttribute!==void 0?r.converter:_t;this._$Em=n;let l=i.fromAttribute(t,r.type);this[n]=l??this._$Ej?.get(n)??l,this._$Em=null}}requestUpdate(e,t,s,n=!1,r){if(e!==void 0){let i=this.constructor;if(n===!1&&(r=this[e]),s??=i.getPropertyOptions(e),!((s.hasChanged??Kt)(r,t)||s.useDefault&&s.reflect&&r===this._$Ej?.get(e)&&!this.hasAttribute(i._$Eu(e,s))))return;this.C(e,t,s)}this.isUpdatePending===!1&&(this._$ES=this._$EP())}C(e,t,{useDefault:s,reflect:n,wrapped:r},i){s&&!(this._$Ej??=new Map).has(e)&&(this._$Ej.set(e,i??t??this[e]),r!==!0||i!==void 0)||(this._$AL.has(e)||(this.hasUpdated||s||(t=void 0),this._$AL.set(e,t)),n===!0&&this._$Em!==e&&(this._$Eq??=new Set).add(e))}async _$EP(){this.isUpdatePending=!0;try{await this._$ES}catch(t){Promise.reject(t)}let e=this.scheduleUpdate();return e!=null&&await e,!this.isUpdatePending}scheduleUpdate(){return this.performUpdate()}performUpdate(){if(!this.isUpdatePending)return;if(!this.hasUpdated){if(this.renderRoot??=this.createRenderRoot(),this._$Ep){for(let[n,r]of this._$Ep)this[n]=r;this._$Ep=void 0}let s=this.constructor.elementProperties;if(s.size>0)for(let[n,r]of s){let{wrapped:i}=r,l=this[n];i!==!0||this._$AL.has(n)||l===void 0||this.C(n,void 0,r,l)}}let e=!1,t=this._$AL;try{e=this.shouldUpdate(t),e?(this.willUpdate(t),this._$EO?.forEach(s=>s.hostUpdate?.()),this.update(t)):this._$EM()}catch(s){throw e=!1,this._$EM(),s}e&&this._$AE(t)}willUpdate(e){}_$AE(e){this._$EO?.forEach(t=>t.hostUpdated?.()),this.hasUpdated||(this.hasUpdated=!0,this.firstUpdated(e)),this.updated(e)}_$EM(){this._$AL=new Map,this.isUpdatePending=!1}get updateComplete(){return this.getUpdateComplete()}getUpdateComplete(){return this._$ES}shouldUpdate(e){return!0}update(e){this._$Eq&&=this._$Eq.forEach(t=>this._$ET(t,this[t])),this._$EM()}updated(e){}firstUpdated(e){}};I.elementStyles=[],I.shadowRootOptions={mode:"open"},I[_e("elementProperties")]=new Map,I[_e("finalized")]=new Map,go?.({ReactiveElement:I}),(Te.reactiveElementVersions??=[]).push("2.1.2");var gt=globalThis,Zt=o=>o,Pe=gt.trustedTypes,Yt=Pe?Pe.createPolicy("lit-html",{createHTML:o=>o}):void 0,yt="$lit$",M=`lit$${Math.random().toFixed(9).slice(2)}$`,wt="?"+M,yo=`<${wt}>`,K=document,ge=()=>K.createComment(""),ye=o=>o===null||typeof o!="object"&&typeof o!="function",vt=Array.isArray,ss=o=>vt(o)||typeof o?.[Symbol.iterator]=="function",ft=`[ 	
\f\r]`,fe=/<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g,Jt=/-->/g,Xt=/>/g,q=RegExp(`>|${ft}(?:([^\\s"'>=/]+)(${ft}*=${ft}*(?:[^ 	
\f\r"'\`<>=]|("|')|))|$)`,"g"),Qt=/'/g,es=/"/g,os=/^(?:script|style|textarea|title)$/i,bt=o=>(e,...t)=>({_$litType$:o,strings:e,values:t}),p=bt(1),oe=bt(2),Cn=bt(3),Z=Symbol.for("lit-noChange"),m=Symbol.for("lit-nothing"),ts=new WeakMap,G=K.createTreeWalker(K,129);function ns(o,e){if(!vt(o)||!o.hasOwnProperty("raw"))throw Error("invalid template strings array");return Yt!==void 0?Yt.createHTML(e):e}var rs=(o,e)=>{let t=o.length-1,s=[],n,r=e===2?"<svg>":e===3?"<math>":"",i=fe;for(let l=0;l<t;l++){let a=o[l],c,u,d=-1,_=0;for(;_<a.length&&(i.lastIndex=_,u=i.exec(a),u!==null);)_=i.lastIndex,i===fe?u[1]==="!--"?i=Jt:u[1]!==void 0?i=Xt:u[2]!==void 0?(os.test(u[2])&&(n=RegExp("</"+u[2],"g")),i=q):u[3]!==void 0&&(i=q):i===q?u[0]===">"?(i=n??fe,d=-1):u[1]===void 0?d=-2:(d=i.lastIndex-u[2].length,c=u[1],i=u[3]===void 0?q:u[3]==='"'?es:Qt):i===es||i===Qt?i=q:i===Jt||i===Xt?i=fe:(i=q,n=void 0);let f=i===q&&o[l+1].startsWith("/>")?" ":"";r+=i===fe?a+yo:d>=0?(s.push(c),a.slice(0,d)+yt+a.slice(d)+M+f):a+M+(d===-2?l:f)}return[ns(o,r+(o[t]||"<?>")+(e===2?"</svg>":e===3?"</math>":"")),s]},we=class o{constructor({strings:e,_$litType$:t},s){let n;this.parts=[];let r=0,i=0,l=e.length-1,a=this.parts,[c,u]=rs(e,t);if(this.el=o.createElement(c,s),G.currentNode=this.el.content,t===2||t===3){let d=this.el.content.firstChild;d.replaceWith(...d.childNodes)}for(;(n=G.nextNode())!==null&&a.length<l;){if(n.nodeType===1){if(n.hasAttributes())for(let d of n.getAttributeNames())if(d.endsWith(yt)){let _=u[i++],f=n.getAttribute(d).split(M),v=/([.?@])?(.*)/.exec(_);a.push({type:1,index:r,name:v[2],strings:f,ctor:v[1]==="."?Ee:v[1]==="?"?ze:v[1]==="@"?Le:J}),n.removeAttribute(d)}else d.startsWith(M)&&(a.push({type:6,index:r}),n.removeAttribute(d));if(os.test(n.tagName)){let d=n.textContent.split(M),_=d.length-1;if(_>0){n.textContent=Pe?Pe.emptyScript:"";for(let f=0;f<_;f++)n.append(d[f],ge()),G.nextNode(),a.push({type:2,index:++r});n.append(d[_],ge())}}}else if(n.nodeType===8)if(n.data===wt)a.push({type:2,index:r});else{let d=-1;for(;(d=n.data.indexOf(M,d+1))!==-1;)a.push({type:7,index:r}),d+=M.length-1}r++}}static createElement(e,t){let s=K.createElement("template");return s.innerHTML=e,s}};function Y(o,e,t=o,s){if(e===Z)return e;let n=s!==void 0?t._$Co?.[s]:t._$Cl,r=ye(e)?void 0:e._$litDirective$;return n?.constructor!==r&&(n?._$AO?.(!1),r===void 0?n=void 0:(n=new r(o),n._$AT(o,t,s)),s!==void 0?(t._$Co??=[])[s]=n:t._$Cl=n),n!==void 0&&(e=Y(o,n._$AS(o,e.values),n,s)),e}var Re=class{constructor(e,t){this._$AV=[],this._$AN=void 0,this._$AD=e,this._$AM=t}get parentNode(){return this._$AM.parentNode}get _$AU(){return this._$AM._$AU}u(e){let{el:{content:t},parts:s}=this._$AD,n=(e?.creationScope??K).importNode(t,!0);G.currentNode=n;let r=G.nextNode(),i=0,l=0,a=s[0];for(;a!==void 0;){if(i===a.index){let c;a.type===2?c=new se(r,r.nextSibling,this,e):a.type===1?c=new a.ctor(r,a.name,a.strings,this,e):a.type===6&&(c=new Ne(r,this,e)),this._$AV.push(c),a=s[++l]}i!==a?.index&&(r=G.nextNode(),i++)}return G.currentNode=K,n}p(e){let t=0;for(let s of this._$AV)s!==void 0&&(s.strings!==void 0?(s._$AI(e,s,t),t+=s.strings.length-2):s._$AI(e[t])),t++}},se=class o{get _$AU(){return this._$AM?._$AU??this._$Cv}constructor(e,t,s,n){this.type=2,this._$AH=m,this._$AN=void 0,this._$AA=e,this._$AB=t,this._$AM=s,this.options=n,this._$Cv=n?.isConnected??!0}get parentNode(){let e=this._$AA.parentNode,t=this._$AM;return t!==void 0&&e?.nodeType===11&&(e=t.parentNode),e}get startNode(){return this._$AA}get endNode(){return this._$AB}_$AI(e,t=this){e=Y(this,e,t),ye(e)?e===m||e==null||e===""?(this._$AH!==m&&this._$AR(),this._$AH=m):e!==this._$AH&&e!==Z&&this._(e):e._$litType$!==void 0?this.$(e):e.nodeType!==void 0?this.T(e):ss(e)?this.k(e):this._(e)}O(e){return this._$AA.parentNode.insertBefore(e,this._$AB)}T(e){this._$AH!==e&&(this._$AR(),this._$AH=this.O(e))}_(e){this._$AH!==m&&ye(this._$AH)?this._$AA.nextSibling.data=e:this.T(K.createTextNode(e)),this._$AH=e}$(e){let{values:t,_$litType$:s}=e,n=typeof s=="number"?this._$AC(e):(s.el===void 0&&(s.el=we.createElement(ns(s.h,s.h[0]),this.options)),s);if(this._$AH?._$AD===n)this._$AH.p(t);else{let r=new Re(n,this),i=r.u(this.options);r.p(t),this.T(i),this._$AH=r}}_$AC(e){let t=ts.get(e.strings);return t===void 0&&ts.set(e.strings,t=new we(e)),t}k(e){vt(this._$AH)||(this._$AH=[],this._$AR());let t=this._$AH,s,n=0;for(let r of e)n===t.length?t.push(s=new o(this.O(ge()),this.O(ge()),this,this.options)):s=t[n],s._$AI(r),n++;n<t.length&&(this._$AR(s&&s._$AB.nextSibling,n),t.length=n)}_$AR(e=this._$AA.nextSibling,t){for(this._$AP?.(!1,!0,t);e!==this._$AB;){let s=Zt(e).nextSibling;Zt(e).remove(),e=s}}setConnected(e){this._$AM===void 0&&(this._$Cv=e,this._$AP?.(e))}},J=class{get tagName(){return this.element.tagName}get _$AU(){return this._$AM._$AU}constructor(e,t,s,n,r){this.type=1,this._$AH=m,this._$AN=void 0,this.element=e,this.name=t,this._$AM=n,this.options=r,s.length>2||s[0]!==""||s[1]!==""?(this._$AH=Array(s.length-1).fill(new String),this.strings=s):this._$AH=m}_$AI(e,t=this,s,n){let r=this.strings,i=!1;if(r===void 0)e=Y(this,e,t,0),i=!ye(e)||e!==this._$AH&&e!==Z,i&&(this._$AH=e);else{let l=e,a,c;for(e=r[0],a=0;a<r.length-1;a++)c=Y(this,l[s+a],t,a),c===Z&&(c=this._$AH[a]),i||=!ye(c)||c!==this._$AH[a],c===m?e=m:e!==m&&(e+=(c??"")+r[a+1]),this._$AH[a]=c}i&&!n&&this.j(e)}j(e){e===m?this.element.removeAttribute(this.name):this.element.setAttribute(this.name,e??"")}},Ee=class extends J{constructor(){super(...arguments),this.type=3}j(e){this.element[this.name]=e===m?void 0:e}},ze=class extends J{constructor(){super(...arguments),this.type=4}j(e){this.element.toggleAttribute(this.name,!!e&&e!==m)}},Le=class extends J{constructor(e,t,s,n,r){super(e,t,s,n,r),this.type=5}_$AI(e,t=this){if((e=Y(this,e,t,0)??m)===Z)return;let s=this._$AH,n=e===m&&s!==m||e.capture!==s.capture||e.once!==s.once||e.passive!==s.passive,r=e!==m&&(s===m||n);n&&this.element.removeEventListener(this.name,this,s),r&&this.element.addEventListener(this.name,this,e),this._$AH=e}handleEvent(e){typeof this._$AH=="function"?this._$AH.call(this.options?.host??this.element,e):this._$AH.handleEvent(e)}},Ne=class{constructor(e,t,s){this.element=e,this.type=6,this._$AN=void 0,this._$AM=t,this.options=s}get _$AU(){return this._$AM._$AU}_$AI(e){Y(this,e)}},is={M:yt,P:M,A:wt,C:1,L:rs,R:Re,D:ss,V:Y,I:se,H:J,N:ze,U:Le,B:Ee,F:Ne},wo=gt.litHtmlPolyfillSupport;wo?.(we,se),(gt.litHtmlVersions??=[]).push("3.3.3");var as=(o,e,t)=>{let s=t?.renderBefore??e,n=s._$litPart$;if(n===void 0){let r=t?.renderBefore??null;s._$litPart$=n=new se(e.insertBefore(ge(),r),r,void 0,t??{})}return n._$AI(o),n};var xt=globalThis,U=class extends I{constructor(){super(...arguments),this.renderOptions={host:this},this._$Do=void 0}createRenderRoot(){let e=super.createRenderRoot();return this.renderOptions.renderBefore??=e.firstChild,e}update(e){let t=this.render();this.hasUpdated||(this.renderOptions.isConnected=this.isConnected),super.update(e),this._$Do=as(t,this.renderRoot,this.renderOptions)}connectedCallback(){super.connectedCallback(),this._$Do?.setConnected(!0)}disconnectedCallback(){super.disconnectedCallback(),this._$Do?.setConnected(!1)}render(){return Z}};U._$litElement$=!0,U.finalized=!0,xt.litElementHydrateSupport?.({LitElement:U});var vo=xt.litElementPolyfillSupport;vo?.({LitElement:U});(xt.litElementVersions??=[]).push("4.2.2");var ls={tf_day:"1T",tf_week:"1W",tf_month:"1M",tf_six_month:"6M",tf_year:"1J",aria_timeframe:"Zeitraum",aria_currency:"W\xE4hrung",search_placeholder:"Name, Symbol oder ISIN",search_none:"Kein Wallet passt zu \u201E{query}\u201C.",aria_search:"Wallets durchsuchen",aria_search_clear:"Suche leeren",return_day:"Rendite \xFCber 1 Tag",return_week:"Rendite \xFCber 1 Woche",return_month:"Rendite \xFCber 1 Monat",return_six_month:"Rendite \xFCber 6 Monate",return_year:"Rendite \xFCber 1 Jahr",value_line:"Gesamtwert, {start} \u2013 heute",value_line_day:"Gesamtwert, letzte 24 Stunden",cash:"Bargeld",cash_plus:"Cash Plus",staked:"{share} im Staking",show_all:"Alle anzeigen ({count})",show_less:"Weniger anzeigen",detail_available:"Verf\xFCgbar",detail_staked:"Im Staking",detail_staking_apr:"Staking-APR",detail_average_buy_price:"\xD8 Kaufpreis",detail_invested:"Investiert",detail_profit_loss:"Gewinn / Verlust",detail_rewards:"Staking-Belohnungen",detail_rewards_net:"Netto, gesamt",detail_rewards_worth:"heute {value} wert",detail_payouts:"Gutschriften",detail_payouts_value:"{count} \xB7 zuletzt {date}",shares_one:"St\xFCck",shares_other:"St\xFCck",eye_hide:"Betr\xE4ge verbergen",eye_show:"Betr\xE4ge anzeigen",change_since:"\xC4nderung seit {date}",ecb_footer:"Preise in {currency}: Bitpandas Euro-Preise, umgerechnet zum EZB-Referenzkurs vom {date}. Ihre \xC4nderung enth\xE4lt die Bewegung des Kurses.",empty_portfolio:"Richte das Bitpanda Portfolio ein, dann erscheint es hier.",empty_wallets:"Noch keine Wallets.",empty_selection_wallets:"Keine Wallets in der Auswahl dieser Karte.",empty_selection_assets:"Keine Assets in der Auswahl dieser Karte.",empty_price_tracker:"Richte den Bitpanda Price Tracker ein und f\xFCge Assets hinzu, dann erscheinen hier Preise.",picker_portfolio:"Gesamtwert und Rendite mit Verlauf, Bargeld und Cash Plus, Verteilung und deine Wallets; jeder Teil l\xE4sst sich ausblenden.",picker_price_tracker:"Preise und \xC4nderungen deiner verfolgten Assets, je mit Verlauf, als Liste oder Kacheln.",invalid_option:"Ung\xFCltiger Wert f\xFCr \u201E{option}\u201C: {value}. Erlaubt: {allowed}.",allowed_text:"Text",allowed_devices:"eine Liste von Ger\xE4te-IDs",allowed_groups:"eine Liste aus {values}",group_content:"Inhalt",group_wallets:"Wallets",group_assets:"Assets",group_appearance:"Darstellung",opt_title:"Titel",opt_title_help:"Leer lassen f\xFCr den grau angezeigten Namen",opt_timeframe:"Standard-Zeitraum",opt_timeframe_help:"Die Tasten 1T bis 1J auf der Karte wechseln ihn nur vor\xFCbergehend",tfo_day:"1 Tag",tfo_week:"1 Woche",tfo_month:"1 Monat",tfo_six_month:"6 Monate",tfo_year:"1 Jahr",opt_show_cash:"Bargeld und Cash Plus",opt_show_allocation:"Verteilung",opt_show_allocation_help:"Der farbige Balken mit den Anteilen der Asset-Gruppen und des Bargelds",opt_show_total:"Gesamtwert und Rendite",opt_show_total_help:"Die Zeitraum-Tasten bleiben, solange der Verlauf gezeigt wird",opt_show_line:"Verlauf des Gesamtwerts",opt_show_wallets:"Wallets",opt_group_wallets:"Wallets in Asset-Gruppen",opt_show_search:"Suchfeld",opt_show_search_help:"Findet Wallets nach Name, Symbol oder ISIN",opt_sort:"Sortieren nach",sort_value:"Wert",sort_return:"Rendite seit Kauf",sort_name:"Name",sort_selection:"Reihenfolge wie gew\xE4hlt",sort_change_desc:"\xC4nderung, h\xF6chste zuerst",sort_change_asc:"\xC4nderung, niedrigste zuerst",opt_sort_help_tracker:"\u201EReihenfolge wie gew\xE4hlt\u201C gilt nur mit \u201ENur die gew\xE4hlten\u201C Assets, sonst nach Name",opt_group_selection:"Angezeigte Asset-Gruppen",opt_group_selection_help:"Gilt nur f\xFCr die Wallets; Gesamtwert, Bargeld, Cash Plus und Verteilung zeigen immer das ganze Portfolio",opt_groups:"Asset-Gruppen w\xE4hlen",opt_asset_selection:"Angezeigte Assets",opt_asset_selection_wallets:"Angezeigte Wallets",sel_all:"Alle",sel_all_except:"Alle au\xDFer den gew\xE4hlten",sel_only:"Nur die gew\xE4hlten",opt_assets:"Assets w\xE4hlen",opt_assets_wallets:"Wallets w\xE4hlen",opt_assets_help:"Ein Asset aus einer ausgeblendeten Asset-Gruppe bleibt verborgen, auch wenn es hier gew\xE4hlt ist",opt_assets_help_wallets:"Ein Wallet aus einer ausgeblendeten Asset-Gruppe bleibt verborgen, auch wenn es hier gew\xE4hlt ist",opt_hide_amounts:"Betr\xE4ge zun\xE4chst verbergen",opt_hide_amounts_help:"Prozente bleiben sichtbar; das Auge oben auf der Karte zeigt die Betr\xE4ge nur vor\xFCbergehend",opt_limit:"Assets vor \u201EAlle anzeigen\u201C",opt_limit_wallets:"Wallets vor \u201EAlle anzeigen\u201C",opt_limit_help:"0 zeigt alle Assets",opt_limit_help_wallets:"Nur wenn \u201EWallets in Asset-Gruppen\u201C aus ist; 0 zeigt alle",opt_layout:"Anzeigen als",layout_list:"Liste",layout_tiles:"Kacheln",opt_currency:"Standard-W\xE4hrung",opt_currency_help:"Die Tasten auf der Karte wechseln sie nur vor\xFCbergehend; weitere W\xE4hrungen \xFCber \u201EKonfigurieren\u201C beim Price Tracker"};var cs={tf_day:"1D",tf_week:"1W",tf_month:"1M",tf_six_month:"6M",tf_year:"1Y",aria_timeframe:"Timeframe",aria_currency:"Currency",search_placeholder:"Name, symbol or ISIN",search_none:"No wallet matches \u201C{query}\u201D.",aria_search:"Search wallets",aria_search_clear:"Clear search",return_day:"return over 1 day",return_week:"return over 1 week",return_month:"return over 1 month",return_six_month:"return over 6 months",return_year:"return over 1 year",value_line:"Total value, {start} \u2013 today",value_line_day:"Total value, last 24 hours",cash:"Cash",cash_plus:"Cash Plus",staked:"{share} staked",show_all:"Show all ({count})",show_less:"Show less",detail_available:"Available",detail_staked:"Staked",detail_staking_apr:"Staking APR",detail_average_buy_price:"Average buy price",detail_invested:"Invested",detail_profit_loss:"Profit / loss",detail_rewards:"Staking rewards",detail_rewards_net:"Net, all time",detail_rewards_worth:"worth {value} today",detail_payouts:"Payouts",detail_payouts_value:"{count} \xB7 last {date}",shares_one:"share",shares_other:"shares",eye_hide:"Hide amounts",eye_show:"Show amounts",change_since:"Change since {date}",ecb_footer:"Prices in {currency}: Bitpanda's EUR prices converted at the ECB reference rate of {date}. Their change includes the rate's move.",empty_portfolio:"Set up the Bitpanda Portfolio to see it here.",empty_wallets:"No wallets yet.",empty_selection_wallets:"No wallets in this card's selection.",empty_selection_assets:"No assets in this card's selection.",empty_price_tracker:"Set up the Bitpanda Price Tracker and add assets to it to see prices here.",picker_portfolio:"Total value and return with a value line, Cash and Cash Plus, allocation and your wallets; each part can be left out.",picker_price_tracker:"Prices and changes of the assets you track, each with a line, as a list or tiles.",invalid_option:"Invalid value for \u201C{option}\u201D: {value}. Allowed: {allowed}.",allowed_text:"text",allowed_devices:"a list of device IDs",allowed_groups:"a list of {values}",group_content:"Content",group_wallets:"Wallets",group_assets:"Assets",group_appearance:"Appearance",opt_title:"Title",opt_title_help:"Leave empty for the name shown in grey",opt_timeframe:"Default timeframe",opt_timeframe_help:"The 1D to 1Y buttons on the card change it only temporarily",tfo_day:"1 day",tfo_week:"1 week",tfo_month:"1 month",tfo_six_month:"6 months",tfo_year:"1 year",opt_show_cash:"Cash and Cash Plus",opt_show_allocation:"Allocation bar",opt_show_allocation_help:"The coloured bar showing the share of each asset group and of cash",opt_show_total:"Total value and return",opt_show_total_help:"The timeframe buttons stay while the line is shown",opt_show_line:"Total value line",opt_show_wallets:"Wallets",opt_group_wallets:"Wallets in asset groups",opt_show_search:"Search field",opt_show_search_help:"Finds wallets by name, symbol or ISIN",opt_sort:"Sort by",sort_value:"Value",sort_return:"Return since purchase",sort_name:"Name",sort_selection:"Order as chosen",sort_change_desc:"Change, highest first",sort_change_asc:"Change, lowest first",opt_sort_help_tracker:"\u201COrder as chosen\u201D applies only when assets are set to \u201COnly the ones chosen\u201D; otherwise by name",opt_group_selection:"Asset groups shown",opt_group_selection_help:"Applies to the wallets only; total value, Cash, Cash Plus and allocation always show the whole portfolio",opt_groups:"Choose asset groups",opt_asset_selection:"Assets shown",opt_asset_selection_wallets:"Wallets shown",sel_all:"All",sel_all_except:"All except the ones chosen",sel_only:"Only the ones chosen",opt_assets:"Choose assets",opt_assets_wallets:"Choose wallets",opt_assets_help:"An asset from a hidden asset group stays hidden, even when chosen here",opt_assets_help_wallets:"A wallet from a hidden asset group stays hidden, even when chosen here",opt_hide_amounts:"Hide amounts initially",opt_hide_amounts_help:"Percentages stay visible; the eye at the top of the card shows the amounts only temporarily",opt_limit:"Assets before \u201CShow all\u201D",opt_limit_wallets:"Wallets before \u201CShow all\u201D",opt_limit_help:"0 shows every asset",opt_limit_help_wallets:"Only while \u201CWallets in asset groups\u201D is off; 0 shows all",opt_layout:"Show as",layout_list:"List",layout_tiles:"Tiles",opt_currency:"Default currency",opt_currency_help:"The buttons on the card change it only temporarily; more currencies via \u201CConfigure\u201D on the Price Tracker"};var ds={tf_day:"1D",tf_week:"1S",tf_month:"1M",tf_six_month:"6M",tf_year:"1A",aria_timeframe:"Periodo",aria_currency:"Moneda",search_placeholder:"Nombre, s\xEDmbolo o ISIN",search_none:"Ning\xFAn wallet coincide con \xAB{query}\xBB.",aria_search:"Buscar wallets",aria_search_clear:"Borrar b\xFAsqueda",return_day:"rentabilidad en 1 d\xEDa",return_week:"rentabilidad en 1 semana",return_month:"rentabilidad en 1 mes",return_six_month:"rentabilidad en 6 meses",return_year:"rentabilidad en 1 a\xF1o",value_line:"Valor total, {start} \u2013 hoy",value_line_day:"Valor total, \xFAltimas 24 horas",cash:"Efectivo",cash_plus:"Cash Plus",staked:"{share} en staking",show_all:"Mostrar todo ({count})",show_less:"Mostrar menos",detail_available:"Disponible",detail_staked:"En staking",detail_staking_apr:"APR de staking",detail_average_buy_price:"Precio medio de compra",detail_invested:"Importe invertido",detail_profit_loss:"Ganancia / p\xE9rdida",detail_rewards:"Recompensas de staking",detail_rewards_net:"Neto, en total",detail_rewards_worth:"hoy valen {value}",detail_payouts:"Pagos",detail_payouts_value:"{count} \xB7 \xFAltimo el {date}",shares_one:"t\xEDtulo",shares_other:"t\xEDtulos",shares_many:"t\xEDtulos",eye_hide:"Ocultar importes",eye_show:"Mostrar importes",change_since:"Variaci\xF3n desde el {date}",ecb_footer:"Precios en {currency}: precios en EUR de Bitpanda convertidos al tipo de referencia del BCE del {date}. Su variaci\xF3n incluye la del tipo.",empty_portfolio:"Configura el Bitpanda Portfolio para verlo aqu\xED.",empty_wallets:"Todav\xEDa no hay wallets.",empty_selection_wallets:"Ning\xFAn wallet en la selecci\xF3n de esta tarjeta.",empty_selection_assets:"Ning\xFAn activo en la selecci\xF3n de esta tarjeta.",empty_price_tracker:"Configura el Bitpanda Price Tracker y a\xF1ade activos para ver precios aqu\xED.",picker_portfolio:"Valor total y rentabilidad con l\xEDnea, efectivo y Cash Plus, distribuci\xF3n y tus wallets; cada parte se puede ocultar.",picker_price_tracker:"Precios y cambios de los activos que sigues, cada uno con su l\xEDnea, en lista o en mosaicos.",invalid_option:"Valor no v\xE1lido para \xAB{option}\xBB: {value}. Permitidos: {allowed}.",allowed_text:"texto",allowed_devices:"una lista de ID de dispositivo",allowed_groups:"una lista de {values}",group_content:"Contenido",group_wallets:"Wallets",group_assets:"Activos",group_appearance:"Apariencia",opt_title:"T\xEDtulo",opt_title_help:"D\xE9jalo vac\xEDo para el nombre mostrado en gris",opt_timeframe:"Periodo predeterminado",opt_timeframe_help:"Los botones 1D a 1A de la tarjeta lo cambian solo temporalmente",tfo_day:"1 d\xEDa",tfo_week:"1 semana",tfo_month:"1 mes",tfo_six_month:"6 meses",tfo_year:"1 a\xF1o",opt_show_cash:"Efectivo y Cash Plus",opt_show_allocation:"Barra de distribuci\xF3n",opt_show_allocation_help:"La barra de colores con la proporci\xF3n de cada grupo de activos y del efectivo",opt_show_total:"Valor total y rentabilidad",opt_show_total_help:"Los botones de periodo se mantienen mientras se muestre la l\xEDnea",opt_show_line:"L\xEDnea del valor total",opt_show_wallets:"Wallets",opt_group_wallets:"Wallets en grupos de activos",opt_show_search:"Campo de b\xFAsqueda",opt_show_search_help:"Encuentra wallets por nombre, s\xEDmbolo o ISIN",opt_sort:"Ordenar por",sort_value:"Valor",sort_return:"Rentabilidad desde la compra",sort_name:"Nombre",sort_selection:"Orden de selecci\xF3n",sort_change_desc:"Cambio, mayor primero",sort_change_asc:"Cambio, menor primero",opt_sort_help_tracker:"\xABOrden de selecci\xF3n\xBB solo se aplica con \xABSolo los elegidos\xBB en los activos; si no, por nombre",opt_group_selection:"Grupos de activos mostrados",opt_group_selection_help:"Solo afecta a los wallets; el valor total, el efectivo, Cash Plus y la distribuci\xF3n muestran siempre toda la cartera",opt_groups:"Elegir grupos de activos",opt_asset_selection:"Activos mostrados",opt_asset_selection_wallets:"Wallets mostrados",sel_all:"Todos",sel_all_except:"Todos excepto los elegidos",sel_only:"Solo los elegidos",opt_assets:"Elegir activos",opt_assets_wallets:"Elegir wallets",opt_assets_help:"Un activo de un grupo de activos oculto sigue oculto, aunque se elija aqu\xED",opt_assets_help_wallets:"Un wallet de un grupo de activos oculto sigue oculto, aunque se elija aqu\xED",opt_hide_amounts:"Ocultar inicialmente los importes",opt_hide_amounts_help:"Los porcentajes siguen visibles; el ojo de la parte superior de la tarjeta muestra los importes solo temporalmente",opt_limit:"Activos antes de \xABMostrar todo\xBB",opt_limit_wallets:"Wallets antes de \xABMostrar todo\xBB",opt_limit_help:"0 muestra todos los activos",opt_limit_help_wallets:"Solo si \xABWallets en grupos de activos\xBB est\xE1 desactivado; 0 muestra todo",opt_layout:"Mostrar como",layout_list:"Lista",layout_tiles:"Mosaicos",opt_currency:"Moneda predeterminada",opt_currency_help:"Los botones de la tarjeta la cambian solo temporalmente; m\xE1s monedas con \xABConfigurar\xBB en el Price Tracker"};var ps={tf_day:"1J",tf_week:"1S",tf_month:"1M",tf_six_month:"6M",tf_year:"1A",aria_timeframe:"P\xE9riode",aria_currency:"Devise",search_placeholder:"Nom, symbole ou ISIN",search_none:"Aucun wallet ne correspond \xE0 \xAB\xA0{query}\xA0\xBB.",aria_search:"Rechercher des wallets",aria_search_clear:"Effacer la recherche",return_day:"rendement sur 1 jour",return_week:"rendement sur 1 semaine",return_month:"rendement sur 1 mois",return_six_month:"rendement sur 6 mois",return_year:"rendement sur 1 an",value_line:"Valeur totale, {start} \u2013 aujourd'hui",value_line_day:"Valeur totale, derni\xE8res 24 heures",cash:"Liquidit\xE9s",cash_plus:"Cash Plus",staked:"{share} en staking",show_all:"Tout afficher ({count})",show_less:"Afficher moins",detail_available:"Disponible",detail_staked:"En staking",detail_staking_apr:"APR du staking",detail_average_buy_price:"Prix d'achat moyen",detail_invested:"Montant investi",detail_profit_loss:"Gain / perte",detail_rewards:"R\xE9compenses de staking",detail_rewards_net:"Net, depuis le d\xE9but",detail_rewards_worth:"valant {value} aujourd'hui",detail_payouts:"Versements",detail_payouts_value:"{count} \xB7 dernier le {date}",shares_one:"titre",shares_other:"titres",shares_many:"titres",eye_hide:"Masquer les montants",eye_show:"Afficher les montants",change_since:"Variation depuis le {date}",ecb_footer:"Prix en {currency}\xA0: prix en EUR de Bitpanda convertis au taux de r\xE9f\xE9rence de la BCE du {date}. Leur variation inclut celle du taux.",empty_portfolio:"Configurez le Bitpanda Portfolio pour le voir ici.",empty_wallets:"Aucun wallet pour le moment.",empty_selection_wallets:"Aucun wallet dans la s\xE9lection de cette carte.",empty_selection_assets:"Aucun actif dans la s\xE9lection de cette carte.",empty_price_tracker:"Configurez le Bitpanda Price Tracker et ajoutez-y des actifs pour voir les prix ici.",picker_portfolio:"Valeur totale et rendement avec courbe, liquidit\xE9s et Cash Plus, r\xE9partition et vos wallets\xA0; chaque partie peut \xEAtre masqu\xE9e.",picker_price_tracker:"Prix et variations des actifs que vous suivez, chacun avec sa courbe, en liste ou en tuiles.",invalid_option:"Valeur non valide pour \xAB\xA0{option}\xA0\xBB\xA0: {value}. Valeurs possibles\xA0: {allowed}.",allowed_text:"texte",allowed_devices:"une liste d'ID d'appareils",allowed_groups:"une liste d'\xE9l\xE9ments parmi {values}",group_content:"Contenu",group_wallets:"Wallets",group_assets:"Actifs",group_appearance:"Apparence",opt_title:"Titre",opt_title_help:"Laisser vide pour le nom affich\xE9 en gris",opt_timeframe:"P\xE9riode par d\xE9faut",opt_timeframe_help:"Les boutons 1J \xE0 1A de la carte ne la changent que temporairement",tfo_day:"1 jour",tfo_week:"1 semaine",tfo_month:"1 mois",tfo_six_month:"6 mois",tfo_year:"1 an",opt_show_cash:"Liquidit\xE9s et Cash Plus",opt_show_allocation:"Barre de r\xE9partition",opt_show_allocation_help:"La barre color\xE9e avec la part de chaque groupe d'actifs et des liquidit\xE9s",opt_show_total:"Valeur totale et rendement",opt_show_total_help:"Les boutons de p\xE9riode restent tant que la courbe est affich\xE9e",opt_show_line:"Courbe de la valeur totale",opt_show_wallets:"Wallets",opt_group_wallets:"Wallets par groupe d'actifs",opt_show_search:"Champ de recherche",opt_show_search_help:"Trouve les wallets par nom, symbole ou ISIN",opt_sort:"Trier par",sort_value:"Valeur",sort_return:"Rendement depuis l'achat",sort_name:"Nom",sort_selection:"Ordre de s\xE9lection",sort_change_desc:"Variation, la plus forte d'abord",sort_change_asc:"Variation, la plus faible d'abord",opt_sort_help_tracker:"\xAB\xA0Ordre de s\xE9lection\xA0\xBB ne s'applique qu'avec \xAB\xA0Seulement ceux choisis\xA0\xBB pour les actifs\xA0; sinon, tri par nom",opt_group_selection:"Groupes d'actifs affich\xE9s",opt_group_selection_help:"S'applique seulement aux wallets\xA0; la valeur totale, les liquidit\xE9s, Cash Plus et la r\xE9partition portent toujours sur l'ensemble du portefeuille",opt_groups:"Choisir les groupes d'actifs",opt_asset_selection:"Actifs affich\xE9s",opt_asset_selection_wallets:"Wallets affich\xE9s",sel_all:"Tous",sel_all_except:"Tous sauf ceux choisis",sel_only:"Seulement ceux choisis",opt_assets:"Choisir les actifs",opt_assets_wallets:"Choisir les wallets",opt_assets_help:"Un actif d'un groupe d'actifs masqu\xE9 reste masqu\xE9, m\xEAme s'il est choisi ici",opt_assets_help_wallets:"Un wallet d'un groupe d'actifs masqu\xE9 reste masqu\xE9, m\xEAme s'il est choisi ici",opt_hide_amounts:"Masquer initialement les montants",opt_hide_amounts_help:"Les pourcentages restent visibles\xA0; l'\u0153il en haut de la carte n'affiche les montants que temporairement",opt_limit:"Actifs avant \xAB\xA0Tout afficher\xA0\xBB",opt_limit_wallets:"Wallets avant \xAB\xA0Tout afficher\xA0\xBB",opt_limit_help:"0 affiche tous les actifs",opt_limit_help_wallets:"Seulement si \xAB\xA0Wallets par groupe d'actifs\xA0\xBB est d\xE9sactiv\xE9\xA0; 0 affiche tout",opt_layout:"Afficher en",layout_list:"Liste",layout_tiles:"Tuiles",opt_currency:"Devise par d\xE9faut",opt_currency_help:"Les boutons de la carte ne la changent que temporairement\xA0; d'autres devises via \xAB\xA0Configurer\xA0\xBB dans le Price Tracker"};var us={tf_day:"1G",tf_week:"1S",tf_month:"1M",tf_six_month:"6M",tf_year:"1A",aria_timeframe:"Periodo",aria_currency:"Valuta",search_placeholder:"Nome, simbolo o ISIN",search_none:"Nessun wallet corrisponde a \xAB{query}\xBB.",aria_search:"Cerca nei wallet",aria_search_clear:"Cancella ricerca",return_day:"rendimento su 1 giorno",return_week:"rendimento su 1 settimana",return_month:"rendimento su 1 mese",return_six_month:"rendimento su 6 mesi",return_year:"rendimento su 1 anno",value_line:"Valore totale, {start} \u2013 oggi",value_line_day:"Valore totale, ultime 24 ore",cash:"Liquidit\xE0",cash_plus:"Cash Plus",staked:"{share} in staking",show_all:"Mostra tutto ({count})",show_less:"Mostra meno",detail_available:"Disponibile",detail_staked:"In staking",detail_staking_apr:"APR dello staking",detail_average_buy_price:"Prezzo medio di acquisto",detail_invested:"Importo investito",detail_profit_loss:"Profitto / perdita",detail_rewards:"Ricompense di staking",detail_rewards_net:"Netto, in totale",detail_rewards_worth:"oggi valgono {value}",detail_payouts:"Accrediti",detail_payouts_value:"{count} \xB7 ultimo il {date}",shares_one:"pezzo",shares_other:"pezzi",shares_many:"pezzi",eye_hide:"Nascondi gli importi",eye_show:"Mostra gli importi",change_since:"Variazione dal {date}",ecb_footer:"Prezzi in {currency}: prezzi in EUR di Bitpanda convertiti al tasso di riferimento BCE del {date}. La loro variazione include quella del tasso.",empty_portfolio:"Configura il Bitpanda Portfolio per vederlo qui.",empty_wallets:"Ancora nessun wallet.",empty_selection_wallets:"Nessun wallet nella selezione di questa scheda.",empty_selection_assets:"Nessun asset nella selezione di questa scheda.",empty_price_tracker:"Configura il Bitpanda Price Tracker e aggiungi degli asset per vedere i prezzi qui.",picker_portfolio:"Valore totale e rendimento con linea, liquidit\xE0 e Cash Plus, ripartizione e i tuoi wallet; ogni parte si pu\xF2 nascondere.",picker_price_tracker:"Prezzi e variazioni degli asset che segui, ognuno con la sua linea, come elenco o riquadri.",invalid_option:"Valore non valido per \xAB{option}\xBB: {value}. Consentiti: {allowed}.",allowed_text:"testo",allowed_devices:"un elenco di ID dispositivo",allowed_groups:"un elenco di valori tra {values}",group_content:"Contenuto",group_wallets:"Wallet",group_assets:"Asset",group_appearance:"Aspetto",opt_title:"Titolo",opt_title_help:"Lascia vuoto per il nome mostrato in grigio",opt_timeframe:"Periodo predefinito",opt_timeframe_help:"I pulsanti da 1G a 1A sulla scheda lo cambiano solo temporaneamente",tfo_day:"1 giorno",tfo_week:"1 settimana",tfo_month:"1 mese",tfo_six_month:"6 mesi",tfo_year:"1 anno",opt_show_cash:"Liquidit\xE0 e Cash Plus",opt_show_allocation:"Barra di ripartizione",opt_show_allocation_help:"La barra colorata con le quote dei gruppi di asset e della liquidit\xE0",opt_show_total:"Valore totale e rendimento",opt_show_total_help:"I pulsanti del periodo restano finch\xE9 \xE8 mostrata la linea",opt_show_line:"Linea del valore totale",opt_show_wallets:"Wallet",opt_group_wallets:"Wallet in gruppi di asset",opt_show_search:"Campo di ricerca",opt_show_search_help:"Trova i wallet per nome, simbolo o ISIN",opt_sort:"Ordina per",sort_value:"Valore",sort_return:"Rendimento dall'acquisto",sort_name:"Nome",sort_selection:"Ordine di selezione",sort_change_desc:"Variazione, maggiore prima",sort_change_asc:"Variazione, minore prima",opt_sort_help_tracker:"\xABOrdine di selezione\xBB vale solo con \xABSolo quelli scelti\xBB per gli asset; altrimenti per nome",opt_group_selection:"Gruppi di asset mostrati",opt_group_selection_help:"Vale solo per i wallet; valore totale, liquidit\xE0, Cash Plus e ripartizione mostrano sempre l'intero portafoglio",opt_groups:"Scegli i gruppi di asset",opt_asset_selection:"Asset mostrati",opt_asset_selection_wallets:"Wallet mostrati",sel_all:"Tutti",sel_all_except:"Tutti tranne quelli scelti",sel_only:"Solo quelli scelti",opt_assets:"Scegli gli asset",opt_assets_wallets:"Scegli i wallet",opt_assets_help:"Un asset di un gruppo di asset nascosto resta nascosto, anche se scelto qui",opt_assets_help_wallets:"Un wallet di un gruppo di asset nascosto resta nascosto, anche se scelto qui",opt_hide_amounts:"Nascondi inizialmente gli importi",opt_hide_amounts_help:"Le percentuali restano visibili; l'occhio in alto nella scheda mostra gli importi solo temporaneamente",opt_limit:"Asset prima di \xABMostra tutto\xBB",opt_limit_wallets:"Wallet prima di \xABMostra tutto\xBB",opt_limit_help:"0 mostra tutti gli asset",opt_limit_help_wallets:"Solo se \xABWallet in gruppi di asset\xBB \xE8 disattivato; 0 mostra tutto",opt_layout:"Mostra come",layout_list:"Elenco",layout_tiles:"Riquadri",opt_currency:"Valuta predefinita",opt_currency_help:"I pulsanti sulla scheda la cambiano solo temporaneamente; altre valute tramite \xABConfigura\xBB nel Price Tracker"};var hs={tf_day:"1D",tf_week:"1W",tf_month:"1M",tf_six_month:"6M",tf_year:"1J",aria_timeframe:"Periode",aria_currency:"Valuta",search_placeholder:"Naam, symbool of ISIN",search_none:"Geen wallet past bij \u2018{query}\u2019.",aria_search:"Wallets doorzoeken",aria_search_clear:"Zoekopdracht wissen",return_day:"rendement over 1 dag",return_week:"rendement over 1 week",return_month:"rendement over 1 maand",return_six_month:"rendement over 6 maanden",return_year:"rendement over 1 jaar",value_line:"Totale waarde, {start} \u2013 vandaag",value_line_day:"Totale waarde, laatste 24 uur",cash:"Contanten",cash_plus:"Cash Plus",staked:"{share} in staking",show_all:"Alles tonen ({count})",show_less:"Minder tonen",detail_available:"Beschikbaar",detail_staked:"In staking",detail_staking_apr:"Staking-APR",detail_average_buy_price:"Gemiddelde aankoopprijs",detail_invested:"Ge\xEFnvesteerd",detail_profit_loss:"Winst / verlies",detail_rewards:"Stakingbeloningen",detail_rewards_net:"Netto, totaal",detail_rewards_worth:"vandaag {value} waard",detail_payouts:"Uitbetalingen",detail_payouts_value:"{count} \xB7 laatste {date}",shares_one:"stuk",shares_other:"stuks",eye_hide:"Bedragen verbergen",eye_show:"Bedragen tonen",change_since:"Verandering sinds {date}",ecb_footer:"Prijzen in {currency}: de EUR-prijzen van Bitpanda, omgerekend tegen de ECB-referentiekoers van {date}. Hun verandering omvat de beweging van de koers.",empty_portfolio:"Stel het Bitpanda Portfolio in om het hier te zien.",empty_wallets:"Nog geen wallets.",empty_selection_wallets:"Geen wallets in de selectie van deze kaart.",empty_selection_assets:"Geen assets in de selectie van deze kaart.",empty_price_tracker:"Stel de Bitpanda Price Tracker in en voeg er assets aan toe om hier prijzen te zien.",picker_portfolio:"Totale waarde en rendement met een lijn, contanten en Cash Plus, verdeling en je wallets; elk deel kan worden verborgen.",picker_price_tracker:"Prijzen en veranderingen van de assets die je volgt, elk met een lijn, als lijst of tegels.",invalid_option:"Ongeldige waarde voor \u2018{option}\u2019: {value}. Toegestaan: {allowed}.",allowed_text:"tekst",allowed_devices:"een lijst met apparaat-ID's",allowed_groups:"een lijst met waarden uit {values}",group_content:"Inhoud",group_wallets:"Wallets",group_assets:"Assets",group_appearance:"Uiterlijk",opt_title:"Titel",opt_title_help:"Leeg laten voor de grijs getoonde naam",opt_timeframe:"Standaardperiode",opt_timeframe_help:"De knoppen 1D tot 1J op de kaart wijzigen die alleen tijdelijk",tfo_day:"1 dag",tfo_week:"1 week",tfo_month:"1 maand",tfo_six_month:"6 maanden",tfo_year:"1 jaar",opt_show_cash:"Contanten en Cash Plus",opt_show_allocation:"Verdelingsbalk",opt_show_allocation_help:"De gekleurde balk met het aandeel van elke assetgroep en van de contanten",opt_show_total:"Totale waarde en rendement",opt_show_total_help:"De periodeknoppen blijven zolang de lijn wordt getoond",opt_show_line:"Lijn van de totale waarde",opt_show_wallets:"Wallets",opt_group_wallets:"Wallets in assetgroepen",opt_show_search:"Zoekveld",opt_show_search_help:"Vindt wallets op naam, symbool of ISIN",opt_sort:"Sorteren op",sort_value:"Waarde",sort_return:"Rendement sinds aankoop",sort_name:"Naam",sort_selection:"Volgorde zoals gekozen",sort_change_desc:"Verandering, hoogste eerst",sort_change_asc:"Verandering, laagste eerst",opt_sort_help_tracker:"\u2018Volgorde zoals gekozen\u2019 geldt alleen bij \u2018Alleen de gekozen\u2019 assets, anders op naam",opt_group_selection:"Getoonde assetgroepen",opt_group_selection_help:"Geldt alleen voor de wallets; totale waarde, contanten, Cash Plus en verdeling tonen altijd het hele portfolio",opt_groups:"Assetgroepen kiezen",opt_asset_selection:"Getoonde assets",opt_asset_selection_wallets:"Getoonde wallets",sel_all:"Alle",sel_all_except:"Alle behalve de gekozen",sel_only:"Alleen de gekozen",opt_assets:"Assets kiezen",opt_assets_wallets:"Wallets kiezen",opt_assets_help:"Een asset uit een verborgen assetgroep blijft verborgen, ook als die hier is gekozen",opt_assets_help_wallets:"Een wallet uit een verborgen assetgroep blijft verborgen, ook als die hier is gekozen",opt_hide_amounts:"Bedragen aanvankelijk verbergen",opt_hide_amounts_help:"Percentages blijven zichtbaar; het oog bovenaan de kaart toont de bedragen alleen tijdelijk",opt_limit:"Assets v\xF3\xF3r \u2018Alles tonen\u2019",opt_limit_wallets:"Wallets v\xF3\xF3r \u2018Alles tonen\u2019",opt_limit_help:"0 toont alle assets",opt_limit_help_wallets:"Alleen als \u2018Wallets in assetgroepen\u2019 uit staat; 0 toont alles",opt_layout:"Weergeven als",layout_list:"Lijst",layout_tiles:"Tegels",opt_currency:"Standaardvaluta",opt_currency_help:"De knoppen op de kaart wijzigen die alleen tijdelijk; meer valuta via \u2018Configureren\u2019 bij de Price Tracker"};var ms={tf_day:"1D",tf_week:"1T",tf_month:"1M",tf_six_month:"6M",tf_year:"1R",aria_timeframe:"Okres",aria_currency:"Waluta",search_placeholder:"Nazwa, symbol lub ISIN",search_none:"\u017Baden portfel nie pasuje do \u201E{query}\u201D.",aria_search:"Szukaj portfeli",aria_search_clear:"Wyczy\u015B\u0107 wyszukiwanie",return_day:"stopa zwrotu za 1 dzie\u0144",return_week:"stopa zwrotu za 1 tydzie\u0144",return_month:"stopa zwrotu za 1 miesi\u0105c",return_six_month:"stopa zwrotu za 6 miesi\u0119cy",return_year:"stopa zwrotu za 1 rok",value_line:"Warto\u015B\u0107 ca\u0142kowita, {start} \u2013 dzi\u015B",value_line_day:"Warto\u015B\u0107 ca\u0142kowita, ostatnie 24 godziny",cash:"Got\xF3wka",cash_plus:"Cash Plus",staked:"{share} w stakingu",show_all:"Poka\u017C wszystkie ({count})",show_less:"Poka\u017C mniej",detail_available:"Dost\u0119pne",detail_staked:"W stakingu",detail_staking_apr:"APR stakingu",detail_average_buy_price:"\u015Arednia cena zakupu",detail_invested:"Zainwestowano",detail_profit_loss:"Zysk / strata",detail_rewards:"Nagrody za staking",detail_rewards_net:"Netto, \u0142\u0105cznie",detail_rewards_worth:"dzi\u015B warte {value}",detail_payouts:"Naliczenia",detail_payouts_value:"{count} \xB7 ostatnio {date}",shares_one:"sztuka",shares_other:"sztuki",shares_few:"sztuki",shares_many:"sztuk",eye_hide:"Ukryj kwoty",eye_show:"Poka\u017C kwoty",change_since:"Zmiana od {date}",ecb_footer:"Ceny w {currency}: ceny Bitpandy w EUR przeliczone po kursie referencyjnym EBC z {date}. Ich zmiana obejmuje ruch kursu.",empty_portfolio:"Skonfiguruj Bitpanda Portfolio, aby zobaczy\u0107 je tutaj.",empty_wallets:"Brak portfeli.",empty_selection_wallets:"Brak portfeli w wyborze tej karty.",empty_selection_assets:"Brak aktyw\xF3w w wyborze tej karty.",empty_price_tracker:"Skonfiguruj Bitpanda Price Tracker i dodaj aktywa, aby zobaczy\u0107 tutaj ceny.",picker_portfolio:"Warto\u015B\u0107 ca\u0142kowita i stopa zwrotu z wykresem, got\xF3wka i Cash Plus, alokacja oraz twoje portfele; ka\u017Cd\u0105 cz\u0119\u015B\u0107 mo\u017Cna ukry\u0107.",picker_price_tracker:"Ceny i zmiany \u015Bledzonych aktyw\xF3w, ka\u017Cde z wykresem, jako lista lub kafelki.",invalid_option:"Nieprawid\u0142owa warto\u015B\u0107 dla \u201E{option}\u201D: {value}. Dozwolone: {allowed}.",allowed_text:"tekst",allowed_devices:"lista identyfikator\xF3w urz\u0105dze\u0144",allowed_groups:"lista warto\u015Bci spo\u015Br\xF3d {values}",group_content:"Zawarto\u015B\u0107",group_wallets:"Portfele",group_assets:"Aktywa",group_appearance:"Wygl\u0105d",opt_title:"Tytu\u0142",opt_title_help:"Pozostaw puste, aby u\u017Cy\u0107 nazwy pokazanej na szaro",opt_timeframe:"Domy\u015Blny okres",opt_timeframe_help:"Przyciski od 1D do 1R na karcie zmieniaj\u0105 go tylko tymczasowo",tfo_day:"1 dzie\u0144",tfo_week:"1 tydzie\u0144",tfo_month:"1 miesi\u0105c",tfo_six_month:"6 miesi\u0119cy",tfo_year:"1 rok",opt_show_cash:"Got\xF3wka i Cash Plus",opt_show_allocation:"Pasek alokacji",opt_show_allocation_help:"Kolorowy pasek pokazuj\u0105cy udzia\u0142 grup aktyw\xF3w i got\xF3wki",opt_show_total:"Warto\u015B\u0107 ca\u0142kowita i stopa zwrotu",opt_show_total_help:"Przyciski okresu pozostaj\u0105, dop\xF3ki wy\u015Bwietlany jest wykres",opt_show_line:"Wykres warto\u015Bci ca\u0142kowitej",opt_show_wallets:"Portfele",opt_group_wallets:"Portfele w grupach aktyw\xF3w",opt_show_search:"Pole wyszukiwania",opt_show_search_help:"Znajduje portfele po nazwie, symbolu lub ISIN",opt_sort:"Sortuj wed\u0142ug",sort_value:"Warto\u015B\u0107",sort_return:"Stopa zwrotu od zakupu",sort_name:"Nazwa",sort_selection:"Kolejno\u015B\u0107 wyboru",sort_change_desc:"Zmiana, najwy\u017Csza najpierw",sort_change_asc:"Zmiana, najni\u017Csza najpierw",opt_sort_help_tracker:"\u201EKolejno\u015B\u0107 wyboru\u201D dzia\u0142a tylko przy opcji \u201ETylko wybrane\u201D dla aktyw\xF3w; w przeciwnym razie wed\u0142ug nazwy",opt_group_selection:"Wy\u015Bwietlane grupy aktyw\xF3w",opt_group_selection_help:"Dotyczy tylko portfeli; warto\u015B\u0107 ca\u0142kowita, got\xF3wka, Cash Plus i alokacja zawsze pokazuj\u0105 ca\u0142e portfolio",opt_groups:"Wybierz grupy aktyw\xF3w",opt_asset_selection:"Wy\u015Bwietlane aktywa",opt_asset_selection_wallets:"Wy\u015Bwietlane portfele",sel_all:"Wszystkie",sel_all_except:"Wszystkie opr\xF3cz wybranych",sel_only:"Tylko wybrane",opt_assets:"Wybierz aktywa",opt_assets_wallets:"Wybierz portfele",opt_assets_help:"Aktywo z ukrytej grupy aktyw\xF3w pozostaje ukryte, nawet je\u015Bli wybrano je tutaj",opt_assets_help_wallets:"Portfel z ukrytej grupy aktyw\xF3w pozostaje ukryty, nawet je\u015Bli wybrano go tutaj",opt_hide_amounts:"Pocz\u0105tkowo ukrywaj kwoty",opt_hide_amounts_help:"Procenty pozostaj\u0105 widoczne; oko u g\xF3ry karty pokazuje kwoty tylko tymczasowo",opt_limit:"Aktywa przed \u201EPoka\u017C wszystkie\u201D",opt_limit_wallets:"Portfele przed \u201EPoka\u017C wszystkie\u201D",opt_limit_help:"0 pokazuje wszystkie aktywa",opt_limit_help_wallets:"Tylko gdy opcja \u201EPortfele w grupach aktyw\xF3w\u201D jest wy\u0142\u0105czona; 0 pokazuje wszystkie",opt_layout:"Poka\u017C jako",layout_list:"Lista",layout_tiles:"Kafelki",opt_currency:"Domy\u015Blna waluta",opt_currency_help:"Przyciski na karcie zmieniaj\u0105 j\u0105 tylko tymczasowo; wi\u0119cej walut przez \u201EKonfiguruj\u201D w Price Trackerze"};var _s={en:cs,de:ls,fr:ps,nl:hs,it:us,es:ds,pl:ms},fs=o=>o in _s,gs="en",bo=o=>{let e=o.toLowerCase().replace(/[-_].*$/,"");return fs(e)?e:"en"};function W(o){let e=o??document.querySelector("home-assistant")?.hass;return e?bo(e.locale.language):gs}function ys(o){return fs(o.locale.language.toLowerCase().replace(/[-_].*$/,""))}function ws(o){gs=W(o)}var vs=o=>_s[W(o)];function h(o,e,t={}){return vs(o)[e].replace(/\{(\w+)\}/g,(s,n)=>n in t?String(t[n]):s)}function bs(o,e,t){let s=new Intl.PluralRules(W(o)).select(t);return vs(o)[`${e}_${s}`]}async function xs(o){await o.loadBackendTranslation("selector","bitpanda")}function kt(o,e){return o.localize(`component.bitpanda.selector.asset_group.options.${e}`)||e}var B=["day","week","month","six_month","year"],L=["crypto","stock","etf","etc","index","metal","other"],O=["all","all_except","only"],ks=["EUR","CHF","CZK","DKK","GBP","HUF","NOK","PLN","RON","SEK","TRY","USD"],$t=["value","return","name"],At=["selection","name","change_desc","change_asc"],St=["list","tiles"];var P=o=>({allowed:()=>o.join(", "),check:e=>typeof e=="string"&&o.includes(e)}),j={allowed:()=>"true, false",check:o=>typeof o=="boolean"},$s={allowed:()=>h(void 0,"allowed_text"),check:o=>typeof o=="string"},He={allowed:()=>"0, 1, 2, \u2026",check:o=>typeof o=="number"&&Number.isInteger(o)&&o>=0},Ie={allowed:()=>h(void 0,"allowed_devices"),check:o=>Array.isArray(o)&&o.every(e=>typeof e=="string")},Me={allowed:()=>h(void 0,"allowed_groups",{values:L.join(", ")}),check:o=>Array.isArray(o)&&o.every(e=>L.includes(e))},As={allowed:()=>"EUR, USD, \u2026",check:o=>typeof o=="string"&&/^[A-Z]{3}$/.test(o)};function We(o,e){if(o===null||typeof o!="object"||Array.isArray(o))throw new Error(h(void 0,"invalid_option",{option:"type",value:JSON.stringify(o),allowed:"custom:\u2026"}));let t=Object.fromEntries(Object.entries(o).filter(([,s])=>s!==null));for(let[s,n]of Object.entries(e)){let r=t[s];if(r!==void 0&&!n.check(r))throw new Error(h(void 0,"invalid_option",{option:s,value:JSON.stringify(r),allowed:n.allowed()}))}return t}var ne=(o,e)=>({select:{mode:"dropdown",options:o.map(t=>({value:t,label:e(t)}))}}),Oe=o=>({name:"title",default:o,selector:{text:{}}}),je=()=>({name:"timeframe",selector:ne(B,o=>h(void 0,`tfo_${o}`))}),D=(o,e)=>({name:o,default:e,selector:{boolean:{}}}),De=o=>({name:"limit",default:o,selector:{number:{min:0,max:100,mode:"box"}}}),Ue=o=>({name:"sort",selector:ne(o,e=>h(void 0,`sort_${e}`))});function re(){return document.querySelector("home-assistant")?.hass}var xo=3e3;async function Be(o){if(!o)return{};let e;try{let s=(await Promise.race([o.callWS({type:"frontend/get_translations",language:o.language,category:"selector",integration:["bitpanda"]}),new Promise(r=>{e=setTimeout(()=>r(void 0),xo)})]))?.resources??{},n={};for(let r of L){let i=s[`component.bitpanda.selector.asset_group.options.${r}`];typeof i=="string"&&i&&(n[r]=i)}return n}catch{return{}}finally{clearTimeout(e)}}var Fe=o=>[{name:"group_selection",selector:ne(O,e=>h(void 0,`sel_${e}`))},{name:"groups",selector:{select:{multiple:!0,mode:"dropdown",options:L.map(e=>({value:e,label:o[e]??e}))}}}],Ve=o=>[{name:"asset_selection",selector:ne(O,e=>h(void 0,`sel_${e}`))},{name:"assets",selector:{device:{multiple:!0,filter:[{integration:"bitpanda",model:o}]}}}],ie=()=>({type:"divider",name:""}),X=(o,e)=>({type:"expandable",name:"",flatten:!0,title:h(void 0,o),schema:e}),ko={title:"opt_title",timeframe:"opt_timeframe",show_total:"opt_show_total",show_graph:"opt_show_line",show_cash:"opt_show_cash",show_allocation:"opt_show_allocation",show_wallets:"opt_show_wallets",group_wallets:"opt_group_wallets",show_search:"opt_show_search",sort:"opt_sort",group_selection:"opt_group_selection",groups:"opt_groups",asset_selection:"opt_asset_selection",assets:"opt_assets",hide_amounts:"opt_hide_amounts",limit:"opt_limit",layout:"opt_layout",currency:"opt_currency"},$o={title:"opt_title_help",timeframe:"opt_timeframe_help",show_total:"opt_show_total_help",show_allocation:"opt_show_allocation_help",hide_amounts:"opt_hide_amounts_help",show_search:"opt_show_search_help",assets:"opt_assets_help",limit:"opt_limit_help",currency:"opt_currency_help"};function qe(o){let e=ko[o.name];return e?h(void 0,e):void 0}function Ge(o){let e=$o[o.name];return e?h(void 0,e):void 0}var Ke=me`
  :host {
    container-type: inline-size;
    --bp-up: var(--success-color, #43a047);
    --bp-down: var(--error-color, #db4437);
    --bp-chip: rgba(var(--rgb-primary-text-color, 33, 33, 33), 0.06);
    --bp-divider: var(--divider-color, rgba(0, 0, 0, 0.12));
    --bp-muted: var(--secondary-text-color, #727272);
    --bp-accent: var(--primary-color, #03a9f4);
    display: block;
  }
  ha-card,
  .card {
    display: block;
    overflow: hidden;
    color: var(--primary-text-color);
  }
  .head {
    display: flex;
    align-items: center;
    padding: 16px 16px 0;
    min-height: 32px;
  }
  .title {
    flex: 1;
    font-size: 16px;
    font-weight: 500;
  }
  .content {
    padding: 8px 16px 16px;
  }
  .icon-btn {
    width: 32px;
    height: 32px;
    border: 0;
    border-radius: 50%;
    padding: 0;
    background: none;
    color: var(--bp-muted);
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    justify-content: center;
  }
  .icon-btn svg {
    width: 20px;
    height: 20px;
    fill: currentColor;
  }
  [role="button"],
  [role="radio"],
  .icon-btn {
    outline: none;
  }
  [role="button"]:focus-visible,
  [role="radio"]:focus-visible,
  .icon-btn:focus-visible {
    box-shadow: 0 0 0 2px var(--bp-accent);
    border-radius: 6px;
  }
  .hero {
    font-size: 32px;
    line-height: 40px;
    letter-spacing: -0.5px;
    cursor: pointer;
  }
  .hero-line {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 4px 8px;
    margin-top: 4px;
  }
  .chip {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 2px 8px;
    border-radius: 12px;
    font-size: 13px;
    font-weight: 500;
    background: var(--bp-chip);
    cursor: pointer;
    white-space: nowrap;
  }
  .chip-amount {
    font-size: 13px;
    font-weight: 500;
    white-space: nowrap;
  }
  .chip-label {
    color: var(--bp-muted);
    font-size: 13px;
    white-space: nowrap;
  }
  .up {
    color: var(--bp-up);
  }
  .down {
    color: var(--bp-down);
  }
  .muted {
    color: var(--bp-muted);
  }
  .switches {
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 8px;
  }
  .seg {
    display: inline-flex;
    border: 1px solid var(--bp-divider);
    border-radius: 18px;
    padding: 2px;
    margin-top: 12px;
  }
  .seg [role="radio"] {
    padding: 4px 12px;
    border-radius: 16px;
    font-size: 13px;
    color: var(--bp-muted);
    cursor: pointer;
    user-select: none;
  }
  .seg [aria-checked="true"] {
    background: color-mix(in srgb, var(--bp-accent) 18%, transparent);
    color: var(--bp-accent);
    font-weight: 500;
  }
  /* The value line, its dashed middle and, while pointed at, a cursor with
     its time and value above and the highest, middle and lowest value at the
     right. A finger moving up or down still scrolls the page. */
  .plot {
    position: relative;
    margin-top: 8px;
    touch-action: pan-y;
  }
  svg.spark {
    display: block;
    width: 100%;
    height: 72px;
  }
  .plot .mid {
    position: absolute;
    left: 0;
    right: 0;
    top: 50%;
    border-top: 1px dashed var(--bp-muted);
    opacity: 0.6;
    pointer-events: none;
  }
  .plot .tag {
    position: absolute;
    right: 0;
    padding: 0 4px;
    border-radius: 4px;
    font-size: 10px;
    line-height: 15px;
    color: var(--bp-muted);
    background: var(--ha-card-background, var(--card-background-color, #1c1c1c));
    pointer-events: none;
  }
  .plot .tag.high {
    top: 0;
  }
  .plot .tag.middle {
    top: 50%;
    transform: translateY(-50%);
  }
  .plot .tag.low {
    bottom: 0;
  }
  .plot .cursor {
    position: absolute;
    top: 0;
    bottom: 0;
    border-left: 1px solid var(--primary-text-color);
    opacity: 0.7;
    pointer-events: none;
  }
  .plot .dot {
    position: absolute;
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: var(--primary-text-color);
    transform: translate(-50%, -50%);
    pointer-events: none;
  }
  .plot .tip {
    position: absolute;
    bottom: calc(100% + 4px);
    z-index: 1;
    transform: translateX(-50%);
    padding: 2px 6px;
    border-radius: 6px;
    font-size: 11px;
    white-space: nowrap;
    color: var(--ha-card-background, var(--card-background-color, #1c1c1c));
    background: var(--primary-text-color);
    pointer-events: none;
  }
  .plot .tip.start {
    transform: none;
  }
  .plot .tip.end {
    transform: translateX(-100%);
  }
  svg.mini {
    display: block;
    width: 96px;
    height: 28px;
  }
  svg .line {
    fill: none;
    stroke: var(--bp-accent);
    stroke-width: 2;
    stroke-linejoin: round;
    stroke-linecap: round;
  }
  svg .area {
    fill: color-mix(in srgb, var(--bp-accent) 20%, transparent);
    stroke: none;
  }
  svg.mini.up .line,
  svg.spark.up .line {
    stroke: var(--bp-up);
  }
  svg.mini.down .line,
  svg.spark.down .line {
    stroke: var(--bp-down);
  }
  svg.mini.flat .line,
  svg.spark.flat .line {
    stroke: var(--bp-muted);
  }
  svg.spark.up .area {
    fill: color-mix(in srgb, var(--bp-up) 20%, transparent);
  }
  svg.spark.down .area {
    fill: color-mix(in srgb, var(--bp-down) 20%, transparent);
  }
  svg.spark.flat .area {
    fill: color-mix(in srgb, var(--bp-muted) 20%, transparent);
  }
  .caption {
    font-size: 11px;
    color: var(--bp-muted);
    text-align: right;
    margin-top: 2px;
  }
  .divider {
    border-top: 1px solid var(--bp-divider);
    margin-top: 12px;
  }
  /* The wallet search: a rounded field, the cross only while there is
     something to clear. */
  .search {
    display: flex;
    align-items: center;
    gap: 6px;
    height: 36px;
    margin-top: 12px;
    padding: 0 6px 0 12px;
    border-radius: 18px;
    background: var(--bp-chip);
    color: var(--bp-muted);
  }
  .search svg {
    width: 20px;
    height: 20px;
    fill: currentColor;
    flex: none;
  }
  .search input {
    flex: 1;
    min-width: 0;
    border: 0;
    outline: 0;
    background: none;
    color: var(--primary-text-color);
    font: inherit;
    font-size: 14px;
  }
  .search input::placeholder {
    color: var(--bp-muted);
  }
  .search:focus-within {
    box-shadow: 0 0 0 2px var(--primary-color);
  }
  .search .clear {
    display: flex;
    padding: 4px;
    border-radius: 50%;
    cursor: pointer;
  }
  .search .clear svg {
    width: 18px;
    height: 18px;
  }
  .search-none {
    margin: 14px 0 4px;
    font-size: 13px;
    color: var(--bp-muted);
  }
  .wallet {
    display: flex;
    align-items: center;
    gap: 6px;
  }
  .wallet .tap {
    flex: 1;
    min-width: 0;
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 8px 0;
    cursor: pointer;
  }
  .wallet .main {
    flex: 1;
    min-width: 0;
  }
  .n {
    font-size: 14px;
    overflow-wrap: anywhere;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }
  /* A wallet's name over two lines takes two of about the same length, as
     in the Price Tracker's list; longer names are still cut after two. */
  .wallet .n {
    text-wrap: balance;
  }
  .s {
    font-size: 12px;
    color: var(--bp-muted);
    margin-top: 2px;
  }
  /* The units may wrap; an ETF's ISIN takes a line of its own if need be. */
  .s .isin {
    white-space: nowrap;
  }
  /* Units and the staked share: below each other, or side by side with the
     share right-aligned when every staked row has room (fitLayout). */
  .sub {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
  }
  /* Only rows with a staked share: a row without one keeps its units free to
     wrap, such as an ETF's units and ISIN. */
  .wallets.stake-inline .sub.staked {
    flex-direction: row;
    align-items: center;
    justify-content: flex-start;
    gap: 8px;
  }
  .wallets.stake-inline .sub.staked > * {
    flex-shrink: 0;
  }
  /* A flex line: the badge sits right below the units, with no line gap
     above it. */
  .stake {
    display: flex;
    margin-top: 3px;
  }
  .wallets.stake-inline .stake {
    margin-top: 2px;
  }
  /* The return chip above the value, beside the units: or, when that is not
     room in every row, below the name, side by side, and when not even that,
     below the name, chip above value (PortfolioCard.fitLayout). */
  .wallet .right {
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    gap: 2px;
    text-align: right;
  }
  .wallets.rows-wrapped .wallet {
    align-items: flex-start;
  }
  .wallets.rows-wrapped .wallet .tap {
    flex-wrap: wrap;
  }
  .wallets.rows-wrapped .wallet .main {
    flex-basis: 100%;
  }
  .wallets.rows-wrapped .wallet .chevron {
    margin: 8px 0 0;
  }
  /* Below the name the row reaches under the chevron, which stands beside
     the name: wider by its width and the gap before it, to where a group's
     sum ends; the negative margin keeps it on a line of its own. */
  .wallets.rows-wrapped .wallet .right {
    flex-basis: calc(100% + 30px);
    margin-right: -30px;
    flex-direction: row;
    justify-content: flex-end;
    align-items: center;
    gap: 8px;
  }
  .wallets.rows-stacked .wallet .right {
    flex-direction: column;
    align-items: flex-end;
    gap: 2px;
  }
  .val {
    font-size: 14px;
    font-variant-numeric: tabular-nums;
    white-space: nowrap;
  }
  .badge {
    display: inline-block;
    line-height: 16px;
    padding: 0 6px;
    border-radius: 8px;
    font-size: 11px;
    background: color-mix(in srgb, var(--bp-up) 18%, transparent);
    color: var(--primary-text-color);
  }
  .chevron {
    width: 24px;
    height: 24px;
    flex: none;
  }
  /* One divider before each shown part after the total, drawn by the card:
     cash and allocation are one part, the wallets the next. */
  .pair {
    display: flex;
    justify-content: space-between;
    margin-top: 12px;
  }
  .pair > div {
    display: flex;
    flex-direction: column;
    cursor: pointer;
  }
  .pair .end {
    text-align: right;
  }
  .pair .k {
    font-size: 12px;
    color: var(--bp-muted);
  }
  .pair .v {
    font-size: 16px;
  }
  .bar {
    display: flex;
    height: 12px;
    border-radius: 6px;
    overflow: hidden;
    margin-top: 14px;
    gap: 2px;
  }
  .legend {
    display: flex;
    flex-wrap: wrap;
    gap: 4px 14px;
    margin-top: 8px;
    font-size: 12px;
    color: var(--bp-muted);
  }
  .legend i {
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    margin-right: 5px;
  }
  .allocation-missing {
    margin-top: 12px;
  }
  .group {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-top: 12px;
    padding: 10px 0 4px;
    border-top: 1px solid var(--bp-divider);
    font-size: 13px;
    font-weight: 500;
    cursor: pointer;
  }
  /* The divider before the wallets stands above the first group. */
  .wallets > .group:first-child {
    margin-top: 0;
    border-top: none;
  }
  /* Name and count, centred beside the chip above the sum. */
  .group .gleft {
    display: flex;
    align-items: center;
    gap: 6px;
    min-width: 0;
  }
  .group .gleft > svg {
    width: 18px;
    height: 18px;
    fill: var(--bp-muted);
    flex: none;
  }
  .group .name {
    flex: none;
  }
  .group .gright {
    margin-left: auto;
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    gap: 2px;
  }
  .group .sum {
    color: var(--bp-muted);
    font-weight: 400;
    white-space: nowrap;
  }
  /* A return in a chip: a group's, a wallet's, a price's change. */
  .gchip,
  .wchip,
  .pchip {
    padding: 1px 6px;
    border-radius: 10px;
    font-size: 12px;
    font-weight: 500;
    background: var(--bp-chip);
    white-space: nowrap;
  }
  .gchip.none,
  .wchip.none,
  .pchip.none {
    background: none;
    color: var(--bp-muted);
  }
  /* Not room in every group: chip and sum below the name, side by side. */
  .wallets.groups-wrapped .group {
    flex-wrap: wrap;
  }
  /* With the line to itself, a name that still does not fit is cut. */
  .wallets.groups-wrapped .group .gleft {
    max-width: 100%;
  }
  .wallets.groups-wrapped .group .name {
    flex: 0 1 auto;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .wallets.groups-wrapped .group .gright {
    flex-basis: 100%;
    flex-direction: row;
    justify-content: flex-end;
    align-items: center;
    gap: 8px;
  }
  /* Not room for that row in every group either: chip above sum again,
     below the name. */
  .wallets.groups-stacked .group .gright {
    flex-direction: column;
    align-items: flex-end;
    gap: 2px;
  }
  .count {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 20px;
    height: 20px;
    padding: 0 6px;
    border-radius: 10px;
    font-size: 12px;
    font-weight: 500;
    color: var(--bp-muted);
    background: color-mix(in srgb, var(--bp-muted) 18%, transparent);
    box-sizing: border-box;
  }
  .members .wallet {
    padding-left: 24px;
  }
  .chevron svg {
    width: 24px;
    height: 24px;
    fill: var(--bp-muted);
  }
  /* As wide as the row it belongs to: the full width in the list, indented
     like its row inside an open group. */
  .detail {
    margin: 0 0 8px;
    padding: 10px 12px;
    border-radius: 8px;
    background: var(--bp-chip);
    font-size: 12px;
  }
  .members .detail {
    margin-left: 24px;
  }
  /* Labels stay on one line; a long value wraps instead. */
  .detail .grid {
    display: grid;
    grid-template-columns: auto minmax(0, 1fr);
    gap: 4px 12px;
  }
  .detail .grid > span:nth-child(odd) {
    color: var(--bp-muted);
    white-space: nowrap;
  }
  .detail .grid > span:nth-child(even) {
    text-align: right;
    overflow-wrap: anywhere;
  }
  /* A value breaks only at its middle dots. */
  .detail .part {
    white-space: nowrap;
  }
  .detail h4 {
    margin: 8px 0 4px;
    font-size: 12px;
    font-weight: 500;
  }
  .amount.blur {
    filter: blur(6px);
  }
  .empty {
    padding: 16px;
    color: var(--bp-muted);
  }
  .show-all {
    display: block;
    width: 100%;
    background: none;
    border: 0;
    border-top: 1px solid var(--bp-divider);
    font: inherit;
    text-align: center;
    color: var(--bp-accent);
    font-weight: 500;
    padding: 10px 0 2px;
    margin-top: 4px;
    cursor: pointer;
  }
  /* Narrow cards: a half-section card on a phone, or a small section. */
  @container (max-width: 340px) {
    .hero {
      font-size: 26px;
      line-height: 32px;
    }
    .seg [role="radio"] {
      padding: 4px 8px;
    }
  }
  /* Narrow cards: each detail label above its value, which then has the
     whole width. */
  @container (max-width: 280px) {
    .detail .grid {
      grid-template-columns: minmax(0, 1fr);
      gap: 0;
    }
    .detail .grid > span:nth-child(even) {
      text-align: left;
      margin-bottom: 6px;
    }
  }
  /* Very narrow cards, such as half a section in a four-column dashboard. */
  @container (max-width: 240px) {
    .hero {
      font-size: 22px;
      line-height: 28px;
    }
    /* A part alone may not fit a line here. */
    .detail .part {
      white-space: normal;
    }
    .seg [role="radio"] {
      padding: 4px 4px;
      font-size: 12px;
    }
  }
`;var Ze={title:$s},F=class extends U{constructor(){super(...arguments);this.timeframe="day";this.amountsHidden=!1;this.seriesRevision=0;this.watched=[]}static{this.properties={hass:{attribute:!1},config:{state:!0},timeframe:{state:!0},amountsHidden:{state:!0},seriesRevision:{state:!0}}}static{this.styles=Ke}setConfig(t){let s=this.validate(t),n=s;this.config=s,this.timeframe=n.timeframe??"day",this.amountsHidden=n.hide_amounts??!1}toggleAmounts(){this.amountsHidden=!this.amountsHidden}seriesArrived(){this.seriesRevision+=1}selectTimeframe(t){this.timeframe=t}shouldUpdate(t){if(t.size!==1||!t.has("hass"))return!0;let s=t.get("hass"),n=this.hass;return!s||!n||s.entities!==n.entities||s.devices!==n.devices||s.locale!==n.locale||s.localize!==n.localize?!0:this.watched.some(r=>s.states[r]!==n.states[r])}connectedCallback(){super.connectedCallback(),typeof ResizeObserver<"u"&&(this.resizer=new ResizeObserver(()=>this.fitLayout()),this.resizer.observe(this))}disconnectedCallback(){this.resizer?.disconnect(),this.resizer=void 0,super.disconnectedCallback()}updated(t){super.updated(t),this.remeasures(t)&&this.fitLayout()}fitLayout(){}remeasures(t){return!0}willUpdate(t){let s=this.hass;if(!s)return;ws(s);let n=W(s);n!==this.categoryLanguage&&(this.categoryLanguage=n,xs(s)),this.watched=this.watchedEntities()}getCardSize(){return 3}getGridOptions(){return{columns:12,min_columns:6}}};var Ao="bitpanda",Ss={return_day:"day",return_week:"week",return_month:"month",return_six_month:"six_month",return_year:"year"},Cs=o=>o.replace(/\s+/g,"").toLowerCase();function So(o,e){let t=(o??"").trim();return t&&Cs(t)!==Cs(e)?`${t} (${e})`:e}function Ct(o,e){let t=new Map;for(let n of Object.values(o.entities)){if(!n||n.platform!==Ao||!n.device_id)continue;let r=t.get(n.device_id)??[];r.push(n),t.set(n.device_id,r)}let s=[];for(let[n,r]of t){let i=o.devices[n];i?.model===e&&s.push([i,r])}return s}var Q=o=>typeof o=="string"&&o!==""?o:void 0,Ts=new Map,Co=/ (Wallet|Price Tracker)$/;function Ps(o,e,t){let s=t.map(i=>o.states[i.entity_id]?.attributes).find(i=>i?.asset),n;if(s){let i=Q(s.asset)??"",l=Q(s.asset_isin),a=Q(s.asset_category),c=Q(s.asset_name);n={name:So(c,i),shortName:c??i,symbol:i,...l?{isin:l}:{},...a&&L.includes(a)?{category:a}:{}},Ts.set(e.id,n)}else{let i=(Q(e.name)??"").replace(Co,"");n=Ts.get(e.id)??{name:i,shortName:i,symbol:""}}let r=Q(e.name_by_user);return{deviceId:e.id,assetId:e.serial_number??"",...n,...r?{name:r,shortName:r}:{}}}function Ye(o){let[e]=Ct(o,"Portfolio");if(!e)return;let[t,s]=e,n={deviceId:t.id,returns:{},wallets:[]};for(let r of s){let i=r.translation_key??"";i==="total_value"?n.totalValue=r.entity_id:i==="cash"?n.cash=r.entity_id:i==="cash_plus"?n.cashPlus=r.entity_id:i in Ss&&(n.returns[Ss[i]]=r.entity_id)}for(let[r,i]of Ct(o,"Wallet")){let l=Ps(o,r,i);for(let a of i)a.translation_key==="wallet"?l.available=a.entity_id:a.translation_key==="wallet_total"?l.total=a.entity_id:a.translation_key==="staking"&&(l.staking=a.entity_id);n.wallets.push(l)}return n}function ve(o){return Ct(o,"Price Tracker").map(([e,t])=>{let s={};for(let n of t){if(n.translation_key!=="price")continue;let r=Q(o.states[n.entity_id]?.attributes.unit_of_measurement);r&&(s[r]=n.entity_id)}return{...Ps(o,e,t),prices:s}})}function Je(o){let e=new Set(o.flatMap(s=>Object.keys(s.prices))),t=[...e].filter(s=>s!=="EUR").sort();return e.has("EUR")?["EUR",...t]:t}function Xe(o,e,t){if(e==="all")return[...o];let s=e==="only";return o.filter(n=>t.includes(n.category??"other")===s)}function Qe(o,e,t){return e==="all_except"?o.filter(s=>!t.includes(s.deviceId)):e==="only"?t.map(s=>o.find(n=>n.deviceId===s)).filter(s=>s!==void 0):[...o]}function et(o){switch(o.locale.number_format){case"comma_decimal":return"en-US";case"decimal_comma":return"de";case"space_comma":return"fr";case"quote_decimal":return"de-CH";case"system":return;default:return o.locale.language}}function Tt(o,e,t,s=0){return new Intl.NumberFormat(et(o),{maximumFractionDigits:t,minimumFractionDigits:s,useGrouping:o.locale.number_format!=="none"}).format(e)}function To(o,e){let t=e!==0&&Math.abs(e)<1e-4;return new Intl.NumberFormat(et(o),{...t?{maximumSignificantDigits:2}:{maximumFractionDigits:4},roundingMode:"trunc",useGrouping:o.locale.number_format!=="none"}).format(e)}function be(o,e,t,s,n=!1){let r=n?To(o,e):Tt(o,e,8);return t==="stock"||t==="etf"||t==="etc"?`${r} ${bs(o,"shares",e)}`:`${r} ${t==="metal"?"g":s}`}var Pt=new Set(["unavailable","unknown"]);function N(o,e){let t=e?o.states[e]:void 0;return t&&!Pt.has(t.state)?o.formatEntityState(t):void 0}function Rs(o,e,t){let s=e?o.states[e]:void 0;return s&&t!==void 0?o.formatEntityState({...s,state:String(t)}):void 0}function xe(o,e,t,s=!1){return zs(o,e,t,2,s)}function Es(o,e,t){let s=Math.abs(e);return zs(o,e,t,s>=10||s===0?2:s>=1?4:8,!1)}function zs(o,e,t,s,n){try{return new Intl.NumberFormat(et(o),{style:"currency",currency:t,minimumFractionDigits:2,maximumFractionDigits:s,useGrouping:o.locale.number_format!=="none",...n?{signDisplay:"exceptZero"}:{}}).format(e)}catch{return`${Tt(o,e,s)} ${t}`}}function Po(o){let e=Math.abs(o);return e===0||e>=10?2:e>=1?4:e>=.1?5:e>=.001?6:e>=1e-4?7:8}function Ls(o,e,t){let s=e?o.states[e]:void 0;if(!s||Pt.has(s.state)||t===void 0||!Number.isFinite(t))return;let n=o.entities[s.entity_id]?.display_precision,r=typeof n=="number"?n:Po(Number(s.state)),i=Number(t.toFixed(r))===0?0 .toFixed(r):t.toFixed(r),l=o.formatEntityState({...s,state:i});return Number(i)>0?`+${l}`:l}function $(o,e){let t=e?o.states[e]:void 0;if(!t||Pt.has(t.state)||t.state.trim()==="")return;let s=Number(t.state);return Number.isFinite(s)?s:void 0}var Ro=new Set(["cs","de","fi","fr","sk","sv"]),Ns=o=>Ro.has(o.locale.language)?"\xA0":"";function H(o,e){if(e===void 0||!Number.isFinite(e))return{text:"\u2014",direction:"none"};let t=new Intl.NumberFormat(et(o),{minimumFractionDigits:2,maximumFractionDigits:2,signDisplay:"exceptZero",useGrouping:o.locale.number_format!=="none"}).format(e),s=Ns(o),r=Math.round(Math.abs(e)*100)===0?"flat":e>0?"up":"down";return{text:`${t}${s}%`,direction:r}}function ae(o,e,t){let s=Ns(o);return`${Tt(o,e,t)}${s}%`}function R(o){return o==="up"||o==="down"?o:""}function ee(o){return o==="up"?"\u25B2":o==="down"?"\u25BC":""}function Rt(o){return ys(o)?o.locale.language:"en"}function Hs(o){return o.locale.time_zone==="server"?o.config?.time_zone:void 0}function Eo(o){let e=o.locale.time_format;return e==="12"||e==="24"?e==="12":new Date("January 1, 2023 22:00:00").toLocaleString(e==="system"?void 0:o.locale.language).includes("10")}function ke(o,e){let t=Hs(o),s=r=>new Intl.DateTimeFormat("en",{year:"numeric",timeZone:t}).format(r),n=s(e)===s(Date.now())?{}:{year:"numeric"};return new Intl.DateTimeFormat(Rt(o),{day:"numeric",month:"short",...n,timeZone:t}).format(e)}function Is(o,e){let t=/^(\d{4})-(\d{2})-(\d{2})$/.exec(e);if(!t)return;let s=Date.UTC(Number(t[1]),Number(t[2])-1,Number(t[3]));return new Intl.DateTimeFormat(Rt(o),{day:"numeric",month:"long",timeZone:"UTC"}).format(s)}function tt(o,e){let t=Eo(o);return new Intl.DateTimeFormat(Rt(o),{day:"numeric",month:"short",hour:t?"numeric":"2-digit",minute:"2-digit",hourCycle:t?"h12":"h23",timeZone:Hs(o)}).format(e)}var{I:yr}=is;var Ms=o=>o.strings===void 0;var Ws={ATTRIBUTE:1,CHILD:2,PROPERTY:3,BOOLEAN_ATTRIBUTE:4,EVENT:5,ELEMENT:6},Et=o=>(...e)=>({_$litDirective$:o,values:e}),st=class{constructor(e){}get _$AU(){return this._$AM._$AU}_$AT(e,t,s){this._$Ct=e,this._$AM=t,this._$Ci=s}_$AS(e,t){return this.update(e,t)}update(e,t){return this.render(...t)}};var $e=(o,e)=>{let t=o._$AN;if(t===void 0)return!1;for(let s of t)s._$AO?.(e,!1),$e(s,e);return!0},ot=o=>{let e,t;do{if((e=o._$AM)===void 0)break;t=e._$AN,t.delete(o),o=e}while(t?.size===0)},Os=o=>{for(let e;e=o._$AM;o=e){let t=e._$AN;if(t===void 0)e._$AN=t=new Set;else if(t.has(o))break;t.add(o),No(e)}};function zo(o){this._$AN!==void 0?(ot(this),this._$AM=o,Os(this)):this._$AM=o}function Lo(o,e=!1,t=0){let s=this._$AH,n=this._$AN;if(n!==void 0&&n.size!==0)if(e)if(Array.isArray(s))for(let r=t;r<s.length;r++)$e(s[r],!1),ot(s[r]);else s!=null&&($e(s,!1),ot(s));else $e(this,o)}var No=o=>{o.type==Ws.CHILD&&(o._$AP??=Lo,o._$AQ??=zo)},nt=class extends st{constructor(){super(...arguments),this._$AN=void 0}_$AT(e,t,s){super._$AT(e,t,s),Os(this),this.isConnected=e._$AU}_$AO(e,t=!0){e!==this.isConnected&&(this.isConnected=e,e?this.reconnected?.():this.disconnected?.()),t&&($e(this,e),ot(this))}setValue(e){if(Ms(this._$Ct))this._$Ct._$AI(e,this);else{let t=[...this._$Ct._$AH];t[this._$Ci]=e,this._$Ct._$AI(t,this,0)}}disconnected(){}reconnected(){}};var js=()=>new Lt,Lt=class{},zt=new WeakMap,Ds=Et(class extends nt{render(o){return m}update(o,[e]){let t=e!==this.G;return t&&this.rt(void 0),(t||this.lt!==this.ct)&&(this.G=e,this.ht=o.options?.host,this.rt(this.ct=o.element)),m}rt(o){if(this.G!==void 0)if(this.isConnected||(o=void 0),typeof this.G=="function"){let e=this.ht??globalThis,t=zt.get(e);t===void 0&&(t=new WeakMap,zt.set(e,t)),t.get(this.G)!==void 0&&this.G.call(this.ht,void 0),t.set(this.G,o),o!==void 0&&this.G.call(this.ht,o)}else this.G.value=o}get lt(){return typeof this.G=="function"?zt.get(this.ht??globalThis)?.get(this.G):this.G?.value}disconnected(){this.lt===this.ct&&this.rt(void 0)}reconnected(){this.rt(this.ct)}});var Ho="M12,9A3,3 0 0,0 9,12A3,3 0 0,0 12,15A3,3 0 0,0 15,12A3,3 0 0,0 12,9M12,17A5,5 0 0,1 7,12A5,5 0 0,1 12,7A5,5 0 0,1 17,12A5,5 0 0,1 12,17M12,4.5C7,4.5 2.73,7.61 1,12C2.73,16.39 7,19.5 12,19.5C17,19.5 21.27,16.39 23,12C21.27,7.61 17,4.5 12,4.5Z",Io="M11.83,9L15,12.16C15,12.11 15,12.05 15,12A3,3 0 0,0 12,9C11.94,9 11.89,9 11.83,9M7.53,9.8L9.08,11.35C9.03,11.56 9,11.77 9,12A3,3 0 0,0 12,15C12.22,15 12.44,14.97 12.65,14.92L14.2,16.47C13.53,16.8 12.79,17 12,17A5,5 0 0,1 7,12C7,11.21 7.2,10.47 7.53,9.8M2,4.27L4.28,6.55L4.73,7C3.08,8.3 1.78,10 1,12C2.73,16.39 7,19.5 12,19.5C13.55,19.5 15.03,19.2 16.38,18.66L16.81,19.08L19.73,22L21,20.73L3.27,3M12,7A5,5 0 0,1 17,12C17,12.64 16.87,13.26 16.64,13.82L19.57,16.75C21.07,15.5 22.27,13.86 23,12C21.27,7.61 17,4.5 12,4.5C10.6,4.5 9.26,4.75 8,5.2L10.17,7.35C10.74,7.13 11.35,7 12,7Z",Bs="M7.41,8.58L12,13.17L16.59,8.58L18,10L12,16L6,10L7.41,8.58Z",Fs="M7.41,15.41L12,10.83L16.59,15.41L18,14L12,8L6,14L7.41,15.41Z",Mo="M8.59,16.58L13.17,12L8.59,7.41L10,6L16,12L10,18L8.59,16.58Z",Wo="M9.5,3A6.5,6.5 0 0,1 16,9.5C16,11.11 15.41,12.59 14.44,13.73L14.71,14H15.5L20.5,19L19,20.5L14,15.5V14.71L13.73,14.44C12.59,15.41 11.11,16 9.5,16A6.5,6.5 0 0,1 3,9.5A6.5,6.5 0 0,1 9.5,3M9.5,5C7,5 5,7 5,9.5C5,12 7,14 9.5,14C12,14 14,12 14,9.5C14,7 12,5 9.5,5Z",Oo="M19,6.41L17.59,5L12,10.59L6.41,5L5,6.41L10.59,12L5,17.59L6.41,19L12,13.41L17.59,19L19,17.59L13.41,12L19,6.41Z",le=o=>oe`<svg viewBox="0 0 24 24" aria-hidden="true"><path d=${o}></path></svg>`,Nt={down:Bs,up:Fs,right:Mo};function T(o){return e=>{(e.key==="Enter"||e.key===" ")&&(e.preventDefault(),o())}}function ce(o,e){o.dispatchEvent(new CustomEvent("hass-more-info",{bubbles:!0,composed:!0,detail:{entityId:e}}))}function de(o,e){let t=o.filter(s=>s.second!==void 0);return t.length>0&&t.every(s=>s.first+e+s.second<=s.room)}function A(o,e){return p`<span class="amount ${e?"blur":""}">${o??"\u2014"}</span>`}function te(o){return p`<div class="empty">${o}</div>`}function Ae(o,e,t){return p`<div class="head">
    <div class="title">${e}</div>
    ${t?p`<button
          class="icon-btn eye"
          aria-label=${h(o,t.hidden?"eye_show":"eye_hide")}
          title=${h(o,t.hidden?"eye_show":"eye_hide")}
          @click=${t.toggle}
        >
          ${le(t.hidden?Io:Ho)}
        </button>`:m}
  </div>`}function Vs(o,e,t,s,n){let{text:r,direction:i}=H(o,e),l=ee(i);return p`<div class="hero-line">
    <span class="chip ${R(i)}" role="button" tabindex="0" @click=${s} @keydown=${T(s)}
      >${l?`${l} `:""}${r}</span
    >
    ${i!=="none"&&n?.text?p`<span class="chip-amount ${R(i)}">${A(n.text,n.hidden)}</span>`:m}
    <span class="chip-label">${h(o,`return_${t}`)}</span>
  </div>`}function qs(o,e,t,s,n){return p`<div class="seg" role="radiogroup" aria-label=${o} @keydown=${i=>{let l=i.key==="ArrowRight"||i.key==="ArrowDown"?1:i.key==="ArrowLeft"||i.key==="ArrowUp"?-1:0;if(l===0)return;i.preventDefault();let a=(e.indexOf(t)+l+e.length)%e.length;n(e[a]),i.currentTarget.querySelectorAll("[role=radio]")[a]?.focus()}}>
    ${e.map(i=>p`<span
          role="radio"
          aria-checked=${i===t?"true":"false"}
          tabindex=${i===t?0:-1}
          @click=${()=>n(i)}
          @keydown=${T(()=>n(i))}
          >${s(i)}</span
        >`)}
  </div>`}function rt(o,e,t){return qs(h(o,"aria_timeframe"),B,e,s=>h(o,`tf_${s}`),t)}function Gs(o,e,t,s){return e.length<2?null:qs(h(o,"aria_currency"),e,t,n=>n,s)}var jo=new Set(["unavailable","unknown"]);function k(o,e){if(!o||jo.has(o.state))return;let t=o.attributes[e];return typeof t=="number"&&Number.isFinite(t)?t:void 0}function Ks(o,e,t){let s=js(),n=()=>{t(""),s.value?.focus()};return p`<div class="search" role="search">
    ${le(Wo)}<input
      ${Ds(s)}
      type="text"
      .value=${e}
      placeholder=${h(o,"search_placeholder")}
      aria-label=${h(o,"aria_search")}
      autocomplete="off"
      spellcheck="false"
      @input=${r=>t(r.target.value)}
    />${e?p`<span class="clear" role="button" tabindex="0" aria-label=${h(o,"aria_search_clear")} @click=${n} @keydown=${T(n)}
          >${le(Oo)}</span
        >`:m}
  </div>`}var Do={\u00DF:"ss",\u00F8:"o",\u00E6:"ae",\u0153:"oe",\u0142:"l",\u0111:"d",\u00F0:"d",\u00FE:"th",\u0131:"i"};function Us(o){return o.normalize("NFD").replace(/\p{M}/gu,"").toLowerCase().replace(/[ßøæœłđðþı]/gu,e=>Do[e]??e).replace(/[^\p{L}\p{N}\s]/gu,"")}function Zs(o,e){let t=Us(e).split(/\s+/).filter(Boolean),s=Us(`${o.name} ${o.symbol} ${o.isin??""}`);return t.length>0&&t.every(n=>s.includes(n))}function Ys(o){let{hass:e,wallet:t,hidden:s,onTap:n,chevron:r}=o,i=t.total?e.states[t.total]:void 0,l=k(i,"units"),a=$(e,t.total),c=$(e,t.staking),u=a&&c&&c>0?c/a*100:void 0,{text:d,direction:_}=H(e,k(i,"total_return_percent")),f=ee(_),v=_==="none"?p`<span class="wchip none">—</span>`:p`<span class="wchip ${R(_)}">${f?`${f} `:""}${d}</span>`,y=u===void 0?m:p`<div class="stake"><span class="badge">${h(e,"staked",{share:ae(e,u,0)})}</span></div>`,g=x=>{x.stopPropagation(),r?.toggle()};return p`<div class="wallet">
    <div class="tap" role="button" tabindex="0" @click=${n} @keydown=${T(n)}>
      <div class="main">
        <div class="n" title=${t.shortName}>${t.shortName}</div>
        <div class="sub ${u===void 0?"":"staked"}">
          <div class="s">
            <span class="units"
              >${A(l===void 0?void 0:be(e,l,t.category,t.symbol,!0),s)}</span
            >${t.isin?p` · <span class="isin">${t.isin}</span>`:m}
          </div>
          ${y}
        </div>
      </div>
      <div class="right">${v}<span class="val">${A(N(e,t.total),s)}</span></div>
    </div>
    ${r?p`<span
          class="chevron"
          role="button"
          tabindex="0"
          aria-expanded=${r.open?"true":"false"}
          @click=${g}
          @keydown=${x=>{x.stopPropagation(),T(r.toggle)(x)}}
          >${le(r.open?Fs:Bs)}</span
        >`:m}
  </div>`}function it(o,e,t){let s=i=>$(o,i.total)??Number.NEGATIVE_INFINITY,n=i=>k(i.total?o.states[i.total]:void 0,"total_return_percent")??Number.NEGATIVE_INFINITY,r=(i,l)=>i.name.localeCompare(l.name,W(o));return[...e].sort((i,l)=>t==="name"?r(i,l):(t==="value"?s(l)-s(i):n(l)-n(i))||r(i,l))}var Uo=window.customElements,Bo=1e4;function Fo(o=()=>window.customElements,e=Uo,t=Bo){let s=Date.now();return new Promise(n=>{let r=()=>{let i=o();i!==e||i.get("home-assistant")||Date.now()-s>=t?n(i):setTimeout(r,50)};r()})}var Vo="https://github.com/Spegeli/hacs_bitpanda#-dashboard-cards";function qo(o,e,t,s,n={}){let r=o.entities[e];return!r||r.platform!=="bitpanda"||!r.device_id?null:(typeof t=="string"?[t]:t).includes(o.devices[r.device_id]?.model??"")?{config:{type:`custom:${s}`,...n}}:null}function at(o,e,t){Fo().then(r=>{r.get(o)||r.define(o,e)});let s=window;if(s.customCards??=[],s.customCards.some(r=>r.type===o))return;let{model:n}=t;s.customCards.push({type:o,name:t.name,get description(){return t.description()},preview:!0,documentationURL:Vo,...n?{getEntitySuggestion:(r,i)=>qo(r,i,n,o,e.getStubConfig?.())}:{}})}var Go={day:[864e5,"5minute"],week:[6048e5,"hour"],month:[2592e6,"hour"],six_month:[157248e5,"day"],year:[31536e6,"day"]};function lt(o){return o==="5minute"?5*6e4:o==="hour"?36e5:864e5}function Js(o){return o.timeframe==="month"?(o.end-o.start)/120:0}function ue(o,e){let[t,s]=Go[o];return{timeframe:o,start:e-t,end:e,period:s}}var Ko=o=>typeof o=="number"?o:Date.parse(o);async function Zo(o,e,t){if(e.length===0)return{};let s;try{s=await o.callWS({type:"recorder/statistics_during_period",start_time:new Date(t.start).toISOString(),end_time:new Date(t.end).toISOString(),statistic_ids:[...e],period:t.period,types:["state"]})}catch{return}let n={};for(let[r,i]of Object.entries(s))n[r]=i.map(l=>({t:Ko(l.start),v:l.state})).filter(l=>typeof l.v=="number"&&Number.isFinite(l.t)).sort((l,a)=>l.t-a.t);return n}var ct="portfolio";async function Xs(o,e,t){let s;try{s=await o.callWS({type:"bitpanda/portfolio_history",timeframe:t.timeframe})}catch{return}let r=(Array.isArray(s?.points)?s.points:[]).filter(i=>Array.isArray(i)&&typeof i[0]=="number"&&typeof i[1]=="number"&&Number.isFinite(i[0])&&Number.isFinite(i[1])).map(([i,l])=>({t:i,v:l})).sort((i,l)=>i.t-l.t);return{[ct]:r}}var pe=class{constructor(e,t=Zo){this.onUpdate=e;this.fetch=t;this.key="";this.end=0;this.latest=0;this.current={}}request(e,t,s,n=""){let r=`${s.timeframe}|${[...t].sort().join(",")}|${n}`;if(r===this.key&&s.end-this.end<lt(s.period))return;s.timeframe!==this.timeframe&&(this.current={}),this.key=r,this.timeframe=s.timeframe,this.end=s.end;let i=++this.latest;this.fetch(e,t,s).then(l=>{if(i===this.latest){if(l===void 0){this.key="";return}this.current=l,this.onUpdate()}})}series(e){return this.current[e]}};function Qs(o,e,t){let s=lt(t.period),n=o.find(r=>r.t>=t.start-s);if(!(e===void 0||n===void 0||n.v===0))return{change:(e-n.v)/n.v*100,amount:e-n.v,...n.t>t.start+s?{since:n.t}:{}}}var eo=2,Ht=o=>Math.round(o*100)/100;function It(o,e,t,s){return Ht(t===e?s/2:s-eo-(o-e)/(t-e)*(s-2*eo))}function to(o,e){let t=0;return o.forEach((s,n)=>{Math.abs(s.t-e)<Math.abs(o[t].t-e)&&(t=n)}),t}function Yo(o,e){if(e<=0||o.length<3)return o;let t=n=>Math.floor(n.t/e),s=[];for(let n of o.slice(0,-1)){let r=s[s.length-1];(!r||t(n)!==t(r))&&s.push(n)}return s.push(o[o.length-1]),s}function so(o,e,t,s,n,r=0){let i=n??1.5*lt(e.period),l=[],a;for(let g of o)(!a||g.t-a.t>i)&&l.push([]),l[l.length-1]?.push(g),a=g;let c=l.map(g=>Yo(g,r)),u=c.flat().map(g=>g.v),d=Math.min(...u),_=Math.max(...u),f=e.end-e.start,v=g=>Ht((g-e.start)/f*t),y=g=>It(g,d,_,s);return c.map(g=>g.map(x=>[v(x.t),y(x.v)]))}function Jo(o,e,t,s,n,r=0){return so(o,e,t,s,n,r).map(i=>i.length===1?`M${i[0]?.[0]},${i[0]?.[1]}l0.01,0`:i.map(([l,a],c)=>`${c===0?"M":"L"}${l},${a}`).join("")).join("")}function Xo(o,e,t,s,n,r=0){return so(o,e,t,s,n,r).map(i=>{let l=i[0],a=i[i.length-1];return`M${l[0]},${s}${i.map(([c,u])=>`L${c},${u}`).join("")}L${a[0]},${s}Z`}).join("")}var Mt=(o,e)=>o.length>0&&o[o.length-1].t-o[0].t>=(e.end-e.start)/10;function dt(o,e,t){let{width:s,height:n,fill:r,className:i,gapMs:l,stepMs:a}=t;return Mt(o,e)?oe`<svg class=${i} viewBox="0 0 ${s} ${n}" preserveAspectRatio="none" aria-hidden="true">${r?oe`<path class="area" d=${Xo(o,e,s,n,l,a)}></path>`:null}<path class="line" d=${Jo(o,e,s,n,l,a)} vector-effect="non-scaling-stroke"></path></svg>`:oe`<svg class=${i} viewBox="0 0 ${s} ${n}" preserveAspectRatio="none" aria-hidden="true"></svg>`}var Qo=480,Wt=72,pt=o=>`${(o*100).toFixed(2)}%`;function en(o,e,t){let{hass:s,refs:n,window:r,hidden:i,cursor:l,onCursor:a}=o,c=e.map(b=>b.v),u=Math.min(...c),d=Math.max(...c),_=r.end-r.start,f=b=>{let w=b.currentTarget.getBoundingClientRect(),z=Math.min(Math.max((b.clientX-w.left)/w.width,0),1);return to(e,r.start+z*_)},v=b=>a(f(b)),y=()=>a(void 0),g=b=>{b.pointerType!=="mouse"&&y()},x=n.totalValue?s.states[n.totalValue]?.attributes.unit_of_measurement:void 0,S=typeof x=="string"&&!i?b=>xe(s,b,x):void 0,C=l===void 0?void 0:e[l],E=m;if(C){let b=(C.t-r.start)/_,w=r.timeframe==="day"||r.timeframe==="week"?tt(s,C.t):ke(s,C.t),z=b<.25?"start":b>.75?"end":"";E=p`${S?p`<span class="tag high">${S(d)}</span><span class="tag middle">${S((d+u)/2)}</span
            ><span class="tag low">${S(u)}</span>`:m}
      <div class="cursor" style="left:${pt(b)}"></div>
      <div class="dot" style="left:${pt(b)};top:${pt(It(C.v,u,d,Wt)/Wt)}"></div>
      <div class="tip ${z}" style="left:${pt(b)}">${S?`${w} \xB7 ${S(C.v)}`:w}</div>`}let V=dt(e,r,{width:Qo,height:Wt,fill:!0,className:`spark ${t}`,gapMs:Number.POSITIVE_INFINITY});return Mt(e,r)?p`<div class="plot" @pointerdown=${v} @pointermove=${v} @pointerup=${g} @pointercancel=${y} @pointerleave=${y}>
    ${V}
    <div class="mid"></div>
    ${E}
  </div>`:p`<div class="plot">${V}</div>`}function tn(o,e,t){if(e.timeframe==="day")return h(o,"value_line_day");let s=t[0]?.t??e.start;return h(o,"value_line",{start:ke(o,Math.max(e.start,s))})}function sn(o,e,t){let s=$(o,e.totalValue),n=$(o,e.returns[t]),r=e.totalValue?o.states[e.totalValue]?.attributes.unit_of_measurement:void 0;if(!(s===void 0||n===void 0||n<=-100||typeof r!="string"))return xe(o,s*n/(100+n),r,!0)}function oo(o){let{host:e,hass:t,refs:s,timeframe:n,hidden:r,window:i,points:l}=o,a=$(t,s.returns[n]),c=R(H(t,a).direction)||"flat",u=d=>()=>{d&&ce(e,d)};return p`${o.total?p`<div class="hero" role="button" tabindex="0" @click=${u(s.totalValue)} @keydown=${T(u(s.totalValue))}>
            ${A(N(t,s.totalValue),r)}
          </div>
          ${Vs(t,a,n,u(s.returns[n]),{text:sn(t,s,n),hidden:r})}`:m}
    ${o.total||o.line?rt(t,n,o.onTimeframe):m}
    ${o.line&&l&&l.length>0?p`${en(o,l,c)}
          <div class="caption">${tn(t,i,l)}</div>`:m}`}var on="bitpanda-portfolio-card",no={crypto:"var(--blue-color, #4269d0)",stock:"var(--indigo-color, #3f51b5)",etf:"var(--amber-color, #efb118)",etc:"var(--cyan-color, #00bcd4)",index:"var(--purple-color, #a463f2)",metal:"var(--green-color, #3ca951)",other:"var(--pink-color, #ff8ab7)",cash_plus:"var(--deep-orange-color, #ff725c)",cash:"var(--teal-color, #6cc5b0)"},ro=o=>o.category??"other",nn={limit:"opt_limit_wallets",asset_selection:"opt_asset_selection_wallets",assets:"opt_assets_wallets"},rn={limit:"opt_limit_help_wallets",group_selection:"opt_group_selection_help",assets:"opt_assets_help_wallets"},an=(o,e)=>Qe(Xe(o.wallets,e.group_selection??"all",e.groups??[]),e.asset_selection??"all",e.assets??[]);function ln(o,e){let t=0,s=0;for(let n of e){let r=$(o,n.total),i=k(n.total?o.states[n.total]:void 0,"invested_amount");if(r===void 0||i===void 0)return;t+=r,s+=i}return s>0?(t-s)/s*100:void 0}function io(o){let e=o.map(s=>({room:s.room,first:s.left,second:Math.max(s.chip??0,s.value)}));if(o.length===0||de(e,cn))return"beside";let t=o.flatMap(s=>s.chip===void 0?[]:[{room:s.below??s.room,first:s.chip,second:s.value}]);return t.length===0||de(t,dn)?"row":"stacked"}function Ot(o){if(!o.some(e=>e===void 0))return Math.round(o.reduce((e,t)=>e+t,0)*1e8)/1e8}var jt="\xA0\xB7 ",cn=12,dn=8,pn=30,un=8,ao=5,Dt=class extends F{constructor(){super(...arguments);this.openGroups=new Set;this.showAll=!1;this.query="";this.cursor=void 0;this.stakeInline=!1;this.groupsLayout="beside";this.rowsLayout="beside";this.openWallets=new Set;this.window=ue("day",Date.now());this.lines=new pe(()=>this.seriesArrived(),Xs)}static{this.properties={...F.properties,openGroups:{state:!0},openWallets:{state:!0},showAll:{state:!0},query:{state:!0},cursor:{state:!0},stakeInline:{state:!0},groupsLayout:{state:!0},rowsLayout:{state:!0}}}static async getConfigForm(){let t=await Be(re());return{schema:[Oe("Bitpanda Portfolio"),X("group_content",[je(),D("show_total",!0),D("show_graph",!0),D("show_cash",!0),D("show_allocation",!0),D("show_wallets",!0)]),X("group_wallets",[D("show_search",!1),D("group_wallets",!0),Ue($t),De(ao),ie(),...Fe(t),ie(),...Ve("Wallet")]),X("group_appearance",[D("hide_amounts",!1)])],computeLabel:s=>{let n=nn[s.name];return n?h(void 0,n):qe(s)},computeHelper:s=>{let n=rn[s.name];return n?h(void 0,n):Ge(s)}}}static getStubConfig(){return{timeframe:"day",sort:"value",group_selection:"all",asset_selection:"all"}}validate(t){return We(t,{...Ze,timeframe:P(B),show_total:j,show_graph:j,show_cash:j,show_allocation:j,show_wallets:j,group_wallets:j,show_search:j,sort:P($t),limit:He,group_selection:P(O),groups:Me,asset_selection:P(O),assets:Ie,hide_amounts:j})}watchedEntities(){let t=this.hass?Ye(this.hass):void 0;return t?[t.totalValue,t.cash,t.cashPlus,...Object.values(t.returns),...t.wallets.flatMap(s=>[s.available,s.total,s.staking])].filter(s=>s!==void 0):[]}willUpdate(t){super.willUpdate(t);let s=this.hass?Ye(this.hass):void 0;this.window=ue(this.timeframe,Date.now());let n=this.hass?.states[s?.returns[this.timeframe]??""]?.state??"";this.hass&&s&&this.config?.show_graph!==!1&&this.lines.request(this.hass,[ct],this.window,n)}getCardSize(){return 8}remeasures(t){return!(t.size===1&&t.has("cursor"))}fitLayout(){let t=d=>[...this.renderRoot.querySelectorAll(d)],s=(d,_)=>d.querySelector(_),n=d=>d?.getBoundingClientRect().width,r=t(".wallet .sub").map(d=>{let _=n(d.querySelector(".stake .badge"));return{room:d.clientWidth,first:s(d,".s").getBoundingClientRect().width,..._===void 0?{}:{second:_}}}),i=de(r,un);i!==this.stakeInline&&(this.stakeInline=i);let l=t(".group").map(d=>{let _=n(d.querySelector(".gchip"));return{room:d.clientWidth,left:s(d,".gleft").getBoundingClientRect().width,..._===void 0?{}:{chip:_},value:s(d,".sum").getBoundingClientRect().width}}),a=io(l);a!==this.groupsLayout&&(this.groupsLayout=a);let c=t(".wallet .tap").map(d=>({room:d.clientWidth,below:d.clientWidth+pn,left:[...s(d,".s .units").getClientRects()].reduce((_,f)=>_+f.width,0),chip:s(d,".wchip").getBoundingClientRect().width,value:s(d,".val").getBoundingClientRect().width})),u=io(c);u!==this.rowsLayout&&(this.rowsLayout=u)}groupChip(t,s){let{text:n,direction:r}=H(t,ln(t,s));if(r==="none")return p`<span class="gchip none">—</span>`;let i=ee(r);return p`<span class="gchip ${R(r)}">${i?`${i} `:""}${n}</span>`}walletsClass(){return["wallets",this.stakeInline?"stake-inline":"",this.groupsLayout==="beside"?"":"groups-wrapped",this.groupsLayout==="stacked"?"groups-stacked":"",this.rowsLayout==="beside"?"":"rows-wrapped",this.rowsLayout==="stacked"?"rows-stacked":""].filter(Boolean).join(" ")}toggle(t,s){let n=new Set(t);return n.has(s)?n.delete(s):n.add(s),n}open(t){return()=>{t&&ce(this,t)}}render(){let t=this.hass,s=this.config;if(!t||!s)return m;let n=Ye(t),r={hidden:this.amountsHidden,toggle:()=>this.toggleAmounts()},i=s.title||"Bitpanda Portfolio";if(!n)return p`<ha-card>${Ae(t,i,r)}${te(h(t,"empty_portfolio"))}</ha-card>`;let l=s.show_total!==!1||s.show_graph!==!1,a=s.show_cash!==!1||s.show_allocation!==!1,c=an(n,s);return p`<ha-card>
      ${Ae(t,i,r)}
      <div class="content">
        ${oo({host:this,hass:t,refs:n,timeframe:this.timeframe,hidden:this.amountsHidden,window:this.window,points:this.lines.series(ct),total:s.show_total!==!1,line:s.show_graph!==!1,onTimeframe:u=>{this.cursor=void 0,this.selectTimeframe(u)},cursor:this.cursor,onCursor:u=>{u!==this.cursor&&(this.cursor=u)}})}
        ${a?p`${l?p`<div class="divider"></div>`:m}
              ${s.show_cash===!1?m:this.renderCash(t,n)}
              ${s.show_allocation===!1?m:this.renderAllocation(t,n)}`:m}
        ${s.show_wallets===!1?m:p`${l||a?p`<div class="divider"></div>`:m}${s.show_search&&c.length>0?Ks(t,this.query,u=>this.query=u):m}${this.renderWallets(t,n,c,s)}`}
      </div>
    </ha-card>`}renderCash(t,s){let n=(r,i,l)=>p`<div class=${l?"end":""} role="button" tabindex="0" @click=${this.open(i)} @keydown=${T(this.open(i))}>
        <span class="k">${r}</span><span class="v">${A(N(t,i),this.amountsHidden)}</span>
      </div>`;return p`<div class="pair">${n(h(t,"cash"),s.cash,!1)}${n(h(t,"cash_plus"),s.cashPlus,!0)}</div>`}renderAllocation(t,s){let n=[];for(let a of L){let c=s.wallets.filter(u=>ro(u)===a);c.length>0&&n.push({key:a,label:kt(t,a),value:Ot(c.map(u=>$(t,u.total)))})}s.cashPlus&&n.push({key:"cash_plus",label:h(t,"cash_plus"),value:$(t,s.cashPlus)}),s.cash&&n.push({key:"cash",label:h(t,"cash"),value:$(t,s.cash)});let r=Ot(n.map(a=>a.value));if(r===void 0)return p`<div class="allocation-missing muted">—</div>`;let i=n.map(a=>({...a,share:r>0?a.value/r*100:0})).filter(a=>a.share>0).sort((a,c)=>c.share-a.share),l=a=>a<1?`<${ae(t,1,0)}`:ae(t,a,0);return p`<div class="bar" role="img" aria-label=${h(t,"opt_show_allocation")}>
        ${i.map(a=>p`<span style="width:${a.share}%;background:${no[a.key]}"></span>`)}
      </div>
      <div class="legend">
        ${i.map(a=>p`<span><i style="background:${no[a.key]}"></i>${a.label} ${l(a.share)}</span>`)}
      </div>`}renderWallets(t,s,n,r){if(s.wallets.length===0)return te(h(t,"empty_wallets"));if(n.length===0)return te(h(t,"empty_selection_wallets"));let i=r.sort??"value",l=r.show_search?this.query.trim():"";if(l){let a=it(t,n.filter(c=>Zs(c,l)),i);return a.length>0?p`<div class=${this.walletsClass()}>${a.map(c=>this.renderWallet(t,s,c))}</div>`:p`<div class="search-none">${h(t,"search_none",{query:l})}</div>`}if(r.group_wallets===!1){let a=it(t,n,i),c=r.limit??ao,u=c>0&&a.length>c,d=u&&!this.showAll?a.slice(0,c):a;return p`<div class=${this.walletsClass()}>${d.map(_=>this.renderWallet(t,s,_))}</div>
        ${u?p`<button class="show-all" @click=${()=>this.showAll=!this.showAll}>
              ${this.showAll?h(t,"show_less"):h(t,"show_all",{count:a.length})}
            </button>`:m}`}return p`<div class=${this.walletsClass()}>${L.map(a=>{let c=n.filter(f=>ro(f)===a);if(c.length===0)return m;let u=Ot(c.map(f=>$(t,f.total))),d=this.openGroups.has(a),_=()=>{this.openGroups=this.toggle(this.openGroups,a)};return p`<div class="group" role="button" tabindex="0" aria-expanded=${d?"true":"false"} @click=${_} @keydown=${T(_)}>
          <span class="gleft"
            >${le(d?Nt.down:Nt.right)}<span class="name">${kt(t,a)}</span
            ><span class="count">${c.length}</span></span
          >
          <span class="gright">${this.groupChip(t,c)}<span class="sum">${A(Rs(t,c[0]?.total,u),this.amountsHidden)}</span></span>
        </div>
        ${d?p`<div class="members">${it(t,c,i).map(f=>this.renderWallet(t,s,f))}</div>`:m}`})}</div>`}renderWallet(t,s,n){let r=this.openWallets.has(n.deviceId);return p`${Ys({hass:t,wallet:n,hidden:this.amountsHidden,onTap:this.open(n.total),chevron:{open:r,toggle:()=>{this.openWallets=this.toggle(this.openWallets,n.deviceId)}}})}${r?this.renderDetail(t,s,n):m}`}renderDetail(t,s,n){let r=this.amountsHidden,i=w=>w?t.states[w]?.attributes.unit_of_measurement:void 0,l=String(i(n.total)??i(s.totalValue)??"EUR"),a=n.total?t.states[n.total]:void 0,c=n.staking?t.states[n.staking]:void 0,u=w=>{let z=k(w?t.states[w]:void 0,"units");return z===void 0?void 0:be(t,z,n.category,n.symbol)},d=(w,z=!1)=>w===void 0?void 0:xe(t,w,l,z),_=w=>w===void 0?void 0:Es(t,w,l),f=w=>p`<span class="part">${w}</span>`,v=w=>p`${f(A(u(w),r))}${jt}${f(A(N(t,w),r))}`,y=k(a,"total_return"),g=H(t,k(a,"total_return_percent")),x=k(c,"apr_percent"),S=k(c,"rewards_net"),C=k(c,"rewards_count"),E=c?.attributes.rewards_last_at,V=typeof E=="string"&&Number.isFinite(Date.parse(E))?tt(t,Date.parse(E)):"\u2014",b=d(k(c,"rewards_net_value"));return p`<div class="detail">
      <div class="grid">
        <span>${h(t,"detail_available")}</span><span>${v(n.available)}</span>
        ${n.staking?p`<span>${h(t,"detail_staked")}</span><span>${v(n.staking)}</span>`:m}
        ${n.staking&&x!==void 0?p`<span>${h(t,"detail_staking_apr")}</span><span>${ae(t,x,1)}</span>`:m}
        <span>${h(t,"detail_average_buy_price")}</span><span>${A(_(k(a,"average_buy_price")),r)}</span>
        <span>${h(t,"detail_invested")}</span><span>${A(d(k(a,"invested_amount")),r)}</span>
        <span>${h(t,"detail_profit_loss")}</span
        ><span class=${R(g.direction)}>${f(A(d(y,!0),r))} ${f(`(${g.text})`)}</span>
      </div>
      ${C!==void 0&&C>0?p`<h4>${h(t,"detail_rewards")}</h4>
            <div class="grid">
              <span>${h(t,"detail_rewards_net")}</span>
              <span
                >${f(A(S===void 0?void 0:be(t,S,n.category,n.symbol),r))}${b?p`${jt}${f(this.worth(t,b))}`:m}</span
              >
              <span>${h(t,"detail_payouts")}</span
              ><span
                >${h(t,"detail_payouts_value",{count:C,date:V}).split(" \xB7 ").map((w,z)=>p`${z>0?jt:""}${f(w)}`)}</span
              >
            </div>`:m}
    </div>`}worth(t,s){let[n="",r=""]=h(t,"detail_rewards_worth").split("{value}");return p`${n}${A(s,this.amountsHidden)}${r}`}};at(on,Dt,{name:"Bitpanda Portfolio",description:()=>h(re(),"picker_portfolio"),model:["Portfolio","Wallet"]});var hn=me`
  /* Price and change in columns as wide as the widest of the list
     (priceColumns), so that every line stands where the others do; as wide
     as their contents until the card has measured them. */
  .price-row {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 96px var(--bp-price, auto) var(--bp-change, minmax(78px, auto));
    grid-template-areas: "lead line price change";
    align-items: center;
    gap: 8px;
    padding: 9px 0;
    border-top: 1px solid var(--bp-divider);
    cursor: pointer;
  }
  .price-row .lead {
    grid-area: lead;
    min-width: 0;
  }
  /* A name over two lines takes two of about the same length: its first
     line keeps off the price. Longer names are still cut after two. */
  .price-row .n {
    text-wrap: balance;
  }
  .price-row .mini {
    grid-area: line;
  }
  /* Price and change only as wide as they are: the card measures them
     alike in either layout (fitLayout). */
  .price-row .p {
    grid-area: price;
    justify-self: end;
  }
  .price-row .c {
    grid-area: change;
    justify-self: end;
    display: flex;
    flex-direction: column;
    align-items: flex-end;
  }
  /* Not room for the name in every row: the price above its change. */
  .rows.stacked .price-row {
    grid-template-columns: minmax(0, 1fr) 96px var(--bp-figures, auto);
    grid-template-areas:
      "lead line price"
      "lead line change";
    row-gap: 2px;
  }
  .rows.stacked .price-row .p {
    align-self: end;
  }
  .rows.stacked .price-row .c {
    align-self: start;
  }
  .price-row:first-of-type {
    border-top: 0;
  }
  .price-row .s {
    font-size: 11px;
  }
  .p {
    text-align: right;
    font-variant-numeric: tabular-nums;
  }
  .c {
    text-align: right;
    font-size: 13px;
    font-weight: 500;
    white-space: nowrap;
  }
  .c .a {
    font-size: 12px;
    font-weight: 400;
    margin-top: 2px;
  }
  .since {
    font-size: 11px;
    color: var(--bp-muted);
    margin-top: 2px;
  }
  .rows {
    margin-top: 10px;
  }
  .tiles {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(124px, 1fr));
    gap: 8px;
    margin-top: 12px;
  }
  .tile {
    border: 1px solid var(--bp-divider);
    border-radius: 10px;
    padding: 10px;
    cursor: pointer;
    min-width: 0;
  }
  .tile .n {
    font-size: 13px;
    font-weight: 500;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    display: block;
  }
  .tile .s {
    font-size: 11px;
  }
  .tile .p {
    text-align: left;
    font-size: 16px;
    margin-top: 6px;
  }
  .tile .c {
    text-align: left;
    font-size: 12px;
    display: flex;
    flex-direction: column;
    align-items: flex-start;
  }
  .tile .c .pct,
  .tile .c .a {
    flex-shrink: 0;
  }
  /* Every tile has room: the amount beside the chip (amountsFit). */
  .tiles.inline .tile .c {
    flex-direction: row;
    align-items: center;
    column-gap: 6px;
  }
  .tiles.inline .tile .c .a {
    margin-top: 0;
  }
  .tile svg.mini {
    width: 100%;
    height: 30px;
    margin-top: 6px;
  }
  .tile .since {
    margin-top: 4px;
  }
  .foot {
    font-size: 11px;
    color: var(--bp-muted);
    padding: 10px 16px 14px;
    border-top: 1px solid var(--bp-divider);
  }
  /* A narrow list, such as the card picker's preview: the names first. */
  @container (max-width: 380px) {
    .price-row {
      grid-template-columns: minmax(0, 1fr) auto auto;
      grid-template-areas: "lead price change";
    }
    .rows.stacked .price-row {
      grid-template-columns: minmax(0, 1fr) auto;
      grid-template-areas:
        "lead price"
        "lead change";
    }
    .price-row .mini {
      display: none;
    }
  }
  /* Not even room for the name beside the price above its change: name and
     category across the row, price, chip and amount right-aligned below. */
  .rows.below .price-row {
    grid-template-columns: minmax(0, 1fr);
    grid-template-areas:
      "lead"
      "price"
      "change";
    row-gap: 2px;
  }
  .rows.below .price-row .lead {
    margin-bottom: 4px;
  }
  .rows.below .price-row .mini {
    display: none;
  }
`,mn=6,_n=120,fn=90,ut=8,gn=78,yn=96,wn=380;function lo(o){let e=Math.ceil(Math.max(0,...o.map(s=>s.price))),t=Math.ceil(Math.max(0,...o.map(s=>s.change)));return{price:e,change:Math.max(gn,t),figures:Math.max(e,t)}}function vn(o){let e=lo(o);return o.every(t=>t.room-e.price-ut-e.change-ut>=_n)?"beside":o.every(t=>t.room-e.figures-ut>=fn)?"stacked":"below"}function bn(o){return de(o.map(e=>({room:e.room,first:e.pct,...e.amount===void 0?{}:{second:e.amount}})),mn)}function xn(o){let e=o?Je(ve(o)):[];return e.length>0?e:ks}var Ut=class extends F{constructor(){super(...arguments);this.showAll=!1;this.amountsInline=!1;this.rowsLayout="beside";this.columns=void 0;this.window=ue("day",Date.now());this.lines=new pe(()=>this.seriesArrived())}static{this.properties={...F.properties,currency:{state:!0},showAll:{state:!0},amountsInline:{state:!0},rowsLayout:{state:!0},columns:{state:!0}}}static{this.styles=[Ke,hn]}static async getConfigForm(){let t=re(),s=await Be(t);return{schema:[Oe("Bitpanda Price Tracker"),X("group_content",[{name:"layout",selector:ne(St,n=>h(void 0,`layout_${n}`))},je(),{name:"currency",selector:{select:{mode:"dropdown",options:xn(t).map(n=>({value:n,label:n}))}}}]),X("group_assets",[Ue(At),De(0),ie(),...Fe(s),ie(),...Ve("Price Tracker")])],computeLabel:qe,computeHelper:n=>n.name==="sort"?h(void 0,"opt_sort_help_tracker"):Ge(n)}}static getStubConfig(){return{layout:"list",timeframe:"day",currency:"EUR",sort:"name",group_selection:"all",asset_selection:"all"}}setConfig(t){super.setConfig(t),this.currency=void 0}validate(t){return We(t,{...Ze,layout:P(St),timeframe:P(B),currency:As,sort:P(At),group_selection:P(O),groups:Me,asset_selection:P(O),assets:Ie,limit:He})}watchedEntities(){return this.hass?ve(this.hass).flatMap(t=>Object.values(t.prices)):[]}shownCurrency(t){let s=Je(t),n=this.currency??this.config?.currency??"EUR";return s.includes(n)?n:s.includes("EUR")?"EUR":s[0]??"EUR"}visible(t,s){let n=ve(t),r=this.shownCurrency(n),i=Xe(n,s.group_selection??"all",s.groups??[]),a=Qe(i,s.asset_selection??"all",s.assets??[]).map(v=>{let y=v.prices[r],g=y?t.states[y]:void 0,x=y?this.lines.series(y):void 0,S=$(t,y),C=this.timeframe==="day"?k(g,"change_24h_pct"):void 0;if(C!==void 0){let V=k(g,"price_24h_ago"),b=S!==void 0&&V!==void 0?S-V:void 0;return{asset:v,entityId:y,change:C,amount:b,points:x,since:void 0}}let E=Qs(x??[],S,this.window);return{asset:v,entityId:y,change:E?.change,amount:E?.amount,points:x,since:E?.since}}),c=s.sort??"name",u=(v,y)=>v.asset.name.localeCompare(y.asset.name,W(t));if(c==="name"||c==="selection"&&s.asset_selection!=="only")a.sort(u);else if(c==="change_desc"||c==="change_asc"){let v=c==="change_desc"?-1:1;a.sort((y,g)=>y.change===void 0||g.change===void 0?y.change===void 0?g.change===void 0?u(y,g):1:-1:v*(y.change-g.change)||u(y,g))}let d=s.limit??0,_=d>0&&a.length>d;return{rows:_&&!this.showAll?a.slice(0,d):a,ranked:a,total:a.length,folds:_,currency:r,currencies:Je(n)}}willUpdate(t){if(super.willUpdate(t),this.window=ue(this.timeframe,Date.now()),!this.hass||!this.config)return;let{rows:s,ranked:n}=this.visible(this.hass,this.config),r=this.config.sort??"name",l=(this.timeframe!=="day"&&(r==="change_desc"||r==="change_asc")?n:s).map(a=>a.entityId).filter(a=>a!==void 0);this.lines.request(this.hass,l,this.window)}fitLayout(){let t=a=>a?.getBoundingClientRect().width,s=[...this.shadowRoot?.querySelectorAll(".tile .c")??[]].map(a=>{let c=t(a.querySelector(".a"));return{room:a.clientWidth,pct:t(a.querySelector(".pct"))??0,...c===void 0?{}:{amount:c}}}),n=bn(s);n!==this.amountsInline&&(this.amountsInline=n);let r=this.clientWidth>wn?yn+ut:0,i=[...this.renderRoot.querySelectorAll(".price-row")].map(a=>{let c=u=>a.querySelector(u).getBoundingClientRect().width;return{room:a.clientWidth-r,price:c(".p"),change:Math.max(c(".c .pct"),t(a.querySelector(".c .a"))??0)}}),l=vn(i);if(l!==this.rowsLayout&&(this.rowsLayout=l),i.length>0){let a=lo(i),c=this.columns;(!c||c.price!==a.price||c.change!==a.change||c.figures!==a.figures)&&(this.columns=a)}}getCardSize(){return 6}open(t){return()=>{t&&ce(this,t)}}line(t,s){let n=t.since===void 0?this.window:{...this.window,start:t.since};return t.points&&t.points.length>0?dt(t.points,n,{width:96,height:28,fill:!1,className:`mini ${s}`,stepMs:Js(n)}):p`<span class="mini"></span>`}change(t,s){let{text:n,direction:r}=H(t,s.change),i=ee(r),l=R(r),a=r==="none"?void 0:Ls(t,s.entityId,s.amount);return{cell:p`<div class="pct pchip ${r==="none"?"none":""}">${r==="none"?"\u2014":`${i?`${i} `:""}${n}`}</div>${a?p`<div class="a">${a}</div>`:m}`,className:l,lineClass:l||"flat"}}since(t,s){return s.since===void 0?m:p`<div class="since">${h(t,"change_since",{date:ke(t,s.since)})}</div>`}renderList(t,s){let n=this.columns,r=n?`--bp-price:${n.price}px;--bp-change:${n.change}px;--bp-figures:${n.figures}px`:"";return p`<div class="rows ${this.rowsLayout==="beside"?"":this.rowsLayout}" style=${r}>
      ${s.map(i=>{let l=this.change(t,i);return p`<div class="price-row" role="button" tabindex="0" @click=${this.open(i.entityId)} @keydown=${T(this.open(i.entityId))}>
          <div class="lead"><div class="n" title=${i.asset.shortName}>${i.asset.shortName}</div><div class="s">${i.asset.isin??i.asset.symbol}</div>${this.since(t,i)}</div>
          ${this.line(i,l.lineClass)}
          <div class="p">${N(t,i.entityId)??"\u2014"}</div>
          <div class="c ${l.className}">${l.cell}</div>
        </div>`})}
    </div>`}renderTiles(t,s){return p`<div class="tiles ${this.amountsInline?"inline":""}">
      ${s.map(n=>{let r=this.change(t,n);return p`<div class="tile" role="button" tabindex="0" @click=${this.open(n.entityId)} @keydown=${T(this.open(n.entityId))}>
          <div class="n" title=${n.asset.shortName}>${n.asset.shortName}</div>
          <div class="s">${n.asset.isin??n.asset.symbol}</div>
          <div class="p">${N(t,n.entityId)??"\u2014"}</div>
          <div class="c ${r.className}">${r.cell}</div>
          ${this.line(n,r.lineClass)}${this.since(t,n)}
        </div>`})}
    </div>`}footer(t,s,n){if(n==="EUR")return m;let r=s.map(i=>i.entityId?t.states[i.entityId]?.attributes.rate_date:void 0).map(i=>typeof i=="string"?Is(t,i):void 0).find(i=>i!==void 0);return r?p`<div class="foot">${h(t,"ecb_footer",{currency:n,date:r})}</div>`:m}render(){let t=this.hass,s=this.config;if(!t||!s)return m;let n=Ae(t,s.title||"Bitpanda Price Tracker");if(ve(t).length===0)return p`<ha-card>${n}${te(h(t,"empty_price_tracker"))}</ha-card>`;let{rows:r,total:i,folds:l,currency:a,currencies:c}=this.visible(t,s);return p`<ha-card>
      ${n}
      <div class="content">
        <div class="switches">
          ${rt(t,this.timeframe,u=>this.selectTimeframe(u))}
          ${Gs(t,c,a,u=>this.currency=u)}
        </div>
        ${r.length===0?te(h(t,"empty_selection_assets")):s.layout==="tiles"?this.renderTiles(t,r):this.renderList(t,r)}
        ${l?p`<button class="show-all" @click=${()=>this.showAll=!this.showAll}>
              ${this.showAll?h(t,"show_less"):h(t,"show_all",{count:i})}
            </button>`:m}
      </div>
      ${this.footer(t,r,a)}
    </ha-card>`}};at("bitpanda-price-tracker-card",Ut,{name:"Bitpanda Price Tracker",description:()=>h(re(),"picker_price_tracker"),model:"Price Tracker"});
/*! Bundled license information:

@lit/reactive-element/css-tag.js:
  (**
   * @license
   * Copyright 2019 Google LLC
   * SPDX-License-Identifier: BSD-3-Clause
   *)

@lit/reactive-element/reactive-element.js:
lit-html/lit-html.js:
lit-element/lit-element.js:
lit-html/directive.js:
lit-html/async-directive.js:
  (**
   * @license
   * Copyright 2017 Google LLC
   * SPDX-License-Identifier: BSD-3-Clause
   *)

lit-html/is-server.js:
  (**
   * @license
   * Copyright 2022 Google LLC
   * SPDX-License-Identifier: BSD-3-Clause
   *)

lit-html/directive-helpers.js:
lit-html/directives/ref.js:
  (**
   * @license
   * Copyright 2020 Google LLC
   * SPDX-License-Identifier: BSD-3-Clause
   *)
*/
