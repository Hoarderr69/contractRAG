#!/usr/bin/env python3
"""Build a self-contained EY-branded HTML deck (no external deps)."""
import base64, os
HERE = os.path.dirname(os.path.abspath(__file__))

def b64(p):
    with open(os.path.join(HERE, p), "rb") as f:
        return "data:image/png;base64," + base64.b64encode(f.read()).decode()

HL = b64("hl_arch.png")
DET = b64("detail_arch.png")

HTML = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Contract360 — Manager Briefing</title>
<style>
:root{--yellow:#FFE600;--black:#2E2E38;--grey:#747480;--light:#F2F2F5;--line:#C4C4CD;--white:#fff;}
*{box-sizing:border-box;margin:0;padding:0;}
html,body{height:100%;font-family:Arial,Helvetica,sans-serif;background:#15151b;color:var(--black);}
.deck{height:100vh;width:100vw;overflow:hidden;}
.slide{display:none;width:100vw;height:100vh;background:var(--white);position:relative;}
.slide.active{display:block;}
/* aspect-stable inner canvas 16:9 */
.canvas{position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);
  width:min(100vw,177.78vh);height:min(56.25vw,100vh);background:var(--white);overflow:hidden;}
/* ---- header band ---- */
.band{position:absolute;top:0;left:0;right:0;height:15.8%;background:var(--black);}
.band:after{content:"";position:absolute;left:0;right:0;bottom:-0.8%;height:0.8%;background:var(--yellow);}
.kicker{position:absolute;top:6%;left:4.1%;color:var(--yellow);font-weight:700;font-size:1.05vw;letter-spacing:.06em;}
.htitle{position:absolute;top:9.2%;left:4.1%;color:#fff;font-weight:700;font-size:2.45vw;}
.logo{position:absolute;font-weight:700;line-height:.9;}
.logo .ey{font-size:2.1vw;}
.logo .beam{height:.62vw;width:1.9vw;background:var(--yellow);margin-top:.18vw;
  clip-path:polygon(14% 0,100% 0,86% 100%,0% 100%);}
.foot{position:absolute;bottom:2.4%;left:4.1%;color:var(--grey);font-size:.92vw;}
.pg{position:absolute;bottom:2.4%;right:4.1%;color:var(--grey);font-size:.95vw;font-weight:700;}
/* ---- cards ---- */
.card{position:absolute;background:var(--light);padding:1.4vw 1.5vw 1.3vw 1.7vw;border-radius:2px;overflow:hidden;}
.card:before{content:"";position:absolute;left:0;top:0;bottom:0;width:.42vw;background:var(--yellow);}
.card.k:before{background:var(--black);}
.card h3{font-size:1.4vw;margin-bottom:.7vw;color:var(--black);}
.card li{list-style:none;font-size:1.06vw;line-height:1.4;margin-bottom:.5vw;color:var(--black);
  padding-left:1.1vw;position:relative;}
.card li:before{content:"•";position:absolute;left:0;color:var(--grey);font-weight:700;}
.card li b{color:var(--black);}
.sub{color:var(--grey);font-size:.97vw;line-height:1.35;}
/* chips */
.chiprow{display:flex;align-items:center;margin-bottom:.55vw;flex-wrap:wrap;gap:.4vw;}
.chiplbl{color:var(--grey);font-weight:700;font-size:.85vw;width:2.6vw;flex:none;}
.chip{background:var(--black);color:var(--yellow);font-weight:700;font-size:.86vw;
  padding:.22vw .6vw;border-radius:1vw;}
/* takeaways */
.tk{position:absolute;padding-left:1vw;}
.tk:before{content:"";position:absolute;left:0;top:.1vw;bottom:.1vw;width:.4vw;background:var(--yellow);}
.tk h4{font-size:1.0vw;color:var(--black);}
.tk p{font-size:.9vw;color:var(--grey);line-height:1.3;margin-top:.15vw;}
.tk.k:before{background:var(--black);}
img.arch{position:absolute;object-fit:contain;}
/* title slide */
.title{background:var(--black);}
.title .beamA{position:absolute;left:-8%;bottom:-6%;width:46%;height:40%;background:var(--yellow);
  clip-path:polygon(18% 0,100% 0,82% 100%,0 100%);}
.title .beamB{position:absolute;left:34%;bottom:-12%;width:42%;height:34%;background:#3a3a45;
  clip-path:polygon(18% 0,100% 0,82% 100%,0 100%);}
.title .tk0{position:absolute;top:27%;left:4.6%;color:var(--yellow);font-weight:700;font-size:1.15vw;letter-spacing:.08em;}
.title h1{position:absolute;top:31%;left:4.4%;color:#fff;font-size:5.6vw;font-weight:700;}
.title .lead{position:absolute;top:50%;left:4.6%;color:var(--light);font-size:1.6vw;width:80%;line-height:1.4;}
.title .pres{position:absolute;top:66.5%;left:4.6%;color:var(--black);font-weight:700;font-size:1.2vw;}
.hint{position:fixed;bottom:10px;right:14px;color:#888;font-size:11px;z-index:50;font-family:Arial;}
.box{position:absolute;background:var(--black);color:#fff;padding:1.1vw 1.3vw;border-radius:2px;}
.box:before{content:"";position:absolute;left:0;top:0;bottom:0;width:.42vw;background:var(--yellow);}
.box h3{color:var(--yellow);font-size:1.35vw;margin-bottom:.5vw;}
.box p{font-size:1.0vw;line-height:1.4;}
.box .y{color:var(--yellow);font-style:italic;}
</style></head>
<body>
<div class="deck">

<!-- 0 TITLE -->
<section class="slide active"><div class="canvas title">
  <div class="beamA"></div><div class="beamB"></div>
  <div class="logo" style="top:7%;left:4.4%"><div class="ey" style="color:#fff">EY</div><div class="beam"></div></div>
  <div class="tk0">CONTRACT INTELLIGENCE &nbsp;·&nbsp; AI / RAG &nbsp;·&nbsp; AZURE-NATIVE</div>
  <h1>Contract360</h1>
  <div class="lead">A retrieval-augmented assistant that answers natural-language questions over energy &amp; infrastructure contracts — with grounded, citation-backed answers.</div>
  <div class="pres">Presented to Senior Leadership</div>
</div></section>

<!-- 1 CONTEXT -->
<section class="slide"><div class="canvas">
  __HEADER__('Slide 1 — Context','Problem, Solution &amp; Where It Creates Value','2')
  <div class="card" style="left:4.1%;top:20%;width:44.6%;height:35%">
    <h3>The problem</h3><ul>
    <li><b>Long &amp; high-stakes.</b> EPC, O&amp;M and PPA contracts run to hundreds of pages of dense legal text.</li>
    <li><b>Slow, manual review.</b> Finding obligations, deadlines, payment, termination &amp; indemnity clauses is hours of work.</li>
    <li><b>Generic AI can't be trusted.</b> Off-the-shelf chatbots hallucinate and give no citations — not auditable.</li></ul>
  </div>
  <div class="card" style="left:51.3%;top:20%;width:44.6%;height:35%">
    <h3>The solution — Contract360</h3><ul>
    <li><b>Ask in plain English.</b> Upload a contract; query it conversationally — one contract or a portfolio.</li>
    <li><b>Grounded &amp; cited.</b> Every answer is drawn from real clause text and cites title, page range &amp; source.</li>
    <li><b>Contract-aware.</b> Clause-aware chunking, a hierarchical tree and a legal knowledge graph.</li></ul>
  </div>
  <div class="card" style="left:4.1%;top:57.5%;width:44.6%;height:35%">
    <h3>Business value</h3><ul>
    <li><b>Faster review &amp; due diligence.</b> Cut manual reading time for legal, commercial &amp; deal teams.</li>
    <li><b>Audit-ready answers.</b> Citation trail supports compliance and risk decisions.</li>
    <li><b>Portfolio insight.</b> Surface obligations, rights &amp; deadlines across many contracts at once.</li></ul>
  </div>
  <div class="card" style="left:51.3%;top:57.5%;width:44.6%;height:35%">
    <h3>Technology stack</h3>
    <div class="chiprow"><span class="chiplbl">APP</span><span class="chip">FastAPI</span><span class="chip">React</span><span class="chip">Vite</span><span class="chip">Tailwind</span></div>
    <div class="chiprow"><span class="chiplbl">AI</span><span class="chip">Azure OpenAI (GPT-4)</span><span class="chip">text-embedding-3</span></div>
    <div class="chiprow"><span class="chiplbl">DATA</span><span class="chip">AI Search</span><span class="chip">Cosmos NoSQL</span><span class="chip">Cosmos Gremlin</span><span class="chip">Blob</span></div>
    <div class="chiprow"><span class="chiplbl">RUN</span><span class="chip">Azure Container Apps</span><span class="chip">ACR</span></div>
  </div>
</div></section>

<!-- 2 HL ARCH -->
<section class="slide"><div class="canvas">
  __HEADER__('Slide 1 (cont.) — How it works','High-Level Architecture','3')
  <img class="arch" src="__HL__" style="left:4.1%;top:18.5%;width:91.8%;height:58%"/>
  <div class="tk"   style="left:4.1%;top:80%;width:29%"><h4>INGEST ONCE</h4><p>Parse → tree → clause chunks + embeddings → searchable index.</p></div>
  <div class="tk"   style="left:35.5%;top:80%;width:29%"><h4>ROUTE EACH QUERY</h4><p>An LLM router picks tree, graph or hybrid retrieval per question.</p></div>
  <div class="tk"   style="left:67%;top:80%;width:29%"><h4>ANSWER, GROUNDED</h4><p>Azure OpenAI answers only from retrieved context — with citations.</p></div>
</div></section>

<!-- 3 DETAIL ARCH -->
<section class="slide"><div class="canvas">
  __HEADER__('Slide 2 — Engineering view','Detailed Architecture','4')
  <img class="arch" src="__DET__" style="left:34%;top:17.5%;width:32%;height:80%"/>
  <div style="position:absolute;left:4.1%;top:18.5%;color:var(--grey);font-weight:700;font-size:.95vw;">FIVE LAYERS</div>
  __LAYERS__
  <div style="position:absolute;left:69%;top:18.5%;color:var(--grey);font-weight:700;font-size:.95vw;">DESIGN HIGHLIGHTS</div>
  __HIGH__
</div></section>

<!-- 4 DEMO -->
<section class="slide"><div class="canvas">
  __HEADER__('Slide 3 — Demo','See It In Action','5')
  <div class="card" style="left:4.1%;top:20%;width:45%;height:41%">
    <h3>Live demo flow</h3><ul>
    <li><b>1. Upload a contract.</b> Drag-drop a PDF; watch parse → embed → index progress live.</li>
    <li><b>2. Ask a question.</b> “What are the contractor's payment obligations?”</li>
    <li><b>3. Read a grounded answer.</b> Response streams in with inline clause citations.</li>
    <li><b>4. Show the routing.</b> A relationship question (graph) vs. a lookup (tree).</li>
    <li><b>5. Multi-contract scope.</b> Filter to one contract or query across several.</li></ul>
  </div>
  <div class="card k" style="left:4.1%;top:63%;width:45%;height:29.5%">
    <h3>Sample questions to demo</h3><ul>
    <li>“Summarise the termination clauses and any notice periods.”</li>
    <li>“What deadlines does the contractor have in the first 90 days?”</li>
    <li>“Which party bears liability for delay, and is there a cap?”</li>
    <li>“List the indemnities granted to the owner.”</li></ul>
  </div>
  <div class="box" style="left:51%;top:20%;width:44.9%;height:19%">
    <h3>⚑ Backup plan</h3>
    <p>A pre-recorded demo video is ready in case of live connectivity or environment issues.<br/>
    <span class="y">[ insert link / embed before the meeting ]</span></p>
  </div>
  <div class="card" style="left:51%;top:41.5%;width:44.9%;height:22%">
    <h3>What to watch for</h3><ul>
    <li><b>Speed.</b> Answer in seconds; ingestion runs in the background.</li>
    <li><b>Trust.</b> Each claim links to a clause — open it to verify.</li>
    <li><b>Range.</b> One assistant handles lookup, summary &amp; relationship questions.</li></ul>
  </div>
  <div class="card k" style="left:51%;top:65.5%;width:44.9%;height:27%">
    <h3>Roadmap (post-MVP)</h3><ul>
    <li>Content-aware scoping by party / contract.</li>
    <li>Reasoning-based navigation of the contract tree.</li>
    <li>Knowledge-graph portfolio analytics across contracts.</li>
    <li>Azure Entra ID authentication for production.</li></ul>
  </div>
</div></section>

</div>
<div class="hint">← → / Space to navigate &nbsp;·&nbsp; F fullscreen</div>
<script>
var i=0,S=document.querySelectorAll('.slide');
function go(n){i=Math.max(0,Math.min(S.length-1,n));S.forEach((s,k)=>s.classList.toggle('active',k===i));}
document.addEventListener('keydown',e=>{
 if(['ArrowRight','PageDown',' '].includes(e.key)){go(i+1);e.preventDefault();}
 else if(['ArrowLeft','PageUp'].includes(e.key))go(i-1);
 else if(e.key==='Home')go(0); else if(e.key==='End')go(S.length-1);
 else if(e.key==='f'||e.key==='F'){if(!document.fullscreenElement)document.documentElement.requestFullscreen();else document.exitFullscreen();}
});
document.addEventListener('click',e=>{if(e.target.closest('.hint'))return;go(i+1);});
</script>
</body></html>"""

def header(kicker, title, pg):
    return (f'<div class="band"></div>'
            f'<div class="kicker">{kicker.upper()}</div>'
            f'<div class="htitle">{title}</div>'
            f'<div class="logo" style="top:3.4%;right:3.5%"><div class="ey" style="color:#fff">EY</div><div class="beam"></div></div>'
            f'<div class="foot">Contract360 &nbsp;|&nbsp; Confidential — for internal management review</div>'
            f'<div class="pg">{pg}</div>')

layers = [("Frontend","React + TypeScript SPA — chat, sidebar, upload."),
          ("FastAPI","Sessions, ask (sync/stream), async ingest."),
          ("Query pipeline","LLM router → search / graph / hybrid / tree → AnswerGenerator."),
          ("Ingestion pipeline","Worker pool: read → tree → chunk → embed → index."),
          ("Knowledge graph","Offline: parties, obligations, rights → Gremlin."),
          ("Azure services","Blob · AI Search · Cosmos NoSQL · Gremlin · OpenAI.")]
high = [("Async ingestion","Upload returns immediately (202); a thread pool processes files with live progress."),
        ("Pluggable parsing","Azure Document Intelligence with a pypdf fallback."),
        ("Cited answers","Sources carried end-to-end into every response."),
        ("Scales out","Container Apps; Service Bus path for multi-instance."),
        ("Config-driven","Graph & Doc-Intelligence toggle on/off via env.")]

def col(items, left, klass=""):
    out=[]; top=23.0; step=(70.0)/len(items)
    for h,b in items:
        out.append(f'<div class="tk {klass}" style="left:{left}%;top:{top}%;width:25%">'
                   f'<h4>{h}</h4><p>{b}</p></div>')
        top+=step
    return "\n".join(out)

html = HTML.replace("__HL__",HL).replace("__DET__",DET)
html = html.replace("__LAYERS__", col(layers,4.1))
html = html.replace("__HIGH__", col(high,69,"k"))
import re
def hsub(m):
    a=m.group(1).split("','")
    return header(a[0].strip("'"),a[1],a[2].strip("'"))
html = re.sub(r"__HEADER__\((.*)\)", hsub, html)

with open(os.path.join(HERE,"Contract360_Manager_Deck.html"),"w") as f:
    f.write(html)
print("wrote Contract360_Manager_Deck.html", len(html), "chars")
