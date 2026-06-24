#!/usr/bin/env python3
"""Generate a skincare-app pitch deck (.pptx) ready to upload to Google Slides."""

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

# ---- Palette (clean pastel baby blue) ------------------------------------
PLUM      = RGBColor(0x2B, 0x48, 0x65)   # deep slate blue (primary text / dark bg)
ROSE      = RGBColor(0x6F, 0xA8, 0xDC)   # sky blue (primary accent)
ROSE_DK   = RGBColor(0x4A, 0x7F, 0xB5)   # deeper blue
SAGE      = RGBColor(0x6C, 0xB4, 0xC4)   # soft teal (secondary accent)
CREAM     = RGBColor(0xF2, 0xF8, 0xFD)   # ice-blue background
WHITE     = RGBColor(0xFF, 0xFF, 0xFF)
GREY      = RGBColor(0x5A, 0x6A, 0x7A)   # cool muted body text
GOLD      = RGBColor(0xBF, 0xE0, 0xF5)   # light baby blue (highlight, dark text)

# 16:9
prs = Presentation()
prs.slide_width  = Inches(13.333)
prs.slide_height = Inches(7.5)
SW, SH = prs.slide_width, prs.slide_height
BLANK = prs.slide_layouts[6]

FONT = "Helvetica Neue"
FONT_H = "Georgia"


def slide():
    return prs.slides.add_slide(BLANK)


def bg(s, color):
    s.background.fill.solid()
    s.background.fill.fore_color.rgb = color


def box(s, l, t, w, h, color, line=None, line_w=None, shape=MSO_SHAPE.RECTANGLE):
    sp = s.shapes.add_shape(shape, l, t, w, h)
    sp.fill.solid()
    sp.fill.fore_color.rgb = color
    if line is None:
        sp.line.fill.background()
    else:
        sp.line.color.rgb = line
        sp.line.width = line_w or Pt(1)
    sp.shadow.inherit = False
    return sp


def text(s, l, t, w, h, runs, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP,
         space_after=6, line_spacing=1.0):
    """runs: list of paragraphs; each paragraph is a list of (text, size, color, bold, font) tuples."""
    tb = s.shapes.add_textbox(l, t, w, h)
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    for i, para in enumerate(runs):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.space_after = Pt(space_after)
        p.space_before = Pt(0)
        p.line_spacing = line_spacing
        for (txt, size, color, bold, font) in para:
            r = p.add_run()
            r.text = txt
            r.font.size = Pt(size)
            r.font.color.rgb = color
            r.font.bold = bold
            r.font.name = font
    return tb


def R(txt, size, color, bold=False, font=FONT):
    return (txt, size, color, bold, font)


def chip(s, l, t, label, fill, txtcolor):
    w = Inches(0.28 * len(label) + 0.5)
    sp = box(s, l, t, w, Inches(0.42), fill, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
    tf = sp.text_frame
    tf.word_wrap = False
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run(); r.text = label
    r.font.size = Pt(12); r.font.bold = True; r.font.color.rgb = txtcolor; r.font.name = FONT
    return sp


def kicker(s, txt, color=ROSE_DK, left=Inches(0.9), top=Inches(0.62)):
    text(s, left, top, Inches(8), Inches(0.4),
         [[R(txt.upper(), 13, color, True)]])


def page_num(s, n):
    text(s, SW - Inches(1.1), SH - Inches(0.55), Inches(0.8), Inches(0.4),
         [[R(str(n), 11, GREY, False)]], align=PP_ALIGN.RIGHT)


APP = "LUMÉ"
TAG = "Your face, understood."

# ========================================================================
# 1 — TITLE
# ========================================================================
s = slide(); bg(s, PLUM)
# decorative arcs
box(s, Inches(-2), Inches(-2), Inches(6), Inches(6), ROSE_DK, shape=MSO_SHAPE.OVAL)
box(s, Inches(-1.4), Inches(-1.4), Inches(4.8), Inches(4.8), PLUM, shape=MSO_SHAPE.OVAL)
box(s, SW - Inches(3), SH - Inches(3), Inches(5.5), Inches(5.5), ROSE, shape=MSO_SHAPE.OVAL)
box(s, SW - Inches(2.3), SH - Inches(2.3), Inches(4.4), Inches(4.4), PLUM, shape=MSO_SHAPE.OVAL)
text(s, Inches(1.2), Inches(2.5), Inches(9), Inches(1.6),
     [[R(APP, 88, WHITE, True, FONT_H)]])
text(s, Inches(1.25), Inches(3.9), Inches(9), Inches(0.7),
     [[R(TAG, 26, ROSE, False)]])
text(s, Inches(1.25), Inches(4.7), Inches(10), Inches(0.7),
     [[R("AI skincare diagnosis — from a single selfie to a regimen built for your skin.", 16, CREAM)]])
text(s, Inches(1.25), SH - Inches(0.9), Inches(8), Inches(0.4),
     [[R("Product & Pitch Overview  ·  2026", 13, RGBColor(0xA6,0xC4,0xDE))]])

# ========================================================================
# 2 — PROBLEM
# ========================================================================
s = slide(); bg(s, CREAM)
kicker(s, "The Problem")
text(s, Inches(0.9), Inches(1.0), Inches(11.5), Inches(1.2),
     [[R("Skincare is guesswork — and it's expensive.", 38, PLUM, True, FONT_H)]])
probs = [
    ("$300+", "wasted per year", "Shoppers buy by trend and packaging, not by what their skin actually needs."),
    ("70%", "use the wrong actives", "Mismatched ingredients trigger irritation, breakouts, and wasted spend."),
    ("1 in 3", "have a sensitivity", "Allergens and reactive ingredients hide in plain sight on labels."),
    ("Zero", "real diagnosis in-aisle", "A dermatologist visit is costly and slow; shelves offer no personalization."),
]
cw = Inches(2.85); gap = Inches(0.18); x0 = Inches(0.9); y = Inches(2.6)
for i,(big,sub,body) in enumerate(probs):
    x = x0 + i*(cw+gap)
    box(s, x, y, cw, Inches(3.4), WHITE, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
    box(s, x, y, cw, Inches(0.12), ROSE)
    text(s, x+Inches(0.25), y+Inches(0.45), cw-Inches(0.5), Inches(0.9),
         [[R(big, 40, ROSE_DK, True, FONT_H)]])
    text(s, x+Inches(0.25), y+Inches(1.4), cw-Inches(0.5), Inches(0.5),
         [[R(sub, 14, PLUM, True)]])
    text(s, x+Inches(0.25), y+Inches(1.95), cw-Inches(0.5), Inches(1.3),
         [[R(body, 13, GREY)]], line_spacing=1.1)
page_num(s, 2)

# ========================================================================
# 3 — SOLUTION
# ========================================================================
s = slide(); bg(s, PLUM)
kicker(s, "The Solution", color=ROSE)
text(s, Inches(0.9), Inches(1.0), Inches(11.5), Inches(1.8),
     [[R("A dermatologist-grade skin read", 40, WHITE, True, FONT_H)],
      [R("in the time it takes to take a selfie.", 40, ROSE, True, FONT_H)]],
     space_after=2)
text(s, Inches(0.9), Inches(3.0), Inches(11), Inches(1.2),
     [[R(f"{APP} turns one front-camera photo into a complete, personalized skincare regimen — "
         "analyzing your skin, accounting for your sensitivities, and recommending the exact "
         "products and the order to use them.", 18, CREAM)]], line_spacing=1.25)
pills = [("Instant", SAGE), ("Personalized", ROSE), ("Sensitivity-aware", GOLD), ("No appointment", WHITE)]
x = Inches(0.9)
for label, col in pills:
    sp = chip(s, x, Inches(4.7), label, col, PLUM)
    x += sp.width + Inches(0.25)
page_num(s, 3)

# ========================================================================
# 4 — HOW IT WORKS (5-step flow)
# ========================================================================
s = slide(); bg(s, CREAM)
kicker(s, "How It Works")
text(s, Inches(0.9), Inches(1.0), Inches(11.5), Inches(0.9),
     [[R("Five steps. One selfie. Zero guesswork.", 34, PLUM, True, FONT_H)]])
steps = [
    ("1", "Take a selfie", "Guided front-camera capture with lighting checks.", ROSE),
    ("2", "Facial analysis", "Computer vision maps 200+ facial zones.", ROSE_DK),
    ("3", "Detect concerns", "Identify acne, redness, pores, lines, texture, tone.", SAGE),
    ("4", "Add sensitivities", "Flag allergens & ingredients to avoid.", GOLD),
    ("5", "Get your regimen", "A ranked AM/PM routine matched to your skin.", PLUM),
]
cw = Inches(2.25); gap = Inches(0.13); x0 = Inches(0.7); y = Inches(2.4)
for i,(num,title,body,col) in enumerate(steps):
    x = x0 + i*(cw+gap)
    box(s, x, y, cw, Inches(3.6), WHITE, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
    circ = box(s, x+Inches(0.35), y+Inches(0.35), Inches(0.85), Inches(0.85), col, shape=MSO_SHAPE.OVAL)
    tf = circ.text_frame; p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
    r = p.add_run(); r.text = num; r.font.size = Pt(30); r.font.bold = True
    r.font.color.rgb = WHITE if col != GOLD else PLUM; r.font.name = FONT_H
    text(s, x+Inches(0.3), y+Inches(1.45), cw-Inches(0.6), Inches(0.8),
         [[R(title, 18, PLUM, True)]])
    text(s, x+Inches(0.3), y+Inches(2.25), cw-Inches(0.6), Inches(1.2),
         [[R(body, 13, GREY)]], line_spacing=1.15)
    if i < 4:
        text(s, x+cw-Inches(0.02), y+Inches(1.5), Inches(0.3), Inches(0.5),
             [[R("›", 28, ROSE_DK, True)]], align=PP_ALIGN.CENTER)
page_num(s, 4)

# ========================================================================
# Step detail slides 5–9
# ========================================================================
def detail_slide(n, step_label, title, lead, bullets, accent, num):
    s = slide(); bg(s, CREAM)
    # left accent panel
    box(s, 0, 0, Inches(4.6), SH, PLUM)
    box(s, 0, 0, Inches(0.18), SH, accent)
    text(s, Inches(0.7), Inches(1.1), Inches(3.4), Inches(1),
         [[R(step_label.upper(), 14, accent, True)]])
    # giant step number
    text(s, Inches(0.6), Inches(2.2), Inches(3.6), Inches(3),
         [[R(n, 200, RGBColor(0x3C,0x5E,0x82), True, FONT_H)]])
    text(s, Inches(0.7), Inches(5.6), Inches(3.4), Inches(1.2),
         [[R(lead, 15, CREAM)]], line_spacing=1.2)
    # right content
    rx = Inches(5.1)
    text(s, rx, Inches(1.1), Inches(7.5), Inches(1.2),
         [[R(title, 34, PLUM, True, FONT_H)]])
    y = Inches(2.5)
    for head, body in bullets:
        box(s, rx, y+Inches(0.08), Inches(0.16), Inches(0.16), accent, shape=MSO_SHAPE.OVAL)
        text(s, rx+Inches(0.35), y, Inches(7.2), Inches(0.5),
             [[R(head, 17, PLUM, True)]])
        text(s, rx+Inches(0.35), y+Inches(0.42), Inches(7.2), Inches(0.7),
             [[R(body, 14, GREY)]], line_spacing=1.15)
        y += Inches(1.02)
    page_num(s, num)
    return s

detail_slide("1", "Step 1 — Capture",
    "A selfie is the only input",
    "No forms. No quizzes. Just look at your phone.",
    [("Guided capture", "On-screen framing, lighting, and distance checks ensure a clean, analyzable image every time."),
     ("Works on any phone", "Standard front camera — no special hardware, attachments, or lab kit required."),
     ("Private by design", "Images are processed securely and never sold; users control retention and deletion."),
     ("3 seconds to result", "From shutter to analysis, the experience feels instant and effortless.")],
    ROSE, 5)

detail_slide("2", "Step 2 — Analysis",
    "Automatic facial analysis",
    "Computer vision reads the skin the way a clinician's eye would.",
    [("200+ facial landmarks", "We segment the face into zones — forehead, cheeks, T-zone, under-eye, jawline."),
     ("Multi-signal models", "Texture, tone, oiliness, hydration, and pigmentation are scored per zone."),
     ("Calibrated for lighting", "Color-correction normalizes for ambient light and camera differences."),
     ("Trained on diverse skin", "Models validated across skin tones, ages, and conditions to reduce bias.")],
    ROSE_DK, 6)

detail_slide("3", "Step 3 — Concerns",
    "Recognition of skin concerns",
    "We translate pixels into the concerns people actually care about.",
    [("Detects what matters", "Acne, redness, enlarged pores, fine lines, dark spots, uneven texture & tone."),
     ("Severity scoring", "Each concern is rated and ranked so the routine targets the biggest wins first."),
     ("Visual skin map", "Users see exactly where each concern appears — on their own face."),
     ("Progress tracking", "Re-scan over time to watch concerns improve and measure what's working.")],
    SAGE, 7)

detail_slide("4", "Step 4 — Sensitivities",
    "Input of product sensitivities",
    "Personalization that protects, not just prescribes.",
    [("Flag known reactions", "Fragrance, alcohol, retinoids, acids, essential oils, and specific allergens."),
     ("Smart ingredient filter", "Every recommendation is screened against the user's avoid-list."),
     ("Pregnancy & condition safe", "Surfaces flags for rosacea, eczema, and other context-specific needs."),
     ("Conflict detection", "Warns when two products shouldn't be layered together.")],
    GOLD, 8)

detail_slide("5", "Step 5 — Regimen",
    "Personalized regimen",
    "A complete routine — products, order, and timing.",
    [("Ranked product matches", "Specific products matched to concerns, budget, and sensitivities."),
     ("AM & PM routines", "Step-by-step order of application, with frequency guidance."),
     ("Why each step", "Plain-language reasoning so users trust and stick with the routine."),
     ("Reorder & restock", "One tap to buy, with reminders timed to when product runs out.")],
    ROSE, 9)

# ========================================================================
# 10 — THE EVIDENCE ENGINE (built today)
# ========================================================================
s = slide(); bg(s, CREAM)
kicker(s, "The Data Moat")
text(s, Inches(0.9), Inches(1.0), Inches(11.5), Inches(0.9),
     [[R("Recommendations grounded in science", 34, PLUM, True, FONT_H)]])
text(s, Inches(0.9), Inches(1.95), Inches(11.5), Inches(1.1),
     [[R("Every ingredient we recommend is backed by an automatically-built knowledge base. "
         "Our literature-ingestion pipeline reads a product's ingredient list and enriches each "
         "ingredient with chemical data and peer-reviewed evidence — no manual data entry.", 16, GREY)]],
     line_spacing=1.25)
feats = [
    ("Self-building database", "Point it at any product label and the knowledge base grows itself."),
    ("Evidence-backed", "Each ingredient links to PubMed studies and PubChem chemical descriptors."),
    ("Deduplicated & canonical", "INCI names are normalized and matched so every compound is stored once."),
    ("Compounding moat", "The more products ingested, the smarter every recommendation becomes."),
]
cw = Inches(2.85); gap = Inches(0.18); x0 = Inches(0.9); y = Inches(3.5)
for i,(t,b) in enumerate(feats):
    x = x0 + i*(cw+gap)
    box(s, x, y, cw, Inches(2.7), WHITE, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
    box(s, x+Inches(0.25), y+Inches(0.3), Inches(0.5), Inches(0.1), SAGE)
    text(s, x+Inches(0.25), y+Inches(0.5), cw-Inches(0.5), Inches(0.8),
         [[R(t, 16, PLUM, True)]])
    text(s, x+Inches(0.25), y+Inches(1.3), cw-Inches(0.5), Inches(1.2),
         [[R(b, 13, GREY)]], line_spacing=1.15)
page_num(s, 10)

# ========================================================================
# 11 — HOW THE ENGINE WORKS (pipeline)
# ========================================================================
s = slide(); bg(s, PLUM)
kicker(s, "Automatic Literature Ingestion", color=ROSE)
text(s, Inches(0.9), Inches(1.0), Inches(11.5), Inches(0.9),
     [[R("From an ingredient list to a living database", 32, WHITE, True, FONT_H)]])
pipe = [
    ("Parse INCI list", "Split & normalize the raw ingredient declaration into ordered, deduped ingredients.", ROSE),
    ("Resolve compound", "Match each ingredient to a canonical compound — or create it — via INCI + aliases.", ROSE_DK),
    ("Enrich", "Pull INCI properties, PubChem chemical descriptors, and PubMed research articles.", SAGE),
    ("Status & store", "Track enrichment state (complete / partial / review) and persist the linked graph.", GOLD),
]
cw = Inches(2.75); gap = Inches(0.2); x0 = Inches(0.9); y = Inches(2.7)
for i,(t,b,col) in enumerate(pipe):
    x = x0 + i*(cw+gap)
    box(s, x, y, cw, Inches(3.0), RGBColor(0x39,0x5A,0x7C), shape=MSO_SHAPE.ROUNDED_RECTANGLE)
    circ = box(s, x+Inches(0.3), y+Inches(0.3), Inches(0.7), Inches(0.7), col, shape=MSO_SHAPE.OVAL)
    tf = circ.text_frame; p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
    r = p.add_run(); r.text = str(i+1); r.font.size=Pt(26); r.font.bold=True
    r.font.color.rgb = WHITE if col != GOLD else PLUM; r.font.name = FONT_H
    text(s, x+Inches(0.3), y+Inches(1.15), cw-Inches(0.6), Inches(0.7),
         [[R(t, 17, WHITE, True)]])
    text(s, x+Inches(0.3), y+Inches(1.85), cw-Inches(0.6), Inches(1.1),
         [[R(b, 12.5, CREAM)]], line_spacing=1.15)
    if i < 3:
        text(s, x+cw-Inches(0.04), y+Inches(1.1), Inches(0.35), Inches(0.6),
             [[R("›", 26, ROSE, True)]], align=PP_ALIGN.CENTER)
text(s, Inches(0.9), Inches(6.1), Inches(11.5), Inches(0.8),
     [[R("Built today — a Django pipeline (formulation_ingest) that turns any product label into "
         "structured, evidence-linked ingredient data, fully tested.", 14, RGBColor(0xC4,0xDD,0xF0))]],
     align=PP_ALIGN.CENTER, line_spacing=1.15)
page_num(s, 15)

# ========================================================================
# 12 — TECHNOLOGY
# ========================================================================
s = slide(); bg(s, PLUM)
kicker(s, "Under the Hood", color=ROSE)
text(s, Inches(0.9), Inches(1.0), Inches(11), Inches(0.9),
     [[R("The intelligence behind the glow", 36, WHITE, True, FONT_H)]])
tech = [
    ("Vision", "Facial segmentation & dermatological feature detection on-device + cloud."),
    ("Knowledge", "Ingredient graph linking 10k+ products to actives, concerns & conflicts."),
    ("Matching", "Ranking engine scores products against the user's skin profile & avoid-list."),
    ("Reasoning", "LLM generates clear, personalized explanations and routine guidance."),
]
cw = Inches(2.85); gap = Inches(0.2); x0 = Inches(0.9); y = Inches(2.4)
for i,(t,b) in enumerate(tech):
    x = x0 + i*(cw+gap)
    box(s, x, y, cw, Inches(3.2), RGBColor(0x39,0x5A,0x7C), shape=MSO_SHAPE.ROUNDED_RECTANGLE)
    box(s, x+Inches(0.3), y+Inches(0.35), Inches(0.6), Inches(0.12), ROSE)
    text(s, x+Inches(0.3), y+Inches(0.6), cw-Inches(0.6), Inches(0.7),
         [[R(t, 22, WHITE, True, FONT_H)]])
    text(s, x+Inches(0.3), y+Inches(1.45), cw-Inches(0.6), Inches(1.6),
         [[R(b, 14, CREAM)]], line_spacing=1.2)
page_num(s, 16)

# ========================================================================
# 13 — MARKET
# ========================================================================
s = slide(); bg(s, CREAM)
kicker(s, "Market Opportunity")
text(s, Inches(0.9), Inches(1.0), Inches(11), Inches(0.9),
     [[R("A massive market hungry for personalization", 32, PLUM, True, FONT_H)]])
mkt = [("$190B", "Global skincare market", ROSE_DK),
       ("$13B+", "Beauty-tech & diagnostics", SAGE),
       ("28%", "Annual growth in AI beauty", GOLD)]
cw = Inches(3.7); gap = Inches(0.25); x0 = Inches(0.9); y = Inches(2.5)
for i,(big,sub,col) in enumerate(mkt):
    x = x0 + i*(cw+gap)
    box(s, x, y, cw, Inches(2.4), WHITE, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
    box(s, x, y, cw, Inches(0.14), col)
    text(s, x, y+Inches(0.5), cw, Inches(1),
         [[R(big, 54, col, True, FONT_H)]], align=PP_ALIGN.CENTER)
    text(s, x, y+Inches(1.65), cw, Inches(0.6),
         [[R(sub, 15, GREY, True)]], align=PP_ALIGN.CENTER)
text(s, Inches(0.9), Inches(5.4), Inches(11.5), Inches(1.2),
     [[R("Consumers already shop for skincare online and crave guidance. "
         f"{APP} captures intent at the exact moment of decision — turning diagnosis into purchase.", 16, PLUM)]],
     align=PP_ALIGN.CENTER, line_spacing=1.2)
page_num(s, 11)

# ========================================================================
# 12 — BUSINESS MODEL
# ========================================================================
s = slide(); bg(s, PLUM)
kicker(s, "Business Model", color=ROSE)
text(s, Inches(0.9), Inches(1.0), Inches(11), Inches(0.9),
     [[R("Three ways to monetize one selfie", 34, WHITE, True, FONT_H)]])
bm = [("Affiliate & commerce", "Revenue share on recommended products users buy in-app."),
      ("Premium subscription", "Progress tracking, unlimited re-scans, and pro routines."),
      ("Brand partnerships", "Sponsored placement and anonymized skin-trend insights for brands.")]
cw = Inches(3.7); gap = Inches(0.25); x0 = Inches(0.9); y = Inches(2.5)
for i,(t,b) in enumerate(bm):
    x = x0 + i*(cw+gap)
    box(s, x, y, cw, Inches(3), RGBColor(0x39,0x5A,0x7C), shape=MSO_SHAPE.ROUNDED_RECTANGLE)
    text(s, x+Inches(0.35), y+Inches(0.45), cw-Inches(0.7), Inches(0.3),
         [[R(f"0{i+1}", 18, ROSE, True)]])
    text(s, x+Inches(0.35), y+Inches(0.95), cw-Inches(0.7), Inches(0.9),
         [[R(t, 21, WHITE, True, FONT_H)]])
    text(s, x+Inches(0.35), y+Inches(1.8), cw-Inches(0.7), Inches(1),
         [[R(b, 14, CREAM)]], line_spacing=1.2)
page_num(s, 12)

# ========================================================================
# 13 — DIFFERENTIATION
# ========================================================================
s = slide(); bg(s, CREAM)
kicker(s, "Why We Win")
text(s, Inches(0.9), Inches(1.0), Inches(11), Inches(0.9),
     [[R("Diagnosis + sensitivity + commerce — in one flow", 30, PLUM, True, FONT_H)]])
rows = [
    ("Selfie-based diagnosis", True, "Quizzes only"),
    ("Sensitivity-aware filtering", True, "Generic suggestions"),
    ("Per-zone severity mapping", True, "One-size scores"),
    ("Routine order & reasoning", True, "Product lists"),
    ("Progress re-scans over time", True, "No follow-up"),
]
y = Inches(2.4); rh = Inches(0.72)
# headers
text(s, Inches(0.9), y-Inches(0.55), Inches(5), Inches(0.4), [[R("Capability", 14, GREY, True)]])
text(s, Inches(6.9), y-Inches(0.55), Inches(2.5), Inches(0.4), [[R(APP, 14, ROSE_DK, True)]], align=PP_ALIGN.CENTER)
text(s, Inches(9.6), y-Inches(0.55), Inches(3), Inches(0.4), [[R("Typical apps", 14, GREY, True)]], align=PP_ALIGN.CENTER)
for i,(cap, ours, theirs) in enumerate(rows):
    yy = y + i*rh
    if i % 2 == 0:
        box(s, Inches(0.7), yy, Inches(11.9), rh-Inches(0.1), WHITE, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
    text(s, Inches(1.0), yy+Inches(0.12), Inches(5.6), Inches(0.5), [[R(cap, 16, PLUM, True)]])
    text(s, Inches(6.9), yy+Inches(0.1), Inches(2.5), Inches(0.5), [[R("✓", 22, SAGE, True)]], align=PP_ALIGN.CENTER)
    text(s, Inches(9.6), yy+Inches(0.14), Inches(3), Inches(0.5), [[R(theirs, 13, GREY)]], align=PP_ALIGN.CENTER)
page_num(s, 13)

# ========================================================================
# 14 — ROADMAP
# ========================================================================
s = slide(); bg(s, CREAM)
kicker(s, "Roadmap")
text(s, Inches(0.9), Inches(1.0), Inches(11), Inches(0.9),
     [[R("Where we're headed", 36, PLUM, True, FONT_H)]])
phases = [
    ("Now", "Core flow live", "Selfie → analysis → concerns → sensitivities → regimen.", ROSE),
    ("Next", "Tracking & commerce", "Progress re-scans, in-app checkout, restock reminders.", ROSE_DK),
    ("Soon", "Body & brands", "Expand beyond face; brand partner portal & insights.", SAGE),
    ("Future", "Clinical-grade", "Derm partnerships, telehealth referrals, predictive skin health.", GOLD),
]
# timeline line
box(s, Inches(1.0), Inches(3.25), Inches(11.3), Inches(0.06), PLUM)
cw = Inches(2.75); x0 = Inches(0.9)
for i,(when,title,body,col) in enumerate(phases):
    x = x0 + i*Inches(2.95)
    box(s, x+Inches(1.0), Inches(3.05), Inches(0.45), Inches(0.45), col, shape=MSO_SHAPE.OVAL)
    text(s, x, Inches(2.3), cw, Inches(0.5), [[R(when.upper(), 15, col, True)]], align=PP_ALIGN.CENTER)
    box(s, x, Inches(3.8), cw, Inches(2.3), WHITE, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
    text(s, x+Inches(0.25), Inches(4.05), cw-Inches(0.5), Inches(0.6), [[R(title, 18, PLUM, True)]])
    text(s, x+Inches(0.25), Inches(4.7), cw-Inches(0.5), Inches(1.3), [[R(body, 13, GREY)]], line_spacing=1.2)
page_num(s, 14)

# ========================================================================
# 15 — CLOSING / CTA
# ========================================================================
s = slide(); bg(s, PLUM)
box(s, SW - Inches(4), Inches(-1.5), Inches(6), Inches(6), ROSE_DK, shape=MSO_SHAPE.OVAL)
box(s, SW - Inches(3.2), Inches(-0.7), Inches(4.4), Inches(4.4), PLUM, shape=MSO_SHAPE.OVAL)
text(s, Inches(1.0), Inches(2.3), Inches(9), Inches(1.4),
     [[R("Skincare that finally", 40, CREAM, False, FONT_H)],
      [R("knows your skin.", 48, ROSE, True, FONT_H)]], space_after=2)
text(s, Inches(1.05), Inches(4.3), Inches(8), Inches(0.6),
     [[R(f"{APP} — {TAG}", 20, WHITE, True)]])
text(s, Inches(1.05), Inches(5.1), Inches(9), Inches(0.6),
     [[R("Let's build the most personal skincare experience in the world.", 16, CREAM)]])
text(s, Inches(1.05), SH - Inches(0.95), Inches(8), Inches(0.4),
     [[R("weilan@chariotmove.com", 14, ROSE)]])

prs.save("Lume_Skincare_Deck.pptx")
print("Saved Lume_Skincare_Deck.pptx with", len(prs.slides._sldIdLst), "slides")
