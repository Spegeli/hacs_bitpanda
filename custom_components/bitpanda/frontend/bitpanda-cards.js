var Se=globalThis,Ce=Se.ShadowRoot&&(Se.ShadyCSS===void 0||Se.ShadyCSS.nativeShadow)&&"adoptedStyleSheets"in Document.prototype&&"replace"in CSSStyleSheet.prototype,mt=Symbol(),Xt=new WeakMap,pe=class{constructor(t,e,o){if(this._$cssResult$=!0,o!==mt)throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");this.cssText=t,this.t=e}get styleSheet(){let t=this.o,e=this.t;if(Ce&&t===void 0){let o=e!==void 0&&e.length===1;o&&(t=Xt.get(e)),t===void 0&&((this.o=t=new CSSStyleSheet).replaceSync(this.cssText),o&&Xt.set(e,t))}return t}toString(){return this.cssText}},Qt=s=>new pe(typeof s=="string"?s:s+"",void 0,mt),ue=(s,...t)=>{let e=s.length===1?s[0]:t.reduce((o,n,r)=>o+(i=>{if(i._$cssResult$===!0)return i.cssText;if(typeof i=="number")return i;throw Error("Value passed to 'css' function must be a 'css' function result: "+i+". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.")})(n)+s[r+1],s[0]);return new pe(e,s,mt)},es=(s,t)=>{if(Ce)s.adoptedStyleSheets=t.map(e=>e instanceof CSSStyleSheet?e:e.styleSheet);else for(let e of t){let o=document.createElement("style"),n=Se.litNonce;n!==void 0&&o.setAttribute("nonce",n),o.textContent=e.cssText,s.appendChild(o)}},_t=Ce?s=>s:s=>s instanceof CSSStyleSheet?(t=>{let e="";for(let o of t.cssRules)e+=o.cssText;return Qt(e)})(s):s;var{is:vo,defineProperty:bo,getOwnPropertyDescriptor:xo,getOwnPropertyNames:ko,getOwnPropertySymbols:$o,getPrototypeOf:Ao}=Object,Te=globalThis,ts=Te.trustedTypes,So=ts?ts.emptyScript:"",Co=Te.reactiveElementPolyfillSupport,he=(s,t)=>s,ft={toAttribute(s,t){switch(t){case Boolean:s=s?So:null;break;case Object:case Array:s=s==null?s:JSON.stringify(s)}return s},fromAttribute(s,t){let e=s;switch(t){case Boolean:e=s!==null;break;case Number:e=s===null?null:Number(s);break;case Object:case Array:try{e=JSON.parse(s)}catch{e=null}}return e}},os=(s,t)=>!vo(s,t),ss={attribute:!0,type:String,converter:ft,reflect:!1,useDefault:!1,hasChanged:os};Symbol.metadata??=Symbol("metadata"),Te.litPropertyMetadata??=new WeakMap;var N=class extends HTMLElement{static addInitializer(t){this._$Ei(),(this.l??=[]).push(t)}static get observedAttributes(){return this.finalize(),this._$Eh&&[...this._$Eh.keys()]}static createProperty(t,e=ss){if(e.state&&(e.attribute=!1),this._$Ei(),this.prototype.hasOwnProperty(t)&&((e=Object.create(e)).wrapped=!0),this.elementProperties.set(t,e),!e.noAccessor){let o=Symbol(),n=this.getPropertyDescriptor(t,o,e);n!==void 0&&bo(this.prototype,t,n)}}static getPropertyDescriptor(t,e,o){let{get:n,set:r}=xo(this.prototype,t)??{get(){return this[e]},set(i){this[e]=i}};return{get:n,set(i){let l=n?.call(this);r?.call(this,i),this.requestUpdate(t,l,o)},configurable:!0,enumerable:!0}}static getPropertyOptions(t){return this.elementProperties.get(t)??ss}static _$Ei(){if(this.hasOwnProperty(he("elementProperties")))return;let t=Ao(this);t.finalize(),t.l!==void 0&&(this.l=[...t.l]),this.elementProperties=new Map(t.elementProperties)}static finalize(){if(this.hasOwnProperty(he("finalized")))return;if(this.finalized=!0,this._$Ei(),this.hasOwnProperty(he("properties"))){let e=this.properties,o=[...ko(e),...$o(e)];for(let n of o)this.createProperty(n,e[n])}let t=this[Symbol.metadata];if(t!==null){let e=litPropertyMetadata.get(t);if(e!==void 0)for(let[o,n]of e)this.elementProperties.set(o,n)}this._$Eh=new Map;for(let[e,o]of this.elementProperties){let n=this._$Eu(e,o);n!==void 0&&this._$Eh.set(n,e)}this.elementStyles=this.finalizeStyles(this.styles)}static finalizeStyles(t){let e=[];if(Array.isArray(t)){let o=new Set(t.flat(1/0).reverse());for(let n of o)e.unshift(_t(n))}else t!==void 0&&e.push(_t(t));return e}static _$Eu(t,e){let o=e.attribute;return o===!1?void 0:typeof o=="string"?o:typeof t=="string"?t.toLowerCase():void 0}constructor(){super(),this._$Ep=void 0,this.isUpdatePending=!1,this.hasUpdated=!1,this._$Em=null,this._$Ev()}_$Ev(){this._$ES=new Promise(t=>this.enableUpdating=t),this._$AL=new Map,this._$E_(),this.requestUpdate(),this.constructor.l?.forEach(t=>t(this))}addController(t){(this._$EO??=new Set).add(t),this.renderRoot!==void 0&&this.isConnected&&t.hostConnected?.()}removeController(t){this._$EO?.delete(t)}_$E_(){let t=new Map,e=this.constructor.elementProperties;for(let o of e.keys())this.hasOwnProperty(o)&&(t.set(o,this[o]),delete this[o]);t.size>0&&(this._$Ep=t)}createRenderRoot(){let t=this.shadowRoot??this.attachShadow(this.constructor.shadowRootOptions);return es(t,this.constructor.elementStyles),t}connectedCallback(){this.renderRoot??=this.createRenderRoot(),this.enableUpdating(!0),this._$EO?.forEach(t=>t.hostConnected?.())}enableUpdating(t){}disconnectedCallback(){this._$EO?.forEach(t=>t.hostDisconnected?.())}attributeChangedCallback(t,e,o){this._$AK(t,o)}_$ET(t,e){let o=this.constructor.elementProperties.get(t),n=this.constructor._$Eu(t,o);if(n!==void 0&&o.reflect===!0){let r=(o.converter?.toAttribute!==void 0?o.converter:ft).toAttribute(e,o.type);this._$Em=t,r==null?this.removeAttribute(n):this.setAttribute(n,r),this._$Em=null}}_$AK(t,e){let o=this.constructor,n=o._$Eh.get(t);if(n!==void 0&&this._$Em!==n){let r=o.getPropertyOptions(n),i=typeof r.converter=="function"?{fromAttribute:r.converter}:r.converter?.fromAttribute!==void 0?r.converter:ft;this._$Em=n;let l=i.fromAttribute(e,r.type);this[n]=l??this._$Ej?.get(n)??l,this._$Em=null}}requestUpdate(t,e,o,n=!1,r){if(t!==void 0){let i=this.constructor;if(n===!1&&(r=this[t]),o??=i.getPropertyOptions(t),!((o.hasChanged??os)(r,e)||o.useDefault&&o.reflect&&r===this._$Ej?.get(t)&&!this.hasAttribute(i._$Eu(t,o))))return;this.C(t,e,o)}this.isUpdatePending===!1&&(this._$ES=this._$EP())}C(t,e,{useDefault:o,reflect:n,wrapped:r},i){o&&!(this._$Ej??=new Map).has(t)&&(this._$Ej.set(t,i??e??this[t]),r!==!0||i!==void 0)||(this._$AL.has(t)||(this.hasUpdated||o||(e=void 0),this._$AL.set(t,e)),n===!0&&this._$Em!==t&&(this._$Eq??=new Set).add(t))}async _$EP(){this.isUpdatePending=!0;try{await this._$ES}catch(e){Promise.reject(e)}let t=this.scheduleUpdate();return t!=null&&await t,!this.isUpdatePending}scheduleUpdate(){return this.performUpdate()}performUpdate(){if(!this.isUpdatePending)return;if(!this.hasUpdated){if(this.renderRoot??=this.createRenderRoot(),this._$Ep){for(let[n,r]of this._$Ep)this[n]=r;this._$Ep=void 0}let o=this.constructor.elementProperties;if(o.size>0)for(let[n,r]of o){let{wrapped:i}=r,l=this[n];i!==!0||this._$AL.has(n)||l===void 0||this.C(n,void 0,r,l)}}let t=!1,e=this._$AL;try{t=this.shouldUpdate(e),t?(this.willUpdate(e),this._$EO?.forEach(o=>o.hostUpdate?.()),this.update(e)):this._$EM()}catch(o){throw t=!1,this._$EM(),o}t&&this._$AE(e)}willUpdate(t){}_$AE(t){this._$EO?.forEach(e=>e.hostUpdated?.()),this.hasUpdated||(this.hasUpdated=!0,this.firstUpdated(t)),this.updated(t)}_$EM(){this._$AL=new Map,this.isUpdatePending=!1}get updateComplete(){return this.getUpdateComplete()}getUpdateComplete(){return this._$ES}shouldUpdate(t){return!0}update(t){this._$Eq&&=this._$Eq.forEach(e=>this._$ET(e,this[e])),this._$EM()}updated(t){}firstUpdated(t){}};N.elementStyles=[],N.shadowRootOptions={mode:"open"},N[he("elementProperties")]=new Map,N[he("finalized")]=new Map,Co?.({ReactiveElement:N}),(Te.reactiveElementVersions??=[]).push("2.1.2");var yt=globalThis,ns=s=>s,Pe=yt.trustedTypes,rs=Pe?Pe.createPolicy("lit-html",{createHTML:s=>s}):void 0,wt="$lit$",M=`lit$${Math.random().toFixed(9).slice(2)}$`,vt="?"+M,To=`<${vt}>`,q=document,_e=()=>q.createComment(""),fe=s=>s===null||typeof s!="object"&&typeof s!="function",bt=Array.isArray,ps=s=>bt(s)||typeof s?.[Symbol.iterator]=="function",gt=`[ 	
\f\r]`,me=/<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g,is=/-->/g,as=/>/g,F=RegExp(`>|${gt}(?:([^\\s"'>=/]+)(${gt}*=${gt}*(?:[^ 	
\f\r"'\`<>=]|("|')|))|$)`,"g"),ls=/'/g,cs=/"/g,us=/^(?:script|style|textarea|title)$/i,xt=s=>(t,...e)=>({_$litType$:s,strings:t,values:e}),d=xt(1),te=xt(2),Fn=xt(3),G=Symbol.for("lit-noChange"),m=Symbol.for("lit-nothing"),ds=new WeakMap,V=q.createTreeWalker(q,129);function hs(s,t){if(!bt(s)||!s.hasOwnProperty("raw"))throw Error("invalid template strings array");return rs!==void 0?rs.createHTML(t):t}var ms=(s,t)=>{let e=s.length-1,o=[],n,r=t===2?"<svg>":t===3?"<math>":"",i=me;for(let l=0;l<e;l++){let a=s[l],c,h,p=-1,_=0;for(;_<a.length&&(i.lastIndex=_,h=i.exec(a),h!==null);)_=i.lastIndex,i===me?h[1]==="!--"?i=is:h[1]!==void 0?i=as:h[2]!==void 0?(us.test(h[2])&&(n=RegExp("</"+h[2],"g")),i=F):h[3]!==void 0&&(i=F):i===F?h[0]===">"?(i=n??me,p=-1):h[1]===void 0?p=-2:(p=i.lastIndex-h[2].length,c=h[1],i=h[3]===void 0?F:h[3]==='"'?cs:ls):i===cs||i===ls?i=F:i===is||i===as?i=me:(i=F,n=void 0);let f=i===F&&s[l+1].startsWith("/>")?" ":"";r+=i===me?a+To:p>=0?(o.push(c),a.slice(0,p)+wt+a.slice(p)+M+f):a+M+(p===-2?l:f)}return[hs(s,r+(s[e]||"<?>")+(t===2?"</svg>":t===3?"</math>":"")),o]},ge=class s{constructor({strings:t,_$litType$:e},o){let n;this.parts=[];let r=0,i=0,l=t.length-1,a=this.parts,[c,h]=ms(t,e);if(this.el=s.createElement(c,o),V.currentNode=this.el.content,e===2||e===3){let p=this.el.content.firstChild;p.replaceWith(...p.childNodes)}for(;(n=V.nextNode())!==null&&a.length<l;){if(n.nodeType===1){if(n.hasAttributes())for(let p of n.getAttributeNames())if(p.endsWith(wt)){let _=h[i++],f=n.getAttribute(p).split(M),v=/([.?@])?(.*)/.exec(_);a.push({type:1,index:r,name:v[2],strings:f,ctor:v[1]==="."?Re:v[1]==="?"?ze:v[1]==="@"?Le:Z}),n.removeAttribute(p)}else p.startsWith(M)&&(a.push({type:6,index:r}),n.removeAttribute(p));if(us.test(n.tagName)){let p=n.textContent.split(M),_=p.length-1;if(_>0){n.textContent=Pe?Pe.emptyScript:"";for(let f=0;f<_;f++)n.append(p[f],_e()),V.nextNode(),a.push({type:2,index:++r});n.append(p[_],_e())}}}else if(n.nodeType===8)if(n.data===vt)a.push({type:2,index:r});else{let p=-1;for(;(p=n.data.indexOf(M,p+1))!==-1;)a.push({type:7,index:r}),p+=M.length-1}r++}}static createElement(t,e){let o=q.createElement("template");return o.innerHTML=t,o}};function K(s,t,e=s,o){if(t===G)return t;let n=o!==void 0?e._$Co?.[o]:e._$Cl,r=fe(t)?void 0:t._$litDirective$;return n?.constructor!==r&&(n?._$AO?.(!1),r===void 0?n=void 0:(n=new r(s),n._$AT(s,e,o)),o!==void 0?(e._$Co??=[])[o]=n:e._$Cl=n),n!==void 0&&(t=K(s,n._$AS(s,t.values),n,o)),t}var Ee=class{constructor(t,e){this._$AV=[],this._$AN=void 0,this._$AD=t,this._$AM=e}get parentNode(){return this._$AM.parentNode}get _$AU(){return this._$AM._$AU}u(t){let{el:{content:e},parts:o}=this._$AD,n=(t?.creationScope??q).importNode(e,!0);V.currentNode=n;let r=V.nextNode(),i=0,l=0,a=o[0];for(;a!==void 0;){if(i===a.index){let c;a.type===2?c=new ee(r,r.nextSibling,this,t):a.type===1?c=new a.ctor(r,a.name,a.strings,this,t):a.type===6&&(c=new Ie(r,this,t)),this._$AV.push(c),a=o[++l]}i!==a?.index&&(r=V.nextNode(),i++)}return V.currentNode=q,n}p(t){let e=0;for(let o of this._$AV)o!==void 0&&(o.strings!==void 0?(o._$AI(t,o,e),e+=o.strings.length-2):o._$AI(t[e])),e++}},ee=class s{get _$AU(){return this._$AM?._$AU??this._$Cv}constructor(t,e,o,n){this.type=2,this._$AH=m,this._$AN=void 0,this._$AA=t,this._$AB=e,this._$AM=o,this.options=n,this._$Cv=n?.isConnected??!0}get parentNode(){let t=this._$AA.parentNode,e=this._$AM;return e!==void 0&&t?.nodeType===11&&(t=e.parentNode),t}get startNode(){return this._$AA}get endNode(){return this._$AB}_$AI(t,e=this){t=K(this,t,e),fe(t)?t===m||t==null||t===""?(this._$AH!==m&&this._$AR(),this._$AH=m):t!==this._$AH&&t!==G&&this._(t):t._$litType$!==void 0?this.$(t):t.nodeType!==void 0?this.T(t):ps(t)?this.k(t):this._(t)}O(t){return this._$AA.parentNode.insertBefore(t,this._$AB)}T(t){this._$AH!==t&&(this._$AR(),this._$AH=this.O(t))}_(t){this._$AH!==m&&fe(this._$AH)?this._$AA.nextSibling.data=t:this.T(q.createTextNode(t)),this._$AH=t}$(t){let{values:e,_$litType$:o}=t,n=typeof o=="number"?this._$AC(t):(o.el===void 0&&(o.el=ge.createElement(hs(o.h,o.h[0]),this.options)),o);if(this._$AH?._$AD===n)this._$AH.p(e);else{let r=new Ee(n,this),i=r.u(this.options);r.p(e),this.T(i),this._$AH=r}}_$AC(t){let e=ds.get(t.strings);return e===void 0&&ds.set(t.strings,e=new ge(t)),e}k(t){bt(this._$AH)||(this._$AH=[],this._$AR());let e=this._$AH,o,n=0;for(let r of t)n===e.length?e.push(o=new s(this.O(_e()),this.O(_e()),this,this.options)):o=e[n],o._$AI(r),n++;n<e.length&&(this._$AR(o&&o._$AB.nextSibling,n),e.length=n)}_$AR(t=this._$AA.nextSibling,e){for(this._$AP?.(!1,!0,e);t!==this._$AB;){let o=ns(t).nextSibling;ns(t).remove(),t=o}}setConnected(t){this._$AM===void 0&&(this._$Cv=t,this._$AP?.(t))}},Z=class{get tagName(){return this.element.tagName}get _$AU(){return this._$AM._$AU}constructor(t,e,o,n,r){this.type=1,this._$AH=m,this._$AN=void 0,this.element=t,this.name=e,this._$AM=n,this.options=r,o.length>2||o[0]!==""||o[1]!==""?(this._$AH=Array(o.length-1).fill(new String),this.strings=o):this._$AH=m}_$AI(t,e=this,o,n){let r=this.strings,i=!1;if(r===void 0)t=K(this,t,e,0),i=!fe(t)||t!==this._$AH&&t!==G,i&&(this._$AH=t);else{let l=t,a,c;for(t=r[0],a=0;a<r.length-1;a++)c=K(this,l[o+a],e,a),c===G&&(c=this._$AH[a]),i||=!fe(c)||c!==this._$AH[a],c===m?t=m:t!==m&&(t+=(c??"")+r[a+1]),this._$AH[a]=c}i&&!n&&this.j(t)}j(t){t===m?this.element.removeAttribute(this.name):this.element.setAttribute(this.name,t??"")}},Re=class extends Z{constructor(){super(...arguments),this.type=3}j(t){this.element[this.name]=t===m?void 0:t}},ze=class extends Z{constructor(){super(...arguments),this.type=4}j(t){this.element.toggleAttribute(this.name,!!t&&t!==m)}},Le=class extends Z{constructor(t,e,o,n,r){super(t,e,o,n,r),this.type=5}_$AI(t,e=this){if((t=K(this,t,e,0)??m)===G)return;let o=this._$AH,n=t===m&&o!==m||t.capture!==o.capture||t.once!==o.once||t.passive!==o.passive,r=t!==m&&(o===m||n);n&&this.element.removeEventListener(this.name,this,o),r&&this.element.addEventListener(this.name,this,t),this._$AH=t}handleEvent(t){typeof this._$AH=="function"?this._$AH.call(this.options?.host??this.element,t):this._$AH.handleEvent(t)}},Ie=class{constructor(t,e,o){this.element=t,this.type=6,this._$AN=void 0,this._$AM=e,this.options=o}get _$AU(){return this._$AM._$AU}_$AI(t){K(this,t)}},_s={M:wt,P:M,A:vt,C:1,L:ms,R:Ee,D:ps,V:K,I:ee,H:Z,N:ze,U:Le,B:Re,F:Ie},Po=yt.litHtmlPolyfillSupport;Po?.(ge,ee),(yt.litHtmlVersions??=[]).push("3.3.3");var fs=(s,t,e)=>{let o=e?.renderBefore??t,n=o._$litPart$;if(n===void 0){let r=e?.renderBefore??null;o._$litPart$=n=new ee(t.insertBefore(_e(),r),r,void 0,e??{})}return n._$AI(s),n};var kt=globalThis,z=class extends N{constructor(){super(...arguments),this.renderOptions={host:this},this._$Do=void 0}createRenderRoot(){let t=super.createRenderRoot();return this.renderOptions.renderBefore??=t.firstChild,t}update(t){let e=this.render();this.hasUpdated||(this.renderOptions.isConnected=this.isConnected),super.update(t),this._$Do=fs(e,this.renderRoot,this.renderOptions)}connectedCallback(){super.connectedCallback(),this._$Do?.setConnected(!0)}disconnectedCallback(){super.disconnectedCallback(),this._$Do?.setConnected(!1)}render(){return G}};z._$litElement$=!0,z.finalized=!0,kt.litElementHydrateSupport?.({LitElement:z});var Eo=kt.litElementPolyfillSupport;Eo?.({LitElement:z});(kt.litElementVersions??=[]).push("4.2.2");var gs={tf_day:"1T",tf_week:"1W",tf_month:"1M",tf_six_month:"6M",tf_year:"1J",aria_timeframe:"Zeitraum",aria_currency:"W\xE4hrung",search_placeholder:"Name, Symbol oder ISIN",search_none:"Kein Wallet passt zu \u201E{query}\u201C.",aria_search:"Wallets durchsuchen",aria_search_clear:"Suche leeren",return_day:"Rendite \xFCber 1 Tag",return_week:"Rendite \xFCber 1 Woche",return_month:"Rendite \xFCber 1 Monat",return_six_month:"Rendite \xFCber 6 Monate",return_year:"Rendite \xFCber 1 Jahr",value_line:"Gesamtwert, {start} \u2013 heute",value_line_day:"Gesamtwert, letzte 24 Stunden",cash:"Bargeld",cash_plus:"Cash Plus",staked:"{share} im Staking",show_all:"Alle anzeigen ({count})",show_less:"Weniger anzeigen",detail_available:"Verf\xFCgbar",detail_staked:"Im Staking",detail_staking_apr:"Staking-APR",detail_average_buy_price:"\xD8 Kaufpreis",detail_invested:"Investiert",detail_profit_loss:"Gewinn / Verlust",detail_rewards:"Staking-Belohnungen",detail_rewards_net:"Netto, gesamt",detail_rewards_worth:"heute {value} wert",detail_payouts:"Gutschriften",detail_payouts_value:"{count} \xB7 zuletzt {date}",shares_one:"St\xFCck",shares_other:"St\xFCck",assets_missing_one:"Dazu geh\xF6rt ein gew\xE4hltes Asset, das es gerade nicht gibt. Es bleibt gespeichert und gilt wieder, sobald es wieder da ist.",assets_missing_other:"Dazu geh\xF6ren {count} gew\xE4hlte Assets, die es gerade nicht gibt. Sie bleiben gespeichert und gelten wieder, sobald sie wieder da sind.",eye_hide:"Betr\xE4ge verbergen",eye_show:"Betr\xE4ge anzeigen",change_since:"\xC4nderung seit {date}",ecb_footer:"Preise in {currency}: Bitpandas Euro-Preise, umgerechnet zum EZB-Referenzkurs vom {date}. Ihre \xC4nderung enth\xE4lt die Bewegung des Kurses.",empty_portfolio:"Richte das Bitpanda Portfolio ein, dann erscheint es hier.",empty_wallets:"Noch keine Wallets.",empty_selection_wallets:"Keine Wallets in der Auswahl dieser Karte.",empty_selection_assets:"Keine Assets in der Auswahl dieser Karte.",empty_price_tracker:"Richte den Bitpanda Price Tracker ein und f\xFCge Assets hinzu, dann erscheinen hier Preise.",picker_portfolio:"Gesamtwert und Rendite mit Verlauf, Bargeld und Cash Plus, Verteilung und deine Wallets; jeder Teil l\xE4sst sich ausblenden.",picker_price_tracker:"Preise und \xC4nderungen deiner verfolgten Assets, je mit Verlauf, als Liste oder Kacheln.",invalid_option:"Ung\xFCltiger Wert f\xFCr \u201E{option}\u201C: {value}. Erlaubt: {allowed}.",allowed_text:"Text",allowed_assets:"eine Liste von Asset-IDs oder Ger\xE4te-IDs",allowed_groups:"eine Liste aus {values}",group_content:"Inhalt",group_wallets:"Wallets",group_assets:"Assets",group_appearance:"Darstellung",opt_title:"Titel",opt_title_help:"Leer lassen f\xFCr den grau angezeigten Namen",opt_timeframe:"Standard-Zeitraum",opt_timeframe_help:"Die Tasten 1T bis 1J auf der Karte wechseln ihn nur vor\xFCbergehend",tfo_day:"1 Tag",tfo_week:"1 Woche",tfo_month:"1 Monat",tfo_six_month:"6 Monate",tfo_year:"1 Jahr",opt_show_cash:"Bargeld und Cash Plus",opt_show_allocation:"Verteilung",opt_show_allocation_help:"Der farbige Balken mit den Anteilen der Asset-Gruppen und des Bargelds",opt_show_total:"Gesamtwert und Rendite",opt_show_total_help:"Die Zeitraum-Tasten bleiben, solange der Verlauf gezeigt wird",opt_show_line:"Verlauf des Gesamtwerts",opt_show_wallets:"Wallets",opt_group_wallets:"Wallets in Asset-Gruppen",opt_show_search:"Suchfeld",opt_show_search_help:"Findet Wallets nach Name, Symbol oder ISIN",opt_sort:"Sortieren nach",sort_value:"Wert",sort_return:"Rendite seit Kauf",sort_name:"Name",sort_selection:"Reihenfolge wie gew\xE4hlt",sort_change_desc:"\xC4nderung, h\xF6chste zuerst",sort_change_asc:"\xC4nderung, niedrigste zuerst",opt_sort_help_tracker:"\u201EReihenfolge wie gew\xE4hlt\u201C gilt nur mit \u201ENur die gew\xE4hlten\u201C Assets, sonst nach Name",opt_group_selection:"Angezeigte Asset-Gruppen",opt_group_selection_help:"Gilt nur f\xFCr die Wallets; Gesamtwert, Bargeld, Cash Plus und Verteilung zeigen immer das ganze Portfolio",opt_groups:"Asset-Gruppen w\xE4hlen",opt_asset_selection:"Angezeigte Assets",opt_asset_selection_wallets:"Angezeigte Wallets",sel_all:"Alle",sel_all_except:"Alle au\xDFer den gew\xE4hlten",sel_only:"Nur die gew\xE4hlten",opt_assets:"Assets w\xE4hlen",opt_assets_wallets:"Wallets w\xE4hlen",opt_assets_help:"Ein Asset aus einer ausgeblendeten Asset-Gruppe bleibt verborgen, auch wenn es hier gew\xE4hlt ist",opt_assets_help_wallets:"Ein Wallet aus einer ausgeblendeten Asset-Gruppe bleibt verborgen, auch wenn es hier gew\xE4hlt ist",opt_hide_amounts:"Betr\xE4ge zun\xE4chst verbergen",opt_hide_amounts_help:"Prozente bleiben sichtbar; das Auge oben auf der Karte zeigt die Betr\xE4ge nur vor\xFCbergehend",opt_limit:"Assets vor \u201EAlle anzeigen\u201C",opt_limit_wallets:"Wallets vor \u201EAlle anzeigen\u201C",opt_limit_help:"0 zeigt alle Assets",opt_limit_help_wallets:"Nur wenn \u201EWallets in Asset-Gruppen\u201C aus ist; 0 zeigt alle",opt_layout:"Anzeigen als",layout_list:"Liste",layout_tiles:"Kacheln",opt_currency:"Standard-W\xE4hrung",opt_currency_help:"Die Tasten auf der Karte wechseln sie nur vor\xFCbergehend; weitere W\xE4hrungen \xFCber \u201EKonfigurieren\u201C beim Price Tracker"};var ys={tf_day:"1D",tf_week:"1W",tf_month:"1M",tf_six_month:"6M",tf_year:"1Y",aria_timeframe:"Timeframe",aria_currency:"Currency",search_placeholder:"Name, symbol or ISIN",search_none:"No wallet matches \u201C{query}\u201D.",aria_search:"Search wallets",aria_search_clear:"Clear search",return_day:"return over 1 day",return_week:"return over 1 week",return_month:"return over 1 month",return_six_month:"return over 6 months",return_year:"return over 1 year",value_line:"Total value, {start} \u2013 today",value_line_day:"Total value, last 24 hours",cash:"Cash",cash_plus:"Cash Plus",staked:"{share} staked",show_all:"Show all ({count})",show_less:"Show less",detail_available:"Available",detail_staked:"Staked",detail_staking_apr:"Staking APR",detail_average_buy_price:"Average buy price",detail_invested:"Invested",detail_profit_loss:"Profit / loss",detail_rewards:"Staking rewards",detail_rewards_net:"Net, all time",detail_rewards_worth:"worth {value} today",detail_payouts:"Payouts",detail_payouts_value:"{count} \xB7 last {date}",shares_one:"share",shares_other:"shares",assets_missing_one:"This includes a chosen asset that is not there right now. It stays saved and applies again once it is back.",assets_missing_other:"This includes {count} chosen assets that are not there right now. They stay saved and apply again once they are back.",eye_hide:"Hide amounts",eye_show:"Show amounts",change_since:"Change since {date}",ecb_footer:"Prices in {currency}: Bitpanda's EUR prices converted at the ECB reference rate of {date}. Their change includes the rate's move.",empty_portfolio:"Set up the Bitpanda Portfolio to see it here.",empty_wallets:"No wallets yet.",empty_selection_wallets:"No wallets in this card's selection.",empty_selection_assets:"No assets in this card's selection.",empty_price_tracker:"Set up the Bitpanda Price Tracker and add assets to it to see prices here.",picker_portfolio:"Total value and return with a value line, Cash and Cash Plus, allocation and your wallets; each part can be left out.",picker_price_tracker:"Prices and changes of the assets you track, each with a line, as a list or tiles.",invalid_option:"Invalid value for \u201C{option}\u201D: {value}. Allowed: {allowed}.",allowed_text:"text",allowed_assets:"a list of asset IDs or device IDs",allowed_groups:"a list of {values}",group_content:"Content",group_wallets:"Wallets",group_assets:"Assets",group_appearance:"Appearance",opt_title:"Title",opt_title_help:"Leave empty for the name shown in grey",opt_timeframe:"Default timeframe",opt_timeframe_help:"The 1D to 1Y buttons on the card change it only temporarily",tfo_day:"1 day",tfo_week:"1 week",tfo_month:"1 month",tfo_six_month:"6 months",tfo_year:"1 year",opt_show_cash:"Cash and Cash Plus",opt_show_allocation:"Allocation bar",opt_show_allocation_help:"The coloured bar showing the share of each asset group and of cash",opt_show_total:"Total value and return",opt_show_total_help:"The timeframe buttons stay while the line is shown",opt_show_line:"Total value line",opt_show_wallets:"Wallets",opt_group_wallets:"Wallets in asset groups",opt_show_search:"Search field",opt_show_search_help:"Finds wallets by name, symbol or ISIN",opt_sort:"Sort by",sort_value:"Value",sort_return:"Return since purchase",sort_name:"Name",sort_selection:"Order as chosen",sort_change_desc:"Change, highest first",sort_change_asc:"Change, lowest first",opt_sort_help_tracker:"\u201COrder as chosen\u201D applies only when assets are set to \u201COnly the ones chosen\u201D; otherwise by name",opt_group_selection:"Asset groups shown",opt_group_selection_help:"Applies to the wallets only; total value, Cash, Cash Plus and allocation always show the whole portfolio",opt_groups:"Choose asset groups",opt_asset_selection:"Assets shown",opt_asset_selection_wallets:"Wallets shown",sel_all:"All",sel_all_except:"All except the ones chosen",sel_only:"Only the ones chosen",opt_assets:"Choose assets",opt_assets_wallets:"Choose wallets",opt_assets_help:"An asset from a hidden asset group stays hidden, even when chosen here",opt_assets_help_wallets:"A wallet from a hidden asset group stays hidden, even when chosen here",opt_hide_amounts:"Hide amounts initially",opt_hide_amounts_help:"Percentages stay visible; the eye at the top of the card shows the amounts only temporarily",opt_limit:"Assets before \u201CShow all\u201D",opt_limit_wallets:"Wallets before \u201CShow all\u201D",opt_limit_help:"0 shows every asset",opt_limit_help_wallets:"Only while \u201CWallets in asset groups\u201D is off; 0 shows all",opt_layout:"Show as",layout_list:"List",layout_tiles:"Tiles",opt_currency:"Default currency",opt_currency_help:"The buttons on the card change it only temporarily; more currencies via \u201CConfigure\u201D on the Price Tracker"};var ws={tf_day:"1D",tf_week:"1S",tf_month:"1M",tf_six_month:"6M",tf_year:"1A",aria_timeframe:"Periodo",aria_currency:"Moneda",search_placeholder:"Nombre, s\xEDmbolo o ISIN",search_none:"Ning\xFAn wallet coincide con \xAB{query}\xBB.",aria_search:"Buscar wallets",aria_search_clear:"Borrar b\xFAsqueda",return_day:"rentabilidad en 1 d\xEDa",return_week:"rentabilidad en 1 semana",return_month:"rentabilidad en 1 mes",return_six_month:"rentabilidad en 6 meses",return_year:"rentabilidad en 1 a\xF1o",value_line:"Valor total, {start} \u2013 hoy",value_line_day:"Valor total, \xFAltimas 24 horas",cash:"Efectivo",cash_plus:"Cash Plus",staked:"{share} en staking",show_all:"Mostrar todo ({count})",show_less:"Mostrar menos",detail_available:"Disponible",detail_staked:"En staking",detail_staking_apr:"APR de staking",detail_average_buy_price:"Precio medio de compra",detail_invested:"Importe invertido",detail_profit_loss:"Ganancia / p\xE9rdida",detail_rewards:"Recompensas de staking",detail_rewards_net:"Neto, en total",detail_rewards_worth:"hoy valen {value}",detail_payouts:"Pagos",detail_payouts_value:"{count} \xB7 \xFAltimo el {date}",shares_one:"t\xEDtulo",shares_other:"t\xEDtulos",shares_many:"t\xEDtulos",assets_missing_one:"Incluye un activo elegido que ahora mismo no existe. Se queda guardado y vuelve a aplicarse en cuanto vuelva.",assets_missing_many:"Incluye {count} activos elegidos que ahora mismo no existen. Se quedan guardados y vuelven a aplicarse en cuanto vuelvan.",assets_missing_other:"Incluye {count} activos elegidos que ahora mismo no existen. Se quedan guardados y vuelven a aplicarse en cuanto vuelvan.",eye_hide:"Ocultar importes",eye_show:"Mostrar importes",change_since:"Variaci\xF3n desde el {date}",ecb_footer:"Precios en {currency}: precios en EUR de Bitpanda convertidos al tipo de referencia del BCE del {date}. Su variaci\xF3n incluye la del tipo.",empty_portfolio:"Configura el Bitpanda Portfolio para verlo aqu\xED.",empty_wallets:"Todav\xEDa no hay wallets.",empty_selection_wallets:"Ning\xFAn wallet en la selecci\xF3n de esta tarjeta.",empty_selection_assets:"Ning\xFAn activo en la selecci\xF3n de esta tarjeta.",empty_price_tracker:"Configura el Bitpanda Price Tracker y a\xF1ade activos para ver precios aqu\xED.",picker_portfolio:"Valor total y rentabilidad con l\xEDnea, efectivo y Cash Plus, distribuci\xF3n y tus wallets; cada parte se puede ocultar.",picker_price_tracker:"Precios y cambios de los activos que sigues, cada uno con su l\xEDnea, en lista o en mosaicos.",invalid_option:"Valor no v\xE1lido para \xAB{option}\xBB: {value}. Permitidos: {allowed}.",allowed_text:"texto",allowed_assets:"una lista de ID de activo o ID de dispositivo",allowed_groups:"una lista de {values}",group_content:"Contenido",group_wallets:"Wallets",group_assets:"Activos",group_appearance:"Apariencia",opt_title:"T\xEDtulo",opt_title_help:"D\xE9jalo vac\xEDo para el nombre mostrado en gris",opt_timeframe:"Periodo predeterminado",opt_timeframe_help:"Los botones 1D a 1A de la tarjeta lo cambian solo temporalmente",tfo_day:"1 d\xEDa",tfo_week:"1 semana",tfo_month:"1 mes",tfo_six_month:"6 meses",tfo_year:"1 a\xF1o",opt_show_cash:"Efectivo y Cash Plus",opt_show_allocation:"Barra de distribuci\xF3n",opt_show_allocation_help:"La barra de colores con la proporci\xF3n de cada grupo de activos y del efectivo",opt_show_total:"Valor total y rentabilidad",opt_show_total_help:"Los botones de periodo se mantienen mientras se muestre la l\xEDnea",opt_show_line:"L\xEDnea del valor total",opt_show_wallets:"Wallets",opt_group_wallets:"Wallets en grupos de activos",opt_show_search:"Campo de b\xFAsqueda",opt_show_search_help:"Encuentra wallets por nombre, s\xEDmbolo o ISIN",opt_sort:"Ordenar por",sort_value:"Valor",sort_return:"Rentabilidad desde la compra",sort_name:"Nombre",sort_selection:"Orden de selecci\xF3n",sort_change_desc:"Cambio, mayor primero",sort_change_asc:"Cambio, menor primero",opt_sort_help_tracker:"\xABOrden de selecci\xF3n\xBB solo se aplica con \xABSolo los elegidos\xBB en los activos; si no, por nombre",opt_group_selection:"Grupos de activos mostrados",opt_group_selection_help:"Solo afecta a los wallets; el valor total, el efectivo, Cash Plus y la distribuci\xF3n muestran siempre toda la cartera",opt_groups:"Elegir grupos de activos",opt_asset_selection:"Activos mostrados",opt_asset_selection_wallets:"Wallets mostrados",sel_all:"Todos",sel_all_except:"Todos excepto los elegidos",sel_only:"Solo los elegidos",opt_assets:"Elegir activos",opt_assets_wallets:"Elegir wallets",opt_assets_help:"Un activo de un grupo de activos oculto sigue oculto, aunque se elija aqu\xED",opt_assets_help_wallets:"Un wallet de un grupo de activos oculto sigue oculto, aunque se elija aqu\xED",opt_hide_amounts:"Ocultar inicialmente los importes",opt_hide_amounts_help:"Los porcentajes siguen visibles; el ojo de la parte superior de la tarjeta muestra los importes solo temporalmente",opt_limit:"Activos antes de \xABMostrar todo\xBB",opt_limit_wallets:"Wallets antes de \xABMostrar todo\xBB",opt_limit_help:"0 muestra todos los activos",opt_limit_help_wallets:"Solo si \xABWallets en grupos de activos\xBB est\xE1 desactivado; 0 muestra todo",opt_layout:"Mostrar como",layout_list:"Lista",layout_tiles:"Mosaicos",opt_currency:"Moneda predeterminada",opt_currency_help:"Los botones de la tarjeta la cambian solo temporalmente; m\xE1s monedas con \xABConfigurar\xBB en el Price Tracker"};var vs={tf_day:"1J",tf_week:"1S",tf_month:"1M",tf_six_month:"6M",tf_year:"1A",aria_timeframe:"P\xE9riode",aria_currency:"Devise",search_placeholder:"Nom, symbole ou ISIN",search_none:"Aucun wallet ne correspond \xE0 \xAB\xA0{query}\xA0\xBB.",aria_search:"Rechercher des wallets",aria_search_clear:"Effacer la recherche",return_day:"rendement sur 1 jour",return_week:"rendement sur 1 semaine",return_month:"rendement sur 1 mois",return_six_month:"rendement sur 6 mois",return_year:"rendement sur 1 an",value_line:"Valeur totale, {start} \u2013 aujourd'hui",value_line_day:"Valeur totale, derni\xE8res 24 heures",cash:"Liquidit\xE9s",cash_plus:"Cash Plus",staked:"{share} en staking",show_all:"Tout afficher ({count})",show_less:"Afficher moins",detail_available:"Disponible",detail_staked:"En staking",detail_staking_apr:"APR du staking",detail_average_buy_price:"Prix d'achat moyen",detail_invested:"Montant investi",detail_profit_loss:"Gain / perte",detail_rewards:"R\xE9compenses de staking",detail_rewards_net:"Net, depuis le d\xE9but",detail_rewards_worth:"valant {value} aujourd'hui",detail_payouts:"Versements",detail_payouts_value:"{count} \xB7 dernier le {date}",shares_one:"titre",shares_other:"titres",shares_many:"titres",assets_missing_one:"Cela inclut un actif choisi qui n'existe pas pour le moment. Il reste enregistr\xE9 et s'applique de nouveau d\xE8s qu'il revient.",assets_missing_many:"Cela inclut {count} actifs choisis qui n'existent pas pour le moment. Ils restent enregistr\xE9s et s'appliquent de nouveau d\xE8s qu'ils reviennent.",assets_missing_other:"Cela inclut {count} actifs choisis qui n'existent pas pour le moment. Ils restent enregistr\xE9s et s'appliquent de nouveau d\xE8s qu'ils reviennent.",eye_hide:"Masquer les montants",eye_show:"Afficher les montants",change_since:"Variation depuis le {date}",ecb_footer:"Prix en {currency}\xA0: prix en EUR de Bitpanda convertis au taux de r\xE9f\xE9rence de la BCE du {date}. Leur variation inclut celle du taux.",empty_portfolio:"Configurez le Bitpanda Portfolio pour le voir ici.",empty_wallets:"Aucun wallet pour le moment.",empty_selection_wallets:"Aucun wallet dans la s\xE9lection de cette carte.",empty_selection_assets:"Aucun actif dans la s\xE9lection de cette carte.",empty_price_tracker:"Configurez le Bitpanda Price Tracker et ajoutez-y des actifs pour voir les prix ici.",picker_portfolio:"Valeur totale et rendement avec courbe, liquidit\xE9s et Cash Plus, r\xE9partition et vos wallets\xA0; chaque partie peut \xEAtre masqu\xE9e.",picker_price_tracker:"Prix et variations des actifs que vous suivez, chacun avec sa courbe, en liste ou en tuiles.",invalid_option:"Valeur non valide pour \xAB\xA0{option}\xA0\xBB\xA0: {value}. Valeurs possibles\xA0: {allowed}.",allowed_text:"texte",allowed_assets:"une liste d'ID d'actifs ou d'ID d'appareils",allowed_groups:"une liste d'\xE9l\xE9ments parmi {values}",group_content:"Contenu",group_wallets:"Wallets",group_assets:"Actifs",group_appearance:"Apparence",opt_title:"Titre",opt_title_help:"Laisser vide pour le nom affich\xE9 en gris",opt_timeframe:"P\xE9riode par d\xE9faut",opt_timeframe_help:"Les boutons 1J \xE0 1A de la carte ne la changent que temporairement",tfo_day:"1 jour",tfo_week:"1 semaine",tfo_month:"1 mois",tfo_six_month:"6 mois",tfo_year:"1 an",opt_show_cash:"Liquidit\xE9s et Cash Plus",opt_show_allocation:"Barre de r\xE9partition",opt_show_allocation_help:"La barre color\xE9e avec la part de chaque groupe d'actifs et des liquidit\xE9s",opt_show_total:"Valeur totale et rendement",opt_show_total_help:"Les boutons de p\xE9riode restent tant que la courbe est affich\xE9e",opt_show_line:"Courbe de la valeur totale",opt_show_wallets:"Wallets",opt_group_wallets:"Wallets par groupe d'actifs",opt_show_search:"Champ de recherche",opt_show_search_help:"Trouve les wallets par nom, symbole ou ISIN",opt_sort:"Trier par",sort_value:"Valeur",sort_return:"Rendement depuis l'achat",sort_name:"Nom",sort_selection:"Ordre de s\xE9lection",sort_change_desc:"Variation, la plus forte d'abord",sort_change_asc:"Variation, la plus faible d'abord",opt_sort_help_tracker:"\xAB\xA0Ordre de s\xE9lection\xA0\xBB ne s'applique qu'avec \xAB\xA0Seulement ceux choisis\xA0\xBB pour les actifs\xA0; sinon, tri par nom",opt_group_selection:"Groupes d'actifs affich\xE9s",opt_group_selection_help:"S'applique seulement aux wallets\xA0; la valeur totale, les liquidit\xE9s, Cash Plus et la r\xE9partition portent toujours sur l'ensemble du portefeuille",opt_groups:"Choisir les groupes d'actifs",opt_asset_selection:"Actifs affich\xE9s",opt_asset_selection_wallets:"Wallets affich\xE9s",sel_all:"Tous",sel_all_except:"Tous sauf ceux choisis",sel_only:"Seulement ceux choisis",opt_assets:"Choisir les actifs",opt_assets_wallets:"Choisir les wallets",opt_assets_help:"Un actif d'un groupe d'actifs masqu\xE9 reste masqu\xE9, m\xEAme s'il est choisi ici",opt_assets_help_wallets:"Un wallet d'un groupe d'actifs masqu\xE9 reste masqu\xE9, m\xEAme s'il est choisi ici",opt_hide_amounts:"Masquer initialement les montants",opt_hide_amounts_help:"Les pourcentages restent visibles\xA0; l'\u0153il en haut de la carte n'affiche les montants que temporairement",opt_limit:"Actifs avant \xAB\xA0Tout afficher\xA0\xBB",opt_limit_wallets:"Wallets avant \xAB\xA0Tout afficher\xA0\xBB",opt_limit_help:"0 affiche tous les actifs",opt_limit_help_wallets:"Seulement si \xAB\xA0Wallets par groupe d'actifs\xA0\xBB est d\xE9sactiv\xE9\xA0; 0 affiche tout",opt_layout:"Afficher en",layout_list:"Liste",layout_tiles:"Tuiles",opt_currency:"Devise par d\xE9faut",opt_currency_help:"Les boutons de la carte ne la changent que temporairement\xA0; d'autres devises via \xAB\xA0Configurer\xA0\xBB dans le Price Tracker"};var bs={tf_day:"1G",tf_week:"1S",tf_month:"1M",tf_six_month:"6M",tf_year:"1A",aria_timeframe:"Periodo",aria_currency:"Valuta",search_placeholder:"Nome, simbolo o ISIN",search_none:"Nessun wallet corrisponde a \xAB{query}\xBB.",aria_search:"Cerca nei wallet",aria_search_clear:"Cancella ricerca",return_day:"rendimento su 1 giorno",return_week:"rendimento su 1 settimana",return_month:"rendimento su 1 mese",return_six_month:"rendimento su 6 mesi",return_year:"rendimento su 1 anno",value_line:"Valore totale, {start} \u2013 oggi",value_line_day:"Valore totale, ultime 24 ore",cash:"Liquidit\xE0",cash_plus:"Cash Plus",staked:"{share} in staking",show_all:"Mostra tutto ({count})",show_less:"Mostra meno",detail_available:"Disponibile",detail_staked:"In staking",detail_staking_apr:"APR dello staking",detail_average_buy_price:"Prezzo medio di acquisto",detail_invested:"Importo investito",detail_profit_loss:"Profitto / perdita",detail_rewards:"Ricompense di staking",detail_rewards_net:"Netto, in totale",detail_rewards_worth:"oggi valgono {value}",detail_payouts:"Accrediti",detail_payouts_value:"{count} \xB7 ultimo il {date}",shares_one:"pezzo",shares_other:"pezzi",shares_many:"pezzi",assets_missing_one:"Include un asset scelto che al momento non c'\xE8. Resta salvato e torna a valere appena \xE8 di nuovo disponibile.",assets_missing_many:"Include {count} asset scelti che al momento non ci sono. Restano salvati e tornano a valere appena sono di nuovo disponibili.",assets_missing_other:"Include {count} asset scelti che al momento non ci sono. Restano salvati e tornano a valere appena sono di nuovo disponibili.",eye_hide:"Nascondi gli importi",eye_show:"Mostra gli importi",change_since:"Variazione dal {date}",ecb_footer:"Prezzi in {currency}: prezzi in EUR di Bitpanda convertiti al tasso di riferimento BCE del {date}. La loro variazione include quella del tasso.",empty_portfolio:"Configura il Bitpanda Portfolio per vederlo qui.",empty_wallets:"Ancora nessun wallet.",empty_selection_wallets:"Nessun wallet nella selezione di questa scheda.",empty_selection_assets:"Nessun asset nella selezione di questa scheda.",empty_price_tracker:"Configura il Bitpanda Price Tracker e aggiungi degli asset per vedere i prezzi qui.",picker_portfolio:"Valore totale e rendimento con linea, liquidit\xE0 e Cash Plus, ripartizione e i tuoi wallet; ogni parte si pu\xF2 nascondere.",picker_price_tracker:"Prezzi e variazioni degli asset che segui, ognuno con la sua linea, come elenco o riquadri.",invalid_option:"Valore non valido per \xAB{option}\xBB: {value}. Consentiti: {allowed}.",allowed_text:"testo",allowed_assets:"un elenco di ID asset o ID dispositivo",allowed_groups:"un elenco di valori tra {values}",group_content:"Contenuto",group_wallets:"Wallet",group_assets:"Asset",group_appearance:"Aspetto",opt_title:"Titolo",opt_title_help:"Lascia vuoto per il nome mostrato in grigio",opt_timeframe:"Periodo predefinito",opt_timeframe_help:"I pulsanti da 1G a 1A sulla scheda lo cambiano solo temporaneamente",tfo_day:"1 giorno",tfo_week:"1 settimana",tfo_month:"1 mese",tfo_six_month:"6 mesi",tfo_year:"1 anno",opt_show_cash:"Liquidit\xE0 e Cash Plus",opt_show_allocation:"Barra di ripartizione",opt_show_allocation_help:"La barra colorata con le quote dei gruppi di asset e della liquidit\xE0",opt_show_total:"Valore totale e rendimento",opt_show_total_help:"I pulsanti del periodo restano finch\xE9 \xE8 mostrata la linea",opt_show_line:"Linea del valore totale",opt_show_wallets:"Wallet",opt_group_wallets:"Wallet in gruppi di asset",opt_show_search:"Campo di ricerca",opt_show_search_help:"Trova i wallet per nome, simbolo o ISIN",opt_sort:"Ordina per",sort_value:"Valore",sort_return:"Rendimento dall'acquisto",sort_name:"Nome",sort_selection:"Ordine di selezione",sort_change_desc:"Variazione, maggiore prima",sort_change_asc:"Variazione, minore prima",opt_sort_help_tracker:"\xABOrdine di selezione\xBB vale solo con \xABSolo quelli scelti\xBB per gli asset; altrimenti per nome",opt_group_selection:"Gruppi di asset mostrati",opt_group_selection_help:"Vale solo per i wallet; valore totale, liquidit\xE0, Cash Plus e ripartizione mostrano sempre l'intero portafoglio",opt_groups:"Scegli i gruppi di asset",opt_asset_selection:"Asset mostrati",opt_asset_selection_wallets:"Wallet mostrati",sel_all:"Tutti",sel_all_except:"Tutti tranne quelli scelti",sel_only:"Solo quelli scelti",opt_assets:"Scegli gli asset",opt_assets_wallets:"Scegli i wallet",opt_assets_help:"Un asset di un gruppo di asset nascosto resta nascosto, anche se scelto qui",opt_assets_help_wallets:"Un wallet di un gruppo di asset nascosto resta nascosto, anche se scelto qui",opt_hide_amounts:"Nascondi inizialmente gli importi",opt_hide_amounts_help:"Le percentuali restano visibili; l'occhio in alto nella scheda mostra gli importi solo temporaneamente",opt_limit:"Asset prima di \xABMostra tutto\xBB",opt_limit_wallets:"Wallet prima di \xABMostra tutto\xBB",opt_limit_help:"0 mostra tutti gli asset",opt_limit_help_wallets:"Solo se \xABWallet in gruppi di asset\xBB \xE8 disattivato; 0 mostra tutto",opt_layout:"Mostra come",layout_list:"Elenco",layout_tiles:"Riquadri",opt_currency:"Valuta predefinita",opt_currency_help:"I pulsanti sulla scheda la cambiano solo temporaneamente; altre valute tramite \xABConfigura\xBB nel Price Tracker"};var xs={tf_day:"1D",tf_week:"1W",tf_month:"1M",tf_six_month:"6M",tf_year:"1J",aria_timeframe:"Periode",aria_currency:"Valuta",search_placeholder:"Naam, symbool of ISIN",search_none:"Geen wallet past bij \u2018{query}\u2019.",aria_search:"Wallets doorzoeken",aria_search_clear:"Zoekopdracht wissen",return_day:"rendement over 1 dag",return_week:"rendement over 1 week",return_month:"rendement over 1 maand",return_six_month:"rendement over 6 maanden",return_year:"rendement over 1 jaar",value_line:"Totale waarde, {start} \u2013 vandaag",value_line_day:"Totale waarde, laatste 24 uur",cash:"Contanten",cash_plus:"Cash Plus",staked:"{share} in staking",show_all:"Alles tonen ({count})",show_less:"Minder tonen",detail_available:"Beschikbaar",detail_staked:"In staking",detail_staking_apr:"Staking-APR",detail_average_buy_price:"Gemiddelde aankoopprijs",detail_invested:"Ge\xEFnvesteerd",detail_profit_loss:"Winst / verlies",detail_rewards:"Stakingbeloningen",detail_rewards_net:"Netto, totaal",detail_rewards_worth:"vandaag {value} waard",detail_payouts:"Uitbetalingen",detail_payouts_value:"{count} \xB7 laatste {date}",shares_one:"stuk",shares_other:"stuks",assets_missing_one:"Hieronder valt een gekozen asset die er nu niet is. Die blijft bewaard en geldt weer zodra die terug is.",assets_missing_other:"Hieronder vallen {count} gekozen assets die er nu niet zijn. Ze blijven bewaard en gelden weer zodra ze terug zijn.",eye_hide:"Bedragen verbergen",eye_show:"Bedragen tonen",change_since:"Verandering sinds {date}",ecb_footer:"Prijzen in {currency}: de EUR-prijzen van Bitpanda, omgerekend tegen de ECB-referentiekoers van {date}. Hun verandering omvat de beweging van de koers.",empty_portfolio:"Stel het Bitpanda Portfolio in om het hier te zien.",empty_wallets:"Nog geen wallets.",empty_selection_wallets:"Geen wallets in de selectie van deze kaart.",empty_selection_assets:"Geen assets in de selectie van deze kaart.",empty_price_tracker:"Stel de Bitpanda Price Tracker in en voeg er assets aan toe om hier prijzen te zien.",picker_portfolio:"Totale waarde en rendement met een lijn, contanten en Cash Plus, verdeling en je wallets; elk deel kan worden verborgen.",picker_price_tracker:"Prijzen en veranderingen van de assets die je volgt, elk met een lijn, als lijst of tegels.",invalid_option:"Ongeldige waarde voor \u2018{option}\u2019: {value}. Toegestaan: {allowed}.",allowed_text:"tekst",allowed_assets:"een lijst met asset-ID's of apparaat-ID's",allowed_groups:"een lijst met waarden uit {values}",group_content:"Inhoud",group_wallets:"Wallets",group_assets:"Assets",group_appearance:"Uiterlijk",opt_title:"Titel",opt_title_help:"Leeg laten voor de grijs getoonde naam",opt_timeframe:"Standaardperiode",opt_timeframe_help:"De knoppen 1D tot 1J op de kaart wijzigen die alleen tijdelijk",tfo_day:"1 dag",tfo_week:"1 week",tfo_month:"1 maand",tfo_six_month:"6 maanden",tfo_year:"1 jaar",opt_show_cash:"Contanten en Cash Plus",opt_show_allocation:"Verdelingsbalk",opt_show_allocation_help:"De gekleurde balk met het aandeel van elke assetgroep en van de contanten",opt_show_total:"Totale waarde en rendement",opt_show_total_help:"De periodeknoppen blijven zolang de lijn wordt getoond",opt_show_line:"Lijn van de totale waarde",opt_show_wallets:"Wallets",opt_group_wallets:"Wallets in assetgroepen",opt_show_search:"Zoekveld",opt_show_search_help:"Vindt wallets op naam, symbool of ISIN",opt_sort:"Sorteren op",sort_value:"Waarde",sort_return:"Rendement sinds aankoop",sort_name:"Naam",sort_selection:"Volgorde zoals gekozen",sort_change_desc:"Verandering, hoogste eerst",sort_change_asc:"Verandering, laagste eerst",opt_sort_help_tracker:"\u2018Volgorde zoals gekozen\u2019 geldt alleen bij \u2018Alleen de gekozen\u2019 assets, anders op naam",opt_group_selection:"Getoonde assetgroepen",opt_group_selection_help:"Geldt alleen voor de wallets; totale waarde, contanten, Cash Plus en verdeling tonen altijd het hele portfolio",opt_groups:"Assetgroepen kiezen",opt_asset_selection:"Getoonde assets",opt_asset_selection_wallets:"Getoonde wallets",sel_all:"Alle",sel_all_except:"Alle behalve de gekozen",sel_only:"Alleen de gekozen",opt_assets:"Assets kiezen",opt_assets_wallets:"Wallets kiezen",opt_assets_help:"Een asset uit een verborgen assetgroep blijft verborgen, ook als die hier is gekozen",opt_assets_help_wallets:"Een wallet uit een verborgen assetgroep blijft verborgen, ook als die hier is gekozen",opt_hide_amounts:"Bedragen aanvankelijk verbergen",opt_hide_amounts_help:"Percentages blijven zichtbaar; het oog bovenaan de kaart toont de bedragen alleen tijdelijk",opt_limit:"Assets v\xF3\xF3r \u2018Alles tonen\u2019",opt_limit_wallets:"Wallets v\xF3\xF3r \u2018Alles tonen\u2019",opt_limit_help:"0 toont alle assets",opt_limit_help_wallets:"Alleen als \u2018Wallets in assetgroepen\u2019 uit staat; 0 toont alles",opt_layout:"Weergeven als",layout_list:"Lijst",layout_tiles:"Tegels",opt_currency:"Standaardvaluta",opt_currency_help:"De knoppen op de kaart wijzigen die alleen tijdelijk; meer valuta via \u2018Configureren\u2019 bij de Price Tracker"};var ks={tf_day:"1D",tf_week:"1T",tf_month:"1M",tf_six_month:"6M",tf_year:"1R",aria_timeframe:"Okres",aria_currency:"Waluta",search_placeholder:"Nazwa, symbol lub ISIN",search_none:"\u017Baden portfel nie pasuje do \u201E{query}\u201D.",aria_search:"Szukaj portfeli",aria_search_clear:"Wyczy\u015B\u0107 wyszukiwanie",return_day:"stopa zwrotu za 1 dzie\u0144",return_week:"stopa zwrotu za 1 tydzie\u0144",return_month:"stopa zwrotu za 1 miesi\u0105c",return_six_month:"stopa zwrotu za 6 miesi\u0119cy",return_year:"stopa zwrotu za 1 rok",value_line:"Warto\u015B\u0107 ca\u0142kowita, {start} \u2013 dzi\u015B",value_line_day:"Warto\u015B\u0107 ca\u0142kowita, ostatnie 24 godziny",cash:"Got\xF3wka",cash_plus:"Cash Plus",staked:"{share} w stakingu",show_all:"Poka\u017C wszystkie ({count})",show_less:"Poka\u017C mniej",detail_available:"Dost\u0119pne",detail_staked:"W stakingu",detail_staking_apr:"APR stakingu",detail_average_buy_price:"\u015Arednia cena zakupu",detail_invested:"Zainwestowano",detail_profit_loss:"Zysk / strata",detail_rewards:"Nagrody za staking",detail_rewards_net:"Netto, \u0142\u0105cznie",detail_rewards_worth:"dzi\u015B warte {value}",detail_payouts:"Naliczenia",detail_payouts_value:"{count} \xB7 ostatnio {date}",shares_one:"sztuka",shares_other:"sztuki",shares_few:"sztuki",shares_many:"sztuk",assets_missing_one:"Obejmuje to jedno wybrane aktywo, kt\xF3rego teraz nie ma. Pozostaje zapisane i zn\xF3w obowi\u0105zuje, gdy wr\xF3ci.",assets_missing_few:"Obejmuje to {count} wybrane aktywa, kt\xF3rych teraz nie ma. Pozostaj\u0105 zapisane i zn\xF3w obowi\u0105zuj\u0105, gdy wr\xF3c\u0105.",assets_missing_many:"Obejmuje to {count} wybranych aktyw\xF3w, kt\xF3rych teraz nie ma. Pozostaj\u0105 zapisane i zn\xF3w obowi\u0105zuj\u0105, gdy wr\xF3c\u0105.",assets_missing_other:"Obejmuje to {count} wybranego aktywa, kt\xF3rego teraz nie ma. Pozostaje zapisane i zn\xF3w obowi\u0105zuje, gdy wr\xF3ci.",eye_hide:"Ukryj kwoty",eye_show:"Poka\u017C kwoty",change_since:"Zmiana od {date}",ecb_footer:"Ceny w {currency}: ceny Bitpandy w EUR przeliczone po kursie referencyjnym EBC z {date}. Ich zmiana obejmuje ruch kursu.",empty_portfolio:"Skonfiguruj Bitpanda Portfolio, aby zobaczy\u0107 je tutaj.",empty_wallets:"Brak portfeli.",empty_selection_wallets:"Brak portfeli w wyborze tej karty.",empty_selection_assets:"Brak aktyw\xF3w w wyborze tej karty.",empty_price_tracker:"Skonfiguruj Bitpanda Price Tracker i dodaj aktywa, aby zobaczy\u0107 tutaj ceny.",picker_portfolio:"Warto\u015B\u0107 ca\u0142kowita i stopa zwrotu z wykresem, got\xF3wka i Cash Plus, alokacja oraz twoje portfele; ka\u017Cd\u0105 cz\u0119\u015B\u0107 mo\u017Cna ukry\u0107.",picker_price_tracker:"Ceny i zmiany \u015Bledzonych aktyw\xF3w, ka\u017Cde z wykresem, jako lista lub kafelki.",invalid_option:"Nieprawid\u0142owa warto\u015B\u0107 dla \u201E{option}\u201D: {value}. Dozwolone: {allowed}.",allowed_text:"tekst",allowed_assets:"lista identyfikator\xF3w aktyw\xF3w lub urz\u0105dze\u0144",allowed_groups:"lista warto\u015Bci spo\u015Br\xF3d {values}",group_content:"Zawarto\u015B\u0107",group_wallets:"Portfele",group_assets:"Aktywa",group_appearance:"Wygl\u0105d",opt_title:"Tytu\u0142",opt_title_help:"Pozostaw puste, aby u\u017Cy\u0107 nazwy pokazanej na szaro",opt_timeframe:"Domy\u015Blny okres",opt_timeframe_help:"Przyciski od 1D do 1R na karcie zmieniaj\u0105 go tylko tymczasowo",tfo_day:"1 dzie\u0144",tfo_week:"1 tydzie\u0144",tfo_month:"1 miesi\u0105c",tfo_six_month:"6 miesi\u0119cy",tfo_year:"1 rok",opt_show_cash:"Got\xF3wka i Cash Plus",opt_show_allocation:"Pasek alokacji",opt_show_allocation_help:"Kolorowy pasek pokazuj\u0105cy udzia\u0142 grup aktyw\xF3w i got\xF3wki",opt_show_total:"Warto\u015B\u0107 ca\u0142kowita i stopa zwrotu",opt_show_total_help:"Przyciski okresu pozostaj\u0105, dop\xF3ki wy\u015Bwietlany jest wykres",opt_show_line:"Wykres warto\u015Bci ca\u0142kowitej",opt_show_wallets:"Portfele",opt_group_wallets:"Portfele w grupach aktyw\xF3w",opt_show_search:"Pole wyszukiwania",opt_show_search_help:"Znajduje portfele po nazwie, symbolu lub ISIN",opt_sort:"Sortuj wed\u0142ug",sort_value:"Warto\u015B\u0107",sort_return:"Stopa zwrotu od zakupu",sort_name:"Nazwa",sort_selection:"Kolejno\u015B\u0107 wyboru",sort_change_desc:"Zmiana, najwy\u017Csza najpierw",sort_change_asc:"Zmiana, najni\u017Csza najpierw",opt_sort_help_tracker:"\u201EKolejno\u015B\u0107 wyboru\u201D dzia\u0142a tylko przy opcji \u201ETylko wybrane\u201D dla aktyw\xF3w; w przeciwnym razie wed\u0142ug nazwy",opt_group_selection:"Wy\u015Bwietlane grupy aktyw\xF3w",opt_group_selection_help:"Dotyczy tylko portfeli; warto\u015B\u0107 ca\u0142kowita, got\xF3wka, Cash Plus i alokacja zawsze pokazuj\u0105 ca\u0142e portfolio",opt_groups:"Wybierz grupy aktyw\xF3w",opt_asset_selection:"Wy\u015Bwietlane aktywa",opt_asset_selection_wallets:"Wy\u015Bwietlane portfele",sel_all:"Wszystkie",sel_all_except:"Wszystkie opr\xF3cz wybranych",sel_only:"Tylko wybrane",opt_assets:"Wybierz aktywa",opt_assets_wallets:"Wybierz portfele",opt_assets_help:"Aktywo z ukrytej grupy aktyw\xF3w pozostaje ukryte, nawet je\u015Bli wybrano je tutaj",opt_assets_help_wallets:"Portfel z ukrytej grupy aktyw\xF3w pozostaje ukryty, nawet je\u015Bli wybrano go tutaj",opt_hide_amounts:"Pocz\u0105tkowo ukrywaj kwoty",opt_hide_amounts_help:"Procenty pozostaj\u0105 widoczne; oko u g\xF3ry karty pokazuje kwoty tylko tymczasowo",opt_limit:"Aktywa przed \u201EPoka\u017C wszystkie\u201D",opt_limit_wallets:"Portfele przed \u201EPoka\u017C wszystkie\u201D",opt_limit_help:"0 pokazuje wszystkie aktywa",opt_limit_help_wallets:"Tylko gdy opcja \u201EPortfele w grupach aktyw\xF3w\u201D jest wy\u0142\u0105czona; 0 pokazuje wszystkie",opt_layout:"Poka\u017C jako",layout_list:"Lista",layout_tiles:"Kafelki",opt_currency:"Domy\u015Blna waluta",opt_currency_help:"Przyciski na karcie zmieniaj\u0105 j\u0105 tylko tymczasowo; wi\u0119cej walut przez \u201EKonfiguruj\u201D w Price Trackerze"};var $s={en:ys,de:gs,fr:vs,nl:xs,it:bs,es:ws,pl:ks},As=s=>s in $s,Ss="en",Ro=s=>{let t=s.toLowerCase().replace(/[-_].*$/,"");return As(t)?t:"en"};function O(s){let t=s??document.querySelector("home-assistant")?.hass;return t?Ro(t.locale.language):Ss}function Cs(s){return As(s.locale.language.toLowerCase().replace(/[-_].*$/,""))}function He(s){Ss=O(s)}var Ts=s=>$s[O(s)];function u(s,t,e={}){return Ts(s)[t].replace(/\{(\w+)\}/g,(o,n)=>n in e?String(e[n]):o)}function Ne(s,t,e){let o=new Intl.PluralRules(O(s)).select(e);return Ts(s)[`${t}_${o}`].replace("{count}",String(e))}async function Ps(s){await s.loadBackendTranslation("selector","bitpanda")}function $t(s,t){return s.localize(`component.bitpanda.selector.asset_group.options.${t}`)||t}var U=["day","week","month","six_month","year"],L=["crypto","stock","etf","etc","index","metal","other"],W=["all","all_except","only"],Es=["EUR","CHF","CZK","DKK","GBP","HUF","NOK","PLN","RON","SEK","TRY","USD"],Me=["value","return","name"];var Oe=["selection","name","change_desc","change_asc"],We=["list","tiles"];var P=s=>({allowed:()=>s.join(", "),check:t=>typeof t=="string"&&s.includes(t)}),j={allowed:()=>"true, false",check:s=>typeof s=="boolean"},Rs={allowed:()=>u(void 0,"allowed_text"),check:s=>typeof s=="string"},je={allowed:()=>"0, 1, 2, \u2026",check:s=>typeof s=="number"&&Number.isInteger(s)&&s>=0},De={allowed:()=>u(void 0,"allowed_assets"),check:s=>Array.isArray(s)&&s.every(t=>typeof t=="string")},Ue={allowed:()=>u(void 0,"allowed_groups",{values:L.join(", ")}),check:s=>Array.isArray(s)&&s.every(t=>L.includes(t))},zs={allowed:()=>"EUR, USD, \u2026",check:s=>typeof s=="string"&&/^[A-Z]{3}$/.test(s)};function Be(s,t){if(s===null||typeof s!="object"||Array.isArray(s))throw new Error(u(void 0,"invalid_option",{option:"type",value:JSON.stringify(s),allowed:"custom:\u2026"}));let e=Object.fromEntries(Object.entries(s).filter(([,o])=>o!==null));for(let[o,n]of Object.entries(t)){let r=e[o];if(r!==void 0&&!n.check(r))throw new Error(u(void 0,"invalid_option",{option:o,value:JSON.stringify(r),allowed:n.allowed()}))}return e}var se=(s,t)=>({select:{mode:"dropdown",options:s.map(e=>({value:e,label:t(e)}))}}),At=s=>({name:"title",default:s,selector:{text:{}}}),St=()=>({name:"timeframe",selector:se(U,s=>u(void 0,`tfo_${s}`))}),D=(s,t)=>({name:s,default:t,selector:{boolean:{}}}),Ct=s=>({name:"limit",default:s,selector:{number:{min:0,max:100,mode:"box"}}}),Tt=s=>({name:"sort",selector:se(s,t=>u(void 0,`sort_${t}`))});function Fe(){return document.querySelector("home-assistant")?.hass}var zo=3e3;async function Ls(s){if(!s)return{};let t;try{let o=(await Promise.race([s.callWS({type:"frontend/get_translations",language:s.language,category:"selector",integration:["bitpanda"]}),new Promise(r=>{t=setTimeout(()=>r(void 0),zo)})]))?.resources??{},n={};for(let r of L){let i=o[`component.bitpanda.selector.asset_group.options.${r}`];typeof i=="string"&&i&&(n[r]=i)}return n}catch{return{}}finally{clearTimeout(t)}}var Ve=s=>s==="only"||s==="all_except",Pt=(s,t)=>[{name:"group_selection",selector:se(W,e=>u(void 0,`sel_${e}`))},...Ve(t)?[{name:"groups",selector:{select:{multiple:!0,mode:"dropdown",options:L.map(e=>({value:e,label:s[e]??e}))}}}]:[]],Et=(s,t)=>[{name:"asset_selection",selector:se(W,e=>u(void 0,`sel_${e}`))},...Ve(t)?[{name:"assets",selector:{device:{multiple:!0,filter:[{integration:"bitpanda",model:s}]}}}]:[]],ye=()=>({type:"divider",name:""}),oe=(s,t)=>({type:"expandable",name:"",flatten:!0,title:u(void 0,s),schema:t}),Lo={title:"opt_title",timeframe:"opt_timeframe",show_total:"opt_show_total",show_graph:"opt_show_line",show_cash:"opt_show_cash",show_allocation:"opt_show_allocation",show_wallets:"opt_show_wallets",group_wallets:"opt_group_wallets",show_search:"opt_show_search",sort:"opt_sort",group_selection:"opt_group_selection",groups:"opt_groups",asset_selection:"opt_asset_selection",assets:"opt_assets",hide_amounts:"opt_hide_amounts",limit:"opt_limit",layout:"opt_layout",currency:"opt_currency"},Io={title:"opt_title_help",timeframe:"opt_timeframe_help",show_total:"opt_show_total_help",show_allocation:"opt_show_allocation_help",hide_amounts:"opt_hide_amounts_help",show_search:"opt_show_search_help",assets:"opt_assets_help",limit:"opt_limit_help",currency:"opt_currency_help"};function Rt(s){let t=Lo[s.name];return t?u(void 0,t):void 0}function zt(s){let t=Io[s.name];return t?u(void 0,t):void 0}var qe=ue`
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
  /* A name breaks between words only; a word too long for its line ends in
     an ellipsis, as a name longer than two lines does. */
  .n {
    font-size: 14px;
    overflow-wrap: normal;
    text-overflow: ellipsis;
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
  /* A part of a text that never breaks inside itself, such as a date. */
  .nw {
    white-space: nowrap;
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
`;var Ge={title:Rs},B=class extends z{constructor(){super(...arguments);this.timeframe="day";this.amountsHidden=!1;this.seriesRevision=0;this.watched=[]}static{this.properties={hass:{attribute:!1},config:{state:!0},timeframe:{state:!0},amountsHidden:{state:!0},seriesRevision:{state:!0}}}static{this.styles=qe}setConfig(e){let o=this.validate(e),n=o;this.config=o,this.timeframe=n.timeframe??"day",this.amountsHidden=n.hide_amounts??!1}toggleAmounts(){this.amountsHidden=!this.amountsHidden}seriesArrived(){this.seriesRevision+=1}selectTimeframe(e){this.timeframe=e}shouldUpdate(e){if(e.size!==1||!e.has("hass"))return!0;let o=e.get("hass"),n=this.hass;return!o||!n||o.entities!==n.entities||o.devices!==n.devices||o.locale!==n.locale||o.localize!==n.localize?!0:this.watched.some(r=>o.states[r]!==n.states[r])}connectedCallback(){super.connectedCallback(),typeof ResizeObserver<"u"&&(this.resizer=new ResizeObserver(()=>this.fitLayout()),this.resizer.observe(this))}disconnectedCallback(){this.resizer?.disconnect(),this.resizer=void 0,super.disconnectedCallback()}updated(e){super.updated(e),this.remeasures(e)&&this.fitLayout()}fitLayout(){}remeasures(e){return!0}willUpdate(e){let o=this.hass;if(!o)return;He(o);let n=O(o);n!==this.categoryLanguage&&(this.categoryLanguage=n,Ps(o)),this.watched=this.watchedEntities()}getCardSize(){return 3}getGridOptions(){return{columns:12,min_columns:6}}};var Ho="bitpanda",Is={return_day:"day",return_week:"week",return_month:"month",return_six_month:"six_month",return_year:"year"},Hs=s=>s.replace(/\s+/g,"").toLowerCase();function No(s,t){let e=(s??"").trim();return e&&Hs(e)!==Hs(t)?`${e} (${t})`:t}function Lt(s,t){let e=new Map;for(let n of Object.values(s.entities)){if(!n||n.platform!==Ho||!n.device_id)continue;let r=e.get(n.device_id)??[];r.push(n),e.set(n.device_id,r)}let o=[];for(let[n,r]of e){let i=s.devices[n];i?.model===t&&o.push([i,r])}return o}var Y=s=>typeof s=="string"&&s!==""?s:void 0,Ns=new Map,Mo=/ (Wallet|Price Tracker)$/;function Os(s,t,e){let o=e.map(i=>s.states[i.entity_id]?.attributes).find(i=>i?.asset),n;if(o){let i=Y(o.asset)??"",l=Y(o.asset_isin),a=Y(o.asset_category),c=Y(o.asset_name);n={name:No(c,i),shortName:c??i,symbol:i,...l?{isin:l}:{},...a&&L.includes(a)?{category:a}:{}},Ns.set(t.id,n)}else{let i=(Y(t.name)??"").replace(Mo,"");n=Ns.get(t.id)??{name:i,shortName:i,symbol:""}}let r=Y(t.name_by_user);return{deviceId:t.id,assetId:t.serial_number??"",...n,...r?{name:r,shortName:r}:{}}}function Ke(s){let[t]=Lt(s,"Portfolio");if(!t)return;let[e,o]=t,n={deviceId:e.id,returns:{},wallets:[]};for(let r of o){let i=r.translation_key??"";i==="total_value"?n.totalValue=r.entity_id:i==="cash"?n.cash=r.entity_id:i==="cash_plus"?n.cashPlus=r.entity_id:i in Is&&(n.returns[Is[i]]=r.entity_id)}for(let[r,i]of Lt(s,"Wallet")){let l=Os(s,r,i);for(let a of i)a.translation_key==="wallet"?l.available=a.entity_id:a.translation_key==="wallet_total"?l.total=a.entity_id:a.translation_key==="staking"&&(l.staking=a.entity_id);n.wallets.push(l)}return n}function ne(s){return Lt(s,"Price Tracker").map(([t,e])=>{let o={};for(let n of e){if(n.translation_key!=="price")continue;let r=Y(s.states[n.entity_id]?.attributes.unit_of_measurement);r&&(o[r]=n.entity_id)}return{...Os(s,t,e),prices:o}})}function we(s){let t=new Set(s.flatMap(o=>Object.keys(o.prices))),e=[...t].filter(o=>o!=="EUR").sort();return t.has("EUR")?["EUR",...e]:e}function Ze(s,t,e){if(t==="all")return[...s];let o=t==="only";return s.filter(n=>e.includes(n.category??"other")===o)}var Ms=(s,t)=>t===s.deviceId||t!==""&&t===s.assetId;function Ye(s,t,e){if(t==="all_except")return s.filter(o=>!e.some(n=>Ms(o,n)));if(t==="only"){let o=[];for(let n of e){let r=s.find(i=>Ms(i,n));r&&!o.includes(r)&&o.push(r)}return o}return[...s]}var Je="bitpanda-portfolio-card-editor",Xe="bitpanda-price-tracker-card-editor",Oo=[["asset_selection","assets"],["group_selection","groups"]],Wo={timeframe:"day",sort:"value",group_selection:"all",asset_selection:"all"},jo={layout:"list",timeframe:"day",currency:"EUR",sort:"name",group_selection:"all",asset_selection:"all"},Do=/^[0-9a-f]{32}$/;function Ws(s,t){return s?Object.values(s.devices).filter(e=>e!==void 0&&e.model===t&&(e.identifiers??[]).some(([o])=>o==="bitpanda")):[]}function Uo(s,t){return s?/[.!?…]$/.test(s)?`${s} ${t}`:`${s}. ${t}`:t}async function Bo(s=customElements,t=window,e=1e4){if(s.get("ha-form"))return;try{await(await(await t.loadCardHelpers?.())?.createCardElement({type:"entities",entities:[]}))?.constructor?.getConfigElement?.()}catch{}let o;await Promise.race([s.whenDefined("ha-form"),new Promise(n=>{o=setTimeout(n,e)})]),clearTimeout(o)}async function et(s){return await Bo(),customElements.get(Je)||customElements.define(Je,It),customElements.get(Xe)||customElements.define(Xe,Ht),document.createElement(s)}var Qe=class extends z{constructor(){super(...arguments);this.names={};this.namesAsked=!1;this.heldBack={}}static{this.properties={hass:{attribute:!1},config:{state:!0},names:{state:!0}}}setConfig(e){this.config=e}chosenAssets(){let e=this.config?.assets,o=Ws(this.hass,this.model),n=[],r=[];for(let i of Array.isArray(e)?e:[]){let l=o.find(a=>a.id===i||a.serial_number&&a.serial_number===i);l?n.includes(l.id)||n.push(l.id):!Do.test(i)&&!r.includes(i)&&r.push(i)}return{devices:n,missing:r}}savedAssets(e){let o=Ws(this.hass,this.model),n=[];for(let r of[...e.map(i=>o.find(l=>l.id===i)?.serial_number||i),...this.chosenAssets().missing])n.includes(r)||n.push(r);return n}willUpdate(e){super.willUpdate(e),this.hass&&(He(this.hass),this.namesAsked||(this.namesAsked=!0,Ls(this.hass).then(o=>{this.names=o})))}render(){if(!this.config)return m;let e=this.form(),{devices:o,missing:n}=this.chosenAssets(),r={...this.defaults,...this.config};"assets"in r&&(r.assets=o);let i=n.length===0?e.computeHelper:l=>l.name==="assets"?Uo(e.computeHelper(l),Ne(void 0,"assets_missing",n.length)):e.computeHelper(l);return d`<ha-form
      .hass=${this.hass}
      .data=${r}
      .schema=${e.schema}
      .computeLabel=${e.computeLabel}
      .computeHelper=${i}
      @value-changed=${this.changed}
    ></ha-form>`}changed(e){e.stopPropagation();let o=this.config??{},n=e.detail.value,r=Array.isArray(n.assets)?{...n,assets:this.savedAssets(n.assets)}:n,i=Object.fromEntries(Object.entries(r).filter(([l,a])=>l in o||this.defaults[l]===void 0||a!==this.defaults[l]));for(let[l,a]of Oo)Ve(i[l])?!(a in i)&&a in this.heldBack&&(i[a]=this.heldBack[a]):(a in i&&(this.heldBack[a]=i[a]),delete i[a]);this.config=i,this.dispatchEvent(new CustomEvent("config-changed",{detail:{config:i},bubbles:!0,composed:!0}))}},Fo={limit:"opt_limit_wallets",asset_selection:"opt_asset_selection_wallets",assets:"opt_assets_wallets"},Vo={limit:"opt_limit_help_wallets",group_selection:"opt_group_selection_help",assets:"opt_assets_help_wallets"},It=class extends Qe{constructor(){super(...arguments);this.defaults=Wo;this.model="Wallet"}form(){let e=this.config??{};return{schema:[At("Bitpanda Portfolio"),oe("group_content",[St(),D("show_total",!0),D("show_graph",!0),D("show_cash",!0),D("show_allocation",!0),D("show_wallets",!0)]),oe("group_wallets",[D("show_search",!1),D("group_wallets",!0),Tt(Me),Ct(5),ye(),...Pt(this.names,e.group_selection??"all"),ye(),...Et("Wallet",e.asset_selection??"all")]),oe("group_appearance",[D("hide_amounts",!1)])],computeLabel:o=>{let n=Fo[o.name];return n?u(void 0,n):Rt(o)},computeHelper:o=>{let n=Vo[o.name];return n?u(void 0,n):zt(o)}}}};function qo(s){let t=s?we(ne(s)):[];return t.length>0?t:Es}var Ht=class extends Qe{constructor(){super(...arguments);this.defaults=jo;this.model="Price Tracker"}form(){let e=this.config??{};return{schema:[At("Bitpanda Price Tracker"),oe("group_content",[{name:"layout",selector:se(We,o=>u(void 0,`layout_${o}`))},St(),{name:"currency",selector:{select:{mode:"dropdown",options:qo(this.hass).map(o=>({value:o,label:o}))}}}]),oe("group_assets",[Tt(Oe),Ct(0),ye(),...Pt(this.names,e.group_selection??"all"),ye(),...Et("Price Tracker",e.asset_selection??"all")])],computeLabel:Rt,computeHelper:o=>o.name==="sort"?u(void 0,"opt_sort_help_tracker"):zt(o)}}};function tt(s){switch(s.locale.number_format){case"comma_decimal":return"en-US";case"decimal_comma":return"de";case"space_comma":return"fr";case"quote_decimal":return"de-CH";case"system":return;default:return s.locale.language}}function Mt(s,t,e,o=0){return new Intl.NumberFormat(tt(s),{maximumFractionDigits:e,minimumFractionDigits:o,useGrouping:s.locale.number_format!=="none"}).format(t)}function Go(s,t){let e=t!==0&&Math.abs(t)<1e-4;return new Intl.NumberFormat(tt(s),{...e?{maximumSignificantDigits:2}:{maximumFractionDigits:4},roundingMode:"trunc",useGrouping:s.locale.number_format!=="none"}).format(t)}function ve(s,t,e,o,n=!1){let r=n?Go(s,t):Mt(s,t,8);return e==="stock"||e==="etf"||e==="etc"?`${r} ${Ne(s,"shares",t)}`:`${r} ${e==="metal"?"g":o}`}var Ot=new Set(["unavailable","unknown"]);function I(s,t){let e=t?s.states[t]:void 0;return e&&!Ot.has(e.state)?s.formatEntityState(e):void 0}function js(s,t,e){let o=t?s.states[t]:void 0;return o&&e!==void 0?s.formatEntityState({...o,state:String(e)}):void 0}function be(s,t,e,o=!1){return Us(s,t,e,2,o)}function Ds(s,t,e){let o=Math.abs(t);return Us(s,t,e,o>=10||o===0?2:o>=1?4:8,!1)}function Us(s,t,e,o,n){try{return new Intl.NumberFormat(tt(s),{style:"currency",currency:e,minimumFractionDigits:2,maximumFractionDigits:o,useGrouping:s.locale.number_format!=="none",...n?{signDisplay:"exceptZero"}:{}}).format(t)}catch{return`${Mt(s,t,o)} ${e}`}}function Ko(s){let t=Math.abs(s);return t===0||t>=10?2:t>=1?4:t>=.1?5:t>=.001?6:t>=1e-4?7:8}function Bs(s,t,e){let o=t?s.states[t]:void 0;if(!o||Ot.has(o.state)||e===void 0||!Number.isFinite(e))return;let n=s.entities[o.entity_id]?.display_precision,r=typeof n=="number"?n:Ko(Number(o.state)),i=Number(e.toFixed(r))===0?0 .toFixed(r):e.toFixed(r),l=s.formatEntityState({...o,state:i});return Number(i)>0?`+${l}`:l}function k(s,t){let e=t?s.states[t]:void 0;if(!e||Ot.has(e.state)||e.state.trim()==="")return;let o=Number(e.state);return Number.isFinite(o)?o:void 0}var Zo=new Set(["cs","de","fi","fr","sk","sv"]),Fs=s=>Zo.has(s.locale.language)?"\xA0":"";function H(s,t){if(t===void 0||!Number.isFinite(t))return{text:"\u2014",direction:"none"};let e=new Intl.NumberFormat(tt(s),{minimumFractionDigits:2,maximumFractionDigits:2,signDisplay:"exceptZero",useGrouping:s.locale.number_format!=="none"}).format(t),o=Fs(s),r=Math.round(Math.abs(t)*100)===0?"flat":t>0?"up":"down";return{text:`${e}${o}%`,direction:r}}function re(s,t,e,o=!1){let n=Fs(s);return`${Mt(s,t,e,o?e:0)}${n}%`}function E(s){return s==="up"||s==="down"?s:""}function J(s){return s==="up"?"\u25B2":s==="down"?"\u25BC":""}function Wt(s){return Cs(s)?s.locale.language:"en"}function Vs(s){return s.locale.time_zone==="server"?s.config?.time_zone:void 0}function Yo(s){let t=s.locale.time_format;return t==="12"||t==="24"?t==="12":new Date("January 1, 2023 22:00:00").toLocaleString(t==="system"?void 0:s.locale.language).includes("10")}function xe(s,t){let e=Vs(s),o=r=>new Intl.DateTimeFormat("en",{year:"numeric",timeZone:e}).format(r),n=o(t)===o(Date.now())?{}:{year:"numeric"};return new Intl.DateTimeFormat(Wt(s),{day:"numeric",month:"short",...n,timeZone:e}).format(t)}function qs(s,t){let e=/^(\d{4})-(\d{2})-(\d{2})$/.exec(t);if(!e)return;let o=Date.UTC(Number(e[1]),Number(e[2])-1,Number(e[3]));return new Intl.DateTimeFormat(Wt(s),{day:"numeric",month:"long",timeZone:"UTC"}).format(o)}function st(s,t){let e=Yo(s);return new Intl.DateTimeFormat(Wt(s),{day:"numeric",month:"short",hour:e?"numeric":"2-digit",minute:"2-digit",hourCycle:e?"h12":"h23",timeZone:Vs(s)}).format(t)}var{I:Dr}=_s;var Gs=s=>s.strings===void 0;var Ks={ATTRIBUTE:1,CHILD:2,PROPERTY:3,BOOLEAN_ATTRIBUTE:4,EVENT:5,ELEMENT:6},jt=s=>(...t)=>({_$litDirective$:s,values:t}),ot=class{constructor(t){}get _$AU(){return this._$AM._$AU}_$AT(t,e,o){this._$Ct=t,this._$AM=e,this._$Ci=o}_$AS(t,e){return this.update(t,e)}update(t,e){return this.render(...e)}};var ke=(s,t)=>{let e=s._$AN;if(e===void 0)return!1;for(let o of e)o._$AO?.(t,!1),ke(o,t);return!0},nt=s=>{let t,e;do{if((t=s._$AM)===void 0)break;e=t._$AN,e.delete(s),s=t}while(e?.size===0)},Zs=s=>{for(let t;t=s._$AM;s=t){let e=t._$AN;if(e===void 0)t._$AN=e=new Set;else if(e.has(s))break;e.add(s),Qo(t)}};function Jo(s){this._$AN!==void 0?(nt(this),this._$AM=s,Zs(this)):this._$AM=s}function Xo(s,t=!1,e=0){let o=this._$AH,n=this._$AN;if(n!==void 0&&n.size!==0)if(t)if(Array.isArray(o))for(let r=e;r<o.length;r++)ke(o[r],!1),nt(o[r]);else o!=null&&(ke(o,!1),nt(o));else ke(this,s)}var Qo=s=>{s.type==Ks.CHILD&&(s._$AP??=Xo,s._$AQ??=Jo)},rt=class extends ot{constructor(){super(...arguments),this._$AN=void 0}_$AT(t,e,o){super._$AT(t,e,o),Zs(this),this.isConnected=t._$AU}_$AO(t,e=!0){t!==this.isConnected&&(this.isConnected=t,t?this.reconnected?.():this.disconnected?.()),e&&(ke(this,t),nt(this))}setValue(t){if(Gs(this._$Ct))this._$Ct._$AI(t,this);else{let e=[...this._$Ct._$AH];e[this._$Ci]=t,this._$Ct._$AI(e,this,0)}}disconnected(){}reconnected(){}};var Ys=()=>new Ut,Ut=class{},Dt=new WeakMap,Js=jt(class extends rt{render(s){return m}update(s,[t]){let e=t!==this.G;return e&&this.rt(void 0),(e||this.lt!==this.ct)&&(this.G=t,this.ht=s.options?.host,this.rt(this.ct=s.element)),m}rt(s){if(this.G!==void 0)if(this.isConnected||(s=void 0),typeof this.G=="function"){let t=this.ht??globalThis,e=Dt.get(t);e===void 0&&(e=new WeakMap,Dt.set(t,e)),e.get(this.G)!==void 0&&this.G.call(this.ht,void 0),e.set(this.G,s),s!==void 0&&this.G.call(this.ht,s)}else this.G.value=s}get lt(){return typeof this.G=="function"?Dt.get(this.ht??globalThis)?.get(this.G):this.G?.value}disconnected(){this.lt===this.ct&&this.rt(void 0)}reconnected(){this.rt(this.ct)}});var en="M12,9A3,3 0 0,0 9,12A3,3 0 0,0 12,15A3,3 0 0,0 15,12A3,3 0 0,0 12,9M12,17A5,5 0 0,1 7,12A5,5 0 0,1 12,7A5,5 0 0,1 17,12A5,5 0 0,1 12,17M12,4.5C7,4.5 2.73,7.61 1,12C2.73,16.39 7,19.5 12,19.5C17,19.5 21.27,16.39 23,12C21.27,7.61 17,4.5 12,4.5Z",tn="M11.83,9L15,12.16C15,12.11 15,12.05 15,12A3,3 0 0,0 12,9C11.94,9 11.89,9 11.83,9M7.53,9.8L9.08,11.35C9.03,11.56 9,11.77 9,12A3,3 0 0,0 12,15C12.22,15 12.44,14.97 12.65,14.92L14.2,16.47C13.53,16.8 12.79,17 12,17A5,5 0 0,1 7,12C7,11.21 7.2,10.47 7.53,9.8M2,4.27L4.28,6.55L4.73,7C3.08,8.3 1.78,10 1,12C2.73,16.39 7,19.5 12,19.5C13.55,19.5 15.03,19.2 16.38,18.66L16.81,19.08L19.73,22L21,20.73L3.27,3M12,7A5,5 0 0,1 17,12C17,12.64 16.87,13.26 16.64,13.82L19.57,16.75C21.07,15.5 22.27,13.86 23,12C21.27,7.61 17,4.5 12,4.5C10.6,4.5 9.26,4.75 8,5.2L10.17,7.35C10.74,7.13 11.35,7 12,7Z",Qs="M7.41,8.58L12,13.17L16.59,8.58L18,10L12,16L6,10L7.41,8.58Z",eo="M7.41,15.41L12,10.83L16.59,15.41L18,14L12,8L6,14L7.41,15.41Z",sn="M8.59,16.58L13.17,12L8.59,7.41L10,6L16,12L10,18L8.59,16.58Z",on="M9.5,3A6.5,6.5 0 0,1 16,9.5C16,11.11 15.41,12.59 14.44,13.73L14.71,14H15.5L20.5,19L19,20.5L14,15.5V14.71L13.73,14.44C12.59,15.41 11.11,16 9.5,16A6.5,6.5 0 0,1 3,9.5A6.5,6.5 0 0,1 9.5,3M9.5,5C7,5 5,7 5,9.5C5,12 7,14 9.5,14C12,14 14,12 14,9.5C14,7 12,5 9.5,5Z",nn="M19,6.41L17.59,5L12,10.59L6.41,5L5,6.41L10.59,12L5,17.59L6.41,19L12,13.41L17.59,19L19,17.59L13.41,12L19,6.41Z",ie=s=>te`<svg viewBox="0 0 24 24" aria-hidden="true"><path d=${s}></path></svg>`,Bt={down:Qs,up:eo,right:sn};function C(s){return t=>{(t.key==="Enter"||t.key===" ")&&(t.preventDefault(),s())}}function ae(s,t){s.dispatchEvent(new CustomEvent("hass-more-info",{bubbles:!0,composed:!0,detail:{entityId:t}}))}function le(s,t){let e=s.filter(o=>o.second!==void 0);return e.length>0&&e.every(o=>o.first+t+o.second<=o.room)}function $(s,t){return d`<span class="amount ${t?"blur":""}">${s??"\u2014"}</span>`}function to(s,t,e){let[o,...n]=s.split(`{${t}}`);return n.length===0?d`${s}`:d`${o}<span class="nw">${e}</span>${n.join(`{${t}}`)}`}function X(s){return d`<div class="empty">${s}</div>`}function $e(s,t,e){return d`<div class="head">
    <div class="title">${t}</div>
    ${e?d`<button
          class="icon-btn eye"
          aria-label=${u(s,e.hidden?"eye_show":"eye_hide")}
          title=${u(s,e.hidden?"eye_show":"eye_hide")}
          @click=${e.toggle}
        >
          ${ie(e.hidden?tn:en)}
        </button>`:m}
  </div>`}function so(s,t,e,o,n){let{text:r,direction:i}=H(s,t),l=J(i);return d`<div class="hero-line">
    <span class="chip ${E(i)}" role="button" tabindex="0" @click=${o} @keydown=${C(o)}
      >${l?`${l} `:""}${r}</span
    >
    ${i!=="none"&&n?.text?d`<span class="chip-amount ${E(i)}">${$(n.text,n.hidden)}</span>`:m}
    <span class="chip-label">${u(s,`return_${e}`)}</span>
  </div>`}function oo(s,t,e,o,n){return d`<div class="seg" role="radiogroup" aria-label=${s} @keydown=${i=>{let l=i.key==="ArrowRight"||i.key==="ArrowDown"?1:i.key==="ArrowLeft"||i.key==="ArrowUp"?-1:0;if(l===0)return;i.preventDefault();let a=(t.indexOf(e)+l+t.length)%t.length;n(t[a]),i.currentTarget.querySelectorAll("[role=radio]")[a]?.focus()}}>
    ${t.map(i=>d`<span
          role="radio"
          aria-checked=${i===e?"true":"false"}
          tabindex=${i===e?0:-1}
          @click=${()=>n(i)}
          @keydown=${C(()=>n(i))}
          >${o(i)}</span
        >`)}
  </div>`}function it(s,t,e){return oo(u(s,"aria_timeframe"),U,t,o=>u(s,`tf_${o}`),e)}function no(s,t,e,o){return t.length<2?null:oo(u(s,"aria_currency"),t,e,n=>n,o)}var rn=new Set(["unavailable","unknown"]);function S(s,t){if(!s||rn.has(s.state))return;let e=s.attributes[t];return typeof e=="number"&&Number.isFinite(e)?e:void 0}function ro(s,t,e){let o=Ys(),n=()=>{e(""),o.value?.focus()};return d`<div class="search" role="search">
    ${ie(on)}<input
      ${Js(o)}
      type="text"
      .value=${t}
      placeholder=${u(s,"search_placeholder")}
      aria-label=${u(s,"aria_search")}
      autocomplete="off"
      spellcheck="false"
      @input=${r=>e(r.target.value)}
    />${t?d`<span class="clear" role="button" tabindex="0" aria-label=${u(s,"aria_search_clear")} @click=${n} @keydown=${C(n)}
          >${ie(nn)}</span
        >`:m}
  </div>`}var an={\u00DF:"ss",\u00F8:"o",\u00E6:"ae",\u0153:"oe",\u0142:"l",\u0111:"d",\u00F0:"d",\u00FE:"th",\u0131:"i"};function Xs(s){return s.normalize("NFD").replace(/\p{M}/gu,"").toLowerCase().replace(/[ßøæœłđðþı]/gu,t=>an[t]??t).replace(/[^\p{L}\p{N}\s]/gu,"")}function io(s,t){let e=Xs(t).split(/\s+/).filter(Boolean),o=Xs(`${s.name} ${s.symbol} ${s.isin??""}`);return e.length>0&&e.every(n=>o.includes(n))}function ao(s){let{hass:t,wallet:e,hidden:o,onTap:n,chevron:r}=s,i=e.total?t.states[e.total]:void 0,l=S(i,"units"),a=k(t,e.total),c=k(t,e.staking),h=a&&c&&c>0?c/a*100:void 0,{text:p,direction:_}=H(t,S(i,"total_return_percent")),f=J(_),v=_==="none"?d`<span class="wchip none">—</span>`:d`<span class="wchip ${E(_)}">${f?`${f} `:""}${p}</span>`,y=h===void 0?m:d`<div class="stake"><span class="badge">${u(t,"staked",{share:re(t,h,0)})}</span></div>`,g=x=>{x.stopPropagation(),r?.toggle()};return d`<div class="wallet">
    <div class="tap" role="button" tabindex="0" @click=${n} @keydown=${C(n)}>
      <div class="main">
        <div class="n" title=${e.shortName}>${e.shortName}</div>
        <div class="sub ${h===void 0?"":"staked"}">
          <div class="s">
            <span class="units"
              >${$(l===void 0?void 0:ve(t,l,e.category,e.symbol,!0),o)}</span
            >${e.isin?d` · <span class="isin">${e.isin}</span>`:m}
          </div>
          ${y}
        </div>
      </div>
      <div class="right">${v}<span class="val">${$(I(t,e.total),o)}</span></div>
    </div>
    ${r?d`<span
          class="chevron"
          role="button"
          tabindex="0"
          aria-expanded=${r.open?"true":"false"}
          @click=${g}
          @keydown=${x=>{x.stopPropagation(),C(r.toggle)(x)}}
          >${ie(r.open?eo:Qs)}</span
        >`:m}
  </div>`}function at(s,t,e){let o=i=>k(s,i.total)??Number.NEGATIVE_INFINITY,n=i=>S(i.total?s.states[i.total]:void 0,"total_return_percent")??Number.NEGATIVE_INFINITY,r=(i,l)=>i.name.localeCompare(l.name,O(s));return[...t].sort((i,l)=>e==="name"?r(i,l):(e==="value"?o(l)-o(i):n(l)-n(i))||r(i,l))}var ln=window.customElements,cn=1e4;function dn(s=()=>window.customElements,t=ln,e=cn){let o=Date.now();return new Promise(n=>{let r=()=>{let i=s();i!==t||i.get("home-assistant")||Date.now()-o>=e?n(i):setTimeout(r,50)};r()})}var pn="https://github.com/Spegeli/hacs_bitpanda#-dashboard-cards";function un(s,t,e,o,n={}){let r=s.entities[t];return!r||r.platform!=="bitpanda"||!r.device_id?null:(typeof e=="string"?[e]:e).includes(s.devices[r.device_id]?.model??"")?{config:{type:`custom:${o}`,...n}}:null}function lt(s,t,e){dn().then(r=>{r.get(s)||r.define(s,t)});let o=window;if(o.customCards??=[],o.customCards.some(r=>r.type===s))return;let{model:n}=e;o.customCards.push({type:s,name:e.name,get description(){return e.description()},preview:!0,documentationURL:pn,...n?{getEntitySuggestion:(r,i)=>un(r,i,n,s,t.getStubConfig?.())}:{}})}var hn={day:[864e5,"5minute"],week:[6048e5,"hour"],month:[2592e6,"hour"],six_month:[157248e5,"day"],year:[31536e6,"day"]};function ct(s){return s==="5minute"?5*6e4:s==="hour"?36e5:864e5}function lo(s){return s.timeframe==="month"?(s.end-s.start)/120:0}function de(s,t){let[e,o]=hn[s];return{timeframe:s,start:t-e,end:t,period:o}}var mn=s=>typeof s=="number"?s:Date.parse(s);async function _n(s,t,e){if(t.length===0)return{};let o;try{o=await s.callWS({type:"recorder/statistics_during_period",start_time:new Date(e.start).toISOString(),end_time:new Date(e.end).toISOString(),statistic_ids:[...t],period:e.period,types:["state"]})}catch{return}let n={};for(let[r,i]of Object.entries(o))n[r]=i.map(l=>({t:mn(l.start),v:l.state})).filter(l=>typeof l.v=="number"&&Number.isFinite(l.t)).sort((l,a)=>l.t-a.t);return n}var dt="portfolio";async function co(s,t,e){let o;try{o=await s.callWS({type:"bitpanda/portfolio_history",timeframe:e.timeframe})}catch{return}let r=(Array.isArray(o?.points)?o.points:[]).filter(i=>Array.isArray(i)&&typeof i[0]=="number"&&typeof i[1]=="number"&&Number.isFinite(i[0])&&Number.isFinite(i[1])).map(([i,l])=>({t:i,v:l})).sort((i,l)=>i.t-l.t);return{[dt]:r}}var ce=class{constructor(t,e=_n){this.onUpdate=t;this.fetch=e;this.key="";this.end=0;this.latest=0;this.current={}}request(t,e,o,n=""){let r=`${o.timeframe}|${[...e].sort().join(",")}|${n}`;if(r===this.key&&o.end-this.end<ct(o.period))return;o.timeframe!==this.timeframe&&(this.current={}),this.key=r,this.timeframe=o.timeframe,this.end=o.end;let i=++this.latest;this.fetch(t,e,o).then(l=>{if(i===this.latest){if(l===void 0){this.key="";return}this.current=l,this.onUpdate()}})}series(t){return this.current[t]}};function po(s,t,e){let o=ct(e.period),n=s.find(r=>r.t>=e.start-o);if(!(t===void 0||n===void 0||n.v===0))return{change:(t-n.v)/n.v*100,amount:t-n.v,...n.t>e.start+o?{since:n.t}:{}}}var uo=2,Ft=s=>Math.round(s*100)/100;function Vt(s,t,e,o){return Ft(e===t?o/2:o-uo-(s-t)/(e-t)*(o-2*uo))}function ho(s,t){let e=0;return s.forEach((o,n)=>{Math.abs(o.t-t)<Math.abs(s[e].t-t)&&(e=n)}),e}function fn(s,t){if(t<=0||s.length<3)return s;let e=n=>Math.floor(n.t/t),o=[];for(let n of s.slice(0,-1)){let r=o[o.length-1];(!r||e(n)!==e(r))&&o.push(n)}return o.push(s[s.length-1]),o}function mo(s,t,e,o,n,r=0){let i=n??1.5*ct(t.period),l=[],a;for(let g of s)(!a||g.t-a.t>i)&&l.push([]),l[l.length-1]?.push(g),a=g;let c=l.map(g=>fn(g,r)),h=c.flat().map(g=>g.v),p=Math.min(...h),_=Math.max(...h),f=t.end-t.start,v=g=>Ft((g-t.start)/f*e),y=g=>Vt(g,p,_,o);return c.map(g=>g.map(x=>[v(x.t),y(x.v)]))}function gn(s,t,e,o,n,r=0){return mo(s,t,e,o,n,r).map(i=>i.length===1?`M${i[0]?.[0]},${i[0]?.[1]}l0.01,0`:i.map(([l,a],c)=>`${c===0?"M":"L"}${l},${a}`).join("")).join("")}function yn(s,t,e,o,n,r=0){return mo(s,t,e,o,n,r).map(i=>{let l=i[0],a=i[i.length-1];return`M${l[0]},${o}${i.map(([c,h])=>`L${c},${h}`).join("")}L${a[0]},${o}Z`}).join("")}var qt=(s,t)=>s.length>0&&s[s.length-1].t-s[0].t>=(t.end-t.start)/10;function pt(s,t,e){let{width:o,height:n,fill:r,className:i,gapMs:l,stepMs:a}=e;return qt(s,t)?te`<svg class=${i} viewBox="0 0 ${o} ${n}" preserveAspectRatio="none" aria-hidden="true">${r?te`<path class="area" d=${yn(s,t,o,n,l,a)}></path>`:null}<path class="line" d=${gn(s,t,o,n,l,a)} vector-effect="non-scaling-stroke"></path></svg>`:te`<svg class=${i} viewBox="0 0 ${o} ${n}" preserveAspectRatio="none" aria-hidden="true"></svg>`}var wn=480,Gt=72,ut=s=>`${(s*100).toFixed(2)}%`;function vn(s,t,e){let{hass:o,refs:n,window:r,hidden:i,cursor:l,onCursor:a}=s,c=t.map(b=>b.v),h=Math.min(...c),p=Math.max(...c),_=r.end-r.start,f=b=>{let w=b.currentTarget.getBoundingClientRect(),R=Math.min(Math.max((b.clientX-w.left)/w.width,0),1);return ho(t,r.start+R*_)},v=b=>a(f(b)),y=()=>a(void 0),g=b=>{b.pointerType!=="mouse"&&y()},x=n.totalValue?o.states[n.totalValue]?.attributes.unit_of_measurement:void 0,T=typeof x=="string"&&!i?b=>be(o,b,x):void 0,A=l===void 0?void 0:t[l],Q=m;if(A){let b=(A.t-r.start)/_,w=r.timeframe==="day"||r.timeframe==="week"?st(o,A.t):xe(o,A.t),R=b<.25?"start":b>.75?"end":"";Q=d`${T?d`<span class="tag high">${T(p)}</span><span class="tag middle">${T((p+h)/2)}</span
            ><span class="tag low">${T(h)}</span>`:m}
      <div class="cursor" style="left:${ut(b)}"></div>
      <div class="dot" style="left:${ut(b)};top:${ut(Vt(A.v,h,p,Gt)/Gt)}"></div>
      <div class="tip ${R}" style="left:${ut(b)}">${T?`${w} \xB7 ${T(A.v)}`:w}</div>`}let Ae=pt(t,r,{width:wn,height:Gt,fill:!0,className:`spark ${e}`,gapMs:Number.POSITIVE_INFINITY});return qt(t,r)?d`<div class="plot" @pointerdown=${v} @pointermove=${v} @pointerup=${g} @pointercancel=${y} @pointerleave=${y}>
    ${Ae}
    <div class="mid"></div>
    ${Q}
  </div>`:d`<div class="plot">${Ae}</div>`}function bn(s,t,e){if(t.timeframe==="day")return u(s,"value_line_day");let o=e[0]?.t??t.start;return u(s,"value_line",{start:xe(s,Math.max(t.start,o))})}function xn(s,t,e){let o=k(s,t.totalValue),n=k(s,t.returns[e]),r=t.totalValue?s.states[t.totalValue]?.attributes.unit_of_measurement:void 0;if(!(o===void 0||n===void 0||n<=-100||typeof r!="string"))return be(s,o*n/(100+n),r,!0)}function _o(s){let{host:t,hass:e,refs:o,timeframe:n,hidden:r,window:i,points:l}=s,a=k(e,o.returns[n]),c=E(H(e,a).direction)||"flat",h=p=>()=>{p&&ae(t,p)};return d`${s.total?d`<div class="hero" role="button" tabindex="0" @click=${h(o.totalValue)} @keydown=${C(h(o.totalValue))}>
            ${$(I(e,o.totalValue),r)}
          </div>
          ${so(e,a,n,h(o.returns[n]),{text:xn(e,o,n),hidden:r})}`:m}
    ${s.total||s.line?it(e,n,s.onTimeframe):m}
    ${s.line&&l&&l.length>0?d`${vn(s,l,c)}
          <div class="caption">${bn(e,i,l)}</div>`:m}`}var kn="bitpanda-portfolio-card",fo={crypto:"var(--blue-color, #4269d0)",stock:"var(--indigo-color, #3f51b5)",etf:"var(--amber-color, #efb118)",etc:"var(--cyan-color, #00bcd4)",index:"var(--purple-color, #a463f2)",metal:"var(--green-color, #3ca951)",other:"var(--pink-color, #ff8ab7)",cash_plus:"var(--deep-orange-color, #ff725c)",cash:"var(--teal-color, #6cc5b0)"},go=s=>s.category??"other";function $n(s,t){return t<1?`<${re(s,1,0)}`:re(s,t,2,!0)}var An=(s,t)=>Ye(Ze(s.wallets,t.group_selection??"all",t.groups??[]),t.asset_selection??"all",t.assets??[]);function Sn(s,t){let e=0,o=0;for(let n of t){let r=k(s,n.total),i=S(n.total?s.states[n.total]:void 0,"invested_amount");if(r===void 0||i===void 0)return;e+=r,o+=i}return o>0?(e-o)/o*100:void 0}function yo(s){let t=s.map(o=>({room:o.room,first:o.left,second:Math.max(o.chip??0,o.value)}));if(s.length===0||le(t,Cn))return"beside";let e=s.flatMap(o=>o.chip===void 0?[]:[{room:o.below??o.room,first:o.chip,second:o.value}]);return e.length===0||le(e,Tn)?"row":"stacked"}function Kt(s){if(!s.some(t=>t===void 0))return Math.round(s.reduce((t,e)=>t+e,0)*1e8)/1e8}var Zt="\xA0\xB7 ",Cn=12,Tn=8,Pn=30,En=8,Yt=class extends B{constructor(){super(...arguments);this.openGroups=new Set;this.showAll=!1;this.query="";this.cursor=void 0;this.stakeInline=!1;this.groupsLayout="beside";this.rowsLayout="beside";this.openWallets=new Set;this.window=de("day",Date.now());this.lines=new ce(()=>this.seriesArrived(),co)}static{this.properties={...B.properties,openGroups:{state:!0},openWallets:{state:!0},showAll:{state:!0},query:{state:!0},cursor:{state:!0},stakeInline:{state:!0},groupsLayout:{state:!0},rowsLayout:{state:!0}}}static async getConfigElement(){return et(Je)}static getStubConfig(){return{timeframe:"day",sort:"value",group_selection:"all",asset_selection:"all"}}validate(e){return Be(e,{...Ge,timeframe:P(U),show_total:j,show_graph:j,show_cash:j,show_allocation:j,show_wallets:j,group_wallets:j,show_search:j,sort:P(Me),limit:je,group_selection:P(W),groups:Ue,asset_selection:P(W),assets:De,hide_amounts:j})}watchedEntities(){let e=this.hass?Ke(this.hass):void 0;return e?[e.totalValue,e.cash,e.cashPlus,...Object.values(e.returns),...e.wallets.flatMap(o=>[o.available,o.total,o.staking])].filter(o=>o!==void 0):[]}willUpdate(e){super.willUpdate(e);let o=this.hass?Ke(this.hass):void 0;this.window=de(this.timeframe,Date.now());let n=this.hass?.states[o?.returns[this.timeframe]??""]?.state??"";this.hass&&o&&this.config?.show_graph!==!1&&this.lines.request(this.hass,[dt],this.window,n)}getCardSize(){return 8}remeasures(e){return!(e.size===1&&e.has("cursor"))}fitLayout(){let e=p=>[...this.renderRoot.querySelectorAll(p)],o=(p,_)=>p.querySelector(_),n=p=>p?.getBoundingClientRect().width,r=e(".wallet .sub").map(p=>{let _=n(p.querySelector(".stake .badge"));return{room:p.clientWidth,first:o(p,".s").getBoundingClientRect().width,..._===void 0?{}:{second:_}}}),i=le(r,En);i!==this.stakeInline&&(this.stakeInline=i);let l=e(".group").map(p=>{let _=n(p.querySelector(".gchip"));return{room:p.clientWidth,left:o(p,".gleft").getBoundingClientRect().width,..._===void 0?{}:{chip:_},value:o(p,".sum").getBoundingClientRect().width}}),a=yo(l);a!==this.groupsLayout&&(this.groupsLayout=a);let c=e(".wallet .tap").map(p=>({room:p.clientWidth,below:p.clientWidth+Pn,left:[...o(p,".s .units").getClientRects()].reduce((_,f)=>_+f.width,0),chip:o(p,".wchip").getBoundingClientRect().width,value:o(p,".val").getBoundingClientRect().width})),h=yo(c);h!==this.rowsLayout&&(this.rowsLayout=h)}groupChip(e,o){let{text:n,direction:r}=H(e,Sn(e,o));if(r==="none")return d`<span class="gchip none">—</span>`;let i=J(r);return d`<span class="gchip ${E(r)}">${i?`${i} `:""}${n}</span>`}walletsClass(){return["wallets",this.stakeInline?"stake-inline":"",this.groupsLayout==="beside"?"":"groups-wrapped",this.groupsLayout==="stacked"?"groups-stacked":"",this.rowsLayout==="beside"?"":"rows-wrapped",this.rowsLayout==="stacked"?"rows-stacked":""].filter(Boolean).join(" ")}toggle(e,o){let n=new Set(e);return n.has(o)?n.delete(o):n.add(o),n}open(e){return()=>{e&&ae(this,e)}}render(){let e=this.hass,o=this.config;if(!e||!o)return m;let n=Ke(e),r={hidden:this.amountsHidden,toggle:()=>this.toggleAmounts()},i=o.title||"Bitpanda Portfolio";if(!n)return d`<ha-card>${$e(e,i,r)}${X(u(e,"empty_portfolio"))}</ha-card>`;let l=o.show_total!==!1||o.show_graph!==!1,a=o.show_cash!==!1||o.show_allocation!==!1,c=An(n,o);return d`<ha-card>
      ${$e(e,i,r)}
      <div class="content">
        ${_o({host:this,hass:e,refs:n,timeframe:this.timeframe,hidden:this.amountsHidden,window:this.window,points:this.lines.series(dt),total:o.show_total!==!1,line:o.show_graph!==!1,onTimeframe:h=>{this.cursor=void 0,this.selectTimeframe(h)},cursor:this.cursor,onCursor:h=>{h!==this.cursor&&(this.cursor=h)}})}
        ${a?d`${l?d`<div class="divider"></div>`:m}
              ${o.show_cash===!1?m:this.renderCash(e,n)}
              ${o.show_allocation===!1?m:this.renderAllocation(e,n)}`:m}
        ${o.show_wallets===!1?m:d`${l||a?d`<div class="divider"></div>`:m}${o.show_search&&c.length>0?ro(e,this.query,h=>this.query=h):m}${this.renderWallets(e,n,c,o)}`}
      </div>
    </ha-card>`}renderCash(e,o){let n=(r,i,l)=>d`<div class=${l?"end":""} role="button" tabindex="0" @click=${this.open(i)} @keydown=${C(this.open(i))}>
        <span class="k">${r}</span><span class="v">${$(I(e,i),this.amountsHidden)}</span>
      </div>`;return d`<div class="pair">${n(u(e,"cash"),o.cash,!1)}${n(u(e,"cash_plus"),o.cashPlus,!0)}</div>`}renderAllocation(e,o){let n=[];for(let l of L){let a=o.wallets.filter(c=>go(c)===l);a.length>0&&n.push({key:l,label:$t(e,l),value:Kt(a.map(c=>k(e,c.total)))})}o.cashPlus&&n.push({key:"cash_plus",label:u(e,"cash_plus"),value:k(e,o.cashPlus)}),o.cash&&n.push({key:"cash",label:u(e,"cash"),value:k(e,o.cash)});let r=Kt(n.map(l=>l.value));if(r===void 0)return d`<div class="allocation-missing muted">—</div>`;let i=n.map(l=>({...l,share:r>0?l.value/r*100:0})).filter(l=>l.share>0).sort((l,a)=>a.share-l.share);return d`<div class="bar" role="img" aria-label=${u(e,"opt_show_allocation")}>
        ${i.map(l=>d`<span style="width:${l.share}%;background:${fo[l.key]}"></span>`)}
      </div>
      <div class="legend">
        ${i.map(l=>d`<span><i style="background:${fo[l.key]}"></i>${l.label} ${$n(e,l.share)}</span>`)}
      </div>`}renderWallets(e,o,n,r){if(o.wallets.length===0)return X(u(e,"empty_wallets"));if(n.length===0)return X(u(e,"empty_selection_wallets"));let i=r.sort??"value",l=r.show_search?this.query.trim():"";if(l){let a=at(e,n.filter(c=>io(c,l)),i);return a.length>0?d`<div class=${this.walletsClass()}>${a.map(c=>this.renderWallet(e,o,c))}</div>`:d`<div class="search-none">${u(e,"search_none",{query:l})}</div>`}if(r.group_wallets===!1){let a=at(e,n,i),c=r.limit??5,h=c>0&&a.length>c,p=h&&!this.showAll?a.slice(0,c):a;return d`<div class=${this.walletsClass()}>${p.map(_=>this.renderWallet(e,o,_))}</div>
        ${h?d`<button class="show-all" @click=${()=>this.showAll=!this.showAll}>
              ${this.showAll?u(e,"show_less"):u(e,"show_all",{count:a.length})}
            </button>`:m}`}return d`<div class=${this.walletsClass()}>${L.map(a=>{let c=n.filter(f=>go(f)===a);if(c.length===0)return m;let h=Kt(c.map(f=>k(e,f.total))),p=this.openGroups.has(a),_=()=>{this.openGroups=this.toggle(this.openGroups,a)};return d`<div class="group" role="button" tabindex="0" aria-expanded=${p?"true":"false"} @click=${_} @keydown=${C(_)}>
          <span class="gleft"
            >${ie(p?Bt.down:Bt.right)}<span class="name">${$t(e,a)}</span
            ><span class="count">${c.length}</span></span
          >
          <span class="gright">${this.groupChip(e,c)}<span class="sum">${$(js(e,c[0]?.total,h),this.amountsHidden)}</span></span>
        </div>
        ${p?d`<div class="members">${at(e,c,i).map(f=>this.renderWallet(e,o,f))}</div>`:m}`})}</div>`}renderWallet(e,o,n){let r=this.openWallets.has(n.deviceId);return d`${ao({hass:e,wallet:n,hidden:this.amountsHidden,onTap:this.open(n.total),chevron:{open:r,toggle:()=>{this.openWallets=this.toggle(this.openWallets,n.deviceId)}}})}${r?this.renderDetail(e,o,n):m}`}renderDetail(e,o,n){let r=this.amountsHidden,i=w=>w?e.states[w]?.attributes.unit_of_measurement:void 0,l=String(i(n.total)??i(o.totalValue)??"EUR"),a=n.total?e.states[n.total]:void 0,c=n.staking?e.states[n.staking]:void 0,h=w=>{let R=S(w?e.states[w]:void 0,"units");return R===void 0?void 0:ve(e,R,n.category,n.symbol)},p=(w,R=!1)=>w===void 0?void 0:be(e,w,l,R),_=w=>w===void 0?void 0:Ds(e,w,l),f=w=>d`<span class="part">${w}</span>`,v=w=>d`${f($(h(w),r))}${Zt}${f($(I(e,w),r))}`,y=S(a,"total_return"),g=H(e,S(a,"total_return_percent")),x=S(c,"apr_percent"),T=S(c,"rewards_net"),A=S(c,"rewards_count"),Q=c?.attributes.rewards_last_at,Ae=typeof Q=="string"&&Number.isFinite(Date.parse(Q))?st(e,Date.parse(Q)):"\u2014",b=p(S(c,"rewards_net_value"));return d`<div class="detail">
      <div class="grid">
        <span>${u(e,"detail_available")}</span><span>${v(n.available)}</span>
        ${n.staking?d`<span>${u(e,"detail_staked")}</span><span>${v(n.staking)}</span>`:m}
        ${n.staking&&x!==void 0?d`<span>${u(e,"detail_staking_apr")}</span><span>${re(e,x,1)}</span>`:m}
        <span>${u(e,"detail_average_buy_price")}</span><span>${$(_(S(a,"average_buy_price")),r)}</span>
        <span>${u(e,"detail_invested")}</span><span>${$(p(S(a,"invested_amount")),r)}</span>
        <span>${u(e,"detail_profit_loss")}</span
        ><span class=${E(g.direction)}>${f($(p(y,!0),r))} ${f(`(${g.text})`)}</span>
      </div>
      ${A!==void 0&&A>0?d`<h4>${u(e,"detail_rewards")}</h4>
            <div class="grid">
              <span>${u(e,"detail_rewards_net")}</span>
              <span
                >${f($(T===void 0?void 0:ve(e,T,n.category,n.symbol),r))}${b?d`${Zt}${f(this.worth(e,b))}`:m}</span
              >
              <span>${u(e,"detail_payouts")}</span
              ><span
                >${u(e,"detail_payouts_value",{count:A,date:Ae}).split(" \xB7 ").map((w,R)=>d`${R>0?Zt:""}${f(w)}`)}</span
              >
            </div>`:m}
    </div>`}worth(e,o){let[n="",r=""]=u(e,"detail_rewards_worth").split("{value}");return d`${n}${$(o,this.amountsHidden)}${r}`}};lt(kn,Yt,{name:"Bitpanda Portfolio",description:()=>u(Fe(),"picker_portfolio"),model:["Portfolio","Wallet"]});var Rn=ue`
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
`,zn=6,Ln=120,In=90,ht=8,Hn=78,Nn=96,Mn=380;function wo(s){let t=Math.ceil(Math.max(0,...s.map(o=>o.price))),e=Math.ceil(Math.max(0,...s.map(o=>o.change)));return{price:t,change:Math.max(Hn,e),figures:Math.max(t,e)}}function On(s){let t=wo(s);return s.every(e=>e.room-t.price-ht-t.change-ht>=Ln)?"beside":s.every(e=>e.room-t.figures-ht>=In)?"stacked":"below"}function Wn(s){return le(s.map(t=>({room:t.room,first:t.pct,...t.amount===void 0?{}:{second:t.amount}})),zn)}var Jt=class extends B{constructor(){super(...arguments);this.showAll=!1;this.amountsInline=!1;this.rowsLayout="beside";this.columns=void 0;this.window=de("day",Date.now());this.lines=new ce(()=>this.seriesArrived())}static{this.properties={...B.properties,currency:{state:!0},showAll:{state:!0},amountsInline:{state:!0},rowsLayout:{state:!0},columns:{state:!0}}}static{this.styles=[qe,Rn]}static async getConfigElement(){return et(Xe)}static getStubConfig(){return{layout:"list",timeframe:"day",currency:"EUR",sort:"name",group_selection:"all",asset_selection:"all"}}setConfig(e){super.setConfig(e),this.currency=void 0}validate(e){return Be(e,{...Ge,layout:P(We),timeframe:P(U),currency:zs,sort:P(Oe),group_selection:P(W),groups:Ue,asset_selection:P(W),assets:De,limit:je})}watchedEntities(){return this.hass?ne(this.hass).flatMap(e=>Object.values(e.prices)):[]}shownCurrency(e){let o=we(e),n=this.currency??this.config?.currency??"EUR";return o.includes(n)?n:o.includes("EUR")?"EUR":o[0]??"EUR"}visible(e,o){let n=ne(e),r=this.shownCurrency(n),i=Ze(n,o.group_selection??"all",o.groups??[]),a=Ye(i,o.asset_selection??"all",o.assets??[]).map(v=>{let y=v.prices[r],g=y?e.states[y]:void 0,x=y?this.lines.series(y):void 0,T=k(e,y),A=po(x??[],T,this.window);return{asset:v,entityId:y,change:A?.change,amount:A?.amount,points:x,since:A?.since}}),c=o.sort??"name",h=(v,y)=>v.asset.name.localeCompare(y.asset.name,O(e));if(c==="name"||c==="selection"&&o.asset_selection!=="only")a.sort(h);else if(c==="change_desc"||c==="change_asc"){let v=c==="change_desc"?-1:1;a.sort((y,g)=>y.change===void 0||g.change===void 0?y.change===void 0?g.change===void 0?h(y,g):1:-1:v*(y.change-g.change)||h(y,g))}let p=o.limit??0,_=p>0&&a.length>p;return{rows:_&&!this.showAll?a.slice(0,p):a,ranked:a,total:a.length,folds:_,currency:r,currencies:we(n)}}willUpdate(e){if(super.willUpdate(e),this.window=de(this.timeframe,Date.now()),!this.hass||!this.config)return;let{rows:o,ranked:n}=this.visible(this.hass,this.config),r=this.config.sort??"name",l=(r==="change_desc"||r==="change_asc"?n:o).map(a=>a.entityId).filter(a=>a!==void 0);this.lines.request(this.hass,l,this.window)}fitLayout(){let e=a=>a?.getBoundingClientRect().width,o=[...this.shadowRoot?.querySelectorAll(".tile .c")??[]].map(a=>{let c=e(a.querySelector(".a"));return{room:a.clientWidth,pct:e(a.querySelector(".pct"))??0,...c===void 0?{}:{amount:c}}}),n=Wn(o);n!==this.amountsInline&&(this.amountsInline=n);let r=this.clientWidth>Mn?Nn+ht:0,i=[...this.renderRoot.querySelectorAll(".price-row")].map(a=>{let c=h=>a.querySelector(h).getBoundingClientRect().width;return{room:a.clientWidth-r,price:c(".p"),change:Math.max(c(".c .pct"),e(a.querySelector(".c .a"))??0)}}),l=On(i);if(l!==this.rowsLayout&&(this.rowsLayout=l),i.length>0){let a=wo(i),c=this.columns;(!c||c.price!==a.price||c.change!==a.change||c.figures!==a.figures)&&(this.columns=a)}}getCardSize(){return 6}open(e){return()=>{e&&ae(this,e)}}line(e,o){let n=e.since===void 0?this.window:{...this.window,start:e.since};return e.points&&e.points.length>0?pt(e.points,n,{width:96,height:28,fill:!1,className:`mini ${o}`,stepMs:lo(n)}):d`<span class="mini"></span>`}change(e,o){let{text:n,direction:r}=H(e,o.change),i=J(r),l=E(r),a=r==="none"?void 0:Bs(e,o.entityId,o.amount);return{cell:d`<div class="pct pchip ${r==="none"?"none":""}">${r==="none"?"\u2014":`${i?`${i} `:""}${n}`}</div>${a?d`<div class="a">${a}</div>`:m}`,className:l,lineClass:l||"flat"}}since(e,o){return o.since===void 0?m:d`<div class="since">${to(u(e,"change_since"),"date",xe(e,o.since))}</div>`}renderList(e,o){let n=this.columns,r=n?`--bp-price:${n.price}px;--bp-change:${n.change}px;--bp-figures:${n.figures}px`:"";return d`<div class="rows ${this.rowsLayout==="beside"?"":this.rowsLayout}" style=${r}>
      ${o.map(i=>{let l=this.change(e,i);return d`<div class="price-row" role="button" tabindex="0" @click=${this.open(i.entityId)} @keydown=${C(this.open(i.entityId))}>
          <div class="lead"><div class="n" title=${i.asset.shortName}>${i.asset.shortName}</div><div class="s">${i.asset.isin??i.asset.symbol}</div>${this.since(e,i)}</div>
          ${this.line(i,l.lineClass)}
          <div class="p">${I(e,i.entityId)??"\u2014"}</div>
          <div class="c ${l.className}">${l.cell}</div>
        </div>`})}
    </div>`}renderTiles(e,o){return d`<div class="tiles ${this.amountsInline?"inline":""}">
      ${o.map(n=>{let r=this.change(e,n);return d`<div class="tile" role="button" tabindex="0" @click=${this.open(n.entityId)} @keydown=${C(this.open(n.entityId))}>
          <div class="n" title=${n.asset.shortName}>${n.asset.shortName}</div>
          <div class="s">${n.asset.isin??n.asset.symbol}</div>
          <div class="p">${I(e,n.entityId)??"\u2014"}</div>
          <div class="c ${r.className}">${r.cell}</div>
          ${this.line(n,r.lineClass)}${this.since(e,n)}
        </div>`})}
    </div>`}footer(e,o,n){if(n==="EUR")return m;let r=o.map(i=>i.entityId?e.states[i.entityId]?.attributes.rate_date:void 0).map(i=>typeof i=="string"?qs(e,i):void 0).find(i=>i!==void 0);return r?d`<div class="foot">${u(e,"ecb_footer",{currency:n,date:r})}</div>`:m}render(){let e=this.hass,o=this.config;if(!e||!o)return m;let n=$e(e,o.title||"Bitpanda Price Tracker");if(ne(e).length===0)return d`<ha-card>${n}${X(u(e,"empty_price_tracker"))}</ha-card>`;let{rows:r,total:i,folds:l,currency:a,currencies:c}=this.visible(e,o);return d`<ha-card>
      ${n}
      <div class="content">
        <div class="switches">
          ${it(e,this.timeframe,h=>this.selectTimeframe(h))}
          ${no(e,c,a,h=>this.currency=h)}
        </div>
        ${r.length===0?X(u(e,"empty_selection_assets")):o.layout==="tiles"?this.renderTiles(e,r):this.renderList(e,r)}
        ${l?d`<button class="show-all" @click=${()=>this.showAll=!this.showAll}>
              ${this.showAll?u(e,"show_less"):u(e,"show_all",{count:i})}
            </button>`:m}
      </div>
      ${this.footer(e,r,a)}
    </ha-card>`}};lt("bitpanda-price-tracker-card",Jt,{name:"Bitpanda Price Tracker",description:()=>u(Fe(),"picker_price_tracker"),model:"Price Tracker"});
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
