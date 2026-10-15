var Se=globalThis,Te=Se.ShadowRoot&&(Se.ShadyCSS===void 0||Se.ShadyCSS.nativeShadow)&&"adoptedStyleSheets"in Document.prototype&&"replace"in CSSStyleSheet.prototype,_t=Symbol(),Xt=new WeakMap,pe=class{constructor(t,e,s){if(this._$cssResult$=!0,s!==_t)throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");this.cssText=t,this.t=e}get styleSheet(){let t=this.o,e=this.t;if(Te&&t===void 0){let s=e!==void 0&&e.length===1;s&&(t=Xt.get(e)),t===void 0&&((this.o=t=new CSSStyleSheet).replaceSync(this.cssText),s&&Xt.set(e,t))}return t}toString(){return this.cssText}},Qt=o=>new pe(typeof o=="string"?o:o+"",void 0,_t),ue=(o,...t)=>{let e=o.length===1?o[0]:t.reduce((s,n,r)=>s+(i=>{if(i._$cssResult$===!0)return i.cssText;if(typeof i=="number")return i;throw Error("Value passed to 'css' function must be a 'css' function result: "+i+". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.")})(n)+o[r+1],o[0]);return new pe(e,o,_t)},es=(o,t)=>{if(Te)o.adoptedStyleSheets=t.map(e=>e instanceof CSSStyleSheet?e:e.styleSheet);else for(let e of t){let s=document.createElement("style"),n=Se.litNonce;n!==void 0&&s.setAttribute("nonce",n),s.textContent=e.cssText,o.appendChild(s)}},ft=Te?o=>o:o=>o instanceof CSSStyleSheet?(t=>{let e="";for(let s of t.cssRules)e+=s.cssText;return Qt(e)})(o):o;var{is:bo,defineProperty:xo,getOwnPropertyDescriptor:ko,getOwnPropertyNames:$o,getOwnPropertySymbols:Ao,getPrototypeOf:So}=Object,Ce=globalThis,ts=Ce.trustedTypes,To=ts?ts.emptyScript:"",Co=Ce.reactiveElementPolyfillSupport,he=(o,t)=>o,gt={toAttribute(o,t){switch(t){case Boolean:o=o?To:null;break;case Object:case Array:o=o==null?o:JSON.stringify(o)}return o},fromAttribute(o,t){let e=o;switch(t){case Boolean:e=o!==null;break;case Number:e=o===null?null:Number(o);break;case Object:case Array:try{e=JSON.parse(o)}catch{e=null}}return e}},os=(o,t)=>!bo(o,t),ss={attribute:!0,type:String,converter:gt,reflect:!1,useDefault:!1,hasChanged:os};Symbol.metadata??=Symbol("metadata"),Ce.litPropertyMetadata??=new WeakMap;var M=class extends HTMLElement{static addInitializer(t){this._$Ei(),(this.l??=[]).push(t)}static get observedAttributes(){return this.finalize(),this._$Eh&&[...this._$Eh.keys()]}static createProperty(t,e=ss){if(e.state&&(e.attribute=!1),this._$Ei(),this.prototype.hasOwnProperty(t)&&((e=Object.create(e)).wrapped=!0),this.elementProperties.set(t,e),!e.noAccessor){let s=Symbol(),n=this.getPropertyDescriptor(t,s,e);n!==void 0&&xo(this.prototype,t,n)}}static getPropertyDescriptor(t,e,s){let{get:n,set:r}=ko(this.prototype,t)??{get(){return this[e]},set(i){this[e]=i}};return{get:n,set(i){let a=n?.call(this);r?.call(this,i),this.requestUpdate(t,a,s)},configurable:!0,enumerable:!0}}static getPropertyOptions(t){return this.elementProperties.get(t)??ss}static _$Ei(){if(this.hasOwnProperty(he("elementProperties")))return;let t=So(this);t.finalize(),t.l!==void 0&&(this.l=[...t.l]),this.elementProperties=new Map(t.elementProperties)}static finalize(){if(this.hasOwnProperty(he("finalized")))return;if(this.finalized=!0,this._$Ei(),this.hasOwnProperty(he("properties"))){let e=this.properties,s=[...$o(e),...Ao(e)];for(let n of s)this.createProperty(n,e[n])}let t=this[Symbol.metadata];if(t!==null){let e=litPropertyMetadata.get(t);if(e!==void 0)for(let[s,n]of e)this.elementProperties.set(s,n)}this._$Eh=new Map;for(let[e,s]of this.elementProperties){let n=this._$Eu(e,s);n!==void 0&&this._$Eh.set(n,e)}this.elementStyles=this.finalizeStyles(this.styles)}static finalizeStyles(t){let e=[];if(Array.isArray(t)){let s=new Set(t.flat(1/0).reverse());for(let n of s)e.unshift(ft(n))}else t!==void 0&&e.push(ft(t));return e}static _$Eu(t,e){let s=e.attribute;return s===!1?void 0:typeof s=="string"?s:typeof t=="string"?t.toLowerCase():void 0}constructor(){super(),this._$Ep=void 0,this.isUpdatePending=!1,this.hasUpdated=!1,this._$Em=null,this._$Ev()}_$Ev(){this._$ES=new Promise(t=>this.enableUpdating=t),this._$AL=new Map,this._$E_(),this.requestUpdate(),this.constructor.l?.forEach(t=>t(this))}addController(t){(this._$EO??=new Set).add(t),this.renderRoot!==void 0&&this.isConnected&&t.hostConnected?.()}removeController(t){this._$EO?.delete(t)}_$E_(){let t=new Map,e=this.constructor.elementProperties;for(let s of e.keys())this.hasOwnProperty(s)&&(t.set(s,this[s]),delete this[s]);t.size>0&&(this._$Ep=t)}createRenderRoot(){let t=this.shadowRoot??this.attachShadow(this.constructor.shadowRootOptions);return es(t,this.constructor.elementStyles),t}connectedCallback(){this.renderRoot??=this.createRenderRoot(),this.enableUpdating(!0),this._$EO?.forEach(t=>t.hostConnected?.())}enableUpdating(t){}disconnectedCallback(){this._$EO?.forEach(t=>t.hostDisconnected?.())}attributeChangedCallback(t,e,s){this._$AK(t,s)}_$ET(t,e){let s=this.constructor.elementProperties.get(t),n=this.constructor._$Eu(t,s);if(n!==void 0&&s.reflect===!0){let r=(s.converter?.toAttribute!==void 0?s.converter:gt).toAttribute(e,s.type);this._$Em=t,r==null?this.removeAttribute(n):this.setAttribute(n,r),this._$Em=null}}_$AK(t,e){let s=this.constructor,n=s._$Eh.get(t);if(n!==void 0&&this._$Em!==n){let r=s.getPropertyOptions(n),i=typeof r.converter=="function"?{fromAttribute:r.converter}:r.converter?.fromAttribute!==void 0?r.converter:gt;this._$Em=n;let a=i.fromAttribute(e,r.type);this[n]=a??this._$Ej?.get(n)??a,this._$Em=null}}requestUpdate(t,e,s,n=!1,r){if(t!==void 0){let i=this.constructor;if(n===!1&&(r=this[t]),s??=i.getPropertyOptions(t),!((s.hasChanged??os)(r,e)||s.useDefault&&s.reflect&&r===this._$Ej?.get(t)&&!this.hasAttribute(i._$Eu(t,s))))return;this.C(t,e,s)}this.isUpdatePending===!1&&(this._$ES=this._$EP())}C(t,e,{useDefault:s,reflect:n,wrapped:r},i){s&&!(this._$Ej??=new Map).has(t)&&(this._$Ej.set(t,i??e??this[t]),r!==!0||i!==void 0)||(this._$AL.has(t)||(this.hasUpdated||s||(e=void 0),this._$AL.set(t,e)),n===!0&&this._$Em!==t&&(this._$Eq??=new Set).add(t))}async _$EP(){this.isUpdatePending=!0;try{await this._$ES}catch(e){Promise.reject(e)}let t=this.scheduleUpdate();return t!=null&&await t,!this.isUpdatePending}scheduleUpdate(){return this.performUpdate()}performUpdate(){if(!this.isUpdatePending)return;if(!this.hasUpdated){if(this.renderRoot??=this.createRenderRoot(),this._$Ep){for(let[n,r]of this._$Ep)this[n]=r;this._$Ep=void 0}let s=this.constructor.elementProperties;if(s.size>0)for(let[n,r]of s){let{wrapped:i}=r,a=this[n];i!==!0||this._$AL.has(n)||a===void 0||this.C(n,void 0,r,a)}}let t=!1,e=this._$AL;try{t=this.shouldUpdate(e),t?(this.willUpdate(e),this._$EO?.forEach(s=>s.hostUpdate?.()),this.update(e)):this._$EM()}catch(s){throw t=!1,this._$EM(),s}t&&this._$AE(e)}willUpdate(t){}_$AE(t){this._$EO?.forEach(e=>e.hostUpdated?.()),this.hasUpdated||(this.hasUpdated=!0,this.firstUpdated(t)),this.updated(t)}_$EM(){this._$AL=new Map,this.isUpdatePending=!1}get updateComplete(){return this.getUpdateComplete()}getUpdateComplete(){return this._$ES}shouldUpdate(t){return!0}update(t){this._$Eq&&=this._$Eq.forEach(e=>this._$ET(e,this[e])),this._$EM()}updated(t){}firstUpdated(t){}};M.elementStyles=[],M.shadowRootOptions={mode:"open"},M[he("elementProperties")]=new Map,M[he("finalized")]=new Map,Co?.({ReactiveElement:M}),(Ce.reactiveElementVersions??=[]).push("2.1.2");var wt=globalThis,ns=o=>o,Pe=wt.trustedTypes,rs=Pe?Pe.createPolicy("lit-html",{createHTML:o=>o}):void 0,vt="$lit$",W=`lit$${Math.random().toFixed(9).slice(2)}$`,bt="?"+W,Po=`<${bt}>`,G=document,_e=()=>G.createComment(""),fe=o=>o===null||typeof o!="object"&&typeof o!="function",xt=Array.isArray,ps=o=>xt(o)||typeof o?.[Symbol.iterator]=="function",yt=`[ 	
\f\r]`,me=/<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g,is=/-->/g,as=/>/g,V=RegExp(`>|${yt}(?:([^\\s"'>=/]+)(${yt}*=${yt}*(?:[^ 	
\f\r"'\`<>=]|("|')|))|$)`,"g"),ls=/'/g,cs=/"/g,us=/^(?:script|style|textarea|title)$/i,kt=o=>(t,...e)=>({_$litType$:o,strings:t,values:e}),d=kt(1),se=kt(2),qn=kt(3),K=Symbol.for("lit-noChange"),h=Symbol.for("lit-nothing"),ds=new WeakMap,q=G.createTreeWalker(G,129);function hs(o,t){if(!xt(o)||!o.hasOwnProperty("raw"))throw Error("invalid template strings array");return rs!==void 0?rs.createHTML(t):t}var ms=(o,t)=>{let e=o.length-1,s=[],n,r=t===2?"<svg>":t===3?"<math>":"",i=me;for(let a=0;a<e;a++){let l=o[a],c,p,m=-1,_=0;for(;_<l.length&&(i.lastIndex=_,p=i.exec(l),p!==null);)_=i.lastIndex,i===me?p[1]==="!--"?i=is:p[1]!==void 0?i=as:p[2]!==void 0?(us.test(p[2])&&(n=RegExp("</"+p[2],"g")),i=V):p[3]!==void 0&&(i=V):i===V?p[0]===">"?(i=n??me,m=-1):p[1]===void 0?m=-2:(m=i.lastIndex-p[2].length,c=p[1],i=p[3]===void 0?V:p[3]==='"'?cs:ls):i===cs||i===ls?i=V:i===is||i===as?i=me:(i=V,n=void 0);let f=i===V&&o[a+1].startsWith("/>")?" ":"";r+=i===me?l+Po:m>=0?(s.push(c),l.slice(0,m)+vt+l.slice(m)+W+f):l+W+(m===-2?a:f)}return[hs(o,r+(o[e]||"<?>")+(t===2?"</svg>":t===3?"</math>":"")),s]},ge=class o{constructor({strings:t,_$litType$:e},s){let n;this.parts=[];let r=0,i=0,a=t.length-1,l=this.parts,[c,p]=ms(t,e);if(this.el=o.createElement(c,s),q.currentNode=this.el.content,e===2||e===3){let m=this.el.content.firstChild;m.replaceWith(...m.childNodes)}for(;(n=q.nextNode())!==null&&l.length<a;){if(n.nodeType===1){if(n.hasAttributes())for(let m of n.getAttributeNames())if(m.endsWith(vt)){let _=p[i++],f=n.getAttribute(m).split(W),v=/([.?@])?(.*)/.exec(_);l.push({type:1,index:r,name:v[2],strings:f,ctor:v[1]==="."?Re:v[1]==="?"?ze:v[1]==="@"?Le:Y}),n.removeAttribute(m)}else m.startsWith(W)&&(l.push({type:6,index:r}),n.removeAttribute(m));if(us.test(n.tagName)){let m=n.textContent.split(W),_=m.length-1;if(_>0){n.textContent=Pe?Pe.emptyScript:"";for(let f=0;f<_;f++)n.append(m[f],_e()),q.nextNode(),l.push({type:2,index:++r});n.append(m[_],_e())}}}else if(n.nodeType===8)if(n.data===bt)l.push({type:2,index:r});else{let m=-1;for(;(m=n.data.indexOf(W,m+1))!==-1;)l.push({type:7,index:r}),m+=W.length-1}r++}}static createElement(t,e){let s=G.createElement("template");return s.innerHTML=t,s}};function Z(o,t,e=o,s){if(t===K)return t;let n=s!==void 0?e._$Co?.[s]:e._$Cl,r=fe(t)?void 0:t._$litDirective$;return n?.constructor!==r&&(n?._$AO?.(!1),r===void 0?n=void 0:(n=new r(o),n._$AT(o,e,s)),s!==void 0?(e._$Co??=[])[s]=n:e._$Cl=n),n!==void 0&&(t=Z(o,n._$AS(o,t.values),n,s)),t}var Ee=class{constructor(t,e){this._$AV=[],this._$AN=void 0,this._$AD=t,this._$AM=e}get parentNode(){return this._$AM.parentNode}get _$AU(){return this._$AM._$AU}u(t){let{el:{content:e},parts:s}=this._$AD,n=(t?.creationScope??G).importNode(e,!0);q.currentNode=n;let r=q.nextNode(),i=0,a=0,l=s[0];for(;l!==void 0;){if(i===l.index){let c;l.type===2?c=new te(r,r.nextSibling,this,t):l.type===1?c=new l.ctor(r,l.name,l.strings,this,t):l.type===6&&(c=new He(r,this,t)),this._$AV.push(c),l=s[++a]}i!==l?.index&&(r=q.nextNode(),i++)}return q.currentNode=G,n}p(t){let e=0;for(let s of this._$AV)s!==void 0&&(s.strings!==void 0?(s._$AI(t,s,e),e+=s.strings.length-2):s._$AI(t[e])),e++}},te=class o{get _$AU(){return this._$AM?._$AU??this._$Cv}constructor(t,e,s,n){this.type=2,this._$AH=h,this._$AN=void 0,this._$AA=t,this._$AB=e,this._$AM=s,this.options=n,this._$Cv=n?.isConnected??!0}get parentNode(){let t=this._$AA.parentNode,e=this._$AM;return e!==void 0&&t?.nodeType===11&&(t=e.parentNode),t}get startNode(){return this._$AA}get endNode(){return this._$AB}_$AI(t,e=this){t=Z(this,t,e),fe(t)?t===h||t==null||t===""?(this._$AH!==h&&this._$AR(),this._$AH=h):t!==this._$AH&&t!==K&&this._(t):t._$litType$!==void 0?this.$(t):t.nodeType!==void 0?this.T(t):ps(t)?this.k(t):this._(t)}O(t){return this._$AA.parentNode.insertBefore(t,this._$AB)}T(t){this._$AH!==t&&(this._$AR(),this._$AH=this.O(t))}_(t){this._$AH!==h&&fe(this._$AH)?this._$AA.nextSibling.data=t:this.T(G.createTextNode(t)),this._$AH=t}$(t){let{values:e,_$litType$:s}=t,n=typeof s=="number"?this._$AC(t):(s.el===void 0&&(s.el=ge.createElement(hs(s.h,s.h[0]),this.options)),s);if(this._$AH?._$AD===n)this._$AH.p(e);else{let r=new Ee(n,this),i=r.u(this.options);r.p(e),this.T(i),this._$AH=r}}_$AC(t){let e=ds.get(t.strings);return e===void 0&&ds.set(t.strings,e=new ge(t)),e}k(t){xt(this._$AH)||(this._$AH=[],this._$AR());let e=this._$AH,s,n=0;for(let r of t)n===e.length?e.push(s=new o(this.O(_e()),this.O(_e()),this,this.options)):s=e[n],s._$AI(r),n++;n<e.length&&(this._$AR(s&&s._$AB.nextSibling,n),e.length=n)}_$AR(t=this._$AA.nextSibling,e){for(this._$AP?.(!1,!0,e);t!==this._$AB;){let s=ns(t).nextSibling;ns(t).remove(),t=s}}setConnected(t){this._$AM===void 0&&(this._$Cv=t,this._$AP?.(t))}},Y=class{get tagName(){return this.element.tagName}get _$AU(){return this._$AM._$AU}constructor(t,e,s,n,r){this.type=1,this._$AH=h,this._$AN=void 0,this.element=t,this.name=e,this._$AM=n,this.options=r,s.length>2||s[0]!==""||s[1]!==""?(this._$AH=Array(s.length-1).fill(new String),this.strings=s):this._$AH=h}_$AI(t,e=this,s,n){let r=this.strings,i=!1;if(r===void 0)t=Z(this,t,e,0),i=!fe(t)||t!==this._$AH&&t!==K,i&&(this._$AH=t);else{let a=t,l,c;for(t=r[0],l=0;l<r.length-1;l++)c=Z(this,a[s+l],e,l),c===K&&(c=this._$AH[l]),i||=!fe(c)||c!==this._$AH[l],c===h?t=h:t!==h&&(t+=(c??"")+r[l+1]),this._$AH[l]=c}i&&!n&&this.j(t)}j(t){t===h?this.element.removeAttribute(this.name):this.element.setAttribute(this.name,t??"")}},Re=class extends Y{constructor(){super(...arguments),this.type=3}j(t){this.element[this.name]=t===h?void 0:t}},ze=class extends Y{constructor(){super(...arguments),this.type=4}j(t){this.element.toggleAttribute(this.name,!!t&&t!==h)}},Le=class extends Y{constructor(t,e,s,n,r){super(t,e,s,n,r),this.type=5}_$AI(t,e=this){if((t=Z(this,t,e,0)??h)===K)return;let s=this._$AH,n=t===h&&s!==h||t.capture!==s.capture||t.once!==s.once||t.passive!==s.passive,r=t!==h&&(s===h||n);n&&this.element.removeEventListener(this.name,this,s),r&&this.element.addEventListener(this.name,this,t),this._$AH=t}handleEvent(t){typeof this._$AH=="function"?this._$AH.call(this.options?.host??this.element,t):this._$AH.handleEvent(t)}},He=class{constructor(t,e,s){this.element=t,this.type=6,this._$AN=void 0,this._$AM=e,this.options=s}get _$AU(){return this._$AM._$AU}_$AI(t){Z(this,t)}},_s={M:vt,P:W,A:bt,C:1,L:ms,R:Ee,D:ps,V:Z,I:te,H:Y,N:ze,U:Le,B:Re,F:He},Eo=wt.litHtmlPolyfillSupport;Eo?.(ge,te),(wt.litHtmlVersions??=[]).push("3.3.3");var fs=(o,t,e)=>{let s=e?.renderBefore??t,n=s._$litPart$;if(n===void 0){let r=e?.renderBefore??null;s._$litPart$=n=new te(t.insertBefore(_e(),r),r,void 0,e??{})}return n._$AI(o),n};var $t=globalThis,L=class extends M{constructor(){super(...arguments),this.renderOptions={host:this},this._$Do=void 0}createRenderRoot(){let t=super.createRenderRoot();return this.renderOptions.renderBefore??=t.firstChild,t}update(t){let e=this.render();this.hasUpdated||(this.renderOptions.isConnected=this.isConnected),super.update(t),this._$Do=fs(e,this.renderRoot,this.renderOptions)}connectedCallback(){super.connectedCallback(),this._$Do?.setConnected(!0)}disconnectedCallback(){super.disconnectedCallback(),this._$Do?.setConnected(!1)}render(){return K}};L._$litElement$=!0,L.finalized=!0,$t.litElementHydrateSupport?.({LitElement:L});var Ro=$t.litElementPolyfillSupport;Ro?.({LitElement:L});($t.litElementVersions??=[]).push("4.2.2");var gs={tf_day:"1T",tf_week:"1W",tf_month:"1M",tf_six_month:"6M",tf_year:"1J",aria_timeframe:"Zeitraum",aria_currency:"W\xE4hrung",search_placeholder:"Name, Symbol oder ISIN",search_none:"Kein Wallet passt zu \u201E{query}\u201C.",aria_search:"Wallets durchsuchen",aria_search_clear:"Suche leeren",return_day:"Rendite \xFCber 1 Tag",return_week:"Rendite \xFCber 1 Woche",return_month:"Rendite \xFCber 1 Monat",return_six_month:"Rendite \xFCber 6 Monate",return_year:"Rendite \xFCber 1 Jahr",value_line:"Gesamtwert, {start} \u2013 heute",value_line_day:"Gesamtwert, letzte 24 Stunden",cash:"Bargeld",cash_plus:"Cash Plus",staked:"{share} im Staking",show_all:"Alle anzeigen ({count})",show_less:"Weniger anzeigen",detail_available:"Verf\xFCgbar",detail_staked:"Im Staking",detail_staking_apr:"Staking-APR",detail_average_buy_price:"\xD8 Kaufpreis",detail_invested:"Investiert",detail_profit_loss:"Gewinn / Verlust",detail_rewards:"Staking-Belohnungen",detail_rewards_net:"Netto, gesamt",detail_rewards_worth:"heute {value} wert",detail_payouts:"Gutschriften",detail_payouts_value:"{count} \xB7 zuletzt {date}",shares_one:"St\xFCck",shares_other:"St\xFCck",assets_missing_one:"Dazu geh\xF6rt ein gew\xE4hltes Asset, das es gerade nicht gibt. Es bleibt gespeichert und gilt wieder, sobald es wieder da ist.",assets_missing_other:"Dazu geh\xF6ren {count} gew\xE4hlte Assets, die es gerade nicht gibt. Sie bleiben gespeichert und gelten wieder, sobald sie wieder da sind.",eye_hide:"Betr\xE4ge verbergen",eye_show:"Betr\xE4ge anzeigen",change_since:"\xC4nderung seit {date}",ecb_footer:"Preise in {currency}: Bitpandas Euro-Preise, umgerechnet zum EZB-Referenzkurs vom {date}. Die Prozente und Betr\xE4ge in {currency} enthalten deshalb auch die Bewegung des Wechselkurses.",empty_portfolio:"Richte das Bitpanda Portfolio ein oder aktiviere es, dann erscheint es hier.",empty_wallets:"Noch keine Wallets.",empty_selection_wallets:"Keine Wallets in der Auswahl dieser Karte.",empty_selection_assets:"Keine Assets in der Auswahl dieser Karte.",empty_price_tracker:"Richte den Bitpanda Price Tracker ein oder aktiviere ihn und f\xFCge Assets hinzu, dann erscheinen sie hier.",picker_portfolio:"Gesamtwert und Rendite mit Verlauf, Bargeld und Cash Plus, Verteilung und deine Wallets; jeder Teil l\xE4sst sich ausblenden.",picker_price_tracker:"Preise und \xC4nderungen deiner verfolgten Assets, je mit Verlauf, als Liste oder Kacheln.",invalid_option:"Ung\xFCltiger Wert f\xFCr \u201E{option}\u201C: {value}. Erlaubt: {allowed}.",allowed_text:"Text",allowed_assets:"eine Liste von Asset-IDs oder Ger\xE4te-IDs",allowed_groups:"eine Liste aus {values}",group_content:"Inhalt",group_wallets:"Wallets",group_assets:"Assets",group_appearance:"Darstellung",opt_title:"Titel",opt_title_help:"Leer lassen f\xFCr den grau angezeigten Namen",opt_timeframe:"Standard-Zeitraum",opt_timeframe_help:"Die Tasten 1T bis 1J auf der Karte wechseln ihn nur vor\xFCbergehend",tfo_day:"1 Tag",tfo_week:"1 Woche",tfo_month:"1 Monat",tfo_six_month:"6 Monate",tfo_year:"1 Jahr",opt_show_cash:"Bargeld und Cash Plus",opt_show_allocation:"Verteilung",opt_show_allocation_help:"Der farbige Balken mit den Anteilen der Asset-Gruppen und des Bargelds",opt_show_total:"Gesamtwert und Rendite",opt_show_total_help:"Die Zeitraum-Tasten bleiben, solange der Verlauf gezeigt wird",opt_show_line:"Verlauf des Gesamtwerts",opt_show_wallets:"Wallets",opt_group_wallets:"Wallets in Asset-Gruppen",opt_show_search:"Suchfeld",opt_show_search_help:"Findet Wallets nach Name, Symbol oder ISIN",opt_sort:"Sortieren nach",sort_value:"Wert",sort_return:"Rendite seit Kauf",sort_name:"Name",sort_selection:"Reihenfolge wie gew\xE4hlt",sort_change_desc:"\xC4nderung, h\xF6chste zuerst",sort_change_asc:"\xC4nderung, niedrigste zuerst",opt_sort_help_tracker:"\u201EReihenfolge wie gew\xE4hlt\u201C gilt nur mit \u201ENur die gew\xE4hlten\u201C Assets, sonst nach Name",opt_group_selection:"Angezeigte Asset-Gruppen",opt_group_selection_help:"Gilt nur f\xFCr die Wallets; Gesamtwert, Bargeld, Cash Plus und Verteilung zeigen immer das ganze Portfolio",opt_groups:"Asset-Gruppen w\xE4hlen",opt_asset_selection:"Angezeigte Assets",opt_asset_selection_wallets:"Angezeigte Wallets",sel_all:"Alle",sel_all_except:"Alle au\xDFer den gew\xE4hlten",sel_only:"Nur die gew\xE4hlten",opt_assets:"Assets w\xE4hlen",opt_assets_wallets:"Wallets w\xE4hlen",opt_assets_help:"Ein Asset aus einer ausgeblendeten Asset-Gruppe bleibt verborgen, auch wenn es hier gew\xE4hlt ist",opt_assets_help_wallets:"Ein Wallet aus einer ausgeblendeten Asset-Gruppe bleibt verborgen, auch wenn es hier gew\xE4hlt ist",opt_hide_amounts:"Betr\xE4ge zun\xE4chst verbergen",opt_hide_amounts_help:"Prozente bleiben sichtbar; das Auge oben auf der Karte zeigt die Betr\xE4ge nur vor\xFCbergehend",opt_limit:"Assets vor \u201EAlle anzeigen\u201C",opt_limit_wallets:"Wallets vor \u201EAlle anzeigen\u201C",opt_limit_help:"0 zeigt alle Assets",opt_limit_help_wallets:"Nur wenn \u201EWallets in Asset-Gruppen\u201C aus ist; 0 zeigt alle",opt_layout:"Anzeigen als",layout_list:"Liste",layout_tiles:"Kacheln",opt_currency:"Standard-W\xE4hrung",opt_currency_help:"Die Tasten auf der Karte wechseln sie nur vor\xFCbergehend; weitere W\xE4hrungen \xFCber \u201EKonfigurieren\u201C beim Price Tracker"};var ys={tf_day:"1D",tf_week:"1W",tf_month:"1M",tf_six_month:"6M",tf_year:"1Y",aria_timeframe:"Timeframe",aria_currency:"Currency",search_placeholder:"Name, symbol or ISIN",search_none:"No wallet matches \u201C{query}\u201D.",aria_search:"Search wallets",aria_search_clear:"Clear search",return_day:"return over 1 day",return_week:"return over 1 week",return_month:"return over 1 month",return_six_month:"return over 6 months",return_year:"return over 1 year",value_line:"Total value, {start} \u2013 today",value_line_day:"Total value, last 24 hours",cash:"Cash",cash_plus:"Cash Plus",staked:"{share} staked",show_all:"Show all ({count})",show_less:"Show less",detail_available:"Available",detail_staked:"Staked",detail_staking_apr:"Staking APR",detail_average_buy_price:"Average buy price",detail_invested:"Invested",detail_profit_loss:"Profit / loss",detail_rewards:"Staking rewards",detail_rewards_net:"Net, all time",detail_rewards_worth:"worth {value} today",detail_payouts:"Payouts",detail_payouts_value:"{count} \xB7 last {date}",shares_one:"share",shares_other:"shares",assets_missing_one:"This includes a chosen asset that is not there right now. It stays saved and applies again once it is back.",assets_missing_other:"This includes {count} chosen assets that are not there right now. They stay saved and apply again once they are back.",eye_hide:"Hide amounts",eye_show:"Show amounts",change_since:"Change since {date}",ecb_footer:"Prices in {currency}: Bitpanda's EUR prices converted at the ECB reference rate of {date}. The percentages and amounts in {currency} therefore also include the exchange rate's move.",empty_portfolio:"Set up the Bitpanda Portfolio or enable it to see it here.",empty_wallets:"No wallets yet.",empty_selection_wallets:"No wallets in this card's selection.",empty_selection_assets:"No assets in this card's selection.",empty_price_tracker:"Set up the Bitpanda Price Tracker or enable it and add assets to it to see them here.",picker_portfolio:"Total value and return with a value line, Cash and Cash Plus, allocation and your wallets; each part can be left out.",picker_price_tracker:"Prices and changes of the assets you track, each with a line, as a list or tiles.",invalid_option:"Invalid value for \u201C{option}\u201D: {value}. Allowed: {allowed}.",allowed_text:"text",allowed_assets:"a list of asset IDs or device IDs",allowed_groups:"a list of {values}",group_content:"Content",group_wallets:"Wallets",group_assets:"Assets",group_appearance:"Appearance",opt_title:"Title",opt_title_help:"Leave empty for the name shown in grey",opt_timeframe:"Default timeframe",opt_timeframe_help:"The 1D to 1Y buttons on the card change it only temporarily",tfo_day:"1 day",tfo_week:"1 week",tfo_month:"1 month",tfo_six_month:"6 months",tfo_year:"1 year",opt_show_cash:"Cash and Cash Plus",opt_show_allocation:"Allocation bar",opt_show_allocation_help:"The coloured bar showing the share of each asset group and of cash",opt_show_total:"Total value and return",opt_show_total_help:"The timeframe buttons stay while the line is shown",opt_show_line:"Total value line",opt_show_wallets:"Wallets",opt_group_wallets:"Wallets in asset groups",opt_show_search:"Search field",opt_show_search_help:"Finds wallets by name, symbol or ISIN",opt_sort:"Sort by",sort_value:"Value",sort_return:"Return since purchase",sort_name:"Name",sort_selection:"Order as chosen",sort_change_desc:"Change, highest first",sort_change_asc:"Change, lowest first",opt_sort_help_tracker:"\u201COrder as chosen\u201D applies only when assets are set to \u201COnly the ones chosen\u201D; otherwise by name",opt_group_selection:"Asset groups shown",opt_group_selection_help:"Applies to the wallets only; total value, Cash, Cash Plus and allocation always show the whole portfolio",opt_groups:"Choose asset groups",opt_asset_selection:"Assets shown",opt_asset_selection_wallets:"Wallets shown",sel_all:"All",sel_all_except:"All except the ones chosen",sel_only:"Only the ones chosen",opt_assets:"Choose assets",opt_assets_wallets:"Choose wallets",opt_assets_help:"An asset from a hidden asset group stays hidden, even when chosen here",opt_assets_help_wallets:"A wallet from a hidden asset group stays hidden, even when chosen here",opt_hide_amounts:"Hide amounts initially",opt_hide_amounts_help:"Percentages stay visible; the eye at the top of the card shows the amounts only temporarily",opt_limit:"Assets before \u201CShow all\u201D",opt_limit_wallets:"Wallets before \u201CShow all\u201D",opt_limit_help:"0 shows every asset",opt_limit_help_wallets:"Only while \u201CWallets in asset groups\u201D is off; 0 shows all",opt_layout:"Show as",layout_list:"List",layout_tiles:"Tiles",opt_currency:"Default currency",opt_currency_help:"The buttons on the card change it only temporarily; more currencies via \u201CConfigure\u201D on the Price Tracker"};var ws={tf_day:"1D",tf_week:"1S",tf_month:"1M",tf_six_month:"6M",tf_year:"1A",aria_timeframe:"Periodo",aria_currency:"Moneda",search_placeholder:"Nombre, s\xEDmbolo o ISIN",search_none:"Ning\xFAn wallet coincide con \xAB{query}\xBB.",aria_search:"Buscar wallets",aria_search_clear:"Borrar b\xFAsqueda",return_day:"rentabilidad en 1 d\xEDa",return_week:"rentabilidad en 1 semana",return_month:"rentabilidad en 1 mes",return_six_month:"rentabilidad en 6 meses",return_year:"rentabilidad en 1 a\xF1o",value_line:"Valor total, {start} \u2013 hoy",value_line_day:"Valor total, \xFAltimas 24 horas",cash:"Efectivo",cash_plus:"Cash Plus",staked:"{share} en staking",show_all:"Mostrar todo ({count})",show_less:"Mostrar menos",detail_available:"Disponible",detail_staked:"En staking",detail_staking_apr:"APR de staking",detail_average_buy_price:"Precio medio de compra",detail_invested:"Importe invertido",detail_profit_loss:"Ganancia / p\xE9rdida",detail_rewards:"Recompensas de staking",detail_rewards_net:"Neto, en total",detail_rewards_worth:"hoy valen {value}",detail_payouts:"Pagos",detail_payouts_value:"{count} \xB7 \xFAltimo el {date}",shares_one:"t\xEDtulo",shares_other:"t\xEDtulos",shares_many:"t\xEDtulos",assets_missing_one:"Incluye un activo elegido que ahora mismo no existe. Se queda guardado y vuelve a aplicarse en cuanto vuelva.",assets_missing_many:"Incluye {count} activos elegidos que ahora mismo no existen. Se quedan guardados y vuelven a aplicarse en cuanto vuelvan.",assets_missing_other:"Incluye {count} activos elegidos que ahora mismo no existen. Se quedan guardados y vuelven a aplicarse en cuanto vuelvan.",eye_hide:"Ocultar importes",eye_show:"Mostrar importes",change_since:"Variaci\xF3n desde el {date}",ecb_footer:"Precios en {currency}: precios en EUR de Bitpanda convertidos al tipo de referencia del BCE del {date}. Los porcentajes y los importes en {currency} incluyen por tanto tambi\xE9n la variaci\xF3n del tipo de cambio.",empty_portfolio:"Configura el Bitpanda Portfolio o act\xEDvalo para verlo aqu\xED.",empty_wallets:"Todav\xEDa no hay wallets.",empty_selection_wallets:"Ning\xFAn wallet en la selecci\xF3n de esta tarjeta.",empty_selection_assets:"Ning\xFAn activo en la selecci\xF3n de esta tarjeta.",empty_price_tracker:"Configura el Bitpanda Price Tracker o act\xEDvalo y a\xF1ade activos para verlos aqu\xED.",picker_portfolio:"Valor total y rentabilidad con l\xEDnea, efectivo y Cash Plus, distribuci\xF3n y tus wallets; cada parte se puede ocultar.",picker_price_tracker:"Precios y cambios de los activos que sigues, cada uno con su l\xEDnea, en lista o en mosaicos.",invalid_option:"Valor no v\xE1lido para \xAB{option}\xBB: {value}. Permitidos: {allowed}.",allowed_text:"texto",allowed_assets:"una lista de ID de activo o ID de dispositivo",allowed_groups:"una lista de {values}",group_content:"Contenido",group_wallets:"Wallets",group_assets:"Activos",group_appearance:"Apariencia",opt_title:"T\xEDtulo",opt_title_help:"D\xE9jalo vac\xEDo para el nombre mostrado en gris",opt_timeframe:"Periodo predeterminado",opt_timeframe_help:"Los botones 1D a 1A de la tarjeta lo cambian solo temporalmente",tfo_day:"1 d\xEDa",tfo_week:"1 semana",tfo_month:"1 mes",tfo_six_month:"6 meses",tfo_year:"1 a\xF1o",opt_show_cash:"Efectivo y Cash Plus",opt_show_allocation:"Barra de distribuci\xF3n",opt_show_allocation_help:"La barra de colores con la proporci\xF3n de cada grupo de activos y del efectivo",opt_show_total:"Valor total y rentabilidad",opt_show_total_help:"Los botones de periodo se mantienen mientras se muestre la l\xEDnea",opt_show_line:"L\xEDnea del valor total",opt_show_wallets:"Wallets",opt_group_wallets:"Wallets en grupos de activos",opt_show_search:"Campo de b\xFAsqueda",opt_show_search_help:"Encuentra wallets por nombre, s\xEDmbolo o ISIN",opt_sort:"Ordenar por",sort_value:"Valor",sort_return:"Rentabilidad desde la compra",sort_name:"Nombre",sort_selection:"Orden de selecci\xF3n",sort_change_desc:"Cambio, mayor primero",sort_change_asc:"Cambio, menor primero",opt_sort_help_tracker:"\xABOrden de selecci\xF3n\xBB solo se aplica con \xABSolo los elegidos\xBB en los activos; si no, por nombre",opt_group_selection:"Grupos de activos mostrados",opt_group_selection_help:"Solo afecta a los wallets; el valor total, el efectivo, Cash Plus y la distribuci\xF3n muestran siempre toda la cartera",opt_groups:"Elegir grupos de activos",opt_asset_selection:"Activos mostrados",opt_asset_selection_wallets:"Wallets mostrados",sel_all:"Todos",sel_all_except:"Todos excepto los elegidos",sel_only:"Solo los elegidos",opt_assets:"Elegir activos",opt_assets_wallets:"Elegir wallets",opt_assets_help:"Un activo de un grupo de activos oculto sigue oculto, aunque se elija aqu\xED",opt_assets_help_wallets:"Un wallet de un grupo de activos oculto sigue oculto, aunque se elija aqu\xED",opt_hide_amounts:"Ocultar inicialmente los importes",opt_hide_amounts_help:"Los porcentajes siguen visibles; el ojo de la parte superior de la tarjeta muestra los importes solo temporalmente",opt_limit:"Activos antes de \xABMostrar todo\xBB",opt_limit_wallets:"Wallets antes de \xABMostrar todo\xBB",opt_limit_help:"0 muestra todos los activos",opt_limit_help_wallets:"Solo si \xABWallets en grupos de activos\xBB est\xE1 desactivado; 0 muestra todo",opt_layout:"Mostrar como",layout_list:"Lista",layout_tiles:"Mosaicos",opt_currency:"Moneda predeterminada",opt_currency_help:"Los botones de la tarjeta la cambian solo temporalmente; m\xE1s monedas con \xABConfigurar\xBB en el Price Tracker"};var vs={tf_day:"1J",tf_week:"1S",tf_month:"1M",tf_six_month:"6M",tf_year:"1A",aria_timeframe:"P\xE9riode",aria_currency:"Devise",search_placeholder:"Nom, symbole ou ISIN",search_none:"Aucun wallet ne correspond \xE0 \xAB\xA0{query}\xA0\xBB.",aria_search:"Rechercher des wallets",aria_search_clear:"Effacer la recherche",return_day:"rendement sur 1 jour",return_week:"rendement sur 1 semaine",return_month:"rendement sur 1 mois",return_six_month:"rendement sur 6 mois",return_year:"rendement sur 1 an",value_line:"Valeur totale, {start} \u2013 aujourd'hui",value_line_day:"Valeur totale, derni\xE8res 24 heures",cash:"Liquidit\xE9s",cash_plus:"Cash Plus",staked:"{share} en staking",show_all:"Tout afficher ({count})",show_less:"Afficher moins",detail_available:"Disponible",detail_staked:"En staking",detail_staking_apr:"APR du staking",detail_average_buy_price:"Prix d'achat moyen",detail_invested:"Montant investi",detail_profit_loss:"Gain / perte",detail_rewards:"R\xE9compenses de staking",detail_rewards_net:"Net, depuis le d\xE9but",detail_rewards_worth:"valant {value} aujourd'hui",detail_payouts:"Versements",detail_payouts_value:"{count} \xB7 dernier le {date}",shares_one:"titre",shares_other:"titres",shares_many:"titres",assets_missing_one:"Cela inclut un actif choisi qui n'existe pas pour le moment. Il reste enregistr\xE9 et s'applique de nouveau d\xE8s qu'il revient.",assets_missing_many:"Cela inclut {count} actifs choisis qui n'existent pas pour le moment. Ils restent enregistr\xE9s et s'appliquent de nouveau d\xE8s qu'ils reviennent.",assets_missing_other:"Cela inclut {count} actifs choisis qui n'existent pas pour le moment. Ils restent enregistr\xE9s et s'appliquent de nouveau d\xE8s qu'ils reviennent.",eye_hide:"Masquer les montants",eye_show:"Afficher les montants",change_since:"Variation depuis le {date}",ecb_footer:"Prix en {currency}\xA0: prix en EUR de Bitpanda convertis au taux de r\xE9f\xE9rence de la BCE du {date}. Les pourcentages et les montants en {currency} incluent donc aussi la variation du taux de change.",empty_portfolio:"Configurez le Bitpanda Portfolio ou activez-le pour le voir ici.",empty_wallets:"Aucun wallet pour le moment.",empty_selection_wallets:"Aucun wallet dans la s\xE9lection de cette carte.",empty_selection_assets:"Aucun actif dans la s\xE9lection de cette carte.",empty_price_tracker:"Configurez le Bitpanda Price Tracker ou activez-le et ajoutez-y des actifs pour les voir ici.",picker_portfolio:"Valeur totale et rendement avec courbe, liquidit\xE9s et Cash Plus, r\xE9partition et vos wallets\xA0; chaque partie peut \xEAtre masqu\xE9e.",picker_price_tracker:"Prix et variations des actifs que vous suivez, chacun avec sa courbe, en liste ou en tuiles.",invalid_option:"Valeur non valide pour \xAB\xA0{option}\xA0\xBB\xA0: {value}. Valeurs possibles\xA0: {allowed}.",allowed_text:"texte",allowed_assets:"une liste d'ID d'actifs ou d'ID d'appareils",allowed_groups:"une liste d'\xE9l\xE9ments parmi {values}",group_content:"Contenu",group_wallets:"Wallets",group_assets:"Actifs",group_appearance:"Apparence",opt_title:"Titre",opt_title_help:"Laisser vide pour le nom affich\xE9 en gris",opt_timeframe:"P\xE9riode par d\xE9faut",opt_timeframe_help:"Les boutons 1J \xE0 1A de la carte ne la changent que temporairement",tfo_day:"1 jour",tfo_week:"1 semaine",tfo_month:"1 mois",tfo_six_month:"6 mois",tfo_year:"1 an",opt_show_cash:"Liquidit\xE9s et Cash Plus",opt_show_allocation:"Barre de r\xE9partition",opt_show_allocation_help:"La barre color\xE9e avec la part de chaque groupe d'actifs et des liquidit\xE9s",opt_show_total:"Valeur totale et rendement",opt_show_total_help:"Les boutons de p\xE9riode restent tant que la courbe est affich\xE9e",opt_show_line:"Courbe de la valeur totale",opt_show_wallets:"Wallets",opt_group_wallets:"Wallets par groupe d'actifs",opt_show_search:"Champ de recherche",opt_show_search_help:"Trouve les wallets par nom, symbole ou ISIN",opt_sort:"Trier par",sort_value:"Valeur",sort_return:"Rendement depuis l'achat",sort_name:"Nom",sort_selection:"Ordre de s\xE9lection",sort_change_desc:"Variation, la plus forte d'abord",sort_change_asc:"Variation, la plus faible d'abord",opt_sort_help_tracker:"\xAB\xA0Ordre de s\xE9lection\xA0\xBB ne s'applique qu'avec \xAB\xA0Seulement ceux choisis\xA0\xBB pour les actifs\xA0; sinon, tri par nom",opt_group_selection:"Groupes d'actifs affich\xE9s",opt_group_selection_help:"S'applique seulement aux wallets\xA0; la valeur totale, les liquidit\xE9s, Cash Plus et la r\xE9partition portent toujours sur l'ensemble du portefeuille",opt_groups:"Choisir les groupes d'actifs",opt_asset_selection:"Actifs affich\xE9s",opt_asset_selection_wallets:"Wallets affich\xE9s",sel_all:"Tous",sel_all_except:"Tous sauf ceux choisis",sel_only:"Seulement ceux choisis",opt_assets:"Choisir les actifs",opt_assets_wallets:"Choisir les wallets",opt_assets_help:"Un actif d'un groupe d'actifs masqu\xE9 reste masqu\xE9, m\xEAme s'il est choisi ici",opt_assets_help_wallets:"Un wallet d'un groupe d'actifs masqu\xE9 reste masqu\xE9, m\xEAme s'il est choisi ici",opt_hide_amounts:"Masquer initialement les montants",opt_hide_amounts_help:"Les pourcentages restent visibles\xA0; l'\u0153il en haut de la carte n'affiche les montants que temporairement",opt_limit:"Actifs avant \xAB\xA0Tout afficher\xA0\xBB",opt_limit_wallets:"Wallets avant \xAB\xA0Tout afficher\xA0\xBB",opt_limit_help:"0 affiche tous les actifs",opt_limit_help_wallets:"Seulement si \xAB\xA0Wallets par groupe d'actifs\xA0\xBB est d\xE9sactiv\xE9\xA0; 0 affiche tout",opt_layout:"Afficher en",layout_list:"Liste",layout_tiles:"Tuiles",opt_currency:"Devise par d\xE9faut",opt_currency_help:"Les boutons de la carte ne la changent que temporairement\xA0; d'autres devises via \xAB\xA0Configurer\xA0\xBB dans le Price Tracker"};var bs={tf_day:"1G",tf_week:"1S",tf_month:"1M",tf_six_month:"6M",tf_year:"1A",aria_timeframe:"Periodo",aria_currency:"Valuta",search_placeholder:"Nome, simbolo o ISIN",search_none:"Nessun wallet corrisponde a \xAB{query}\xBB.",aria_search:"Cerca nei wallet",aria_search_clear:"Cancella ricerca",return_day:"rendimento su 1 giorno",return_week:"rendimento su 1 settimana",return_month:"rendimento su 1 mese",return_six_month:"rendimento su 6 mesi",return_year:"rendimento su 1 anno",value_line:"Valore totale, {start} \u2013 oggi",value_line_day:"Valore totale, ultime 24 ore",cash:"Liquidit\xE0",cash_plus:"Cash Plus",staked:"{share} in staking",show_all:"Mostra tutto ({count})",show_less:"Mostra meno",detail_available:"Disponibile",detail_staked:"In staking",detail_staking_apr:"APR dello staking",detail_average_buy_price:"Prezzo medio di acquisto",detail_invested:"Importo investito",detail_profit_loss:"Profitto / perdita",detail_rewards:"Ricompense di staking",detail_rewards_net:"Netto, in totale",detail_rewards_worth:"oggi valgono {value}",detail_payouts:"Accrediti",detail_payouts_value:"{count} \xB7 ultimo il {date}",shares_one:"pezzo",shares_other:"pezzi",shares_many:"pezzi",assets_missing_one:"Include un asset scelto che al momento non c'\xE8. Resta salvato e torna a valere appena \xE8 di nuovo disponibile.",assets_missing_many:"Include {count} asset scelti che al momento non ci sono. Restano salvati e tornano a valere appena sono di nuovo disponibili.",assets_missing_other:"Include {count} asset scelti che al momento non ci sono. Restano salvati e tornano a valere appena sono di nuovo disponibili.",eye_hide:"Nascondi gli importi",eye_show:"Mostra gli importi",change_since:"Variazione dal {date}",ecb_footer:"Prezzi in {currency}: prezzi in EUR di Bitpanda convertiti al tasso di riferimento BCE del {date}. Le percentuali e gli importi in {currency} includono quindi anche la variazione del tasso di cambio.",empty_portfolio:"Configura il Bitpanda Portfolio o attivalo per vederlo qui.",empty_wallets:"Ancora nessun wallet.",empty_selection_wallets:"Nessun wallet nella selezione di questa scheda.",empty_selection_assets:"Nessun asset nella selezione di questa scheda.",empty_price_tracker:"Configura il Bitpanda Price Tracker o attivalo e aggiungi degli asset per vederli qui.",picker_portfolio:"Valore totale e rendimento con linea, liquidit\xE0 e Cash Plus, ripartizione e i tuoi wallet; ogni parte si pu\xF2 nascondere.",picker_price_tracker:"Prezzi e variazioni degli asset che segui, ognuno con la sua linea, come elenco o riquadri.",invalid_option:"Valore non valido per \xAB{option}\xBB: {value}. Consentiti: {allowed}.",allowed_text:"testo",allowed_assets:"un elenco di ID asset o ID dispositivo",allowed_groups:"un elenco di valori tra {values}",group_content:"Contenuto",group_wallets:"Wallet",group_assets:"Asset",group_appearance:"Aspetto",opt_title:"Titolo",opt_title_help:"Lascia vuoto per il nome mostrato in grigio",opt_timeframe:"Periodo predefinito",opt_timeframe_help:"I pulsanti da 1G a 1A sulla scheda lo cambiano solo temporaneamente",tfo_day:"1 giorno",tfo_week:"1 settimana",tfo_month:"1 mese",tfo_six_month:"6 mesi",tfo_year:"1 anno",opt_show_cash:"Liquidit\xE0 e Cash Plus",opt_show_allocation:"Barra di ripartizione",opt_show_allocation_help:"La barra colorata con le quote dei gruppi di asset e della liquidit\xE0",opt_show_total:"Valore totale e rendimento",opt_show_total_help:"I pulsanti del periodo restano finch\xE9 \xE8 mostrata la linea",opt_show_line:"Linea del valore totale",opt_show_wallets:"Wallet",opt_group_wallets:"Wallet in gruppi di asset",opt_show_search:"Campo di ricerca",opt_show_search_help:"Trova i wallet per nome, simbolo o ISIN",opt_sort:"Ordina per",sort_value:"Valore",sort_return:"Rendimento dall'acquisto",sort_name:"Nome",sort_selection:"Ordine di selezione",sort_change_desc:"Variazione, maggiore prima",sort_change_asc:"Variazione, minore prima",opt_sort_help_tracker:"\xABOrdine di selezione\xBB vale solo con \xABSolo quelli scelti\xBB per gli asset; altrimenti per nome",opt_group_selection:"Gruppi di asset mostrati",opt_group_selection_help:"Vale solo per i wallet; valore totale, liquidit\xE0, Cash Plus e ripartizione mostrano sempre l'intero portafoglio",opt_groups:"Scegli i gruppi di asset",opt_asset_selection:"Asset mostrati",opt_asset_selection_wallets:"Wallet mostrati",sel_all:"Tutti",sel_all_except:"Tutti tranne quelli scelti",sel_only:"Solo quelli scelti",opt_assets:"Scegli gli asset",opt_assets_wallets:"Scegli i wallet",opt_assets_help:"Un asset di un gruppo di asset nascosto resta nascosto, anche se scelto qui",opt_assets_help_wallets:"Un wallet di un gruppo di asset nascosto resta nascosto, anche se scelto qui",opt_hide_amounts:"Nascondi inizialmente gli importi",opt_hide_amounts_help:"Le percentuali restano visibili; l'occhio in alto nella scheda mostra gli importi solo temporaneamente",opt_limit:"Asset prima di \xABMostra tutto\xBB",opt_limit_wallets:"Wallet prima di \xABMostra tutto\xBB",opt_limit_help:"0 mostra tutti gli asset",opt_limit_help_wallets:"Solo se \xABWallet in gruppi di asset\xBB \xE8 disattivato; 0 mostra tutto",opt_layout:"Mostra come",layout_list:"Elenco",layout_tiles:"Riquadri",opt_currency:"Valuta predefinita",opt_currency_help:"I pulsanti sulla scheda la cambiano solo temporaneamente; altre valute tramite \xABConfigura\xBB nel Price Tracker"};var xs={tf_day:"1D",tf_week:"1W",tf_month:"1M",tf_six_month:"6M",tf_year:"1J",aria_timeframe:"Periode",aria_currency:"Valuta",search_placeholder:"Naam, symbool of ISIN",search_none:"Geen wallet past bij \u2018{query}\u2019.",aria_search:"Wallets doorzoeken",aria_search_clear:"Zoekopdracht wissen",return_day:"rendement over 1 dag",return_week:"rendement over 1 week",return_month:"rendement over 1 maand",return_six_month:"rendement over 6 maanden",return_year:"rendement over 1 jaar",value_line:"Totale waarde, {start} \u2013 vandaag",value_line_day:"Totale waarde, laatste 24 uur",cash:"Contanten",cash_plus:"Cash Plus",staked:"{share} in staking",show_all:"Alles tonen ({count})",show_less:"Minder tonen",detail_available:"Beschikbaar",detail_staked:"In staking",detail_staking_apr:"Staking-APR",detail_average_buy_price:"Gemiddelde aankoopprijs",detail_invested:"Ge\xEFnvesteerd",detail_profit_loss:"Winst / verlies",detail_rewards:"Stakingbeloningen",detail_rewards_net:"Netto, totaal",detail_rewards_worth:"vandaag {value} waard",detail_payouts:"Uitbetalingen",detail_payouts_value:"{count} \xB7 laatste {date}",shares_one:"stuk",shares_other:"stuks",assets_missing_one:"Hieronder valt een gekozen asset die er nu niet is. Die blijft bewaard en geldt weer zodra die terug is.",assets_missing_other:"Hieronder vallen {count} gekozen assets die er nu niet zijn. Ze blijven bewaard en gelden weer zodra ze terug zijn.",eye_hide:"Bedragen verbergen",eye_show:"Bedragen tonen",change_since:"Verandering sinds {date}",ecb_footer:"Prijzen in {currency}: de EUR-prijzen van Bitpanda, omgerekend tegen de ECB-referentiekoers van {date}. De percentages en bedragen in {currency} bevatten daardoor ook de beweging van de wisselkoers.",empty_portfolio:"Stel het Bitpanda Portfolio in of schakel het in om het hier te zien.",empty_wallets:"Nog geen wallets.",empty_selection_wallets:"Geen wallets in de selectie van deze kaart.",empty_selection_assets:"Geen assets in de selectie van deze kaart.",empty_price_tracker:"Stel de Bitpanda Price Tracker in of schakel hem in en voeg er assets aan toe om ze hier te zien.",picker_portfolio:"Totale waarde en rendement met een lijn, contanten en Cash Plus, verdeling en je wallets; elk deel kan worden verborgen.",picker_price_tracker:"Prijzen en veranderingen van de assets die je volgt, elk met een lijn, als lijst of tegels.",invalid_option:"Ongeldige waarde voor \u2018{option}\u2019: {value}. Toegestaan: {allowed}.",allowed_text:"tekst",allowed_assets:"een lijst met asset-ID's of apparaat-ID's",allowed_groups:"een lijst met waarden uit {values}",group_content:"Inhoud",group_wallets:"Wallets",group_assets:"Assets",group_appearance:"Uiterlijk",opt_title:"Titel",opt_title_help:"Leeg laten voor de grijs getoonde naam",opt_timeframe:"Standaardperiode",opt_timeframe_help:"De knoppen 1D tot 1J op de kaart wijzigen die alleen tijdelijk",tfo_day:"1 dag",tfo_week:"1 week",tfo_month:"1 maand",tfo_six_month:"6 maanden",tfo_year:"1 jaar",opt_show_cash:"Contanten en Cash Plus",opt_show_allocation:"Verdelingsbalk",opt_show_allocation_help:"De gekleurde balk met het aandeel van elke assetgroep en van de contanten",opt_show_total:"Totale waarde en rendement",opt_show_total_help:"De periodeknoppen blijven zolang de lijn wordt getoond",opt_show_line:"Lijn van de totale waarde",opt_show_wallets:"Wallets",opt_group_wallets:"Wallets in assetgroepen",opt_show_search:"Zoekveld",opt_show_search_help:"Vindt wallets op naam, symbool of ISIN",opt_sort:"Sorteren op",sort_value:"Waarde",sort_return:"Rendement sinds aankoop",sort_name:"Naam",sort_selection:"Volgorde zoals gekozen",sort_change_desc:"Verandering, hoogste eerst",sort_change_asc:"Verandering, laagste eerst",opt_sort_help_tracker:"\u2018Volgorde zoals gekozen\u2019 geldt alleen bij \u2018Alleen de gekozen\u2019 assets, anders op naam",opt_group_selection:"Getoonde assetgroepen",opt_group_selection_help:"Geldt alleen voor de wallets; totale waarde, contanten, Cash Plus en verdeling tonen altijd het hele portfolio",opt_groups:"Assetgroepen kiezen",opt_asset_selection:"Getoonde assets",opt_asset_selection_wallets:"Getoonde wallets",sel_all:"Alle",sel_all_except:"Alle behalve de gekozen",sel_only:"Alleen de gekozen",opt_assets:"Assets kiezen",opt_assets_wallets:"Wallets kiezen",opt_assets_help:"Een asset uit een verborgen assetgroep blijft verborgen, ook als die hier is gekozen",opt_assets_help_wallets:"Een wallet uit een verborgen assetgroep blijft verborgen, ook als die hier is gekozen",opt_hide_amounts:"Bedragen aanvankelijk verbergen",opt_hide_amounts_help:"Percentages blijven zichtbaar; het oog bovenaan de kaart toont de bedragen alleen tijdelijk",opt_limit:"Assets v\xF3\xF3r \u2018Alles tonen\u2019",opt_limit_wallets:"Wallets v\xF3\xF3r \u2018Alles tonen\u2019",opt_limit_help:"0 toont alle assets",opt_limit_help_wallets:"Alleen als \u2018Wallets in assetgroepen\u2019 uit staat; 0 toont alles",opt_layout:"Weergeven als",layout_list:"Lijst",layout_tiles:"Tegels",opt_currency:"Standaardvaluta",opt_currency_help:"De knoppen op de kaart wijzigen die alleen tijdelijk; meer valuta via \u2018Configureren\u2019 bij de Price Tracker"};var ks={tf_day:"1D",tf_week:"1T",tf_month:"1M",tf_six_month:"6M",tf_year:"1R",aria_timeframe:"Okres",aria_currency:"Waluta",search_placeholder:"Nazwa, symbol lub ISIN",search_none:"\u017Baden portfel nie pasuje do \u201E{query}\u201D.",aria_search:"Szukaj portfeli",aria_search_clear:"Wyczy\u015B\u0107 wyszukiwanie",return_day:"stopa zwrotu za 1 dzie\u0144",return_week:"stopa zwrotu za 1 tydzie\u0144",return_month:"stopa zwrotu za 1 miesi\u0105c",return_six_month:"stopa zwrotu za 6 miesi\u0119cy",return_year:"stopa zwrotu za 1 rok",value_line:"Warto\u015B\u0107 ca\u0142kowita, {start} \u2013 dzi\u015B",value_line_day:"Warto\u015B\u0107 ca\u0142kowita, ostatnie 24 godziny",cash:"Got\xF3wka",cash_plus:"Cash Plus",staked:"{share} w stakingu",show_all:"Poka\u017C wszystkie ({count})",show_less:"Poka\u017C mniej",detail_available:"Dost\u0119pne",detail_staked:"W stakingu",detail_staking_apr:"APR stakingu",detail_average_buy_price:"\u015Arednia cena zakupu",detail_invested:"Zainwestowano",detail_profit_loss:"Zysk / strata",detail_rewards:"Nagrody za staking",detail_rewards_net:"Netto, \u0142\u0105cznie",detail_rewards_worth:"dzi\u015B warte {value}",detail_payouts:"Naliczenia",detail_payouts_value:"{count} \xB7 ostatnio {date}",shares_one:"sztuka",shares_other:"sztuki",shares_few:"sztuki",shares_many:"sztuk",assets_missing_one:"Obejmuje to jedno wybrane aktywo, kt\xF3rego teraz nie ma. Pozostaje zapisane i zn\xF3w obowi\u0105zuje, gdy wr\xF3ci.",assets_missing_few:"Obejmuje to {count} wybrane aktywa, kt\xF3rych teraz nie ma. Pozostaj\u0105 zapisane i zn\xF3w obowi\u0105zuj\u0105, gdy wr\xF3c\u0105.",assets_missing_many:"Obejmuje to {count} wybranych aktyw\xF3w, kt\xF3rych teraz nie ma. Pozostaj\u0105 zapisane i zn\xF3w obowi\u0105zuj\u0105, gdy wr\xF3c\u0105.",assets_missing_other:"Obejmuje to {count} wybranego aktywa, kt\xF3rego teraz nie ma. Pozostaje zapisane i zn\xF3w obowi\u0105zuje, gdy wr\xF3ci.",eye_hide:"Ukryj kwoty",eye_show:"Poka\u017C kwoty",change_since:"Zmiana od {date}",ecb_footer:"Ceny w {currency}: ceny Bitpandy w EUR przeliczone po kursie referencyjnym EBC z {date}. Warto\u015Bci procentowe i kwoty w {currency} obejmuj\u0105 wi\u0119c r\xF3wnie\u017C zmian\u0119 kursu walutowego.",empty_portfolio:"Skonfiguruj Bitpanda Portfolio lub je w\u0142\u0105cz, aby zobaczy\u0107 je tutaj.",empty_wallets:"Brak portfeli.",empty_selection_wallets:"Brak portfeli w wyborze tej karty.",empty_selection_assets:"Brak aktyw\xF3w w wyborze tej karty.",empty_price_tracker:"Skonfiguruj Bitpanda Price Tracker lub go w\u0142\u0105cz i dodaj aktywa, aby zobaczy\u0107 je tutaj.",picker_portfolio:"Warto\u015B\u0107 ca\u0142kowita i stopa zwrotu z wykresem, got\xF3wka i Cash Plus, alokacja oraz twoje portfele; ka\u017Cd\u0105 cz\u0119\u015B\u0107 mo\u017Cna ukry\u0107.",picker_price_tracker:"Ceny i zmiany \u015Bledzonych aktyw\xF3w, ka\u017Cde z wykresem, jako lista lub kafelki.",invalid_option:"Nieprawid\u0142owa warto\u015B\u0107 dla \u201E{option}\u201D: {value}. Dozwolone: {allowed}.",allowed_text:"tekst",allowed_assets:"lista identyfikator\xF3w aktyw\xF3w lub urz\u0105dze\u0144",allowed_groups:"lista warto\u015Bci spo\u015Br\xF3d {values}",group_content:"Zawarto\u015B\u0107",group_wallets:"Portfele",group_assets:"Aktywa",group_appearance:"Wygl\u0105d",opt_title:"Tytu\u0142",opt_title_help:"Pozostaw puste, aby u\u017Cy\u0107 nazwy pokazanej na szaro",opt_timeframe:"Domy\u015Blny okres",opt_timeframe_help:"Przyciski od 1D do 1R na karcie zmieniaj\u0105 go tylko tymczasowo",tfo_day:"1 dzie\u0144",tfo_week:"1 tydzie\u0144",tfo_month:"1 miesi\u0105c",tfo_six_month:"6 miesi\u0119cy",tfo_year:"1 rok",opt_show_cash:"Got\xF3wka i Cash Plus",opt_show_allocation:"Pasek alokacji",opt_show_allocation_help:"Kolorowy pasek pokazuj\u0105cy udzia\u0142 grup aktyw\xF3w i got\xF3wki",opt_show_total:"Warto\u015B\u0107 ca\u0142kowita i stopa zwrotu",opt_show_total_help:"Przyciski okresu pozostaj\u0105, dop\xF3ki wy\u015Bwietlany jest wykres",opt_show_line:"Wykres warto\u015Bci ca\u0142kowitej",opt_show_wallets:"Portfele",opt_group_wallets:"Portfele w grupach aktyw\xF3w",opt_show_search:"Pole wyszukiwania",opt_show_search_help:"Znajduje portfele po nazwie, symbolu lub ISIN",opt_sort:"Sortuj wed\u0142ug",sort_value:"Warto\u015B\u0107",sort_return:"Stopa zwrotu od zakupu",sort_name:"Nazwa",sort_selection:"Kolejno\u015B\u0107 wyboru",sort_change_desc:"Zmiana, najwy\u017Csza najpierw",sort_change_asc:"Zmiana, najni\u017Csza najpierw",opt_sort_help_tracker:"\u201EKolejno\u015B\u0107 wyboru\u201D dzia\u0142a tylko przy opcji \u201ETylko wybrane\u201D dla aktyw\xF3w; w przeciwnym razie wed\u0142ug nazwy",opt_group_selection:"Wy\u015Bwietlane grupy aktyw\xF3w",opt_group_selection_help:"Dotyczy tylko portfeli; warto\u015B\u0107 ca\u0142kowita, got\xF3wka, Cash Plus i alokacja zawsze pokazuj\u0105 ca\u0142e portfolio",opt_groups:"Wybierz grupy aktyw\xF3w",opt_asset_selection:"Wy\u015Bwietlane aktywa",opt_asset_selection_wallets:"Wy\u015Bwietlane portfele",sel_all:"Wszystkie",sel_all_except:"Wszystkie opr\xF3cz wybranych",sel_only:"Tylko wybrane",opt_assets:"Wybierz aktywa",opt_assets_wallets:"Wybierz portfele",opt_assets_help:"Aktywo z ukrytej grupy aktyw\xF3w pozostaje ukryte, nawet je\u015Bli wybrano je tutaj",opt_assets_help_wallets:"Portfel z ukrytej grupy aktyw\xF3w pozostaje ukryty, nawet je\u015Bli wybrano go tutaj",opt_hide_amounts:"Pocz\u0105tkowo ukrywaj kwoty",opt_hide_amounts_help:"Procenty pozostaj\u0105 widoczne; oko u g\xF3ry karty pokazuje kwoty tylko tymczasowo",opt_limit:"Aktywa przed \u201EPoka\u017C wszystkie\u201D",opt_limit_wallets:"Portfele przed \u201EPoka\u017C wszystkie\u201D",opt_limit_help:"0 pokazuje wszystkie aktywa",opt_limit_help_wallets:"Tylko gdy opcja \u201EPortfele w grupach aktyw\xF3w\u201D jest wy\u0142\u0105czona; 0 pokazuje wszystkie",opt_layout:"Poka\u017C jako",layout_list:"Lista",layout_tiles:"Kafelki",opt_currency:"Domy\u015Blna waluta",opt_currency_help:"Przyciski na karcie zmieniaj\u0105 j\u0105 tylko tymczasowo; wi\u0119cej walut przez \u201EKonfiguruj\u201D w Price Trackerze"};var $s={en:ys,de:gs,fr:vs,nl:xs,it:bs,es:ws,pl:ks},As=o=>o in $s,Ss="en",zo=o=>{let t=o.toLowerCase().replace(/[-_].*$/,"");return As(t)?t:"en"};function O(o){let t=o??document.querySelector("home-assistant")?.hass;return t?zo(t.locale.language):Ss}function Ts(o){return As(o.locale.language.toLowerCase().replace(/[-_].*$/,""))}function Ie(o){Ss=O(o)}var Cs=o=>$s[O(o)];function u(o,t,e={}){return Cs(o)[t].replace(/\{(\w+)\}/g,(s,n)=>n in e?String(e[n]):s)}function Ne(o,t,e){let s=new Intl.PluralRules(O(o)).select(e);return Cs(o)[`${t}_${s}`].replace("{count}",String(e))}async function Ps(o){await o.loadBackendTranslation("selector","bitpanda")}function At(o,t){return o.localize(`component.bitpanda.selector.asset_group.options.${t}`)||t}var F=["day","week","month","six_month","year"],H=["crypto","stock","etf","etc","index","metal","other"],j=["all","all_except","only"],Es=["EUR","CHF","CZK","DKK","GBP","HUF","NOK","PLN","RON","SEK","TRY","USD"],Me=["value","return","name"];var We=["selection","name","change_desc","change_asc"],Oe=["list","tiles"];var P=o=>({allowed:()=>o.join(", "),check:t=>typeof t=="string"&&o.includes(t)}),D={allowed:()=>"true, false",check:o=>typeof o=="boolean"},Rs={allowed:()=>u(void 0,"allowed_text"),check:o=>typeof o=="string"},je={allowed:()=>"0, 1, 2, \u2026",check:o=>typeof o=="number"&&Number.isInteger(o)&&o>=0},De={allowed:()=>u(void 0,"allowed_assets"),check:o=>Array.isArray(o)&&o.every(t=>typeof t=="string")},Ue={allowed:()=>u(void 0,"allowed_groups",{values:H.join(", ")}),check:o=>Array.isArray(o)&&o.every(t=>H.includes(t))},zs={allowed:()=>"EUR, USD, \u2026",check:o=>typeof o=="string"&&/^[A-Z]{3}$/.test(o)};function Fe(o,t){if(o===null||typeof o!="object"||Array.isArray(o))throw new Error(u(void 0,"invalid_option",{option:"type",value:JSON.stringify(o),allowed:"custom:\u2026"}));let e=Object.fromEntries(Object.entries(o).filter(([,s])=>s!==null));for(let[s,n]of Object.entries(t)){let r=e[s];if(r!==void 0&&!n.check(r))throw new Error(u(void 0,"invalid_option",{option:s,value:JSON.stringify(r),allowed:n.allowed()}))}return e}var oe=(o,t)=>({select:{mode:"dropdown",options:o.map(e=>({value:e,label:t(e)}))}}),St=o=>({name:"title",default:o,selector:{text:{}}}),Tt=()=>({name:"timeframe",selector:oe(F,o=>u(void 0,`tfo_${o}`))}),U=(o,t)=>({name:o,default:t,selector:{boolean:{}}}),Ct=o=>({name:"limit",default:o,selector:{number:{min:0,max:100,mode:"box"}}}),Pt=o=>({name:"sort",selector:oe(o,t=>u(void 0,`sort_${t}`))});function Be(){return document.querySelector("home-assistant")?.hass}var Lo=3e3;async function Ls(o){if(!o)return{};let t;try{let s=(await Promise.race([o.callWS({type:"frontend/get_translations",language:o.language,category:"selector",integration:["bitpanda"]}),new Promise(r=>{t=setTimeout(()=>r(void 0),Lo)})]))?.resources??{},n={};for(let r of H){let i=s[`component.bitpanda.selector.asset_group.options.${r}`];typeof i=="string"&&i&&(n[r]=i)}return n}catch{return{}}finally{clearTimeout(t)}}var Ve=o=>o==="only"||o==="all_except",Et=(o,t)=>[{name:"group_selection",selector:oe(j,e=>u(void 0,`sel_${e}`))},...Ve(t)?[{name:"groups",selector:{select:{multiple:!0,mode:"dropdown",options:H.map(e=>({value:e,label:o[e]??e}))}}}]:[]],Rt=(o,t)=>[{name:"asset_selection",selector:oe(j,e=>u(void 0,`sel_${e}`))},...Ve(t)?[{name:"assets",selector:{device:{multiple:!0,filter:[{integration:"bitpanda",model:o}]}}}]:[]],ye=()=>({type:"divider",name:""}),ne=(o,t)=>({type:"expandable",name:"",flatten:!0,title:u(void 0,o),schema:t}),Ho={title:"opt_title",timeframe:"opt_timeframe",show_total:"opt_show_total",show_graph:"opt_show_line",show_cash:"opt_show_cash",show_allocation:"opt_show_allocation",show_wallets:"opt_show_wallets",group_wallets:"opt_group_wallets",show_search:"opt_show_search",sort:"opt_sort",group_selection:"opt_group_selection",groups:"opt_groups",asset_selection:"opt_asset_selection",assets:"opt_assets",hide_amounts:"opt_hide_amounts",limit:"opt_limit",layout:"opt_layout",currency:"opt_currency"},Io={title:"opt_title_help",timeframe:"opt_timeframe_help",show_total:"opt_show_total_help",show_allocation:"opt_show_allocation_help",hide_amounts:"opt_hide_amounts_help",show_search:"opt_show_search_help",assets:"opt_assets_help",limit:"opt_limit_help",currency:"opt_currency_help"};function zt(o){let t=Ho[o.name];return t?u(void 0,t):void 0}function Lt(o){let t=Io[o.name];return t?u(void 0,t):void 0}var qe=ue`
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
`;var Ge={title:Rs},B=class extends L{constructor(){super(...arguments);this.timeframe="day";this.amountsHidden=!1;this.seriesRevision=0;this.watched=[]}static{this.properties={hass:{attribute:!1},config:{state:!0},timeframe:{state:!0},amountsHidden:{state:!0},seriesRevision:{state:!0}}}static{this.styles=qe}setConfig(e){let s=this.validate(e),n=s;this.config=s,this.timeframe=n.timeframe??"day",this.amountsHidden=n.hide_amounts??!1}toggleAmounts(){this.amountsHidden=!this.amountsHidden}seriesArrived(){this.seriesRevision+=1}selectTimeframe(e){this.timeframe=e}shouldUpdate(e){if(e.size!==1||!e.has("hass"))return!0;let s=e.get("hass"),n=this.hass;return!s||!n||s.entities!==n.entities||s.devices!==n.devices||s.locale!==n.locale||s.localize!==n.localize?!0:this.watched.some(r=>s.states[r]!==n.states[r])}connectedCallback(){super.connectedCallback(),typeof ResizeObserver<"u"&&(this.resizer=new ResizeObserver(()=>this.fitLayout()),this.resizer.observe(this))}disconnectedCallback(){this.resizer?.disconnect(),this.resizer=void 0,super.disconnectedCallback()}updated(e){super.updated(e),this.remeasures(e)&&this.fitLayout()}fitLayout(){}widthMeter(){let e=this.getBoundingClientRect().width,s=e>0&&this.offsetWidth>0?e/this.offsetWidth:1;return(n,r=!1)=>{let i=r?[...n.getClientRects()].reduce((a,l)=>a+l.width,0):n.getBoundingClientRect().width;return Math.round(i/s*100)/100}}remeasures(e){return!0}willUpdate(e){let s=this.hass;if(!s)return;Ie(s);let n=O(s);n!==this.categoryLanguage&&(this.categoryLanguage=n,Ps(s)),this.watched=this.watchedEntities()}getCardSize(){return 3}getGridOptions(){return{columns:12,min_columns:6}}};var No="bitpanda",Hs={return_day:"day",return_week:"week",return_month:"month",return_six_month:"six_month",return_year:"year"},Is=o=>o.replace(/\s+/g,"").toLowerCase();function Mo(o,t){let e=(o??"").trim();return e&&Is(e)!==Is(t)?`${e} (${t})`:t}var Ns=new WeakMap;function Wo(o){let t=Ns.get(o.entities);if(t)return t;let e=new Map;for(let s of Object.values(o.entities)){if(!s||s.platform!==No||!s.device_id)continue;let n=e.get(s.device_id)??[];n.push(s),e.set(s.device_id,n)}return Ns.set(o.entities,e),e}function Ht(o,t){let e=Wo(o),s=[];for(let[n,r]of e){let i=o.devices[n];i?.model===t&&s.push([i,r])}return s}var J=o=>typeof o=="string"&&o!==""?o:void 0,Ms=new Map,Oo=/ (Wallet|Price Tracker)$/;function Os(o,t,e){let s=e.map(i=>o.states[i.entity_id]?.attributes).find(i=>i?.asset),n;if(s){let i=J(s.asset)??"",a=J(s.asset_isin),l=J(s.asset_category),c=J(s.asset_name);n={name:Mo(c,i),shortName:c??i,symbol:i,...a?{isin:a}:{},...l&&H.includes(l)?{category:l}:{}},Ms.set(t.id,n)}else{let i=(J(t.name)??"").replace(Oo,"");n=Ms.get(t.id)??{name:i,shortName:i,symbol:""}}let r=J(t.name_by_user);return{deviceId:t.id,assetId:t.serial_number??"",...n,...r?{name:r,shortName:r}:{}}}function Ke(o){let[t]=Ht(o,"Portfolio");if(!t)return;let[e,s]=t,n={deviceId:e.id,returns:{},wallets:[]};for(let r of s){let i=r.translation_key??"";i==="total_value"?n.totalValue=r.entity_id:i==="cash"?n.cash=r.entity_id:i==="cash_plus"?n.cashPlus=r.entity_id:i in Hs&&(n.returns[Hs[i]]=r.entity_id)}for(let[r,i]of Ht(o,"Wallet")){let a=Os(o,r,i);for(let l of i)l.translation_key==="wallet"?a.available=l.entity_id:l.translation_key==="wallet_total"?a.total=l.entity_id:l.translation_key==="staking"&&(a.staking=l.entity_id);n.wallets.push(a)}return n}function re(o){return Ht(o,"Price Tracker").map(([t,e])=>{let s={};for(let n of e){if(n.translation_key!=="price")continue;let r=J(o.states[n.entity_id]?.attributes.unit_of_measurement);r&&(s[r]=n.entity_id)}return{...Os(o,t,e),prices:s}})}function we(o){let t=new Set(o.flatMap(s=>Object.keys(s.prices))),e=[...t].filter(s=>s!=="EUR").sort();return t.has("EUR")?["EUR",...e]:e}function Ze(o,t,e){if(t==="all")return[...o];let s=t==="only";return o.filter(n=>e.includes(n.category??"other")===s)}var Ws=(o,t)=>t===o.deviceId||t!==""&&t===o.assetId;function Ye(o,t,e){if(t==="all_except")return o.filter(s=>!e.some(n=>Ws(s,n)));if(t==="only"){let s=[];for(let n of e){let r=o.find(i=>Ws(i,n));r&&!s.includes(r)&&s.push(r)}return s}return[...o]}var Je="bitpanda-portfolio-card-editor",Xe="bitpanda-price-tracker-card-editor",jo=[["asset_selection","assets"],["group_selection","groups"]],Do={timeframe:"day",sort:"value",group_selection:"all",asset_selection:"all"},Uo={layout:"list",timeframe:"day",currency:"EUR",sort:"name",group_selection:"all",asset_selection:"all"},Fo=/^[0-9a-f]{32}$/;function js(o,t){return o?Object.values(o.devices).filter(e=>e!==void 0&&e.model===t&&(e.identifiers??[]).some(([s])=>s==="bitpanda")):[]}function Bo(o,t){return o?/[.!?…]$/.test(o)?`${o} ${t}`:`${o}. ${t}`:t}async function Vo(o=customElements,t=window,e=1e4){if(o.get("ha-form"))return;try{await(await(await t.loadCardHelpers?.())?.createCardElement({type:"entities",entities:[]}))?.constructor?.getConfigElement?.()}catch{}let s;await Promise.race([o.whenDefined("ha-form"),new Promise(n=>{s=setTimeout(n,e)})]),clearTimeout(s)}async function et(o){return await Vo(),customElements.get(Je)||customElements.define(Je,It),customElements.get(Xe)||customElements.define(Xe,Nt),document.createElement(o)}var Qe=class extends L{constructor(){super(...arguments);this.names={};this.namesAsked=!1;this.heldBack={}}static{this.properties={hass:{attribute:!1},config:{state:!0},names:{state:!0}}}setConfig(e){this.config=e}chosenAssets(){let e=this.config?.assets,s=js(this.hass,this.model),n=[],r=[];for(let i of Array.isArray(e)?e:[]){let a=s.find(l=>l.id===i||l.serial_number&&l.serial_number===i);a?n.includes(a.id)||n.push(a.id):!Fo.test(i)&&!r.includes(i)&&r.push(i)}return{devices:n,missing:r}}savedAssets(e){let s=js(this.hass,this.model),n=[];for(let r of[...e.map(i=>s.find(a=>a.id===i)?.serial_number||i),...this.chosenAssets().missing])n.includes(r)||n.push(r);return n}willUpdate(e){super.willUpdate(e),this.hass&&(Ie(this.hass),this.namesAsked||(this.namesAsked=!0,Ls(this.hass).then(s=>{this.names=s})))}render(){if(!this.config)return h;let e=this.form(),{devices:s,missing:n}=this.chosenAssets(),r={...this.defaults,...this.config};"assets"in r&&(r.assets=s);let i=n.length===0?e.computeHelper:a=>a.name==="assets"?Bo(e.computeHelper(a),Ne(void 0,"assets_missing",n.length)):e.computeHelper(a);return d`<ha-form
      .hass=${this.hass}
      .data=${r}
      .schema=${e.schema}
      .computeLabel=${e.computeLabel}
      .computeHelper=${i}
      @value-changed=${this.changed}
    ></ha-form>`}changed(e){e.stopPropagation();let s=this.config??{},n=e.detail.value,r=Array.isArray(n.assets)?{...n,assets:this.savedAssets(n.assets)}:n,i=Object.fromEntries(Object.entries(r).filter(([a,l])=>a in s||this.defaults[a]===void 0||l!==this.defaults[a]));for(let[a,l]of jo)Ve(i[a])?!(l in i)&&l in this.heldBack&&(i[l]=this.heldBack[l]):(l in i&&(this.heldBack[l]=i[l]),delete i[l]);this.config=i,this.dispatchEvent(new CustomEvent("config-changed",{detail:{config:i},bubbles:!0,composed:!0}))}},qo={limit:"opt_limit_wallets",asset_selection:"opt_asset_selection_wallets",assets:"opt_assets_wallets"},Go={limit:"opt_limit_help_wallets",group_selection:"opt_group_selection_help",assets:"opt_assets_help_wallets"},It=class extends Qe{constructor(){super(...arguments);this.defaults=Do;this.model="Wallet"}form(){let e=this.config??{};return{schema:[St("Bitpanda Portfolio"),ne("group_content",[Tt(),U("show_total",!0),U("show_graph",!0),U("show_cash",!0),U("show_allocation",!0),U("show_wallets",!0)]),ne("group_wallets",[U("show_search",!1),U("group_wallets",!0),Pt(Me),Ct(5),ye(),...Et(this.names,e.group_selection??"all"),ye(),...Rt("Wallet",e.asset_selection??"all")]),ne("group_appearance",[U("hide_amounts",!1)])],computeLabel:s=>{let n=qo[s.name];return n?u(void 0,n):zt(s)},computeHelper:s=>{let n=Go[s.name];return n?u(void 0,n):Lt(s)}}}};function Ko(o){let t=o?we(re(o)):[];return t.length>0?t:Es}var Nt=class extends Qe{constructor(){super(...arguments);this.defaults=Uo;this.model="Price Tracker"}form(){let e=this.config??{};return{schema:[St("Bitpanda Price Tracker"),ne("group_content",[{name:"layout",selector:oe(Oe,s=>u(void 0,`layout_${s}`))},Tt(),{name:"currency",selector:{select:{mode:"dropdown",options:Ko(this.hass).map(s=>({value:s,label:s}))}}}]),ne("group_assets",[Pt(We),Ct(0),ye(),...Et(this.names,e.group_selection??"all"),ye(),...Rt("Price Tracker",e.asset_selection??"all")])],computeLabel:zt,computeHelper:s=>s.name==="sort"?u(void 0,"opt_sort_help_tracker"):Lt(s)}}};function tt(o){switch(o.locale.number_format){case"comma_decimal":return"en-US";case"decimal_comma":return"de";case"space_comma":return"fr";case"quote_decimal":return"de-CH";case"system":return;default:return o.locale.language}}function Wt(o,t,e,s=0){return new Intl.NumberFormat(tt(o),{maximumFractionDigits:e,minimumFractionDigits:s,useGrouping:o.locale.number_format!=="none"}).format(t)}function Zo(o,t){let e=t!==0&&Math.abs(t)<1e-4;return new Intl.NumberFormat(tt(o),{...e?{maximumSignificantDigits:2}:{maximumFractionDigits:4},roundingMode:"trunc",useGrouping:o.locale.number_format!=="none"}).format(t)}function ve(o,t,e,s,n=!1){let r=n?Zo(o,t):Wt(o,t,8);return e==="stock"||e==="etf"||e==="etc"?`${r} ${Ne(o,"shares",t)}`:`${r} ${e==="metal"?"g":s}`}var st=new Set(["unavailable","unknown"]);function I(o,t){let e=t?o.states[t]:void 0;return e&&!st.has(e.state)?o.formatEntityState(e):void 0}function Ds(o,t,e){let s=t?o.states[t]:void 0;return s&&e!==void 0?o.formatEntityState({...s,state:String(e)}):void 0}function be(o,t,e,s=!1){return Fs(o,t,e,2,s)}function Us(o,t,e){let s=Math.abs(t);return Fs(o,t,e,s>=10||s===0?2:s>=1?4:8,!1)}function Fs(o,t,e,s,n){try{return new Intl.NumberFormat(tt(o),{style:"currency",currency:e,minimumFractionDigits:2,maximumFractionDigits:s,useGrouping:o.locale.number_format!=="none",...n?{signDisplay:"exceptZero"}:{}}).format(t)}catch{return`${Wt(o,t,s)} ${e}`}}function Yo(o){let t=Math.abs(o);return t===0||t>=10?2:t>=1?4:t>=.1?5:t>=.001?6:t>=1e-4?7:8}function Bs(o,t,e){let s=t?o.states[t]:void 0;if(!s||st.has(s.state)||e===void 0||!Number.isFinite(e))return;let n=o.entities[s.entity_id]?.display_precision,r=typeof n=="number"?n:Yo(Number(s.state)),i=Number(e.toFixed(r))===0?0 .toFixed(r):e.toFixed(r),a=o.formatEntityState({...s,state:i});return Number(i)>0?`+${a}`:a}function $(o,t){if(!o||st.has(o.state))return;let e=o.attributes[t];return typeof e=="number"&&Number.isFinite(e)?e:void 0}function k(o,t){let e=t?o.states[t]:void 0;if(!e||st.has(e.state)||e.state.trim()==="")return;let s=Number(e.state);return Number.isFinite(s)?s:void 0}var Jo=new Set(["cs","de","fi","fr","sk","sv"]),Vs=o=>Jo.has(o.locale.language)?"\xA0":"";function N(o,t){if(t===void 0||!Number.isFinite(t))return{text:"\u2014",direction:"none"};let e=new Intl.NumberFormat(tt(o),{minimumFractionDigits:2,maximumFractionDigits:2,signDisplay:"exceptZero",useGrouping:o.locale.number_format!=="none"}).format(t),s=Vs(o),r=Math.round(Math.abs(t)*100)===0?"flat":t>0?"up":"down";return{text:`${e}${s}%`,direction:r}}function ie(o,t,e,s=!1){let n=Vs(o);return`${Wt(o,t,e,s?e:0)}${n}%`}function E(o){return o==="up"||o==="down"?o:""}function X(o){return o==="up"?"\u25B2":o==="down"?"\u25BC":""}function Ot(o){return Ts(o)?o.locale.language:"en"}function qs(o){return o.locale.time_zone==="server"?o.config?.time_zone:void 0}function Xo(o){let t=o.locale.time_format;return t==="12"||t==="24"?t==="12":new Date("January 1, 2023 22:00:00").toLocaleString(t==="system"?void 0:o.locale.language).includes("10")}function xe(o,t){let e=qs(o),s=r=>new Intl.DateTimeFormat("en",{year:"numeric",timeZone:e}).format(r),n=s(t)===s(Date.now())?{}:{year:"numeric"};return new Intl.DateTimeFormat(Ot(o),{day:"numeric",month:"short",...n,timeZone:e}).format(t)}function Gs(o,t){let e=/^(\d{4})-(\d{2})-(\d{2})$/.exec(t);if(!e)return;let s=Date.UTC(Number(e[1]),Number(e[2])-1,Number(e[3]));return new Intl.DateTimeFormat(Ot(o),{day:"numeric",month:"long",timeZone:"UTC"}).format(s)}function ot(o,t){let e=Xo(o);return new Intl.DateTimeFormat(Ot(o),{day:"numeric",month:"short",hour:e?"numeric":"2-digit",minute:"2-digit",hourCycle:e?"h12":"h23",timeZone:qs(o)}).format(t)}var{I:Fr}=_s;var Ks=o=>o.strings===void 0;var Zs={ATTRIBUTE:1,CHILD:2,PROPERTY:3,BOOLEAN_ATTRIBUTE:4,EVENT:5,ELEMENT:6},jt=o=>(...t)=>({_$litDirective$:o,values:t}),nt=class{constructor(t){}get _$AU(){return this._$AM._$AU}_$AT(t,e,s){this._$Ct=t,this._$AM=e,this._$Ci=s}_$AS(t,e){return this.update(t,e)}update(t,e){return this.render(...e)}};var ke=(o,t)=>{let e=o._$AN;if(e===void 0)return!1;for(let s of e)s._$AO?.(t,!1),ke(s,t);return!0},rt=o=>{let t,e;do{if((t=o._$AM)===void 0)break;e=t._$AN,e.delete(o),o=t}while(e?.size===0)},Ys=o=>{for(let t;t=o._$AM;o=t){let e=t._$AN;if(e===void 0)t._$AN=e=new Set;else if(e.has(o))break;e.add(o),tn(t)}};function Qo(o){this._$AN!==void 0?(rt(this),this._$AM=o,Ys(this)):this._$AM=o}function en(o,t=!1,e=0){let s=this._$AH,n=this._$AN;if(n!==void 0&&n.size!==0)if(t)if(Array.isArray(s))for(let r=e;r<s.length;r++)ke(s[r],!1),rt(s[r]);else s!=null&&(ke(s,!1),rt(s));else ke(this,o)}var tn=o=>{o.type==Zs.CHILD&&(o._$AP??=en,o._$AQ??=Qo)},it=class extends nt{constructor(){super(...arguments),this._$AN=void 0}_$AT(t,e,s){super._$AT(t,e,s),Ys(this),this.isConnected=t._$AU}_$AO(t,e=!0){t!==this.isConnected&&(this.isConnected=t,t?this.reconnected?.():this.disconnected?.()),e&&(ke(this,t),rt(this))}setValue(t){if(Ks(this._$Ct))this._$Ct._$AI(t,this);else{let e=[...this._$Ct._$AH];e[this._$Ci]=t,this._$Ct._$AI(e,this,0)}}disconnected(){}reconnected(){}};var Js=()=>new Ut,Ut=class{},Dt=new WeakMap,Xs=jt(class extends it{render(o){return h}update(o,[t]){let e=t!==this.G;return e&&this.rt(void 0),(e||this.lt!==this.ct)&&(this.G=t,this.ht=o.options?.host,this.rt(this.ct=o.element)),h}rt(o){if(this.G!==void 0)if(this.isConnected||(o=void 0),typeof this.G=="function"){let t=this.ht??globalThis,e=Dt.get(t);e===void 0&&(e=new WeakMap,Dt.set(t,e)),e.get(this.G)!==void 0&&this.G.call(this.ht,void 0),e.set(this.G,o),o!==void 0&&this.G.call(this.ht,o)}else this.G.value=o}get lt(){return typeof this.G=="function"?Dt.get(this.ht??globalThis)?.get(this.G):this.G?.value}disconnected(){this.lt===this.ct&&this.rt(void 0)}reconnected(){this.rt(this.ct)}});var sn="M12,9A3,3 0 0,0 9,12A3,3 0 0,0 12,15A3,3 0 0,0 15,12A3,3 0 0,0 12,9M12,17A5,5 0 0,1 7,12A5,5 0 0,1 12,7A5,5 0 0,1 17,12A5,5 0 0,1 12,17M12,4.5C7,4.5 2.73,7.61 1,12C2.73,16.39 7,19.5 12,19.5C17,19.5 21.27,16.39 23,12C21.27,7.61 17,4.5 12,4.5Z",on="M11.83,9L15,12.16C15,12.11 15,12.05 15,12A3,3 0 0,0 12,9C11.94,9 11.89,9 11.83,9M7.53,9.8L9.08,11.35C9.03,11.56 9,11.77 9,12A3,3 0 0,0 12,15C12.22,15 12.44,14.97 12.65,14.92L14.2,16.47C13.53,16.8 12.79,17 12,17A5,5 0 0,1 7,12C7,11.21 7.2,10.47 7.53,9.8M2,4.27L4.28,6.55L4.73,7C3.08,8.3 1.78,10 1,12C2.73,16.39 7,19.5 12,19.5C13.55,19.5 15.03,19.2 16.38,18.66L16.81,19.08L19.73,22L21,20.73L3.27,3M12,7A5,5 0 0,1 17,12C17,12.64 16.87,13.26 16.64,13.82L19.57,16.75C21.07,15.5 22.27,13.86 23,12C21.27,7.61 17,4.5 12,4.5C10.6,4.5 9.26,4.75 8,5.2L10.17,7.35C10.74,7.13 11.35,7 12,7Z",eo="M7.41,8.58L12,13.17L16.59,8.58L18,10L12,16L6,10L7.41,8.58Z",to="M7.41,15.41L12,10.83L16.59,15.41L18,14L12,8L6,14L7.41,15.41Z",nn="M8.59,16.58L13.17,12L8.59,7.41L10,6L16,12L10,18L8.59,16.58Z",rn="M9.5,3A6.5,6.5 0 0,1 16,9.5C16,11.11 15.41,12.59 14.44,13.73L14.71,14H15.5L20.5,19L19,20.5L14,15.5V14.71L13.73,14.44C12.59,15.41 11.11,16 9.5,16A6.5,6.5 0 0,1 3,9.5A6.5,6.5 0 0,1 9.5,3M9.5,5C7,5 5,7 5,9.5C5,12 7,14 9.5,14C12,14 14,12 14,9.5C14,7 12,5 9.5,5Z",an="M19,6.41L17.59,5L12,10.59L6.41,5L5,6.41L10.59,12L5,17.59L6.41,19L12,13.41L17.59,19L19,17.59L13.41,12L19,6.41Z",ae=o=>se`<svg viewBox="0 0 24 24" aria-hidden="true"><path d=${o}></path></svg>`,Ft={down:eo,up:to,right:nn};function T(o){return t=>{(t.key==="Enter"||t.key===" ")&&(t.preventDefault(),o())}}function ln(o,t){o.dispatchEvent(new CustomEvent("hass-more-info",{bubbles:!0,composed:!0,detail:{entityId:t}}))}function R(o,t){return()=>{t&&ln(o,t)}}function le(o,t){let e=o.filter(s=>s.second!==void 0);return e.length>0&&e.every(s=>s.first+t+s.second<=s.room)}function A(o,t){return d`<span class="amount ${t?"blur":""}">${o??"\u2014"}</span>`}function so(o,t,e){let[s,...n]=o.split(`{${t}}`);return n.length===0?d`${o}`:d`${s}<span class="nw">${e}</span>${n.join(`{${t}}`)}`}function Q(o){return d`<div class="empty">${o}</div>`}function $e(o,t,e){return d`<div class="head">
    <div class="title">${t}</div>
    ${e?d`<button
          class="icon-btn eye"
          aria-label=${u(o,e.hidden?"eye_show":"eye_hide")}
          title=${u(o,e.hidden?"eye_show":"eye_hide")}
          @click=${e.toggle}
        >
          ${ae(e.hidden?on:sn)}
        </button>`:h}
  </div>`}function oo(o,t,e,s,n){let{text:r,direction:i}=N(o,t),a=X(i);return d`<div class="hero-line">
    <span class="chip ${E(i)}" role="button" tabindex="0" @click=${s} @keydown=${T(s)}
      >${a?`${a} `:""}${r}</span
    >
    ${i!=="none"&&n?.text?d`<span class="chip-amount ${E(i)}">${A(n.text,n.hidden)}</span>`:h}
    <span class="chip-label">${u(o,`return_${e}`)}</span>
  </div>`}function no(o,t,e,s,n){return d`<div class="seg" role="radiogroup" aria-label=${o} @keydown=${i=>{let a=i.key==="ArrowRight"||i.key==="ArrowDown"?1:i.key==="ArrowLeft"||i.key==="ArrowUp"?-1:0;if(a===0)return;i.preventDefault();let l=(t.indexOf(e)+a+t.length)%t.length;n(t[l]),i.currentTarget.querySelectorAll("[role=radio]")[l]?.focus()}}>
    ${t.map(i=>d`<span
          role="radio"
          aria-checked=${i===e?"true":"false"}
          tabindex=${i===e?0:-1}
          @click=${()=>n(i)}
          @keydown=${T(()=>n(i))}
          >${s(i)}</span
        >`)}
  </div>`}function at(o,t,e){return no(u(o,"aria_timeframe"),F,t,s=>u(o,`tf_${s}`),e)}function ro(o,t,e,s){return t.length<2?null:no(u(o,"aria_currency"),t,e,n=>n,s)}function io(o,t,e){let s=Js(),n=()=>{e(""),s.value?.focus()};return d`<div class="search" role="search">
    ${ae(rn)}<input
      ${Xs(s)}
      type="text"
      .value=${t}
      placeholder=${u(o,"search_placeholder")}
      aria-label=${u(o,"aria_search")}
      autocomplete="off"
      spellcheck="false"
      @input=${r=>e(r.target.value)}
    />${t?d`<span class="clear" role="button" tabindex="0" aria-label=${u(o,"aria_search_clear")} @click=${n} @keydown=${T(n)}
          >${ae(an)}</span
        >`:h}
  </div>`}var cn={\u00DF:"ss",\u00F8:"o",\u00E6:"ae",\u0153:"oe",\u0142:"l",\u0111:"d",\u00F0:"d",\u00FE:"th",\u0131:"i"};function Qs(o){return o.normalize("NFD").replace(/\p{M}/gu,"").toLowerCase().replace(/[ßøæœłđðþı]/gu,t=>cn[t]??t).replace(/[^\p{L}\p{N}\s]/gu,"")}function ao(o,t){let e=Qs(t).split(/\s+/).filter(Boolean),s=Qs(`${o.name} ${o.symbol} ${o.isin??""}`);return e.length>0&&e.every(n=>s.includes(n))}function lo(o){let{hass:t,wallet:e,hidden:s,onTap:n,chevron:r}=o,i=e.total?t.states[e.total]:void 0,a=$(i,"units"),l=k(t,e.total),c=k(t,e.staking),p=l&&c&&c>0?c/l*100:void 0,{text:m,direction:_}=N(t,$(i,"total_return_percent")),f=X(_),v=_==="none"?d`<span class="wchip none">—</span>`:d`<span class="wchip ${E(_)}">${f?`${f} `:""}${m}</span>`,y=p===void 0?h:d`<div class="stake"><span class="badge">${u(t,"staked",{share:ie(t,p,0)})}</span></div>`,g=x=>{x.stopPropagation(),r?.toggle()};return d`<div class="wallet">
    <div class="tap" role="button" tabindex="0" @click=${n} @keydown=${T(n)}>
      <div class="main">
        <div class="n" title=${e.shortName}>${e.shortName}</div>
        <div class="sub ${p===void 0?"":"staked"}">
          <div class="s">
            <span class="units"
              >${A(a===void 0?void 0:ve(t,a,e.category,e.symbol,!0),s)}</span
            >${e.isin?d` · <span class="isin">${e.isin}</span>`:h}
          </div>
          ${y}
        </div>
      </div>
      <div class="right">${v}<span class="val">${A(I(t,e.total),s)}</span></div>
    </div>
    ${r?d`<span
          class="chevron"
          role="button"
          tabindex="0"
          aria-expanded=${r.open?"true":"false"}
          @click=${g}
          @keydown=${x=>{x.stopPropagation(),T(r.toggle)(x)}}
          >${ae(r.open?to:eo)}</span
        >`:h}
  </div>`}function lt(o,t,e){let s=i=>k(o,i.total)??Number.NEGATIVE_INFINITY,n=i=>$(i.total?o.states[i.total]:void 0,"total_return_percent")??Number.NEGATIVE_INFINITY,r=(i,a)=>i.name.localeCompare(a.name,O(o));return[...t].sort((i,a)=>e==="name"?r(i,a):(e==="value"?s(a)-s(i):n(a)-n(i))||r(i,a))}var dn=window.customElements,pn=1e4;function un(o=()=>window.customElements,t=dn,e=pn){let s=Date.now();return new Promise(n=>{let r=()=>{let i=o();i!==t||i.get("home-assistant")||Date.now()-s>=e?n(i):setTimeout(r,50)};r()})}var hn="https://github.com/Spegeli/hacs_bitpanda#-dashboard-cards";function mn(o,t,e,s,n={}){let r=o.entities[t];return!r||r.platform!=="bitpanda"||!r.device_id?null:(typeof e=="string"?[e]:e).includes(o.devices[r.device_id]?.model??"")?{config:{type:`custom:${s}`,...n}}:null}function ct(o,t,e){un().then(r=>{r.get(o)||r.define(o,t)});let s=window;if(s.customCards??=[],s.customCards.some(r=>r.type===o))return;let{model:n}=e;s.customCards.push({type:o,name:e.name,get description(){return e.description()},preview:!0,documentationURL:hn,...n?{getEntitySuggestion:(r,i)=>mn(r,i,n,o,t.getStubConfig?.())}:{}})}var _n={day:[864e5,"5minute"],week:[6048e5,"hour"],month:[2592e6,"hour"],six_month:[157248e5,"day"],year:[31536e6,"day"]};function dt(o){return o==="5minute"?5*6e4:o==="hour"?36e5:864e5}function co(o){return o.timeframe==="month"?(o.end-o.start)/120:0}function de(o,t){let[e,s]=_n[o];return{timeframe:o,start:t-e,end:t,period:s}}var fn=o=>typeof o=="number"?o:Date.parse(o);async function gn(o,t,e){if(t.length===0)return{};let s;try{s=await o.callWS({type:"recorder/statistics_during_period",start_time:new Date(e.start).toISOString(),end_time:new Date(e.end).toISOString(),statistic_ids:[...t],period:e.period,types:["state"]})}catch{return}let n={};for(let[r,i]of Object.entries(s))n[r]=i.map(a=>({t:fn(a.start),v:a.state})).filter(a=>typeof a.v=="number"&&Number.isFinite(a.t)).sort((a,l)=>a.t-l.t);return n}var pt="portfolio";async function po(o,t,e){let s;try{s=await o.callWS({type:"bitpanda/portfolio_history",timeframe:e.timeframe})}catch{return}let r=(Array.isArray(s?.points)?s.points:[]).filter(i=>Array.isArray(i)&&typeof i[0]=="number"&&typeof i[1]=="number"&&Number.isFinite(i[0])&&Number.isFinite(i[1])).map(([i,a])=>({t:i,v:a})).sort((i,a)=>i.t-a.t);return{[pt]:r}}var ce=class{constructor(t,e=gn){this.onUpdate=t;this.fetch=e;this.key="";this.end=0;this.latest=0;this.current={}}request(t,e,s,n=""){let r=`${s.timeframe}|${[...e].sort().join(",")}|${n}`;if(r===this.key&&s.end-this.end<dt(s.period))return;s.timeframe!==this.timeframe&&(this.current={}),this.key=r,this.timeframe=s.timeframe,this.end=s.end;let i=++this.latest;this.fetch(t,e,s).then(a=>{if(i===this.latest){if(a===void 0){this.key="";return}this.current=a,this.onUpdate()}})}series(t){return this.current[t]}};function uo(o,t,e){let s=dt(e.period),n=o.find(r=>r.t>=e.start-s);if(!(t===void 0||n===void 0||n.v===0))return{change:(t-n.v)/n.v*100,amount:t-n.v,...n.t>e.start+s?{since:n.t}:{}}}var ho=2,Bt=o=>Math.round(o*100)/100;function Vt(o,t,e,s){return Bt(e===t?s/2:s-ho-(o-t)/(e-t)*(s-2*ho))}function mo(o,t){let e=0;return o.forEach((s,n)=>{Math.abs(s.t-t)<Math.abs(o[e].t-t)&&(e=n)}),e}function yn(o,t){if(t<=0||o.length<3)return o;let e=n=>Math.floor(n.t/t),s=[];for(let n of o.slice(0,-1)){let r=s[s.length-1];(!r||e(n)!==e(r))&&s.push(n)}return s.push(o[o.length-1]),s}function _o(o,t,e,s,n,r=0){let i=n??1.5*dt(t.period),a=[],l;for(let g of o)(!l||g.t-l.t>i)&&a.push([]),a[a.length-1]?.push(g),l=g;let c=a.map(g=>yn(g,r)),p=c.flat().map(g=>g.v),m=Math.min(...p),_=Math.max(...p),f=t.end-t.start,v=g=>Bt((g-t.start)/f*e),y=g=>Vt(g,m,_,s);return c.map(g=>g.map(x=>[v(x.t),y(x.v)]))}function wn(o,t,e,s,n,r=0){return _o(o,t,e,s,n,r).map(i=>i.length===1?`M${i[0]?.[0]},${i[0]?.[1]}l0.01,0`:i.map(([a,l],c)=>`${c===0?"M":"L"}${a},${l}`).join("")).join("")}function vn(o,t,e,s,n,r=0){return _o(o,t,e,s,n,r).map(i=>{let a=i[0],l=i[i.length-1];return`M${a[0]},${s}${i.map(([c,p])=>`L${c},${p}`).join("")}L${l[0]},${s}Z`}).join("")}var qt=(o,t)=>o.length>0&&o[o.length-1].t-o[0].t>=(t.end-t.start)/10;function ut(o,t,e){let{width:s,height:n,fill:r,className:i,gapMs:a,stepMs:l}=e;return qt(o,t)?se`<svg class=${i} viewBox="0 0 ${s} ${n}" preserveAspectRatio="none" aria-hidden="true">${r?se`<path class="area" d=${vn(o,t,s,n,a,l)}></path>`:null}<path class="line" d=${wn(o,t,s,n,a,l)} vector-effect="non-scaling-stroke"></path></svg>`:se`<svg class=${i} viewBox="0 0 ${s} ${n}" preserveAspectRatio="none" aria-hidden="true"></svg>`}var bn=480,Gt=72,ht=o=>`${(o*100).toFixed(2)}%`;function xn(o,t,e){let{hass:s,refs:n,window:r,hidden:i,cursor:a,onCursor:l}=o,c=t.map(b=>b.v),p=Math.min(...c),m=Math.max(...c),_=r.end-r.start,f=b=>{let w=b.currentTarget.getBoundingClientRect(),z=Math.min(Math.max((b.clientX-w.left)/w.width,0),1);return mo(t,r.start+z*_)},v=b=>l(f(b)),y=()=>l(void 0),g=b=>{b.pointerType!=="mouse"&&y()},x=n.totalValue?s.states[n.totalValue]?.attributes.unit_of_measurement:void 0,C=typeof x=="string"&&!i?b=>be(s,b,x):void 0,S=a===void 0?void 0:t[a],ee=h;if(S){let b=(S.t-r.start)/_,w=r.timeframe==="day"||r.timeframe==="week"?ot(s,S.t):xe(s,S.t),z=b<.25?"start":b>.75?"end":"";ee=d`${C?d`<span class="tag high">${C(m)}</span><span class="tag middle">${C((m+p)/2)}</span
            ><span class="tag low">${C(p)}</span>`:h}
      <div class="cursor" style="left:${ht(b)}"></div>
      <div class="dot" style="left:${ht(b)};top:${ht(Vt(S.v,p,m,Gt)/Gt)}"></div>
      <div class="tip ${z}" style="left:${ht(b)}">${C?`${w} \xB7 ${C(S.v)}`:w}</div>`}let Ae=ut(t,r,{width:bn,height:Gt,fill:!0,className:`spark ${e}`,gapMs:Number.POSITIVE_INFINITY});return qt(t,r)?d`<div class="plot" @pointerdown=${v} @pointermove=${v} @pointerup=${g} @pointercancel=${y} @pointerleave=${y}>
    ${Ae}
    <div class="mid"></div>
    ${ee}
  </div>`:d`<div class="plot">${Ae}</div>`}function kn(o,t,e){if(t.timeframe==="day")return u(o,"value_line_day");let s=e[0]?.t??t.start;return u(o,"value_line",{start:xe(o,Math.max(t.start,s))})}function $n(o,t,e){let s=k(o,t.totalValue),n=k(o,t.returns[e]),r=t.totalValue?o.states[t.totalValue]?.attributes.unit_of_measurement:void 0;if(!(s===void 0||n===void 0||n<=-100||typeof r!="string"))return be(o,s*n/(100+n),r,!0)}function fo(o){let{host:t,hass:e,refs:s,timeframe:n,hidden:r,window:i,points:a}=o,l=k(e,s.returns[n]),c=E(N(e,l).direction)||"flat",p=m=>R(t,m);return d`${o.total?d`<div class="hero" role="button" tabindex="0" @click=${p(s.totalValue)} @keydown=${T(p(s.totalValue))}>
            ${A(I(e,s.totalValue),r)}
          </div>
          ${oo(e,l,n,p(s.returns[n]),{text:$n(e,s,n),hidden:r})}`:h}
    ${o.total||o.line?at(e,n,o.onTimeframe):h}
    ${o.line&&a&&a.length>0?d`${xn(o,a,c)}
          <div class="caption">${kn(e,i,a)}</div>`:h}`}var An="bitpanda-portfolio-card",go={crypto:"var(--blue-color, #4269d0)",stock:"var(--indigo-color, #3f51b5)",etf:"var(--amber-color, #efb118)",etc:"var(--cyan-color, #00bcd4)",index:"var(--purple-color, #a463f2)",metal:"var(--green-color, #3ca951)",other:"var(--pink-color, #ff8ab7)",cash_plus:"var(--deep-orange-color, #ff725c)",cash:"var(--teal-color, #6cc5b0)"},yo=o=>o.category??"other";function Sn(o,t){return t<1?`<${ie(o,1,0)}`:ie(o,t,2,!0)}var Tn=(o,t)=>Ye(Ze(o.wallets,t.group_selection??"all",t.groups??[]),t.asset_selection??"all",t.assets??[]);function Cn(o,t){let e=0,s=0;for(let n of t){let r=k(o,n.total),i=$(n.total?o.states[n.total]:void 0,"invested_amount");if(r===void 0||i===void 0)return;e+=r,s+=i}return s>0?(e-s)/s*100:void 0}function wo(o){let t=o.map(s=>({room:s.room,first:s.left,second:Math.max(s.chip??0,s.value)}));if(o.length===0||le(t,Pn))return"beside";let e=o.flatMap(s=>s.chip===void 0?[]:[{room:s.below??s.room,first:s.chip,second:s.value}]);return e.length===0||le(e,En)?"row":"stacked"}function Kt(o){if(!o.some(t=>t===void 0))return Math.round(o.reduce((t,e)=>t+e,0)*1e8)/1e8}var Zt="\xA0\xB7 ",Pn=12,En=8,Rn=30,zn=8,Yt=class extends B{constructor(){super(...arguments);this.openGroups=new Set;this.showAll=!1;this.query="";this.cursor=void 0;this.stakeInline=!1;this.groupsLayout="beside";this.rowsLayout="beside";this.openWallets=new Set;this.window=de("day",Date.now());this.lines=new ce(()=>this.seriesArrived(),po)}static{this.properties={...B.properties,openGroups:{state:!0},openWallets:{state:!0},showAll:{state:!0},query:{state:!0},cursor:{state:!0},stakeInline:{state:!0},groupsLayout:{state:!0},rowsLayout:{state:!0}}}static async getConfigElement(){return et(Je)}static getStubConfig(){return{timeframe:"day",sort:"value",group_selection:"all",asset_selection:"all"}}validate(e){return Fe(e,{...Ge,timeframe:P(F),show_total:D,show_graph:D,show_cash:D,show_allocation:D,show_wallets:D,group_wallets:D,show_search:D,sort:P(Me),limit:je,group_selection:P(j),groups:Ue,asset_selection:P(j),assets:De,hide_amounts:D})}watchedEntities(){let e=this.hass?Ke(this.hass):void 0;return e?[e.totalValue,e.cash,e.cashPlus,...Object.values(e.returns),...e.wallets.flatMap(s=>[s.available,s.total,s.staking])].filter(s=>s!==void 0):[]}willUpdate(e){super.willUpdate(e);let s=this.hass?Ke(this.hass):void 0;this.window=de(this.timeframe,Date.now());let n=this.hass?.states[s?.returns[this.timeframe]??""]?.state??"";this.hass&&s&&this.config?.show_graph!==!1&&this.lines.request(this.hass,[pt],this.window,n)}getCardSize(){return 8}remeasures(e){return!(e.size===1&&e.has("cursor"))}fitLayout(){let e=_=>[...this.renderRoot.querySelectorAll(_)],s=(_,f)=>_.querySelector(f),n=this.widthMeter(),r=_=>_?n(_):void 0,i=e(".wallet .sub").map(_=>{let f=r(_.querySelector(".stake .badge"));return{room:_.clientWidth,first:n(s(_,".s")),...f===void 0?{}:{second:f}}}),a=le(i,zn);a!==this.stakeInline&&(this.stakeInline=a);let l=e(".group").map(_=>{let f=r(_.querySelector(".gchip"));return{room:_.clientWidth,left:n(s(_,".gleft")),...f===void 0?{}:{chip:f},value:n(s(_,".sum"))}}),c=wo(l);c!==this.groupsLayout&&(this.groupsLayout=c);let p=e(".wallet .tap").map(_=>({room:_.clientWidth,below:_.clientWidth+Rn,left:n(s(_,".s .units"),!0),chip:n(s(_,".wchip")),value:n(s(_,".val"))})),m=wo(p);m!==this.rowsLayout&&(this.rowsLayout=m)}groupChip(e,s){let{text:n,direction:r}=N(e,Cn(e,s));if(r==="none")return d`<span class="gchip none">—</span>`;let i=X(r);return d`<span class="gchip ${E(r)}">${i?`${i} `:""}${n}</span>`}walletsClass(){return["wallets",this.stakeInline?"stake-inline":"",this.groupsLayout==="beside"?"":"groups-wrapped",this.groupsLayout==="stacked"?"groups-stacked":"",this.rowsLayout==="beside"?"":"rows-wrapped",this.rowsLayout==="stacked"?"rows-stacked":""].filter(Boolean).join(" ")}toggle(e,s){let n=new Set(e);return n.has(s)?n.delete(s):n.add(s),n}render(){let e=this.hass,s=this.config;if(!e||!s)return h;let n=Ke(e),r={hidden:this.amountsHidden,toggle:()=>this.toggleAmounts()},i=s.title||"Bitpanda Portfolio";if(!n)return d`<ha-card>${$e(e,i)}${Q(u(e,"empty_portfolio"))}</ha-card>`;let a=s.show_total!==!1||s.show_graph!==!1,l=s.show_cash!==!1||s.show_allocation!==!1,c=Tn(n,s);return d`<ha-card>
      ${$e(e,i,r)}
      <div class="content">
        ${fo({host:this,hass:e,refs:n,timeframe:this.timeframe,hidden:this.amountsHidden,window:this.window,points:this.lines.series(pt),total:s.show_total!==!1,line:s.show_graph!==!1,onTimeframe:p=>{this.cursor=void 0,this.selectTimeframe(p)},cursor:this.cursor,onCursor:p=>{p!==this.cursor&&(this.cursor=p)}})}
        ${l?d`${a?d`<div class="divider"></div>`:h}
              ${s.show_cash===!1?h:this.renderCash(e,n)}
              ${s.show_allocation===!1?h:this.renderAllocation(e,n)}`:h}
        ${s.show_wallets===!1?h:d`${a||l?d`<div class="divider"></div>`:h}${s.show_search&&c.length>0?io(e,this.query,p=>this.query=p):h}${this.renderWallets(e,n,c,s)}`}
      </div>
    </ha-card>`}renderCash(e,s){let n=(r,i,a)=>d`<div class=${a?"end":""} role="button" tabindex="0" @click=${R(this,i)} @keydown=${T(R(this,i))}>
        <span class="k">${r}</span><span class="v">${A(I(e,i),this.amountsHidden)}</span>
      </div>`;return d`<div class="pair">${n(u(e,"cash"),s.cash,!1)}${n(u(e,"cash_plus"),s.cashPlus,!0)}</div>`}renderAllocation(e,s){let n=[];for(let a of H){let l=s.wallets.filter(c=>yo(c)===a);l.length>0&&n.push({key:a,label:At(e,a),value:Kt(l.map(c=>k(e,c.total)))})}s.cashPlus&&n.push({key:"cash_plus",label:u(e,"cash_plus"),value:k(e,s.cashPlus)}),s.cash&&n.push({key:"cash",label:u(e,"cash"),value:k(e,s.cash)});let r=Kt(n.map(a=>a.value));if(r===void 0)return d`<div class="allocation-missing muted">—</div>`;let i=n.map(a=>({...a,share:r>0?a.value/r*100:0})).filter(a=>a.share>0).sort((a,l)=>l.share-a.share);return d`<div class="bar" role="img" aria-label=${u(e,"opt_show_allocation")}>
        ${i.map(a=>d`<span style="width:${a.share}%;background:${go[a.key]}"></span>`)}
      </div>
      <div class="legend">
        ${i.map(a=>d`<span><i style="background:${go[a.key]}"></i>${a.label} ${Sn(e,a.share)}</span>`)}
      </div>`}renderWallets(e,s,n,r){if(s.wallets.length===0)return Q(u(e,"empty_wallets"));if(n.length===0)return Q(u(e,"empty_selection_wallets"));let i=r.sort??"value",a=r.show_search?this.query.trim():"";if(a){let l=lt(e,n.filter(c=>ao(c,a)),i);return l.length>0?d`<div class=${this.walletsClass()}>${l.map(c=>this.renderWallet(e,s,c))}</div>`:d`<div class="search-none">${u(e,"search_none",{query:a})}</div>`}if(r.group_wallets===!1){let l=lt(e,n,i),c=r.limit??5,p=c>0&&l.length>c,m=p&&!this.showAll?l.slice(0,c):l;return d`<div class=${this.walletsClass()}>${m.map(_=>this.renderWallet(e,s,_))}</div>
        ${p?d`<button class="show-all" @click=${()=>this.showAll=!this.showAll}>
              ${this.showAll?u(e,"show_less"):u(e,"show_all",{count:l.length})}
            </button>`:h}`}return d`<div class=${this.walletsClass()}>${H.map(l=>{let c=n.filter(f=>yo(f)===l);if(c.length===0)return h;let p=Kt(c.map(f=>k(e,f.total))),m=this.openGroups.has(l),_=()=>{this.openGroups=this.toggle(this.openGroups,l)};return d`<div class="group" role="button" tabindex="0" aria-expanded=${m?"true":"false"} @click=${_} @keydown=${T(_)}>
          <span class="gleft"
            >${ae(m?Ft.down:Ft.right)}<span class="name">${At(e,l)}</span
            ><span class="count">${c.length}</span></span
          >
          <span class="gright">${this.groupChip(e,c)}<span class="sum">${A(Ds(e,c[0]?.total,p),this.amountsHidden)}</span></span>
        </div>
        ${m?d`<div class="members">${lt(e,c,i).map(f=>this.renderWallet(e,s,f))}</div>`:h}`})}</div>`}renderWallet(e,s,n){let r=this.openWallets.has(n.deviceId);return d`${lo({hass:e,wallet:n,hidden:this.amountsHidden,onTap:R(this,n.total),chevron:{open:r,toggle:()=>{this.openWallets=this.toggle(this.openWallets,n.deviceId)}}})}${r?this.renderDetail(e,s,n):h}`}renderDetail(e,s,n){let r=this.amountsHidden,i=w=>w?e.states[w]?.attributes.unit_of_measurement:void 0,a=String(i(n.total)??i(s.totalValue)??"EUR"),l=n.total?e.states[n.total]:void 0,c=n.staking?e.states[n.staking]:void 0,p=w=>{let z=$(w?e.states[w]:void 0,"units");return z===void 0?void 0:ve(e,z,n.category,n.symbol)},m=(w,z=!1)=>w===void 0?void 0:be(e,w,a,z),_=w=>w===void 0?void 0:Us(e,w,a),f=w=>d`<span class="part">${w}</span>`,v=w=>d`${f(A(p(w),r))}${Zt}${f(A(I(e,w),r))}`,y=$(l,"total_return"),g=N(e,$(l,"total_return_percent")),x=$(c,"apr_percent"),C=$(c,"rewards_net"),S=$(c,"rewards_count"),ee=c?.attributes.rewards_last_at,Ae=typeof ee=="string"&&Number.isFinite(Date.parse(ee))?ot(e,Date.parse(ee)):"\u2014",b=m($(c,"rewards_net_value"));return d`<div class="detail">
      <div class="grid">
        <span>${u(e,"detail_available")}</span><span>${v(n.available)}</span>
        ${n.staking?d`<span>${u(e,"detail_staked")}</span><span>${v(n.staking)}</span>`:h}
        ${n.staking&&x!==void 0?d`<span>${u(e,"detail_staking_apr")}</span><span>${ie(e,x,1)}</span>`:h}
        <span>${u(e,"detail_average_buy_price")}</span><span>${A(_($(l,"average_buy_price")),r)}</span>
        <span>${u(e,"detail_invested")}</span><span>${A(m($(l,"invested_amount")),r)}</span>
        <span>${u(e,"detail_profit_loss")}</span
        ><span class=${E(g.direction)}>${f(A(m(y,!0),r))} ${f(`(${g.text})`)}</span>
      </div>
      ${S!==void 0&&S>0?d`<h4>${u(e,"detail_rewards")}</h4>
            <div class="grid">
              <span>${u(e,"detail_rewards_net")}</span>
              <span
                >${f(A(C===void 0?void 0:ve(e,C,n.category,n.symbol),r))}${b?d`${Zt}${f(this.worth(e,b))}`:h}</span
              >
              <span>${u(e,"detail_payouts")}</span
              ><span
                >${u(e,"detail_payouts_value",{count:S,date:Ae}).split(" \xB7 ").map((w,z)=>d`${z>0?Zt:""}${f(w)}`)}</span
              >
            </div>`:h}
    </div>`}worth(e,s){let[n="",r=""]=u(e,"detail_rewards_worth").split("{value}");return d`${n}${A(s,this.amountsHidden)}${r}`}};ct(An,Yt,{name:"Bitpanda Portfolio",description:()=>u(Be(),"picker_portfolio"),model:["Portfolio","Wallet"]});var Ln=ue`
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
`,Hn=6,In=120,Nn=90,mt=8,Mn=78,Wn=96,On=380;function vo(o){let t=Math.ceil(Math.max(0,...o.map(s=>s.price))),e=Math.ceil(Math.max(0,...o.map(s=>s.change)));return{price:t,change:Math.max(Mn,e),figures:Math.max(t,e)}}function jn(o){let t=vo(o);return o.every(e=>e.room-t.price-mt-t.change-mt>=In)?"beside":o.every(e=>e.room-t.figures-mt>=Nn)?"stacked":"below"}function Dn(o){return le(o.map(t=>({room:t.room,first:t.pct,...t.amount===void 0?{}:{second:t.amount}})),Hn)}var Jt=class extends B{constructor(){super(...arguments);this.showAll=!1;this.amountsInline=!1;this.rowsLayout="beside";this.columns=void 0;this.window=de("day",Date.now());this.lines=new ce(()=>this.seriesArrived())}static{this.properties={...B.properties,currency:{state:!0},showAll:{state:!0},amountsInline:{state:!0},rowsLayout:{state:!0},columns:{state:!0}}}static{this.styles=[qe,Ln]}static async getConfigElement(){return et(Xe)}static getStubConfig(){return{layout:"list",timeframe:"day",currency:"EUR",sort:"name",group_selection:"all",asset_selection:"all"}}setConfig(e){super.setConfig(e),this.currency=void 0}validate(e){return Fe(e,{...Ge,layout:P(Oe),timeframe:P(F),currency:zs,sort:P(We),group_selection:P(j),groups:Ue,asset_selection:P(j),assets:De,limit:je})}watchedEntities(){return this.hass?re(this.hass).flatMap(e=>Object.values(e.prices)):[]}shownCurrency(e){let s=we(e),n=this.currency??this.config?.currency??"EUR";return s.includes(n)?n:s.includes("EUR")?"EUR":s[0]??"EUR"}visible(e,s){let n=re(e),r=this.shownCurrency(n),i=Ze(n,s.group_selection??"all",s.groups??[]),l=Ye(i,s.asset_selection??"all",s.assets??[]).map(v=>{let y=v.prices[r],g=y?e.states[y]:void 0,x=y?this.lines.series(y):void 0,C=k(e,y),S=uo(x??[],C,this.window);return{asset:v,entityId:y,change:S?.change,amount:S?.amount,points:x,since:S?.since}}),c=s.sort??"name",p=(v,y)=>v.asset.name.localeCompare(y.asset.name,O(e));if(c==="name"||c==="selection"&&s.asset_selection!=="only")l.sort(p);else if(c==="change_desc"||c==="change_asc"){let v=c==="change_desc"?-1:1;l.sort((y,g)=>y.change===void 0||g.change===void 0?y.change===void 0?g.change===void 0?p(y,g):1:-1:v*(y.change-g.change)||p(y,g))}let m=s.limit??0,_=m>0&&l.length>m;return{rows:_&&!this.showAll?l.slice(0,m):l,ranked:l,total:l.length,folds:_,currency:r,currencies:we(n)}}willUpdate(e){if(super.willUpdate(e),this.window=de(this.timeframe,Date.now()),!this.hass||!this.config)return;let{rows:s,ranked:n}=this.visible(this.hass,this.config),r=this.config.sort??"name",a=(r==="change_desc"||r==="change_asc"?n:s).map(l=>l.entityId).filter(l=>l!==void 0);this.lines.request(this.hass,a,this.window)}fitLayout(){let e=this.widthMeter(),s=c=>c?e(c):void 0,n=[...this.shadowRoot?.querySelectorAll(".tile .c")??[]].map(c=>{let p=s(c.querySelector(".a"));return{room:c.clientWidth,pct:s(c.querySelector(".pct"))??0,...p===void 0?{}:{amount:p}}}),r=Dn(n);r!==this.amountsInline&&(this.amountsInline=r);let i=this.clientWidth>On?Wn+mt:0,a=[...this.renderRoot.querySelectorAll(".price-row")].map(c=>{let p=m=>e(c.querySelector(m));return{room:c.clientWidth-i,price:p(".p"),change:Math.max(p(".c .pct"),s(c.querySelector(".c .a"))??0)}}),l=jn(a);if(l!==this.rowsLayout&&(this.rowsLayout=l),a.length>0){let c=vo(a),p=this.columns;(!p||p.price!==c.price||p.change!==c.change||p.figures!==c.figures)&&(this.columns=c)}}getCardSize(){return 6}line(e,s){let n=e.since===void 0?this.window:{...this.window,start:e.since};return e.points&&e.points.length>0?ut(e.points,n,{width:96,height:28,fill:!1,className:`mini ${s}`,stepMs:co(n)}):d`<span class="mini"></span>`}change(e,s){let{text:n,direction:r}=N(e,s.change),i=X(r),a=E(r),l=r==="none"?void 0:Bs(e,s.entityId,s.amount);return{cell:d`<div class="pct pchip ${r==="none"?"none":""}">${r==="none"?"\u2014":`${i?`${i} `:""}${n}`}</div>${l?d`<div class="a">${l}</div>`:h}`,className:a,lineClass:a||"flat"}}since(e,s){return s.since===void 0?h:d`<div class="since">${so(u(e,"change_since"),"date",xe(e,s.since))}</div>`}renderList(e,s){let n=this.columns,r=n?`--bp-price:${n.price}px;--bp-change:${n.change}px;--bp-figures:${n.figures}px`:"";return d`<div class="rows ${this.rowsLayout==="beside"?"":this.rowsLayout}" style=${r}>
      ${s.map(i=>{let a=this.change(e,i);return d`<div class="price-row" role="button" tabindex="0" @click=${R(this,i.entityId)} @keydown=${T(R(this,i.entityId))}>
          <div class="lead"><div class="n" title=${i.asset.shortName}>${i.asset.shortName}</div><div class="s">${i.asset.isin??i.asset.symbol}</div>${this.since(e,i)}</div>
          ${this.line(i,a.lineClass)}
          <div class="p">${I(e,i.entityId)??"\u2014"}</div>
          <div class="c ${a.className}">${a.cell}</div>
        </div>`})}
    </div>`}renderTiles(e,s){return d`<div class="tiles ${this.amountsInline?"inline":""}">
      ${s.map(n=>{let r=this.change(e,n);return d`<div class="tile" role="button" tabindex="0" @click=${R(this,n.entityId)} @keydown=${T(R(this,n.entityId))}>
          <div class="n" title=${n.asset.shortName}>${n.asset.shortName}</div>
          <div class="s">${n.asset.isin??n.asset.symbol}</div>
          <div class="p">${I(e,n.entityId)??"\u2014"}</div>
          <div class="c ${r.className}">${r.cell}</div>
          ${this.line(n,r.lineClass)}${this.since(e,n)}
        </div>`})}
    </div>`}footer(e,s,n){if(n==="EUR")return h;let r=s.map(i=>i.entityId?e.states[i.entityId]?.attributes.rate_date:void 0).map(i=>typeof i=="string"?Gs(e,i):void 0).find(i=>i!==void 0);return r?d`<div class="foot">${u(e,"ecb_footer",{currency:n,date:r})}</div>`:h}render(){let e=this.hass,s=this.config;if(!e||!s)return h;let n=$e(e,s.title||"Bitpanda Price Tracker");if(re(e).length===0)return d`<ha-card>${n}${Q(u(e,"empty_price_tracker"))}</ha-card>`;let{rows:r,total:i,folds:a,currency:l,currencies:c}=this.visible(e,s);return d`<ha-card>
      ${n}
      <div class="content">
        <div class="switches">
          ${at(e,this.timeframe,p=>this.selectTimeframe(p))}
          ${ro(e,c,l,p=>this.currency=p)}
        </div>
        ${r.length===0?Q(u(e,"empty_selection_assets")):s.layout==="tiles"?this.renderTiles(e,r):this.renderList(e,r)}
        ${a?d`<button class="show-all" @click=${()=>this.showAll=!this.showAll}>
              ${this.showAll?u(e,"show_less"):u(e,"show_all",{count:i})}
            </button>`:h}
      </div>
      ${this.footer(e,r,l)}
    </ha-card>`}};ct("bitpanda-price-tracker-card",Jt,{name:"Bitpanda Price Tracker",description:()=>u(Be(),"picker_price_tracker"),model:"Price Tracker"});
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
