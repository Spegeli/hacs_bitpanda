var je=globalThis,Oe=je.ShadowRoot&&(je.ShadyCSS===void 0||je.ShadyCSS.nativeShadow)&&"adoptedStyleSheets"in Document.prototype&&"replace"in CSSStyleSheet.prototype,Rt=Symbol(),ps=new WeakMap,ye=class{constructor(t,e,s){if(this._$cssResult$=!0,s!==Rt)throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");this.cssText=t,this.t=e}get styleSheet(){let t=this.o,e=this.t;if(Oe&&t===void 0){let s=e!==void 0&&e.length===1;s&&(t=ps.get(e)),t===void 0&&((this.o=t=new CSSStyleSheet).replaceSync(this.cssText),s&&ps.set(e,t))}return t}toString(){return this.cssText}},us=n=>new ye(typeof n=="string"?n:n+"",void 0,Rt),ve=(n,...t)=>{let e=n.length===1?n[0]:t.reduce((s,o,a)=>s+(i=>{if(i._$cssResult$===!0)return i.cssText;if(typeof i=="number")return i;throw Error("Value passed to 'css' function must be a 'css' function result: "+i+". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.")})(o)+n[a+1],n[0]);return new ye(e,n,Rt)},hs=(n,t)=>{if(Oe)n.adoptedStyleSheets=t.map(e=>e instanceof CSSStyleSheet?e:e.styleSheet);else for(let e of t){let s=document.createElement("style"),o=je.litNonce;o!==void 0&&s.setAttribute("nonce",o),s.textContent=e.cssText,n.appendChild(s)}},Et=Oe?n=>n:n=>n instanceof CSSStyleSheet?(t=>{let e="";for(let s of t.cssRules)e+=s.cssText;return us(e)})(n):n;var{is:Wn,defineProperty:Dn,getOwnPropertyDescriptor:Bn,getOwnPropertyNames:Un,getOwnPropertySymbols:Fn,getPrototypeOf:Vn}=Object,We=globalThis,ms=We.trustedTypes,qn=ms?ms.emptyScript:"",Gn=We.reactiveElementPolyfillSupport,be=(n,t)=>n,zt={toAttribute(n,t){switch(t){case Boolean:n=n?qn:null;break;case Object:case Array:n=n==null?n:JSON.stringify(n)}return n},fromAttribute(n,t){let e=n;switch(t){case Boolean:e=n!==null;break;case Number:e=n===null?null:Number(n);break;case Object:case Array:try{e=JSON.parse(n)}catch{e=null}}return e}},fs=(n,t)=>!Wn(n,t),_s={attribute:!0,type:String,converter:zt,reflect:!1,useDefault:!1,hasChanged:fs};Symbol.metadata??=Symbol("metadata"),We.litPropertyMetadata??=new WeakMap;var D=class extends HTMLElement{static addInitializer(t){this._$Ei(),(this.l??=[]).push(t)}static get observedAttributes(){return this.finalize(),this._$Eh&&[...this._$Eh.keys()]}static createProperty(t,e=_s){if(e.state&&(e.attribute=!1),this._$Ei(),this.prototype.hasOwnProperty(t)&&((e=Object.create(e)).wrapped=!0),this.elementProperties.set(t,e),!e.noAccessor){let s=Symbol(),o=this.getPropertyDescriptor(t,s,e);o!==void 0&&Dn(this.prototype,t,o)}}static getPropertyDescriptor(t,e,s){let{get:o,set:a}=Bn(this.prototype,t)??{get(){return this[e]},set(i){this[e]=i}};return{get:o,set(i){let l=o?.call(this);a?.call(this,i),this.requestUpdate(t,l,s)},configurable:!0,enumerable:!0}}static getPropertyOptions(t){return this.elementProperties.get(t)??_s}static _$Ei(){if(this.hasOwnProperty(be("elementProperties")))return;let t=Vn(this);t.finalize(),t.l!==void 0&&(this.l=[...t.l]),this.elementProperties=new Map(t.elementProperties)}static finalize(){if(this.hasOwnProperty(be("finalized")))return;if(this.finalized=!0,this._$Ei(),this.hasOwnProperty(be("properties"))){let e=this.properties,s=[...Un(e),...Fn(e)];for(let o of s)this.createProperty(o,e[o])}let t=this[Symbol.metadata];if(t!==null){let e=litPropertyMetadata.get(t);if(e!==void 0)for(let[s,o]of e)this.elementProperties.set(s,o)}this._$Eh=new Map;for(let[e,s]of this.elementProperties){let o=this._$Eu(e,s);o!==void 0&&this._$Eh.set(o,e)}this.elementStyles=this.finalizeStyles(this.styles)}static finalizeStyles(t){let e=[];if(Array.isArray(t)){let s=new Set(t.flat(1/0).reverse());for(let o of s)e.unshift(Et(o))}else t!==void 0&&e.push(Et(t));return e}static _$Eu(t,e){let s=e.attribute;return s===!1?void 0:typeof s=="string"?s:typeof t=="string"?t.toLowerCase():void 0}constructor(){super(),this._$Ep=void 0,this.isUpdatePending=!1,this.hasUpdated=!1,this._$Em=null,this._$Ev()}_$Ev(){this._$ES=new Promise(t=>this.enableUpdating=t),this._$AL=new Map,this._$E_(),this.requestUpdate(),this.constructor.l?.forEach(t=>t(this))}addController(t){(this._$EO??=new Set).add(t),this.renderRoot!==void 0&&this.isConnected&&t.hostConnected?.()}removeController(t){this._$EO?.delete(t)}_$E_(){let t=new Map,e=this.constructor.elementProperties;for(let s of e.keys())this.hasOwnProperty(s)&&(t.set(s,this[s]),delete this[s]);t.size>0&&(this._$Ep=t)}createRenderRoot(){let t=this.shadowRoot??this.attachShadow(this.constructor.shadowRootOptions);return hs(t,this.constructor.elementStyles),t}connectedCallback(){this.renderRoot??=this.createRenderRoot(),this.enableUpdating(!0),this._$EO?.forEach(t=>t.hostConnected?.())}enableUpdating(t){}disconnectedCallback(){this._$EO?.forEach(t=>t.hostDisconnected?.())}attributeChangedCallback(t,e,s){this._$AK(t,s)}_$ET(t,e){let s=this.constructor.elementProperties.get(t),o=this.constructor._$Eu(t,s);if(o!==void 0&&s.reflect===!0){let a=(s.converter?.toAttribute!==void 0?s.converter:zt).toAttribute(e,s.type);this._$Em=t,a==null?this.removeAttribute(o):this.setAttribute(o,a),this._$Em=null}}_$AK(t,e){let s=this.constructor,o=s._$Eh.get(t);if(o!==void 0&&this._$Em!==o){let a=s.getPropertyOptions(o),i=typeof a.converter=="function"?{fromAttribute:a.converter}:a.converter?.fromAttribute!==void 0?a.converter:zt;this._$Em=o;let l=i.fromAttribute(e,a.type);this[o]=l??this._$Ej?.get(o)??l,this._$Em=null}}requestUpdate(t,e,s,o=!1,a){if(t!==void 0){let i=this.constructor;if(o===!1&&(a=this[t]),s??=i.getPropertyOptions(t),!((s.hasChanged??fs)(a,e)||s.useDefault&&s.reflect&&a===this._$Ej?.get(t)&&!this.hasAttribute(i._$Eu(t,s))))return;this.C(t,e,s)}this.isUpdatePending===!1&&(this._$ES=this._$EP())}C(t,e,{useDefault:s,reflect:o,wrapped:a},i){s&&!(this._$Ej??=new Map).has(t)&&(this._$Ej.set(t,i??e??this[t]),a!==!0||i!==void 0)||(this._$AL.has(t)||(this.hasUpdated||s||(e=void 0),this._$AL.set(t,e)),o===!0&&this._$Em!==t&&(this._$Eq??=new Set).add(t))}async _$EP(){this.isUpdatePending=!0;try{await this._$ES}catch(e){Promise.reject(e)}let t=this.scheduleUpdate();return t!=null&&await t,!this.isUpdatePending}scheduleUpdate(){return this.performUpdate()}performUpdate(){if(!this.isUpdatePending)return;if(!this.hasUpdated){if(this.renderRoot??=this.createRenderRoot(),this._$Ep){for(let[o,a]of this._$Ep)this[o]=a;this._$Ep=void 0}let s=this.constructor.elementProperties;if(s.size>0)for(let[o,a]of s){let{wrapped:i}=a,l=this[o];i!==!0||this._$AL.has(o)||l===void 0||this.C(o,void 0,a,l)}}let t=!1,e=this._$AL;try{t=this.shouldUpdate(e),t?(this.willUpdate(e),this._$EO?.forEach(s=>s.hostUpdate?.()),this.update(e)):this._$EM()}catch(s){throw t=!1,this._$EM(),s}t&&this._$AE(e)}willUpdate(t){}_$AE(t){this._$EO?.forEach(e=>e.hostUpdated?.()),this.hasUpdated||(this.hasUpdated=!0,this.firstUpdated(t)),this.updated(t)}_$EM(){this._$AL=new Map,this.isUpdatePending=!1}get updateComplete(){return this.getUpdateComplete()}getUpdateComplete(){return this._$ES}shouldUpdate(t){return!0}update(t){this._$Eq&&=this._$Eq.forEach(e=>this._$ET(e,this[e])),this._$EM()}updated(t){}firstUpdated(t){}};D.elementStyles=[],D.shadowRootOptions={mode:"open"},D[be("elementProperties")]=new Map,D[be("finalized")]=new Map,Gn?.({ReactiveElement:D}),(We.reactiveElementVersions??=[]).push("2.1.2");var Ht=globalThis,gs=n=>n,De=Ht.trustedTypes,ws=De?De.createPolicy("lit-html",{createHTML:n=>n}):void 0,It="$lit$",B=`lit$${Math.random().toFixed(9).slice(2)}$`,Nt="?"+B,Kn=`<${Nt}>`,Q=document,xe=()=>Q.createComment(""),$e=n=>n===null||typeof n!="object"&&typeof n!="function",Mt=Array.isArray,$s=n=>Mt(n)||typeof n?.[Symbol.iterator]=="function",Lt=`[ 	
\f\r]`,ke=/<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g,ys=/-->/g,vs=/>/g,J=RegExp(`>|${Lt}(?:([^\\s"'>=/]+)(${Lt}*=${Lt}*(?:[^ 	
\f\r"'\`<>=]|("|')|))|$)`,"g"),bs=/'/g,ks=/"/g,As=/^(?:script|style|textarea|title)$/i,jt=n=>(t,...e)=>({_$litType$:n,strings:t,values:e}),d=jt(1),de=jt(2),da=jt(3),ee=Symbol.for("lit-noChange"),u=Symbol.for("lit-nothing"),xs=new WeakMap,X=Q.createTreeWalker(Q,129);function Ss(n,t){if(!Mt(n)||!n.hasOwnProperty("raw"))throw Error("invalid template strings array");return ws!==void 0?ws.createHTML(t):t}var Ts=(n,t)=>{let e=n.length-1,s=[],o,a=t===2?"<svg>":t===3?"<math>":"",i=ke;for(let l=0;l<e;l++){let r=n[l],c,p,h=-1,_=0;for(;_<r.length&&(i.lastIndex=_,p=i.exec(r),p!==null);)_=i.lastIndex,i===ke?p[1]==="!--"?i=ys:p[1]!==void 0?i=vs:p[2]!==void 0?(As.test(p[2])&&(o=RegExp("</"+p[2],"g")),i=J):p[3]!==void 0&&(i=J):i===J?p[0]===">"?(i=o??ke,h=-1):p[1]===void 0?h=-2:(h=i.lastIndex-p[2].length,c=p[1],i=p[3]===void 0?J:p[3]==='"'?ks:bs):i===ks||i===bs?i=J:i===ys||i===vs?i=ke:(i=J,o=void 0);let f=i===J&&n[l+1].startsWith("/>")?" ":"";a+=i===ke?r+Kn:h>=0?(s.push(c),r.slice(0,h)+It+r.slice(h)+B+f):r+B+(h===-2?l:f)}return[Ss(n,a+(n[e]||"<?>")+(t===2?"</svg>":t===3?"</math>":"")),s]},Ae=class n{constructor({strings:t,_$litType$:e},s){let o;this.parts=[];let a=0,i=0,l=t.length-1,r=this.parts,[c,p]=Ts(t,e);if(this.el=n.createElement(c,s),X.currentNode=this.el.content,e===2||e===3){let h=this.el.content.firstChild;h.replaceWith(...h.childNodes)}for(;(o=X.nextNode())!==null&&r.length<l;){if(o.nodeType===1){if(o.hasAttributes())for(let h of o.getAttributeNames())if(h.endsWith(It)){let _=p[i++],f=o.getAttribute(h).split(B),y=/([.?@])?(.*)/.exec(_);r.push({type:1,index:a,name:y[2],strings:f,ctor:y[1]==="."?Ue:y[1]==="?"?Fe:y[1]==="@"?Ve:se}),o.removeAttribute(h)}else h.startsWith(B)&&(r.push({type:6,index:a}),o.removeAttribute(h));if(As.test(o.tagName)){let h=o.textContent.split(B),_=h.length-1;if(_>0){o.textContent=De?De.emptyScript:"";for(let f=0;f<_;f++)o.append(h[f],xe()),X.nextNode(),r.push({type:2,index:++a});o.append(h[_],xe())}}}else if(o.nodeType===8)if(o.data===Nt)r.push({type:2,index:a});else{let h=-1;for(;(h=o.data.indexOf(B,h+1))!==-1;)r.push({type:7,index:a}),h+=B.length-1}a++}}static createElement(t,e){let s=Q.createElement("template");return s.innerHTML=t,s}};function te(n,t,e=n,s){if(t===ee)return t;let o=s!==void 0?e._$Co?.[s]:e._$Cl,a=$e(t)?void 0:t._$litDirective$;return o?.constructor!==a&&(o?._$AO?.(!1),a===void 0?o=void 0:(o=new a(n),o._$AT(n,e,s)),s!==void 0?(e._$Co??=[])[s]=o:e._$Cl=o),o!==void 0&&(t=te(n,o._$AS(n,t.values),o,s)),t}var Be=class{constructor(t,e){this._$AV=[],this._$AN=void 0,this._$AD=t,this._$AM=e}get parentNode(){return this._$AM.parentNode}get _$AU(){return this._$AM._$AU}u(t){let{el:{content:e},parts:s}=this._$AD,o=(t?.creationScope??Q).importNode(e,!0);X.currentNode=o;let a=X.nextNode(),i=0,l=0,r=s[0];for(;r!==void 0;){if(i===r.index){let c;r.type===2?c=new ce(a,a.nextSibling,this,t):r.type===1?c=new r.ctor(a,r.name,r.strings,this,t):r.type===6&&(c=new qe(a,this,t)),this._$AV.push(c),r=s[++l]}i!==r?.index&&(a=X.nextNode(),i++)}return X.currentNode=Q,o}p(t){let e=0;for(let s of this._$AV)s!==void 0&&(s.strings!==void 0?(s._$AI(t,s,e),e+=s.strings.length-2):s._$AI(t[e])),e++}},ce=class n{get _$AU(){return this._$AM?._$AU??this._$Cv}constructor(t,e,s,o){this.type=2,this._$AH=u,this._$AN=void 0,this._$AA=t,this._$AB=e,this._$AM=s,this.options=o,this._$Cv=o?.isConnected??!0}get parentNode(){let t=this._$AA.parentNode,e=this._$AM;return e!==void 0&&t?.nodeType===11&&(t=e.parentNode),t}get startNode(){return this._$AA}get endNode(){return this._$AB}_$AI(t,e=this){t=te(this,t,e),$e(t)?t===u||t==null||t===""?(this._$AH!==u&&this._$AR(),this._$AH=u):t!==this._$AH&&t!==ee&&this._(t):t._$litType$!==void 0?this.$(t):t.nodeType!==void 0?this.T(t):$s(t)?this.k(t):this._(t)}O(t){return this._$AA.parentNode.insertBefore(t,this._$AB)}T(t){this._$AH!==t&&(this._$AR(),this._$AH=this.O(t))}_(t){this._$AH!==u&&$e(this._$AH)?this._$AA.nextSibling.data=t:this.T(Q.createTextNode(t)),this._$AH=t}$(t){let{values:e,_$litType$:s}=t,o=typeof s=="number"?this._$AC(t):(s.el===void 0&&(s.el=Ae.createElement(Ss(s.h,s.h[0]),this.options)),s);if(this._$AH?._$AD===o)this._$AH.p(e);else{let a=new Be(o,this),i=a.u(this.options);a.p(e),this.T(i),this._$AH=a}}_$AC(t){let e=xs.get(t.strings);return e===void 0&&xs.set(t.strings,e=new Ae(t)),e}k(t){Mt(this._$AH)||(this._$AH=[],this._$AR());let e=this._$AH,s,o=0;for(let a of t)o===e.length?e.push(s=new n(this.O(xe()),this.O(xe()),this,this.options)):s=e[o],s._$AI(a),o++;o<e.length&&(this._$AR(s&&s._$AB.nextSibling,o),e.length=o)}_$AR(t=this._$AA.nextSibling,e){for(this._$AP?.(!1,!0,e);t!==this._$AB;){let s=gs(t).nextSibling;gs(t).remove(),t=s}}setConnected(t){this._$AM===void 0&&(this._$Cv=t,this._$AP?.(t))}},se=class{get tagName(){return this.element.tagName}get _$AU(){return this._$AM._$AU}constructor(t,e,s,o,a){this.type=1,this._$AH=u,this._$AN=void 0,this.element=t,this.name=e,this._$AM=o,this.options=a,s.length>2||s[0]!==""||s[1]!==""?(this._$AH=Array(s.length-1).fill(new String),this.strings=s):this._$AH=u}_$AI(t,e=this,s,o){let a=this.strings,i=!1;if(a===void 0)t=te(this,t,e,0),i=!$e(t)||t!==this._$AH&&t!==ee,i&&(this._$AH=t);else{let l=t,r,c;for(t=a[0],r=0;r<a.length-1;r++)c=te(this,l[s+r],e,r),c===ee&&(c=this._$AH[r]),i||=!$e(c)||c!==this._$AH[r],c===u?t=u:t!==u&&(t+=(c??"")+a[r+1]),this._$AH[r]=c}i&&!o&&this.j(t)}j(t){t===u?this.element.removeAttribute(this.name):this.element.setAttribute(this.name,t??"")}},Ue=class extends se{constructor(){super(...arguments),this.type=3}j(t){this.element[this.name]=t===u?void 0:t}},Fe=class extends se{constructor(){super(...arguments),this.type=4}j(t){this.element.toggleAttribute(this.name,!!t&&t!==u)}},Ve=class extends se{constructor(t,e,s,o,a){super(t,e,s,o,a),this.type=5}_$AI(t,e=this){if((t=te(this,t,e,0)??u)===ee)return;let s=this._$AH,o=t===u&&s!==u||t.capture!==s.capture||t.once!==s.once||t.passive!==s.passive,a=t!==u&&(s===u||o);o&&this.element.removeEventListener(this.name,this,s),a&&this.element.addEventListener(this.name,this,t),this._$AH=t}handleEvent(t){typeof this._$AH=="function"?this._$AH.call(this.options?.host??this.element,t):this._$AH.handleEvent(t)}},qe=class{constructor(t,e,s){this.element=t,this.type=6,this._$AN=void 0,this._$AM=e,this.options=s}get _$AU(){return this._$AM._$AU}_$AI(t){te(this,t)}},Cs={M:It,P:B,A:Nt,C:1,L:Ts,R:Be,D:$s,V:te,I:ce,H:se,N:Fe,U:Ve,B:Ue,F:qe},Zn=Ht.litHtmlPolyfillSupport;Zn?.(Ae,ce),(Ht.litHtmlVersions??=[]).push("3.3.3");var Ps=(n,t,e)=>{let s=e?.renderBefore??t,o=s._$litPart$;if(o===void 0){let a=e?.renderBefore??null;s._$litPart$=o=new ce(t.insertBefore(xe(),a),a,void 0,e??{})}return o._$AI(n),o};var Ot=globalThis,M=class extends D{constructor(){super(...arguments),this.renderOptions={host:this},this._$Do=void 0}createRenderRoot(){let t=super.createRenderRoot();return this.renderOptions.renderBefore??=t.firstChild,t}update(t){let e=this.render();this.hasUpdated||(this.renderOptions.isConnected=this.isConnected),super.update(t),this._$Do=Ps(e,this.renderRoot,this.renderOptions)}connectedCallback(){super.connectedCallback(),this._$Do?.setConnected(!0)}disconnectedCallback(){super.disconnectedCallback(),this._$Do?.setConnected(!1)}render(){return ee}};M._$litElement$=!0,M.finalized=!0,Ot.litElementHydrateSupport?.({LitElement:M});var Yn=Ot.litElementPolyfillSupport;Yn?.({LitElement:M});(Ot.litElementVersions??=[]).push("4.2.2");var Rs={tf_day:"1T",tf_week:"1W",tf_month:"1M",tf_six_month:"6M",tf_year:"1J",aria_timeframe:"Zeitraum",aria_currency:"W\xE4hrung",search_placeholder:"Name, Symbol oder ISIN",search_none:"Kein Wallet passt zu \u201E{query}\u201C.",aria_search:"Wallets durchsuchen",aria_search_clear:"Suche leeren",return_day:"Rendite \xFCber 1 Tag",return_week:"Rendite \xFCber 1 Woche",return_month:"Rendite \xFCber 1 Monat",return_six_month:"Rendite \xFCber 6 Monate",return_year:"Rendite \xFCber 1 Jahr",value_line:"Gesamtwert, {start} \u2013 heute",value_line_day:"Gesamtwert, letzte 24 Stunden",line_point:"{value}, {time}",staking_line:"Staking",staking_wallets_one:"in {count} Wallet",staking_wallets_other:"in {count} Wallets",staking_apr:"APR {apr}",since_purchase:"Seit Kauf",cash:"Bargeld",cash_plus:"Cash Plus",staked:"{share} im Staking",show_all:"Alle anzeigen ({count})",show_less:"Weniger anzeigen",detail_price:"Aktueller Preis",detail_staked:"Im Staking",detail_staking_apr:"Staking-APR",detail_average_buy_price:"\xD8 Kaufpreis",detail_invested:"Investiert",detail_return_24h:"Rendite (24 h)",detail_total_return:"Gesamtrendite",detail_staking:"Staking",detail_earned_30d:"Verdient (30 Tage)",detail_earned_total:"Verdient (gesamt)",detail_payouts:"Gutschriften",detail_payouts_value:"{count} \xB7 zuletzt {date}",shares_one:"St\xFCck",shares_other:"St\xFCck",assets_missing_one:"Dazu geh\xF6rt ein gew\xE4hltes Asset, das es gerade nicht gibt. Es bleibt gespeichert und gilt wieder, sobald es wieder da ist.",assets_missing_other:"Dazu geh\xF6ren {count} gew\xE4hlte Assets, die es gerade nicht gibt. Sie bleiben gespeichert und gelten wieder, sobald sie wieder da sind.",amount_hidden:"Betrag verborgen",allocation_label:"Verteilung: {parts}",eye_hide:"Betr\xE4ge verbergen",eye_show:"Betr\xE4ge anzeigen",change_since:"\xC4nderung seit {date}",ecb_footer:"Preise in {currency}: Bitpandas Euro-Preise, umgerechnet zum EZB-Referenzkurs vom {date}. Die Prozente und Betr\xE4ge in {currency} enthalten deshalb auch die Bewegung des Wechselkurses.",ecb_footer_percent:"Preise in {currency}: Bitpandas Euro-Preise, umgerechnet zum EZB-Referenzkurs vom {date}. Die Prozente enthalten deshalb auch die Bewegung des Wechselkurses.",empty_portfolio:"Richte das Bitpanda Portfolio ein oder aktiviere es, dann erscheint es hier.",empty_wallets:"Noch keine Wallets.",empty_selection_wallets:"Keine Wallets in der Auswahl dieser Karte.",empty_selection_assets:"Keine Assets in der Auswahl dieser Karte.",empty_price_tracker:"Richte den Bitpanda Price Tracker ein oder aktiviere ihn und f\xFCge Assets hinzu, dann erscheinen sie hier.",picker_portfolio:"Gesamtwert und Rendite mit Verlauf, Rendite seit Kauf, Bargeld und Cash Plus, Staking, Verteilung und deine Wallets; jeder Teil l\xE4sst sich ausblenden.",picker_price_tracker:"Preise und \xC4nderungen deiner verfolgten Assets, je mit Verlauf, als Liste oder Kacheln.",invalid_option:"Ung\xFCltiger Wert f\xFCr \u201E{option}\u201C: {value}. Erlaubt: {allowed}.",allowed_text:"Text",allowed_assets:"eine Liste von Asset-IDs oder Ger\xE4te-IDs",allowed_groups:"eine Liste aus {values}",group_content:"Inhalt",group_wallets:"Wallets",group_assets:"Assets",group_appearance:"Darstellung",opt_title:"Titel",opt_title_help:"Leer lassen f\xFCr den grau angezeigten Namen",opt_timeframe:"Standard-Zeitraum",opt_timeframe_help:"Die Tasten 1T bis 1J auf der Karte wechseln ihn nur vor\xFCbergehend",tfo_day:"1 Tag",tfo_week:"1 Woche",tfo_month:"1 Monat",tfo_six_month:"6 Monate",tfo_year:"1 Jahr",opt_show_cash:"Bargeld und Cash Plus",opt_show_staking:"Staking",opt_show_allocation:"Verteilung",opt_show_allocation_help:"Der farbige Balken mit den Anteilen der Asset-Gruppen und des Bargelds",opt_show_total:"Gesamtwert und Rendite",opt_show_total_help:"Die Zeitraum-Tasten bleiben, solange der Verlauf gezeigt wird, au\xDFer \u201EDarstellung\u201C blendet sie aus",opt_show_since_purchase:"Rendite seit Kauf",opt_show_since_purchase_help:"Nur mit dem Gesamtwert und seiner Rendite",opt_show_line:"Verlauf des Gesamtwerts",opt_show_wallets:"Wallets",opt_group_wallets:"Wallets in Asset-Gruppen",opt_show_search:"Suchfeld",opt_show_search_help:"Findet Wallets nach Name, Symbol oder ISIN",opt_sort:"Sortieren nach",sort_value:"Wert",sort_return:"Rendite seit Kauf",sort_name:"Name",sort_selection:"Reihenfolge wie gew\xE4hlt",sort_change_desc:"\xC4nderung, h\xF6chste zuerst",sort_change_asc:"\xC4nderung, niedrigste zuerst",opt_sort_help_tracker:"\u201EReihenfolge wie gew\xE4hlt\u201C gilt nur mit \u201ENur die gew\xE4hlten\u201C Assets, sonst nach Name",opt_group_selection:"Angezeigte Asset-Gruppen",opt_group_selection_help:"Gilt nur f\xFCr die Wallets; Gesamtwert, Bargeld, Cash Plus und Verteilung zeigen immer das ganze Portfolio",opt_groups:"Asset-Gruppen w\xE4hlen",opt_asset_selection:"Angezeigte Assets",opt_asset_selection_wallets:"Angezeigte Wallets",sel_all:"Alle",sel_all_except:"Alle au\xDFer den gew\xE4hlten",sel_only:"Nur die gew\xE4hlten",opt_assets:"Assets w\xE4hlen",opt_assets_wallets:"Wallets w\xE4hlen",opt_assets_help:"Ein Asset aus einer ausgeblendeten Asset-Gruppe bleibt verborgen, auch wenn es hier gew\xE4hlt ist",opt_assets_help_wallets:"Ein Wallet aus einer ausgeblendeten Asset-Gruppe bleibt verborgen, auch wenn es hier gew\xE4hlt ist",opt_hide_amounts:"Betr\xE4ge zun\xE4chst verbergen",opt_hide_amounts_help:"Prozente bleiben sichtbar; das Auge auf der Karte zeigt die Betr\xE4ge nur vor\xFCbergehend",opt_show_header:"Kopfzeile",opt_show_header_help_portfolio:"Titel und Auge; ohne sie steht das Auge neben dem Gesamtwert, ohne Gesamtwert in einer eigenen Zeile",opt_show_timeframes:"Zeitraum-Tasten",opt_show_timeframes_help_portfolio:"Nur solange der Gesamtwert oder der Verlauf gezeigt wird; ohne sie bleibt der oben gew\xE4hlte Zeitraum",opt_show_timeframes_help:"Ohne sie bleibt der oben gew\xE4hlte Zeitraum",opt_show_currencies:"W\xE4hrungs-Tasten",opt_show_currencies_help:"Ohne sie bleibt die oben gew\xE4hlte W\xE4hrung",opt_show_lines:"Kursverl\xE4ufe",opt_show_amounts:"\xC4nderung in der W\xE4hrung des Preises",opt_limit:"Assets vor \u201EAlle anzeigen\u201C",opt_limit_wallets:"Wallets vor \u201EAlle anzeigen\u201C",opt_limit_help:"0 zeigt alle Assets",opt_limit_help_wallets:"Nur wenn \u201EWallets in Asset-Gruppen\u201C aus ist; 0 zeigt alle",opt_layout:"Anzeigen als",layout_list:"Liste",layout_tiles:"Kacheln",opt_currency:"Standard-W\xE4hrung",opt_currency_help:"Die Tasten auf der Karte wechseln sie nur vor\xFCbergehend; weitere W\xE4hrungen \xFCber \u201EKonfigurieren\u201C beim Price Tracker"};var Es={tf_day:"1D",tf_week:"1W",tf_month:"1M",tf_six_month:"6M",tf_year:"1Y",aria_timeframe:"Timeframe",aria_currency:"Currency",search_placeholder:"Name, symbol or ISIN",search_none:"No wallet matches \u201C{query}\u201D.",aria_search:"Search wallets",aria_search_clear:"Clear search",return_day:"return over 1 day",return_week:"return over 1 week",return_month:"return over 1 month",return_six_month:"return over 6 months",return_year:"return over 1 year",value_line:"Total value, {start} \u2013 today",value_line_day:"Total value, last 24 hours",line_point:"{value}, {time}",staking_line:"Staking",staking_wallets_one:"in {count} wallet",staking_wallets_other:"in {count} wallets",staking_apr:"APR {apr}",since_purchase:"Since purchase",cash:"Cash",cash_plus:"Cash Plus",staked:"{share} staked",show_all:"Show all ({count})",show_less:"Show less",detail_price:"Current price",detail_staked:"Staked",detail_staking_apr:"Staking APR",detail_average_buy_price:"Average buy price",detail_invested:"Invested",detail_return_24h:"Return (24 h)",detail_total_return:"Total return",detail_staking:"Staking",detail_earned_30d:"Earned (30 days)",detail_earned_total:"Earned (total)",detail_payouts:"Payouts",detail_payouts_value:"{count} \xB7 last {date}",shares_one:"share",shares_other:"shares",assets_missing_one:"This includes a chosen asset that is not there right now. It stays saved and applies again once it is back.",assets_missing_other:"This includes {count} chosen assets that are not there right now. They stay saved and apply again once they are back.",amount_hidden:"Amount hidden",allocation_label:"Allocation: {parts}",eye_hide:"Hide amounts",eye_show:"Show amounts",change_since:"Change since {date}",ecb_footer:"Prices in {currency}: Bitpanda's EUR prices converted at the ECB reference rate of {date}. The percentages and amounts in {currency} therefore also include the exchange rate's move.",ecb_footer_percent:"Prices in {currency}: Bitpanda's EUR prices converted at the ECB reference rate of {date}. The percentages therefore also include the exchange rate's move.",empty_portfolio:"Set up the Bitpanda Portfolio or enable it to see it here.",empty_wallets:"No wallets yet.",empty_selection_wallets:"No wallets in this card's selection.",empty_selection_assets:"No assets in this card's selection.",empty_price_tracker:"Set up the Bitpanda Price Tracker or enable it and add assets to it to see them here.",picker_portfolio:"Total value and return with a value line, return since purchase, Cash and Cash Plus, staking, allocation and your wallets; each part can be left out.",picker_price_tracker:"Prices and changes of the assets you track, each with a line, as a list or tiles.",invalid_option:"Invalid value for \u201C{option}\u201D: {value}. Allowed: {allowed}.",allowed_text:"text",allowed_assets:"a list of asset IDs or device IDs",allowed_groups:"a list of {values}",group_content:"Content",group_wallets:"Wallets",group_assets:"Assets",group_appearance:"Appearance",opt_title:"Title",opt_title_help:"Leave empty for the name shown in grey",opt_timeframe:"Default timeframe",opt_timeframe_help:"The 1D to 1Y buttons on the card change it only temporarily",tfo_day:"1 day",tfo_week:"1 week",tfo_month:"1 month",tfo_six_month:"6 months",tfo_year:"1 year",opt_show_cash:"Cash and Cash Plus",opt_show_staking:"Staking",opt_show_allocation:"Allocation bar",opt_show_allocation_help:"The coloured bar showing the share of each asset group and of cash",opt_show_total:"Total value and return",opt_show_total_help:"The timeframe buttons stay while the line is shown, unless \u201CAppearance\u201D hides them",opt_show_since_purchase:"Return since purchase",opt_show_since_purchase_help:"Only with the total value and its return",opt_show_line:"Total value line",opt_show_wallets:"Wallets",opt_group_wallets:"Wallets in asset groups",opt_show_search:"Search field",opt_show_search_help:"Finds wallets by name, symbol or ISIN",opt_sort:"Sort by",sort_value:"Value",sort_return:"Return since purchase",sort_name:"Name",sort_selection:"Order as chosen",sort_change_desc:"Change, highest first",sort_change_asc:"Change, lowest first",opt_sort_help_tracker:"\u201COrder as chosen\u201D applies only when assets are set to \u201COnly the ones chosen\u201D; otherwise by name",opt_group_selection:"Asset groups shown",opt_group_selection_help:"Applies to the wallets only; total value, Cash, Cash Plus and allocation always show the whole portfolio",opt_groups:"Choose asset groups",opt_asset_selection:"Assets shown",opt_asset_selection_wallets:"Wallets shown",sel_all:"All",sel_all_except:"All except the ones chosen",sel_only:"Only the ones chosen",opt_assets:"Choose assets",opt_assets_wallets:"Choose wallets",opt_assets_help:"An asset from a hidden asset group stays hidden, even when chosen here",opt_assets_help_wallets:"A wallet from a hidden asset group stays hidden, even when chosen here",opt_hide_amounts:"Hide amounts initially",opt_hide_amounts_help:"Percentages stay visible; the eye on the card shows the amounts only temporarily",opt_show_header:"Header",opt_show_header_help_portfolio:"Title and eye; without it the eye stands beside the total value, or in a row of its own without that",opt_show_timeframes:"Timeframe buttons",opt_show_timeframes_help_portfolio:"Only while the total value or the line is shown; without them the card keeps the timeframe chosen above",opt_show_timeframes_help:"Without them the card keeps the timeframe chosen above",opt_show_currencies:"Currency buttons",opt_show_currencies_help:"Without them the card keeps the currency chosen above",opt_show_lines:"Price lines",opt_show_amounts:"Change in the price's currency",opt_limit:"Assets before \u201CShow all\u201D",opt_limit_wallets:"Wallets before \u201CShow all\u201D",opt_limit_help:"0 shows every asset",opt_limit_help_wallets:"Only while \u201CWallets in asset groups\u201D is off; 0 shows all",opt_layout:"Show as",layout_list:"List",layout_tiles:"Tiles",opt_currency:"Default currency",opt_currency_help:"The buttons on the card change it only temporarily; more currencies via \u201CConfigure\u201D on the Price Tracker"};var zs={tf_day:"1D",tf_week:"1S",tf_month:"1M",tf_six_month:"6M",tf_year:"1A",aria_timeframe:"Periodo",aria_currency:"Moneda",search_placeholder:"Nombre, s\xEDmbolo o ISIN",search_none:"Ning\xFAn wallet coincide con \xAB{query}\xBB.",aria_search:"Buscar wallets",aria_search_clear:"Borrar b\xFAsqueda",return_day:"rentabilidad en 1 d\xEDa",return_week:"rentabilidad en 1 semana",return_month:"rentabilidad en 1 mes",return_six_month:"rentabilidad en 6 meses",return_year:"rentabilidad en 1 a\xF1o",value_line:"Valor total, {start} \u2013 hoy",value_line_day:"Valor total, \xFAltimas 24 horas",line_point:"{value}, {time}",staking_line:"Staking",staking_wallets_one:"en {count} wallet",staking_wallets_many:"en {count} wallets",staking_wallets_other:"en {count} wallets",staking_apr:"APR {apr}",since_purchase:"Desde la compra",cash:"Efectivo",cash_plus:"Cash Plus",staked:"{share} en staking",show_all:"Mostrar todo ({count})",show_less:"Mostrar menos",detail_price:"Precio actual",detail_staked:"En staking",detail_staking_apr:"APR de staking",detail_average_buy_price:"Precio medio de compra",detail_invested:"Importe invertido",detail_return_24h:"Rentabilidad (24 h)",detail_total_return:"Rentabilidad total",detail_staking:"Staking",detail_earned_30d:"Ganado (30 d\xEDas)",detail_earned_total:"Ganado (total)",detail_payouts:"Pagos",detail_payouts_value:"{count} \xB7 \xFAltimo el {date}",shares_one:"t\xEDtulo",shares_other:"t\xEDtulos",shares_many:"t\xEDtulos",assets_missing_one:"Incluye un activo elegido que ahora mismo no existe. Se queda guardado y vuelve a aplicarse en cuanto vuelva.",assets_missing_many:"Incluye {count} activos elegidos que ahora mismo no existen. Se quedan guardados y vuelven a aplicarse en cuanto vuelvan.",assets_missing_other:"Incluye {count} activos elegidos que ahora mismo no existen. Se quedan guardados y vuelven a aplicarse en cuanto vuelvan.",amount_hidden:"Importe oculto",allocation_label:"Distribuci\xF3n: {parts}",eye_hide:"Ocultar importes",eye_show:"Mostrar importes",change_since:"Variaci\xF3n desde el {date}",ecb_footer:"Precios en {currency}: precios en EUR de Bitpanda convertidos al tipo de referencia del BCE del {date}. Los porcentajes y los importes en {currency} incluyen por tanto tambi\xE9n la variaci\xF3n del tipo de cambio.",ecb_footer_percent:"Precios en {currency}: precios en EUR de Bitpanda convertidos al tipo de referencia del BCE del {date}. Los porcentajes incluyen por tanto tambi\xE9n la variaci\xF3n del tipo de cambio.",empty_portfolio:"Configura el Bitpanda Portfolio o act\xEDvalo para verlo aqu\xED.",empty_wallets:"Todav\xEDa no hay wallets.",empty_selection_wallets:"Ning\xFAn wallet en la selecci\xF3n de esta tarjeta.",empty_selection_assets:"Ning\xFAn activo en la selecci\xF3n de esta tarjeta.",empty_price_tracker:"Configura el Bitpanda Price Tracker o act\xEDvalo y a\xF1ade activos para verlos aqu\xED.",picker_portfolio:"Valor total y rentabilidad con l\xEDnea, rentabilidad desde la compra, efectivo y Cash Plus, staking, distribuci\xF3n y tus wallets; cada parte se puede ocultar.",picker_price_tracker:"Precios y cambios de los activos que sigues, cada uno con su l\xEDnea, en lista o en mosaicos.",invalid_option:"Valor no v\xE1lido para \xAB{option}\xBB: {value}. Permitidos: {allowed}.",allowed_text:"texto",allowed_assets:"una lista de ID de activo o ID de dispositivo",allowed_groups:"una lista de {values}",group_content:"Contenido",group_wallets:"Wallets",group_assets:"Activos",group_appearance:"Apariencia",opt_title:"T\xEDtulo",opt_title_help:"D\xE9jalo vac\xEDo para el nombre mostrado en gris",opt_timeframe:"Periodo predeterminado",opt_timeframe_help:"Los botones 1D a 1A de la tarjeta lo cambian solo temporalmente",tfo_day:"1 d\xEDa",tfo_week:"1 semana",tfo_month:"1 mes",tfo_six_month:"6 meses",tfo_year:"1 a\xF1o",opt_show_cash:"Efectivo y Cash Plus",opt_show_staking:"Staking",opt_show_allocation:"Barra de distribuci\xF3n",opt_show_allocation_help:"La barra de colores con la proporci\xF3n de cada grupo de activos y del efectivo",opt_show_total:"Valor total y rentabilidad",opt_show_total_help:"Los botones de periodo se mantienen mientras se muestre la l\xEDnea, salvo que \xABApariencia\xBB los oculte",opt_show_since_purchase:"Rentabilidad desde la compra",opt_show_since_purchase_help:"Solo con el valor total y su rentabilidad",opt_show_line:"L\xEDnea del valor total",opt_show_wallets:"Wallets",opt_group_wallets:"Wallets en grupos de activos",opt_show_search:"Campo de b\xFAsqueda",opt_show_search_help:"Encuentra wallets por nombre, s\xEDmbolo o ISIN",opt_sort:"Ordenar por",sort_value:"Valor",sort_return:"Rentabilidad desde la compra",sort_name:"Nombre",sort_selection:"Orden de selecci\xF3n",sort_change_desc:"Cambio, mayor primero",sort_change_asc:"Cambio, menor primero",opt_sort_help_tracker:"\xABOrden de selecci\xF3n\xBB solo se aplica con \xABSolo los elegidos\xBB en los activos; si no, por nombre",opt_group_selection:"Grupos de activos mostrados",opt_group_selection_help:"Solo afecta a los wallets; el valor total, el efectivo, Cash Plus y la distribuci\xF3n muestran siempre toda la cartera",opt_groups:"Elegir grupos de activos",opt_asset_selection:"Activos mostrados",opt_asset_selection_wallets:"Wallets mostrados",sel_all:"Todos",sel_all_except:"Todos excepto los elegidos",sel_only:"Solo los elegidos",opt_assets:"Elegir activos",opt_assets_wallets:"Elegir wallets",opt_assets_help:"Un activo de un grupo de activos oculto sigue oculto, aunque se elija aqu\xED",opt_assets_help_wallets:"Un wallet de un grupo de activos oculto sigue oculto, aunque se elija aqu\xED",opt_hide_amounts:"Ocultar inicialmente los importes",opt_hide_amounts_help:"Los porcentajes siguen visibles; el ojo de la tarjeta muestra los importes solo temporalmente",opt_show_header:"Encabezado",opt_show_header_help_portfolio:"T\xEDtulo y ojo; sin \xE9l, el ojo queda junto al valor total, o en una fila propia sin este",opt_show_timeframes:"Botones de periodo",opt_show_timeframes_help_portfolio:"Solo mientras se muestre el valor total o la l\xEDnea; sin ellos, la tarjeta mantiene el periodo elegido arriba",opt_show_timeframes_help:"Sin ellos, la tarjeta mantiene el periodo elegido arriba",opt_show_currencies:"Botones de moneda",opt_show_currencies_help:"Sin ellos, la tarjeta mantiene la moneda elegida arriba",opt_show_lines:"L\xEDneas de precio",opt_show_amounts:"Variaci\xF3n en la moneda del precio",opt_limit:"Activos antes de \xABMostrar todo\xBB",opt_limit_wallets:"Wallets antes de \xABMostrar todo\xBB",opt_limit_help:"0 muestra todos los activos",opt_limit_help_wallets:"Solo si \xABWallets en grupos de activos\xBB est\xE1 desactivado; 0 muestra todo",opt_layout:"Mostrar como",layout_list:"Lista",layout_tiles:"Mosaicos",opt_currency:"Moneda predeterminada",opt_currency_help:"Los botones de la tarjeta la cambian solo temporalmente; m\xE1s monedas con \xABConfigurar\xBB en el Price Tracker"};var Ls={tf_day:"1J",tf_week:"1S",tf_month:"1M",tf_six_month:"6M",tf_year:"1A",aria_timeframe:"P\xE9riode",aria_currency:"Devise",search_placeholder:"Nom, symbole ou ISIN",search_none:"Aucun wallet ne correspond \xE0 \xAB\xA0{query}\xA0\xBB.",aria_search:"Rechercher des wallets",aria_search_clear:"Effacer la recherche",return_day:"rendement sur 1 jour",return_week:"rendement sur 1 semaine",return_month:"rendement sur 1 mois",return_six_month:"rendement sur 6 mois",return_year:"rendement sur 1 an",value_line:"Valeur totale, {start} \u2013 aujourd'hui",value_line_day:"Valeur totale, derni\xE8res 24 heures",line_point:"{value}, {time}",staking_line:"Staking",staking_wallets_one:"dans {count} wallet",staking_wallets_many:"dans {count} wallets",staking_wallets_other:"dans {count} wallets",staking_apr:"APR {apr}",since_purchase:"Depuis l'achat",cash:"Liquidit\xE9s",cash_plus:"Cash Plus",staked:"{share} en staking",show_all:"Tout afficher ({count})",show_less:"Afficher moins",detail_price:"Prix actuel",detail_staked:"En staking",detail_staking_apr:"APR du staking",detail_average_buy_price:"Prix d'achat moyen",detail_invested:"Montant investi",detail_return_24h:"Rendement (24\xA0h)",detail_total_return:"Rendement total",detail_staking:"Staking",detail_earned_30d:"Gagn\xE9 (30 jours)",detail_earned_total:"Gagn\xE9 (total)",detail_payouts:"Versements",detail_payouts_value:"{count} \xB7 dernier le {date}",shares_one:"titre",shares_other:"titres",shares_many:"titres",assets_missing_one:"Cela inclut un actif choisi qui n'existe pas pour le moment. Il reste enregistr\xE9 et s'applique de nouveau d\xE8s qu'il revient.",assets_missing_many:"Cela inclut {count} actifs choisis qui n'existent pas pour le moment. Ils restent enregistr\xE9s et s'appliquent de nouveau d\xE8s qu'ils reviennent.",assets_missing_other:"Cela inclut {count} actifs choisis qui n'existent pas pour le moment. Ils restent enregistr\xE9s et s'appliquent de nouveau d\xE8s qu'ils reviennent.",amount_hidden:"Montant masqu\xE9",allocation_label:"R\xE9partition\xA0: {parts}",eye_hide:"Masquer les montants",eye_show:"Afficher les montants",change_since:"Variation depuis le {date}",ecb_footer:"Prix en {currency}\xA0: prix en EUR de Bitpanda convertis au taux de r\xE9f\xE9rence de la BCE du {date}. Les pourcentages et les montants en {currency} incluent donc aussi la variation du taux de change.",ecb_footer_percent:"Prix en {currency}\xA0: prix en EUR de Bitpanda convertis au taux de r\xE9f\xE9rence de la BCE du {date}. Les pourcentages incluent donc aussi la variation du taux de change.",empty_portfolio:"Configurez le Bitpanda Portfolio ou activez-le pour le voir ici.",empty_wallets:"Aucun wallet pour le moment.",empty_selection_wallets:"Aucun wallet dans la s\xE9lection de cette carte.",empty_selection_assets:"Aucun actif dans la s\xE9lection de cette carte.",empty_price_tracker:"Configurez le Bitpanda Price Tracker ou activez-le et ajoutez-y des actifs pour les voir ici.",picker_portfolio:"Valeur totale et rendement avec courbe, rendement depuis l'achat, liquidit\xE9s et Cash Plus, staking, r\xE9partition et vos wallets\xA0; chaque partie peut \xEAtre masqu\xE9e.",picker_price_tracker:"Prix et variations des actifs que vous suivez, chacun avec sa courbe, en liste ou en tuiles.",invalid_option:"Valeur non valide pour \xAB\xA0{option}\xA0\xBB\xA0: {value}. Valeurs possibles\xA0: {allowed}.",allowed_text:"texte",allowed_assets:"une liste d'ID d'actifs ou d'ID d'appareils",allowed_groups:"une liste d'\xE9l\xE9ments parmi {values}",group_content:"Contenu",group_wallets:"Wallets",group_assets:"Actifs",group_appearance:"Apparence",opt_title:"Titre",opt_title_help:"Laisser vide pour le nom affich\xE9 en gris",opt_timeframe:"P\xE9riode par d\xE9faut",opt_timeframe_help:"Les boutons 1J \xE0 1A de la carte ne la changent que temporairement",tfo_day:"1 jour",tfo_week:"1 semaine",tfo_month:"1 mois",tfo_six_month:"6 mois",tfo_year:"1 an",opt_show_cash:"Liquidit\xE9s et Cash Plus",opt_show_staking:"Staking",opt_show_allocation:"Barre de r\xE9partition",opt_show_allocation_help:"La barre color\xE9e avec la part de chaque groupe d'actifs et des liquidit\xE9s",opt_show_total:"Valeur totale et rendement",opt_show_total_help:"Les boutons de p\xE9riode restent tant que la courbe est affich\xE9e, sauf si \xAB\xA0Apparence\xA0\xBB les masque",opt_show_since_purchase:"Rendement depuis l'achat",opt_show_since_purchase_help:"Uniquement avec la valeur totale et son rendement",opt_show_line:"Courbe de la valeur totale",opt_show_wallets:"Wallets",opt_group_wallets:"Wallets par groupe d'actifs",opt_show_search:"Champ de recherche",opt_show_search_help:"Trouve les wallets par nom, symbole ou ISIN",opt_sort:"Trier par",sort_value:"Valeur",sort_return:"Rendement depuis l'achat",sort_name:"Nom",sort_selection:"Ordre de s\xE9lection",sort_change_desc:"Variation, la plus forte d'abord",sort_change_asc:"Variation, la plus faible d'abord",opt_sort_help_tracker:"\xAB\xA0Ordre de s\xE9lection\xA0\xBB ne s'applique qu'avec \xAB\xA0Seulement ceux choisis\xA0\xBB pour les actifs\xA0; sinon, tri par nom",opt_group_selection:"Groupes d'actifs affich\xE9s",opt_group_selection_help:"S'applique seulement aux wallets\xA0; la valeur totale, les liquidit\xE9s, Cash Plus et la r\xE9partition portent toujours sur l'ensemble du portefeuille",opt_groups:"Choisir les groupes d'actifs",opt_asset_selection:"Actifs affich\xE9s",opt_asset_selection_wallets:"Wallets affich\xE9s",sel_all:"Tous",sel_all_except:"Tous sauf ceux choisis",sel_only:"Seulement ceux choisis",opt_assets:"Choisir les actifs",opt_assets_wallets:"Choisir les wallets",opt_assets_help:"Un actif d'un groupe d'actifs masqu\xE9 reste masqu\xE9, m\xEAme s'il est choisi ici",opt_assets_help_wallets:"Un wallet d'un groupe d'actifs masqu\xE9 reste masqu\xE9, m\xEAme s'il est choisi ici",opt_hide_amounts:"Masquer initialement les montants",opt_hide_amounts_help:"Les pourcentages restent visibles\xA0; l'\u0153il sur la carte n'affiche les montants que temporairement",opt_show_header:"En-t\xEAte",opt_show_header_help_portfolio:"Titre et \u0153il\xA0; sans lui, l'\u0153il se place \xE0 c\xF4t\xE9 de la valeur totale, ou sur une ligne \xE0 part sans celle-ci",opt_show_timeframes:"Boutons de p\xE9riode",opt_show_timeframes_help_portfolio:"Uniquement tant que la valeur totale ou la courbe est affich\xE9e\xA0; sans eux, la carte garde la p\xE9riode choisie plus haut",opt_show_timeframes_help:"Sans eux, la carte garde la p\xE9riode choisie plus haut",opt_show_currencies:"Boutons de devise",opt_show_currencies_help:"Sans eux, la carte garde la devise choisie plus haut",opt_show_lines:"Courbes des prix",opt_show_amounts:"Variation dans la devise du prix",opt_limit:"Actifs avant \xAB\xA0Tout afficher\xA0\xBB",opt_limit_wallets:"Wallets avant \xAB\xA0Tout afficher\xA0\xBB",opt_limit_help:"0 affiche tous les actifs",opt_limit_help_wallets:"Seulement si \xAB\xA0Wallets par groupe d'actifs\xA0\xBB est d\xE9sactiv\xE9\xA0; 0 affiche tout",opt_layout:"Afficher en",layout_list:"Liste",layout_tiles:"Tuiles",opt_currency:"Devise par d\xE9faut",opt_currency_help:"Les boutons de la carte ne la changent que temporairement\xA0; d'autres devises via \xAB\xA0Configurer\xA0\xBB dans le Price Tracker"};var Hs={tf_day:"1G",tf_week:"1S",tf_month:"1M",tf_six_month:"6M",tf_year:"1A",aria_timeframe:"Periodo",aria_currency:"Valuta",search_placeholder:"Nome, simbolo o ISIN",search_none:"Nessun wallet corrisponde a \xAB{query}\xBB.",aria_search:"Cerca nei wallet",aria_search_clear:"Cancella ricerca",return_day:"rendimento su 1 giorno",return_week:"rendimento su 1 settimana",return_month:"rendimento su 1 mese",return_six_month:"rendimento su 6 mesi",return_year:"rendimento su 1 anno",value_line:"Valore totale, {start} \u2013 oggi",value_line_day:"Valore totale, ultime 24 ore",line_point:"{value}, {time}",staking_line:"Staking",staking_wallets_one:"in {count} wallet",staking_wallets_many:"in {count} wallet",staking_wallets_other:"in {count} wallet",staking_apr:"APR {apr}",since_purchase:"Dall'acquisto",cash:"Liquidit\xE0",cash_plus:"Cash Plus",staked:"{share} in staking",show_all:"Mostra tutto ({count})",show_less:"Mostra meno",detail_price:"Prezzo attuale",detail_staked:"In staking",detail_staking_apr:"APR dello staking",detail_average_buy_price:"Prezzo medio di acquisto",detail_invested:"Importo investito",detail_return_24h:"Rendimento (24 h)",detail_total_return:"Rendimento totale",detail_staking:"Staking",detail_earned_30d:"Guadagnato (30 giorni)",detail_earned_total:"Guadagnato (totale)",detail_payouts:"Accrediti",detail_payouts_value:"{count} \xB7 ultimo il {date}",shares_one:"pezzo",shares_other:"pezzi",shares_many:"pezzi",assets_missing_one:"Include un asset scelto che al momento non c'\xE8. Resta salvato e torna a valere appena \xE8 di nuovo disponibile.",assets_missing_many:"Include {count} asset scelti che al momento non ci sono. Restano salvati e tornano a valere appena sono di nuovo disponibili.",assets_missing_other:"Include {count} asset scelti che al momento non ci sono. Restano salvati e tornano a valere appena sono di nuovo disponibili.",amount_hidden:"Importo nascosto",allocation_label:"Ripartizione: {parts}",eye_hide:"Nascondi gli importi",eye_show:"Mostra gli importi",change_since:"Variazione dal {date}",ecb_footer:"Prezzi in {currency}: prezzi in EUR di Bitpanda convertiti al tasso di riferimento BCE del {date}. Le percentuali e gli importi in {currency} includono quindi anche la variazione del tasso di cambio.",ecb_footer_percent:"Prezzi in {currency}: prezzi in EUR di Bitpanda convertiti al tasso di riferimento BCE del {date}. Le percentuali includono quindi anche la variazione del tasso di cambio.",empty_portfolio:"Configura il Bitpanda Portfolio o attivalo per vederlo qui.",empty_wallets:"Ancora nessun wallet.",empty_selection_wallets:"Nessun wallet nella selezione di questa scheda.",empty_selection_assets:"Nessun asset nella selezione di questa scheda.",empty_price_tracker:"Configura il Bitpanda Price Tracker o attivalo e aggiungi degli asset per vederli qui.",picker_portfolio:"Valore totale e rendimento con linea, rendimento dall'acquisto, liquidit\xE0 e Cash Plus, staking, ripartizione e i tuoi wallet; ogni parte si pu\xF2 nascondere.",picker_price_tracker:"Prezzi e variazioni degli asset che segui, ognuno con la sua linea, come elenco o riquadri.",invalid_option:"Valore non valido per \xAB{option}\xBB: {value}. Consentiti: {allowed}.",allowed_text:"testo",allowed_assets:"un elenco di ID asset o ID dispositivo",allowed_groups:"un elenco di valori tra {values}",group_content:"Contenuto",group_wallets:"Wallet",group_assets:"Asset",group_appearance:"Aspetto",opt_title:"Titolo",opt_title_help:"Lascia vuoto per il nome mostrato in grigio",opt_timeframe:"Periodo predefinito",opt_timeframe_help:"I pulsanti da 1G a 1A sulla scheda lo cambiano solo temporaneamente",tfo_day:"1 giorno",tfo_week:"1 settimana",tfo_month:"1 mese",tfo_six_month:"6 mesi",tfo_year:"1 anno",opt_show_cash:"Liquidit\xE0 e Cash Plus",opt_show_staking:"Staking",opt_show_allocation:"Barra di ripartizione",opt_show_allocation_help:"La barra colorata con le quote dei gruppi di asset e della liquidit\xE0",opt_show_total:"Valore totale e rendimento",opt_show_total_help:"I pulsanti del periodo restano finch\xE9 \xE8 mostrata la linea, a meno che \xABAspetto\xBB li nasconda",opt_show_since_purchase:"Rendimento dall'acquisto",opt_show_since_purchase_help:"Solo con il valore totale e il suo rendimento",opt_show_line:"Linea del valore totale",opt_show_wallets:"Wallet",opt_group_wallets:"Wallet in gruppi di asset",opt_show_search:"Campo di ricerca",opt_show_search_help:"Trova i wallet per nome, simbolo o ISIN",opt_sort:"Ordina per",sort_value:"Valore",sort_return:"Rendimento dall'acquisto",sort_name:"Nome",sort_selection:"Ordine di selezione",sort_change_desc:"Variazione, maggiore prima",sort_change_asc:"Variazione, minore prima",opt_sort_help_tracker:"\xABOrdine di selezione\xBB vale solo con \xABSolo quelli scelti\xBB per gli asset; altrimenti per nome",opt_group_selection:"Gruppi di asset mostrati",opt_group_selection_help:"Vale solo per i wallet; valore totale, liquidit\xE0, Cash Plus e ripartizione mostrano sempre l'intero portafoglio",opt_groups:"Scegli i gruppi di asset",opt_asset_selection:"Asset mostrati",opt_asset_selection_wallets:"Wallet mostrati",sel_all:"Tutti",sel_all_except:"Tutti tranne quelli scelti",sel_only:"Solo quelli scelti",opt_assets:"Scegli gli asset",opt_assets_wallets:"Scegli i wallet",opt_assets_help:"Un asset di un gruppo di asset nascosto resta nascosto, anche se scelto qui",opt_assets_help_wallets:"Un wallet di un gruppo di asset nascosto resta nascosto, anche se scelto qui",opt_hide_amounts:"Nascondi inizialmente gli importi",opt_hide_amounts_help:"Le percentuali restano visibili; l'occhio sulla scheda mostra gli importi solo temporaneamente",opt_show_header:"Intestazione",opt_show_header_help_portfolio:"Titolo e occhio; senza, l'occhio sta accanto al valore totale, o su una riga a s\xE9 senza di esso",opt_show_timeframes:"Pulsanti del periodo",opt_show_timeframes_help_portfolio:"Solo finch\xE9 \xE8 mostrato il valore totale o la linea; senza, la scheda mantiene il periodo scelto sopra",opt_show_timeframes_help:"Senza, la scheda mantiene il periodo scelto sopra",opt_show_currencies:"Pulsanti della valuta",opt_show_currencies_help:"Senza, la scheda mantiene la valuta scelta sopra",opt_show_lines:"Linee dei prezzi",opt_show_amounts:"Variazione nella valuta del prezzo",opt_limit:"Asset prima di \xABMostra tutto\xBB",opt_limit_wallets:"Wallet prima di \xABMostra tutto\xBB",opt_limit_help:"0 mostra tutti gli asset",opt_limit_help_wallets:"Solo se \xABWallet in gruppi di asset\xBB \xE8 disattivato; 0 mostra tutto",opt_layout:"Mostra come",layout_list:"Elenco",layout_tiles:"Riquadri",opt_currency:"Valuta predefinita",opt_currency_help:"I pulsanti sulla scheda la cambiano solo temporaneamente; altre valute tramite \xABConfigura\xBB nel Price Tracker"};var Is={tf_day:"1D",tf_week:"1W",tf_month:"1M",tf_six_month:"6M",tf_year:"1J",aria_timeframe:"Periode",aria_currency:"Valuta",search_placeholder:"Naam, symbool of ISIN",search_none:"Geen wallet past bij \u2018{query}\u2019.",aria_search:"Wallets doorzoeken",aria_search_clear:"Zoekopdracht wissen",return_day:"rendement over 1 dag",return_week:"rendement over 1 week",return_month:"rendement over 1 maand",return_six_month:"rendement over 6 maanden",return_year:"rendement over 1 jaar",value_line:"Totale waarde, {start} \u2013 vandaag",value_line_day:"Totale waarde, laatste 24 uur",line_point:"{value}, {time}",staking_line:"Staking",staking_wallets_one:"in {count} wallet",staking_wallets_other:"in {count} wallets",staking_apr:"APR {apr}",since_purchase:"Sinds aankoop",cash:"Contanten",cash_plus:"Cash Plus",staked:"{share} in staking",show_all:"Alles tonen ({count})",show_less:"Minder tonen",detail_price:"Huidige prijs",detail_staked:"In staking",detail_staking_apr:"Staking-APR",detail_average_buy_price:"Gemiddelde aankoopprijs",detail_invested:"Ge\xEFnvesteerd",detail_return_24h:"Rendement (24 uur)",detail_total_return:"Totaalrendement",detail_staking:"Staking",detail_earned_30d:"Verdiend (30 dagen)",detail_earned_total:"Verdiend (totaal)",detail_payouts:"Uitbetalingen",detail_payouts_value:"{count} \xB7 laatste {date}",shares_one:"stuk",shares_other:"stuks",assets_missing_one:"Hieronder valt een gekozen asset die er nu niet is. Die blijft bewaard en geldt weer zodra die terug is.",assets_missing_other:"Hieronder vallen {count} gekozen assets die er nu niet zijn. Ze blijven bewaard en gelden weer zodra ze terug zijn.",amount_hidden:"Bedrag verborgen",allocation_label:"Verdeling: {parts}",eye_hide:"Bedragen verbergen",eye_show:"Bedragen tonen",change_since:"Verandering sinds {date}",ecb_footer:"Prijzen in {currency}: de EUR-prijzen van Bitpanda, omgerekend tegen de ECB-referentiekoers van {date}. De percentages en bedragen in {currency} bevatten daardoor ook de beweging van de wisselkoers.",ecb_footer_percent:"Prijzen in {currency}: de EUR-prijzen van Bitpanda, omgerekend tegen de ECB-referentiekoers van {date}. De percentages bevatten daardoor ook de beweging van de wisselkoers.",empty_portfolio:"Stel het Bitpanda Portfolio in of schakel het in om het hier te zien.",empty_wallets:"Nog geen wallets.",empty_selection_wallets:"Geen wallets in de selectie van deze kaart.",empty_selection_assets:"Geen assets in de selectie van deze kaart.",empty_price_tracker:"Stel de Bitpanda Price Tracker in of schakel hem in en voeg er assets aan toe om ze hier te zien.",picker_portfolio:"Totale waarde en rendement met een lijn, rendement sinds aankoop, contanten en Cash Plus, staking, verdeling en je wallets; elk deel kan worden verborgen.",picker_price_tracker:"Prijzen en veranderingen van de assets die je volgt, elk met een lijn, als lijst of tegels.",invalid_option:"Ongeldige waarde voor \u2018{option}\u2019: {value}. Toegestaan: {allowed}.",allowed_text:"tekst",allowed_assets:"een lijst met asset-ID's of apparaat-ID's",allowed_groups:"een lijst met waarden uit {values}",group_content:"Inhoud",group_wallets:"Wallets",group_assets:"Assets",group_appearance:"Uiterlijk",opt_title:"Titel",opt_title_help:"Leeg laten voor de grijs getoonde naam",opt_timeframe:"Standaardperiode",opt_timeframe_help:"De knoppen 1D tot 1J op de kaart wijzigen die alleen tijdelijk",tfo_day:"1 dag",tfo_week:"1 week",tfo_month:"1 maand",tfo_six_month:"6 maanden",tfo_year:"1 jaar",opt_show_cash:"Contanten en Cash Plus",opt_show_staking:"Staking",opt_show_allocation:"Verdelingsbalk",opt_show_allocation_help:"De gekleurde balk met het aandeel van elke assetgroep en van de contanten",opt_show_total:"Totale waarde en rendement",opt_show_total_help:"De periodeknoppen blijven zolang de lijn wordt getoond, tenzij \u2018Uiterlijk\u2019 ze verbergt",opt_show_since_purchase:"Rendement sinds aankoop",opt_show_since_purchase_help:"Alleen met de totale waarde en het rendement",opt_show_line:"Lijn van de totale waarde",opt_show_wallets:"Wallets",opt_group_wallets:"Wallets in assetgroepen",opt_show_search:"Zoekveld",opt_show_search_help:"Vindt wallets op naam, symbool of ISIN",opt_sort:"Sorteren op",sort_value:"Waarde",sort_return:"Rendement sinds aankoop",sort_name:"Naam",sort_selection:"Volgorde zoals gekozen",sort_change_desc:"Verandering, hoogste eerst",sort_change_asc:"Verandering, laagste eerst",opt_sort_help_tracker:"\u2018Volgorde zoals gekozen\u2019 geldt alleen bij \u2018Alleen de gekozen\u2019 assets, anders op naam",opt_group_selection:"Getoonde assetgroepen",opt_group_selection_help:"Geldt alleen voor de wallets; totale waarde, contanten, Cash Plus en verdeling tonen altijd het hele portfolio",opt_groups:"Assetgroepen kiezen",opt_asset_selection:"Getoonde assets",opt_asset_selection_wallets:"Getoonde wallets",sel_all:"Alle",sel_all_except:"Alle behalve de gekozen",sel_only:"Alleen de gekozen",opt_assets:"Assets kiezen",opt_assets_wallets:"Wallets kiezen",opt_assets_help:"Een asset uit een verborgen assetgroep blijft verborgen, ook als die hier is gekozen",opt_assets_help_wallets:"Een wallet uit een verborgen assetgroep blijft verborgen, ook als die hier is gekozen",opt_hide_amounts:"Bedragen aanvankelijk verbergen",opt_hide_amounts_help:"Percentages blijven zichtbaar; het oog op de kaart toont de bedragen alleen tijdelijk",opt_show_header:"Koptekst",opt_show_header_help_portfolio:"Titel en oog; zonder koptekst staat het oog naast de totale waarde, zonder die op een eigen regel",opt_show_timeframes:"Periodeknoppen",opt_show_timeframes_help_portfolio:"Alleen zolang de totale waarde of de lijn wordt getoond; zonder knoppen houdt de kaart de hierboven gekozen periode",opt_show_timeframes_help:"Zonder knoppen houdt de kaart de hierboven gekozen periode",opt_show_currencies:"Valutaknoppen",opt_show_currencies_help:"Zonder knoppen houdt de kaart de hierboven gekozen valuta",opt_show_lines:"Prijslijnen",opt_show_amounts:"Verandering in de valuta van de prijs",opt_limit:"Assets v\xF3\xF3r \u2018Alles tonen\u2019",opt_limit_wallets:"Wallets v\xF3\xF3r \u2018Alles tonen\u2019",opt_limit_help:"0 toont alle assets",opt_limit_help_wallets:"Alleen als \u2018Wallets in assetgroepen\u2019 uit staat; 0 toont alles",opt_layout:"Weergeven als",layout_list:"Lijst",layout_tiles:"Tegels",opt_currency:"Standaardvaluta",opt_currency_help:"De knoppen op de kaart wijzigen die alleen tijdelijk; meer valuta via \u2018Configureren\u2019 bij de Price Tracker"};var Ns={tf_day:"1D",tf_week:"1T",tf_month:"1M",tf_six_month:"6M",tf_year:"1R",aria_timeframe:"Okres",aria_currency:"Waluta",search_placeholder:"Nazwa, symbol lub ISIN",search_none:"\u017Baden portfel nie pasuje do \u201E{query}\u201D.",aria_search:"Szukaj portfeli",aria_search_clear:"Wyczy\u015B\u0107 wyszukiwanie",return_day:"stopa zwrotu za 1 dzie\u0144",return_week:"stopa zwrotu za 1 tydzie\u0144",return_month:"stopa zwrotu za 1 miesi\u0105c",return_six_month:"stopa zwrotu za 6 miesi\u0119cy",return_year:"stopa zwrotu za 1 rok",value_line:"Warto\u015B\u0107 ca\u0142kowita, {start} \u2013 dzi\u015B",value_line_day:"Warto\u015B\u0107 ca\u0142kowita, ostatnie 24 godziny",line_point:"{value}, {time}",staking_line:"Staking",staking_wallets_one:"w {count} portfelu",staking_wallets_few:"w {count} portfelach",staking_wallets_many:"w {count} portfelach",staking_wallets_other:"w {count} portfela",staking_apr:"APR {apr}",since_purchase:"Od zakupu",cash:"Got\xF3wka",cash_plus:"Cash Plus",staked:"{share} w stakingu",show_all:"Poka\u017C wszystkie ({count})",show_less:"Poka\u017C mniej",detail_price:"Aktualna cena",detail_staked:"W stakingu",detail_staking_apr:"APR stakingu",detail_average_buy_price:"\u015Arednia cena zakupu",detail_invested:"Zainwestowano",detail_return_24h:"Zwrot (24 h)",detail_total_return:"Ca\u0142kowity zwrot",detail_staking:"Staking",detail_earned_30d:"Zarobiono (30 dni)",detail_earned_total:"Zarobiono (\u0142\u0105cznie)",detail_payouts:"Naliczenia",detail_payouts_value:"{count} \xB7 ostatnio {date}",shares_one:"sztuka",shares_other:"sztuki",shares_few:"sztuki",shares_many:"sztuk",assets_missing_one:"Obejmuje to jedno wybrane aktywo, kt\xF3rego teraz nie ma. Pozostaje zapisane i zn\xF3w obowi\u0105zuje, gdy wr\xF3ci.",assets_missing_few:"Obejmuje to {count} wybrane aktywa, kt\xF3rych teraz nie ma. Pozostaj\u0105 zapisane i zn\xF3w obowi\u0105zuj\u0105, gdy wr\xF3c\u0105.",assets_missing_many:"Obejmuje to {count} wybranych aktyw\xF3w, kt\xF3rych teraz nie ma. Pozostaj\u0105 zapisane i zn\xF3w obowi\u0105zuj\u0105, gdy wr\xF3c\u0105.",assets_missing_other:"Obejmuje to {count} wybranego aktywa, kt\xF3rego teraz nie ma. Pozostaje zapisane i zn\xF3w obowi\u0105zuje, gdy wr\xF3ci.",amount_hidden:"Kwota ukryta",allocation_label:"Alokacja: {parts}",eye_hide:"Ukryj kwoty",eye_show:"Poka\u017C kwoty",change_since:"Zmiana od {date}",ecb_footer:"Ceny w {currency}: ceny Bitpandy w EUR przeliczone po kursie referencyjnym EBC z {date}. Warto\u015Bci procentowe i kwoty w {currency} obejmuj\u0105 wi\u0119c r\xF3wnie\u017C zmian\u0119 kursu walutowego.",ecb_footer_percent:"Ceny w {currency}: ceny Bitpandy w EUR przeliczone po kursie referencyjnym EBC z {date}. Warto\u015Bci procentowe obejmuj\u0105 wi\u0119c r\xF3wnie\u017C zmian\u0119 kursu walutowego.",empty_portfolio:"Skonfiguruj Bitpanda Portfolio lub je w\u0142\u0105cz, aby zobaczy\u0107 je tutaj.",empty_wallets:"Brak portfeli.",empty_selection_wallets:"Brak portfeli w wyborze tej karty.",empty_selection_assets:"Brak aktyw\xF3w w wyborze tej karty.",empty_price_tracker:"Skonfiguruj Bitpanda Price Tracker lub go w\u0142\u0105cz i dodaj aktywa, aby zobaczy\u0107 je tutaj.",picker_portfolio:"Warto\u015B\u0107 ca\u0142kowita i stopa zwrotu z wykresem, stopa zwrotu od zakupu, got\xF3wka i Cash Plus, staking, alokacja oraz twoje portfele; ka\u017Cd\u0105 cz\u0119\u015B\u0107 mo\u017Cna ukry\u0107.",picker_price_tracker:"Ceny i zmiany \u015Bledzonych aktyw\xF3w, ka\u017Cde z wykresem, jako lista lub kafelki.",invalid_option:"Nieprawid\u0142owa warto\u015B\u0107 dla \u201E{option}\u201D: {value}. Dozwolone: {allowed}.",allowed_text:"tekst",allowed_assets:"lista identyfikator\xF3w aktyw\xF3w lub urz\u0105dze\u0144",allowed_groups:"lista warto\u015Bci spo\u015Br\xF3d {values}",group_content:"Zawarto\u015B\u0107",group_wallets:"Portfele",group_assets:"Aktywa",group_appearance:"Wygl\u0105d",opt_title:"Tytu\u0142",opt_title_help:"Pozostaw puste, aby u\u017Cy\u0107 nazwy pokazanej na szaro",opt_timeframe:"Domy\u015Blny okres",opt_timeframe_help:"Przyciski od 1D do 1R na karcie zmieniaj\u0105 go tylko tymczasowo",tfo_day:"1 dzie\u0144",tfo_week:"1 tydzie\u0144",tfo_month:"1 miesi\u0105c",tfo_six_month:"6 miesi\u0119cy",tfo_year:"1 rok",opt_show_cash:"Got\xF3wka i Cash Plus",opt_show_staking:"Staking",opt_show_allocation:"Pasek alokacji",opt_show_allocation_help:"Kolorowy pasek pokazuj\u0105cy udzia\u0142 grup aktyw\xF3w i got\xF3wki",opt_show_total:"Warto\u015B\u0107 ca\u0142kowita i stopa zwrotu",opt_show_total_help:"Przyciski okresu pozostaj\u0105, dop\xF3ki wy\u015Bwietlany jest wykres, chyba \u017Ce \u201EWygl\u0105d\u201D je ukrywa",opt_show_since_purchase:"Stopa zwrotu od zakupu",opt_show_since_purchase_help:"Tylko z warto\u015Bci\u0105 ca\u0142kowit\u0105 i jej stop\u0105 zwrotu",opt_show_line:"Wykres warto\u015Bci ca\u0142kowitej",opt_show_wallets:"Portfele",opt_group_wallets:"Portfele w grupach aktyw\xF3w",opt_show_search:"Pole wyszukiwania",opt_show_search_help:"Znajduje portfele po nazwie, symbolu lub ISIN",opt_sort:"Sortuj wed\u0142ug",sort_value:"Warto\u015B\u0107",sort_return:"Stopa zwrotu od zakupu",sort_name:"Nazwa",sort_selection:"Kolejno\u015B\u0107 wyboru",sort_change_desc:"Zmiana, najwy\u017Csza najpierw",sort_change_asc:"Zmiana, najni\u017Csza najpierw",opt_sort_help_tracker:"\u201EKolejno\u015B\u0107 wyboru\u201D dzia\u0142a tylko przy opcji \u201ETylko wybrane\u201D dla aktyw\xF3w; w przeciwnym razie wed\u0142ug nazwy",opt_group_selection:"Wy\u015Bwietlane grupy aktyw\xF3w",opt_group_selection_help:"Dotyczy tylko portfeli; warto\u015B\u0107 ca\u0142kowita, got\xF3wka, Cash Plus i alokacja zawsze pokazuj\u0105 ca\u0142e portfolio",opt_groups:"Wybierz grupy aktyw\xF3w",opt_asset_selection:"Wy\u015Bwietlane aktywa",opt_asset_selection_wallets:"Wy\u015Bwietlane portfele",sel_all:"Wszystkie",sel_all_except:"Wszystkie opr\xF3cz wybranych",sel_only:"Tylko wybrane",opt_assets:"Wybierz aktywa",opt_assets_wallets:"Wybierz portfele",opt_assets_help:"Aktywo z ukrytej grupy aktyw\xF3w pozostaje ukryte, nawet je\u015Bli wybrano je tutaj",opt_assets_help_wallets:"Portfel z ukrytej grupy aktyw\xF3w pozostaje ukryty, nawet je\u015Bli wybrano go tutaj",opt_hide_amounts:"Pocz\u0105tkowo ukrywaj kwoty",opt_hide_amounts_help:"Procenty pozostaj\u0105 widoczne; oko na karcie pokazuje kwoty tylko tymczasowo",opt_show_header:"Nag\u0142\xF3wek",opt_show_header_help_portfolio:"Tytu\u0142 i oko; bez nag\u0142\xF3wka oko stoi obok warto\u015Bci ca\u0142kowitej, a bez niej w osobnym wierszu",opt_show_timeframes:"Przyciski okresu",opt_show_timeframes_help_portfolio:"Tylko gdy wy\u015Bwietlana jest warto\u015B\u0107 ca\u0142kowita lub wykres; bez nich karta zachowuje wybrany wy\u017Cej okres",opt_show_timeframes_help:"Bez nich karta zachowuje wybrany wy\u017Cej okres",opt_show_currencies:"Przyciski waluty",opt_show_currencies_help:"Bez nich karta zachowuje wybran\u0105 wy\u017Cej walut\u0119",opt_show_lines:"Wykresy cen",opt_show_amounts:"Zmiana w walucie ceny",opt_limit:"Aktywa przed \u201EPoka\u017C wszystkie\u201D",opt_limit_wallets:"Portfele przed \u201EPoka\u017C wszystkie\u201D",opt_limit_help:"0 pokazuje wszystkie aktywa",opt_limit_help_wallets:"Tylko gdy opcja \u201EPortfele w grupach aktyw\xF3w\u201D jest wy\u0142\u0105czona; 0 pokazuje wszystkie",opt_layout:"Poka\u017C jako",layout_list:"Lista",layout_tiles:"Kafelki",opt_currency:"Domy\u015Blna waluta",opt_currency_help:"Przyciski na karcie zmieniaj\u0105 j\u0105 tylko tymczasowo; wi\u0119cej walut przez \u201EKonfiguruj\u201D w Price Trackerze"};var Ms={en:Es,de:Rs,fr:Ls,nl:Is,it:Hs,es:zs,pl:Ns},js=n=>n in Ms,Os="en",Jn=n=>{let t=n.toLowerCase().replace(/[-_].*$/,"");return js(t)?t:"en"};function z(n){let t=n??document.querySelector("home-assistant")?.hass;return t?Jn(t.locale.language):Os}function Ws(n){return js(n.locale.language.toLowerCase().replace(/[-_].*$/,""))}function Ge(n){Os=z(n)}var Ds=n=>Ms[z(n)];function m(n,t,e={}){return Ds(n)[t].replace(/\{(\w+)\}/g,(s,o)=>o in e?String(e[o]):s)}function pe(n,t,e,s={}){let o=new Intl.PluralRules(z(n),s).select(e);return Ds(n)[`${t}_${o}`].replace("{count}",String(e))}async function Bs(n){await n.loadBackendTranslation("selector","bitpanda")}function Wt(n,t){return n.localize(`component.bitpanda.selector.asset_group.options.${t}`)||t}var K=["day","week","month","six_month","year"],j=["crypto","stock","etf","etc","index","metal","other"],U=["all","all_except","only"],Us=["EUR","CHF","CZK","DKK","GBP","HUF","NOK","PLN","RON","SEK","TRY","USD"],Ke=["value","return","name"];var Ze=["selection","name","change_desc","change_asc"],Ye=["list","tiles"];var L=n=>({allowed:()=>n.join(", "),check:t=>typeof t=="string"&&n.includes(t)}),S={allowed:()=>"true, false",check:n=>typeof n=="boolean"},Fs={allowed:()=>m(void 0,"allowed_text"),check:n=>typeof n=="string"},Je={allowed:()=>"0, 1, 2, \u2026",check:n=>typeof n=="number"&&Number.isInteger(n)&&n>=0},Xe={allowed:()=>m(void 0,"allowed_assets"),check:n=>Array.isArray(n)&&n.every(t=>typeof t=="string")},Qe={allowed:()=>m(void 0,"allowed_groups",{values:j.join(", ")}),check:n=>Array.isArray(n)&&n.every(t=>j.includes(t))},Vs={allowed:()=>"EUR, USD, \u2026",check:n=>typeof n=="string"&&/^[A-Z]{3}$/.test(n)};function et(n,t){if(n===null||typeof n!="object"||Array.isArray(n))throw new Error(m(void 0,"invalid_option",{option:"type",value:JSON.stringify(n),allowed:"custom:\u2026"}));let e=Object.fromEntries(Object.entries(n).filter(([,s])=>s!==null));for(let[s,o]of Object.entries(t)){let a=e[s];if(a!==void 0&&!o.check(a))throw new Error(m(void 0,"invalid_option",{option:s,value:JSON.stringify(a),allowed:o.allowed()}))}return e}var ue=(n,t)=>({select:{mode:"dropdown",options:n.map(e=>({value:e,label:t(e)}))}}),Dt=n=>({name:"title",default:n,selector:{text:{}}}),Bt=()=>({name:"timeframe",selector:ue(K,n=>m(void 0,`tfo_${n}`))}),T=(n,t)=>({name:n,default:t,selector:{boolean:{}}}),Ut=n=>({name:"limit",default:n,selector:{number:{min:0,max:100,mode:"box"}}}),Ft=n=>({name:"sort",selector:ue(n,t=>m(void 0,`sort_${t}`))});function tt(){return document.querySelector("home-assistant")?.hass}var Xn=3e3;async function qs(n){if(!n)return{};let t;try{let s=(await Promise.race([n.callWS({type:"frontend/get_translations",language:n.language,category:"selector",integration:["bitpanda"]}),new Promise(a=>{t=setTimeout(()=>a(void 0),Xn)})]))?.resources??{},o={};for(let a of j){let i=s[`component.bitpanda.selector.asset_group.options.${a}`];typeof i=="string"&&i&&(o[a]=i)}return o}catch{return{}}finally{clearTimeout(t)}}var st=n=>n==="only"||n==="all_except",Vt=(n,t)=>[{name:"group_selection",selector:ue(U,e=>m(void 0,`sel_${e}`))},...st(t)?[{name:"groups",selector:{select:{multiple:!0,mode:"dropdown",options:j.map(e=>({value:e,label:n[e]??e}))}}}]:[]],qt=(n,t,e)=>[{name:"asset_selection",selector:ue(U,s=>m(void 0,`sel_${s}`))},...st(t)?[e?{name:"assets",selector:{select:{multiple:!0,reorder:!0,mode:"dropdown",options:e}}}:{name:"assets",selector:{device:{multiple:!0,filter:[{integration:"bitpanda",model:n}]}}}]:[]],Se=()=>({type:"divider",name:""}),ne=(n,t)=>({type:"expandable",name:"",flatten:!0,title:m(void 0,n),schema:t}),Qn={title:"opt_title",timeframe:"opt_timeframe",show_total:"opt_show_total",show_since_purchase:"opt_show_since_purchase",show_graph:"opt_show_line",show_cash:"opt_show_cash",show_staking:"opt_show_staking",show_allocation:"opt_show_allocation",show_wallets:"opt_show_wallets",group_wallets:"opt_group_wallets",show_search:"opt_show_search",sort:"opt_sort",group_selection:"opt_group_selection",groups:"opt_groups",asset_selection:"opt_asset_selection",assets:"opt_assets",hide_amounts:"opt_hide_amounts",show_header:"opt_show_header",show_timeframes:"opt_show_timeframes",show_currencies:"opt_show_currencies",show_lines:"opt_show_lines",show_amounts:"opt_show_amounts",limit:"opt_limit",layout:"opt_layout",currency:"opt_currency"},eo={title:"opt_title_help",timeframe:"opt_timeframe_help",show_total:"opt_show_total_help",show_since_purchase:"opt_show_since_purchase_help",show_allocation:"opt_show_allocation_help",hide_amounts:"opt_hide_amounts_help",show_timeframes:"opt_show_timeframes_help",show_currencies:"opt_show_currencies_help",show_search:"opt_show_search_help",assets:"opt_assets_help",limit:"opt_limit_help",currency:"opt_currency_help"};function Gt(n){let t=Qn[n.name];return t?m(void 0,t):void 0}function Kt(n){let t=eo[n.name];return t?m(void 0,t):void 0}var nt=ve`
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
  /* Without the header the content starts where the header would. */
  .content.headless {
    padding-top: 16px;
  }
  /* Without the header: the eye beside the total value, the value wrapping
     or shrinking, the eye never; without the total too, in a row of its own. */
  .hero-row {
    display: flex;
    align-items: flex-start;
    gap: 8px;
  }
  .hero-row .hero {
    flex: 1;
    min-width: 0;
    overflow-wrap: anywhere;
  }
  .hero-row .eye {
    flex: none;
  }
  .eye-row {
    display: flex;
    justify-content: flex-end;
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
  [role="slider"],
  .icon-btn {
    outline: none;
  }
  [role="button"] {
    cursor: pointer;
  }
  [role="button"]:focus-visible,
  [role="radio"]:focus-visible,
  .plot[role="slider"]:focus-visible,
  .icon-btn:focus-visible {
    box-shadow: 0 0 0 2px var(--bp-accent);
    border-radius: 6px;
  }
  .hero {
    font-size: 32px;
    line-height: 40px;
    letter-spacing: -0.5px;
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
  /* The staking line under Cash, and its wallets. */
  .staking {
    margin-top: 10px;
    font-size: 13px;
  }
  .staking svg {
    width: 16px;
    height: 16px;
    fill: currentColor;
    vertical-align: -3px;
    margin-right: 2px;
    color: var(--bp-muted);
  }
  .staking .part {
    white-space: nowrap;
  }
  .staking-list {
    margin: 4px 0 0 18px;
  }
  .staking-row {
    display: flex;
    justify-content: space-between;
    gap: 8px;
    padding: 4px 0;
    font-size: 13px;
  }
  .staking-name {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .staking-value {
    white-space: nowrap;
    color: var(--bp-muted);
  }
  /* The return since purchase: one line, broken only at its middle dot. */
  .since {
    margin-top: 6px;
    font-size: 13px;
    color: var(--bp-muted);
  }
  .since .part {
    white-space: nowrap;
  }
  .since-chip {
    display: inline-flex;
    align-items: center;
    padding: 1px 6px;
    border-radius: 10px;
    font-size: 12px;
    font-weight: 500;
    background: var(--bp-chip);
  }
  .since-amount {
    font-weight: 500;
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
`;var ot={title:Fs,show_header:S,show_timeframes:S},Z=class extends M{constructor(){super(...arguments);this.timeframe="day";this.amountsHidden=!1;this.seriesRevision=0;this.watched=[]}static{this.properties={hass:{attribute:!1},config:{state:!0},timeframe:{state:!0},amountsHidden:{state:!0},seriesRevision:{state:!0}}}static{this.styles=nt}setConfig(e){let s=this.validate(e),o=s;this.config=s,this.timeframe=o.timeframe??"day",this.amountsHidden=o.hide_amounts??!1}toggleAmounts(){this.amountsHidden=!this.amountsHidden}seriesArrived(){this.seriesRevision+=1}selectTimeframe(e){this.timeframe=e}shouldUpdate(e){if(e.size!==1||!e.has("hass"))return!0;let s=e.get("hass"),o=this.hass;return!s||!o||s.entities!==o.entities||s.devices!==o.devices||s.locale!==o.locale||s.localize!==o.localize?!0:this.watched.some(a=>s.states[a]!==o.states[a])}connectedCallback(){super.connectedCallback(),typeof ResizeObserver<"u"&&(this.resizer=new ResizeObserver(()=>this.fitLayout()),this.resizer.observe(this))}disconnectedCallback(){this.resizer?.disconnect(),this.resizer=void 0,super.disconnectedCallback()}updated(e){super.updated(e),this.remeasures(e)&&this.fitLayout()}fitLayout(){}widthMeter(){let e=this.getBoundingClientRect().width,s=e>0&&this.offsetWidth>0?e/this.offsetWidth:1;return(o,a=!1)=>{let i=a?[...o.getClientRects()].reduce((l,r)=>l+r.width,0):o.getBoundingClientRect().width;return Math.round(i/s*100)/100}}remeasures(e){return!0}willUpdate(e){let s=this.hass;if(!s)return;Ge(s);let o=z(s);o!==this.categoryLanguage&&(this.categoryLanguage=o,Bs(s)),this.watched=this.watchedEntities()}getCardSize(){return 3}getGridOptions(){return{columns:12,min_columns:6}}};var to="bitpanda",Gs={return_day:"day",return_week:"week",return_month:"month",return_six_month:"six_month",return_year:"year"},Ks=n=>n.replace(/\s+/g,"").toLowerCase();function so(n,t){let e=(n??"").trim();return e&&Ks(e)!==Ks(t)?`${e} (${t})`:t}var Zs=new WeakMap;function no(n){let t=Zs.get(n.entities);if(t)return t;let e=new Map;for(let s of Object.values(n.entities)){if(!s||s.platform!==to||!s.device_id)continue;let o=e.get(s.device_id)??[];o.push(s),e.set(s.device_id,o)}return Zs.set(n.entities,e),e}function Zt(n,t){let e=no(n),s=[];for(let[o,a]of e){let i=n.devices[o];i?.model===t&&s.push([i,a])}return s}var F=n=>typeof n=="string"&&n!==""?n:void 0,Ys=new Map,Xs=/ (Wallet|Price Tracker)$/;function Te(n,t){return n?Object.values(n.devices).filter(e=>e!==void 0&&e.model===t&&(e.identifiers??[]).some(([s])=>s==="bitpanda")):[]}function Qs(n){return(F(n.name_by_user)??F(n.name)??"").replace(Xs,"")}function en(n,t,e){let s=e.map(i=>n.states[i.entity_id]?.attributes).find(i=>i?.asset),o;if(s){let i=F(s.asset)??"",l=F(s.asset_isin),r=F(s.asset_category),c=F(s.asset_name);o={name:so(c,i),shortName:c??i,symbol:i,...l?{isin:l}:{},...r&&j.includes(r)?{category:r}:{}},Ys.set(t.id,o)}else{let i=(F(t.name)??"").replace(Xs,"");o=Ys.get(t.id)??{name:i,shortName:i,symbol:""}}let a=F(t.name_by_user);return{deviceId:t.id,assetId:t.serial_number??"",...o,...a?{name:a,shortName:a}:{}}}function at(n){let[t]=Zt(n,"Portfolio");if(!t)return;let[e,s]=t,o={deviceId:e.id,returns:{},wallets:[]};for(let a of s){let i=a.translation_key??"";i==="total_value"?o.totalValue=a.entity_id:i==="cash"?o.cash=a.entity_id:i==="cash_plus"?o.cashPlus=a.entity_id:i==="invested"?o.invested=a.entity_id:i==="total_return"?o.totalReturn=a.entity_id:i==="total_return_percent"?o.totalReturnPercent=a.entity_id:i in Gs&&(o.returns[Gs[i]]=a.entity_id)}for(let[a,i]of Zt(n,"Wallet")){let l=en(n,a,i);for(let r of i)r.translation_key==="wallet"?l.available=r.entity_id:r.translation_key==="wallet_total"?l.total=r.entity_id:r.translation_key==="staking"&&(l.staking=r.entity_id);o.wallets.push(l)}return o}function he(n){return Zt(n,"Price Tracker").map(([t,e])=>{let s={};for(let o of e){if(o.translation_key!=="price")continue;let a=F(n.states[o.entity_id]?.attributes.unit_of_measurement);a&&(s[a]=o.entity_id)}return{...en(n,t,e),prices:s}})}function Ce(n){let t=new Set(n.flatMap(s=>Object.keys(s.prices))),e=[...t].filter(s=>s!=="EUR").sort();return t.has("EUR")?["EUR",...e]:e}function it(n,t,e){if(t==="all")return[...n];let s=t==="only";return n.filter(o=>e.includes(o.category??"other")===s)}var Js=(n,t)=>t===n.deviceId||t!==""&&t===n.assetId;function rt(n,t,e){if(t==="all_except")return n.filter(s=>!e.some(o=>Js(s,o)));if(t==="only"){let s=[];for(let o of e){let a=n.find(i=>Js(i,o));a&&!s.includes(a)&&s.push(a)}return s}return[...n]}var ct="bitpanda-portfolio-card-editor",dt="bitpanda-price-tracker-card-editor",oo=[["asset_selection","assets"],["group_selection","groups"]],ao={timeframe:"day",sort:"value",group_selection:"all",asset_selection:"all"},io={layout:"list",timeframe:"day",currency:"EUR",sort:"name",group_selection:"all",asset_selection:"all"},ro=/^[0-9a-f]{32}$/,lt=n=>n.serial_number||n.id;function lo(n,t){return n?/[.!?…]$/.test(n)?`${n} ${t}`:`${n}. ${t}`:t}async function co(n=customElements,t=window,e=1e4){if(n.get("ha-form"))return;try{await(await(await t.loadCardHelpers?.())?.createCardElement({type:"entities",entities:[]}))?.constructor?.getConfigElement?.()}catch{}let s;await Promise.race([n.whenDefined("ha-form"),new Promise(o=>{s=setTimeout(o,e)})]),clearTimeout(s)}async function ut(n){return await co(),customElements.get(ct)||customElements.define(ct,Yt),customElements.get(dt)||customElements.define(dt,Jt),document.createElement(n)}var pt=class extends M{constructor(){super(...arguments);this.names={};this.namesAsked=!1;this.heldBack={}}static{this.properties={hass:{attribute:!1},config:{state:!0},names:{state:!0}}}setConfig(e){this.config=e}reorders(){return!1}chosenAssets(){let e=this.config?.assets,s=Te(this.hass,this.model),o=[],a=[],i=[];for(let l of Array.isArray(e)?e:[]){let r=s.find(c=>c.id===l||c.serial_number&&c.serial_number===l);r?o.includes(r.id)||(o.push(r.id),a.push(lt(r))):!ro.test(l)&&!i.includes(l)&&i.push(l)}return{devices:o,values:a,missing:i}}savedAssets(e){let s=Te(this.hass,this.model),o=[];for(let a of[...e.map(i=>s.find(l=>l.id===i)?.serial_number||i),...this.chosenAssets().missing])o.includes(a)||o.push(a);return o}orderedAssets(e){let s=this.config?.assets,o=Te(this.hass,this.model),{missing:a}=this.chosenAssets(),i=[...new Set(e)],l=new Set,r=0;for(let c of Array.isArray(s)?s:[]){if(a.includes(c)){if(i.includes(c))continue;i.splice(Math.min(l.size+r,i.length),0,c),r+=1;continue}let p=o.find(h=>h.id===c||h.serial_number&&h.serial_number===c);p&&i.includes(lt(p))&&l.add(lt(p))}return i}willUpdate(e){super.willUpdate(e),this.hass&&(Ge(this.hass),this.namesAsked||(this.namesAsked=!0,qs(this.hass).then(s=>{this.names=s})))}render(){if(!this.config)return u;let e=this.form(),{devices:s,values:o,missing:a}=this.chosenAssets(),i={...this.defaults,...this.config};"assets"in i&&(i.assets=this.reorders()?o:s);let l=a.length===0?e.computeHelper:r=>r.name==="assets"?lo(e.computeHelper(r),pe(void 0,"assets_missing",a.length)):e.computeHelper(r);return d`<ha-form
      .hass=${this.hass}
      .data=${i}
      .schema=${e.schema}
      .computeLabel=${e.computeLabel}
      .computeHelper=${l}
      @value-changed=${this.changed}
    ></ha-form>`}changed(e){e.stopPropagation();let s=this.config??{},o=e.detail.value,a=o.assets,i=Array.isArray(o.assets)?{...o,assets:this.reorders()?this.orderedAssets(a):this.savedAssets(a)}:o,l=Object.fromEntries(Object.entries(i).filter(([r,c])=>r in s||this.defaults[r]===void 0||c!==this.defaults[r]));for(let[r,c]of oo)st(l[r])?!(c in l)&&c in this.heldBack&&(l[c]=this.heldBack[c]):(c in l&&(this.heldBack[c]=l[c]),delete l[c]);this.config=l,this.dispatchEvent(new CustomEvent("config-changed",{detail:{config:l},bubbles:!0,composed:!0}))}},po={limit:"opt_limit_wallets",asset_selection:"opt_asset_selection_wallets",assets:"opt_assets_wallets"},uo={show_header:"opt_show_header_help_portfolio",show_timeframes:"opt_show_timeframes_help_portfolio",limit:"opt_limit_help_wallets",group_selection:"opt_group_selection_help",assets:"opt_assets_help_wallets"},Yt=class extends pt{constructor(){super(...arguments);this.defaults=ao;this.model="Wallet"}form(){let e=this.config??{};return{schema:[Dt("Bitpanda Portfolio"),ne("group_content",[T("show_total",!0),T("show_since_purchase",!0),T("show_graph",!0),T("show_cash",!0),T("show_staking",!0),T("show_allocation",!0),T("show_wallets",!0)]),ne("group_wallets",[T("show_search",!1),T("group_wallets",!0),Ft(Ke),Ut(5),Se(),...Vt(this.names,e.group_selection??"all"),Se(),...qt("Wallet",e.asset_selection??"all")]),ne("group_appearance",[T("show_header",!0),Bt(),T("show_timeframes",!0),T("hide_amounts",!1)])],computeLabel:s=>{let o=po[s.name];return o?m(void 0,o):Gt(s)},computeHelper:s=>{let o=uo[s.name];return o?m(void 0,o):Kt(s)}}}};function ho(n){let t=n?Ce(he(n)):[];return t.length>0?t:Us}var Jt=class extends pt{constructor(){super(...arguments);this.defaults=io;this.model="Price Tracker"}reorders(){return this.config?.asset_selection==="only"&&this.config.sort==="selection"}assetOptions(){return Te(this.hass,this.model).map(e=>({value:lt(e),label:Qs(e)})).sort((e,s)=>e.label.localeCompare(s.label,z(this.hass)))}form(){let e=this.config??{};return{schema:[Dt("Bitpanda Price Tracker"),ne("group_content",[T("show_lines",!0),T("show_amounts",!0)]),ne("group_assets",[Ft(Ze),Ut(0),Se(),...Vt(this.names,e.group_selection??"all"),Se(),...qt("Price Tracker",e.asset_selection??"all",this.reorders()?this.assetOptions():void 0)]),ne("group_appearance",[{name:"layout",selector:ue(Ye,s=>m(void 0,`layout_${s}`))},T("show_header",!0),Bt(),T("show_timeframes",!0),{name:"currency",selector:{select:{mode:"dropdown",options:ho(this.hass).map(s=>({value:s,label:s}))}}},T("show_currencies",!0)])],computeLabel:Gt,computeHelper:s=>s.name==="sort"?m(void 0,"opt_sort_help_tracker"):Kt(s)}}};function ht(n){switch(n.locale.number_format){case"comma_decimal":return"en-US";case"decimal_comma":return"de";case"space_comma":return"fr";case"quote_decimal":return"de-CH";case"system":return;default:return n.locale.language}}function Qt(n,t,e,s=0){return new Intl.NumberFormat(ht(n),{maximumFractionDigits:e,minimumFractionDigits:s,useGrouping:n.locale.number_format!=="none"}).format(t)}function sn(n){return{...n!==0&&Math.abs(n)<1e-4?{maximumSignificantDigits:2}:{maximumFractionDigits:4},roundingMode:"trunc"}}function mo(n,t){return new Intl.NumberFormat(ht(n),{...sn(t),useGrouping:n.locale.number_format!=="none"}).format(t)}var tn=8;function Pe(n,t,e,s,o=!1){let a=o?mo(n,t):Qt(n,t,tn);if(e==="stock"||e==="etf"||e==="etc"){let i=o?sn(t):{maximumFractionDigits:tn};return`${a} ${pe(n,"shares",t,i)}`}return`${a} ${e==="metal"?"g":s}`}var mt=new Set(["unavailable","unknown"]);function H(n,t){let e=t?n.states[t]:void 0;return e&&!mt.has(e.state)?n.formatEntityState(e):void 0}function nn(n,t,e){let s=t?n.states[t]:void 0;return s&&e!==void 0?n.formatEntityState({...s,state:String(e)}):void 0}function oe(n,t,e,s=!1){return es(n,t,e,2,s)}function on(n,t,e){let s=Math.abs(t);return es(n,t,e,s>=10||s===0?2:s>=1?4:8,!1)}function an(n,t,e){return es(n,t,e,rn(t),!1)}function es(n,t,e,s,o){try{return new Intl.NumberFormat(ht(n),{style:"currency",currency:e,minimumFractionDigits:2,maximumFractionDigits:s,useGrouping:n.locale.number_format!=="none",...o?{signDisplay:"exceptZero"}:{}}).format(t)}catch{return`${Qt(n,t,s)} ${e}`}}function rn(n){let t=Math.abs(n);return t===0||t>=10?2:t>=1?4:t>=.1?5:t>=.001?6:t>=1e-4?7:8}function ln(n,t,e){let s=t?n.states[t]:void 0;if(!s||mt.has(s.state)||e===void 0||!Number.isFinite(e))return;let o=n.entities[s.entity_id]?.display_precision,a=typeof o=="number"?o:rn(Number(s.state)),i=Number(e.toFixed(a))===0?0 .toFixed(a):e.toFixed(a),l=n.formatEntityState({...s,state:i});return Number(i)>0?`+${l}`:l}function x(n,t){if(!n||mt.has(n.state))return;let e=n.attributes[t];return typeof e=="number"&&Number.isFinite(e)?e:void 0}function C(n,t){let e=t?n.states[t]:void 0;if(!e||mt.has(e.state)||e.state.trim()==="")return;let s=Number(e.state);return Number.isFinite(s)?s:void 0}var _o=new Set(["cs","de","fi","fr","sk","sv"]),cn=n=>_o.has(n.locale.language)?"\xA0":"";function R(n,t){if(t===void 0||!Number.isFinite(t))return{text:"\u2014",direction:"none"};let e=new Intl.NumberFormat(ht(n),{minimumFractionDigits:2,maximumFractionDigits:2,signDisplay:"exceptZero",useGrouping:n.locale.number_format!=="none"}).format(t),s=cn(n),a=Math.round(Math.abs(t)*100)===0?"flat":t>0?"up":"down";return{text:`${e}${s}%`,direction:a}}function ae(n,t,e,s=!1){let o=cn(n);return`${Qt(n,t,e,s?e:0)}${o}%`}function P(n){return n==="up"||n==="down"?n:""}function V(n){return n==="up"?"\u25B2":n==="down"?"\u25BC":""}function ts(n){return Ws(n)?n.locale.language:"en"}function dn(n){return n.locale.time_zone==="server"?n.config?.time_zone:void 0}function fo(n){let t=n.locale.time_format;return t==="12"||t==="24"?t==="12":new Date("January 1, 2023 22:00:00").toLocaleString(t==="system"?void 0:n.locale.language).includes("10")}function Re(n,t){let e=dn(n),s=a=>new Intl.DateTimeFormat("en",{year:"numeric",timeZone:e}).format(a),o=s(t)===s(Date.now())?{}:{year:"numeric"};return new Intl.DateTimeFormat(ts(n),{day:"numeric",month:"short",...o,timeZone:e}).format(t)}function pn(n,t){let e=/^(\d{4})-(\d{2})-(\d{2})$/.exec(t);if(!e)return;let s=Date.UTC(Number(e[1]),Number(e[2])-1,Number(e[3]));return new Intl.DateTimeFormat(ts(n),{day:"numeric",month:"long",timeZone:"UTC"}).format(s)}function _t(n,t){let e=fo(n);return new Intl.DateTimeFormat(ts(n),{day:"numeric",month:"short",hour:e?"numeric":"2-digit",minute:"2-digit",hourCycle:e?"h12":"h23",timeZone:dn(n)}).format(t)}var{I:ri}=Cs;var un=n=>n.strings===void 0;var hn={ATTRIBUTE:1,CHILD:2,PROPERTY:3,BOOLEAN_ATTRIBUTE:4,EVENT:5,ELEMENT:6},ss=n=>(...t)=>({_$litDirective$:n,values:t}),ft=class{constructor(t){}get _$AU(){return this._$AM._$AU}_$AT(t,e,s){this._$Ct=t,this._$AM=e,this._$Ci=s}_$AS(t,e){return this.update(t,e)}update(t,e){return this.render(...e)}};var Ee=(n,t)=>{let e=n._$AN;if(e===void 0)return!1;for(let s of e)s._$AO?.(t,!1),Ee(s,t);return!0},gt=n=>{let t,e;do{if((t=n._$AM)===void 0)break;e=t._$AN,e.delete(n),n=t}while(e?.size===0)},mn=n=>{for(let t;t=n._$AM;n=t){let e=t._$AN;if(e===void 0)t._$AN=e=new Set;else if(e.has(n))break;e.add(n),yo(t)}};function go(n){this._$AN!==void 0?(gt(this),this._$AM=n,mn(this)):this._$AM=n}function wo(n,t=!1,e=0){let s=this._$AH,o=this._$AN;if(o!==void 0&&o.size!==0)if(t)if(Array.isArray(s))for(let a=e;a<s.length;a++)Ee(s[a],!1),gt(s[a]);else s!=null&&(Ee(s,!1),gt(s));else Ee(this,n)}var yo=n=>{n.type==hn.CHILD&&(n._$AP??=wo,n._$AQ??=go)},wt=class extends ft{constructor(){super(...arguments),this._$AN=void 0}_$AT(t,e,s){super._$AT(t,e,s),mn(this),this.isConnected=t._$AU}_$AO(t,e=!0){t!==this.isConnected&&(this.isConnected=t,t?this.reconnected?.():this.disconnected?.()),e&&(Ee(this,t),gt(this))}setValue(t){if(un(this._$Ct))this._$Ct._$AI(t,this);else{let e=[...this._$Ct._$AH];e[this._$Ci]=t,this._$Ct._$AI(e,this,0)}}disconnected(){}reconnected(){}};var _n=()=>new os,os=class{},ns=new WeakMap,fn=ss(class extends wt{render(n){return u}update(n,[t]){let e=t!==this.G;return e&&this.rt(void 0),(e||this.lt!==this.ct)&&(this.G=t,this.ht=n.options?.host,this.rt(this.ct=n.element)),u}rt(n){if(this.G!==void 0)if(this.isConnected||(n=void 0),typeof this.G=="function"){let t=this.ht??globalThis,e=ns.get(t);e===void 0&&(e=new WeakMap,ns.set(t,e)),e.get(this.G)!==void 0&&this.G.call(this.ht,void 0),e.set(this.G,n),n!==void 0&&this.G.call(this.ht,n)}else this.G.value=n}get lt(){return typeof this.G=="function"?ns.get(this.ht??globalThis)?.get(this.G):this.G?.value}disconnected(){this.lt===this.ct&&this.rt(void 0)}reconnected(){this.rt(this.ct)}});var vo="M12,9A3,3 0 0,0 9,12A3,3 0 0,0 12,15A3,3 0 0,0 15,12A3,3 0 0,0 12,9M12,17A5,5 0 0,1 7,12A5,5 0 0,1 12,7A5,5 0 0,1 17,12A5,5 0 0,1 12,17M12,4.5C7,4.5 2.73,7.61 1,12C2.73,16.39 7,19.5 12,19.5C17,19.5 21.27,16.39 23,12C21.27,7.61 17,4.5 12,4.5Z",bo="M11.83,9L15,12.16C15,12.11 15,12.05 15,12A3,3 0 0,0 12,9C11.94,9 11.89,9 11.83,9M7.53,9.8L9.08,11.35C9.03,11.56 9,11.77 9,12A3,3 0 0,0 12,15C12.22,15 12.44,14.97 12.65,14.92L14.2,16.47C13.53,16.8 12.79,17 12,17A5,5 0 0,1 7,12C7,11.21 7.2,10.47 7.53,9.8M2,4.27L4.28,6.55L4.73,7C3.08,8.3 1.78,10 1,12C2.73,16.39 7,19.5 12,19.5C13.55,19.5 15.03,19.2 16.38,18.66L16.81,19.08L19.73,22L21,20.73L3.27,3M12,7A5,5 0 0,1 17,12C17,12.64 16.87,13.26 16.64,13.82L19.57,16.75C21.07,15.5 22.27,13.86 23,12C21.27,7.61 17,4.5 12,4.5C10.6,4.5 9.26,4.75 8,5.2L10.17,7.35C10.74,7.13 11.35,7 12,7Z",wn="M7.41,8.58L12,13.17L16.59,8.58L18,10L12,16L6,10L7.41,8.58Z",yn="M7.41,15.41L12,10.83L16.59,15.41L18,14L12,8L6,14L7.41,15.41Z",ko="M8.59,16.58L13.17,12L8.59,7.41L10,6L16,12L10,18L8.59,16.58Z",xo="M9.5,3A6.5,6.5 0 0,1 16,9.5C16,11.11 15.41,12.59 14.44,13.73L14.71,14H15.5L20.5,19L19,20.5L14,15.5V14.71L13.73,14.44C12.59,15.41 11.11,16 9.5,16A6.5,6.5 0 0,1 3,9.5A6.5,6.5 0 0,1 9.5,3M9.5,5C7,5 5,7 5,9.5C5,12 7,14 9.5,14C12,14 14,12 14,9.5C14,7 12,5 9.5,5Z",$o="M19,6.41L17.59,5L12,10.59L6.41,5L5,6.41L10.59,12L5,17.59L6.41,19L12,13.41L17.59,19L19,17.59L13.41,12L19,6.41Z",ie=n=>de`<svg viewBox="0 0 24 24" aria-hidden="true"><path d=${n}></path></svg>`,ze={down:wn,up:yn,right:ko};function re(n){return t=>{(t.key==="Enter"||t.key===" ")&&(t.preventDefault(),n())}}function Ao(n,t){n.dispatchEvent(new CustomEvent("hass-more-info",{bubbles:!0,composed:!0,detail:{entityId:t}}))}function O(n,t){return t?()=>Ao(n,t):void 0}function me(n,t){let e=n.filter(s=>s.second!==void 0);return e.length>0&&e.every(s=>s.first+t+s.second<=s.room)}var So="\u2022\u2022\u2022\u2022\u2022\u2022";function A(n,t,e){return e?d`<span class="amount blur" role="img" aria-label=${m(n,"amount_hidden")}>${So}</span>`:d`<span class="amount">${t??"\u2014"}</span>`}function I(n){return n?{role:"button",tabindex:"0",click:n,keydown:re(n)}:{role:u,tabindex:u,click:u,keydown:u}}function vn(n,t,e){let[s,...o]=n.split(`{${t}}`);return o.length===0?d`${n}`:d`${s}<span class="nw">${e}</span>${o.join(`{${t}}`)}`}function le(n){return d`<div class="empty">${n}</div>`}function Le(n,t){return d`<button
    class="icon-btn eye"
    aria-label=${m(n,t.hidden?"eye_show":"eye_hide")}
    title=${m(n,t.hidden?"eye_show":"eye_hide")}
    @click=${t.toggle}
  >
    ${ie(t.hidden?bo:vo)}
  </button>`}function He(n,t,e){return d`<div class="head">
    <div class="title">${t}</div>
    ${e?Le(n,e):u}
  </div>`}function bn(n,t,e,s,o){let{text:a,direction:i}=R(n,t),l=V(i),r=I(s);return d`<div class="hero-line">
    <span class="chip ${P(i)}" role=${r.role} tabindex=${r.tabindex} @click=${r.click} @keydown=${r.keydown}
      >${l?`${l} `:""}${a}</span
    >
    ${i!=="none"&&o?.text?d`<span class="chip-amount ${P(i)}">${A(n,o.text,o.hidden)}</span>`:u}
    <span class="chip-label">${m(n,`return_${e}`)}</span>
  </div>`}function kn(n,t,e,s,o){return d`<div class="seg" role="radiogroup" aria-label=${n} @keydown=${i=>{let l=i.key==="ArrowRight"||i.key==="ArrowDown"?1:i.key==="ArrowLeft"||i.key==="ArrowUp"?-1:0;if(l===0)return;i.preventDefault();let r=(t.indexOf(e)+l+t.length)%t.length;o(t[r]),i.currentTarget.querySelectorAll("[role=radio]")[r]?.focus()}}>
    ${t.map(i=>d`<span
          role="radio"
          aria-checked=${i===e?"true":"false"}
          tabindex=${i===e?0:-1}
          @click=${()=>o(i)}
          @keydown=${re(()=>o(i))}
          >${s(i)}</span
        >`)}
  </div>`}function yt(n,t,e){return kn(m(n,"aria_timeframe"),K,t,s=>m(n,`tf_${s}`),e)}function xn(n,t,e,s){return t.length<2?null:kn(m(n,"aria_currency"),t,e,o=>o,s)}function $n(n,t,e){let s=_n(),o=()=>{e(""),s.value?.focus()};return d`<div class="search" role="search">
    ${ie(xo)}<input
      ${fn(s)}
      type="text"
      .value=${t}
      placeholder=${m(n,"search_placeholder")}
      aria-label=${m(n,"aria_search")}
      autocomplete="off"
      spellcheck="false"
      @input=${a=>e(a.target.value)}
    />${t?d`<span class="clear" role="button" tabindex="0" aria-label=${m(n,"aria_search_clear")} @click=${o} @keydown=${re(o)}
          >${ie($o)}</span
        >`:u}
  </div>`}var To={\u00DF:"ss",\u00F8:"o",\u00E6:"ae",\u0153:"oe",\u0142:"l",\u0111:"d",\u00F0:"d",\u00FE:"th",\u0131:"i"};function gn(n){return n.normalize("NFD").replace(/\p{M}/gu,"").toLowerCase().replace(/[ßøæœłđðþı]/gu,t=>To[t]??t).replace(/[^\p{L}\p{N}\s]/gu,"")}function An(n,t){let e=gn(t).split(/\s+/).filter(Boolean),s=gn(`${n.name} ${n.symbol} ${n.isin??""}`);return e.length>0&&e.every(o=>s.includes(o))}function Sn(n){let{hass:t,wallet:e,hidden:s,onTap:o,chevron:a}=n,i=e.total?t.states[e.total]:void 0,l=x(i,"units"),r=C(t,e.total),c=C(t,e.staking),p=r&&c&&c>0?c/r*100:void 0,{text:h,direction:_}=R(t,x(i,"total_return_percent")),f=V(_),y=_==="none"?d`<span class="wchip none">—</span>`:d`<span class="wchip ${P(_)}">${f?`${f} `:""}${h}</span>`,g=p===void 0?u:d`<div class="stake"><span class="badge">${m(t,"staked",{share:ae(t,p,0)})}</span></div>`,w=$=>{$.stopPropagation(),a?.toggle()},k=I(s?void 0:o);return d`<div class="wallet">
    <div class="tap" role=${k.role} tabindex=${k.tabindex} @click=${k.click} @keydown=${k.keydown}>
      <div class="main">
        <div class="n" title=${e.shortName}>${e.shortName}</div>
        <div class="sub ${p===void 0?"":"staked"}">
          <div class="s">
            <span class="units"
              >${A(t,l===void 0?void 0:Pe(t,l,e.category,e.symbol,!0),s)}</span
            >${e.isin?d` · <span class="isin">${e.isin}</span>`:u}
          </div>
          ${g}
        </div>
      </div>
      <div class="right">${y}<span class="val">${A(t,H(t,e.total),s)}</span></div>
    </div>
    ${a?d`<span
          class="chevron"
          role="button"
          tabindex="0"
          aria-expanded=${a.open?"true":"false"}
          @click=${w}
          @keydown=${$=>{$.stopPropagation(),re(a.toggle)($)}}
          >${ie(a.open?yn:wn)}</span
        >`:u}
  </div>`}function vt(n,t,e){let s=i=>C(n,i.total)??Number.NEGATIVE_INFINITY,o=i=>x(i.total?n.states[i.total]:void 0,"total_return_percent")??Number.NEGATIVE_INFINITY,a=(i,l)=>i.name.localeCompare(l.name,z(n));return[...t].sort((i,l)=>e==="name"?a(i,l):(e==="value"?s(l)-s(i):o(l)-o(i))||a(i,l))}var Co=window.customElements,Po=1e4;function Ro(n=()=>window.customElements,t=Co,e=Po){let s=Date.now();return new Promise(o=>{let a=()=>{let i=n();i!==t||i.get("home-assistant")||Date.now()-s>=e?o(i):setTimeout(a,50)};a()})}var Eo="https://github.com/Spegeli/hacs_bitpanda#-dashboard-cards";function zo(n,t,e,s,o={}){let a=n.entities[t];return!a||a.platform!=="bitpanda"||!a.device_id?null:(typeof e=="string"?[e]:e).includes(n.devices[a.device_id]?.model??"")?{config:{type:`custom:${s}`,...o}}:null}function bt(n,t,e){Ro().then(a=>{a.get(n)||a.define(n,t)});let s=window;if(s.customCards??=[],s.customCards.some(a=>a.type===n))return;let{model:o}=e;s.customCards.push({type:n,name:e.name,get description(){return e.description()},preview:!0,documentationURL:Eo,...o?{getEntitySuggestion:(a,i)=>zo(a,i,o,n,t.getStubConfig?.())}:{}})}var Lo={day:[864e5,"5minute"],week:[6048e5,"hour"],month:[2592e6,"hour"],six_month:[157248e5,"day"],year:[31536e6,"day"]};function kt(n){return n==="5minute"?5*6e4:n==="hour"?36e5:864e5}function Tn(n){return n.timeframe==="month"?(n.end-n.start)/120:0}function fe(n,t){let[e,s]=Lo[n];return{timeframe:n,start:t-e,end:t,period:s}}var Ho=n=>typeof n=="number"?n:Date.parse(n);async function Io(n,t,e){if(t.length===0)return{};let s;try{s=await n.callWS({type:"recorder/statistics_during_period",start_time:new Date(e.start).toISOString(),end_time:new Date(e.end).toISOString(),statistic_ids:[...t],period:e.period,types:["state"]})}catch{return}let o={};for(let[a,i]of Object.entries(s))o[a]=i.map(l=>({t:Ho(l.start),v:l.state})).filter(l=>typeof l.v=="number"&&Number.isFinite(l.t)).sort((l,r)=>l.t-r.t);return o}var xt="portfolio";async function Cn(n,t,e){let s;try{s=await n.callWS({type:"bitpanda/portfolio_history",timeframe:e.timeframe})}catch{return}let a=(Array.isArray(s?.points)?s.points:[]).filter(i=>Array.isArray(i)&&typeof i[0]=="number"&&typeof i[1]=="number"&&Number.isFinite(i[0])&&Number.isFinite(i[1])).map(([i,l])=>({t:i,v:l})).sort((i,l)=>i.t-l.t);return{[xt]:a}}var _e=class{constructor(t,e=Io){this.onUpdate=t;this.fetch=e;this.key="";this.end=0;this.latest=0;this.current={}}request(t,e,s,o=""){let a=`${s.timeframe}|${[...e].sort().join(",")}|${o}`;if(a===this.key&&s.end-this.end<kt(s.period))return;s.timeframe!==this.timeframe&&(this.current={}),this.key=a,this.timeframe=s.timeframe,this.end=s.end;let i=++this.latest;this.fetch(t,e,s).then(l=>{if(i===this.latest){if(l===void 0){this.key="";return}this.current=l,this.onUpdate()}})}series(t){return this.current[t]}};function Pn(n,t,e){let s=kt(e.period),o=n.find(a=>a.t>=e.start-s);if(!(t===void 0||o===void 0||o.v===0))return{change:(t-o.v)/o.v*100,amount:t-o.v,...o.t>e.start+s?{since:o.t}:{}}}var Rn=2,as=n=>Math.round(n*100)/100;function is(n,t,e,s){return as(e===t?s/2:s-Rn-(n-t)/(e-t)*(s-2*Rn))}function En(n,t){let e=0;return n.forEach((s,o)=>{Math.abs(s.t-t)<Math.abs(n[e].t-t)&&(e=o)}),e}function No(n,t){if(t<=0||n.length<3)return n;let e=o=>Math.floor(o.t/t),s=[];for(let o of n.slice(0,-1)){let a=s[s.length-1];(!a||e(o)!==e(a))&&s.push(o)}return s.push(n[n.length-1]),s}function zn(n,t,e,s,o,a=0){let i=o??1.5*kt(t.period),l=[],r;for(let w of n)(!r||w.t-r.t>i)&&l.push([]),l[l.length-1]?.push(w),r=w;let c=l.map(w=>No(w,a)),p=c.flat().map(w=>w.v),h=Math.min(...p),_=Math.max(...p),f=t.end-t.start,y=w=>as((w-t.start)/f*e),g=w=>is(w,h,_,s);return c.map(w=>w.map(k=>[y(k.t),g(k.v)]))}function Mo(n,t,e,s,o,a=0){return zn(n,t,e,s,o,a).map(i=>i.length===1?`M${i[0]?.[0]},${i[0]?.[1]}l0.01,0`:i.map(([l,r],c)=>`${c===0?"M":"L"}${l},${r}`).join("")).join("")}function jo(n,t,e,s,o,a=0){return zn(n,t,e,s,o,a).map(i=>{let l=i[0],r=i[i.length-1];return`M${l[0]},${s}${i.map(([c,p])=>`L${c},${p}`).join("")}L${r[0]},${s}Z`}).join("")}var rs=(n,t)=>n.length>0&&n[n.length-1].t-n[0].t>=(t.end-t.start)/10;function $t(n,t,e){let{width:s,height:o,fill:a,className:i,gapMs:l,stepMs:r}=e;return rs(n,t)?de`<svg class=${i} viewBox="0 0 ${s} ${o}" preserveAspectRatio="none" aria-hidden="true">${a?de`<path class="area" d=${jo(n,t,s,o,l,r)}></path>`:null}<path class="line" d=${Mo(n,t,s,o,l,r)} vector-effect="non-scaling-stroke"></path></svg>`:de`<svg class=${i} viewBox="0 0 ${s} ${o}" preserveAspectRatio="none" aria-hidden="true"></svg>`}var Oo=480,ls=72,At=n=>`${(n*100).toFixed(2)}%`;function Wo(n,t,e,s){let{hass:o,refs:a,window:i,hidden:l,cursor:r,onCursor:c}=n,p=t.length-1,h=r===void 0?void 0:Math.min(r,p),_=t.map(v=>v.v),f=Math.min(..._),y=Math.max(..._),g=i.end-i.start,w=v=>{let G=v.currentTarget.getBoundingClientRect(),Pt=Math.min(Math.max((v.clientX-G.left)/G.width,0),1);return En(t,i.start+Pt*g)},k=v=>c(w(v)),$=()=>c(void 0),q=v=>{v.pointerType!=="mouse"&&$()},ge=a.totalValue?o.states[a.totalValue]?.attributes.unit_of_measurement:void 0,E=typeof ge=="string"&&!l?v=>oe(o,v,ge):void 0,Y=v=>i.timeframe==="day"||i.timeframe==="week"?_t(o,v):Re(o,v),W=h===void 0?void 0:t[h],Ne=u;if(W){let v=(W.t-i.start)/g,G=Y(W.t),Pt=v<.25?"start":v>.75?"end":"";Ne=d`${E?d`<span class="tag high">${E(y)}</span><span class="tag middle">${E((y+f)/2)}</span
            ><span class="tag low">${E(f)}</span>`:u}
      <div class="cursor" style="left:${At(v)}"></div>
      <div class="dot" style="left:${At(v)};top:${At(is(W.v,f,y,ls)/ls)}"></div>
      <div class="tip ${Pt}" style="left:${At(v)}">${E?`${G} \xB7 ${E(W.v)}`:G}</div>`}let we=$t(t,i,{width:Oo,height:ls,fill:!0,className:`spark ${e}`,gapMs:Number.POSITIVE_INFINITY});if(!rs(t,i))return d`<div class="plot">${we}</div>`;let Me=v=>{let G=v.key==="ArrowLeft"?Math.max(0,(h??p)-1):v.key==="ArrowRight"?h===void 0?p:Math.min(p,h+1):v.key==="Home"?0:v.key==="End"?p:void 0;G!==void 0?(v.preventDefault(),c(G)):v.key==="Escape"&&$()},b=t[h??p],N=E?m(o,"line_point",{value:E(b.v),time:Y(b.t)}):Y(b.t);return d`<div
    class="plot"
    role="slider"
    tabindex="0"
    aria-label=${s}
    aria-valuemin="0"
    aria-valuemax=${p}
    aria-valuenow=${h??p}
    aria-valuetext=${N}
    @keydown=${Me}
    @blur=${$}
    @pointerdown=${k}
    @pointermove=${k}
    @pointerup=${q}
    @pointercancel=${$}
    @pointerleave=${$}
  >
    ${we}
    <div class="mid"></div>
    ${Ne}
  </div>`}function Do(n,t,e){if(t.timeframe==="day")return m(n,"value_line_day");let s=e[0]?.t??t.start;return m(n,"value_line",{start:Re(n,Math.max(t.start,s))})}function St(n,t){for(let e of[t.totalValue,t.invested,...t.wallets.map(s=>s.total)]){let s=e?n.states[e]?.attributes.unit_of_measurement:void 0;if(typeof s=="string"&&s)return s}}function Bo(n,t,e){let s=t.returns[e],o=x(s?n.states[s]:void 0,"return_amount"),a=St(n,t);return o===void 0||a===void 0?void 0:oe(n,o,a,!0)}function Uo(n){let{host:t,hass:e,refs:s,hidden:o}=n;if(!s.totalReturn&&!s.totalReturnPercent)return u;let{text:a,direction:i}=R(e,C(e,s.totalReturnPercent)),l=V(i),r=P(i),c=St(e,s),p=C(e,s.totalReturn),h=p===void 0||c===void 0?void 0:oe(e,p,c,!0),_=(y,g,w,k)=>{let $=I(k&&o?void 0:O(t,g));return d`<span class=${y} role=${$.role} tabindex=${$.tabindex} @click=${$.click} @keydown=${$.keydown}
      >${w}</span
    >`},f=i==="none"?_("since-chip none",s.totalReturnPercent,"\u2014",!1):_(`since-chip ${r}`,s.totalReturnPercent,`${l?`${l} `:""}${a}`,!1);return d`<div class="since">
    <span class="part since-label">${m(e,"since_purchase")}</span>
    <span class="part">${f} ${_(`since-amount ${r}`,s.totalReturn,A(e,h,o),!0)}</span>
  </div>`}function Ln(n){let{host:t,hass:e,refs:s,timeframe:o,hidden:a,window:i,points:l}=n,r=C(e,s.returns[o]),c=P(R(e,r).direction)||"flat",p=g=>a?void 0:O(t,g),h=I(p(s.totalValue)),_=d`<div class="hero" role=${h.role} tabindex=${h.tabindex} @click=${h.click} @keydown=${h.keydown}>
    ${A(e,H(e,s.totalValue),a)}
  </div>`,f=n.line&&l!==void 0&&l.length>0,y=f?Do(e,i,l):"";return d`${n.total?d`${n.eye?d`<div class="hero-row">${_}${Le(e,n.eye)}</div>`:_}
          ${bn(e,r,o,p(s.returns[o]),{text:Bo(e,s,o),hidden:a})}
          ${n.since?Uo(n):u}`:u}
    ${n.timeframes&&(n.total||n.line)?yt(e,o,n.onTimeframe):u}
    ${f?d`${Wo(n,l,c,y)}
          <div class="caption">${y}</div>`:u}`}var Fo="bitpanda-portfolio-card",Hn={crypto:"var(--blue-color, #4269d0)",stock:"var(--indigo-color, #3f51b5)",etf:"var(--amber-color, #efb118)",etc:"var(--cyan-color, #00bcd4)",index:"var(--purple-color, #a463f2)",metal:"var(--green-color, #3ca951)",other:"var(--pink-color, #ff8ab7)",cash_plus:"var(--deep-orange-color, #ff725c)",cash:"var(--teal-color, #6cc5b0)"},In=n=>n.category??"other";function Nn(n,t){return t<1?`<${ae(n,1,0)}`:ae(n,t,2,!0)}var Vo=(n,t)=>rt(it(n.wallets,t.group_selection??"all",t.groups??[]),t.asset_selection??"all",t.assets??[]);function qo(n,t){let e=0,s=0;for(let o of t){let a=C(n,o.total),i=x(o.total?n.states[o.total]:void 0,"invested_amount");if(a===void 0||i===void 0)return;e+=a,s+=i}return s>0?(e-s)/s*100:void 0}function Mn(n){let t=n.map(s=>({room:s.room,first:s.left,second:Math.max(s.chip??0,s.value)}));if(n.length===0||me(t,Go))return"beside";let e=n.flatMap(s=>s.chip===void 0?[]:[{room:s.below??s.room,first:s.chip,second:s.value}]);return e.length===0||me(e,Ko)?"row":"stacked"}function Tt(n){if(!n.some(t=>t===void 0))return Math.round(n.reduce((t,e)=>t+e,0)*1e8)/1e8}var Ie="\xA0\xB7 ";function jn(n,t){let e=[],s=!1;for(let o of t.wallets){if(!o.staking)continue;let a=C(n,o.staking);a===void 0?s=!0:a>0&&e.push({wallet:o,value:a})}return e.sort((o,a)=>a.value-o.value),{counted:e,unknown:s}}var Go=12,Ko=8,Zo=30,Yo=8,cs=class extends Z{constructor(){super(...arguments);this.openGroups=new Set;this.stakingOpen=!1;this.showAll=!1;this.query="";this.cursor=void 0;this.stakeInline=!1;this.groupsLayout="beside";this.rowsLayout="beside";this.openWallets=new Set;this.window=fe("day",Date.now());this.lines=new _e(()=>this.seriesArrived(),Cn)}static{this.properties={...Z.properties,openGroups:{state:!0},openWallets:{state:!0},stakingOpen:{state:!0},showAll:{state:!0},query:{state:!0},cursor:{state:!0},stakeInline:{state:!0},groupsLayout:{state:!0},rowsLayout:{state:!0}}}static async getConfigElement(){return ut(ct)}static getStubConfig(){return{timeframe:"day",sort:"value",group_selection:"all",asset_selection:"all"}}validate(e){return et(e,{...ot,timeframe:L(K),show_total:S,show_since_purchase:S,show_graph:S,show_cash:S,show_staking:S,show_allocation:S,show_wallets:S,group_wallets:S,show_search:S,sort:L(Ke),limit:Je,group_selection:L(U),groups:Qe,asset_selection:L(U),assets:Xe,hide_amounts:S})}watchedEntities(){let e=this.hass?at(this.hass):void 0;return e?[e.totalValue,e.cash,e.cashPlus,e.invested,e.totalReturn,e.totalReturnPercent,...Object.values(e.returns),...e.wallets.flatMap(s=>[s.available,s.total,s.staking])].filter(s=>s!==void 0):[]}willUpdate(e){super.willUpdate(e);let s=this.hass?at(this.hass):void 0;this.window=fe(this.timeframe,Date.now());let o=this.hass?.states[s?.returns[this.timeframe]??""]?.state??"";this.hass&&s&&this.config?.show_graph!==!1&&this.lines.request(this.hass,[xt],this.window,o)}getCardSize(){return this.config?.show_header===!1?7:8}remeasures(e){return!(e.size===1&&e.has("cursor"))}fitLayout(){let e=_=>[...this.renderRoot.querySelectorAll(_)],s=(_,f)=>_.querySelector(f),o=this.widthMeter(),a=_=>_?o(_):void 0,i=e(".wallet .sub").map(_=>{let f=a(_.querySelector(".stake .badge"));return{room:_.clientWidth,first:o(s(_,".s")),...f===void 0?{}:{second:f}}}),l=me(i,Yo);l!==this.stakeInline&&(this.stakeInline=l);let r=e(".group").map(_=>{let f=a(_.querySelector(".gchip"));return{room:_.clientWidth,left:o(s(_,".gleft")),...f===void 0?{}:{chip:f},value:o(s(_,".sum"))}}),c=Mn(r);c!==this.groupsLayout&&(this.groupsLayout=c);let p=e(".wallet .tap").map(_=>({room:_.clientWidth,below:_.clientWidth+Zo,left:o(s(_,".s .units"),!0),chip:o(s(_,".wchip")),value:o(s(_,".val"))})),h=Mn(p);h!==this.rowsLayout&&(this.rowsLayout=h)}groupChip(e,s){let{text:o,direction:a}=R(e,qo(e,s));if(a==="none")return d`<span class="gchip none">—</span>`;let i=V(a);return d`<span class="gchip ${P(a)}">${i?`${i} `:""}${o}</span>`}walletsClass(){return["wallets",this.stakeInline?"stake-inline":"",this.groupsLayout==="beside"?"":"groups-wrapped",this.groupsLayout==="stacked"?"groups-stacked":"",this.rowsLayout==="beside"?"":"rows-wrapped",this.rowsLayout==="stacked"?"rows-stacked":""].filter(Boolean).join(" ")}toggle(e,s){let o=new Set(e);return o.has(s)?o.delete(s):o.add(s),o}render(){let e=this.hass,s=this.config;if(!e||!s)return u;let o=at(e),a={hidden:this.amountsHidden,toggle:()=>this.toggleAmounts()},i=s.title||"Bitpanda Portfolio",l=s.show_header!==!1;if(!o)return d`<ha-card>${l?He(e,i):u}${le(m(e,"empty_portfolio"))}</ha-card>`;let r=s.show_total!==!1||s.show_graph!==!1,c=s.show_staking!==!1&&jn(e,o).counted.length>0,p=s.show_cash!==!1||c||s.show_allocation!==!1,h=Vo(o,s);return d`<ha-card>
      ${l?He(e,i,a):u}
      <div class="content ${l?"":"headless"}">
        ${!l&&s.show_total===!1?d`<div class="eye-row">${Le(e,a)}</div>`:u}
        ${Ln({host:this,hass:e,refs:o,timeframe:this.timeframe,hidden:this.amountsHidden,window:this.window,points:this.lines.series(xt),total:s.show_total!==!1,since:s.show_since_purchase!==!1,line:s.show_graph!==!1,timeframes:s.show_timeframes!==!1,eye:l?void 0:a,onTimeframe:_=>{this.cursor=void 0,this.selectTimeframe(_)},cursor:this.cursor,onCursor:_=>{_!==this.cursor&&(this.cursor=_)}})}
        ${p?d`${r?d`<div class="divider"></div>`:u}
              ${s.show_cash===!1?u:this.renderCash(e,o)}
              ${c?this.renderStaking(e,o):u}
              ${s.show_allocation===!1?u:this.renderAllocation(e,o)}`:u}
        ${s.show_wallets===!1?u:d`${r||p?d`<div class="divider"></div>`:u}${s.show_search&&h.length>0?$n(e,this.query,_=>this.query=_):u}${this.renderWallets(e,o,h,s)}`}
      </div>
    </ha-card>`}renderCash(e,s){let o=(a,i,l)=>{let r=I(this.amountsHidden?void 0:O(this,i));return d`<div class=${l?"end":""} role=${r.role} tabindex=${r.tabindex} @click=${r.click} @keydown=${r.keydown}>
        <span class="k">${a}</span><span class="v">${A(e,H(e,i),this.amountsHidden)}</span>
      </div>`};return d`<div class="pair">${o(m(e,"cash"),s.cash,!1)}${o(m(e,"cash_plus"),s.cashPlus,!0)}</div>`}renderStaking(e,s){let o=this.amountsHidden,{counted:a,unknown:i}=jn(e,s),l=g=>g.staking?e.states[g.staking]:void 0,r=a[0]?l(a[0].wallet)?.attributes.unit_of_measurement:void 0,c=typeof r=="string"&&r?r:St(e,s),p=i?void 0:Tt(a.map(g=>g.value)),h=p===void 0||c===void 0?void 0:oe(e,p,c),_=i?m(e,"staking_wallets_other").replace("{count}","\u2014"):pe(e,"staking_wallets",a.length),f=this.stakingOpen,y=()=>{this.stakingOpen=!this.stakingOpen};return d`<div class="staking" role="button" tabindex="0" aria-expanded=${f?"true":"false"} @click=${y} @keydown=${re(y)}>
        ${ie(f?ze.down:ze.right)}<span class="part"><span class="k">${m(e,"staking_line")}</span></span>${Ie}<span class="part"
          >${A(e,h,o)} ${_}</span
        >
      </div>
      ${f?d`<div class="staking-list">
            ${a.map(({wallet:g})=>{let w=x(l(g),"apr_percent"),k=I(o?void 0:O(this,g.staking));return d`<div class="staking-row" role=${k.role} tabindex=${k.tabindex} @click=${k.click} @keydown=${k.keydown}>
                <span class="staking-name">${g.shortName}</span>
                <span class="staking-value">${A(e,H(e,g.staking),o)}${w===void 0?u:d`${Ie}${m(e,"staking_apr",{apr:ae(e,w,1)})}`}</span>
              </div>`})}
          </div>`:u}`}renderAllocation(e,s){let o=[];for(let r of j){let c=s.wallets.filter(p=>In(p)===r);c.length>0&&o.push({key:r,label:Wt(e,r),value:Tt(c.map(p=>C(e,p.total)))})}s.cashPlus&&o.push({key:"cash_plus",label:m(e,"cash_plus"),value:C(e,s.cashPlus)}),s.cash&&o.push({key:"cash",label:m(e,"cash"),value:C(e,s.cash)});let a=Tt(o.map(r=>r.value));if(a===void 0)return d`<div class="allocation-missing muted">—</div>`;let i=o.map(r=>({...r,share:a>0?r.value/a*100:0})).filter(r=>r.share>0).sort((r,c)=>c.share-r.share),l=m(e,"allocation_label",{parts:i.map(r=>`${r.label} ${Nn(e,r.share)}`).join(", ")});return d`<div class="bar" role="img" aria-label=${l}>
        ${i.map(r=>d`<span style="width:${r.share}%;background:${Hn[r.key]}"></span>`)}
      </div>
      <div class="legend" aria-hidden="true">
        ${i.map(r=>d`<span><i style="background:${Hn[r.key]}"></i>${r.label} ${Nn(e,r.share)}</span>`)}
      </div>`}renderWallets(e,s,o,a){if(s.wallets.length===0)return le(m(e,"empty_wallets"));if(o.length===0)return le(m(e,"empty_selection_wallets"));let i=a.sort??"value",l=a.show_search?this.query.trim():"";if(l){let r=vt(e,o.filter(c=>An(c,l)),i);return r.length>0?d`<div class=${this.walletsClass()}>${r.map(c=>this.renderWallet(e,s,c))}</div>`:d`<div class="search-none">${m(e,"search_none",{query:l})}</div>`}if(a.group_wallets===!1){let r=vt(e,o,i),c=a.limit??5,p=c>0&&r.length>c,h=p&&!this.showAll?r.slice(0,c):r;return d`<div class=${this.walletsClass()}>${h.map(_=>this.renderWallet(e,s,_))}</div>
        ${p?d`<button class="show-all" @click=${()=>this.showAll=!this.showAll}>
              ${this.showAll?m(e,"show_less"):m(e,"show_all",{count:r.length})}
            </button>`:u}`}return d`<div class=${this.walletsClass()}>${j.map(r=>{let c=o.filter(f=>In(f)===r);if(c.length===0)return u;let p=Tt(c.map(f=>C(e,f.total))),h=this.openGroups.has(r),_=()=>{this.openGroups=this.toggle(this.openGroups,r)};return d`<div class="group" role="button" tabindex="0" aria-expanded=${h?"true":"false"} @click=${_} @keydown=${re(_)}>
          <span class="gleft"
            >${ie(h?ze.down:ze.right)}<span class="name">${Wt(e,r)}</span
            ><span class="count">${c.length}</span></span
          >
          <span class="gright">${this.groupChip(e,c)}<span class="sum">${A(e,nn(e,c[0]?.total,p),this.amountsHidden)}</span></span>
        </div>
        ${h?d`<div class="members">${vt(e,c,i).map(f=>this.renderWallet(e,s,f))}</div>`:u}`})}</div>`}renderWallet(e,s,o){let a=this.openWallets.has(o.deviceId);return d`${Sn({hass:e,wallet:o,hidden:this.amountsHidden,onTap:O(this,o.total),chevron:{open:a,toggle:()=>{this.openWallets=this.toggle(this.openWallets,o.deviceId)}}})}${a?this.renderDetail(e,s,o):u}`}renderDetail(e,s,o){let a=this.amountsHidden,i=b=>b?e.states[b]?.attributes.unit_of_measurement:void 0,l=String(i(o.total)??i(s.totalValue)??"EUR"),r=o.total?e.states[o.total]:void 0,c=o.staking?e.states[o.staking]:void 0,p=b=>{let N=x(b?e.states[b]:void 0,"units");return N===void 0?void 0:Pe(e,N,o.category,o.symbol)},h=(b,N=!1)=>b===void 0?void 0:oe(e,b,l,N),_=b=>b===void 0?void 0:on(e,b,l),f=b=>d`<span class="part">${b}</span>`,y=b=>d`${f(A(e,p(b),a))}${Ie}${f(A(e,H(e,b),a))}`,g=x(r,"total_return"),w=R(e,x(r,"total_return_percent")),k=x(r,"price"),$=x(r,"return_24h"),q=x(r,"change_24h_pct"),ge=R(e,q),E=x(c,"apr_percent"),Y=x(c,"rewards_count"),W=c?.attributes.rewards_last_at,Ne=typeof W=="string"&&Number.isFinite(Date.parse(W))?_t(e,Date.parse(W)):"\u2014",we=x(c,"rewards_net_30d"),Me=(b,N)=>d`${f(A(e,b===void 0?void 0:Pe(e,b,o.category,o.symbol),a))}${Ie}${f(A(e,h(N),a))}`;return d`<div class="detail">
      <div class="grid">
        <span>${m(e,"detail_price")}</span><span>${k===void 0?"\u2014":an(e,k,l)}</span>
        <span>${m(e,"detail_average_buy_price")}</span><span>${A(e,_(x(r,"average_buy_price")),a)}</span>
        <span>${m(e,"detail_invested")}</span><span>${A(e,h(x(r,"invested_amount")),a)}</span>
        ${$!==void 0&&q!==void 0?d`<span>${m(e,"detail_return_24h")}</span
              ><span class=${P(ge.direction)}>${f(A(e,h($,!0),a))} ${f(`(${ge.text})`)}</span>`:u}
        <span>${m(e,"detail_total_return")}</span
        ><span class=${P(w.direction)}>${f(A(e,h(g,!0),a))} ${f(`(${w.text})`)}</span>
      </div>
      ${o.staking?d`<h4>${m(e,"detail_staking")}</h4>
            <div class="grid">
              <span>${m(e,"detail_staked")}</span><span>${y(o.staking)}</span>
              ${E!==void 0?d`<span>${m(e,"detail_staking_apr")}</span><span>${ae(e,E,1)}</span>`:u}
              ${Y!==void 0&&Y>0?d`${we===void 0?u:d`<span>${m(e,"detail_earned_30d")}</span
                          ><span>${Me(we,x(c,"rewards_net_value_30d"))}</span>`}
                    <span>${m(e,"detail_earned_total")}</span
                    ><span>${Me(x(c,"rewards_net"),x(c,"rewards_net_value"))}</span>
                    <span>${m(e,"detail_payouts")}</span
                    ><span
                      >${m(e,"detail_payouts_value",{count:Y,date:Ne}).split(" \xB7 ").map((b,N)=>d`${N>0?Ie:""}${f(b)}`)}</span
                    >`:u}
            </div>`:u}
    </div>`}};bt(Fo,cs,{name:"Bitpanda Portfolio",description:()=>m(tt(),"picker_portfolio"),model:["Portfolio","Wallet"]});var Jo=ve`
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
  /* Without lines: no line column. */
  .rows.no-lines .price-row {
    grid-template-columns: minmax(0, 1fr) var(--bp-price, auto) var(--bp-change, minmax(78px, auto));
    grid-template-areas: "lead price change";
  }
  .rows.no-lines.stacked .price-row {
    grid-template-columns: minmax(0, 1fr) var(--bp-figures, auto);
    grid-template-areas:
      "lead price"
      "lead change";
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
    .rows.no-lines .price-row {
      grid-template-columns: minmax(0, 1fr) auto auto;
    }
    .rows.no-lines.stacked .price-row {
      grid-template-columns: minmax(0, 1fr) auto;
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
`,Xo=6,Qo=120,ea=90,Ct=8,ta=78,sa=96,na=380;function On(n){let t=Math.ceil(Math.max(0,...n.map(s=>s.price))),e=Math.ceil(Math.max(0,...n.map(s=>s.change)));return{price:t,change:Math.max(ta,e),figures:Math.max(t,e)}}function oa(n){let t=On(n);return n.every(e=>e.room-t.price-Ct-t.change-Ct>=Qo)?"beside":n.every(e=>e.room-t.figures-Ct>=ea)?"stacked":"below"}function aa(n){return me(n.map(t=>({room:t.room,first:t.pct,...t.amount===void 0?{}:{second:t.amount}})),Xo)}var ds=class extends Z{constructor(){super(...arguments);this.showAll=!1;this.amountsInline=!1;this.rowsLayout="beside";this.columns=void 0;this.window=fe("day",Date.now());this.lines=new _e(()=>this.seriesArrived())}static{this.properties={...Z.properties,currency:{state:!0},showAll:{state:!0},amountsInline:{state:!0},rowsLayout:{state:!0},columns:{state:!0}}}static{this.styles=[nt,Jo]}static async getConfigElement(){return ut(dt)}static getStubConfig(){return{layout:"list",timeframe:"day",currency:"EUR",sort:"name",group_selection:"all",asset_selection:"all"}}setConfig(e){super.setConfig(e),this.currency=void 0}validate(e){return et(e,{...ot,layout:L(Ye),timeframe:L(K),currency:Vs,sort:L(Ze),group_selection:L(U),groups:Qe,asset_selection:L(U),assets:Xe,limit:Je,show_currencies:S,show_lines:S,show_amounts:S})}watchedEntities(){return this.hass?he(this.hass).flatMap(e=>Object.values(e.prices)):[]}shownCurrency(e){let s=Ce(e),o=this.currency??this.config?.currency??"EUR";return s.includes(o)?o:s.includes("EUR")?"EUR":s[0]??"EUR"}visible(e,s){let o=he(e),a=this.shownCurrency(o),i=it(o,s.group_selection??"all",s.groups??[]),r=rt(i,s.asset_selection??"all",s.assets??[]).map(y=>{let g=y.prices[a],w=g?e.states[g]:void 0,k=g?this.lines.series(g):void 0,$=C(e,g),q=Pn(k??[],$,this.window);return{asset:y,entityId:g,change:q?.change,amount:q?.amount,points:k,since:q?.since}}),c=s.sort??"name",p=(y,g)=>y.asset.name.localeCompare(g.asset.name,z(e));if(c==="name"||c==="selection"&&s.asset_selection!=="only")r.sort(p);else if(c==="change_desc"||c==="change_asc"){let y=c==="change_desc"?-1:1;r.sort((g,w)=>g.change===void 0||w.change===void 0?g.change===void 0?w.change===void 0?p(g,w):1:-1:y*(g.change-w.change)||p(g,w))}let h=s.limit??0,_=h>0&&r.length>h;return{rows:_&&!this.showAll?r.slice(0,h):r,ranked:r,total:r.length,folds:_,currency:a,currencies:Ce(o)}}willUpdate(e){if(super.willUpdate(e),this.window=fe(this.timeframe,Date.now()),!this.hass||!this.config)return;let{rows:s,ranked:o}=this.visible(this.hass,this.config),a=this.config.sort??"name",l=(a==="change_desc"||a==="change_asc"?o:s).map(r=>r.entityId).filter(r=>r!==void 0);this.lines.request(this.hass,l,this.window)}fitLayout(){let e=this.widthMeter(),s=c=>c?e(c):void 0,o=[...this.shadowRoot?.querySelectorAll(".tile .c")??[]].map(c=>{let p=s(c.querySelector(".a"));return{room:c.clientWidth,pct:s(c.querySelector(".pct"))??0,...p===void 0?{}:{amount:p}}}),a=aa(o);a!==this.amountsInline&&(this.amountsInline=a);let i=this.config?.show_lines!==!1&&this.clientWidth>na?sa+Ct:0,l=[...this.renderRoot.querySelectorAll(".price-row")].map(c=>{let p=h=>e(c.querySelector(h));return{room:c.clientWidth-i,price:p(".p"),change:Math.max(p(".c .pct"),s(c.querySelector(".c .a"))??0)}}),r=oa(l);if(r!==this.rowsLayout&&(this.rowsLayout=r),l.length>0){let c=On(l),p=this.columns;(!p||p.price!==c.price||p.change!==c.change||p.figures!==c.figures)&&(this.columns=c)}}getCardSize(){return this.config?.show_header===!1?5:6}line(e,s){if(this.config?.show_lines===!1)return u;let o=e.since===void 0?this.window:{...this.window,start:e.since};return e.points&&e.points.length>0?$t(e.points,o,{width:96,height:28,fill:!1,className:`mini ${s}`,stepMs:Tn(o)}):d`<span class="mini"></span>`}change(e,s){let{text:o,direction:a}=R(e,s.change),i=V(a),l=P(a),r=a==="none"||this.config?.show_amounts===!1?void 0:ln(e,s.entityId,s.amount);return{cell:d`<div class="pct pchip ${a==="none"?"none":""}">${a==="none"?"\u2014":`${i?`${i} `:""}${o}`}</div>${r?d`<div class="a">${r}</div>`:u}`,className:l,lineClass:l||"flat"}}since(e,s){return s.since===void 0?u:d`<div class="since">${vn(m(e,"change_since"),"date",Re(e,s.since))}</div>`}renderList(e,s){let o=this.columns,a=o?`--bp-price:${o.price}px;--bp-change:${o.change}px;--bp-figures:${o.figures}px`:"",i=[this.rowsLayout==="beside"?"":this.rowsLayout,this.config?.show_lines===!1?"no-lines":""].filter(Boolean).join(" ");return d`<div class="rows ${i}" style=${a}>
      ${s.map(l=>{let r=this.change(e,l),c=I(O(this,l.entityId));return d`<div class="price-row" role=${c.role} tabindex=${c.tabindex} @click=${c.click} @keydown=${c.keydown}>
          <div class="lead"><div class="n" title=${l.asset.shortName}>${l.asset.shortName}</div><div class="s">${l.asset.isin??l.asset.symbol}</div>${this.since(e,l)}</div>
          ${this.line(l,r.lineClass)}
          <div class="p">${H(e,l.entityId)??"\u2014"}</div>
          <div class="c ${r.className}">${r.cell}</div>
        </div>`})}
    </div>`}renderTiles(e,s){return d`<div class="tiles ${this.amountsInline?"inline":""}">
      ${s.map(o=>{let a=this.change(e,o),i=I(O(this,o.entityId));return d`<div class="tile" role=${i.role} tabindex=${i.tabindex} @click=${i.click} @keydown=${i.keydown}>
          <div class="n" title=${o.asset.shortName}>${o.asset.shortName}</div>
          <div class="s">${o.asset.isin??o.asset.symbol}</div>
          <div class="p">${H(e,o.entityId)??"\u2014"}</div>
          <div class="c ${a.className}">${a.cell}</div>
          ${this.line(o,a.lineClass)}${this.since(e,o)}
        </div>`})}
    </div>`}footer(e,s,o){if(o==="EUR")return u;let a=s.map(l=>l.entityId?e.states[l.entityId]?.attributes.rate_date:void 0).map(l=>typeof l=="string"?pn(e,l):void 0).find(l=>l!==void 0),i=this.config?.show_amounts===!1?"ecb_footer_percent":"ecb_footer";return a?d`<div class="foot">${m(e,i,{currency:o,date:a})}</div>`:u}render(){let e=this.hass,s=this.config;if(!e||!s)return u;let o=s.show_header!==!1,a=o?He(e,s.title||"Bitpanda Price Tracker"):u;if(he(e).length===0)return d`<ha-card>${a}${le(m(e,"empty_price_tracker"))}</ha-card>`;let{rows:i,total:l,folds:r,currency:c,currencies:p}=this.visible(e,s),h=s.show_timeframes!==!1,_=s.show_currencies!==!1;return d`<ha-card>
      ${a}
      <div class="content ${o?"":"headless"}">
        ${h||_?d`<div class="switches">
              ${h?yt(e,this.timeframe,f=>this.selectTimeframe(f)):u}
              ${_?xn(e,p,c,f=>this.currency=f):u}
            </div>`:u}
        ${i.length===0?le(m(e,"empty_selection_assets")):s.layout==="tiles"?this.renderTiles(e,i):this.renderList(e,i)}
        ${r?d`<button class="show-all" @click=${()=>this.showAll=!this.showAll}>
              ${this.showAll?m(e,"show_less"):m(e,"show_all",{count:l})}
            </button>`:u}
      </div>
      ${this.footer(e,i,c)}
    </ha-card>`}};bt("bitpanda-price-tracker-card",ds,{name:"Bitpanda Price Tracker",description:()=>m(tt(),"picker_price_tracker"),model:"Price Tracker"});
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
