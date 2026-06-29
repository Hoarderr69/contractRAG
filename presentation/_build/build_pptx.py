#!/usr/bin/env python3
"""Contract360 — EY-branded manager deck generator (python-pptx)."""
import os
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from pptx.oxml.ns import qn
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "Contract360_Manager_Deck.pptx")

# ---- EY brand palette ----
EY_YELLOW = RGBColor(0xFF, 0xE6, 0x00)
EY_BLACK  = RGBColor(0x2E, 0x2E, 0x38)   # EY "off-black"
EY_GREY   = RGBColor(0x74, 0x74, 0x80)
EY_LIGHT  = RGBColor(0xF2, 0xF2, 0xF5)   # card fill
EY_LINE   = RGBColor(0xC4, 0xC4, 0xCD)
WHITE     = RGBColor(0xFF, 0xFF, 0xFF)
FONT      = "Arial"

prs = Presentation()
prs.slide_width  = Inches(13.333)
prs.slide_height = Inches(7.5)
SW, SH = prs.slide_width, prs.slide_height
BLANK = prs.slide_layouts[6]


def solid(shape, color):
    shape.fill.solid(); shape.fill.fore_color.rgb = color
    shape.line.fill.background()


def no_shadow(shape):
    sp = shape._element.spPr
    el = sp.find(qn('a:effectLst'))
    if el is None:
        el = sp.makeelement(qn('a:effectLst'), {}); sp.append(el)


def rect(slide, l, t, w, h, color=None, line=None, line_w=None, shape=MSO_SHAPE.RECTANGLE):
    sp = slide.shapes.add_shape(shape, l, t, w, h)
    if color is not None:
        sp.fill.solid(); sp.fill.fore_color.rgb = color
    else:
        sp.fill.background()
    if line is not None:
        sp.line.color.rgb = line; sp.line.width = line_w or Pt(1)
    else:
        sp.line.fill.background()
    no_shadow(sp)
    return sp


def txt(slide, l, t, w, h, runs, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP,
        space_after=4, line_spacing=1.0, wrap=True):
    """runs: list of paragraphs; each paragraph is list of (text,size,color,bold,italic)."""
    tb = slide.shapes.add_textbox(l, t, w, h); tf = tb.text_frame
    tf.word_wrap = wrap
    tf.vertical_anchor = anchor
    for m in (tf.margin_left, ):
        pass
    tf.margin_left = Pt(0); tf.margin_right = Pt(0)
    tf.margin_top = Pt(0); tf.margin_bottom = Pt(0)
    for i, para in enumerate(runs):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align; p.space_after = Pt(space_after); p.space_before = Pt(0)
        p.line_spacing = line_spacing
        for (text, size, color, bold, italic) in para:
            r = p.add_run(); r.text = text
            r.font.size = Pt(size); r.font.color.rgb = color
            r.font.bold = bold; r.font.italic = italic; r.font.name = FONT
    return tb


def ey_logo(slide, l, t, dark_bg=False, scale=1.0):
    """EY wordmark: 'EY' + a yellow angled beam underneath."""
    h = Inches(0.46 * scale); w = Inches(0.74 * scale)
    tb = slide.shapes.add_textbox(l, t, w, h); tf = tb.text_frame
    tf.margin_left = Pt(0); tf.margin_top = Pt(0); tf.margin_bottom = Pt(0)
    p = tf.paragraphs[0]; p.alignment = PP_ALIGN.LEFT
    r = p.add_run(); r.text = "EY"
    r.font.size = Pt(26 * scale); r.font.bold = True; r.font.name = FONT
    r.font.color.rgb = WHITE if dark_bg else EY_BLACK
    beam = slide.shapes.add_shape(MSO_SHAPE.PARALLELOGRAM, l, t + Inches(0.40*scale),
                                  Inches(0.66*scale), Inches(0.12*scale))
    solid(beam, EY_YELLOW); no_shadow(beam)
    beam.adjustments[0] = 0.6
    return tb


def footer(slide, page):
    txt(slide, Inches(0.55), Inches(7.06), Inches(8), Inches(0.3),
        [[("Contract360  |  Confidential — for internal management review", 8.5, EY_GREY, False, False)]])
    txt(slide, Inches(11.8), Inches(7.06), Inches(1.0), Inches(0.3),
        [[(str(page), 9, EY_GREY, True, False)]], align=PP_ALIGN.RIGHT)


def header(slide, kicker, title, page):
    # top black band
    rect(slide, 0, 0, SW, Inches(1.18), EY_BLACK)
    # yellow accent under band
    rect(slide, 0, Inches(1.18), SW, Inches(0.06), EY_YELLOW)
    txt(slide, Inches(0.55), Inches(0.20), Inches(10), Inches(0.3),
        [[(kicker.upper(), 11, EY_YELLOW, True, False)]])
    txt(slide, Inches(0.55), Inches(0.48), Inches(11.5), Inches(0.6),
        [[(title, 25, WHITE, True, False)]])
    ey_logo(slide, Inches(12.25), Inches(0.30), dark_bg=True, scale=0.85)
    footer(slide, page)


def card(slide, l, t, w, h, heading, bullets, head_color=EY_BLACK, accent=EY_YELLOW,
         heading_size=14, body_size=11.5):
    rect(slide, l, t, w, h, EY_LIGHT)
    rect(slide, l, t, Inches(0.09), h, accent)  # left accent bar
    pad = Inches(0.22)
    txt(slide, l + pad + Inches(0.04), t + Inches(0.14), w - pad - Inches(0.2), Inches(0.4),
        [[(heading, heading_size, head_color, True, False)]])
    runs = []
    for b in bullets:
        if isinstance(b, tuple):
            lead, rest = b
            runs.append([("• ", body_size, accent_dark(accent), True, False),
                         (lead, body_size, EY_BLACK, True, False),
                         (rest, body_size, EY_BLACK, False, False)])
        else:
            runs.append([("• ", body_size, EY_GREY, True, False),
                         (b, body_size, EY_BLACK, False, False)])
    txt(slide, l + pad + Inches(0.04), t + Inches(0.56), w - pad - Inches(0.18), h - Inches(0.7),
        runs, space_after=5, line_spacing=1.04)


def accent_dark(c):
    return EY_GREY


def chip(slide, l, t, text):
    w = Inches(0.16 + 0.092 * len(text))
    sp = rect(slide, l, t, w, Inches(0.34), EY_BLACK, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
    try: sp.adjustments[0] = 0.5
    except Exception: pass
    tf = sp.text_frame; tf.word_wrap = False
    tf.margin_left = Pt(2); tf.margin_right = Pt(2); tf.margin_top = Pt(0); tf.margin_bottom = Pt(0)
    p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
    r = p.add_run(); r.text = text; r.font.size = Pt(10); r.font.bold = True
    r.font.color.rgb = EY_YELLOW; r.font.name = FONT
    return l + w + Inches(0.12)


def add_image_fit(slide, path, box_l, box_t, box_w, box_h, align="center"):
    iw, ih = Image.open(path).size
    ar = iw / ih; box_ar = box_w / box_h
    if ar > box_ar:
        w = box_w; h = int(box_w / ar)
    else:
        h = box_h; w = int(box_h * ar)
    l = box_l + (box_w - w) // 2
    t = box_t + (box_h - h) // 2
    return slide.shapes.add_picture(path, l, t, w, h)


def notes(slide, text):
    slide.notes_slide.notes_text_frame.text = text


# ============================================================== TITLE SLIDE
s = prs.slides.add_slide(BLANK)
rect(s, 0, 0, SW, SH, EY_BLACK)
# yellow beam motif (EY signature) bottom-left diagonal
beam = s.shapes.add_shape(MSO_SHAPE.PARALLELOGRAM, Inches(-1.2), Inches(5.7), Inches(7.5), Inches(2.6))
solid(beam, EY_YELLOW); no_shadow(beam); beam.adjustments[0] = 0.55
beam2 = s.shapes.add_shape(MSO_SHAPE.PARALLELOGRAM, Inches(4.2), Inches(6.5), Inches(7.0), Inches(2.2))
solid(beam2, RGBColor(0x3A,0x3A,0x45)); no_shadow(beam2); beam2.adjustments[0] = 0.55
ey_logo(s, Inches(0.6), Inches(0.55), dark_bg=True, scale=1.25)
txt(s, Inches(0.62), Inches(2.05), Inches(11), Inches(0.4),
    [[("CONTRACT INTELLIGENCE  ·  AI / RAG  ·  AZURE-NATIVE", 13, EY_YELLOW, True, False)]])
txt(s, Inches(0.6), Inches(2.5), Inches(12), Inches(1.4),
    [[("Contract360", 60, WHITE, True, False)]])
txt(s, Inches(0.62), Inches(3.75), Inches(11.5), Inches(1.0),
    [[("A retrieval-augmented assistant that answers natural-language questions over", 18, EY_LIGHT, False, False)],
     [("energy & infrastructure contracts — with grounded, citation-backed answers.", 18, EY_LIGHT, False, False)]],
    space_after=2)
txt(s, Inches(0.62), Inches(5.05), Inches(11), Inches(0.4),
    [[("Presented to Senior Leadership", 13, WHITE, True, False)]])
notes(s, "Contract360 is an AI assistant for our energy & infrastructure contracts (EPC, O&M, PPA). "
        "It is built end-to-end on Azure. Today: the problem we set out to solve, the solution and how it works, "
        "the architecture, and a live demo. Headline: every answer is grounded in the actual contract text and cites its source — built for auditability.")

# ============================================================== SLIDE 1 — PROBLEM / SOLUTION / USE CASE / STACK
s = prs.slides.add_slide(BLANK)
header(s, "Slide 1 — Context", "Problem, Solution & Where It Creates Value", 2)
top = Inches(1.55); ch = Inches(2.42); gap = Inches(0.3)
colw = Inches(6.06)
lcol = Inches(0.55); rcol = lcol + colw + gap
card(s, lcol, top, colw, ch, "The problem",
     [("Long & high-stakes.  ", "EPC, O&M and PPA contracts run to hundreds of pages of dense legal text."),
      ("Slow, manual review.  ", "Finding obligations, deadlines, payment terms, termination & indemnity clauses is hours of work."),
      ("Generic AI can't be trusted.  ", "Off-the-shelf chatbots hallucinate and give no citations — not auditable for legal decisions.")],
     accent=EY_YELLOW)
card(s, rcol, top, colw, ch, "The solution — Contract360",
     [("Ask in plain English.  ", "Upload a contract; query it conversationally — single contract or a portfolio."),
      ("Grounded & cited.  ", "Every answer is drawn from actual clause text and cites title, page range & source."),
      ("Contract-aware.  ", "Clause-aware chunking, a hierarchical contract tree and a legal knowledge graph for relationship questions.")],
     accent=EY_YELLOW)
bt = top + ch + gap
card(s, lcol, bt, colw, ch, "Business value",
     [("Faster review & due diligence.  ", "Cut manual contract-reading time across legal, commercial & deal teams."),
      ("Audit-ready answers.  ", "Citation trail supports compliance and risk decisions."),
      ("Portfolio insight.  ", "Surface obligations, rights & deadlines across many contracts at once.")],
     accent=EY_YELLOW)
# Tech stack card with chips
rect(s, rcol, bt, colw, ch, EY_LIGHT)
rect(s, rcol, bt, Inches(0.09), ch, EY_YELLOW)
txt(s, rcol + Inches(0.26), bt + Inches(0.14), colw - Inches(0.4), Inches(0.4),
    [[("Technology stack", 14, EY_BLACK, True, False)]])
rows = [("APP", ["FastAPI", "React", "Vite", "Tailwind"]),
        ("AI", ["Azure OpenAI (GPT-4)", "text-embedding-3"]),
        ("DATA", ["AI Search", "Cosmos NoSQL", "Cosmos Gremlin", "Blob"]),
        ("RUN", ["Azure Container Apps", "ACR"])]
yy = bt + Inches(0.58)
for label, items in rows:
    txt(s, rcol + Inches(0.28), yy + Inches(0.02), Inches(0.7), Inches(0.3),
        [[(label, 9.5, EY_GREY, True, False)]])
    xx = rcol + Inches(1.05)
    for it in items:
        xx = chip(s, xx, yy, it)
    yy += Inches(0.44)
notes(s, "Problem: our key contracts are long, dense and high-stakes, and reviewing them is slow and manual. "
        "Generic AI tools hallucinate and don't cite sources, so they can't be trusted for legal decisions. "
        "Solution: Contract360 lets you upload a contract and ask questions in plain English; every answer is grounded "
        "in the real clause text and cites title, page and source. Value: faster review and due diligence, audit-ready "
        "answers, and portfolio-wide visibility of obligations and deadlines. It's built entirely on our Azure stack — "
        "no new vendor footprint.")

# ============================================================== SLIDE 2 — HIGH-LEVEL ARCHITECTURE
s = prs.slides.add_slide(BLANK)
header(s, "Slide 1 (cont.) — How it works", "High-Level Architecture", 3)
add_image_fit(s, os.path.join(HERE, "hl_arch.png"), Inches(0.55), Inches(1.5), Inches(12.25), Inches(4.45))
# three takeaways strip
ty = Inches(6.05)
tk = [("INGEST ONCE", "Parse → tree → clause chunks + embeddings → searchable index."),
      ("ROUTE EACH QUERY", "An LLM router picks tree, graph or hybrid retrieval per question."),
      ("ANSWER, GROUNDED", "Azure OpenAI answers only from retrieved context — with citations.")]
cw = Inches(4.0); cl = Inches(0.55)
for i,(h,b) in enumerate(tk):
    x = cl + i*(cw + Inches(0.21))
    rect(s, x, ty, Inches(0.07), Inches(0.78), EY_YELLOW)
    txt(s, x+Inches(0.18), ty, cw-Inches(0.2), Inches(0.8),
        [[(h, 11, EY_BLACK, True, False)],[(b, 10, EY_GREY, False, False)]], space_after=2, line_spacing=1.0)
notes(s, "Two pipelines over one shared Azure backbone. Ingestion runs once per contract: we parse the document, "
        "build a hierarchical tree, create clause-aware chunks with embeddings, and index them — optionally extracting a "
        "knowledge graph. At query time, an LLM router reads the question and picks the best retrieval strategy — tree "
        "search, graph lookup, or a hybrid — then Azure OpenAI generates an answer using only what was retrieved, with "
        "inline citations. Everything sits on Azure services we already operate.")

# ============================================================== SLIDE 3 — DETAILED ARCHITECTURE
s = prs.slides.add_slide(BLANK)
header(s, "Slide 2 — Engineering view", "Detailed Architecture", 4)
add_image_fit(s, os.path.join(HERE, "detail_arch.png"), Inches(4.55), Inches(1.40), Inches(4.6), Inches(5.55))
# left legend / explanation column
lx = Inches(0.55); lw = Inches(3.7)
txt(s, lx, Inches(1.55), lw, Inches(0.4), [[("FIVE LAYERS", 11, EY_GREY, True, False)]])
layers = [("Frontend", "React + TypeScript SPA — chat, sidebar, upload."),
          ("FastAPI", "Sessions, ask (sync/stream), async ingest."),
          ("Query pipeline", "LLM router → search / graph / hybrid / tree → AnswerGenerator."),
          ("Ingestion pipeline", "Worker pool: read → tree → chunk → embed → index."),
          ("Knowledge graph", "Offline: parties, obligations, rights → Gremlin."),
          ("Azure services", "Blob · AI Search · Cosmos NoSQL · Gremlin · OpenAI.")]
yy = Inches(1.95)
for h,b in layers:
    rect(s, lx, yy+Inches(0.03), Inches(0.07), Inches(0.62), EY_YELLOW)
    txt(s, lx+Inches(0.18), yy, lw-Inches(0.2), Inches(0.7),
        [[(h, 11.5, EY_BLACK, True, False)],[(b, 9.5, EY_GREY, False, False)]], space_after=1, line_spacing=1.0)
    yy += Inches(0.72)
# right column highlights
rx = Inches(9.45); rw = Inches(3.4)
txt(s, rx, Inches(1.55), rw, Inches(0.4), [[("DESIGN HIGHLIGHTS", 11, EY_GREY, True, False)]])
hi = [("Async ingestion", "Upload returns immediately (202); a thread pool processes files with live progress."),
      ("Pluggable parsing", "Azure Document Intelligence with a pypdf fallback."),
      ("Cited answers", "Sources carried end-to-end into every response."),
      ("Scales out", "Container Apps; Service Bus path for multi-instance."),
      ("Config-driven", "Graph & Doc-Intelligence toggle on/off via env.")]
yy = Inches(1.95)
for h,b in hi:
    rect(s, rx, yy+Inches(0.03), Inches(0.07), Inches(0.74), EY_BLACK)
    txt(s, rx+Inches(0.18), yy, rw-Inches(0.2), Inches(0.85),
        [[(h, 11.5, EY_BLACK, True, False)],[(b, 9.5, EY_GREY, False, False)]], space_after=1, line_spacing=1.0)
    yy += Inches(0.86)
notes(s, "The engineering view. Frontend talks to a FastAPI backend. Reads go through the query pipeline: the LLM router "
        "rewrites the question, resolves scope, and chooses a retrieval route; results feed the AnswerGenerator. Writes go "
        "through the ingestion pipeline: an async worker pool parses, builds the tree, chunks, embeds and indexes each file "
        "with live status. An offline knowledge-graph pipeline adds parties, obligations and rights to Cosmos Gremlin for "
        "relationship questions. All of it runs on Azure-managed services, and the optional pieces are env-toggle. "
        "Full interactive diagram lives in ARCHITECTURE.md in the repo.")

# ============================================================== SLIDE 4 — DEMO
s = prs.slides.add_slide(BLANK)
header(s, "Slide 3 — Demo", "See It In Action", 5)
# left: demo flow
lx = Inches(0.55); lw = Inches(6.1); top = Inches(1.6)
card(s, lx, top, lw, Inches(3.05), "Live demo flow",
     [("1. Upload a contract.  ", "Drag-drop a PDF; watch parse → embed → index progress live."),
      ("2. Ask a question.  ", "“What are the contractor's payment obligations?”"),
      ("3. Read a grounded answer.  ", "Response streams in with inline clause citations."),
      ("4. Show the routing.  ", "A relationship question (graph) vs. a lookup (tree)."),
      ("5. Multi-contract scope.  ", "Filter to one contract or query across several.")],
     accent=EY_YELLOW, body_size=11.5)
# sample questions card
card(s, lx, top+Inches(3.25), lw, Inches(2.35), "Sample questions to demo",
     ["“Summarise the termination clauses and any notice periods.”",
      "“What deadlines does the contractor have in the first 90 days?”",
      "“Which party bears liability for delay, and is there a cap?”",
      "“List the indemnities granted to the owner.”"],
     accent=EY_BLACK, body_size=11)
# right: backup + what to watch
rx = Inches(6.95); rw = Inches(5.85)
rect(s, rx, top, rw, Inches(1.5), EY_BLACK)
rect(s, rx, top, Inches(0.09), Inches(1.5), EY_YELLOW)
txt(s, rx+Inches(0.28), top+Inches(0.18), rw-Inches(0.5), Inches(0.4),
    [[("⚑  Backup plan", 14, EY_YELLOW, True, False)]])
txt(s, rx+Inches(0.28), top+Inches(0.62), rw-Inches(0.5), Inches(0.8),
    [[("A pre-recorded demo video is ready in case of live connectivity or", 11, WHITE, False, False)],
     [("environment issues. ", 11, WHITE, True, False),("[ insert link / embed before the meeting ]", 11, EY_YELLOW, False, True)]],
    space_after=2, line_spacing=1.05)
card(s, rx, top+Inches(1.72), rw, Inches(1.6), "What to watch for",
     [("Speed.  ", "Answer in seconds; ingestion runs in the background."),
      ("Trust.  ", "Each claim links to a clause — open it to verify."),
      ("Range.  ", "Same assistant handles lookup, summary & relationship questions.")],
     accent=EY_YELLOW, body_size=11)
card(s, rx, top+Inches(3.35), rw, Inches(1.95), "Roadmap (post-MVP)",
     ["Content-aware scoping by party / contract.",
      "Reasoning-based navigation of the contract tree.",
      "Knowledge-graph portfolio analytics across contracts.",
      "Azure Entra ID authentication for production."],
     accent=EY_BLACK, body_size=11)
notes(s, "Demo plan: upload a contract live and show the ingestion progress, then ask a payment-obligations question and "
        "show the streamed, cited answer — click a citation to prove it's grounded. Then contrast a relationship question "
        "(graph route) with a simple lookup (tree route), and show multi-contract scope. Always click into at least one "
        "citation — that's the trust moment. Backup: a recorded video is ready if the live environment misbehaves "
        "(remember to insert the link before the meeting). Close on roadmap: content-aware scoping, reasoning-based "
        "retrieval, portfolio analytics, and Entra ID auth.")

prs.save(OUT)
print("Saved", OUT, os.path.getsize(OUT), "bytes,", len(prs.slides.__iter__.__self__._sldIdLst), "slides")
