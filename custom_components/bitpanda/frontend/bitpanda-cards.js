var Ce=globalThis,Pe=Ce.ShadowRoot&&(Ce.ShadyCSS===void 0||Ce.ShadyCSS.nativeShadow)&&"adoptedStyleSheets"in Document.prototype&&"replace"in CSSStyleSheet.prototype,gt=Symbol(),es=new WeakMap,me=class{constructor(t,e,n){if(this._$cssResult$=!0,n!==gt)throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");this.cssText=t,this.t=e}get styleSheet(){let t=this.o,e=this.t;if(Pe&&t===void 0){let n=e!==void 0&&e.length===1;n&&(t=es.get(e)),t===void 0&&((this.o=t=new CSSStyleSheet).replaceSync(this.cssText),n&&es.set(e,t))}return t}toString(){return this.cssText}},ts=s=>new me(typeof s=="string"?s:s+"",void 0,gt),_e=(s,...t)=>{let e=s.length===1?s[0]:t.reduce((n,o,r)=>n+(i=>{if(i._$cssResult$===!0)return i.cssText;if(typeof i=="number")return i;throw Error("Value passed to 'css' function must be a 'css' function result: "+i+". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.")})(o)+s[r+1],s[0]);return new me(e,s,gt)},ss=(s,t)=>{if(Pe)s.adoptedStyleSheets=t.map(e=>e instanceof CSSStyleSheet?e:e.styleSheet);else for(let e of t){let n=document.createElement("style"),o=Ce.litNonce;o!==void 0&&n.setAttribute("nonce",o),n.textContent=e.cssText,s.appendChild(n)}},yt=Pe?s=>s:s=>s instanceof CSSStyleSheet?(t=>{let e="";for(let n of t.cssRules)e+=n.cssText;return ts(e)})(s):s;var{is:Pn,defineProperty:En,getOwnPropertyDescriptor:Rn,getOwnPropertyNames:zn,getOwnPropertySymbols:Ln,getPrototypeOf:In}=Object,Ee=globalThis,ns=Ee.trustedTypes,Hn=ns?ns.emptyScript:"",Nn=Ee.reactiveElementPolyfillSupport,fe=(s,t)=>s,wt={toAttribute(s,t){switch(t){case Boolean:s=s?Hn:null;break;case Object:case Array:s=s==null?s:JSON.stringify(s)}return s},fromAttribute(s,t){let e=s;switch(t){case Boolean:e=s!==null;break;case Number:e=s===null?null:Number(s);break;case Object:case Array:try{e=JSON.parse(s)}catch{e=null}}return e}},rs=(s,t)=>!Pn(s,t),os={attribute:!0,type:String,converter:wt,reflect:!1,useDefault:!1,hasChanged:rs};Symbol.metadata??=Symbol("metadata"),Ee.litPropertyMetadata??=new WeakMap;var M=class extends HTMLElement{static addInitializer(t){this._$Ei(),(this.l??=[]).push(t)}static get observedAttributes(){return this.finalize(),this._$Eh&&[...this._$Eh.keys()]}static createProperty(t,e=os){if(e.state&&(e.attribute=!1),this._$Ei(),this.prototype.hasOwnProperty(t)&&((e=Object.create(e)).wrapped=!0),this.elementProperties.set(t,e),!e.noAccessor){let n=Symbol(),o=this.getPropertyDescriptor(t,n,e);o!==void 0&&En(this.prototype,t,o)}}static getPropertyDescriptor(t,e,n){let{get:o,set:r}=Rn(this.prototype,t)??{get(){return this[e]},set(i){this[e]=i}};return{get:o,set(i){let a=o?.call(this);r?.call(this,i),this.requestUpdate(t,a,n)},configurable:!0,enumerable:!0}}static getPropertyOptions(t){return this.elementProperties.get(t)??os}static _$Ei(){if(this.hasOwnProperty(fe("elementProperties")))return;let t=In(this);t.finalize(),t.l!==void 0&&(this.l=[...t.l]),this.elementProperties=new Map(t.elementProperties)}static finalize(){if(this.hasOwnProperty(fe("finalized")))return;if(this.finalized=!0,this._$Ei(),this.hasOwnProperty(fe("properties"))){let e=this.properties,n=[...zn(e),...Ln(e)];for(let o of n)this.createProperty(o,e[o])}let t=this[Symbol.metadata];if(t!==null){let e=litPropertyMetadata.get(t);if(e!==void 0)for(let[n,o]of e)this.elementProperties.set(n,o)}this._$Eh=new Map;for(let[e,n]of this.elementProperties){let o=this._$Eu(e,n);o!==void 0&&this._$Eh.set(o,e)}this.elementStyles=this.finalizeStyles(this.styles)}static finalizeStyles(t){let e=[];if(Array.isArray(t)){let n=new Set(t.flat(1/0).reverse());for(let o of n)e.unshift(yt(o))}else t!==void 0&&e.push(yt(t));return e}static _$Eu(t,e){let n=e.attribute;return n===!1?void 0:typeof n=="string"?n:typeof t=="string"?t.toLowerCase():void 0}constructor(){super(),this._$Ep=void 0,this.isUpdatePending=!1,this.hasUpdated=!1,this._$Em=null,this._$Ev()}_$Ev(){this._$ES=new Promise(t=>this.enableUpdating=t),this._$AL=new Map,this._$E_(),this.requestUpdate(),this.constructor.l?.forEach(t=>t(this))}addController(t){(this._$EO??=new Set).add(t),this.renderRoot!==void 0&&this.isConnected&&t.hostConnected?.()}removeController(t){this._$EO?.delete(t)}_$E_(){let t=new Map,e=this.constructor.elementProperties;for(let n of e.keys())this.hasOwnProperty(n)&&(t.set(n,this[n]),delete this[n]);t.size>0&&(this._$Ep=t)}createRenderRoot(){let t=this.shadowRoot??this.attachShadow(this.constructor.shadowRootOptions);return ss(t,this.constructor.elementStyles),t}connectedCallback(){this.renderRoot??=this.createRenderRoot(),this.enableUpdating(!0),this._$EO?.forEach(t=>t.hostConnected?.())}enableUpdating(t){}disconnectedCallback(){this._$EO?.forEach(t=>t.hostDisconnected?.())}attributeChangedCallback(t,e,n){this._$AK(t,n)}_$ET(t,e){let n=this.constructor.elementProperties.get(t),o=this.constructor._$Eu(t,n);if(o!==void 0&&n.reflect===!0){let r=(n.converter?.toAttribute!==void 0?n.converter:wt).toAttribute(e,n.type);this._$Em=t,r==null?this.removeAttribute(o):this.setAttribute(o,r),this._$Em=null}}_$AK(t,e){let n=this.constructor,o=n._$Eh.get(t);if(o!==void 0&&this._$Em!==o){let r=n.getPropertyOptions(o),i=typeof r.converter=="function"?{fromAttribute:r.converter}:r.converter?.fromAttribute!==void 0?r.converter:wt;this._$Em=o;let a=i.fromAttribute(e,r.type);this[o]=a??this._$Ej?.get(o)??a,this._$Em=null}}requestUpdate(t,e,n,o=!1,r){if(t!==void 0){let i=this.constructor;if(o===!1&&(r=this[t]),n??=i.getPropertyOptions(t),!((n.hasChanged??rs)(r,e)||n.useDefault&&n.reflect&&r===this._$Ej?.get(t)&&!this.hasAttribute(i._$Eu(t,n))))return;this.C(t,e,n)}this.isUpdatePending===!1&&(this._$ES=this._$EP())}C(t,e,{useDefault:n,reflect:o,wrapped:r},i){n&&!(this._$Ej??=new Map).has(t)&&(this._$Ej.set(t,i??e??this[t]),r!==!0||i!==void 0)||(this._$AL.has(t)||(this.hasUpdated||n||(e=void 0),this._$AL.set(t,e)),o===!0&&this._$Em!==t&&(this._$Eq??=new Set).add(t))}async _$EP(){this.isUpdatePending=!0;try{await this._$ES}catch(e){Promise.reject(e)}let t=this.scheduleUpdate();return t!=null&&await t,!this.isUpdatePending}scheduleUpdate(){return this.performUpdate()}performUpdate(){if(!this.isUpdatePending)return;if(!this.hasUpdated){if(this.renderRoot??=this.createRenderRoot(),this._$Ep){for(let[o,r]of this._$Ep)this[o]=r;this._$Ep=void 0}let n=this.constructor.elementProperties;if(n.size>0)for(let[o,r]of n){let{wrapped:i}=r,a=this[o];i!==!0||this._$AL.has(o)||a===void 0||this.C(o,void 0,r,a)}}let t=!1,e=this._$AL;try{t=this.shouldUpdate(e),t?(this.willUpdate(e),this._$EO?.forEach(n=>n.hostUpdate?.()),this.update(e)):this._$EM()}catch(n){throw t=!1,this._$EM(),n}t&&this._$AE(e)}willUpdate(t){}_$AE(t){this._$EO?.forEach(e=>e.hostUpdated?.()),this.hasUpdated||(this.hasUpdated=!0,this.firstUpdated(t)),this.updated(t)}_$EM(){this._$AL=new Map,this.isUpdatePending=!1}get updateComplete(){return this.getUpdateComplete()}getUpdateComplete(){return this._$ES}shouldUpdate(t){return!0}update(t){this._$Eq&&=this._$Eq.forEach(e=>this._$ET(e,this[e])),this._$EM()}updated(t){}firstUpdated(t){}};M.elementStyles=[],M.shadowRootOptions={mode:"open"},M[fe("elementProperties")]=new Map,M[fe("finalized")]=new Map,Nn?.({ReactiveElement:M}),(Ee.reactiveElementVersions??=[]).push("2.1.2");var bt=globalThis,is=s=>s,Re=bt.trustedTypes,as=Re?Re.createPolicy("lit-html",{createHTML:s=>s}):void 0,xt="$lit$",W=`lit$${Math.random().toFixed(9).slice(2)}$`,kt="?"+W,Mn=`<${kt}>`,K=document,ye=()=>K.createComment(""),we=s=>s===null||typeof s!="object"&&typeof s!="function",$t=Array.isArray,hs=s=>$t(s)||typeof s?.[Symbol.iterator]=="function",vt=`[ 	
\f\r]`,ge=/<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g,ls=/-->/g,cs=/>/g,q=RegExp(`>|${vt}(?:([^\\s"'>=/]+)(${vt}*=${vt}*(?:[^ 	
\f\r"'\`<>=]|("|')|))|$)`,"g"),ds=/'/g,ps=/"/g,ms=/^(?:script|style|textarea|title)$/i,At=s=>(t,...e)=>({_$litType$:s,strings:t,values:e}),d=At(1),ne=At(2),Qo=At(3),Z=Symbol.for("lit-noChange"),h=Symbol.for("lit-nothing"),us=new WeakMap,G=K.createTreeWalker(K,129);function _s(s,t){if(!$t(s)||!s.hasOwnProperty("raw"))throw Error("invalid template strings array");return as!==void 0?as.createHTML(t):t}var fs=(s,t)=>{let e=s.length-1,n=[],o,r=t===2?"<svg>":t===3?"<math>":"",i=ge;for(let a=0;a<e;a++){let l=s[a],c,p,m=-1,_=0;for(;_<l.length&&(i.lastIndex=_,p=i.exec(l),p!==null);)_=i.lastIndex,i===ge?p[1]==="!--"?i=ls:p[1]!==void 0?i=cs:p[2]!==void 0?(ms.test(p[2])&&(o=RegExp("</"+p[2],"g")),i=q):p[3]!==void 0&&(i=q):i===q?p[0]===">"?(i=o??ge,m=-1):p[1]===void 0?m=-2:(m=i.lastIndex-p[2].length,c=p[1],i=p[3]===void 0?q:p[3]==='"'?ps:ds):i===ps||i===ds?i=q:i===ls||i===cs?i=ge:(i=q,o=void 0);let f=i===q&&s[a+1].startsWith("/>")?" ":"";r+=i===ge?l+Mn:m>=0?(n.push(c),l.slice(0,m)+xt+l.slice(m)+W+f):l+W+(m===-2?a:f)}return[_s(s,r+(s[e]||"<?>")+(t===2?"</svg>":t===3?"</math>":"")),n]},ve=class s{constructor({strings:t,_$litType$:e},n){let o;this.parts=[];let r=0,i=0,a=t.length-1,l=this.parts,[c,p]=fs(t,e);if(this.el=s.createElement(c,n),G.currentNode=this.el.content,e===2||e===3){let m=this.el.content.firstChild;m.replaceWith(...m.childNodes)}for(;(o=G.nextNode())!==null&&l.length<a;){if(o.nodeType===1){if(o.hasAttributes())for(let m of o.getAttributeNames())if(m.endsWith(xt)){let _=p[i++],f=o.getAttribute(m).split(W),w=/([.?@])?(.*)/.exec(_);l.push({type:1,index:r,name:w[2],strings:f,ctor:w[1]==="."?Le:w[1]==="?"?Ie:w[1]==="@"?He:J}),o.removeAttribute(m)}else m.startsWith(W)&&(l.push({type:6,index:r}),o.removeAttribute(m));if(ms.test(o.tagName)){let m=o.textContent.split(W),_=m.length-1;if(_>0){o.textContent=Re?Re.emptyScript:"";for(let f=0;f<_;f++)o.append(m[f],ye()),G.nextNode(),l.push({type:2,index:++r});o.append(m[_],ye())}}}else if(o.nodeType===8)if(o.data===kt)l.push({type:2,index:r});else{let m=-1;for(;(m=o.data.indexOf(W,m+1))!==-1;)l.push({type:7,index:r}),m+=W.length-1}r++}}static createElement(t,e){let n=K.createElement("template");return n.innerHTML=t,n}};function Y(s,t,e=s,n){if(t===Z)return t;let o=n!==void 0?e._$Co?.[n]:e._$Cl,r=we(t)?void 0:t._$litDirective$;return o?.constructor!==r&&(o?._$AO?.(!1),r===void 0?o=void 0:(o=new r(s),o._$AT(s,e,n)),n!==void 0?(e._$Co??=[])[n]=o:e._$Cl=o),o!==void 0&&(t=Y(s,o._$AS(s,t.values),o,n)),t}var ze=class{constructor(t,e){this._$AV=[],this._$AN=void 0,this._$AD=t,this._$AM=e}get parentNode(){return this._$AM.parentNode}get _$AU(){return this._$AM._$AU}u(t){let{el:{content:e},parts:n}=this._$AD,o=(t?.creationScope??K).importNode(e,!0);G.currentNode=o;let r=G.nextNode(),i=0,a=0,l=n[0];for(;l!==void 0;){if(i===l.index){let c;l.type===2?c=new se(r,r.nextSibling,this,t):l.type===1?c=new l.ctor(r,l.name,l.strings,this,t):l.type===6&&(c=new Ne(r,this,t)),this._$AV.push(c),l=n[++a]}i!==l?.index&&(r=G.nextNode(),i++)}return G.currentNode=K,o}p(t){let e=0;for(let n of this._$AV)n!==void 0&&(n.strings!==void 0?(n._$AI(t,n,e),e+=n.strings.length-2):n._$AI(t[e])),e++}},se=class s{get _$AU(){return this._$AM?._$AU??this._$Cv}constructor(t,e,n,o){this.type=2,this._$AH=h,this._$AN=void 0,this._$AA=t,this._$AB=e,this._$AM=n,this.options=o,this._$Cv=o?.isConnected??!0}get parentNode(){let t=this._$AA.parentNode,e=this._$AM;return e!==void 0&&t?.nodeType===11&&(t=e.parentNode),t}get startNode(){return this._$AA}get endNode(){return this._$AB}_$AI(t,e=this){t=Y(this,t,e),we(t)?t===h||t==null||t===""?(this._$AH!==h&&this._$AR(),this._$AH=h):t!==this._$AH&&t!==Z&&this._(t):t._$litType$!==void 0?this.$(t):t.nodeType!==void 0?this.T(t):hs(t)?this.k(t):this._(t)}O(t){return this._$AA.parentNode.insertBefore(t,this._$AB)}T(t){this._$AH!==t&&(this._$AR(),this._$AH=this.O(t))}_(t){this._$AH!==h&&we(this._$AH)?this._$AA.nextSibling.data=t:this.T(K.createTextNode(t)),this._$AH=t}$(t){let{values:e,_$litType$:n}=t,o=typeof n=="number"?this._$AC(t):(n.el===void 0&&(n.el=ve.createElement(_s(n.h,n.h[0]),this.options)),n);if(this._$AH?._$AD===o)this._$AH.p(e);else{let r=new ze(o,this),i=r.u(this.options);r.p(e),this.T(i),this._$AH=r}}_$AC(t){let e=us.get(t.strings);return e===void 0&&us.set(t.strings,e=new ve(t)),e}k(t){$t(this._$AH)||(this._$AH=[],this._$AR());let e=this._$AH,n,o=0;for(let r of t)o===e.length?e.push(n=new s(this.O(ye()),this.O(ye()),this,this.options)):n=e[o],n._$AI(r),o++;o<e.length&&(this._$AR(n&&n._$AB.nextSibling,o),e.length=o)}_$AR(t=this._$AA.nextSibling,e){for(this._$AP?.(!1,!0,e);t!==this._$AB;){let n=is(t).nextSibling;is(t).remove(),t=n}}setConnected(t){this._$AM===void 0&&(this._$Cv=t,this._$AP?.(t))}},J=class{get tagName(){return this.element.tagName}get _$AU(){return this._$AM._$AU}constructor(t,e,n,o,r){this.type=1,this._$AH=h,this._$AN=void 0,this.element=t,this.name=e,this._$AM=o,this.options=r,n.length>2||n[0]!==""||n[1]!==""?(this._$AH=Array(n.length-1).fill(new String),this.strings=n):this._$AH=h}_$AI(t,e=this,n,o){let r=this.strings,i=!1;if(r===void 0)t=Y(this,t,e,0),i=!we(t)||t!==this._$AH&&t!==Z,i&&(this._$AH=t);else{let a=t,l,c;for(t=r[0],l=0;l<r.length-1;l++)c=Y(this,a[n+l],e,l),c===Z&&(c=this._$AH[l]),i||=!we(c)||c!==this._$AH[l],c===h?t=h:t!==h&&(t+=(c??"")+r[l+1]),this._$AH[l]=c}i&&!o&&this.j(t)}j(t){t===h?this.element.removeAttribute(this.name):this.element.setAttribute(this.name,t??"")}},Le=class extends J{constructor(){super(...arguments),this.type=3}j(t){this.element[this.name]=t===h?void 0:t}},Ie=class extends J{constructor(){super(...arguments),this.type=4}j(t){this.element.toggleAttribute(this.name,!!t&&t!==h)}},He=class extends J{constructor(t,e,n,o,r){super(t,e,n,o,r),this.type=5}_$AI(t,e=this){if((t=Y(this,t,e,0)??h)===Z)return;let n=this._$AH,o=t===h&&n!==h||t.capture!==n.capture||t.once!==n.once||t.passive!==n.passive,r=t!==h&&(n===h||o);o&&this.element.removeEventListener(this.name,this,n),r&&this.element.addEventListener(this.name,this,t),this._$AH=t}handleEvent(t){typeof this._$AH=="function"?this._$AH.call(this.options?.host??this.element,t):this._$AH.handleEvent(t)}},Ne=class{constructor(t,e,n){this.element=t,this.type=6,this._$AN=void 0,this._$AM=e,this.options=n}get _$AU(){return this._$AM._$AU}_$AI(t){Y(this,t)}},gs={M:xt,P:W,A:kt,C:1,L:fs,R:ze,D:hs,V:Y,I:se,H:J,N:Ie,U:He,B:Le,F:Ne},Wn=bt.litHtmlPolyfillSupport;Wn?.(ve,se),(bt.litHtmlVersions??=[]).push("3.3.3");var ys=(s,t,e)=>{let n=e?.renderBefore??t,o=n._$litPart$;if(o===void 0){let r=e?.renderBefore??null;n._$litPart$=o=new se(t.insertBefore(ye(),r),r,void 0,e??{})}return o._$AI(s),o};var St=globalThis,L=class extends M{constructor(){super(...arguments),this.renderOptions={host:this},this._$Do=void 0}createRenderRoot(){let t=super.createRenderRoot();return this.renderOptions.renderBefore??=t.firstChild,t}update(t){let e=this.render();this.hasUpdated||(this.renderOptions.isConnected=this.isConnected),super.update(t),this._$Do=ys(e,this.renderRoot,this.renderOptions)}connectedCallback(){super.connectedCallback(),this._$Do?.setConnected(!0)}disconnectedCallback(){super.disconnectedCallback(),this._$Do?.setConnected(!1)}render(){return Z}};L._$litElement$=!0,L.finalized=!0,St.litElementHydrateSupport?.({LitElement:L});var On=St.litElementPolyfillSupport;On?.({LitElement:L});(St.litElementVersions??=[]).push("4.2.2");var ws={tf_day:"1T",tf_week:"1W",tf_month:"1M",tf_six_month:"6M",tf_year:"1J",aria_timeframe:"Zeitraum",aria_currency:"W\xE4hrung",search_placeholder:"Name, Symbol oder ISIN",search_none:"Kein Wallet passt zu \u201E{query}\u201C.",aria_search:"Wallets durchsuchen",aria_search_clear:"Suche leeren",return_day:"Rendite \xFCber 1 Tag",return_week:"Rendite \xFCber 1 Woche",return_month:"Rendite \xFCber 1 Monat",return_six_month:"Rendite \xFCber 6 Monate",return_year:"Rendite \xFCber 1 Jahr",value_line:"Gesamtwert, {start} \u2013 heute",value_line_day:"Gesamtwert, letzte 24 Stunden",cash:"Bargeld",cash_plus:"Cash Plus",staked:"{share} im Staking",show_all:"Alle anzeigen ({count})",show_less:"Weniger anzeigen",detail_price:"Aktueller Preis",detail_staked:"Im Staking",detail_staking_apr:"Staking-APR",detail_average_buy_price:"\xD8 Kaufpreis",detail_invested:"Investiert",detail_return_24h:"Rendite (24 h)",detail_total_return:"Gesamtrendite",detail_staking:"Staking",detail_rewards_net:"Verdient (netto)",detail_rewards_value:"Heutiger Wert",detail_payouts:"Gutschriften",detail_payouts_value:"{count} \xB7 zuletzt {date}",shares_one:"St\xFCck",shares_other:"St\xFCck",assets_missing_one:"Dazu geh\xF6rt ein gew\xE4hltes Asset, das es gerade nicht gibt. Es bleibt gespeichert und gilt wieder, sobald es wieder da ist.",assets_missing_other:"Dazu geh\xF6ren {count} gew\xE4hlte Assets, die es gerade nicht gibt. Sie bleiben gespeichert und gelten wieder, sobald sie wieder da sind.",eye_hide:"Betr\xE4ge verbergen",eye_show:"Betr\xE4ge anzeigen",change_since:"\xC4nderung seit {date}",ecb_footer:"Preise in {currency}: Bitpandas Euro-Preise, umgerechnet zum EZB-Referenzkurs vom {date}. Die Prozente und Betr\xE4ge in {currency} enthalten deshalb auch die Bewegung des Wechselkurses.",empty_portfolio:"Richte das Bitpanda Portfolio ein oder aktiviere es, dann erscheint es hier.",empty_wallets:"Noch keine Wallets.",empty_selection_wallets:"Keine Wallets in der Auswahl dieser Karte.",empty_selection_assets:"Keine Assets in der Auswahl dieser Karte.",empty_price_tracker:"Richte den Bitpanda Price Tracker ein oder aktiviere ihn und f\xFCge Assets hinzu, dann erscheinen sie hier.",picker_portfolio:"Gesamtwert und Rendite mit Verlauf, Bargeld und Cash Plus, Verteilung und deine Wallets; jeder Teil l\xE4sst sich ausblenden.",picker_price_tracker:"Preise und \xC4nderungen deiner verfolgten Assets, je mit Verlauf, als Liste oder Kacheln.",invalid_option:"Ung\xFCltiger Wert f\xFCr \u201E{option}\u201C: {value}. Erlaubt: {allowed}.",allowed_text:"Text",allowed_assets:"eine Liste von Asset-IDs oder Ger\xE4te-IDs",allowed_groups:"eine Liste aus {values}",group_content:"Inhalt",group_wallets:"Wallets",group_assets:"Assets",group_appearance:"Darstellung",opt_title:"Titel",opt_title_help:"Leer lassen f\xFCr den grau angezeigten Namen",opt_timeframe:"Standard-Zeitraum",opt_timeframe_help:"Die Tasten 1T bis 1J auf der Karte wechseln ihn nur vor\xFCbergehend",tfo_day:"1 Tag",tfo_week:"1 Woche",tfo_month:"1 Monat",tfo_six_month:"6 Monate",tfo_year:"1 Jahr",opt_show_cash:"Bargeld und Cash Plus",opt_show_allocation:"Verteilung",opt_show_allocation_help:"Der farbige Balken mit den Anteilen der Asset-Gruppen und des Bargelds",opt_show_total:"Gesamtwert und Rendite",opt_show_total_help:"Die Zeitraum-Tasten bleiben, solange der Verlauf gezeigt wird",opt_show_line:"Verlauf des Gesamtwerts",opt_show_wallets:"Wallets",opt_group_wallets:"Wallets in Asset-Gruppen",opt_show_search:"Suchfeld",opt_show_search_help:"Findet Wallets nach Name, Symbol oder ISIN",opt_sort:"Sortieren nach",sort_value:"Wert",sort_return:"Rendite seit Kauf",sort_name:"Name",sort_selection:"Reihenfolge wie gew\xE4hlt",sort_change_desc:"\xC4nderung, h\xF6chste zuerst",sort_change_asc:"\xC4nderung, niedrigste zuerst",opt_sort_help_tracker:"\u201EReihenfolge wie gew\xE4hlt\u201C gilt nur mit \u201ENur die gew\xE4hlten\u201C Assets, sonst nach Name",opt_group_selection:"Angezeigte Asset-Gruppen",opt_group_selection_help:"Gilt nur f\xFCr die Wallets; Gesamtwert, Bargeld, Cash Plus und Verteilung zeigen immer das ganze Portfolio",opt_groups:"Asset-Gruppen w\xE4hlen",opt_asset_selection:"Angezeigte Assets",opt_asset_selection_wallets:"Angezeigte Wallets",sel_all:"Alle",sel_all_except:"Alle au\xDFer den gew\xE4hlten",sel_only:"Nur die gew\xE4hlten",opt_assets:"Assets w\xE4hlen",opt_assets_wallets:"Wallets w\xE4hlen",opt_assets_help:"Ein Asset aus einer ausgeblendeten Asset-Gruppe bleibt verborgen, auch wenn es hier gew\xE4hlt ist",opt_assets_help_wallets:"Ein Wallet aus einer ausgeblendeten Asset-Gruppe bleibt verborgen, auch wenn es hier gew\xE4hlt ist",opt_hide_amounts:"Betr\xE4ge zun\xE4chst verbergen",opt_hide_amounts_help:"Prozente bleiben sichtbar; das Auge oben auf der Karte zeigt die Betr\xE4ge nur vor\xFCbergehend",opt_limit:"Assets vor \u201EAlle anzeigen\u201C",opt_limit_wallets:"Wallets vor \u201EAlle anzeigen\u201C",opt_limit_help:"0 zeigt alle Assets",opt_limit_help_wallets:"Nur wenn \u201EWallets in Asset-Gruppen\u201C aus ist; 0 zeigt alle",opt_layout:"Anzeigen als",layout_list:"Liste",layout_tiles:"Kacheln",opt_currency:"Standard-W\xE4hrung",opt_currency_help:"Die Tasten auf der Karte wechseln sie nur vor\xFCbergehend; weitere W\xE4hrungen \xFCber \u201EKonfigurieren\u201C beim Price Tracker"};var vs={tf_day:"1D",tf_week:"1W",tf_month:"1M",tf_six_month:"6M",tf_year:"1Y",aria_timeframe:"Timeframe",aria_currency:"Currency",search_placeholder:"Name, symbol or ISIN",search_none:"No wallet matches \u201C{query}\u201D.",aria_search:"Search wallets",aria_search_clear:"Clear search",return_day:"return over 1 day",return_week:"return over 1 week",return_month:"return over 1 month",return_six_month:"return over 6 months",return_year:"return over 1 year",value_line:"Total value, {start} \u2013 today",value_line_day:"Total value, last 24 hours",cash:"Cash",cash_plus:"Cash Plus",staked:"{share} staked",show_all:"Show all ({count})",show_less:"Show less",detail_price:"Current price",detail_staked:"Staked",detail_staking_apr:"Staking APR",detail_average_buy_price:"Average buy price",detail_invested:"Invested",detail_return_24h:"Return (24 h)",detail_total_return:"Total return",detail_staking:"Staking",detail_rewards_net:"Earned (net)",detail_rewards_value:"Value today",detail_payouts:"Payouts",detail_payouts_value:"{count} \xB7 last {date}",shares_one:"share",shares_other:"shares",assets_missing_one:"This includes a chosen asset that is not there right now. It stays saved and applies again once it is back.",assets_missing_other:"This includes {count} chosen assets that are not there right now. They stay saved and apply again once they are back.",eye_hide:"Hide amounts",eye_show:"Show amounts",change_since:"Change since {date}",ecb_footer:"Prices in {currency}: Bitpanda's EUR prices converted at the ECB reference rate of {date}. The percentages and amounts in {currency} therefore also include the exchange rate's move.",empty_portfolio:"Set up the Bitpanda Portfolio or enable it to see it here.",empty_wallets:"No wallets yet.",empty_selection_wallets:"No wallets in this card's selection.",empty_selection_assets:"No assets in this card's selection.",empty_price_tracker:"Set up the Bitpanda Price Tracker or enable it and add assets to it to see them here.",picker_portfolio:"Total value and return with a value line, Cash and Cash Plus, allocation and your wallets; each part can be left out.",picker_price_tracker:"Prices and changes of the assets you track, each with a line, as a list or tiles.",invalid_option:"Invalid value for \u201C{option}\u201D: {value}. Allowed: {allowed}.",allowed_text:"text",allowed_assets:"a list of asset IDs or device IDs",allowed_groups:"a list of {values}",group_content:"Content",group_wallets:"Wallets",group_assets:"Assets",group_appearance:"Appearance",opt_title:"Title",opt_title_help:"Leave empty for the name shown in grey",opt_timeframe:"Default timeframe",opt_timeframe_help:"The 1D to 1Y buttons on the card change it only temporarily",tfo_day:"1 day",tfo_week:"1 week",tfo_month:"1 month",tfo_six_month:"6 months",tfo_year:"1 year",opt_show_cash:"Cash and Cash Plus",opt_show_allocation:"Allocation bar",opt_show_allocation_help:"The coloured bar showing the share of each asset group and of cash",opt_show_total:"Total value and return",opt_show_total_help:"The timeframe buttons stay while the line is shown",opt_show_line:"Total value line",opt_show_wallets:"Wallets",opt_group_wallets:"Wallets in asset groups",opt_show_search:"Search field",opt_show_search_help:"Finds wallets by name, symbol or ISIN",opt_sort:"Sort by",sort_value:"Value",sort_return:"Return since purchase",sort_name:"Name",sort_selection:"Order as chosen",sort_change_desc:"Change, highest first",sort_change_asc:"Change, lowest first",opt_sort_help_tracker:"\u201COrder as chosen\u201D applies only when assets are set to \u201COnly the ones chosen\u201D; otherwise by name",opt_group_selection:"Asset groups shown",opt_group_selection_help:"Applies to the wallets only; total value, Cash, Cash Plus and allocation always show the whole portfolio",opt_groups:"Choose asset groups",opt_asset_selection:"Assets shown",opt_asset_selection_wallets:"Wallets shown",sel_all:"All",sel_all_except:"All except the ones chosen",sel_only:"Only the ones chosen",opt_assets:"Choose assets",opt_assets_wallets:"Choose wallets",opt_assets_help:"An asset from a hidden asset group stays hidden, even when chosen here",opt_assets_help_wallets:"A wallet from a hidden asset group stays hidden, even when chosen here",opt_hide_amounts:"Hide amounts initially",opt_hide_amounts_help:"Percentages stay visible; the eye at the top of the card shows the amounts only temporarily",opt_limit:"Assets before \u201CShow all\u201D",opt_limit_wallets:"Wallets before \u201CShow all\u201D",opt_limit_help:"0 shows every asset",opt_limit_help_wallets:"Only while \u201CWallets in asset groups\u201D is off; 0 shows all",opt_layout:"Show as",layout_list:"List",layout_tiles:"Tiles",opt_currency:"Default currency",opt_currency_help:"The buttons on the card change it only temporarily; more currencies via \u201CConfigure\u201D on the Price Tracker"};var bs={tf_day:"1D",tf_week:"1S",tf_month:"1M",tf_six_month:"6M",tf_year:"1A",aria_timeframe:"Periodo",aria_currency:"Moneda",search_placeholder:"Nombre, s\xEDmbolo o ISIN",search_none:"Ning\xFAn wallet coincide con \xAB{query}\xBB.",aria_search:"Buscar wallets",aria_search_clear:"Borrar b\xFAsqueda",return_day:"rentabilidad en 1 d\xEDa",return_week:"rentabilidad en 1 semana",return_month:"rentabilidad en 1 mes",return_six_month:"rentabilidad en 6 meses",return_year:"rentabilidad en 1 a\xF1o",value_line:"Valor total, {start} \u2013 hoy",value_line_day:"Valor total, \xFAltimas 24 horas",cash:"Efectivo",cash_plus:"Cash Plus",staked:"{share} en staking",show_all:"Mostrar todo ({count})",show_less:"Mostrar menos",detail_price:"Precio actual",detail_staked:"En staking",detail_staking_apr:"APR de staking",detail_average_buy_price:"Precio medio de compra",detail_invested:"Importe invertido",detail_return_24h:"Rentabilidad (24 h)",detail_total_return:"Rentabilidad total",detail_staking:"Staking",detail_rewards_net:"Ganado (neto)",detail_rewards_value:"Valor hoy",detail_payouts:"Pagos",detail_payouts_value:"{count} \xB7 \xFAltimo el {date}",shares_one:"t\xEDtulo",shares_other:"t\xEDtulos",shares_many:"t\xEDtulos",assets_missing_one:"Incluye un activo elegido que ahora mismo no existe. Se queda guardado y vuelve a aplicarse en cuanto vuelva.",assets_missing_many:"Incluye {count} activos elegidos que ahora mismo no existen. Se quedan guardados y vuelven a aplicarse en cuanto vuelvan.",assets_missing_other:"Incluye {count} activos elegidos que ahora mismo no existen. Se quedan guardados y vuelven a aplicarse en cuanto vuelvan.",eye_hide:"Ocultar importes",eye_show:"Mostrar importes",change_since:"Variaci\xF3n desde el {date}",ecb_footer:"Precios en {currency}: precios en EUR de Bitpanda convertidos al tipo de referencia del BCE del {date}. Los porcentajes y los importes en {currency} incluyen por tanto tambi\xE9n la variaci\xF3n del tipo de cambio.",empty_portfolio:"Configura el Bitpanda Portfolio o act\xEDvalo para verlo aqu\xED.",empty_wallets:"Todav\xEDa no hay wallets.",empty_selection_wallets:"Ning\xFAn wallet en la selecci\xF3n de esta tarjeta.",empty_selection_assets:"Ning\xFAn activo en la selecci\xF3n de esta tarjeta.",empty_price_tracker:"Configura el Bitpanda Price Tracker o act\xEDvalo y a\xF1ade activos para verlos aqu\xED.",picker_portfolio:"Valor total y rentabilidad con l\xEDnea, efectivo y Cash Plus, distribuci\xF3n y tus wallets; cada parte se puede ocultar.",picker_price_tracker:"Precios y cambios de los activos que sigues, cada uno con su l\xEDnea, en lista o en mosaicos.",invalid_option:"Valor no v\xE1lido para \xAB{option}\xBB: {value}. Permitidos: {allowed}.",allowed_text:"texto",allowed_assets:"una lista de ID de activo o ID de dispositivo",allowed_groups:"una lista de {values}",group_content:"Contenido",group_wallets:"Wallets",group_assets:"Activos",group_appearance:"Apariencia",opt_title:"T\xEDtulo",opt_title_help:"D\xE9jalo vac\xEDo para el nombre mostrado en gris",opt_timeframe:"Periodo predeterminado",opt_timeframe_help:"Los botones 1D a 1A de la tarjeta lo cambian solo temporalmente",tfo_day:"1 d\xEDa",tfo_week:"1 semana",tfo_month:"1 mes",tfo_six_month:"6 meses",tfo_year:"1 a\xF1o",opt_show_cash:"Efectivo y Cash Plus",opt_show_allocation:"Barra de distribuci\xF3n",opt_show_allocation_help:"La barra de colores con la proporci\xF3n de cada grupo de activos y del efectivo",opt_show_total:"Valor total y rentabilidad",opt_show_total_help:"Los botones de periodo se mantienen mientras se muestre la l\xEDnea",opt_show_line:"L\xEDnea del valor total",opt_show_wallets:"Wallets",opt_group_wallets:"Wallets en grupos de activos",opt_show_search:"Campo de b\xFAsqueda",opt_show_search_help:"Encuentra wallets por nombre, s\xEDmbolo o ISIN",opt_sort:"Ordenar por",sort_value:"Valor",sort_return:"Rentabilidad desde la compra",sort_name:"Nombre",sort_selection:"Orden de selecci\xF3n",sort_change_desc:"Cambio, mayor primero",sort_change_asc:"Cambio, menor primero",opt_sort_help_tracker:"\xABOrden de selecci\xF3n\xBB solo se aplica con \xABSolo los elegidos\xBB en los activos; si no, por nombre",opt_group_selection:"Grupos de activos mostrados",opt_group_selection_help:"Solo afecta a los wallets; el valor total, el efectivo, Cash Plus y la distribuci\xF3n muestran siempre toda la cartera",opt_groups:"Elegir grupos de activos",opt_asset_selection:"Activos mostrados",opt_asset_selection_wallets:"Wallets mostrados",sel_all:"Todos",sel_all_except:"Todos excepto los elegidos",sel_only:"Solo los elegidos",opt_assets:"Elegir activos",opt_assets_wallets:"Elegir wallets",opt_assets_help:"Un activo de un grupo de activos oculto sigue oculto, aunque se elija aqu\xED",opt_assets_help_wallets:"Un wallet de un grupo de activos oculto sigue oculto, aunque se elija aqu\xED",opt_hide_amounts:"Ocultar inicialmente los importes",opt_hide_amounts_help:"Los porcentajes siguen visibles; el ojo de la parte superior de la tarjeta muestra los importes solo temporalmente",opt_limit:"Activos antes de \xABMostrar todo\xBB",opt_limit_wallets:"Wallets antes de \xABMostrar todo\xBB",opt_limit_help:"0 muestra todos los activos",opt_limit_help_wallets:"Solo si \xABWallets en grupos de activos\xBB est\xE1 desactivado; 0 muestra todo",opt_layout:"Mostrar como",layout_list:"Lista",layout_tiles:"Mosaicos",opt_currency:"Moneda predeterminada",opt_currency_help:"Los botones de la tarjeta la cambian solo temporalmente; m\xE1s monedas con \xABConfigurar\xBB en el Price Tracker"};var xs={tf_day:"1J",tf_week:"1S",tf_month:"1M",tf_six_month:"6M",tf_year:"1A",aria_timeframe:"P\xE9riode",aria_currency:"Devise",search_placeholder:"Nom, symbole ou ISIN",search_none:"Aucun wallet ne correspond \xE0 \xAB\xA0{query}\xA0\xBB.",aria_search:"Rechercher des wallets",aria_search_clear:"Effacer la recherche",return_day:"rendement sur 1 jour",return_week:"rendement sur 1 semaine",return_month:"rendement sur 1 mois",return_six_month:"rendement sur 6 mois",return_year:"rendement sur 1 an",value_line:"Valeur totale, {start} \u2013 aujourd'hui",value_line_day:"Valeur totale, derni\xE8res 24 heures",cash:"Liquidit\xE9s",cash_plus:"Cash Plus",staked:"{share} en staking",show_all:"Tout afficher ({count})",show_less:"Afficher moins",detail_price:"Prix actuel",detail_staked:"En staking",detail_staking_apr:"APR du staking",detail_average_buy_price:"Prix d'achat moyen",detail_invested:"Montant investi",detail_return_24h:"Rendement (24\xA0h)",detail_total_return:"Rendement total",detail_staking:"Staking",detail_rewards_net:"Gagn\xE9 (net)",detail_rewards_value:"Valeur aujourd'hui",detail_payouts:"Versements",detail_payouts_value:"{count} \xB7 dernier le {date}",shares_one:"titre",shares_other:"titres",shares_many:"titres",assets_missing_one:"Cela inclut un actif choisi qui n'existe pas pour le moment. Il reste enregistr\xE9 et s'applique de nouveau d\xE8s qu'il revient.",assets_missing_many:"Cela inclut {count} actifs choisis qui n'existent pas pour le moment. Ils restent enregistr\xE9s et s'appliquent de nouveau d\xE8s qu'ils reviennent.",assets_missing_other:"Cela inclut {count} actifs choisis qui n'existent pas pour le moment. Ils restent enregistr\xE9s et s'appliquent de nouveau d\xE8s qu'ils reviennent.",eye_hide:"Masquer les montants",eye_show:"Afficher les montants",change_since:"Variation depuis le {date}",ecb_footer:"Prix en {currency}\xA0: prix en EUR de Bitpanda convertis au taux de r\xE9f\xE9rence de la BCE du {date}. Les pourcentages et les montants en {currency} incluent donc aussi la variation du taux de change.",empty_portfolio:"Configurez le Bitpanda Portfolio ou activez-le pour le voir ici.",empty_wallets:"Aucun wallet pour le moment.",empty_selection_wallets:"Aucun wallet dans la s\xE9lection de cette carte.",empty_selection_assets:"Aucun actif dans la s\xE9lection de cette carte.",empty_price_tracker:"Configurez le Bitpanda Price Tracker ou activez-le et ajoutez-y des actifs pour les voir ici.",picker_portfolio:"Valeur totale et rendement avec courbe, liquidit\xE9s et Cash Plus, r\xE9partition et vos wallets\xA0; chaque partie peut \xEAtre masqu\xE9e.",picker_price_tracker:"Prix et variations des actifs que vous suivez, chacun avec sa courbe, en liste ou en tuiles.",invalid_option:"Valeur non valide pour \xAB\xA0{option}\xA0\xBB\xA0: {value}. Valeurs possibles\xA0: {allowed}.",allowed_text:"texte",allowed_assets:"une liste d'ID d'actifs ou d'ID d'appareils",allowed_groups:"une liste d'\xE9l\xE9ments parmi {values}",group_content:"Contenu",group_wallets:"Wallets",group_assets:"Actifs",group_appearance:"Apparence",opt_title:"Titre",opt_title_help:"Laisser vide pour le nom affich\xE9 en gris",opt_timeframe:"P\xE9riode par d\xE9faut",opt_timeframe_help:"Les boutons 1J \xE0 1A de la carte ne la changent que temporairement",tfo_day:"1 jour",tfo_week:"1 semaine",tfo_month:"1 mois",tfo_six_month:"6 mois",tfo_year:"1 an",opt_show_cash:"Liquidit\xE9s et Cash Plus",opt_show_allocation:"Barre de r\xE9partition",opt_show_allocation_help:"La barre color\xE9e avec la part de chaque groupe d'actifs et des liquidit\xE9s",opt_show_total:"Valeur totale et rendement",opt_show_total_help:"Les boutons de p\xE9riode restent tant que la courbe est affich\xE9e",opt_show_line:"Courbe de la valeur totale",opt_show_wallets:"Wallets",opt_group_wallets:"Wallets par groupe d'actifs",opt_show_search:"Champ de recherche",opt_show_search_help:"Trouve les wallets par nom, symbole ou ISIN",opt_sort:"Trier par",sort_value:"Valeur",sort_return:"Rendement depuis l'achat",sort_name:"Nom",sort_selection:"Ordre de s\xE9lection",sort_change_desc:"Variation, la plus forte d'abord",sort_change_asc:"Variation, la plus faible d'abord",opt_sort_help_tracker:"\xAB\xA0Ordre de s\xE9lection\xA0\xBB ne s'applique qu'avec \xAB\xA0Seulement ceux choisis\xA0\xBB pour les actifs\xA0; sinon, tri par nom",opt_group_selection:"Groupes d'actifs affich\xE9s",opt_group_selection_help:"S'applique seulement aux wallets\xA0; la valeur totale, les liquidit\xE9s, Cash Plus et la r\xE9partition portent toujours sur l'ensemble du portefeuille",opt_groups:"Choisir les groupes d'actifs",opt_asset_selection:"Actifs affich\xE9s",opt_asset_selection_wallets:"Wallets affich\xE9s",sel_all:"Tous",sel_all_except:"Tous sauf ceux choisis",sel_only:"Seulement ceux choisis",opt_assets:"Choisir les actifs",opt_assets_wallets:"Choisir les wallets",opt_assets_help:"Un actif d'un groupe d'actifs masqu\xE9 reste masqu\xE9, m\xEAme s'il est choisi ici",opt_assets_help_wallets:"Un wallet d'un groupe d'actifs masqu\xE9 reste masqu\xE9, m\xEAme s'il est choisi ici",opt_hide_amounts:"Masquer initialement les montants",opt_hide_amounts_help:"Les pourcentages restent visibles\xA0; l'\u0153il en haut de la carte n'affiche les montants que temporairement",opt_limit:"Actifs avant \xAB\xA0Tout afficher\xA0\xBB",opt_limit_wallets:"Wallets avant \xAB\xA0Tout afficher\xA0\xBB",opt_limit_help:"0 affiche tous les actifs",opt_limit_help_wallets:"Seulement si \xAB\xA0Wallets par groupe d'actifs\xA0\xBB est d\xE9sactiv\xE9\xA0; 0 affiche tout",opt_layout:"Afficher en",layout_list:"Liste",layout_tiles:"Tuiles",opt_currency:"Devise par d\xE9faut",opt_currency_help:"Les boutons de la carte ne la changent que temporairement\xA0; d'autres devises via \xAB\xA0Configurer\xA0\xBB dans le Price Tracker"};var ks={tf_day:"1G",tf_week:"1S",tf_month:"1M",tf_six_month:"6M",tf_year:"1A",aria_timeframe:"Periodo",aria_currency:"Valuta",search_placeholder:"Nome, simbolo o ISIN",search_none:"Nessun wallet corrisponde a \xAB{query}\xBB.",aria_search:"Cerca nei wallet",aria_search_clear:"Cancella ricerca",return_day:"rendimento su 1 giorno",return_week:"rendimento su 1 settimana",return_month:"rendimento su 1 mese",return_six_month:"rendimento su 6 mesi",return_year:"rendimento su 1 anno",value_line:"Valore totale, {start} \u2013 oggi",value_line_day:"Valore totale, ultime 24 ore",cash:"Liquidit\xE0",cash_plus:"Cash Plus",staked:"{share} in staking",show_all:"Mostra tutto ({count})",show_less:"Mostra meno",detail_price:"Prezzo attuale",detail_staked:"In staking",detail_staking_apr:"APR dello staking",detail_average_buy_price:"Prezzo medio di acquisto",detail_invested:"Importo investito",detail_return_24h:"Rendimento (24 h)",detail_total_return:"Rendimento totale",detail_staking:"Staking",detail_rewards_net:"Guadagnato (netto)",detail_rewards_value:"Valore oggi",detail_payouts:"Accrediti",detail_payouts_value:"{count} \xB7 ultimo il {date}",shares_one:"pezzo",shares_other:"pezzi",shares_many:"pezzi",assets_missing_one:"Include un asset scelto che al momento non c'\xE8. Resta salvato e torna a valere appena \xE8 di nuovo disponibile.",assets_missing_many:"Include {count} asset scelti che al momento non ci sono. Restano salvati e tornano a valere appena sono di nuovo disponibili.",assets_missing_other:"Include {count} asset scelti che al momento non ci sono. Restano salvati e tornano a valere appena sono di nuovo disponibili.",eye_hide:"Nascondi gli importi",eye_show:"Mostra gli importi",change_since:"Variazione dal {date}",ecb_footer:"Prezzi in {currency}: prezzi in EUR di Bitpanda convertiti al tasso di riferimento BCE del {date}. Le percentuali e gli importi in {currency} includono quindi anche la variazione del tasso di cambio.",empty_portfolio:"Configura il Bitpanda Portfolio o attivalo per vederlo qui.",empty_wallets:"Ancora nessun wallet.",empty_selection_wallets:"Nessun wallet nella selezione di questa scheda.",empty_selection_assets:"Nessun asset nella selezione di questa scheda.",empty_price_tracker:"Configura il Bitpanda Price Tracker o attivalo e aggiungi degli asset per vederli qui.",picker_portfolio:"Valore totale e rendimento con linea, liquidit\xE0 e Cash Plus, ripartizione e i tuoi wallet; ogni parte si pu\xF2 nascondere.",picker_price_tracker:"Prezzi e variazioni degli asset che segui, ognuno con la sua linea, come elenco o riquadri.",invalid_option:"Valore non valido per \xAB{option}\xBB: {value}. Consentiti: {allowed}.",allowed_text:"testo",allowed_assets:"un elenco di ID asset o ID dispositivo",allowed_groups:"un elenco di valori tra {values}",group_content:"Contenuto",group_wallets:"Wallet",group_assets:"Asset",group_appearance:"Aspetto",opt_title:"Titolo",opt_title_help:"Lascia vuoto per il nome mostrato in grigio",opt_timeframe:"Periodo predefinito",opt_timeframe_help:"I pulsanti da 1G a 1A sulla scheda lo cambiano solo temporaneamente",tfo_day:"1 giorno",tfo_week:"1 settimana",tfo_month:"1 mese",tfo_six_month:"6 mesi",tfo_year:"1 anno",opt_show_cash:"Liquidit\xE0 e Cash Plus",opt_show_allocation:"Barra di ripartizione",opt_show_allocation_help:"La barra colorata con le quote dei gruppi di asset e della liquidit\xE0",opt_show_total:"Valore totale e rendimento",opt_show_total_help:"I pulsanti del periodo restano finch\xE9 \xE8 mostrata la linea",opt_show_line:"Linea del valore totale",opt_show_wallets:"Wallet",opt_group_wallets:"Wallet in gruppi di asset",opt_show_search:"Campo di ricerca",opt_show_search_help:"Trova i wallet per nome, simbolo o ISIN",opt_sort:"Ordina per",sort_value:"Valore",sort_return:"Rendimento dall'acquisto",sort_name:"Nome",sort_selection:"Ordine di selezione",sort_change_desc:"Variazione, maggiore prima",sort_change_asc:"Variazione, minore prima",opt_sort_help_tracker:"\xABOrdine di selezione\xBB vale solo con \xABSolo quelli scelti\xBB per gli asset; altrimenti per nome",opt_group_selection:"Gruppi di asset mostrati",opt_group_selection_help:"Vale solo per i wallet; valore totale, liquidit\xE0, Cash Plus e ripartizione mostrano sempre l'intero portafoglio",opt_groups:"Scegli i gruppi di asset",opt_asset_selection:"Asset mostrati",opt_asset_selection_wallets:"Wallet mostrati",sel_all:"Tutti",sel_all_except:"Tutti tranne quelli scelti",sel_only:"Solo quelli scelti",opt_assets:"Scegli gli asset",opt_assets_wallets:"Scegli i wallet",opt_assets_help:"Un asset di un gruppo di asset nascosto resta nascosto, anche se scelto qui",opt_assets_help_wallets:"Un wallet di un gruppo di asset nascosto resta nascosto, anche se scelto qui",opt_hide_amounts:"Nascondi inizialmente gli importi",opt_hide_amounts_help:"Le percentuali restano visibili; l'occhio in alto nella scheda mostra gli importi solo temporaneamente",opt_limit:"Asset prima di \xABMostra tutto\xBB",opt_limit_wallets:"Wallet prima di \xABMostra tutto\xBB",opt_limit_help:"0 mostra tutti gli asset",opt_limit_help_wallets:"Solo se \xABWallet in gruppi di asset\xBB \xE8 disattivato; 0 mostra tutto",opt_layout:"Mostra come",layout_list:"Elenco",layout_tiles:"Riquadri",opt_currency:"Valuta predefinita",opt_currency_help:"I pulsanti sulla scheda la cambiano solo temporaneamente; altre valute tramite \xABConfigura\xBB nel Price Tracker"};var $s={tf_day:"1D",tf_week:"1W",tf_month:"1M",tf_six_month:"6M",tf_year:"1J",aria_timeframe:"Periode",aria_currency:"Valuta",search_placeholder:"Naam, symbool of ISIN",search_none:"Geen wallet past bij \u2018{query}\u2019.",aria_search:"Wallets doorzoeken",aria_search_clear:"Zoekopdracht wissen",return_day:"rendement over 1 dag",return_week:"rendement over 1 week",return_month:"rendement over 1 maand",return_six_month:"rendement over 6 maanden",return_year:"rendement over 1 jaar",value_line:"Totale waarde, {start} \u2013 vandaag",value_line_day:"Totale waarde, laatste 24 uur",cash:"Contanten",cash_plus:"Cash Plus",staked:"{share} in staking",show_all:"Alles tonen ({count})",show_less:"Minder tonen",detail_price:"Huidige prijs",detail_staked:"In staking",detail_staking_apr:"Staking-APR",detail_average_buy_price:"Gemiddelde aankoopprijs",detail_invested:"Ge\xEFnvesteerd",detail_return_24h:"Rendement (24 uur)",detail_total_return:"Totaalrendement",detail_staking:"Staking",detail_rewards_net:"Verdiend (netto)",detail_rewards_value:"Waarde vandaag",detail_payouts:"Uitbetalingen",detail_payouts_value:"{count} \xB7 laatste {date}",shares_one:"stuk",shares_other:"stuks",assets_missing_one:"Hieronder valt een gekozen asset die er nu niet is. Die blijft bewaard en geldt weer zodra die terug is.",assets_missing_other:"Hieronder vallen {count} gekozen assets die er nu niet zijn. Ze blijven bewaard en gelden weer zodra ze terug zijn.",eye_hide:"Bedragen verbergen",eye_show:"Bedragen tonen",change_since:"Verandering sinds {date}",ecb_footer:"Prijzen in {currency}: de EUR-prijzen van Bitpanda, omgerekend tegen de ECB-referentiekoers van {date}. De percentages en bedragen in {currency} bevatten daardoor ook de beweging van de wisselkoers.",empty_portfolio:"Stel het Bitpanda Portfolio in of schakel het in om het hier te zien.",empty_wallets:"Nog geen wallets.",empty_selection_wallets:"Geen wallets in de selectie van deze kaart.",empty_selection_assets:"Geen assets in de selectie van deze kaart.",empty_price_tracker:"Stel de Bitpanda Price Tracker in of schakel hem in en voeg er assets aan toe om ze hier te zien.",picker_portfolio:"Totale waarde en rendement met een lijn, contanten en Cash Plus, verdeling en je wallets; elk deel kan worden verborgen.",picker_price_tracker:"Prijzen en veranderingen van de assets die je volgt, elk met een lijn, als lijst of tegels.",invalid_option:"Ongeldige waarde voor \u2018{option}\u2019: {value}. Toegestaan: {allowed}.",allowed_text:"tekst",allowed_assets:"een lijst met asset-ID's of apparaat-ID's",allowed_groups:"een lijst met waarden uit {values}",group_content:"Inhoud",group_wallets:"Wallets",group_assets:"Assets",group_appearance:"Uiterlijk",opt_title:"Titel",opt_title_help:"Leeg laten voor de grijs getoonde naam",opt_timeframe:"Standaardperiode",opt_timeframe_help:"De knoppen 1D tot 1J op de kaart wijzigen die alleen tijdelijk",tfo_day:"1 dag",tfo_week:"1 week",tfo_month:"1 maand",tfo_six_month:"6 maanden",tfo_year:"1 jaar",opt_show_cash:"Contanten en Cash Plus",opt_show_allocation:"Verdelingsbalk",opt_show_allocation_help:"De gekleurde balk met het aandeel van elke assetgroep en van de contanten",opt_show_total:"Totale waarde en rendement",opt_show_total_help:"De periodeknoppen blijven zolang de lijn wordt getoond",opt_show_line:"Lijn van de totale waarde",opt_show_wallets:"Wallets",opt_group_wallets:"Wallets in assetgroepen",opt_show_search:"Zoekveld",opt_show_search_help:"Vindt wallets op naam, symbool of ISIN",opt_sort:"Sorteren op",sort_value:"Waarde",sort_return:"Rendement sinds aankoop",sort_name:"Naam",sort_selection:"Volgorde zoals gekozen",sort_change_desc:"Verandering, hoogste eerst",sort_change_asc:"Verandering, laagste eerst",opt_sort_help_tracker:"\u2018Volgorde zoals gekozen\u2019 geldt alleen bij \u2018Alleen de gekozen\u2019 assets, anders op naam",opt_group_selection:"Getoonde assetgroepen",opt_group_selection_help:"Geldt alleen voor de wallets; totale waarde, contanten, Cash Plus en verdeling tonen altijd het hele portfolio",opt_groups:"Assetgroepen kiezen",opt_asset_selection:"Getoonde assets",opt_asset_selection_wallets:"Getoonde wallets",sel_all:"Alle",sel_all_except:"Alle behalve de gekozen",sel_only:"Alleen de gekozen",opt_assets:"Assets kiezen",opt_assets_wallets:"Wallets kiezen",opt_assets_help:"Een asset uit een verborgen assetgroep blijft verborgen, ook als die hier is gekozen",opt_assets_help_wallets:"Een wallet uit een verborgen assetgroep blijft verborgen, ook als die hier is gekozen",opt_hide_amounts:"Bedragen aanvankelijk verbergen",opt_hide_amounts_help:"Percentages blijven zichtbaar; het oog bovenaan de kaart toont de bedragen alleen tijdelijk",opt_limit:"Assets v\xF3\xF3r \u2018Alles tonen\u2019",opt_limit_wallets:"Wallets v\xF3\xF3r \u2018Alles tonen\u2019",opt_limit_help:"0 toont alle assets",opt_limit_help_wallets:"Alleen als \u2018Wallets in assetgroepen\u2019 uit staat; 0 toont alles",opt_layout:"Weergeven als",layout_list:"Lijst",layout_tiles:"Tegels",opt_currency:"Standaardvaluta",opt_currency_help:"De knoppen op de kaart wijzigen die alleen tijdelijk; meer valuta via \u2018Configureren\u2019 bij de Price Tracker"};var As={tf_day:"1D",tf_week:"1T",tf_month:"1M",tf_six_month:"6M",tf_year:"1R",aria_timeframe:"Okres",aria_currency:"Waluta",search_placeholder:"Nazwa, symbol lub ISIN",search_none:"\u017Baden portfel nie pasuje do \u201E{query}\u201D.",aria_search:"Szukaj portfeli",aria_search_clear:"Wyczy\u015B\u0107 wyszukiwanie",return_day:"stopa zwrotu za 1 dzie\u0144",return_week:"stopa zwrotu za 1 tydzie\u0144",return_month:"stopa zwrotu za 1 miesi\u0105c",return_six_month:"stopa zwrotu za 6 miesi\u0119cy",return_year:"stopa zwrotu za 1 rok",value_line:"Warto\u015B\u0107 ca\u0142kowita, {start} \u2013 dzi\u015B",value_line_day:"Warto\u015B\u0107 ca\u0142kowita, ostatnie 24 godziny",cash:"Got\xF3wka",cash_plus:"Cash Plus",staked:"{share} w stakingu",show_all:"Poka\u017C wszystkie ({count})",show_less:"Poka\u017C mniej",detail_price:"Aktualna cena",detail_staked:"W stakingu",detail_staking_apr:"APR stakingu",detail_average_buy_price:"\u015Arednia cena zakupu",detail_invested:"Zainwestowano",detail_return_24h:"Zwrot (24 h)",detail_total_return:"Ca\u0142kowity zwrot",detail_staking:"Staking",detail_rewards_net:"Zarobiono (netto)",detail_rewards_value:"Warto\u015B\u0107 dzi\u015B",detail_payouts:"Naliczenia",detail_payouts_value:"{count} \xB7 ostatnio {date}",shares_one:"sztuka",shares_other:"sztuki",shares_few:"sztuki",shares_many:"sztuk",assets_missing_one:"Obejmuje to jedno wybrane aktywo, kt\xF3rego teraz nie ma. Pozostaje zapisane i zn\xF3w obowi\u0105zuje, gdy wr\xF3ci.",assets_missing_few:"Obejmuje to {count} wybrane aktywa, kt\xF3rych teraz nie ma. Pozostaj\u0105 zapisane i zn\xF3w obowi\u0105zuj\u0105, gdy wr\xF3c\u0105.",assets_missing_many:"Obejmuje to {count} wybranych aktyw\xF3w, kt\xF3rych teraz nie ma. Pozostaj\u0105 zapisane i zn\xF3w obowi\u0105zuj\u0105, gdy wr\xF3c\u0105.",assets_missing_other:"Obejmuje to {count} wybranego aktywa, kt\xF3rego teraz nie ma. Pozostaje zapisane i zn\xF3w obowi\u0105zuje, gdy wr\xF3ci.",eye_hide:"Ukryj kwoty",eye_show:"Poka\u017C kwoty",change_since:"Zmiana od {date}",ecb_footer:"Ceny w {currency}: ceny Bitpandy w EUR przeliczone po kursie referencyjnym EBC z {date}. Warto\u015Bci procentowe i kwoty w {currency} obejmuj\u0105 wi\u0119c r\xF3wnie\u017C zmian\u0119 kursu walutowego.",empty_portfolio:"Skonfiguruj Bitpanda Portfolio lub je w\u0142\u0105cz, aby zobaczy\u0107 je tutaj.",empty_wallets:"Brak portfeli.",empty_selection_wallets:"Brak portfeli w wyborze tej karty.",empty_selection_assets:"Brak aktyw\xF3w w wyborze tej karty.",empty_price_tracker:"Skonfiguruj Bitpanda Price Tracker lub go w\u0142\u0105cz i dodaj aktywa, aby zobaczy\u0107 je tutaj.",picker_portfolio:"Warto\u015B\u0107 ca\u0142kowita i stopa zwrotu z wykresem, got\xF3wka i Cash Plus, alokacja oraz twoje portfele; ka\u017Cd\u0105 cz\u0119\u015B\u0107 mo\u017Cna ukry\u0107.",picker_price_tracker:"Ceny i zmiany \u015Bledzonych aktyw\xF3w, ka\u017Cde z wykresem, jako lista lub kafelki.",invalid_option:"Nieprawid\u0142owa warto\u015B\u0107 dla \u201E{option}\u201D: {value}. Dozwolone: {allowed}.",allowed_text:"tekst",allowed_assets:"lista identyfikator\xF3w aktyw\xF3w lub urz\u0105dze\u0144",allowed_groups:"lista warto\u015Bci spo\u015Br\xF3d {values}",group_content:"Zawarto\u015B\u0107",group_wallets:"Portfele",group_assets:"Aktywa",group_appearance:"Wygl\u0105d",opt_title:"Tytu\u0142",opt_title_help:"Pozostaw puste, aby u\u017Cy\u0107 nazwy pokazanej na szaro",opt_timeframe:"Domy\u015Blny okres",opt_timeframe_help:"Przyciski od 1D do 1R na karcie zmieniaj\u0105 go tylko tymczasowo",tfo_day:"1 dzie\u0144",tfo_week:"1 tydzie\u0144",tfo_month:"1 miesi\u0105c",tfo_six_month:"6 miesi\u0119cy",tfo_year:"1 rok",opt_show_cash:"Got\xF3wka i Cash Plus",opt_show_allocation:"Pasek alokacji",opt_show_allocation_help:"Kolorowy pasek pokazuj\u0105cy udzia\u0142 grup aktyw\xF3w i got\xF3wki",opt_show_total:"Warto\u015B\u0107 ca\u0142kowita i stopa zwrotu",opt_show_total_help:"Przyciski okresu pozostaj\u0105, dop\xF3ki wy\u015Bwietlany jest wykres",opt_show_line:"Wykres warto\u015Bci ca\u0142kowitej",opt_show_wallets:"Portfele",opt_group_wallets:"Portfele w grupach aktyw\xF3w",opt_show_search:"Pole wyszukiwania",opt_show_search_help:"Znajduje portfele po nazwie, symbolu lub ISIN",opt_sort:"Sortuj wed\u0142ug",sort_value:"Warto\u015B\u0107",sort_return:"Stopa zwrotu od zakupu",sort_name:"Nazwa",sort_selection:"Kolejno\u015B\u0107 wyboru",sort_change_desc:"Zmiana, najwy\u017Csza najpierw",sort_change_asc:"Zmiana, najni\u017Csza najpierw",opt_sort_help_tracker:"\u201EKolejno\u015B\u0107 wyboru\u201D dzia\u0142a tylko przy opcji \u201ETylko wybrane\u201D dla aktyw\xF3w; w przeciwnym razie wed\u0142ug nazwy",opt_group_selection:"Wy\u015Bwietlane grupy aktyw\xF3w",opt_group_selection_help:"Dotyczy tylko portfeli; warto\u015B\u0107 ca\u0142kowita, got\xF3wka, Cash Plus i alokacja zawsze pokazuj\u0105 ca\u0142e portfolio",opt_groups:"Wybierz grupy aktyw\xF3w",opt_asset_selection:"Wy\u015Bwietlane aktywa",opt_asset_selection_wallets:"Wy\u015Bwietlane portfele",sel_all:"Wszystkie",sel_all_except:"Wszystkie opr\xF3cz wybranych",sel_only:"Tylko wybrane",opt_assets:"Wybierz aktywa",opt_assets_wallets:"Wybierz portfele",opt_assets_help:"Aktywo z ukrytej grupy aktyw\xF3w pozostaje ukryte, nawet je\u015Bli wybrano je tutaj",opt_assets_help_wallets:"Portfel z ukrytej grupy aktyw\xF3w pozostaje ukryty, nawet je\u015Bli wybrano go tutaj",opt_hide_amounts:"Pocz\u0105tkowo ukrywaj kwoty",opt_hide_amounts_help:"Procenty pozostaj\u0105 widoczne; oko u g\xF3ry karty pokazuje kwoty tylko tymczasowo",opt_limit:"Aktywa przed \u201EPoka\u017C wszystkie\u201D",opt_limit_wallets:"Portfele przed \u201EPoka\u017C wszystkie\u201D",opt_limit_help:"0 pokazuje wszystkie aktywa",opt_limit_help_wallets:"Tylko gdy opcja \u201EPortfele w grupach aktyw\xF3w\u201D jest wy\u0142\u0105czona; 0 pokazuje wszystkie",opt_layout:"Poka\u017C jako",layout_list:"Lista",layout_tiles:"Kafelki",opt_currency:"Domy\u015Blna waluta",opt_currency_help:"Przyciski na karcie zmieniaj\u0105 j\u0105 tylko tymczasowo; wi\u0119cej walut przez \u201EKonfiguruj\u201D w Price Trackerze"};var Ss={en:vs,de:ws,fr:xs,nl:$s,it:ks,es:bs,pl:As},Ts=s=>s in Ss,Cs="en",jn=s=>{let t=s.toLowerCase().replace(/[-_].*$/,"");return Ts(t)?t:"en"};function O(s){let t=s??document.querySelector("home-assistant")?.hass;return t?jn(t.locale.language):Cs}function Ps(s){return Ts(s.locale.language.toLowerCase().replace(/[-_].*$/,""))}function Me(s){Cs=O(s)}var Es=s=>Ss[O(s)];function u(s,t,e={}){return Es(s)[t].replace(/\{(\w+)\}/g,(n,o)=>o in e?String(e[o]):n)}function We(s,t,e,n={}){let o=new Intl.PluralRules(O(s),n).select(e);return Es(s)[`${t}_${o}`].replace("{count}",String(e))}async function Rs(s){await s.loadBackendTranslation("selector","bitpanda")}function Tt(s,t){return s.localize(`component.bitpanda.selector.asset_group.options.${t}`)||t}var F=["day","week","month","six_month","year"],I=["crypto","stock","etf","etc","index","metal","other"],j=["all","all_except","only"],zs=["EUR","CHF","CZK","DKK","GBP","HUF","NOK","PLN","RON","SEK","TRY","USD"],Oe=["value","return","name"];var je=["selection","name","change_desc","change_asc"],De=["list","tiles"];var E=s=>({allowed:()=>s.join(", "),check:t=>typeof t=="string"&&s.includes(t)}),D={allowed:()=>"true, false",check:s=>typeof s=="boolean"},Ls={allowed:()=>u(void 0,"allowed_text"),check:s=>typeof s=="string"},Ue={allowed:()=>"0, 1, 2, \u2026",check:s=>typeof s=="number"&&Number.isInteger(s)&&s>=0},Fe={allowed:()=>u(void 0,"allowed_assets"),check:s=>Array.isArray(s)&&s.every(t=>typeof t=="string")},Ve={allowed:()=>u(void 0,"allowed_groups",{values:I.join(", ")}),check:s=>Array.isArray(s)&&s.every(t=>I.includes(t))},Is={allowed:()=>"EUR, USD, \u2026",check:s=>typeof s=="string"&&/^[A-Z]{3}$/.test(s)};function Be(s,t){if(s===null||typeof s!="object"||Array.isArray(s))throw new Error(u(void 0,"invalid_option",{option:"type",value:JSON.stringify(s),allowed:"custom:\u2026"}));let e=Object.fromEntries(Object.entries(s).filter(([,n])=>n!==null));for(let[n,o]of Object.entries(t)){let r=e[n];if(r!==void 0&&!o.check(r))throw new Error(u(void 0,"invalid_option",{option:n,value:JSON.stringify(r),allowed:o.allowed()}))}return e}var oe=(s,t)=>({select:{mode:"dropdown",options:s.map(e=>({value:e,label:t(e)}))}}),Ct=s=>({name:"title",default:s,selector:{text:{}}}),Pt=()=>({name:"timeframe",selector:oe(F,s=>u(void 0,`tfo_${s}`))}),U=(s,t)=>({name:s,default:t,selector:{boolean:{}}}),Et=s=>({name:"limit",default:s,selector:{number:{min:0,max:100,mode:"box"}}}),Rt=s=>({name:"sort",selector:oe(s,t=>u(void 0,`sort_${t}`))});function qe(){return document.querySelector("home-assistant")?.hass}var Dn=3e3;async function Hs(s){if(!s)return{};let t;try{let n=(await Promise.race([s.callWS({type:"frontend/get_translations",language:s.language,category:"selector",integration:["bitpanda"]}),new Promise(r=>{t=setTimeout(()=>r(void 0),Dn)})]))?.resources??{},o={};for(let r of I){let i=n[`component.bitpanda.selector.asset_group.options.${r}`];typeof i=="string"&&i&&(o[r]=i)}return o}catch{return{}}finally{clearTimeout(t)}}var Ge=s=>s==="only"||s==="all_except",zt=(s,t)=>[{name:"group_selection",selector:oe(j,e=>u(void 0,`sel_${e}`))},...Ge(t)?[{name:"groups",selector:{select:{multiple:!0,mode:"dropdown",options:I.map(e=>({value:e,label:s[e]??e}))}}}]:[]],Lt=(s,t)=>[{name:"asset_selection",selector:oe(j,e=>u(void 0,`sel_${e}`))},...Ge(t)?[{name:"assets",selector:{device:{multiple:!0,filter:[{integration:"bitpanda",model:s}]}}}]:[]],be=()=>({type:"divider",name:""}),re=(s,t)=>({type:"expandable",name:"",flatten:!0,title:u(void 0,s),schema:t}),Un={title:"opt_title",timeframe:"opt_timeframe",show_total:"opt_show_total",show_graph:"opt_show_line",show_cash:"opt_show_cash",show_allocation:"opt_show_allocation",show_wallets:"opt_show_wallets",group_wallets:"opt_group_wallets",show_search:"opt_show_search",sort:"opt_sort",group_selection:"opt_group_selection",groups:"opt_groups",asset_selection:"opt_asset_selection",assets:"opt_assets",hide_amounts:"opt_hide_amounts",limit:"opt_limit",layout:"opt_layout",currency:"opt_currency"},Fn={title:"opt_title_help",timeframe:"opt_timeframe_help",show_total:"opt_show_total_help",show_allocation:"opt_show_allocation_help",hide_amounts:"opt_hide_amounts_help",show_search:"opt_show_search_help",assets:"opt_assets_help",limit:"opt_limit_help",currency:"opt_currency_help"};function It(s){let t=Un[s.name];return t?u(void 0,t):void 0}function Ht(s){let t=Fn[s.name];return t?u(void 0,t):void 0}var Ke=_e`
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
`;var Ze={title:Ls},V=class extends L{constructor(){super(...arguments);this.timeframe="day";this.amountsHidden=!1;this.seriesRevision=0;this.watched=[]}static{this.properties={hass:{attribute:!1},config:{state:!0},timeframe:{state:!0},amountsHidden:{state:!0},seriesRevision:{state:!0}}}static{this.styles=Ke}setConfig(e){let n=this.validate(e),o=n;this.config=n,this.timeframe=o.timeframe??"day",this.amountsHidden=o.hide_amounts??!1}toggleAmounts(){this.amountsHidden=!this.amountsHidden}seriesArrived(){this.seriesRevision+=1}selectTimeframe(e){this.timeframe=e}shouldUpdate(e){if(e.size!==1||!e.has("hass"))return!0;let n=e.get("hass"),o=this.hass;return!n||!o||n.entities!==o.entities||n.devices!==o.devices||n.locale!==o.locale||n.localize!==o.localize?!0:this.watched.some(r=>n.states[r]!==o.states[r])}connectedCallback(){super.connectedCallback(),typeof ResizeObserver<"u"&&(this.resizer=new ResizeObserver(()=>this.fitLayout()),this.resizer.observe(this))}disconnectedCallback(){this.resizer?.disconnect(),this.resizer=void 0,super.disconnectedCallback()}updated(e){super.updated(e),this.remeasures(e)&&this.fitLayout()}fitLayout(){}widthMeter(){let e=this.getBoundingClientRect().width,n=e>0&&this.offsetWidth>0?e/this.offsetWidth:1;return(o,r=!1)=>{let i=r?[...o.getClientRects()].reduce((a,l)=>a+l.width,0):o.getBoundingClientRect().width;return Math.round(i/n*100)/100}}remeasures(e){return!0}willUpdate(e){let n=this.hass;if(!n)return;Me(n);let o=O(n);o!==this.categoryLanguage&&(this.categoryLanguage=o,Rs(n)),this.watched=this.watchedEntities()}getCardSize(){return 3}getGridOptions(){return{columns:12,min_columns:6}}};var Vn="bitpanda",Ns={return_day:"day",return_week:"week",return_month:"month",return_six_month:"six_month",return_year:"year"},Ms=s=>s.replace(/\s+/g,"").toLowerCase();function Bn(s,t){let e=(s??"").trim();return e&&Ms(e)!==Ms(t)?`${e} (${t})`:t}var Ws=new WeakMap;function qn(s){let t=Ws.get(s.entities);if(t)return t;let e=new Map;for(let n of Object.values(s.entities)){if(!n||n.platform!==Vn||!n.device_id)continue;let o=e.get(n.device_id)??[];o.push(n),e.set(n.device_id,o)}return Ws.set(s.entities,e),e}function Nt(s,t){let e=qn(s),n=[];for(let[o,r]of e){let i=s.devices[o];i?.model===t&&n.push([i,r])}return n}var X=s=>typeof s=="string"&&s!==""?s:void 0,Os=new Map,Gn=/ (Wallet|Price Tracker)$/;function Ds(s,t,e){let n=e.map(i=>s.states[i.entity_id]?.attributes).find(i=>i?.asset),o;if(n){let i=X(n.asset)??"",a=X(n.asset_isin),l=X(n.asset_category),c=X(n.asset_name);o={name:Bn(c,i),shortName:c??i,symbol:i,...a?{isin:a}:{},...l&&I.includes(l)?{category:l}:{}},Os.set(t.id,o)}else{let i=(X(t.name)??"").replace(Gn,"");o=Os.get(t.id)??{name:i,shortName:i,symbol:""}}let r=X(t.name_by_user);return{deviceId:t.id,assetId:t.serial_number??"",...o,...r?{name:r,shortName:r}:{}}}function Ye(s){let[t]=Nt(s,"Portfolio");if(!t)return;let[e,n]=t,o={deviceId:e.id,returns:{},wallets:[]};for(let r of n){let i=r.translation_key??"";i==="total_value"?o.totalValue=r.entity_id:i==="cash"?o.cash=r.entity_id:i==="cash_plus"?o.cashPlus=r.entity_id:i in Ns&&(o.returns[Ns[i]]=r.entity_id)}for(let[r,i]of Nt(s,"Wallet")){let a=Ds(s,r,i);for(let l of i)l.translation_key==="wallet"?a.available=l.entity_id:l.translation_key==="wallet_total"?a.total=l.entity_id:l.translation_key==="staking"&&(a.staking=l.entity_id);o.wallets.push(a)}return o}function ie(s){return Nt(s,"Price Tracker").map(([t,e])=>{let n={};for(let o of e){if(o.translation_key!=="price")continue;let r=X(s.states[o.entity_id]?.attributes.unit_of_measurement);r&&(n[r]=o.entity_id)}return{...Ds(s,t,e),prices:n}})}function xe(s){let t=new Set(s.flatMap(n=>Object.keys(n.prices))),e=[...t].filter(n=>n!=="EUR").sort();return t.has("EUR")?["EUR",...e]:e}function Je(s,t,e){if(t==="all")return[...s];let n=t==="only";return s.filter(o=>e.includes(o.category??"other")===n)}var js=(s,t)=>t===s.deviceId||t!==""&&t===s.assetId;function Xe(s,t,e){if(t==="all_except")return s.filter(n=>!e.some(o=>js(n,o)));if(t==="only"){let n=[];for(let o of e){let r=s.find(i=>js(i,o));r&&!n.includes(r)&&n.push(r)}return n}return[...s]}var Qe="bitpanda-portfolio-card-editor",et="bitpanda-price-tracker-card-editor",Kn=[["asset_selection","assets"],["group_selection","groups"]],Zn={timeframe:"day",sort:"value",group_selection:"all",asset_selection:"all"},Yn={layout:"list",timeframe:"day",currency:"EUR",sort:"name",group_selection:"all",asset_selection:"all"},Jn=/^[0-9a-f]{32}$/;function Us(s,t){return s?Object.values(s.devices).filter(e=>e!==void 0&&e.model===t&&(e.identifiers??[]).some(([n])=>n==="bitpanda")):[]}function Xn(s,t){return s?/[.!?…]$/.test(s)?`${s} ${t}`:`${s}. ${t}`:t}async function Qn(s=customElements,t=window,e=1e4){if(s.get("ha-form"))return;try{await(await(await t.loadCardHelpers?.())?.createCardElement({type:"entities",entities:[]}))?.constructor?.getConfigElement?.()}catch{}let n;await Promise.race([s.whenDefined("ha-form"),new Promise(o=>{n=setTimeout(o,e)})]),clearTimeout(n)}async function st(s){return await Qn(),customElements.get(Qe)||customElements.define(Qe,Mt),customElements.get(et)||customElements.define(et,Wt),document.createElement(s)}var tt=class extends L{constructor(){super(...arguments);this.names={};this.namesAsked=!1;this.heldBack={}}static{this.properties={hass:{attribute:!1},config:{state:!0},names:{state:!0}}}setConfig(e){this.config=e}chosenAssets(){let e=this.config?.assets,n=Us(this.hass,this.model),o=[],r=[];for(let i of Array.isArray(e)?e:[]){let a=n.find(l=>l.id===i||l.serial_number&&l.serial_number===i);a?o.includes(a.id)||o.push(a.id):!Jn.test(i)&&!r.includes(i)&&r.push(i)}return{devices:o,missing:r}}savedAssets(e){let n=Us(this.hass,this.model),o=[];for(let r of[...e.map(i=>n.find(a=>a.id===i)?.serial_number||i),...this.chosenAssets().missing])o.includes(r)||o.push(r);return o}willUpdate(e){super.willUpdate(e),this.hass&&(Me(this.hass),this.namesAsked||(this.namesAsked=!0,Hs(this.hass).then(n=>{this.names=n})))}render(){if(!this.config)return h;let e=this.form(),{devices:n,missing:o}=this.chosenAssets(),r={...this.defaults,...this.config};"assets"in r&&(r.assets=n);let i=o.length===0?e.computeHelper:a=>a.name==="assets"?Xn(e.computeHelper(a),We(void 0,"assets_missing",o.length)):e.computeHelper(a);return d`<ha-form
      .hass=${this.hass}
      .data=${r}
      .schema=${e.schema}
      .computeLabel=${e.computeLabel}
      .computeHelper=${i}
      @value-changed=${this.changed}
    ></ha-form>`}changed(e){e.stopPropagation();let n=this.config??{},o=e.detail.value,r=Array.isArray(o.assets)?{...o,assets:this.savedAssets(o.assets)}:o,i=Object.fromEntries(Object.entries(r).filter(([a,l])=>a in n||this.defaults[a]===void 0||l!==this.defaults[a]));for(let[a,l]of Kn)Ge(i[a])?!(l in i)&&l in this.heldBack&&(i[l]=this.heldBack[l]):(l in i&&(this.heldBack[l]=i[l]),delete i[l]);this.config=i,this.dispatchEvent(new CustomEvent("config-changed",{detail:{config:i},bubbles:!0,composed:!0}))}},eo={limit:"opt_limit_wallets",asset_selection:"opt_asset_selection_wallets",assets:"opt_assets_wallets"},to={limit:"opt_limit_help_wallets",group_selection:"opt_group_selection_help",assets:"opt_assets_help_wallets"},Mt=class extends tt{constructor(){super(...arguments);this.defaults=Zn;this.model="Wallet"}form(){let e=this.config??{};return{schema:[Ct("Bitpanda Portfolio"),re("group_content",[Pt(),U("show_total",!0),U("show_graph",!0),U("show_cash",!0),U("show_allocation",!0),U("show_wallets",!0)]),re("group_wallets",[U("show_search",!1),U("group_wallets",!0),Rt(Oe),Et(5),be(),...zt(this.names,e.group_selection??"all"),be(),...Lt("Wallet",e.asset_selection??"all")]),re("group_appearance",[U("hide_amounts",!1)])],computeLabel:n=>{let o=eo[n.name];return o?u(void 0,o):It(n)},computeHelper:n=>{let o=to[n.name];return o?u(void 0,o):Ht(n)}}}};function so(s){let t=s?xe(ie(s)):[];return t.length>0?t:zs}var Wt=class extends tt{constructor(){super(...arguments);this.defaults=Yn;this.model="Price Tracker"}form(){let e=this.config??{};return{schema:[Ct("Bitpanda Price Tracker"),re("group_content",[{name:"layout",selector:oe(De,n=>u(void 0,`layout_${n}`))},Pt(),{name:"currency",selector:{select:{mode:"dropdown",options:so(this.hass).map(n=>({value:n,label:n}))}}}]),re("group_assets",[Rt(je),Et(0),be(),...zt(this.names,e.group_selection??"all"),be(),...Lt("Price Tracker",e.asset_selection??"all")])],computeLabel:It,computeHelper:n=>n.name==="sort"?u(void 0,"opt_sort_help_tracker"):Ht(n)}}};function nt(s){switch(s.locale.number_format){case"comma_decimal":return"en-US";case"decimal_comma":return"de";case"space_comma":return"fr";case"quote_decimal":return"de-CH";case"system":return;default:return s.locale.language}}function jt(s,t,e,n=0){return new Intl.NumberFormat(nt(s),{maximumFractionDigits:e,minimumFractionDigits:n,useGrouping:s.locale.number_format!=="none"}).format(t)}function Vs(s){return{...s!==0&&Math.abs(s)<1e-4?{maximumSignificantDigits:2}:{maximumFractionDigits:4},roundingMode:"trunc"}}function no(s,t){return new Intl.NumberFormat(nt(s),{...Vs(t),useGrouping:s.locale.number_format!=="none"}).format(t)}var Fs=8;function ke(s,t,e,n,o=!1){let r=o?no(s,t):jt(s,t,Fs);if(e==="stock"||e==="etf"||e==="etc"){let i=o?Vs(t):{maximumFractionDigits:Fs};return`${r} ${We(s,"shares",t,i)}`}return`${r} ${e==="metal"?"g":n}`}var ot=new Set(["unavailable","unknown"]);function H(s,t){let e=t?s.states[t]:void 0;return e&&!ot.has(e.state)?s.formatEntityState(e):void 0}function Bs(s,t,e){let n=t?s.states[t]:void 0;return n&&e!==void 0?s.formatEntityState({...n,state:String(e)}):void 0}function $e(s,t,e,n=!1){return Dt(s,t,e,2,n)}function qs(s,t,e){let n=Math.abs(t);return Dt(s,t,e,n>=10||n===0?2:n>=1?4:8,!1)}function Gs(s,t,e){return Dt(s,t,e,Ks(t),!1)}function Dt(s,t,e,n,o){try{return new Intl.NumberFormat(nt(s),{style:"currency",currency:e,minimumFractionDigits:2,maximumFractionDigits:n,useGrouping:s.locale.number_format!=="none",...o?{signDisplay:"exceptZero"}:{}}).format(t)}catch{return`${jt(s,t,n)} ${e}`}}function Ks(s){let t=Math.abs(s);return t===0||t>=10?2:t>=1?4:t>=.1?5:t>=.001?6:t>=1e-4?7:8}function Zs(s,t,e){let n=t?s.states[t]:void 0;if(!n||ot.has(n.state)||e===void 0||!Number.isFinite(e))return;let o=s.entities[n.entity_id]?.display_precision,r=typeof o=="number"?o:Ks(Number(n.state)),i=Number(e.toFixed(r))===0?0 .toFixed(r):e.toFixed(r),a=s.formatEntityState({...n,state:i});return Number(i)>0?`+${a}`:a}function x(s,t){if(!s||ot.has(s.state))return;let e=s.attributes[t];return typeof e=="number"&&Number.isFinite(e)?e:void 0}function $(s,t){let e=t?s.states[t]:void 0;if(!e||ot.has(e.state)||e.state.trim()==="")return;let n=Number(e.state);return Number.isFinite(n)?n:void 0}var oo=new Set(["cs","de","fi","fr","sk","sv"]),Ys=s=>oo.has(s.locale.language)?"\xA0":"";function R(s,t){if(t===void 0||!Number.isFinite(t))return{text:"\u2014",direction:"none"};let e=new Intl.NumberFormat(nt(s),{minimumFractionDigits:2,maximumFractionDigits:2,signDisplay:"exceptZero",useGrouping:s.locale.number_format!=="none"}).format(t),n=Ys(s),r=Math.round(Math.abs(t)*100)===0?"flat":t>0?"up":"down";return{text:`${e}${n}%`,direction:r}}function ae(s,t,e,n=!1){let o=Ys(s);return`${jt(s,t,e,n?e:0)}${o}%`}function C(s){return s==="up"||s==="down"?s:""}function Q(s){return s==="up"?"\u25B2":s==="down"?"\u25BC":""}function Ut(s){return Ps(s)?s.locale.language:"en"}function Js(s){return s.locale.time_zone==="server"?s.config?.time_zone:void 0}function ro(s){let t=s.locale.time_format;return t==="12"||t==="24"?t==="12":new Date("January 1, 2023 22:00:00").toLocaleString(t==="system"?void 0:s.locale.language).includes("10")}function Ae(s,t){let e=Js(s),n=r=>new Intl.DateTimeFormat("en",{year:"numeric",timeZone:e}).format(r),o=n(t)===n(Date.now())?{}:{year:"numeric"};return new Intl.DateTimeFormat(Ut(s),{day:"numeric",month:"short",...o,timeZone:e}).format(t)}function Xs(s,t){let e=/^(\d{4})-(\d{2})-(\d{2})$/.exec(t);if(!e)return;let n=Date.UTC(Number(e[1]),Number(e[2])-1,Number(e[3]));return new Intl.DateTimeFormat(Ut(s),{day:"numeric",month:"long",timeZone:"UTC"}).format(n)}function rt(s,t){let e=ro(s);return new Intl.DateTimeFormat(Ut(s),{day:"numeric",month:"short",hour:e?"numeric":"2-digit",minute:"2-digit",hourCycle:e?"h12":"h23",timeZone:Js(s)}).format(t)}var{I:Yr}=gs;var Qs=s=>s.strings===void 0;var en={ATTRIBUTE:1,CHILD:2,PROPERTY:3,BOOLEAN_ATTRIBUTE:4,EVENT:5,ELEMENT:6},Ft=s=>(...t)=>({_$litDirective$:s,values:t}),it=class{constructor(t){}get _$AU(){return this._$AM._$AU}_$AT(t,e,n){this._$Ct=t,this._$AM=e,this._$Ci=n}_$AS(t,e){return this.update(t,e)}update(t,e){return this.render(...e)}};var Se=(s,t)=>{let e=s._$AN;if(e===void 0)return!1;for(let n of e)n._$AO?.(t,!1),Se(n,t);return!0},at=s=>{let t,e;do{if((t=s._$AM)===void 0)break;e=t._$AN,e.delete(s),s=t}while(e?.size===0)},tn=s=>{for(let t;t=s._$AM;s=t){let e=t._$AN;if(e===void 0)t._$AN=e=new Set;else if(e.has(s))break;e.add(s),lo(t)}};function io(s){this._$AN!==void 0?(at(this),this._$AM=s,tn(this)):this._$AM=s}function ao(s,t=!1,e=0){let n=this._$AH,o=this._$AN;if(o!==void 0&&o.size!==0)if(t)if(Array.isArray(n))for(let r=e;r<n.length;r++)Se(n[r],!1),at(n[r]);else n!=null&&(Se(n,!1),at(n));else Se(this,s)}var lo=s=>{s.type==en.CHILD&&(s._$AP??=ao,s._$AQ??=io)},lt=class extends it{constructor(){super(...arguments),this._$AN=void 0}_$AT(t,e,n){super._$AT(t,e,n),tn(this),this.isConnected=t._$AU}_$AO(t,e=!0){t!==this.isConnected&&(this.isConnected=t,t?this.reconnected?.():this.disconnected?.()),e&&(Se(this,t),at(this))}setValue(t){if(Qs(this._$Ct))this._$Ct._$AI(t,this);else{let e=[...this._$Ct._$AH];e[this._$Ci]=t,this._$Ct._$AI(e,this,0)}}disconnected(){}reconnected(){}};var sn=()=>new Bt,Bt=class{},Vt=new WeakMap,nn=Ft(class extends lt{render(s){return h}update(s,[t]){let e=t!==this.G;return e&&this.rt(void 0),(e||this.lt!==this.ct)&&(this.G=t,this.ht=s.options?.host,this.rt(this.ct=s.element)),h}rt(s){if(this.G!==void 0)if(this.isConnected||(s=void 0),typeof this.G=="function"){let t=this.ht??globalThis,e=Vt.get(t);e===void 0&&(e=new WeakMap,Vt.set(t,e)),e.get(this.G)!==void 0&&this.G.call(this.ht,void 0),e.set(this.G,s),s!==void 0&&this.G.call(this.ht,s)}else this.G.value=s}get lt(){return typeof this.G=="function"?Vt.get(this.ht??globalThis)?.get(this.G):this.G?.value}disconnected(){this.lt===this.ct&&this.rt(void 0)}reconnected(){this.rt(this.ct)}});var co="M12,9A3,3 0 0,0 9,12A3,3 0 0,0 12,15A3,3 0 0,0 15,12A3,3 0 0,0 12,9M12,17A5,5 0 0,1 7,12A5,5 0 0,1 12,7A5,5 0 0,1 17,12A5,5 0 0,1 12,17M12,4.5C7,4.5 2.73,7.61 1,12C2.73,16.39 7,19.5 12,19.5C17,19.5 21.27,16.39 23,12C21.27,7.61 17,4.5 12,4.5Z",po="M11.83,9L15,12.16C15,12.11 15,12.05 15,12A3,3 0 0,0 12,9C11.94,9 11.89,9 11.83,9M7.53,9.8L9.08,11.35C9.03,11.56 9,11.77 9,12A3,3 0 0,0 12,15C12.22,15 12.44,14.97 12.65,14.92L14.2,16.47C13.53,16.8 12.79,17 12,17A5,5 0 0,1 7,12C7,11.21 7.2,10.47 7.53,9.8M2,4.27L4.28,6.55L4.73,7C3.08,8.3 1.78,10 1,12C2.73,16.39 7,19.5 12,19.5C13.55,19.5 15.03,19.2 16.38,18.66L16.81,19.08L19.73,22L21,20.73L3.27,3M12,7A5,5 0 0,1 17,12C17,12.64 16.87,13.26 16.64,13.82L19.57,16.75C21.07,15.5 22.27,13.86 23,12C21.27,7.61 17,4.5 12,4.5C10.6,4.5 9.26,4.75 8,5.2L10.17,7.35C10.74,7.13 11.35,7 12,7Z",rn="M7.41,8.58L12,13.17L16.59,8.58L18,10L12,16L6,10L7.41,8.58Z",an="M7.41,15.41L12,10.83L16.59,15.41L18,14L12,8L6,14L7.41,15.41Z",uo="M8.59,16.58L13.17,12L8.59,7.41L10,6L16,12L10,18L8.59,16.58Z",ho="M9.5,3A6.5,6.5 0 0,1 16,9.5C16,11.11 15.41,12.59 14.44,13.73L14.71,14H15.5L20.5,19L19,20.5L14,15.5V14.71L13.73,14.44C12.59,15.41 11.11,16 9.5,16A6.5,6.5 0 0,1 3,9.5A6.5,6.5 0 0,1 9.5,3M9.5,5C7,5 5,7 5,9.5C5,12 7,14 9.5,14C12,14 14,12 14,9.5C14,7 12,5 9.5,5Z",mo="M19,6.41L17.59,5L12,10.59L6.41,5L5,6.41L10.59,12L5,17.59L6.41,19L12,13.41L17.59,19L19,17.59L13.41,12L19,6.41Z",le=s=>ne`<svg viewBox="0 0 24 24" aria-hidden="true"><path d=${s}></path></svg>`,qt={down:rn,up:an,right:uo};function T(s){return t=>{(t.key==="Enter"||t.key===" ")&&(t.preventDefault(),s())}}function _o(s,t){s.dispatchEvent(new CustomEvent("hass-more-info",{bubbles:!0,composed:!0,detail:{entityId:t}}))}function z(s,t){return()=>{t&&_o(s,t)}}function ce(s,t){let e=s.filter(n=>n.second!==void 0);return e.length>0&&e.every(n=>n.first+t+n.second<=n.room)}function A(s,t){return d`<span class="amount ${t?"blur":""}">${s??"\u2014"}</span>`}function ln(s,t,e){let[n,...o]=s.split(`{${t}}`);return o.length===0?d`${s}`:d`${n}<span class="nw">${e}</span>${o.join(`{${t}}`)}`}function ee(s){return d`<div class="empty">${s}</div>`}function Te(s,t,e){return d`<div class="head">
    <div class="title">${t}</div>
    ${e?d`<button
          class="icon-btn eye"
          aria-label=${u(s,e.hidden?"eye_show":"eye_hide")}
          title=${u(s,e.hidden?"eye_show":"eye_hide")}
          @click=${e.toggle}
        >
          ${le(e.hidden?po:co)}
        </button>`:h}
  </div>`}function cn(s,t,e,n,o){let{text:r,direction:i}=R(s,t),a=Q(i);return d`<div class="hero-line">
    <span class="chip ${C(i)}" role="button" tabindex="0" @click=${n} @keydown=${T(n)}
      >${a?`${a} `:""}${r}</span
    >
    ${i!=="none"&&o?.text?d`<span class="chip-amount ${C(i)}">${A(o.text,o.hidden)}</span>`:h}
    <span class="chip-label">${u(s,`return_${e}`)}</span>
  </div>`}function dn(s,t,e,n,o){return d`<div class="seg" role="radiogroup" aria-label=${s} @keydown=${i=>{let a=i.key==="ArrowRight"||i.key==="ArrowDown"?1:i.key==="ArrowLeft"||i.key==="ArrowUp"?-1:0;if(a===0)return;i.preventDefault();let l=(t.indexOf(e)+a+t.length)%t.length;o(t[l]),i.currentTarget.querySelectorAll("[role=radio]")[l]?.focus()}}>
    ${t.map(i=>d`<span
          role="radio"
          aria-checked=${i===e?"true":"false"}
          tabindex=${i===e?0:-1}
          @click=${()=>o(i)}
          @keydown=${T(()=>o(i))}
          >${n(i)}</span
        >`)}
  </div>`}function ct(s,t,e){return dn(u(s,"aria_timeframe"),F,t,n=>u(s,`tf_${n}`),e)}function pn(s,t,e,n){return t.length<2?null:dn(u(s,"aria_currency"),t,e,o=>o,n)}function un(s,t,e){let n=sn(),o=()=>{e(""),n.value?.focus()};return d`<div class="search" role="search">
    ${le(ho)}<input
      ${nn(n)}
      type="text"
      .value=${t}
      placeholder=${u(s,"search_placeholder")}
      aria-label=${u(s,"aria_search")}
      autocomplete="off"
      spellcheck="false"
      @input=${r=>e(r.target.value)}
    />${t?d`<span class="clear" role="button" tabindex="0" aria-label=${u(s,"aria_search_clear")} @click=${o} @keydown=${T(o)}
          >${le(mo)}</span
        >`:h}
  </div>`}var fo={\u00DF:"ss",\u00F8:"o",\u00E6:"ae",\u0153:"oe",\u0142:"l",\u0111:"d",\u00F0:"d",\u00FE:"th",\u0131:"i"};function on(s){return s.normalize("NFD").replace(/\p{M}/gu,"").toLowerCase().replace(/[ßøæœłđðþı]/gu,t=>fo[t]??t).replace(/[^\p{L}\p{N}\s]/gu,"")}function hn(s,t){let e=on(t).split(/\s+/).filter(Boolean),n=on(`${s.name} ${s.symbol} ${s.isin??""}`);return e.length>0&&e.every(o=>n.includes(o))}function mn(s){let{hass:t,wallet:e,hidden:n,onTap:o,chevron:r}=s,i=e.total?t.states[e.total]:void 0,a=x(i,"units"),l=$(t,e.total),c=$(t,e.staking),p=l&&c&&c>0?c/l*100:void 0,{text:m,direction:_}=R(t,x(i,"total_return_percent")),f=Q(_),w=_==="none"?d`<span class="wchip none">—</span>`:d`<span class="wchip ${C(_)}">${f?`${f} `:""}${m}</span>`,y=p===void 0?h:d`<div class="stake"><span class="badge">${u(t,"staked",{share:ae(t,p,0)})}</span></div>`,g=k=>{k.stopPropagation(),r?.toggle()};return d`<div class="wallet">
    <div class="tap" role="button" tabindex="0" @click=${o} @keydown=${T(o)}>
      <div class="main">
        <div class="n" title=${e.shortName}>${e.shortName}</div>
        <div class="sub ${p===void 0?"":"staked"}">
          <div class="s">
            <span class="units"
              >${A(a===void 0?void 0:ke(t,a,e.category,e.symbol,!0),n)}</span
            >${e.isin?d` · <span class="isin">${e.isin}</span>`:h}
          </div>
          ${y}
        </div>
      </div>
      <div class="right">${w}<span class="val">${A(H(t,e.total),n)}</span></div>
    </div>
    ${r?d`<span
          class="chevron"
          role="button"
          tabindex="0"
          aria-expanded=${r.open?"true":"false"}
          @click=${g}
          @keydown=${k=>{k.stopPropagation(),T(r.toggle)(k)}}
          >${le(r.open?an:rn)}</span
        >`:h}
  </div>`}function dt(s,t,e){let n=i=>$(s,i.total)??Number.NEGATIVE_INFINITY,o=i=>x(i.total?s.states[i.total]:void 0,"total_return_percent")??Number.NEGATIVE_INFINITY,r=(i,a)=>i.name.localeCompare(a.name,O(s));return[...t].sort((i,a)=>e==="name"?r(i,a):(e==="value"?n(a)-n(i):o(a)-o(i))||r(i,a))}var go=window.customElements,yo=1e4;function wo(s=()=>window.customElements,t=go,e=yo){let n=Date.now();return new Promise(o=>{let r=()=>{let i=s();i!==t||i.get("home-assistant")||Date.now()-n>=e?o(i):setTimeout(r,50)};r()})}var vo="https://github.com/Spegeli/hacs_bitpanda#-dashboard-cards";function bo(s,t,e,n,o={}){let r=s.entities[t];return!r||r.platform!=="bitpanda"||!r.device_id?null:(typeof e=="string"?[e]:e).includes(s.devices[r.device_id]?.model??"")?{config:{type:`custom:${n}`,...o}}:null}function pt(s,t,e){wo().then(r=>{r.get(s)||r.define(s,t)});let n=window;if(n.customCards??=[],n.customCards.some(r=>r.type===s))return;let{model:o}=e;n.customCards.push({type:s,name:e.name,get description(){return e.description()},preview:!0,documentationURL:vo,...o?{getEntitySuggestion:(r,i)=>bo(r,i,o,s,t.getStubConfig?.())}:{}})}var xo={day:[864e5,"5minute"],week:[6048e5,"hour"],month:[2592e6,"hour"],six_month:[157248e5,"day"],year:[31536e6,"day"]};function ut(s){return s==="5minute"?5*6e4:s==="hour"?36e5:864e5}function _n(s){return s.timeframe==="month"?(s.end-s.start)/120:0}function pe(s,t){let[e,n]=xo[s];return{timeframe:s,start:t-e,end:t,period:n}}var ko=s=>typeof s=="number"?s:Date.parse(s);async function $o(s,t,e){if(t.length===0)return{};let n;try{n=await s.callWS({type:"recorder/statistics_during_period",start_time:new Date(e.start).toISOString(),end_time:new Date(e.end).toISOString(),statistic_ids:[...t],period:e.period,types:["state"]})}catch{return}let o={};for(let[r,i]of Object.entries(n))o[r]=i.map(a=>({t:ko(a.start),v:a.state})).filter(a=>typeof a.v=="number"&&Number.isFinite(a.t)).sort((a,l)=>a.t-l.t);return o}var ht="portfolio";async function fn(s,t,e){let n;try{n=await s.callWS({type:"bitpanda/portfolio_history",timeframe:e.timeframe})}catch{return}let r=(Array.isArray(n?.points)?n.points:[]).filter(i=>Array.isArray(i)&&typeof i[0]=="number"&&typeof i[1]=="number"&&Number.isFinite(i[0])&&Number.isFinite(i[1])).map(([i,a])=>({t:i,v:a})).sort((i,a)=>i.t-a.t);return{[ht]:r}}var de=class{constructor(t,e=$o){this.onUpdate=t;this.fetch=e;this.key="";this.end=0;this.latest=0;this.current={}}request(t,e,n,o=""){let r=`${n.timeframe}|${[...e].sort().join(",")}|${o}`;if(r===this.key&&n.end-this.end<ut(n.period))return;n.timeframe!==this.timeframe&&(this.current={}),this.key=r,this.timeframe=n.timeframe,this.end=n.end;let i=++this.latest;this.fetch(t,e,n).then(a=>{if(i===this.latest){if(a===void 0){this.key="";return}this.current=a,this.onUpdate()}})}series(t){return this.current[t]}};function gn(s,t,e){let n=ut(e.period),o=s.find(r=>r.t>=e.start-n);if(!(t===void 0||o===void 0||o.v===0))return{change:(t-o.v)/o.v*100,amount:t-o.v,...o.t>e.start+n?{since:o.t}:{}}}var yn=2,Gt=s=>Math.round(s*100)/100;function Kt(s,t,e,n){return Gt(e===t?n/2:n-yn-(s-t)/(e-t)*(n-2*yn))}function wn(s,t){let e=0;return s.forEach((n,o)=>{Math.abs(n.t-t)<Math.abs(s[e].t-t)&&(e=o)}),e}function Ao(s,t){if(t<=0||s.length<3)return s;let e=o=>Math.floor(o.t/t),n=[];for(let o of s.slice(0,-1)){let r=n[n.length-1];(!r||e(o)!==e(r))&&n.push(o)}return n.push(s[s.length-1]),n}function vn(s,t,e,n,o,r=0){let i=o??1.5*ut(t.period),a=[],l;for(let g of s)(!l||g.t-l.t>i)&&a.push([]),a[a.length-1]?.push(g),l=g;let c=a.map(g=>Ao(g,r)),p=c.flat().map(g=>g.v),m=Math.min(...p),_=Math.max(...p),f=t.end-t.start,w=g=>Gt((g-t.start)/f*e),y=g=>Kt(g,m,_,n);return c.map(g=>g.map(k=>[w(k.t),y(k.v)]))}function So(s,t,e,n,o,r=0){return vn(s,t,e,n,o,r).map(i=>i.length===1?`M${i[0]?.[0]},${i[0]?.[1]}l0.01,0`:i.map(([a,l],c)=>`${c===0?"M":"L"}${a},${l}`).join("")).join("")}function To(s,t,e,n,o,r=0){return vn(s,t,e,n,o,r).map(i=>{let a=i[0],l=i[i.length-1];return`M${a[0]},${n}${i.map(([c,p])=>`L${c},${p}`).join("")}L${l[0]},${n}Z`}).join("")}var Zt=(s,t)=>s.length>0&&s[s.length-1].t-s[0].t>=(t.end-t.start)/10;function mt(s,t,e){let{width:n,height:o,fill:r,className:i,gapMs:a,stepMs:l}=e;return Zt(s,t)?ne`<svg class=${i} viewBox="0 0 ${n} ${o}" preserveAspectRatio="none" aria-hidden="true">${r?ne`<path class="area" d=${To(s,t,n,o,a,l)}></path>`:null}<path class="line" d=${So(s,t,n,o,a,l)} vector-effect="non-scaling-stroke"></path></svg>`:ne`<svg class=${i} viewBox="0 0 ${n} ${o}" preserveAspectRatio="none" aria-hidden="true"></svg>`}var Co=480,Yt=72,_t=s=>`${(s*100).toFixed(2)}%`;function Po(s,t,e){let{hass:n,refs:o,window:r,hidden:i,cursor:a,onCursor:l}=s,c=t.map(v=>v.v),p=Math.min(...c),m=Math.max(...c),_=r.end-r.start,f=v=>{let N=v.currentTarget.getBoundingClientRect(),B=Math.min(Math.max((v.clientX-N.left)/N.width,0),1);return wn(t,r.start+B*_)},w=v=>l(f(v)),y=()=>l(void 0),g=v=>{v.pointerType!=="mouse"&&y()},k=o.totalValue?n.states[o.totalValue]?.attributes.unit_of_measurement:void 0,P=typeof k=="string"&&!i?v=>$e(n,v,k):void 0,S=a===void 0?void 0:t[a],ue=h;if(S){let v=(S.t-r.start)/_,N=r.timeframe==="day"||r.timeframe==="week"?rt(n,S.t):Ae(n,S.t),B=v<.25?"start":v>.75?"end":"";ue=d`${P?d`<span class="tag high">${P(m)}</span><span class="tag middle">${P((m+p)/2)}</span
            ><span class="tag low">${P(p)}</span>`:h}
      <div class="cursor" style="left:${_t(v)}"></div>
      <div class="dot" style="left:${_t(v)};top:${_t(Kt(S.v,p,m,Yt)/Yt)}"></div>
      <div class="tip ${B}" style="left:${_t(v)}">${P?`${N} \xB7 ${P(S.v)}`:N}</div>`}let he=mt(t,r,{width:Co,height:Yt,fill:!0,className:`spark ${e}`,gapMs:Number.POSITIVE_INFINITY});return Zt(t,r)?d`<div class="plot" @pointerdown=${w} @pointermove=${w} @pointerup=${g} @pointercancel=${y} @pointerleave=${y}>
    ${he}
    <div class="mid"></div>
    ${ue}
  </div>`:d`<div class="plot">${he}</div>`}function Eo(s,t,e){if(t.timeframe==="day")return u(s,"value_line_day");let n=e[0]?.t??t.start;return u(s,"value_line",{start:Ae(s,Math.max(t.start,n))})}function Ro(s,t,e){let n=$(s,t.totalValue),o=$(s,t.returns[e]),r=t.totalValue?s.states[t.totalValue]?.attributes.unit_of_measurement:void 0;if(!(n===void 0||o===void 0||o<=-100||typeof r!="string"))return $e(s,n*o/(100+o),r,!0)}function bn(s){let{host:t,hass:e,refs:n,timeframe:o,hidden:r,window:i,points:a}=s,l=$(e,n.returns[o]),c=C(R(e,l).direction)||"flat",p=m=>z(t,m);return d`${s.total?d`<div class="hero" role="button" tabindex="0" @click=${p(n.totalValue)} @keydown=${T(p(n.totalValue))}>
            ${A(H(e,n.totalValue),r)}
          </div>
          ${cn(e,l,o,p(n.returns[o]),{text:Ro(e,n,o),hidden:r})}`:h}
    ${s.total||s.line?ct(e,o,s.onTimeframe):h}
    ${s.line&&a&&a.length>0?d`${Po(s,a,c)}
          <div class="caption">${Eo(e,i,a)}</div>`:h}`}var zo="bitpanda-portfolio-card",xn={crypto:"var(--blue-color, #4269d0)",stock:"var(--indigo-color, #3f51b5)",etf:"var(--amber-color, #efb118)",etc:"var(--cyan-color, #00bcd4)",index:"var(--purple-color, #a463f2)",metal:"var(--green-color, #3ca951)",other:"var(--pink-color, #ff8ab7)",cash_plus:"var(--deep-orange-color, #ff725c)",cash:"var(--teal-color, #6cc5b0)"},kn=s=>s.category??"other";function Lo(s,t){return t<1?`<${ae(s,1,0)}`:ae(s,t,2,!0)}var Io=(s,t)=>Xe(Je(s.wallets,t.group_selection??"all",t.groups??[]),t.asset_selection??"all",t.assets??[]);function Ho(s,t){let e=0,n=0;for(let o of t){let r=$(s,o.total),i=x(o.total?s.states[o.total]:void 0,"invested_amount");if(r===void 0||i===void 0)return;e+=r,n+=i}return n>0?(e-n)/n*100:void 0}function $n(s){let t=s.map(n=>({room:n.room,first:n.left,second:Math.max(n.chip??0,n.value)}));if(s.length===0||ce(t,No))return"beside";let e=s.flatMap(n=>n.chip===void 0?[]:[{room:n.below??n.room,first:n.chip,second:n.value}]);return e.length===0||ce(e,Mo)?"row":"stacked"}function Jt(s){if(!s.some(t=>t===void 0))return Math.round(s.reduce((t,e)=>t+e,0)*1e8)/1e8}var An="\xA0\xB7 ",No=12,Mo=8,Wo=30,Oo=8,Xt=class extends V{constructor(){super(...arguments);this.openGroups=new Set;this.showAll=!1;this.query="";this.cursor=void 0;this.stakeInline=!1;this.groupsLayout="beside";this.rowsLayout="beside";this.openWallets=new Set;this.window=pe("day",Date.now());this.lines=new de(()=>this.seriesArrived(),fn)}static{this.properties={...V.properties,openGroups:{state:!0},openWallets:{state:!0},showAll:{state:!0},query:{state:!0},cursor:{state:!0},stakeInline:{state:!0},groupsLayout:{state:!0},rowsLayout:{state:!0}}}static async getConfigElement(){return st(Qe)}static getStubConfig(){return{timeframe:"day",sort:"value",group_selection:"all",asset_selection:"all"}}validate(e){return Be(e,{...Ze,timeframe:E(F),show_total:D,show_graph:D,show_cash:D,show_allocation:D,show_wallets:D,group_wallets:D,show_search:D,sort:E(Oe),limit:Ue,group_selection:E(j),groups:Ve,asset_selection:E(j),assets:Fe,hide_amounts:D})}watchedEntities(){let e=this.hass?Ye(this.hass):void 0;return e?[e.totalValue,e.cash,e.cashPlus,...Object.values(e.returns),...e.wallets.flatMap(n=>[n.available,n.total,n.staking])].filter(n=>n!==void 0):[]}willUpdate(e){super.willUpdate(e);let n=this.hass?Ye(this.hass):void 0;this.window=pe(this.timeframe,Date.now());let o=this.hass?.states[n?.returns[this.timeframe]??""]?.state??"";this.hass&&n&&this.config?.show_graph!==!1&&this.lines.request(this.hass,[ht],this.window,o)}getCardSize(){return 8}remeasures(e){return!(e.size===1&&e.has("cursor"))}fitLayout(){let e=_=>[...this.renderRoot.querySelectorAll(_)],n=(_,f)=>_.querySelector(f),o=this.widthMeter(),r=_=>_?o(_):void 0,i=e(".wallet .sub").map(_=>{let f=r(_.querySelector(".stake .badge"));return{room:_.clientWidth,first:o(n(_,".s")),...f===void 0?{}:{second:f}}}),a=ce(i,Oo);a!==this.stakeInline&&(this.stakeInline=a);let l=e(".group").map(_=>{let f=r(_.querySelector(".gchip"));return{room:_.clientWidth,left:o(n(_,".gleft")),...f===void 0?{}:{chip:f},value:o(n(_,".sum"))}}),c=$n(l);c!==this.groupsLayout&&(this.groupsLayout=c);let p=e(".wallet .tap").map(_=>({room:_.clientWidth,below:_.clientWidth+Wo,left:o(n(_,".s .units"),!0),chip:o(n(_,".wchip")),value:o(n(_,".val"))})),m=$n(p);m!==this.rowsLayout&&(this.rowsLayout=m)}groupChip(e,n){let{text:o,direction:r}=R(e,Ho(e,n));if(r==="none")return d`<span class="gchip none">—</span>`;let i=Q(r);return d`<span class="gchip ${C(r)}">${i?`${i} `:""}${o}</span>`}walletsClass(){return["wallets",this.stakeInline?"stake-inline":"",this.groupsLayout==="beside"?"":"groups-wrapped",this.groupsLayout==="stacked"?"groups-stacked":"",this.rowsLayout==="beside"?"":"rows-wrapped",this.rowsLayout==="stacked"?"rows-stacked":""].filter(Boolean).join(" ")}toggle(e,n){let o=new Set(e);return o.has(n)?o.delete(n):o.add(n),o}render(){let e=this.hass,n=this.config;if(!e||!n)return h;let o=Ye(e),r={hidden:this.amountsHidden,toggle:()=>this.toggleAmounts()},i=n.title||"Bitpanda Portfolio";if(!o)return d`<ha-card>${Te(e,i)}${ee(u(e,"empty_portfolio"))}</ha-card>`;let a=n.show_total!==!1||n.show_graph!==!1,l=n.show_cash!==!1||n.show_allocation!==!1,c=Io(o,n);return d`<ha-card>
      ${Te(e,i,r)}
      <div class="content">
        ${bn({host:this,hass:e,refs:o,timeframe:this.timeframe,hidden:this.amountsHidden,window:this.window,points:this.lines.series(ht),total:n.show_total!==!1,line:n.show_graph!==!1,onTimeframe:p=>{this.cursor=void 0,this.selectTimeframe(p)},cursor:this.cursor,onCursor:p=>{p!==this.cursor&&(this.cursor=p)}})}
        ${l?d`${a?d`<div class="divider"></div>`:h}
              ${n.show_cash===!1?h:this.renderCash(e,o)}
              ${n.show_allocation===!1?h:this.renderAllocation(e,o)}`:h}
        ${n.show_wallets===!1?h:d`${a||l?d`<div class="divider"></div>`:h}${n.show_search&&c.length>0?un(e,this.query,p=>this.query=p):h}${this.renderWallets(e,o,c,n)}`}
      </div>
    </ha-card>`}renderCash(e,n){let o=(r,i,a)=>d`<div class=${a?"end":""} role="button" tabindex="0" @click=${z(this,i)} @keydown=${T(z(this,i))}>
        <span class="k">${r}</span><span class="v">${A(H(e,i),this.amountsHidden)}</span>
      </div>`;return d`<div class="pair">${o(u(e,"cash"),n.cash,!1)}${o(u(e,"cash_plus"),n.cashPlus,!0)}</div>`}renderAllocation(e,n){let o=[];for(let a of I){let l=n.wallets.filter(c=>kn(c)===a);l.length>0&&o.push({key:a,label:Tt(e,a),value:Jt(l.map(c=>$(e,c.total)))})}n.cashPlus&&o.push({key:"cash_plus",label:u(e,"cash_plus"),value:$(e,n.cashPlus)}),n.cash&&o.push({key:"cash",label:u(e,"cash"),value:$(e,n.cash)});let r=Jt(o.map(a=>a.value));if(r===void 0)return d`<div class="allocation-missing muted">—</div>`;let i=o.map(a=>({...a,share:r>0?a.value/r*100:0})).filter(a=>a.share>0).sort((a,l)=>l.share-a.share);return d`<div class="bar" role="img" aria-label=${u(e,"opt_show_allocation")}>
        ${i.map(a=>d`<span style="width:${a.share}%;background:${xn[a.key]}"></span>`)}
      </div>
      <div class="legend">
        ${i.map(a=>d`<span><i style="background:${xn[a.key]}"></i>${a.label} ${Lo(e,a.share)}</span>`)}
      </div>`}renderWallets(e,n,o,r){if(n.wallets.length===0)return ee(u(e,"empty_wallets"));if(o.length===0)return ee(u(e,"empty_selection_wallets"));let i=r.sort??"value",a=r.show_search?this.query.trim():"";if(a){let l=dt(e,o.filter(c=>hn(c,a)),i);return l.length>0?d`<div class=${this.walletsClass()}>${l.map(c=>this.renderWallet(e,n,c))}</div>`:d`<div class="search-none">${u(e,"search_none",{query:a})}</div>`}if(r.group_wallets===!1){let l=dt(e,o,i),c=r.limit??5,p=c>0&&l.length>c,m=p&&!this.showAll?l.slice(0,c):l;return d`<div class=${this.walletsClass()}>${m.map(_=>this.renderWallet(e,n,_))}</div>
        ${p?d`<button class="show-all" @click=${()=>this.showAll=!this.showAll}>
              ${this.showAll?u(e,"show_less"):u(e,"show_all",{count:l.length})}
            </button>`:h}`}return d`<div class=${this.walletsClass()}>${I.map(l=>{let c=o.filter(f=>kn(f)===l);if(c.length===0)return h;let p=Jt(c.map(f=>$(e,f.total))),m=this.openGroups.has(l),_=()=>{this.openGroups=this.toggle(this.openGroups,l)};return d`<div class="group" role="button" tabindex="0" aria-expanded=${m?"true":"false"} @click=${_} @keydown=${T(_)}>
          <span class="gleft"
            >${le(m?qt.down:qt.right)}<span class="name">${Tt(e,l)}</span
            ><span class="count">${c.length}</span></span
          >
          <span class="gright">${this.groupChip(e,c)}<span class="sum">${A(Bs(e,c[0]?.total,p),this.amountsHidden)}</span></span>
        </div>
        ${m?d`<div class="members">${dt(e,c,i).map(f=>this.renderWallet(e,n,f))}</div>`:h}`})}</div>`}renderWallet(e,n,o){let r=this.openWallets.has(o.deviceId);return d`${mn({hass:e,wallet:o,hidden:this.amountsHidden,onTap:z(this,o.total),chevron:{open:r,toggle:()=>{this.openWallets=this.toggle(this.openWallets,o.deviceId)}}})}${r?this.renderDetail(e,n,o):h}`}renderDetail(e,n,o){let r=this.amountsHidden,i=b=>b?e.states[b]?.attributes.unit_of_measurement:void 0,a=String(i(o.total)??i(n.totalValue)??"EUR"),l=o.total?e.states[o.total]:void 0,c=o.staking?e.states[o.staking]:void 0,p=b=>{let te=x(b?e.states[b]:void 0,"units");return te===void 0?void 0:ke(e,te,o.category,o.symbol)},m=(b,te=!1)=>b===void 0?void 0:$e(e,b,a,te),_=b=>b===void 0?void 0:qs(e,b,a),f=b=>d`<span class="part">${b}</span>`,w=b=>d`${f(A(p(b),r))}${An}${f(A(H(e,b),r))}`,y=x(l,"total_return"),g=R(e,x(l,"total_return_percent")),k=x(l,"price"),P=x(l,"return_24h"),S=x(l,"change_24h_pct"),ue=R(e,S),he=x(c,"apr_percent"),v=x(c,"rewards_net"),N=x(c,"rewards_count"),B=c?.attributes.rewards_last_at,Tn=typeof B=="string"&&Number.isFinite(Date.parse(B))?rt(e,Date.parse(B)):"\u2014",Cn=m(x(c,"rewards_net_value"));return d`<div class="detail">
      <div class="grid">
        <span>${u(e,"detail_price")}</span><span>${k===void 0?"\u2014":Gs(e,k,a)}</span>
        <span>${u(e,"detail_average_buy_price")}</span><span>${A(_(x(l,"average_buy_price")),r)}</span>
        <span>${u(e,"detail_invested")}</span><span>${A(m(x(l,"invested_amount")),r)}</span>
        ${P!==void 0&&S!==void 0?d`<span>${u(e,"detail_return_24h")}</span
              ><span class=${C(ue.direction)}>${f(A(m(P,!0),r))} ${f(`(${ue.text})`)}</span>`:h}
        <span>${u(e,"detail_total_return")}</span
        ><span class=${C(g.direction)}>${f(A(m(y,!0),r))} ${f(`(${g.text})`)}</span>
      </div>
      ${o.staking?d`<h4>${u(e,"detail_staking")}</h4>
            <div class="grid">
              <span>${u(e,"detail_staked")}</span><span>${w(o.staking)}</span>
              ${he!==void 0?d`<span>${u(e,"detail_staking_apr")}</span><span>${ae(e,he,1)}</span>`:h}
              ${N!==void 0&&N>0?d`<span>${u(e,"detail_rewards_net")}</span
                    ><span>${A(v===void 0?void 0:ke(e,v,o.category,o.symbol),r)}</span>
                    <span>${u(e,"detail_rewards_value")}</span><span>${A(Cn,r)}</span>
                    <span>${u(e,"detail_payouts")}</span
                    ><span
                      >${u(e,"detail_payouts_value",{count:N,date:Tn}).split(" \xB7 ").map((b,te)=>d`${te>0?An:""}${f(b)}`)}</span
                    >`:h}
            </div>`:h}
    </div>`}};pt(zo,Xt,{name:"Bitpanda Portfolio",description:()=>u(qe(),"picker_portfolio"),model:["Portfolio","Wallet"]});var jo=_e`
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
`,Do=6,Uo=120,Fo=90,ft=8,Vo=78,Bo=96,qo=380;function Sn(s){let t=Math.ceil(Math.max(0,...s.map(n=>n.price))),e=Math.ceil(Math.max(0,...s.map(n=>n.change)));return{price:t,change:Math.max(Vo,e),figures:Math.max(t,e)}}function Go(s){let t=Sn(s);return s.every(e=>e.room-t.price-ft-t.change-ft>=Uo)?"beside":s.every(e=>e.room-t.figures-ft>=Fo)?"stacked":"below"}function Ko(s){return ce(s.map(t=>({room:t.room,first:t.pct,...t.amount===void 0?{}:{second:t.amount}})),Do)}var Qt=class extends V{constructor(){super(...arguments);this.showAll=!1;this.amountsInline=!1;this.rowsLayout="beside";this.columns=void 0;this.window=pe("day",Date.now());this.lines=new de(()=>this.seriesArrived())}static{this.properties={...V.properties,currency:{state:!0},showAll:{state:!0},amountsInline:{state:!0},rowsLayout:{state:!0},columns:{state:!0}}}static{this.styles=[Ke,jo]}static async getConfigElement(){return st(et)}static getStubConfig(){return{layout:"list",timeframe:"day",currency:"EUR",sort:"name",group_selection:"all",asset_selection:"all"}}setConfig(e){super.setConfig(e),this.currency=void 0}validate(e){return Be(e,{...Ze,layout:E(De),timeframe:E(F),currency:Is,sort:E(je),group_selection:E(j),groups:Ve,asset_selection:E(j),assets:Fe,limit:Ue})}watchedEntities(){return this.hass?ie(this.hass).flatMap(e=>Object.values(e.prices)):[]}shownCurrency(e){let n=xe(e),o=this.currency??this.config?.currency??"EUR";return n.includes(o)?o:n.includes("EUR")?"EUR":n[0]??"EUR"}visible(e,n){let o=ie(e),r=this.shownCurrency(o),i=Je(o,n.group_selection??"all",n.groups??[]),l=Xe(i,n.asset_selection??"all",n.assets??[]).map(w=>{let y=w.prices[r],g=y?e.states[y]:void 0,k=y?this.lines.series(y):void 0,P=$(e,y),S=gn(k??[],P,this.window);return{asset:w,entityId:y,change:S?.change,amount:S?.amount,points:k,since:S?.since}}),c=n.sort??"name",p=(w,y)=>w.asset.name.localeCompare(y.asset.name,O(e));if(c==="name"||c==="selection"&&n.asset_selection!=="only")l.sort(p);else if(c==="change_desc"||c==="change_asc"){let w=c==="change_desc"?-1:1;l.sort((y,g)=>y.change===void 0||g.change===void 0?y.change===void 0?g.change===void 0?p(y,g):1:-1:w*(y.change-g.change)||p(y,g))}let m=n.limit??0,_=m>0&&l.length>m;return{rows:_&&!this.showAll?l.slice(0,m):l,ranked:l,total:l.length,folds:_,currency:r,currencies:xe(o)}}willUpdate(e){if(super.willUpdate(e),this.window=pe(this.timeframe,Date.now()),!this.hass||!this.config)return;let{rows:n,ranked:o}=this.visible(this.hass,this.config),r=this.config.sort??"name",a=(r==="change_desc"||r==="change_asc"?o:n).map(l=>l.entityId).filter(l=>l!==void 0);this.lines.request(this.hass,a,this.window)}fitLayout(){let e=this.widthMeter(),n=c=>c?e(c):void 0,o=[...this.shadowRoot?.querySelectorAll(".tile .c")??[]].map(c=>{let p=n(c.querySelector(".a"));return{room:c.clientWidth,pct:n(c.querySelector(".pct"))??0,...p===void 0?{}:{amount:p}}}),r=Ko(o);r!==this.amountsInline&&(this.amountsInline=r);let i=this.clientWidth>qo?Bo+ft:0,a=[...this.renderRoot.querySelectorAll(".price-row")].map(c=>{let p=m=>e(c.querySelector(m));return{room:c.clientWidth-i,price:p(".p"),change:Math.max(p(".c .pct"),n(c.querySelector(".c .a"))??0)}}),l=Go(a);if(l!==this.rowsLayout&&(this.rowsLayout=l),a.length>0){let c=Sn(a),p=this.columns;(!p||p.price!==c.price||p.change!==c.change||p.figures!==c.figures)&&(this.columns=c)}}getCardSize(){return 6}line(e,n){let o=e.since===void 0?this.window:{...this.window,start:e.since};return e.points&&e.points.length>0?mt(e.points,o,{width:96,height:28,fill:!1,className:`mini ${n}`,stepMs:_n(o)}):d`<span class="mini"></span>`}change(e,n){let{text:o,direction:r}=R(e,n.change),i=Q(r),a=C(r),l=r==="none"?void 0:Zs(e,n.entityId,n.amount);return{cell:d`<div class="pct pchip ${r==="none"?"none":""}">${r==="none"?"\u2014":`${i?`${i} `:""}${o}`}</div>${l?d`<div class="a">${l}</div>`:h}`,className:a,lineClass:a||"flat"}}since(e,n){return n.since===void 0?h:d`<div class="since">${ln(u(e,"change_since"),"date",Ae(e,n.since))}</div>`}renderList(e,n){let o=this.columns,r=o?`--bp-price:${o.price}px;--bp-change:${o.change}px;--bp-figures:${o.figures}px`:"";return d`<div class="rows ${this.rowsLayout==="beside"?"":this.rowsLayout}" style=${r}>
      ${n.map(i=>{let a=this.change(e,i);return d`<div class="price-row" role="button" tabindex="0" @click=${z(this,i.entityId)} @keydown=${T(z(this,i.entityId))}>
          <div class="lead"><div class="n" title=${i.asset.shortName}>${i.asset.shortName}</div><div class="s">${i.asset.isin??i.asset.symbol}</div>${this.since(e,i)}</div>
          ${this.line(i,a.lineClass)}
          <div class="p">${H(e,i.entityId)??"\u2014"}</div>
          <div class="c ${a.className}">${a.cell}</div>
        </div>`})}
    </div>`}renderTiles(e,n){return d`<div class="tiles ${this.amountsInline?"inline":""}">
      ${n.map(o=>{let r=this.change(e,o);return d`<div class="tile" role="button" tabindex="0" @click=${z(this,o.entityId)} @keydown=${T(z(this,o.entityId))}>
          <div class="n" title=${o.asset.shortName}>${o.asset.shortName}</div>
          <div class="s">${o.asset.isin??o.asset.symbol}</div>
          <div class="p">${H(e,o.entityId)??"\u2014"}</div>
          <div class="c ${r.className}">${r.cell}</div>
          ${this.line(o,r.lineClass)}${this.since(e,o)}
        </div>`})}
    </div>`}footer(e,n,o){if(o==="EUR")return h;let r=n.map(i=>i.entityId?e.states[i.entityId]?.attributes.rate_date:void 0).map(i=>typeof i=="string"?Xs(e,i):void 0).find(i=>i!==void 0);return r?d`<div class="foot">${u(e,"ecb_footer",{currency:o,date:r})}</div>`:h}render(){let e=this.hass,n=this.config;if(!e||!n)return h;let o=Te(e,n.title||"Bitpanda Price Tracker");if(ie(e).length===0)return d`<ha-card>${o}${ee(u(e,"empty_price_tracker"))}</ha-card>`;let{rows:r,total:i,folds:a,currency:l,currencies:c}=this.visible(e,n);return d`<ha-card>
      ${o}
      <div class="content">
        <div class="switches">
          ${ct(e,this.timeframe,p=>this.selectTimeframe(p))}
          ${pn(e,c,l,p=>this.currency=p)}
        </div>
        ${r.length===0?ee(u(e,"empty_selection_assets")):n.layout==="tiles"?this.renderTiles(e,r):this.renderList(e,r)}
        ${a?d`<button class="show-all" @click=${()=>this.showAll=!this.showAll}>
              ${this.showAll?u(e,"show_less"):u(e,"show_all",{count:i})}
            </button>`:h}
      </div>
      ${this.footer(e,r,l)}
    </ha-card>`}};pt("bitpanda-price-tracker-card",Qt,{name:"Bitpanda Price Tracker",description:()=>u(qe(),"picker_price_tracker"),model:"Price Tracker"});
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
