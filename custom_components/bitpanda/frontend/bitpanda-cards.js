var Se=globalThis,Ce=Se.ShadowRoot&&(Se.ShadyCSS===void 0||Se.ShadyCSS.nativeShadow)&&"adoptedStyleSheets"in Document.prototype&&"replace"in CSSStyleSheet.prototype,ht=Symbol(),Bt=new WeakMap,he=class{constructor(e,t,o){if(this._$cssResult$=!0,o!==ht)throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");this.cssText=e,this.t=t}get styleSheet(){let e=this.o,t=this.t;if(Ce&&e===void 0){let o=t!==void 0&&t.length===1;o&&(e=Bt.get(t)),e===void 0&&((this.o=e=new CSSStyleSheet).replaceSync(this.cssText),o&&Bt.set(t,e))}return e}toString(){return this.cssText}},Ft=s=>new he(typeof s=="string"?s:s+"",void 0,ht),me=(s,...e)=>{let t=s.length===1?s[0]:e.reduce((o,n,r)=>o+(a=>{if(a._$cssResult$===!0)return a.cssText;if(typeof a=="number")return a;throw Error("Value passed to 'css' function must be a 'css' function result: "+a+". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.")})(n)+s[r+1],s[0]);return new he(t,s,ht)},Vt=(s,e)=>{if(Ce)s.adoptedStyleSheets=e.map(t=>t instanceof CSSStyleSheet?t:t.styleSheet);else for(let t of e){let o=document.createElement("style"),n=Se.litNonce;n!==void 0&&o.setAttribute("nonce",n),o.textContent=t.cssText,s.appendChild(o)}},mt=Ce?s=>s:s=>s instanceof CSSStyleSheet?(e=>{let t="";for(let o of e.cssRules)t+=o.cssText;return Ft(t)})(s):s;var{is:po,defineProperty:uo,getOwnPropertyDescriptor:ho,getOwnPropertyNames:mo,getOwnPropertySymbols:_o,getPrototypeOf:fo}=Object,Te=globalThis,qt=Te.trustedTypes,go=qt?qt.emptyScript:"",yo=Te.reactiveElementPolyfillSupport,_e=(s,e)=>s,_t={toAttribute(s,e){switch(e){case Boolean:s=s?go:null;break;case Object:case Array:s=s==null?s:JSON.stringify(s)}return s},fromAttribute(s,e){let t=s;switch(e){case Boolean:t=s!==null;break;case Number:t=s===null?null:Number(s);break;case Object:case Array:try{t=JSON.parse(s)}catch{t=null}}return t}},Kt=(s,e)=>!po(s,e),Gt={attribute:!0,type:String,converter:_t,reflect:!1,useDefault:!1,hasChanged:Kt};Symbol.metadata??=Symbol("metadata"),Te.litPropertyMetadata??=new WeakMap;var H=class extends HTMLElement{static addInitializer(e){this._$Ei(),(this.l??=[]).push(e)}static get observedAttributes(){return this.finalize(),this._$Eh&&[...this._$Eh.keys()]}static createProperty(e,t=Gt){if(t.state&&(t.attribute=!1),this._$Ei(),this.prototype.hasOwnProperty(e)&&((t=Object.create(t)).wrapped=!0),this.elementProperties.set(e,t),!t.noAccessor){let o=Symbol(),n=this.getPropertyDescriptor(e,o,t);n!==void 0&&uo(this.prototype,e,n)}}static getPropertyDescriptor(e,t,o){let{get:n,set:r}=ho(this.prototype,e)??{get(){return this[t]},set(a){this[t]=a}};return{get:n,set(a){let l=n?.call(this);r?.call(this,a),this.requestUpdate(e,l,o)},configurable:!0,enumerable:!0}}static getPropertyOptions(e){return this.elementProperties.get(e)??Gt}static _$Ei(){if(this.hasOwnProperty(_e("elementProperties")))return;let e=fo(this);e.finalize(),e.l!==void 0&&(this.l=[...e.l]),this.elementProperties=new Map(e.elementProperties)}static finalize(){if(this.hasOwnProperty(_e("finalized")))return;if(this.finalized=!0,this._$Ei(),this.hasOwnProperty(_e("properties"))){let t=this.properties,o=[...mo(t),..._o(t)];for(let n of o)this.createProperty(n,t[n])}let e=this[Symbol.metadata];if(e!==null){let t=litPropertyMetadata.get(e);if(t!==void 0)for(let[o,n]of t)this.elementProperties.set(o,n)}this._$Eh=new Map;for(let[t,o]of this.elementProperties){let n=this._$Eu(t,o);n!==void 0&&this._$Eh.set(n,t)}this.elementStyles=this.finalizeStyles(this.styles)}static finalizeStyles(e){let t=[];if(Array.isArray(e)){let o=new Set(e.flat(1/0).reverse());for(let n of o)t.unshift(mt(n))}else e!==void 0&&t.push(mt(e));return t}static _$Eu(e,t){let o=t.attribute;return o===!1?void 0:typeof o=="string"?o:typeof e=="string"?e.toLowerCase():void 0}constructor(){super(),this._$Ep=void 0,this.isUpdatePending=!1,this.hasUpdated=!1,this._$Em=null,this._$Ev()}_$Ev(){this._$ES=new Promise(e=>this.enableUpdating=e),this._$AL=new Map,this._$E_(),this.requestUpdate(),this.constructor.l?.forEach(e=>e(this))}addController(e){(this._$EO??=new Set).add(e),this.renderRoot!==void 0&&this.isConnected&&e.hostConnected?.()}removeController(e){this._$EO?.delete(e)}_$E_(){let e=new Map,t=this.constructor.elementProperties;for(let o of t.keys())this.hasOwnProperty(o)&&(e.set(o,this[o]),delete this[o]);e.size>0&&(this._$Ep=e)}createRenderRoot(){let e=this.shadowRoot??this.attachShadow(this.constructor.shadowRootOptions);return Vt(e,this.constructor.elementStyles),e}connectedCallback(){this.renderRoot??=this.createRenderRoot(),this.enableUpdating(!0),this._$EO?.forEach(e=>e.hostConnected?.())}enableUpdating(e){}disconnectedCallback(){this._$EO?.forEach(e=>e.hostDisconnected?.())}attributeChangedCallback(e,t,o){this._$AK(e,o)}_$ET(e,t){let o=this.constructor.elementProperties.get(e),n=this.constructor._$Eu(e,o);if(n!==void 0&&o.reflect===!0){let r=(o.converter?.toAttribute!==void 0?o.converter:_t).toAttribute(t,o.type);this._$Em=e,r==null?this.removeAttribute(n):this.setAttribute(n,r),this._$Em=null}}_$AK(e,t){let o=this.constructor,n=o._$Eh.get(e);if(n!==void 0&&this._$Em!==n){let r=o.getPropertyOptions(n),a=typeof r.converter=="function"?{fromAttribute:r.converter}:r.converter?.fromAttribute!==void 0?r.converter:_t;this._$Em=n;let l=a.fromAttribute(t,r.type);this[n]=l??this._$Ej?.get(n)??l,this._$Em=null}}requestUpdate(e,t,o,n=!1,r){if(e!==void 0){let a=this.constructor;if(n===!1&&(r=this[e]),o??=a.getPropertyOptions(e),!((o.hasChanged??Kt)(r,t)||o.useDefault&&o.reflect&&r===this._$Ej?.get(e)&&!this.hasAttribute(a._$Eu(e,o))))return;this.C(e,t,o)}this.isUpdatePending===!1&&(this._$ES=this._$EP())}C(e,t,{useDefault:o,reflect:n,wrapped:r},a){o&&!(this._$Ej??=new Map).has(e)&&(this._$Ej.set(e,a??t??this[e]),r!==!0||a!==void 0)||(this._$AL.has(e)||(this.hasUpdated||o||(t=void 0),this._$AL.set(e,t)),n===!0&&this._$Em!==e&&(this._$Eq??=new Set).add(e))}async _$EP(){this.isUpdatePending=!0;try{await this._$ES}catch(t){Promise.reject(t)}let e=this.scheduleUpdate();return e!=null&&await e,!this.isUpdatePending}scheduleUpdate(){return this.performUpdate()}performUpdate(){if(!this.isUpdatePending)return;if(!this.hasUpdated){if(this.renderRoot??=this.createRenderRoot(),this._$Ep){for(let[n,r]of this._$Ep)this[n]=r;this._$Ep=void 0}let o=this.constructor.elementProperties;if(o.size>0)for(let[n,r]of o){let{wrapped:a}=r,l=this[n];a!==!0||this._$AL.has(n)||l===void 0||this.C(n,void 0,r,l)}}let e=!1,t=this._$AL;try{e=this.shouldUpdate(t),e?(this.willUpdate(t),this._$EO?.forEach(o=>o.hostUpdate?.()),this.update(t)):this._$EM()}catch(o){throw e=!1,this._$EM(),o}e&&this._$AE(t)}willUpdate(e){}_$AE(e){this._$EO?.forEach(t=>t.hostUpdated?.()),this.hasUpdated||(this.hasUpdated=!0,this.firstUpdated(e)),this.updated(e)}_$EM(){this._$AL=new Map,this.isUpdatePending=!1}get updateComplete(){return this.getUpdateComplete()}getUpdateComplete(){return this._$ES}shouldUpdate(e){return!0}update(e){this._$Eq&&=this._$Eq.forEach(t=>this._$ET(t,this[t])),this._$EM()}updated(e){}firstUpdated(e){}};H.elementStyles=[],H.shadowRootOptions={mode:"open"},H[_e("elementProperties")]=new Map,H[_e("finalized")]=new Map,yo?.({ReactiveElement:H}),(Te.reactiveElementVersions??=[]).push("2.1.2");var gt=globalThis,Zt=s=>s,Pe=gt.trustedTypes,Yt=Pe?Pe.createPolicy("lit-html",{createHTML:s=>s}):void 0,yt="$lit$",M=`lit$${Math.random().toFixed(9).slice(2)}$`,wt="?"+M,wo=`<${wt}>`,K=document,ge=()=>K.createComment(""),ye=s=>s===null||typeof s!="object"&&typeof s!="function",vt=Array.isArray,ss=s=>vt(s)||typeof s?.[Symbol.iterator]=="function",ft=`[ 	
\f\r]`,fe=/<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g,Jt=/-->/g,Xt=/>/g,q=RegExp(`>|${ft}(?:([^\\s"'>=/]+)(${ft}*=${ft}*(?:[^ 	
\f\r"'\`<>=]|("|')|))|$)`,"g"),Qt=/'/g,es=/"/g,os=/^(?:script|style|textarea|title)$/i,bt=s=>(e,...t)=>({_$litType$:s,strings:e,values:t}),p=bt(1),oe=bt(2),Tn=bt(3),Z=Symbol.for("lit-noChange"),m=Symbol.for("lit-nothing"),ts=new WeakMap,G=K.createTreeWalker(K,129);function ns(s,e){if(!vt(s)||!s.hasOwnProperty("raw"))throw Error("invalid template strings array");return Yt!==void 0?Yt.createHTML(e):e}var rs=(s,e)=>{let t=s.length-1,o=[],n,r=e===2?"<svg>":e===3?"<math>":"",a=fe;for(let l=0;l<t;l++){let i=s[l],c,u,d=-1,_=0;for(;_<i.length&&(a.lastIndex=_,u=a.exec(i),u!==null);)_=a.lastIndex,a===fe?u[1]==="!--"?a=Jt:u[1]!==void 0?a=Xt:u[2]!==void 0?(os.test(u[2])&&(n=RegExp("</"+u[2],"g")),a=q):u[3]!==void 0&&(a=q):a===q?u[0]===">"?(a=n??fe,d=-1):u[1]===void 0?d=-2:(d=a.lastIndex-u[2].length,c=u[1],a=u[3]===void 0?q:u[3]==='"'?es:Qt):a===es||a===Qt?a=q:a===Jt||a===Xt?a=fe:(a=q,n=void 0);let f=a===q&&s[l+1].startsWith("/>")?" ":"";r+=a===fe?i+wo:d>=0?(o.push(c),i.slice(0,d)+yt+i.slice(d)+M+f):i+M+(d===-2?l:f)}return[ns(s,r+(s[t]||"<?>")+(e===2?"</svg>":e===3?"</math>":"")),o]},we=class s{constructor({strings:e,_$litType$:t},o){let n;this.parts=[];let r=0,a=0,l=e.length-1,i=this.parts,[c,u]=rs(e,t);if(this.el=s.createElement(c,o),G.currentNode=this.el.content,t===2||t===3){let d=this.el.content.firstChild;d.replaceWith(...d.childNodes)}for(;(n=G.nextNode())!==null&&i.length<l;){if(n.nodeType===1){if(n.hasAttributes())for(let d of n.getAttributeNames())if(d.endsWith(yt)){let _=u[a++],f=n.getAttribute(d).split(M),v=/([.?@])?(.*)/.exec(_);i.push({type:1,index:r,name:v[2],strings:f,ctor:v[1]==="."?Ee:v[1]==="?"?ze:v[1]==="@"?Le:J}),n.removeAttribute(d)}else d.startsWith(M)&&(i.push({type:6,index:r}),n.removeAttribute(d));if(os.test(n.tagName)){let d=n.textContent.split(M),_=d.length-1;if(_>0){n.textContent=Pe?Pe.emptyScript:"";for(let f=0;f<_;f++)n.append(d[f],ge()),G.nextNode(),i.push({type:2,index:++r});n.append(d[_],ge())}}}else if(n.nodeType===8)if(n.data===wt)i.push({type:2,index:r});else{let d=-1;for(;(d=n.data.indexOf(M,d+1))!==-1;)i.push({type:7,index:r}),d+=M.length-1}r++}}static createElement(e,t){let o=K.createElement("template");return o.innerHTML=e,o}};function Y(s,e,t=s,o){if(e===Z)return e;let n=o!==void 0?t._$Co?.[o]:t._$Cl,r=ye(e)?void 0:e._$litDirective$;return n?.constructor!==r&&(n?._$AO?.(!1),r===void 0?n=void 0:(n=new r(s),n._$AT(s,t,o)),o!==void 0?(t._$Co??=[])[o]=n:t._$Cl=n),n!==void 0&&(e=Y(s,n._$AS(s,e.values),n,o)),e}var Re=class{constructor(e,t){this._$AV=[],this._$AN=void 0,this._$AD=e,this._$AM=t}get parentNode(){return this._$AM.parentNode}get _$AU(){return this._$AM._$AU}u(e){let{el:{content:t},parts:o}=this._$AD,n=(e?.creationScope??K).importNode(t,!0);G.currentNode=n;let r=G.nextNode(),a=0,l=0,i=o[0];for(;i!==void 0;){if(a===i.index){let c;i.type===2?c=new se(r,r.nextSibling,this,e):i.type===1?c=new i.ctor(r,i.name,i.strings,this,e):i.type===6&&(c=new Ne(r,this,e)),this._$AV.push(c),i=o[++l]}a!==i?.index&&(r=G.nextNode(),a++)}return G.currentNode=K,n}p(e){let t=0;for(let o of this._$AV)o!==void 0&&(o.strings!==void 0?(o._$AI(e,o,t),t+=o.strings.length-2):o._$AI(e[t])),t++}},se=class s{get _$AU(){return this._$AM?._$AU??this._$Cv}constructor(e,t,o,n){this.type=2,this._$AH=m,this._$AN=void 0,this._$AA=e,this._$AB=t,this._$AM=o,this.options=n,this._$Cv=n?.isConnected??!0}get parentNode(){let e=this._$AA.parentNode,t=this._$AM;return t!==void 0&&e?.nodeType===11&&(e=t.parentNode),e}get startNode(){return this._$AA}get endNode(){return this._$AB}_$AI(e,t=this){e=Y(this,e,t),ye(e)?e===m||e==null||e===""?(this._$AH!==m&&this._$AR(),this._$AH=m):e!==this._$AH&&e!==Z&&this._(e):e._$litType$!==void 0?this.$(e):e.nodeType!==void 0?this.T(e):ss(e)?this.k(e):this._(e)}O(e){return this._$AA.parentNode.insertBefore(e,this._$AB)}T(e){this._$AH!==e&&(this._$AR(),this._$AH=this.O(e))}_(e){this._$AH!==m&&ye(this._$AH)?this._$AA.nextSibling.data=e:this.T(K.createTextNode(e)),this._$AH=e}$(e){let{values:t,_$litType$:o}=e,n=typeof o=="number"?this._$AC(e):(o.el===void 0&&(o.el=we.createElement(ns(o.h,o.h[0]),this.options)),o);if(this._$AH?._$AD===n)this._$AH.p(t);else{let r=new Re(n,this),a=r.u(this.options);r.p(t),this.T(a),this._$AH=r}}_$AC(e){let t=ts.get(e.strings);return t===void 0&&ts.set(e.strings,t=new we(e)),t}k(e){vt(this._$AH)||(this._$AH=[],this._$AR());let t=this._$AH,o,n=0;for(let r of e)n===t.length?t.push(o=new s(this.O(ge()),this.O(ge()),this,this.options)):o=t[n],o._$AI(r),n++;n<t.length&&(this._$AR(o&&o._$AB.nextSibling,n),t.length=n)}_$AR(e=this._$AA.nextSibling,t){for(this._$AP?.(!1,!0,t);e!==this._$AB;){let o=Zt(e).nextSibling;Zt(e).remove(),e=o}}setConnected(e){this._$AM===void 0&&(this._$Cv=e,this._$AP?.(e))}},J=class{get tagName(){return this.element.tagName}get _$AU(){return this._$AM._$AU}constructor(e,t,o,n,r){this.type=1,this._$AH=m,this._$AN=void 0,this.element=e,this.name=t,this._$AM=n,this.options=r,o.length>2||o[0]!==""||o[1]!==""?(this._$AH=Array(o.length-1).fill(new String),this.strings=o):this._$AH=m}_$AI(e,t=this,o,n){let r=this.strings,a=!1;if(r===void 0)e=Y(this,e,t,0),a=!ye(e)||e!==this._$AH&&e!==Z,a&&(this._$AH=e);else{let l=e,i,c;for(e=r[0],i=0;i<r.length-1;i++)c=Y(this,l[o+i],t,i),c===Z&&(c=this._$AH[i]),a||=!ye(c)||c!==this._$AH[i],c===m?e=m:e!==m&&(e+=(c??"")+r[i+1]),this._$AH[i]=c}a&&!n&&this.j(e)}j(e){e===m?this.element.removeAttribute(this.name):this.element.setAttribute(this.name,e??"")}},Ee=class extends J{constructor(){super(...arguments),this.type=3}j(e){this.element[this.name]=e===m?void 0:e}},ze=class extends J{constructor(){super(...arguments),this.type=4}j(e){this.element.toggleAttribute(this.name,!!e&&e!==m)}},Le=class extends J{constructor(e,t,o,n,r){super(e,t,o,n,r),this.type=5}_$AI(e,t=this){if((e=Y(this,e,t,0)??m)===Z)return;let o=this._$AH,n=e===m&&o!==m||e.capture!==o.capture||e.once!==o.once||e.passive!==o.passive,r=e!==m&&(o===m||n);n&&this.element.removeEventListener(this.name,this,o),r&&this.element.addEventListener(this.name,this,e),this._$AH=e}handleEvent(e){typeof this._$AH=="function"?this._$AH.call(this.options?.host??this.element,e):this._$AH.handleEvent(e)}},Ne=class{constructor(e,t,o){this.element=e,this.type=6,this._$AN=void 0,this._$AM=t,this.options=o}get _$AU(){return this._$AM._$AU}_$AI(e){Y(this,e)}},as={M:yt,P:M,A:wt,C:1,L:rs,R:Re,D:ss,V:Y,I:se,H:J,N:ze,U:Le,B:Ee,F:Ne},vo=gt.litHtmlPolyfillSupport;vo?.(we,se),(gt.litHtmlVersions??=[]).push("3.3.3");var is=(s,e,t)=>{let o=t?.renderBefore??e,n=o._$litPart$;if(n===void 0){let r=t?.renderBefore??null;o._$litPart$=n=new se(e.insertBefore(ge(),r),r,void 0,t??{})}return n._$AI(s),n};var xt=globalThis,U=class extends H{constructor(){super(...arguments),this.renderOptions={host:this},this._$Do=void 0}createRenderRoot(){let e=super.createRenderRoot();return this.renderOptions.renderBefore??=e.firstChild,e}update(e){let t=this.render();this.hasUpdated||(this.renderOptions.isConnected=this.isConnected),super.update(e),this._$Do=is(t,this.renderRoot,this.renderOptions)}connectedCallback(){super.connectedCallback(),this._$Do?.setConnected(!0)}disconnectedCallback(){super.disconnectedCallback(),this._$Do?.setConnected(!1)}render(){return Z}};U._$litElement$=!0,U.finalized=!0,xt.litElementHydrateSupport?.({LitElement:U});var bo=xt.litElementPolyfillSupport;bo?.({LitElement:U});(xt.litElementVersions??=[]).push("4.2.2");var ls={tf_day:"1T",tf_week:"1W",tf_month:"1M",tf_six_month:"6M",tf_year:"1J",aria_timeframe:"Zeitraum",aria_currency:"W\xE4hrung",search_placeholder:"Name, Symbol oder ISIN",search_none:"Kein Wallet passt zu \u201E{query}\u201C.",aria_search:"Wallets durchsuchen",aria_search_clear:"Suche leeren",return_day:"Rendite \xFCber 1 Tag",return_week:"Rendite \xFCber 1 Woche",return_month:"Rendite \xFCber 1 Monat",return_six_month:"Rendite \xFCber 6 Monate",return_year:"Rendite \xFCber 1 Jahr",value_line:"Gesamtwert, {start} \u2013 heute",value_line_day:"Gesamtwert, letzte 24 Stunden",cash:"Bargeld",cash_plus:"Cash Plus",staked:"{share} im Staking",show_all:"Alle anzeigen ({count})",show_less:"Weniger anzeigen",detail_available:"Verf\xFCgbar",detail_staked:"Im Staking",detail_staking_apr:"Staking-APR",detail_average_buy_price:"\xD8 Kaufpreis",detail_invested:"Investiert",detail_profit_loss:"Gewinn / Verlust",detail_rewards:"Staking-Belohnungen",detail_rewards_net:"Netto, gesamt",detail_rewards_worth:"heute {value} wert",detail_payouts:"Gutschriften",detail_payouts_value:"{count} \xB7 zuletzt {date}",shares_one:"St\xFCck",shares_other:"St\xFCck",eye_hide:"Betr\xE4ge verbergen",eye_show:"Betr\xE4ge anzeigen",change_since:"\xC4nderung seit {date}",ecb_footer:"Preise in {currency}: Bitpandas Euro-Preise, umgerechnet zum EZB-Referenzkurs vom {date}. Ihre \xC4nderung enth\xE4lt die Bewegung des Kurses.",empty_portfolio:"Richte das Bitpanda Portfolio ein, dann erscheint es hier.",empty_wallets:"Noch keine Wallets.",empty_selection_wallets:"Keine Wallets in der Auswahl dieser Karte.",empty_selection_assets:"Keine Assets in der Auswahl dieser Karte.",empty_price_tracker:"Richte den Bitpanda Price Tracker ein und f\xFCge Assets hinzu, dann erscheinen hier Preise.",picker_portfolio:"Gesamtwert und Rendite mit Verlauf, Bargeld und Cash Plus, Verteilung und deine Wallets; jeder Teil l\xE4sst sich ausblenden.",picker_price_tracker:"Preise und \xC4nderungen deiner verfolgten Assets, je mit Verlauf, als Liste oder Kacheln.",invalid_option:"Ung\xFCltiger Wert f\xFCr \u201E{option}\u201C: {value}. Erlaubt: {allowed}.",allowed_text:"Text",allowed_assets:"eine Liste von Asset-IDs oder Ger\xE4te-IDs",allowed_groups:"eine Liste aus {values}",group_content:"Inhalt",group_wallets:"Wallets",group_assets:"Assets",group_appearance:"Darstellung",opt_title:"Titel",opt_title_help:"Leer lassen f\xFCr den grau angezeigten Namen",opt_timeframe:"Standard-Zeitraum",opt_timeframe_help:"Die Tasten 1T bis 1J auf der Karte wechseln ihn nur vor\xFCbergehend",tfo_day:"1 Tag",tfo_week:"1 Woche",tfo_month:"1 Monat",tfo_six_month:"6 Monate",tfo_year:"1 Jahr",opt_show_cash:"Bargeld und Cash Plus",opt_show_allocation:"Verteilung",opt_show_allocation_help:"Der farbige Balken mit den Anteilen der Asset-Gruppen und des Bargelds",opt_show_total:"Gesamtwert und Rendite",opt_show_total_help:"Die Zeitraum-Tasten bleiben, solange der Verlauf gezeigt wird",opt_show_line:"Verlauf des Gesamtwerts",opt_show_wallets:"Wallets",opt_group_wallets:"Wallets in Asset-Gruppen",opt_show_search:"Suchfeld",opt_show_search_help:"Findet Wallets nach Name, Symbol oder ISIN",opt_sort:"Sortieren nach",sort_value:"Wert",sort_return:"Rendite seit Kauf",sort_name:"Name",sort_selection:"Reihenfolge wie gew\xE4hlt",sort_change_desc:"\xC4nderung, h\xF6chste zuerst",sort_change_asc:"\xC4nderung, niedrigste zuerst",opt_sort_help_tracker:"\u201EReihenfolge wie gew\xE4hlt\u201C gilt nur mit \u201ENur die gew\xE4hlten\u201C Assets, sonst nach Name",opt_group_selection:"Angezeigte Asset-Gruppen",opt_group_selection_help:"Gilt nur f\xFCr die Wallets; Gesamtwert, Bargeld, Cash Plus und Verteilung zeigen immer das ganze Portfolio",opt_groups:"Asset-Gruppen w\xE4hlen",opt_asset_selection:"Angezeigte Assets",opt_asset_selection_wallets:"Angezeigte Wallets",sel_all:"Alle",sel_all_except:"Alle au\xDFer den gew\xE4hlten",sel_only:"Nur die gew\xE4hlten",opt_assets:"Assets w\xE4hlen",opt_assets_wallets:"Wallets w\xE4hlen",opt_assets_help:"Ein Asset aus einer ausgeblendeten Asset-Gruppe bleibt verborgen, auch wenn es hier gew\xE4hlt ist",opt_assets_help_wallets:"Ein Wallet aus einer ausgeblendeten Asset-Gruppe bleibt verborgen, auch wenn es hier gew\xE4hlt ist",opt_hide_amounts:"Betr\xE4ge zun\xE4chst verbergen",opt_hide_amounts_help:"Prozente bleiben sichtbar; das Auge oben auf der Karte zeigt die Betr\xE4ge nur vor\xFCbergehend",opt_limit:"Assets vor \u201EAlle anzeigen\u201C",opt_limit_wallets:"Wallets vor \u201EAlle anzeigen\u201C",opt_limit_help:"0 zeigt alle Assets",opt_limit_help_wallets:"Nur wenn \u201EWallets in Asset-Gruppen\u201C aus ist; 0 zeigt alle",opt_layout:"Anzeigen als",layout_list:"Liste",layout_tiles:"Kacheln",opt_currency:"Standard-W\xE4hrung",opt_currency_help:"Die Tasten auf der Karte wechseln sie nur vor\xFCbergehend; weitere W\xE4hrungen \xFCber \u201EKonfigurieren\u201C beim Price Tracker"};var cs={tf_day:"1D",tf_week:"1W",tf_month:"1M",tf_six_month:"6M",tf_year:"1Y",aria_timeframe:"Timeframe",aria_currency:"Currency",search_placeholder:"Name, symbol or ISIN",search_none:"No wallet matches \u201C{query}\u201D.",aria_search:"Search wallets",aria_search_clear:"Clear search",return_day:"return over 1 day",return_week:"return over 1 week",return_month:"return over 1 month",return_six_month:"return over 6 months",return_year:"return over 1 year",value_line:"Total value, {start} \u2013 today",value_line_day:"Total value, last 24 hours",cash:"Cash",cash_plus:"Cash Plus",staked:"{share} staked",show_all:"Show all ({count})",show_less:"Show less",detail_available:"Available",detail_staked:"Staked",detail_staking_apr:"Staking APR",detail_average_buy_price:"Average buy price",detail_invested:"Invested",detail_profit_loss:"Profit / loss",detail_rewards:"Staking rewards",detail_rewards_net:"Net, all time",detail_rewards_worth:"worth {value} today",detail_payouts:"Payouts",detail_payouts_value:"{count} \xB7 last {date}",shares_one:"share",shares_other:"shares",eye_hide:"Hide amounts",eye_show:"Show amounts",change_since:"Change since {date}",ecb_footer:"Prices in {currency}: Bitpanda's EUR prices converted at the ECB reference rate of {date}. Their change includes the rate's move.",empty_portfolio:"Set up the Bitpanda Portfolio to see it here.",empty_wallets:"No wallets yet.",empty_selection_wallets:"No wallets in this card's selection.",empty_selection_assets:"No assets in this card's selection.",empty_price_tracker:"Set up the Bitpanda Price Tracker and add assets to it to see prices here.",picker_portfolio:"Total value and return with a value line, Cash and Cash Plus, allocation and your wallets; each part can be left out.",picker_price_tracker:"Prices and changes of the assets you track, each with a line, as a list or tiles.",invalid_option:"Invalid value for \u201C{option}\u201D: {value}. Allowed: {allowed}.",allowed_text:"text",allowed_assets:"a list of asset IDs or device IDs",allowed_groups:"a list of {values}",group_content:"Content",group_wallets:"Wallets",group_assets:"Assets",group_appearance:"Appearance",opt_title:"Title",opt_title_help:"Leave empty for the name shown in grey",opt_timeframe:"Default timeframe",opt_timeframe_help:"The 1D to 1Y buttons on the card change it only temporarily",tfo_day:"1 day",tfo_week:"1 week",tfo_month:"1 month",tfo_six_month:"6 months",tfo_year:"1 year",opt_show_cash:"Cash and Cash Plus",opt_show_allocation:"Allocation bar",opt_show_allocation_help:"The coloured bar showing the share of each asset group and of cash",opt_show_total:"Total value and return",opt_show_total_help:"The timeframe buttons stay while the line is shown",opt_show_line:"Total value line",opt_show_wallets:"Wallets",opt_group_wallets:"Wallets in asset groups",opt_show_search:"Search field",opt_show_search_help:"Finds wallets by name, symbol or ISIN",opt_sort:"Sort by",sort_value:"Value",sort_return:"Return since purchase",sort_name:"Name",sort_selection:"Order as chosen",sort_change_desc:"Change, highest first",sort_change_asc:"Change, lowest first",opt_sort_help_tracker:"\u201COrder as chosen\u201D applies only when assets are set to \u201COnly the ones chosen\u201D; otherwise by name",opt_group_selection:"Asset groups shown",opt_group_selection_help:"Applies to the wallets only; total value, Cash, Cash Plus and allocation always show the whole portfolio",opt_groups:"Choose asset groups",opt_asset_selection:"Assets shown",opt_asset_selection_wallets:"Wallets shown",sel_all:"All",sel_all_except:"All except the ones chosen",sel_only:"Only the ones chosen",opt_assets:"Choose assets",opt_assets_wallets:"Choose wallets",opt_assets_help:"An asset from a hidden asset group stays hidden, even when chosen here",opt_assets_help_wallets:"A wallet from a hidden asset group stays hidden, even when chosen here",opt_hide_amounts:"Hide amounts initially",opt_hide_amounts_help:"Percentages stay visible; the eye at the top of the card shows the amounts only temporarily",opt_limit:"Assets before \u201CShow all\u201D",opt_limit_wallets:"Wallets before \u201CShow all\u201D",opt_limit_help:"0 shows every asset",opt_limit_help_wallets:"Only while \u201CWallets in asset groups\u201D is off; 0 shows all",opt_layout:"Show as",layout_list:"List",layout_tiles:"Tiles",opt_currency:"Default currency",opt_currency_help:"The buttons on the card change it only temporarily; more currencies via \u201CConfigure\u201D on the Price Tracker"};var ds={tf_day:"1D",tf_week:"1S",tf_month:"1M",tf_six_month:"6M",tf_year:"1A",aria_timeframe:"Periodo",aria_currency:"Moneda",search_placeholder:"Nombre, s\xEDmbolo o ISIN",search_none:"Ning\xFAn wallet coincide con \xAB{query}\xBB.",aria_search:"Buscar wallets",aria_search_clear:"Borrar b\xFAsqueda",return_day:"rentabilidad en 1 d\xEDa",return_week:"rentabilidad en 1 semana",return_month:"rentabilidad en 1 mes",return_six_month:"rentabilidad en 6 meses",return_year:"rentabilidad en 1 a\xF1o",value_line:"Valor total, {start} \u2013 hoy",value_line_day:"Valor total, \xFAltimas 24 horas",cash:"Efectivo",cash_plus:"Cash Plus",staked:"{share} en staking",show_all:"Mostrar todo ({count})",show_less:"Mostrar menos",detail_available:"Disponible",detail_staked:"En staking",detail_staking_apr:"APR de staking",detail_average_buy_price:"Precio medio de compra",detail_invested:"Importe invertido",detail_profit_loss:"Ganancia / p\xE9rdida",detail_rewards:"Recompensas de staking",detail_rewards_net:"Neto, en total",detail_rewards_worth:"hoy valen {value}",detail_payouts:"Pagos",detail_payouts_value:"{count} \xB7 \xFAltimo el {date}",shares_one:"t\xEDtulo",shares_other:"t\xEDtulos",shares_many:"t\xEDtulos",eye_hide:"Ocultar importes",eye_show:"Mostrar importes",change_since:"Variaci\xF3n desde el {date}",ecb_footer:"Precios en {currency}: precios en EUR de Bitpanda convertidos al tipo de referencia del BCE del {date}. Su variaci\xF3n incluye la del tipo.",empty_portfolio:"Configura el Bitpanda Portfolio para verlo aqu\xED.",empty_wallets:"Todav\xEDa no hay wallets.",empty_selection_wallets:"Ning\xFAn wallet en la selecci\xF3n de esta tarjeta.",empty_selection_assets:"Ning\xFAn activo en la selecci\xF3n de esta tarjeta.",empty_price_tracker:"Configura el Bitpanda Price Tracker y a\xF1ade activos para ver precios aqu\xED.",picker_portfolio:"Valor total y rentabilidad con l\xEDnea, efectivo y Cash Plus, distribuci\xF3n y tus wallets; cada parte se puede ocultar.",picker_price_tracker:"Precios y cambios de los activos que sigues, cada uno con su l\xEDnea, en lista o en mosaicos.",invalid_option:"Valor no v\xE1lido para \xAB{option}\xBB: {value}. Permitidos: {allowed}.",allowed_text:"texto",allowed_assets:"una lista de ID de activo o ID de dispositivo",allowed_groups:"una lista de {values}",group_content:"Contenido",group_wallets:"Wallets",group_assets:"Activos",group_appearance:"Apariencia",opt_title:"T\xEDtulo",opt_title_help:"D\xE9jalo vac\xEDo para el nombre mostrado en gris",opt_timeframe:"Periodo predeterminado",opt_timeframe_help:"Los botones 1D a 1A de la tarjeta lo cambian solo temporalmente",tfo_day:"1 d\xEDa",tfo_week:"1 semana",tfo_month:"1 mes",tfo_six_month:"6 meses",tfo_year:"1 a\xF1o",opt_show_cash:"Efectivo y Cash Plus",opt_show_allocation:"Barra de distribuci\xF3n",opt_show_allocation_help:"La barra de colores con la proporci\xF3n de cada grupo de activos y del efectivo",opt_show_total:"Valor total y rentabilidad",opt_show_total_help:"Los botones de periodo se mantienen mientras se muestre la l\xEDnea",opt_show_line:"L\xEDnea del valor total",opt_show_wallets:"Wallets",opt_group_wallets:"Wallets en grupos de activos",opt_show_search:"Campo de b\xFAsqueda",opt_show_search_help:"Encuentra wallets por nombre, s\xEDmbolo o ISIN",opt_sort:"Ordenar por",sort_value:"Valor",sort_return:"Rentabilidad desde la compra",sort_name:"Nombre",sort_selection:"Orden de selecci\xF3n",sort_change_desc:"Cambio, mayor primero",sort_change_asc:"Cambio, menor primero",opt_sort_help_tracker:"\xABOrden de selecci\xF3n\xBB solo se aplica con \xABSolo los elegidos\xBB en los activos; si no, por nombre",opt_group_selection:"Grupos de activos mostrados",opt_group_selection_help:"Solo afecta a los wallets; el valor total, el efectivo, Cash Plus y la distribuci\xF3n muestran siempre toda la cartera",opt_groups:"Elegir grupos de activos",opt_asset_selection:"Activos mostrados",opt_asset_selection_wallets:"Wallets mostrados",sel_all:"Todos",sel_all_except:"Todos excepto los elegidos",sel_only:"Solo los elegidos",opt_assets:"Elegir activos",opt_assets_wallets:"Elegir wallets",opt_assets_help:"Un activo de un grupo de activos oculto sigue oculto, aunque se elija aqu\xED",opt_assets_help_wallets:"Un wallet de un grupo de activos oculto sigue oculto, aunque se elija aqu\xED",opt_hide_amounts:"Ocultar inicialmente los importes",opt_hide_amounts_help:"Los porcentajes siguen visibles; el ojo de la parte superior de la tarjeta muestra los importes solo temporalmente",opt_limit:"Activos antes de \xABMostrar todo\xBB",opt_limit_wallets:"Wallets antes de \xABMostrar todo\xBB",opt_limit_help:"0 muestra todos los activos",opt_limit_help_wallets:"Solo si \xABWallets en grupos de activos\xBB est\xE1 desactivado; 0 muestra todo",opt_layout:"Mostrar como",layout_list:"Lista",layout_tiles:"Mosaicos",opt_currency:"Moneda predeterminada",opt_currency_help:"Los botones de la tarjeta la cambian solo temporalmente; m\xE1s monedas con \xABConfigurar\xBB en el Price Tracker"};var ps={tf_day:"1J",tf_week:"1S",tf_month:"1M",tf_six_month:"6M",tf_year:"1A",aria_timeframe:"P\xE9riode",aria_currency:"Devise",search_placeholder:"Nom, symbole ou ISIN",search_none:"Aucun wallet ne correspond \xE0 \xAB\xA0{query}\xA0\xBB.",aria_search:"Rechercher des wallets",aria_search_clear:"Effacer la recherche",return_day:"rendement sur 1 jour",return_week:"rendement sur 1 semaine",return_month:"rendement sur 1 mois",return_six_month:"rendement sur 6 mois",return_year:"rendement sur 1 an",value_line:"Valeur totale, {start} \u2013 aujourd'hui",value_line_day:"Valeur totale, derni\xE8res 24 heures",cash:"Liquidit\xE9s",cash_plus:"Cash Plus",staked:"{share} en staking",show_all:"Tout afficher ({count})",show_less:"Afficher moins",detail_available:"Disponible",detail_staked:"En staking",detail_staking_apr:"APR du staking",detail_average_buy_price:"Prix d'achat moyen",detail_invested:"Montant investi",detail_profit_loss:"Gain / perte",detail_rewards:"R\xE9compenses de staking",detail_rewards_net:"Net, depuis le d\xE9but",detail_rewards_worth:"valant {value} aujourd'hui",detail_payouts:"Versements",detail_payouts_value:"{count} \xB7 dernier le {date}",shares_one:"titre",shares_other:"titres",shares_many:"titres",eye_hide:"Masquer les montants",eye_show:"Afficher les montants",change_since:"Variation depuis le {date}",ecb_footer:"Prix en {currency}\xA0: prix en EUR de Bitpanda convertis au taux de r\xE9f\xE9rence de la BCE du {date}. Leur variation inclut celle du taux.",empty_portfolio:"Configurez le Bitpanda Portfolio pour le voir ici.",empty_wallets:"Aucun wallet pour le moment.",empty_selection_wallets:"Aucun wallet dans la s\xE9lection de cette carte.",empty_selection_assets:"Aucun actif dans la s\xE9lection de cette carte.",empty_price_tracker:"Configurez le Bitpanda Price Tracker et ajoutez-y des actifs pour voir les prix ici.",picker_portfolio:"Valeur totale et rendement avec courbe, liquidit\xE9s et Cash Plus, r\xE9partition et vos wallets\xA0; chaque partie peut \xEAtre masqu\xE9e.",picker_price_tracker:"Prix et variations des actifs que vous suivez, chacun avec sa courbe, en liste ou en tuiles.",invalid_option:"Valeur non valide pour \xAB\xA0{option}\xA0\xBB\xA0: {value}. Valeurs possibles\xA0: {allowed}.",allowed_text:"texte",allowed_assets:"une liste d'ID d'actifs ou d'ID d'appareils",allowed_groups:"une liste d'\xE9l\xE9ments parmi {values}",group_content:"Contenu",group_wallets:"Wallets",group_assets:"Actifs",group_appearance:"Apparence",opt_title:"Titre",opt_title_help:"Laisser vide pour le nom affich\xE9 en gris",opt_timeframe:"P\xE9riode par d\xE9faut",opt_timeframe_help:"Les boutons 1J \xE0 1A de la carte ne la changent que temporairement",tfo_day:"1 jour",tfo_week:"1 semaine",tfo_month:"1 mois",tfo_six_month:"6 mois",tfo_year:"1 an",opt_show_cash:"Liquidit\xE9s et Cash Plus",opt_show_allocation:"Barre de r\xE9partition",opt_show_allocation_help:"La barre color\xE9e avec la part de chaque groupe d'actifs et des liquidit\xE9s",opt_show_total:"Valeur totale et rendement",opt_show_total_help:"Les boutons de p\xE9riode restent tant que la courbe est affich\xE9e",opt_show_line:"Courbe de la valeur totale",opt_show_wallets:"Wallets",opt_group_wallets:"Wallets par groupe d'actifs",opt_show_search:"Champ de recherche",opt_show_search_help:"Trouve les wallets par nom, symbole ou ISIN",opt_sort:"Trier par",sort_value:"Valeur",sort_return:"Rendement depuis l'achat",sort_name:"Nom",sort_selection:"Ordre de s\xE9lection",sort_change_desc:"Variation, la plus forte d'abord",sort_change_asc:"Variation, la plus faible d'abord",opt_sort_help_tracker:"\xAB\xA0Ordre de s\xE9lection\xA0\xBB ne s'applique qu'avec \xAB\xA0Seulement ceux choisis\xA0\xBB pour les actifs\xA0; sinon, tri par nom",opt_group_selection:"Groupes d'actifs affich\xE9s",opt_group_selection_help:"S'applique seulement aux wallets\xA0; la valeur totale, les liquidit\xE9s, Cash Plus et la r\xE9partition portent toujours sur l'ensemble du portefeuille",opt_groups:"Choisir les groupes d'actifs",opt_asset_selection:"Actifs affich\xE9s",opt_asset_selection_wallets:"Wallets affich\xE9s",sel_all:"Tous",sel_all_except:"Tous sauf ceux choisis",sel_only:"Seulement ceux choisis",opt_assets:"Choisir les actifs",opt_assets_wallets:"Choisir les wallets",opt_assets_help:"Un actif d'un groupe d'actifs masqu\xE9 reste masqu\xE9, m\xEAme s'il est choisi ici",opt_assets_help_wallets:"Un wallet d'un groupe d'actifs masqu\xE9 reste masqu\xE9, m\xEAme s'il est choisi ici",opt_hide_amounts:"Masquer initialement les montants",opt_hide_amounts_help:"Les pourcentages restent visibles\xA0; l'\u0153il en haut de la carte n'affiche les montants que temporairement",opt_limit:"Actifs avant \xAB\xA0Tout afficher\xA0\xBB",opt_limit_wallets:"Wallets avant \xAB\xA0Tout afficher\xA0\xBB",opt_limit_help:"0 affiche tous les actifs",opt_limit_help_wallets:"Seulement si \xAB\xA0Wallets par groupe d'actifs\xA0\xBB est d\xE9sactiv\xE9\xA0; 0 affiche tout",opt_layout:"Afficher en",layout_list:"Liste",layout_tiles:"Tuiles",opt_currency:"Devise par d\xE9faut",opt_currency_help:"Les boutons de la carte ne la changent que temporairement\xA0; d'autres devises via \xAB\xA0Configurer\xA0\xBB dans le Price Tracker"};var us={tf_day:"1G",tf_week:"1S",tf_month:"1M",tf_six_month:"6M",tf_year:"1A",aria_timeframe:"Periodo",aria_currency:"Valuta",search_placeholder:"Nome, simbolo o ISIN",search_none:"Nessun wallet corrisponde a \xAB{query}\xBB.",aria_search:"Cerca nei wallet",aria_search_clear:"Cancella ricerca",return_day:"rendimento su 1 giorno",return_week:"rendimento su 1 settimana",return_month:"rendimento su 1 mese",return_six_month:"rendimento su 6 mesi",return_year:"rendimento su 1 anno",value_line:"Valore totale, {start} \u2013 oggi",value_line_day:"Valore totale, ultime 24 ore",cash:"Liquidit\xE0",cash_plus:"Cash Plus",staked:"{share} in staking",show_all:"Mostra tutto ({count})",show_less:"Mostra meno",detail_available:"Disponibile",detail_staked:"In staking",detail_staking_apr:"APR dello staking",detail_average_buy_price:"Prezzo medio di acquisto",detail_invested:"Importo investito",detail_profit_loss:"Profitto / perdita",detail_rewards:"Ricompense di staking",detail_rewards_net:"Netto, in totale",detail_rewards_worth:"oggi valgono {value}",detail_payouts:"Accrediti",detail_payouts_value:"{count} \xB7 ultimo il {date}",shares_one:"pezzo",shares_other:"pezzi",shares_many:"pezzi",eye_hide:"Nascondi gli importi",eye_show:"Mostra gli importi",change_since:"Variazione dal {date}",ecb_footer:"Prezzi in {currency}: prezzi in EUR di Bitpanda convertiti al tasso di riferimento BCE del {date}. La loro variazione include quella del tasso.",empty_portfolio:"Configura il Bitpanda Portfolio per vederlo qui.",empty_wallets:"Ancora nessun wallet.",empty_selection_wallets:"Nessun wallet nella selezione di questa scheda.",empty_selection_assets:"Nessun asset nella selezione di questa scheda.",empty_price_tracker:"Configura il Bitpanda Price Tracker e aggiungi degli asset per vedere i prezzi qui.",picker_portfolio:"Valore totale e rendimento con linea, liquidit\xE0 e Cash Plus, ripartizione e i tuoi wallet; ogni parte si pu\xF2 nascondere.",picker_price_tracker:"Prezzi e variazioni degli asset che segui, ognuno con la sua linea, come elenco o riquadri.",invalid_option:"Valore non valido per \xAB{option}\xBB: {value}. Consentiti: {allowed}.",allowed_text:"testo",allowed_assets:"un elenco di ID asset o ID dispositivo",allowed_groups:"un elenco di valori tra {values}",group_content:"Contenuto",group_wallets:"Wallet",group_assets:"Asset",group_appearance:"Aspetto",opt_title:"Titolo",opt_title_help:"Lascia vuoto per il nome mostrato in grigio",opt_timeframe:"Periodo predefinito",opt_timeframe_help:"I pulsanti da 1G a 1A sulla scheda lo cambiano solo temporaneamente",tfo_day:"1 giorno",tfo_week:"1 settimana",tfo_month:"1 mese",tfo_six_month:"6 mesi",tfo_year:"1 anno",opt_show_cash:"Liquidit\xE0 e Cash Plus",opt_show_allocation:"Barra di ripartizione",opt_show_allocation_help:"La barra colorata con le quote dei gruppi di asset e della liquidit\xE0",opt_show_total:"Valore totale e rendimento",opt_show_total_help:"I pulsanti del periodo restano finch\xE9 \xE8 mostrata la linea",opt_show_line:"Linea del valore totale",opt_show_wallets:"Wallet",opt_group_wallets:"Wallet in gruppi di asset",opt_show_search:"Campo di ricerca",opt_show_search_help:"Trova i wallet per nome, simbolo o ISIN",opt_sort:"Ordina per",sort_value:"Valore",sort_return:"Rendimento dall'acquisto",sort_name:"Nome",sort_selection:"Ordine di selezione",sort_change_desc:"Variazione, maggiore prima",sort_change_asc:"Variazione, minore prima",opt_sort_help_tracker:"\xABOrdine di selezione\xBB vale solo con \xABSolo quelli scelti\xBB per gli asset; altrimenti per nome",opt_group_selection:"Gruppi di asset mostrati",opt_group_selection_help:"Vale solo per i wallet; valore totale, liquidit\xE0, Cash Plus e ripartizione mostrano sempre l'intero portafoglio",opt_groups:"Scegli i gruppi di asset",opt_asset_selection:"Asset mostrati",opt_asset_selection_wallets:"Wallet mostrati",sel_all:"Tutti",sel_all_except:"Tutti tranne quelli scelti",sel_only:"Solo quelli scelti",opt_assets:"Scegli gli asset",opt_assets_wallets:"Scegli i wallet",opt_assets_help:"Un asset di un gruppo di asset nascosto resta nascosto, anche se scelto qui",opt_assets_help_wallets:"Un wallet di un gruppo di asset nascosto resta nascosto, anche se scelto qui",opt_hide_amounts:"Nascondi inizialmente gli importi",opt_hide_amounts_help:"Le percentuali restano visibili; l'occhio in alto nella scheda mostra gli importi solo temporaneamente",opt_limit:"Asset prima di \xABMostra tutto\xBB",opt_limit_wallets:"Wallet prima di \xABMostra tutto\xBB",opt_limit_help:"0 mostra tutti gli asset",opt_limit_help_wallets:"Solo se \xABWallet in gruppi di asset\xBB \xE8 disattivato; 0 mostra tutto",opt_layout:"Mostra come",layout_list:"Elenco",layout_tiles:"Riquadri",opt_currency:"Valuta predefinita",opt_currency_help:"I pulsanti sulla scheda la cambiano solo temporaneamente; altre valute tramite \xABConfigura\xBB nel Price Tracker"};var hs={tf_day:"1D",tf_week:"1W",tf_month:"1M",tf_six_month:"6M",tf_year:"1J",aria_timeframe:"Periode",aria_currency:"Valuta",search_placeholder:"Naam, symbool of ISIN",search_none:"Geen wallet past bij \u2018{query}\u2019.",aria_search:"Wallets doorzoeken",aria_search_clear:"Zoekopdracht wissen",return_day:"rendement over 1 dag",return_week:"rendement over 1 week",return_month:"rendement over 1 maand",return_six_month:"rendement over 6 maanden",return_year:"rendement over 1 jaar",value_line:"Totale waarde, {start} \u2013 vandaag",value_line_day:"Totale waarde, laatste 24 uur",cash:"Contanten",cash_plus:"Cash Plus",staked:"{share} in staking",show_all:"Alles tonen ({count})",show_less:"Minder tonen",detail_available:"Beschikbaar",detail_staked:"In staking",detail_staking_apr:"Staking-APR",detail_average_buy_price:"Gemiddelde aankoopprijs",detail_invested:"Ge\xEFnvesteerd",detail_profit_loss:"Winst / verlies",detail_rewards:"Stakingbeloningen",detail_rewards_net:"Netto, totaal",detail_rewards_worth:"vandaag {value} waard",detail_payouts:"Uitbetalingen",detail_payouts_value:"{count} \xB7 laatste {date}",shares_one:"stuk",shares_other:"stuks",eye_hide:"Bedragen verbergen",eye_show:"Bedragen tonen",change_since:"Verandering sinds {date}",ecb_footer:"Prijzen in {currency}: de EUR-prijzen van Bitpanda, omgerekend tegen de ECB-referentiekoers van {date}. Hun verandering omvat de beweging van de koers.",empty_portfolio:"Stel het Bitpanda Portfolio in om het hier te zien.",empty_wallets:"Nog geen wallets.",empty_selection_wallets:"Geen wallets in de selectie van deze kaart.",empty_selection_assets:"Geen assets in de selectie van deze kaart.",empty_price_tracker:"Stel de Bitpanda Price Tracker in en voeg er assets aan toe om hier prijzen te zien.",picker_portfolio:"Totale waarde en rendement met een lijn, contanten en Cash Plus, verdeling en je wallets; elk deel kan worden verborgen.",picker_price_tracker:"Prijzen en veranderingen van de assets die je volgt, elk met een lijn, als lijst of tegels.",invalid_option:"Ongeldige waarde voor \u2018{option}\u2019: {value}. Toegestaan: {allowed}.",allowed_text:"tekst",allowed_assets:"een lijst met asset-ID's of apparaat-ID's",allowed_groups:"een lijst met waarden uit {values}",group_content:"Inhoud",group_wallets:"Wallets",group_assets:"Assets",group_appearance:"Uiterlijk",opt_title:"Titel",opt_title_help:"Leeg laten voor de grijs getoonde naam",opt_timeframe:"Standaardperiode",opt_timeframe_help:"De knoppen 1D tot 1J op de kaart wijzigen die alleen tijdelijk",tfo_day:"1 dag",tfo_week:"1 week",tfo_month:"1 maand",tfo_six_month:"6 maanden",tfo_year:"1 jaar",opt_show_cash:"Contanten en Cash Plus",opt_show_allocation:"Verdelingsbalk",opt_show_allocation_help:"De gekleurde balk met het aandeel van elke assetgroep en van de contanten",opt_show_total:"Totale waarde en rendement",opt_show_total_help:"De periodeknoppen blijven zolang de lijn wordt getoond",opt_show_line:"Lijn van de totale waarde",opt_show_wallets:"Wallets",opt_group_wallets:"Wallets in assetgroepen",opt_show_search:"Zoekveld",opt_show_search_help:"Vindt wallets op naam, symbool of ISIN",opt_sort:"Sorteren op",sort_value:"Waarde",sort_return:"Rendement sinds aankoop",sort_name:"Naam",sort_selection:"Volgorde zoals gekozen",sort_change_desc:"Verandering, hoogste eerst",sort_change_asc:"Verandering, laagste eerst",opt_sort_help_tracker:"\u2018Volgorde zoals gekozen\u2019 geldt alleen bij \u2018Alleen de gekozen\u2019 assets, anders op naam",opt_group_selection:"Getoonde assetgroepen",opt_group_selection_help:"Geldt alleen voor de wallets; totale waarde, contanten, Cash Plus en verdeling tonen altijd het hele portfolio",opt_groups:"Assetgroepen kiezen",opt_asset_selection:"Getoonde assets",opt_asset_selection_wallets:"Getoonde wallets",sel_all:"Alle",sel_all_except:"Alle behalve de gekozen",sel_only:"Alleen de gekozen",opt_assets:"Assets kiezen",opt_assets_wallets:"Wallets kiezen",opt_assets_help:"Een asset uit een verborgen assetgroep blijft verborgen, ook als die hier is gekozen",opt_assets_help_wallets:"Een wallet uit een verborgen assetgroep blijft verborgen, ook als die hier is gekozen",opt_hide_amounts:"Bedragen aanvankelijk verbergen",opt_hide_amounts_help:"Percentages blijven zichtbaar; het oog bovenaan de kaart toont de bedragen alleen tijdelijk",opt_limit:"Assets v\xF3\xF3r \u2018Alles tonen\u2019",opt_limit_wallets:"Wallets v\xF3\xF3r \u2018Alles tonen\u2019",opt_limit_help:"0 toont alle assets",opt_limit_help_wallets:"Alleen als \u2018Wallets in assetgroepen\u2019 uit staat; 0 toont alles",opt_layout:"Weergeven als",layout_list:"Lijst",layout_tiles:"Tegels",opt_currency:"Standaardvaluta",opt_currency_help:"De knoppen op de kaart wijzigen die alleen tijdelijk; meer valuta via \u2018Configureren\u2019 bij de Price Tracker"};var ms={tf_day:"1D",tf_week:"1T",tf_month:"1M",tf_six_month:"6M",tf_year:"1R",aria_timeframe:"Okres",aria_currency:"Waluta",search_placeholder:"Nazwa, symbol lub ISIN",search_none:"\u017Baden portfel nie pasuje do \u201E{query}\u201D.",aria_search:"Szukaj portfeli",aria_search_clear:"Wyczy\u015B\u0107 wyszukiwanie",return_day:"stopa zwrotu za 1 dzie\u0144",return_week:"stopa zwrotu za 1 tydzie\u0144",return_month:"stopa zwrotu za 1 miesi\u0105c",return_six_month:"stopa zwrotu za 6 miesi\u0119cy",return_year:"stopa zwrotu za 1 rok",value_line:"Warto\u015B\u0107 ca\u0142kowita, {start} \u2013 dzi\u015B",value_line_day:"Warto\u015B\u0107 ca\u0142kowita, ostatnie 24 godziny",cash:"Got\xF3wka",cash_plus:"Cash Plus",staked:"{share} w stakingu",show_all:"Poka\u017C wszystkie ({count})",show_less:"Poka\u017C mniej",detail_available:"Dost\u0119pne",detail_staked:"W stakingu",detail_staking_apr:"APR stakingu",detail_average_buy_price:"\u015Arednia cena zakupu",detail_invested:"Zainwestowano",detail_profit_loss:"Zysk / strata",detail_rewards:"Nagrody za staking",detail_rewards_net:"Netto, \u0142\u0105cznie",detail_rewards_worth:"dzi\u015B warte {value}",detail_payouts:"Naliczenia",detail_payouts_value:"{count} \xB7 ostatnio {date}",shares_one:"sztuka",shares_other:"sztuki",shares_few:"sztuki",shares_many:"sztuk",eye_hide:"Ukryj kwoty",eye_show:"Poka\u017C kwoty",change_since:"Zmiana od {date}",ecb_footer:"Ceny w {currency}: ceny Bitpandy w EUR przeliczone po kursie referencyjnym EBC z {date}. Ich zmiana obejmuje ruch kursu.",empty_portfolio:"Skonfiguruj Bitpanda Portfolio, aby zobaczy\u0107 je tutaj.",empty_wallets:"Brak portfeli.",empty_selection_wallets:"Brak portfeli w wyborze tej karty.",empty_selection_assets:"Brak aktyw\xF3w w wyborze tej karty.",empty_price_tracker:"Skonfiguruj Bitpanda Price Tracker i dodaj aktywa, aby zobaczy\u0107 tutaj ceny.",picker_portfolio:"Warto\u015B\u0107 ca\u0142kowita i stopa zwrotu z wykresem, got\xF3wka i Cash Plus, alokacja oraz twoje portfele; ka\u017Cd\u0105 cz\u0119\u015B\u0107 mo\u017Cna ukry\u0107.",picker_price_tracker:"Ceny i zmiany \u015Bledzonych aktyw\xF3w, ka\u017Cde z wykresem, jako lista lub kafelki.",invalid_option:"Nieprawid\u0142owa warto\u015B\u0107 dla \u201E{option}\u201D: {value}. Dozwolone: {allowed}.",allowed_text:"tekst",allowed_assets:"lista identyfikator\xF3w aktyw\xF3w lub urz\u0105dze\u0144",allowed_groups:"lista warto\u015Bci spo\u015Br\xF3d {values}",group_content:"Zawarto\u015B\u0107",group_wallets:"Portfele",group_assets:"Aktywa",group_appearance:"Wygl\u0105d",opt_title:"Tytu\u0142",opt_title_help:"Pozostaw puste, aby u\u017Cy\u0107 nazwy pokazanej na szaro",opt_timeframe:"Domy\u015Blny okres",opt_timeframe_help:"Przyciski od 1D do 1R na karcie zmieniaj\u0105 go tylko tymczasowo",tfo_day:"1 dzie\u0144",tfo_week:"1 tydzie\u0144",tfo_month:"1 miesi\u0105c",tfo_six_month:"6 miesi\u0119cy",tfo_year:"1 rok",opt_show_cash:"Got\xF3wka i Cash Plus",opt_show_allocation:"Pasek alokacji",opt_show_allocation_help:"Kolorowy pasek pokazuj\u0105cy udzia\u0142 grup aktyw\xF3w i got\xF3wki",opt_show_total:"Warto\u015B\u0107 ca\u0142kowita i stopa zwrotu",opt_show_total_help:"Przyciski okresu pozostaj\u0105, dop\xF3ki wy\u015Bwietlany jest wykres",opt_show_line:"Wykres warto\u015Bci ca\u0142kowitej",opt_show_wallets:"Portfele",opt_group_wallets:"Portfele w grupach aktyw\xF3w",opt_show_search:"Pole wyszukiwania",opt_show_search_help:"Znajduje portfele po nazwie, symbolu lub ISIN",opt_sort:"Sortuj wed\u0142ug",sort_value:"Warto\u015B\u0107",sort_return:"Stopa zwrotu od zakupu",sort_name:"Nazwa",sort_selection:"Kolejno\u015B\u0107 wyboru",sort_change_desc:"Zmiana, najwy\u017Csza najpierw",sort_change_asc:"Zmiana, najni\u017Csza najpierw",opt_sort_help_tracker:"\u201EKolejno\u015B\u0107 wyboru\u201D dzia\u0142a tylko przy opcji \u201ETylko wybrane\u201D dla aktyw\xF3w; w przeciwnym razie wed\u0142ug nazwy",opt_group_selection:"Wy\u015Bwietlane grupy aktyw\xF3w",opt_group_selection_help:"Dotyczy tylko portfeli; warto\u015B\u0107 ca\u0142kowita, got\xF3wka, Cash Plus i alokacja zawsze pokazuj\u0105 ca\u0142e portfolio",opt_groups:"Wybierz grupy aktyw\xF3w",opt_asset_selection:"Wy\u015Bwietlane aktywa",opt_asset_selection_wallets:"Wy\u015Bwietlane portfele",sel_all:"Wszystkie",sel_all_except:"Wszystkie opr\xF3cz wybranych",sel_only:"Tylko wybrane",opt_assets:"Wybierz aktywa",opt_assets_wallets:"Wybierz portfele",opt_assets_help:"Aktywo z ukrytej grupy aktyw\xF3w pozostaje ukryte, nawet je\u015Bli wybrano je tutaj",opt_assets_help_wallets:"Portfel z ukrytej grupy aktyw\xF3w pozostaje ukryty, nawet je\u015Bli wybrano go tutaj",opt_hide_amounts:"Pocz\u0105tkowo ukrywaj kwoty",opt_hide_amounts_help:"Procenty pozostaj\u0105 widoczne; oko u g\xF3ry karty pokazuje kwoty tylko tymczasowo",opt_limit:"Aktywa przed \u201EPoka\u017C wszystkie\u201D",opt_limit_wallets:"Portfele przed \u201EPoka\u017C wszystkie\u201D",opt_limit_help:"0 pokazuje wszystkie aktywa",opt_limit_help_wallets:"Tylko gdy opcja \u201EPortfele w grupach aktyw\xF3w\u201D jest wy\u0142\u0105czona; 0 pokazuje wszystkie",opt_layout:"Poka\u017C jako",layout_list:"Lista",layout_tiles:"Kafelki",opt_currency:"Domy\u015Blna waluta",opt_currency_help:"Przyciski na karcie zmieniaj\u0105 j\u0105 tylko tymczasowo; wi\u0119cej walut przez \u201EKonfiguruj\u201D w Price Trackerze"};var _s={en:cs,de:ls,fr:ps,nl:hs,it:us,es:ds,pl:ms},fs=s=>s in _s,gs="en",xo=s=>{let e=s.toLowerCase().replace(/[-_].*$/,"");return fs(e)?e:"en"};function W(s){let e=s??document.querySelector("home-assistant")?.hass;return e?xo(e.locale.language):gs}function ys(s){return fs(s.locale.language.toLowerCase().replace(/[-_].*$/,""))}function ws(s){gs=W(s)}var vs=s=>_s[W(s)];function h(s,e,t={}){return vs(s)[e].replace(/\{(\w+)\}/g,(o,n)=>n in t?String(t[n]):o)}function bs(s,e,t){let o=new Intl.PluralRules(W(s)).select(t);return vs(s)[`${e}_${o}`]}async function xs(s){await s.loadBackendTranslation("selector","bitpanda")}function kt(s,e){return s.localize(`component.bitpanda.selector.asset_group.options.${e}`)||e}var B=["day","week","month","six_month","year"],L=["crypto","stock","etf","etc","index","metal","other"],O=["all","all_except","only"],ks=["EUR","CHF","CZK","DKK","GBP","HUF","NOK","PLN","RON","SEK","TRY","USD"],$t=["value","return","name"],At=["selection","name","change_desc","change_asc"],St=["list","tiles"];var P=s=>({allowed:()=>s.join(", "),check:e=>typeof e=="string"&&s.includes(e)}),j={allowed:()=>"true, false",check:s=>typeof s=="boolean"},$s={allowed:()=>h(void 0,"allowed_text"),check:s=>typeof s=="string"},Ie={allowed:()=>"0, 1, 2, \u2026",check:s=>typeof s=="number"&&Number.isInteger(s)&&s>=0},He={allowed:()=>h(void 0,"allowed_assets"),check:s=>Array.isArray(s)&&s.every(e=>typeof e=="string")},Me={allowed:()=>h(void 0,"allowed_groups",{values:L.join(", ")}),check:s=>Array.isArray(s)&&s.every(e=>L.includes(e))},As={allowed:()=>"EUR, USD, \u2026",check:s=>typeof s=="string"&&/^[A-Z]{3}$/.test(s)};function We(s,e){if(s===null||typeof s!="object"||Array.isArray(s))throw new Error(h(void 0,"invalid_option",{option:"type",value:JSON.stringify(s),allowed:"custom:\u2026"}));let t=Object.fromEntries(Object.entries(s).filter(([,o])=>o!==null));for(let[o,n]of Object.entries(e)){let r=t[o];if(r!==void 0&&!n.check(r))throw new Error(h(void 0,"invalid_option",{option:o,value:JSON.stringify(r),allowed:n.allowed()}))}return t}var ne=(s,e)=>({select:{mode:"dropdown",options:s.map(t=>({value:t,label:e(t)}))}}),Oe=s=>({name:"title",default:s,selector:{text:{}}}),je=()=>({name:"timeframe",selector:ne(B,s=>h(void 0,`tfo_${s}`))}),D=(s,e)=>({name:s,default:e,selector:{boolean:{}}}),De=s=>({name:"limit",default:s,selector:{number:{min:0,max:100,mode:"box"}}}),Ue=s=>({name:"sort",selector:ne(s,e=>h(void 0,`sort_${e}`))});function re(){return document.querySelector("home-assistant")?.hass}var ko=3e3;async function Be(s){if(!s)return{};let e;try{let o=(await Promise.race([s.callWS({type:"frontend/get_translations",language:s.language,category:"selector",integration:["bitpanda"]}),new Promise(r=>{e=setTimeout(()=>r(void 0),ko)})]))?.resources??{},n={};for(let r of L){let a=o[`component.bitpanda.selector.asset_group.options.${r}`];typeof a=="string"&&a&&(n[r]=a)}return n}catch{return{}}finally{clearTimeout(e)}}var Fe=s=>[{name:"group_selection",selector:ne(O,e=>h(void 0,`sel_${e}`))},{name:"groups",selector:{select:{multiple:!0,mode:"dropdown",options:L.map(e=>({value:e,label:s[e]??e}))}}}],Ve=s=>[{name:"asset_selection",selector:ne(O,e=>h(void 0,`sel_${e}`))},{name:"assets",selector:{device:{multiple:!0,filter:[{integration:"bitpanda",model:s}]}}}],ae=()=>({type:"divider",name:""}),X=(s,e)=>({type:"expandable",name:"",flatten:!0,title:h(void 0,s),schema:e}),$o={title:"opt_title",timeframe:"opt_timeframe",show_total:"opt_show_total",show_graph:"opt_show_line",show_cash:"opt_show_cash",show_allocation:"opt_show_allocation",show_wallets:"opt_show_wallets",group_wallets:"opt_group_wallets",show_search:"opt_show_search",sort:"opt_sort",group_selection:"opt_group_selection",groups:"opt_groups",asset_selection:"opt_asset_selection",assets:"opt_assets",hide_amounts:"opt_hide_amounts",limit:"opt_limit",layout:"opt_layout",currency:"opt_currency"},Ao={title:"opt_title_help",timeframe:"opt_timeframe_help",show_total:"opt_show_total_help",show_allocation:"opt_show_allocation_help",hide_amounts:"opt_hide_amounts_help",show_search:"opt_show_search_help",assets:"opt_assets_help",limit:"opt_limit_help",currency:"opt_currency_help"};function qe(s){let e=$o[s.name];return e?h(void 0,e):void 0}function Ge(s){let e=Ao[s.name];return e?h(void 0,e):void 0}var Ke=me`
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
`;var Ze={title:$s},F=class extends U{constructor(){super(...arguments);this.timeframe="day";this.amountsHidden=!1;this.seriesRevision=0;this.watched=[]}static{this.properties={hass:{attribute:!1},config:{state:!0},timeframe:{state:!0},amountsHidden:{state:!0},seriesRevision:{state:!0}}}static{this.styles=Ke}setConfig(t){let o=this.validate(t),n=o;this.config=o,this.timeframe=n.timeframe??"day",this.amountsHidden=n.hide_amounts??!1}toggleAmounts(){this.amountsHidden=!this.amountsHidden}seriesArrived(){this.seriesRevision+=1}selectTimeframe(t){this.timeframe=t}shouldUpdate(t){if(t.size!==1||!t.has("hass"))return!0;let o=t.get("hass"),n=this.hass;return!o||!n||o.entities!==n.entities||o.devices!==n.devices||o.locale!==n.locale||o.localize!==n.localize?!0:this.watched.some(r=>o.states[r]!==n.states[r])}connectedCallback(){super.connectedCallback(),typeof ResizeObserver<"u"&&(this.resizer=new ResizeObserver(()=>this.fitLayout()),this.resizer.observe(this))}disconnectedCallback(){this.resizer?.disconnect(),this.resizer=void 0,super.disconnectedCallback()}updated(t){super.updated(t),this.remeasures(t)&&this.fitLayout()}fitLayout(){}remeasures(t){return!0}willUpdate(t){let o=this.hass;if(!o)return;ws(o);let n=W(o);n!==this.categoryLanguage&&(this.categoryLanguage=n,xs(o)),this.watched=this.watchedEntities()}getCardSize(){return 3}getGridOptions(){return{columns:12,min_columns:6}}};var So="bitpanda",Ss={return_day:"day",return_week:"week",return_month:"month",return_six_month:"six_month",return_year:"year"},Cs=s=>s.replace(/\s+/g,"").toLowerCase();function Co(s,e){let t=(s??"").trim();return t&&Cs(t)!==Cs(e)?`${t} (${e})`:e}function Ct(s,e){let t=new Map;for(let n of Object.values(s.entities)){if(!n||n.platform!==So||!n.device_id)continue;let r=t.get(n.device_id)??[];r.push(n),t.set(n.device_id,r)}let o=[];for(let[n,r]of t){let a=s.devices[n];a?.model===e&&o.push([a,r])}return o}var Q=s=>typeof s=="string"&&s!==""?s:void 0,Ts=new Map,To=/ (Wallet|Price Tracker)$/;function Rs(s,e,t){let o=t.map(a=>s.states[a.entity_id]?.attributes).find(a=>a?.asset),n;if(o){let a=Q(o.asset)??"",l=Q(o.asset_isin),i=Q(o.asset_category),c=Q(o.asset_name);n={name:Co(c,a),shortName:c??a,symbol:a,...l?{isin:l}:{},...i&&L.includes(i)?{category:i}:{}},Ts.set(e.id,n)}else{let a=(Q(e.name)??"").replace(To,"");n=Ts.get(e.id)??{name:a,shortName:a,symbol:""}}let r=Q(e.name_by_user);return{deviceId:e.id,assetId:e.serial_number??"",...n,...r?{name:r,shortName:r}:{}}}function Ye(s){let[e]=Ct(s,"Portfolio");if(!e)return;let[t,o]=e,n={deviceId:t.id,returns:{},wallets:[]};for(let r of o){let a=r.translation_key??"";a==="total_value"?n.totalValue=r.entity_id:a==="cash"?n.cash=r.entity_id:a==="cash_plus"?n.cashPlus=r.entity_id:a in Ss&&(n.returns[Ss[a]]=r.entity_id)}for(let[r,a]of Ct(s,"Wallet")){let l=Rs(s,r,a);for(let i of a)i.translation_key==="wallet"?l.available=i.entity_id:i.translation_key==="wallet_total"?l.total=i.entity_id:i.translation_key==="staking"&&(l.staking=i.entity_id);n.wallets.push(l)}return n}function ve(s){return Ct(s,"Price Tracker").map(([e,t])=>{let o={};for(let n of t){if(n.translation_key!=="price")continue;let r=Q(s.states[n.entity_id]?.attributes.unit_of_measurement);r&&(o[r]=n.entity_id)}return{...Rs(s,e,t),prices:o}})}function Je(s){let e=new Set(s.flatMap(o=>Object.keys(o.prices))),t=[...e].filter(o=>o!=="EUR").sort();return e.has("EUR")?["EUR",...t]:t}function Xe(s,e,t){if(e==="all")return[...s];let o=e==="only";return s.filter(n=>t.includes(n.category??"other")===o)}var Ps=(s,e)=>e===s.deviceId||e!==""&&e===s.assetId;function Qe(s,e,t){if(e==="all_except")return s.filter(o=>!t.some(n=>Ps(o,n)));if(e==="only"){let o=[];for(let n of t){let r=s.find(a=>Ps(a,n));r&&!o.includes(r)&&o.push(r)}return o}return[...s]}function et(s){switch(s.locale.number_format){case"comma_decimal":return"en-US";case"decimal_comma":return"de";case"space_comma":return"fr";case"quote_decimal":return"de-CH";case"system":return;default:return s.locale.language}}function Tt(s,e,t,o=0){return new Intl.NumberFormat(et(s),{maximumFractionDigits:t,minimumFractionDigits:o,useGrouping:s.locale.number_format!=="none"}).format(e)}function Po(s,e){let t=e!==0&&Math.abs(e)<1e-4;return new Intl.NumberFormat(et(s),{...t?{maximumSignificantDigits:2}:{maximumFractionDigits:4},roundingMode:"trunc",useGrouping:s.locale.number_format!=="none"}).format(e)}function be(s,e,t,o,n=!1){let r=n?Po(s,e):Tt(s,e,8);return t==="stock"||t==="etf"||t==="etc"?`${r} ${bs(s,"shares",e)}`:`${r} ${t==="metal"?"g":o}`}var Pt=new Set(["unavailable","unknown"]);function N(s,e){let t=e?s.states[e]:void 0;return t&&!Pt.has(t.state)?s.formatEntityState(t):void 0}function Es(s,e,t){let o=e?s.states[e]:void 0;return o&&t!==void 0?s.formatEntityState({...o,state:String(t)}):void 0}function xe(s,e,t,o=!1){return Ls(s,e,t,2,o)}function zs(s,e,t){let o=Math.abs(e);return Ls(s,e,t,o>=10||o===0?2:o>=1?4:8,!1)}function Ls(s,e,t,o,n){try{return new Intl.NumberFormat(et(s),{style:"currency",currency:t,minimumFractionDigits:2,maximumFractionDigits:o,useGrouping:s.locale.number_format!=="none",...n?{signDisplay:"exceptZero"}:{}}).format(e)}catch{return`${Tt(s,e,o)} ${t}`}}function Ro(s){let e=Math.abs(s);return e===0||e>=10?2:e>=1?4:e>=.1?5:e>=.001?6:e>=1e-4?7:8}function Ns(s,e,t){let o=e?s.states[e]:void 0;if(!o||Pt.has(o.state)||t===void 0||!Number.isFinite(t))return;let n=s.entities[o.entity_id]?.display_precision,r=typeof n=="number"?n:Ro(Number(o.state)),a=Number(t.toFixed(r))===0?0 .toFixed(r):t.toFixed(r),l=s.formatEntityState({...o,state:a});return Number(a)>0?`+${l}`:l}function $(s,e){let t=e?s.states[e]:void 0;if(!t||Pt.has(t.state)||t.state.trim()==="")return;let o=Number(t.state);return Number.isFinite(o)?o:void 0}var Eo=new Set(["cs","de","fi","fr","sk","sv"]),Is=s=>Eo.has(s.locale.language)?"\xA0":"";function I(s,e){if(e===void 0||!Number.isFinite(e))return{text:"\u2014",direction:"none"};let t=new Intl.NumberFormat(et(s),{minimumFractionDigits:2,maximumFractionDigits:2,signDisplay:"exceptZero",useGrouping:s.locale.number_format!=="none"}).format(e),o=Is(s),r=Math.round(Math.abs(e)*100)===0?"flat":e>0?"up":"down";return{text:`${t}${o}%`,direction:r}}function ie(s,e,t){let o=Is(s);return`${Tt(s,e,t)}${o}%`}function R(s){return s==="up"||s==="down"?s:""}function ee(s){return s==="up"?"\u25B2":s==="down"?"\u25BC":""}function Rt(s){return ys(s)?s.locale.language:"en"}function Hs(s){return s.locale.time_zone==="server"?s.config?.time_zone:void 0}function zo(s){let e=s.locale.time_format;return e==="12"||e==="24"?e==="12":new Date("January 1, 2023 22:00:00").toLocaleString(e==="system"?void 0:s.locale.language).includes("10")}function ke(s,e){let t=Hs(s),o=r=>new Intl.DateTimeFormat("en",{year:"numeric",timeZone:t}).format(r),n=o(e)===o(Date.now())?{}:{year:"numeric"};return new Intl.DateTimeFormat(Rt(s),{day:"numeric",month:"short",...n,timeZone:t}).format(e)}function Ms(s,e){let t=/^(\d{4})-(\d{2})-(\d{2})$/.exec(e);if(!t)return;let o=Date.UTC(Number(t[1]),Number(t[2])-1,Number(t[3]));return new Intl.DateTimeFormat(Rt(s),{day:"numeric",month:"long",timeZone:"UTC"}).format(o)}function tt(s,e){let t=zo(s);return new Intl.DateTimeFormat(Rt(s),{day:"numeric",month:"short",hour:t?"numeric":"2-digit",minute:"2-digit",hourCycle:t?"h12":"h23",timeZone:Hs(s)}).format(e)}var{I:wr}=as;var Ws=s=>s.strings===void 0;var Os={ATTRIBUTE:1,CHILD:2,PROPERTY:3,BOOLEAN_ATTRIBUTE:4,EVENT:5,ELEMENT:6},Et=s=>(...e)=>({_$litDirective$:s,values:e}),st=class{constructor(e){}get _$AU(){return this._$AM._$AU}_$AT(e,t,o){this._$Ct=e,this._$AM=t,this._$Ci=o}_$AS(e,t){return this.update(e,t)}update(e,t){return this.render(...t)}};var $e=(s,e)=>{let t=s._$AN;if(t===void 0)return!1;for(let o of t)o._$AO?.(e,!1),$e(o,e);return!0},ot=s=>{let e,t;do{if((e=s._$AM)===void 0)break;t=e._$AN,t.delete(s),s=e}while(t?.size===0)},js=s=>{for(let e;e=s._$AM;s=e){let t=e._$AN;if(t===void 0)e._$AN=t=new Set;else if(t.has(s))break;t.add(s),Io(e)}};function Lo(s){this._$AN!==void 0?(ot(this),this._$AM=s,js(this)):this._$AM=s}function No(s,e=!1,t=0){let o=this._$AH,n=this._$AN;if(n!==void 0&&n.size!==0)if(e)if(Array.isArray(o))for(let r=t;r<o.length;r++)$e(o[r],!1),ot(o[r]);else o!=null&&($e(o,!1),ot(o));else $e(this,s)}var Io=s=>{s.type==Os.CHILD&&(s._$AP??=No,s._$AQ??=Lo)},nt=class extends st{constructor(){super(...arguments),this._$AN=void 0}_$AT(e,t,o){super._$AT(e,t,o),js(this),this.isConnected=e._$AU}_$AO(e,t=!0){e!==this.isConnected&&(this.isConnected=e,e?this.reconnected?.():this.disconnected?.()),t&&($e(this,e),ot(this))}setValue(e){if(Ws(this._$Ct))this._$Ct._$AI(e,this);else{let t=[...this._$Ct._$AH];t[this._$Ci]=e,this._$Ct._$AI(t,this,0)}}disconnected(){}reconnected(){}};var Ds=()=>new Lt,Lt=class{},zt=new WeakMap,Us=Et(class extends nt{render(s){return m}update(s,[e]){let t=e!==this.G;return t&&this.rt(void 0),(t||this.lt!==this.ct)&&(this.G=e,this.ht=s.options?.host,this.rt(this.ct=s.element)),m}rt(s){if(this.G!==void 0)if(this.isConnected||(s=void 0),typeof this.G=="function"){let e=this.ht??globalThis,t=zt.get(e);t===void 0&&(t=new WeakMap,zt.set(e,t)),t.get(this.G)!==void 0&&this.G.call(this.ht,void 0),t.set(this.G,s),s!==void 0&&this.G.call(this.ht,s)}else this.G.value=s}get lt(){return typeof this.G=="function"?zt.get(this.ht??globalThis)?.get(this.G):this.G?.value}disconnected(){this.lt===this.ct&&this.rt(void 0)}reconnected(){this.rt(this.ct)}});var Ho="M12,9A3,3 0 0,0 9,12A3,3 0 0,0 12,15A3,3 0 0,0 15,12A3,3 0 0,0 12,9M12,17A5,5 0 0,1 7,12A5,5 0 0,1 12,7A5,5 0 0,1 17,12A5,5 0 0,1 12,17M12,4.5C7,4.5 2.73,7.61 1,12C2.73,16.39 7,19.5 12,19.5C17,19.5 21.27,16.39 23,12C21.27,7.61 17,4.5 12,4.5Z",Mo="M11.83,9L15,12.16C15,12.11 15,12.05 15,12A3,3 0 0,0 12,9C11.94,9 11.89,9 11.83,9M7.53,9.8L9.08,11.35C9.03,11.56 9,11.77 9,12A3,3 0 0,0 12,15C12.22,15 12.44,14.97 12.65,14.92L14.2,16.47C13.53,16.8 12.79,17 12,17A5,5 0 0,1 7,12C7,11.21 7.2,10.47 7.53,9.8M2,4.27L4.28,6.55L4.73,7C3.08,8.3 1.78,10 1,12C2.73,16.39 7,19.5 12,19.5C13.55,19.5 15.03,19.2 16.38,18.66L16.81,19.08L19.73,22L21,20.73L3.27,3M12,7A5,5 0 0,1 17,12C17,12.64 16.87,13.26 16.64,13.82L19.57,16.75C21.07,15.5 22.27,13.86 23,12C21.27,7.61 17,4.5 12,4.5C10.6,4.5 9.26,4.75 8,5.2L10.17,7.35C10.74,7.13 11.35,7 12,7Z",Fs="M7.41,8.58L12,13.17L16.59,8.58L18,10L12,16L6,10L7.41,8.58Z",Vs="M7.41,15.41L12,10.83L16.59,15.41L18,14L12,8L6,14L7.41,15.41Z",Wo="M8.59,16.58L13.17,12L8.59,7.41L10,6L16,12L10,18L8.59,16.58Z",Oo="M9.5,3A6.5,6.5 0 0,1 16,9.5C16,11.11 15.41,12.59 14.44,13.73L14.71,14H15.5L20.5,19L19,20.5L14,15.5V14.71L13.73,14.44C12.59,15.41 11.11,16 9.5,16A6.5,6.5 0 0,1 3,9.5A6.5,6.5 0 0,1 9.5,3M9.5,5C7,5 5,7 5,9.5C5,12 7,14 9.5,14C12,14 14,12 14,9.5C14,7 12,5 9.5,5Z",jo="M19,6.41L17.59,5L12,10.59L6.41,5L5,6.41L10.59,12L5,17.59L6.41,19L12,13.41L17.59,19L19,17.59L13.41,12L19,6.41Z",le=s=>oe`<svg viewBox="0 0 24 24" aria-hidden="true"><path d=${s}></path></svg>`,Nt={down:Fs,up:Vs,right:Wo};function T(s){return e=>{(e.key==="Enter"||e.key===" ")&&(e.preventDefault(),s())}}function ce(s,e){s.dispatchEvent(new CustomEvent("hass-more-info",{bubbles:!0,composed:!0,detail:{entityId:e}}))}function de(s,e){let t=s.filter(o=>o.second!==void 0);return t.length>0&&t.every(o=>o.first+e+o.second<=o.room)}function A(s,e){return p`<span class="amount ${e?"blur":""}">${s??"\u2014"}</span>`}function te(s){return p`<div class="empty">${s}</div>`}function Ae(s,e,t){return p`<div class="head">
    <div class="title">${e}</div>
    ${t?p`<button
          class="icon-btn eye"
          aria-label=${h(s,t.hidden?"eye_show":"eye_hide")}
          title=${h(s,t.hidden?"eye_show":"eye_hide")}
          @click=${t.toggle}
        >
          ${le(t.hidden?Mo:Ho)}
        </button>`:m}
  </div>`}function qs(s,e,t,o,n){let{text:r,direction:a}=I(s,e),l=ee(a);return p`<div class="hero-line">
    <span class="chip ${R(a)}" role="button" tabindex="0" @click=${o} @keydown=${T(o)}
      >${l?`${l} `:""}${r}</span
    >
    ${a!=="none"&&n?.text?p`<span class="chip-amount ${R(a)}">${A(n.text,n.hidden)}</span>`:m}
    <span class="chip-label">${h(s,`return_${t}`)}</span>
  </div>`}function Gs(s,e,t,o,n){return p`<div class="seg" role="radiogroup" aria-label=${s} @keydown=${a=>{let l=a.key==="ArrowRight"||a.key==="ArrowDown"?1:a.key==="ArrowLeft"||a.key==="ArrowUp"?-1:0;if(l===0)return;a.preventDefault();let i=(e.indexOf(t)+l+e.length)%e.length;n(e[i]),a.currentTarget.querySelectorAll("[role=radio]")[i]?.focus()}}>
    ${e.map(a=>p`<span
          role="radio"
          aria-checked=${a===t?"true":"false"}
          tabindex=${a===t?0:-1}
          @click=${()=>n(a)}
          @keydown=${T(()=>n(a))}
          >${o(a)}</span
        >`)}
  </div>`}function rt(s,e,t){return Gs(h(s,"aria_timeframe"),B,e,o=>h(s,`tf_${o}`),t)}function Ks(s,e,t,o){return e.length<2?null:Gs(h(s,"aria_currency"),e,t,n=>n,o)}var Do=new Set(["unavailable","unknown"]);function k(s,e){if(!s||Do.has(s.state))return;let t=s.attributes[e];return typeof t=="number"&&Number.isFinite(t)?t:void 0}function Zs(s,e,t){let o=Ds(),n=()=>{t(""),o.value?.focus()};return p`<div class="search" role="search">
    ${le(Oo)}<input
      ${Us(o)}
      type="text"
      .value=${e}
      placeholder=${h(s,"search_placeholder")}
      aria-label=${h(s,"aria_search")}
      autocomplete="off"
      spellcheck="false"
      @input=${r=>t(r.target.value)}
    />${e?p`<span class="clear" role="button" tabindex="0" aria-label=${h(s,"aria_search_clear")} @click=${n} @keydown=${T(n)}
          >${le(jo)}</span
        >`:m}
  </div>`}var Uo={\u00DF:"ss",\u00F8:"o",\u00E6:"ae",\u0153:"oe",\u0142:"l",\u0111:"d",\u00F0:"d",\u00FE:"th",\u0131:"i"};function Bs(s){return s.normalize("NFD").replace(/\p{M}/gu,"").toLowerCase().replace(/[ßøæœłđðþı]/gu,e=>Uo[e]??e).replace(/[^\p{L}\p{N}\s]/gu,"")}function Ys(s,e){let t=Bs(e).split(/\s+/).filter(Boolean),o=Bs(`${s.name} ${s.symbol} ${s.isin??""}`);return t.length>0&&t.every(n=>o.includes(n))}function Js(s){let{hass:e,wallet:t,hidden:o,onTap:n,chevron:r}=s,a=t.total?e.states[t.total]:void 0,l=k(a,"units"),i=$(e,t.total),c=$(e,t.staking),u=i&&c&&c>0?c/i*100:void 0,{text:d,direction:_}=I(e,k(a,"total_return_percent")),f=ee(_),v=_==="none"?p`<span class="wchip none">—</span>`:p`<span class="wchip ${R(_)}">${f?`${f} `:""}${d}</span>`,y=u===void 0?m:p`<div class="stake"><span class="badge">${h(e,"staked",{share:ie(e,u,0)})}</span></div>`,g=x=>{x.stopPropagation(),r?.toggle()};return p`<div class="wallet">
    <div class="tap" role="button" tabindex="0" @click=${n} @keydown=${T(n)}>
      <div class="main">
        <div class="n" title=${t.shortName}>${t.shortName}</div>
        <div class="sub ${u===void 0?"":"staked"}">
          <div class="s">
            <span class="units"
              >${A(l===void 0?void 0:be(e,l,t.category,t.symbol,!0),o)}</span
            >${t.isin?p` · <span class="isin">${t.isin}</span>`:m}
          </div>
          ${y}
        </div>
      </div>
      <div class="right">${v}<span class="val">${A(N(e,t.total),o)}</span></div>
    </div>
    ${r?p`<span
          class="chevron"
          role="button"
          tabindex="0"
          aria-expanded=${r.open?"true":"false"}
          @click=${g}
          @keydown=${x=>{x.stopPropagation(),T(r.toggle)(x)}}
          >${le(r.open?Vs:Fs)}</span
        >`:m}
  </div>`}function at(s,e,t){let o=a=>$(s,a.total)??Number.NEGATIVE_INFINITY,n=a=>k(a.total?s.states[a.total]:void 0,"total_return_percent")??Number.NEGATIVE_INFINITY,r=(a,l)=>a.name.localeCompare(l.name,W(s));return[...e].sort((a,l)=>t==="name"?r(a,l):(t==="value"?o(l)-o(a):n(l)-n(a))||r(a,l))}var Bo=window.customElements,Fo=1e4;function Vo(s=()=>window.customElements,e=Bo,t=Fo){let o=Date.now();return new Promise(n=>{let r=()=>{let a=s();a!==e||a.get("home-assistant")||Date.now()-o>=t?n(a):setTimeout(r,50)};r()})}var qo="https://github.com/Spegeli/hacs_bitpanda#-dashboard-cards";function Go(s,e,t,o,n={}){let r=s.entities[e];return!r||r.platform!=="bitpanda"||!r.device_id?null:(typeof t=="string"?[t]:t).includes(s.devices[r.device_id]?.model??"")?{config:{type:`custom:${o}`,...n}}:null}function it(s,e,t){Vo().then(r=>{r.get(s)||r.define(s,e)});let o=window;if(o.customCards??=[],o.customCards.some(r=>r.type===s))return;let{model:n}=t;o.customCards.push({type:s,name:t.name,get description(){return t.description()},preview:!0,documentationURL:qo,...n?{getEntitySuggestion:(r,a)=>Go(r,a,n,s,e.getStubConfig?.())}:{}})}var Ko={day:[864e5,"5minute"],week:[6048e5,"hour"],month:[2592e6,"hour"],six_month:[157248e5,"day"],year:[31536e6,"day"]};function lt(s){return s==="5minute"?5*6e4:s==="hour"?36e5:864e5}function Xs(s){return s.timeframe==="month"?(s.end-s.start)/120:0}function ue(s,e){let[t,o]=Ko[s];return{timeframe:s,start:e-t,end:e,period:o}}var Zo=s=>typeof s=="number"?s:Date.parse(s);async function Yo(s,e,t){if(e.length===0)return{};let o;try{o=await s.callWS({type:"recorder/statistics_during_period",start_time:new Date(t.start).toISOString(),end_time:new Date(t.end).toISOString(),statistic_ids:[...e],period:t.period,types:["state"]})}catch{return}let n={};for(let[r,a]of Object.entries(o))n[r]=a.map(l=>({t:Zo(l.start),v:l.state})).filter(l=>typeof l.v=="number"&&Number.isFinite(l.t)).sort((l,i)=>l.t-i.t);return n}var ct="portfolio";async function Qs(s,e,t){let o;try{o=await s.callWS({type:"bitpanda/portfolio_history",timeframe:t.timeframe})}catch{return}let r=(Array.isArray(o?.points)?o.points:[]).filter(a=>Array.isArray(a)&&typeof a[0]=="number"&&typeof a[1]=="number"&&Number.isFinite(a[0])&&Number.isFinite(a[1])).map(([a,l])=>({t:a,v:l})).sort((a,l)=>a.t-l.t);return{[ct]:r}}var pe=class{constructor(e,t=Yo){this.onUpdate=e;this.fetch=t;this.key="";this.end=0;this.latest=0;this.current={}}request(e,t,o,n=""){let r=`${o.timeframe}|${[...t].sort().join(",")}|${n}`;if(r===this.key&&o.end-this.end<lt(o.period))return;o.timeframe!==this.timeframe&&(this.current={}),this.key=r,this.timeframe=o.timeframe,this.end=o.end;let a=++this.latest;this.fetch(e,t,o).then(l=>{if(a===this.latest){if(l===void 0){this.key="";return}this.current=l,this.onUpdate()}})}series(e){return this.current[e]}};function eo(s,e,t){let o=lt(t.period),n=s.find(r=>r.t>=t.start-o);if(!(e===void 0||n===void 0||n.v===0))return{change:(e-n.v)/n.v*100,amount:e-n.v,...n.t>t.start+o?{since:n.t}:{}}}var to=2,It=s=>Math.round(s*100)/100;function Ht(s,e,t,o){return It(t===e?o/2:o-to-(s-e)/(t-e)*(o-2*to))}function so(s,e){let t=0;return s.forEach((o,n)=>{Math.abs(o.t-e)<Math.abs(s[t].t-e)&&(t=n)}),t}function Jo(s,e){if(e<=0||s.length<3)return s;let t=n=>Math.floor(n.t/e),o=[];for(let n of s.slice(0,-1)){let r=o[o.length-1];(!r||t(n)!==t(r))&&o.push(n)}return o.push(s[s.length-1]),o}function oo(s,e,t,o,n,r=0){let a=n??1.5*lt(e.period),l=[],i;for(let g of s)(!i||g.t-i.t>a)&&l.push([]),l[l.length-1]?.push(g),i=g;let c=l.map(g=>Jo(g,r)),u=c.flat().map(g=>g.v),d=Math.min(...u),_=Math.max(...u),f=e.end-e.start,v=g=>It((g-e.start)/f*t),y=g=>Ht(g,d,_,o);return c.map(g=>g.map(x=>[v(x.t),y(x.v)]))}function Xo(s,e,t,o,n,r=0){return oo(s,e,t,o,n,r).map(a=>a.length===1?`M${a[0]?.[0]},${a[0]?.[1]}l0.01,0`:a.map(([l,i],c)=>`${c===0?"M":"L"}${l},${i}`).join("")).join("")}function Qo(s,e,t,o,n,r=0){return oo(s,e,t,o,n,r).map(a=>{let l=a[0],i=a[a.length-1];return`M${l[0]},${o}${a.map(([c,u])=>`L${c},${u}`).join("")}L${i[0]},${o}Z`}).join("")}var Mt=(s,e)=>s.length>0&&s[s.length-1].t-s[0].t>=(e.end-e.start)/10;function dt(s,e,t){let{width:o,height:n,fill:r,className:a,gapMs:l,stepMs:i}=t;return Mt(s,e)?oe`<svg class=${a} viewBox="0 0 ${o} ${n}" preserveAspectRatio="none" aria-hidden="true">${r?oe`<path class="area" d=${Qo(s,e,o,n,l,i)}></path>`:null}<path class="line" d=${Xo(s,e,o,n,l,i)} vector-effect="non-scaling-stroke"></path></svg>`:oe`<svg class=${a} viewBox="0 0 ${o} ${n}" preserveAspectRatio="none" aria-hidden="true"></svg>`}var en=480,Wt=72,pt=s=>`${(s*100).toFixed(2)}%`;function tn(s,e,t){let{hass:o,refs:n,window:r,hidden:a,cursor:l,onCursor:i}=s,c=e.map(b=>b.v),u=Math.min(...c),d=Math.max(...c),_=r.end-r.start,f=b=>{let w=b.currentTarget.getBoundingClientRect(),z=Math.min(Math.max((b.clientX-w.left)/w.width,0),1);return so(e,r.start+z*_)},v=b=>i(f(b)),y=()=>i(void 0),g=b=>{b.pointerType!=="mouse"&&y()},x=n.totalValue?o.states[n.totalValue]?.attributes.unit_of_measurement:void 0,S=typeof x=="string"&&!a?b=>xe(o,b,x):void 0,C=l===void 0?void 0:e[l],E=m;if(C){let b=(C.t-r.start)/_,w=r.timeframe==="day"||r.timeframe==="week"?tt(o,C.t):ke(o,C.t),z=b<.25?"start":b>.75?"end":"";E=p`${S?p`<span class="tag high">${S(d)}</span><span class="tag middle">${S((d+u)/2)}</span
            ><span class="tag low">${S(u)}</span>`:m}
      <div class="cursor" style="left:${pt(b)}"></div>
      <div class="dot" style="left:${pt(b)};top:${pt(Ht(C.v,u,d,Wt)/Wt)}"></div>
      <div class="tip ${z}" style="left:${pt(b)}">${S?`${w} \xB7 ${S(C.v)}`:w}</div>`}let V=dt(e,r,{width:en,height:Wt,fill:!0,className:`spark ${t}`,gapMs:Number.POSITIVE_INFINITY});return Mt(e,r)?p`<div class="plot" @pointerdown=${v} @pointermove=${v} @pointerup=${g} @pointercancel=${y} @pointerleave=${y}>
    ${V}
    <div class="mid"></div>
    ${E}
  </div>`:p`<div class="plot">${V}</div>`}function sn(s,e,t){if(e.timeframe==="day")return h(s,"value_line_day");let o=t[0]?.t??e.start;return h(s,"value_line",{start:ke(s,Math.max(e.start,o))})}function on(s,e,t){let o=$(s,e.totalValue),n=$(s,e.returns[t]),r=e.totalValue?s.states[e.totalValue]?.attributes.unit_of_measurement:void 0;if(!(o===void 0||n===void 0||n<=-100||typeof r!="string"))return xe(s,o*n/(100+n),r,!0)}function no(s){let{host:e,hass:t,refs:o,timeframe:n,hidden:r,window:a,points:l}=s,i=$(t,o.returns[n]),c=R(I(t,i).direction)||"flat",u=d=>()=>{d&&ce(e,d)};return p`${s.total?p`<div class="hero" role="button" tabindex="0" @click=${u(o.totalValue)} @keydown=${T(u(o.totalValue))}>
            ${A(N(t,o.totalValue),r)}
          </div>
          ${qs(t,i,n,u(o.returns[n]),{text:on(t,o,n),hidden:r})}`:m}
    ${s.total||s.line?rt(t,n,s.onTimeframe):m}
    ${s.line&&l&&l.length>0?p`${tn(s,l,c)}
          <div class="caption">${sn(t,a,l)}</div>`:m}`}var nn="bitpanda-portfolio-card",ro={crypto:"var(--blue-color, #4269d0)",stock:"var(--indigo-color, #3f51b5)",etf:"var(--amber-color, #efb118)",etc:"var(--cyan-color, #00bcd4)",index:"var(--purple-color, #a463f2)",metal:"var(--green-color, #3ca951)",other:"var(--pink-color, #ff8ab7)",cash_plus:"var(--deep-orange-color, #ff725c)",cash:"var(--teal-color, #6cc5b0)"},ao=s=>s.category??"other",rn={limit:"opt_limit_wallets",asset_selection:"opt_asset_selection_wallets",assets:"opt_assets_wallets"},an={limit:"opt_limit_help_wallets",group_selection:"opt_group_selection_help",assets:"opt_assets_help_wallets"},ln=(s,e)=>Qe(Xe(s.wallets,e.group_selection??"all",e.groups??[]),e.asset_selection??"all",e.assets??[]);function cn(s,e){let t=0,o=0;for(let n of e){let r=$(s,n.total),a=k(n.total?s.states[n.total]:void 0,"invested_amount");if(r===void 0||a===void 0)return;t+=r,o+=a}return o>0?(t-o)/o*100:void 0}function io(s){let e=s.map(o=>({room:o.room,first:o.left,second:Math.max(o.chip??0,o.value)}));if(s.length===0||de(e,dn))return"beside";let t=s.flatMap(o=>o.chip===void 0?[]:[{room:o.below??o.room,first:o.chip,second:o.value}]);return t.length===0||de(t,pn)?"row":"stacked"}function Ot(s){if(!s.some(e=>e===void 0))return Math.round(s.reduce((e,t)=>e+t,0)*1e8)/1e8}var jt="\xA0\xB7 ",dn=12,pn=8,un=30,hn=8,lo=5,Dt=class extends F{constructor(){super(...arguments);this.openGroups=new Set;this.showAll=!1;this.query="";this.cursor=void 0;this.stakeInline=!1;this.groupsLayout="beside";this.rowsLayout="beside";this.openWallets=new Set;this.window=ue("day",Date.now());this.lines=new pe(()=>this.seriesArrived(),Qs)}static{this.properties={...F.properties,openGroups:{state:!0},openWallets:{state:!0},showAll:{state:!0},query:{state:!0},cursor:{state:!0},stakeInline:{state:!0},groupsLayout:{state:!0},rowsLayout:{state:!0}}}static async getConfigForm(){let t=await Be(re());return{schema:[Oe("Bitpanda Portfolio"),X("group_content",[je(),D("show_total",!0),D("show_graph",!0),D("show_cash",!0),D("show_allocation",!0),D("show_wallets",!0)]),X("group_wallets",[D("show_search",!1),D("group_wallets",!0),Ue($t),De(lo),ae(),...Fe(t),ae(),...Ve("Wallet")]),X("group_appearance",[D("hide_amounts",!1)])],computeLabel:o=>{let n=rn[o.name];return n?h(void 0,n):qe(o)},computeHelper:o=>{let n=an[o.name];return n?h(void 0,n):Ge(o)}}}static getStubConfig(){return{timeframe:"day",sort:"value",group_selection:"all",asset_selection:"all"}}validate(t){return We(t,{...Ze,timeframe:P(B),show_total:j,show_graph:j,show_cash:j,show_allocation:j,show_wallets:j,group_wallets:j,show_search:j,sort:P($t),limit:Ie,group_selection:P(O),groups:Me,asset_selection:P(O),assets:He,hide_amounts:j})}watchedEntities(){let t=this.hass?Ye(this.hass):void 0;return t?[t.totalValue,t.cash,t.cashPlus,...Object.values(t.returns),...t.wallets.flatMap(o=>[o.available,o.total,o.staking])].filter(o=>o!==void 0):[]}willUpdate(t){super.willUpdate(t);let o=this.hass?Ye(this.hass):void 0;this.window=ue(this.timeframe,Date.now());let n=this.hass?.states[o?.returns[this.timeframe]??""]?.state??"";this.hass&&o&&this.config?.show_graph!==!1&&this.lines.request(this.hass,[ct],this.window,n)}getCardSize(){return 8}remeasures(t){return!(t.size===1&&t.has("cursor"))}fitLayout(){let t=d=>[...this.renderRoot.querySelectorAll(d)],o=(d,_)=>d.querySelector(_),n=d=>d?.getBoundingClientRect().width,r=t(".wallet .sub").map(d=>{let _=n(d.querySelector(".stake .badge"));return{room:d.clientWidth,first:o(d,".s").getBoundingClientRect().width,..._===void 0?{}:{second:_}}}),a=de(r,hn);a!==this.stakeInline&&(this.stakeInline=a);let l=t(".group").map(d=>{let _=n(d.querySelector(".gchip"));return{room:d.clientWidth,left:o(d,".gleft").getBoundingClientRect().width,..._===void 0?{}:{chip:_},value:o(d,".sum").getBoundingClientRect().width}}),i=io(l);i!==this.groupsLayout&&(this.groupsLayout=i);let c=t(".wallet .tap").map(d=>({room:d.clientWidth,below:d.clientWidth+un,left:[...o(d,".s .units").getClientRects()].reduce((_,f)=>_+f.width,0),chip:o(d,".wchip").getBoundingClientRect().width,value:o(d,".val").getBoundingClientRect().width})),u=io(c);u!==this.rowsLayout&&(this.rowsLayout=u)}groupChip(t,o){let{text:n,direction:r}=I(t,cn(t,o));if(r==="none")return p`<span class="gchip none">—</span>`;let a=ee(r);return p`<span class="gchip ${R(r)}">${a?`${a} `:""}${n}</span>`}walletsClass(){return["wallets",this.stakeInline?"stake-inline":"",this.groupsLayout==="beside"?"":"groups-wrapped",this.groupsLayout==="stacked"?"groups-stacked":"",this.rowsLayout==="beside"?"":"rows-wrapped",this.rowsLayout==="stacked"?"rows-stacked":""].filter(Boolean).join(" ")}toggle(t,o){let n=new Set(t);return n.has(o)?n.delete(o):n.add(o),n}open(t){return()=>{t&&ce(this,t)}}render(){let t=this.hass,o=this.config;if(!t||!o)return m;let n=Ye(t),r={hidden:this.amountsHidden,toggle:()=>this.toggleAmounts()},a=o.title||"Bitpanda Portfolio";if(!n)return p`<ha-card>${Ae(t,a,r)}${te(h(t,"empty_portfolio"))}</ha-card>`;let l=o.show_total!==!1||o.show_graph!==!1,i=o.show_cash!==!1||o.show_allocation!==!1,c=ln(n,o);return p`<ha-card>
      ${Ae(t,a,r)}
      <div class="content">
        ${no({host:this,hass:t,refs:n,timeframe:this.timeframe,hidden:this.amountsHidden,window:this.window,points:this.lines.series(ct),total:o.show_total!==!1,line:o.show_graph!==!1,onTimeframe:u=>{this.cursor=void 0,this.selectTimeframe(u)},cursor:this.cursor,onCursor:u=>{u!==this.cursor&&(this.cursor=u)}})}
        ${i?p`${l?p`<div class="divider"></div>`:m}
              ${o.show_cash===!1?m:this.renderCash(t,n)}
              ${o.show_allocation===!1?m:this.renderAllocation(t,n)}`:m}
        ${o.show_wallets===!1?m:p`${l||i?p`<div class="divider"></div>`:m}${o.show_search&&c.length>0?Zs(t,this.query,u=>this.query=u):m}${this.renderWallets(t,n,c,o)}`}
      </div>
    </ha-card>`}renderCash(t,o){let n=(r,a,l)=>p`<div class=${l?"end":""} role="button" tabindex="0" @click=${this.open(a)} @keydown=${T(this.open(a))}>
        <span class="k">${r}</span><span class="v">${A(N(t,a),this.amountsHidden)}</span>
      </div>`;return p`<div class="pair">${n(h(t,"cash"),o.cash,!1)}${n(h(t,"cash_plus"),o.cashPlus,!0)}</div>`}renderAllocation(t,o){let n=[];for(let i of L){let c=o.wallets.filter(u=>ao(u)===i);c.length>0&&n.push({key:i,label:kt(t,i),value:Ot(c.map(u=>$(t,u.total)))})}o.cashPlus&&n.push({key:"cash_plus",label:h(t,"cash_plus"),value:$(t,o.cashPlus)}),o.cash&&n.push({key:"cash",label:h(t,"cash"),value:$(t,o.cash)});let r=Ot(n.map(i=>i.value));if(r===void 0)return p`<div class="allocation-missing muted">—</div>`;let a=n.map(i=>({...i,share:r>0?i.value/r*100:0})).filter(i=>i.share>0).sort((i,c)=>c.share-i.share),l=i=>i<1?`<${ie(t,1,0)}`:ie(t,i,0);return p`<div class="bar" role="img" aria-label=${h(t,"opt_show_allocation")}>
        ${a.map(i=>p`<span style="width:${i.share}%;background:${ro[i.key]}"></span>`)}
      </div>
      <div class="legend">
        ${a.map(i=>p`<span><i style="background:${ro[i.key]}"></i>${i.label} ${l(i.share)}</span>`)}
      </div>`}renderWallets(t,o,n,r){if(o.wallets.length===0)return te(h(t,"empty_wallets"));if(n.length===0)return te(h(t,"empty_selection_wallets"));let a=r.sort??"value",l=r.show_search?this.query.trim():"";if(l){let i=at(t,n.filter(c=>Ys(c,l)),a);return i.length>0?p`<div class=${this.walletsClass()}>${i.map(c=>this.renderWallet(t,o,c))}</div>`:p`<div class="search-none">${h(t,"search_none",{query:l})}</div>`}if(r.group_wallets===!1){let i=at(t,n,a),c=r.limit??lo,u=c>0&&i.length>c,d=u&&!this.showAll?i.slice(0,c):i;return p`<div class=${this.walletsClass()}>${d.map(_=>this.renderWallet(t,o,_))}</div>
        ${u?p`<button class="show-all" @click=${()=>this.showAll=!this.showAll}>
              ${this.showAll?h(t,"show_less"):h(t,"show_all",{count:i.length})}
            </button>`:m}`}return p`<div class=${this.walletsClass()}>${L.map(i=>{let c=n.filter(f=>ao(f)===i);if(c.length===0)return m;let u=Ot(c.map(f=>$(t,f.total))),d=this.openGroups.has(i),_=()=>{this.openGroups=this.toggle(this.openGroups,i)};return p`<div class="group" role="button" tabindex="0" aria-expanded=${d?"true":"false"} @click=${_} @keydown=${T(_)}>
          <span class="gleft"
            >${le(d?Nt.down:Nt.right)}<span class="name">${kt(t,i)}</span
            ><span class="count">${c.length}</span></span
          >
          <span class="gright">${this.groupChip(t,c)}<span class="sum">${A(Es(t,c[0]?.total,u),this.amountsHidden)}</span></span>
        </div>
        ${d?p`<div class="members">${at(t,c,a).map(f=>this.renderWallet(t,o,f))}</div>`:m}`})}</div>`}renderWallet(t,o,n){let r=this.openWallets.has(n.deviceId);return p`${Js({hass:t,wallet:n,hidden:this.amountsHidden,onTap:this.open(n.total),chevron:{open:r,toggle:()=>{this.openWallets=this.toggle(this.openWallets,n.deviceId)}}})}${r?this.renderDetail(t,o,n):m}`}renderDetail(t,o,n){let r=this.amountsHidden,a=w=>w?t.states[w]?.attributes.unit_of_measurement:void 0,l=String(a(n.total)??a(o.totalValue)??"EUR"),i=n.total?t.states[n.total]:void 0,c=n.staking?t.states[n.staking]:void 0,u=w=>{let z=k(w?t.states[w]:void 0,"units");return z===void 0?void 0:be(t,z,n.category,n.symbol)},d=(w,z=!1)=>w===void 0?void 0:xe(t,w,l,z),_=w=>w===void 0?void 0:zs(t,w,l),f=w=>p`<span class="part">${w}</span>`,v=w=>p`${f(A(u(w),r))}${jt}${f(A(N(t,w),r))}`,y=k(i,"total_return"),g=I(t,k(i,"total_return_percent")),x=k(c,"apr_percent"),S=k(c,"rewards_net"),C=k(c,"rewards_count"),E=c?.attributes.rewards_last_at,V=typeof E=="string"&&Number.isFinite(Date.parse(E))?tt(t,Date.parse(E)):"\u2014",b=d(k(c,"rewards_net_value"));return p`<div class="detail">
      <div class="grid">
        <span>${h(t,"detail_available")}</span><span>${v(n.available)}</span>
        ${n.staking?p`<span>${h(t,"detail_staked")}</span><span>${v(n.staking)}</span>`:m}
        ${n.staking&&x!==void 0?p`<span>${h(t,"detail_staking_apr")}</span><span>${ie(t,x,1)}</span>`:m}
        <span>${h(t,"detail_average_buy_price")}</span><span>${A(_(k(i,"average_buy_price")),r)}</span>
        <span>${h(t,"detail_invested")}</span><span>${A(d(k(i,"invested_amount")),r)}</span>
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
    </div>`}worth(t,o){let[n="",r=""]=h(t,"detail_rewards_worth").split("{value}");return p`${n}${A(o,this.amountsHidden)}${r}`}};it(nn,Dt,{name:"Bitpanda Portfolio",description:()=>h(re(),"picker_portfolio"),model:["Portfolio","Wallet"]});var mn=me`
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
`,_n=6,fn=120,gn=90,ut=8,yn=78,wn=96,vn=380;function co(s){let e=Math.ceil(Math.max(0,...s.map(o=>o.price))),t=Math.ceil(Math.max(0,...s.map(o=>o.change)));return{price:e,change:Math.max(yn,t),figures:Math.max(e,t)}}function bn(s){let e=co(s);return s.every(t=>t.room-e.price-ut-e.change-ut>=fn)?"beside":s.every(t=>t.room-e.figures-ut>=gn)?"stacked":"below"}function xn(s){return de(s.map(e=>({room:e.room,first:e.pct,...e.amount===void 0?{}:{second:e.amount}})),_n)}function kn(s){let e=s?Je(ve(s)):[];return e.length>0?e:ks}var Ut=class extends F{constructor(){super(...arguments);this.showAll=!1;this.amountsInline=!1;this.rowsLayout="beside";this.columns=void 0;this.window=ue("day",Date.now());this.lines=new pe(()=>this.seriesArrived())}static{this.properties={...F.properties,currency:{state:!0},showAll:{state:!0},amountsInline:{state:!0},rowsLayout:{state:!0},columns:{state:!0}}}static{this.styles=[Ke,mn]}static async getConfigForm(){let t=re(),o=await Be(t);return{schema:[Oe("Bitpanda Price Tracker"),X("group_content",[{name:"layout",selector:ne(St,n=>h(void 0,`layout_${n}`))},je(),{name:"currency",selector:{select:{mode:"dropdown",options:kn(t).map(n=>({value:n,label:n}))}}}]),X("group_assets",[Ue(At),De(0),ae(),...Fe(o),ae(),...Ve("Price Tracker")])],computeLabel:qe,computeHelper:n=>n.name==="sort"?h(void 0,"opt_sort_help_tracker"):Ge(n)}}static getStubConfig(){return{layout:"list",timeframe:"day",currency:"EUR",sort:"name",group_selection:"all",asset_selection:"all"}}setConfig(t){super.setConfig(t),this.currency=void 0}validate(t){return We(t,{...Ze,layout:P(St),timeframe:P(B),currency:As,sort:P(At),group_selection:P(O),groups:Me,asset_selection:P(O),assets:He,limit:Ie})}watchedEntities(){return this.hass?ve(this.hass).flatMap(t=>Object.values(t.prices)):[]}shownCurrency(t){let o=Je(t),n=this.currency??this.config?.currency??"EUR";return o.includes(n)?n:o.includes("EUR")?"EUR":o[0]??"EUR"}visible(t,o){let n=ve(t),r=this.shownCurrency(n),a=Xe(n,o.group_selection??"all",o.groups??[]),i=Qe(a,o.asset_selection??"all",o.assets??[]).map(v=>{let y=v.prices[r],g=y?t.states[y]:void 0,x=y?this.lines.series(y):void 0,S=$(t,y),C=this.timeframe==="day"?k(g,"change_24h_pct"):void 0;if(C!==void 0){let V=k(g,"price_24h_ago"),b=S!==void 0&&V!==void 0?S-V:void 0;return{asset:v,entityId:y,change:C,amount:b,points:x,since:void 0}}let E=eo(x??[],S,this.window);return{asset:v,entityId:y,change:E?.change,amount:E?.amount,points:x,since:E?.since}}),c=o.sort??"name",u=(v,y)=>v.asset.name.localeCompare(y.asset.name,W(t));if(c==="name"||c==="selection"&&o.asset_selection!=="only")i.sort(u);else if(c==="change_desc"||c==="change_asc"){let v=c==="change_desc"?-1:1;i.sort((y,g)=>y.change===void 0||g.change===void 0?y.change===void 0?g.change===void 0?u(y,g):1:-1:v*(y.change-g.change)||u(y,g))}let d=o.limit??0,_=d>0&&i.length>d;return{rows:_&&!this.showAll?i.slice(0,d):i,ranked:i,total:i.length,folds:_,currency:r,currencies:Je(n)}}willUpdate(t){if(super.willUpdate(t),this.window=ue(this.timeframe,Date.now()),!this.hass||!this.config)return;let{rows:o,ranked:n}=this.visible(this.hass,this.config),r=this.config.sort??"name",l=(this.timeframe!=="day"&&(r==="change_desc"||r==="change_asc")?n:o).map(i=>i.entityId).filter(i=>i!==void 0);this.lines.request(this.hass,l,this.window)}fitLayout(){let t=i=>i?.getBoundingClientRect().width,o=[...this.shadowRoot?.querySelectorAll(".tile .c")??[]].map(i=>{let c=t(i.querySelector(".a"));return{room:i.clientWidth,pct:t(i.querySelector(".pct"))??0,...c===void 0?{}:{amount:c}}}),n=xn(o);n!==this.amountsInline&&(this.amountsInline=n);let r=this.clientWidth>vn?wn+ut:0,a=[...this.renderRoot.querySelectorAll(".price-row")].map(i=>{let c=u=>i.querySelector(u).getBoundingClientRect().width;return{room:i.clientWidth-r,price:c(".p"),change:Math.max(c(".c .pct"),t(i.querySelector(".c .a"))??0)}}),l=bn(a);if(l!==this.rowsLayout&&(this.rowsLayout=l),a.length>0){let i=co(a),c=this.columns;(!c||c.price!==i.price||c.change!==i.change||c.figures!==i.figures)&&(this.columns=i)}}getCardSize(){return 6}open(t){return()=>{t&&ce(this,t)}}line(t,o){let n=t.since===void 0?this.window:{...this.window,start:t.since};return t.points&&t.points.length>0?dt(t.points,n,{width:96,height:28,fill:!1,className:`mini ${o}`,stepMs:Xs(n)}):p`<span class="mini"></span>`}change(t,o){let{text:n,direction:r}=I(t,o.change),a=ee(r),l=R(r),i=r==="none"?void 0:Ns(t,o.entityId,o.amount);return{cell:p`<div class="pct pchip ${r==="none"?"none":""}">${r==="none"?"\u2014":`${a?`${a} `:""}${n}`}</div>${i?p`<div class="a">${i}</div>`:m}`,className:l,lineClass:l||"flat"}}since(t,o){return o.since===void 0?m:p`<div class="since">${h(t,"change_since",{date:ke(t,o.since)})}</div>`}renderList(t,o){let n=this.columns,r=n?`--bp-price:${n.price}px;--bp-change:${n.change}px;--bp-figures:${n.figures}px`:"";return p`<div class="rows ${this.rowsLayout==="beside"?"":this.rowsLayout}" style=${r}>
      ${o.map(a=>{let l=this.change(t,a);return p`<div class="price-row" role="button" tabindex="0" @click=${this.open(a.entityId)} @keydown=${T(this.open(a.entityId))}>
          <div class="lead"><div class="n" title=${a.asset.shortName}>${a.asset.shortName}</div><div class="s">${a.asset.isin??a.asset.symbol}</div>${this.since(t,a)}</div>
          ${this.line(a,l.lineClass)}
          <div class="p">${N(t,a.entityId)??"\u2014"}</div>
          <div class="c ${l.className}">${l.cell}</div>
        </div>`})}
    </div>`}renderTiles(t,o){return p`<div class="tiles ${this.amountsInline?"inline":""}">
      ${o.map(n=>{let r=this.change(t,n);return p`<div class="tile" role="button" tabindex="0" @click=${this.open(n.entityId)} @keydown=${T(this.open(n.entityId))}>
          <div class="n" title=${n.asset.shortName}>${n.asset.shortName}</div>
          <div class="s">${n.asset.isin??n.asset.symbol}</div>
          <div class="p">${N(t,n.entityId)??"\u2014"}</div>
          <div class="c ${r.className}">${r.cell}</div>
          ${this.line(n,r.lineClass)}${this.since(t,n)}
        </div>`})}
    </div>`}footer(t,o,n){if(n==="EUR")return m;let r=o.map(a=>a.entityId?t.states[a.entityId]?.attributes.rate_date:void 0).map(a=>typeof a=="string"?Ms(t,a):void 0).find(a=>a!==void 0);return r?p`<div class="foot">${h(t,"ecb_footer",{currency:n,date:r})}</div>`:m}render(){let t=this.hass,o=this.config;if(!t||!o)return m;let n=Ae(t,o.title||"Bitpanda Price Tracker");if(ve(t).length===0)return p`<ha-card>${n}${te(h(t,"empty_price_tracker"))}</ha-card>`;let{rows:r,total:a,folds:l,currency:i,currencies:c}=this.visible(t,o);return p`<ha-card>
      ${n}
      <div class="content">
        <div class="switches">
          ${rt(t,this.timeframe,u=>this.selectTimeframe(u))}
          ${Ks(t,c,i,u=>this.currency=u)}
        </div>
        ${r.length===0?te(h(t,"empty_selection_assets")):o.layout==="tiles"?this.renderTiles(t,r):this.renderList(t,r)}
        ${l?p`<button class="show-all" @click=${()=>this.showAll=!this.showAll}>
              ${this.showAll?h(t,"show_less"):h(t,"show_all",{count:a})}
            </button>`:m}
      </div>
      ${this.footer(t,r,i)}
    </ha-card>`}};it("bitpanda-price-tracker-card",Ut,{name:"Bitpanda Price Tracker",description:()=>h(re(),"picker_price_tracker"),model:"Price Tracker"});
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
