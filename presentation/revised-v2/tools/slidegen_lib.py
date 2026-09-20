# -*- coding: utf-8 -*-
"""Slide XML builders in the deck's existing idiom (Poppins, light theme)."""

W, H = 18288000, 10287000
L, R = 1047750, 17240250
CW = R - L

INK   = "191A18"
BODY  = "5A5D59"
MUTE  = "8B8378"
BRASS = "9B712B"
BLUE  = "326B8C"
CRIT  = "A44B3C"
OKG   = "46683F"
CARD  = "FBF9F3"
EDGE  = "DFD8C6"
SHDW  = "BFB49A"
BG    = "F7F4EC"
PANEL = "F1ECE0"

FONT = "Poppins"
ADV  = {0: 0.578, 1: 0.605}          # average advance in em
EMU_PT = 12700

_id = [100]
def nid():
    _id[0] += 1
    return _id[0]

def esc(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))

def chars_per_line(w, sz, b):
    return max(1, int(w / (sz / 100.0 * EMU_PT * ADV[1 if b else 0])))

def wrapped(text, w, sz, b):
    """Number of visual lines this text needs in a box of width w."""
    cpl = chars_per_line(w, sz, b)
    lines, cur = 0, ""
    for word in text.split():
        cand = word if not cur else cur + " " + word
        if len(cand) <= cpl:
            cur = cand
        else:
            lines += 1
            cur = word
    return max(1, lines + (1 if cur else 0))

def height_of(paras, w, lnspc=1.18, gap=0):
    tot = 0
    for p in paras:
        t, sz, b = p[0], p[1], p[2]
        tot += wrapped(t, w, sz, b) * sz / 100.0 * EMU_PT * lnspc + gap
    return int(tot)

def fits(paras, w, h, label, lnspc=1.18, gap=0):
    need = height_of(paras, w, lnspc, gap)
    if need > h:
        raise SystemExit("OVERFLOW %s: needs %d, has %d" % (label, need, h))
    return True

def run(t, sz, b, color, font=FONT):
    return ('<a:r><a:rPr lang="en-US" sz="%d" b="%d" dirty="0"><a:solidFill>'
            '<a:srgbClr val="%s"/></a:solidFill><a:latin typeface="%s"/>'
            '<a:ea typeface="%s"/><a:cs typeface="%s"/></a:rPr>'
            '<a:t>%s</a:t></a:r>' % (sz, 1 if b else 0, color, font, font, font, esc(t)))

def para(runs, algn="l", lnspc=118, spc_before=0):
    pre = '<a:lnSpc><a:spcPct val="%d000"/></a:lnSpc>' % lnspc if lnspc else ""
    if spc_before:
        pre += '<a:spcBef><a:spcPts val="%d"/></a:spcBef>' % spc_before
    return '<a:p><a:pPr algn="%s">%s</a:pPr>%s</a:p>' % (algn, pre, "".join(runs))

def tb(x, y, w, h, paras, anchor="t", name=None):
    """Text box. paras = list of XML paragraph strings."""
    nm = esc(name or "Text")
    return ('<p:sp><p:nvSpPr><p:cNvPr id="%d" name="%s"/><p:cNvSpPr txBox="1"/>'
            '<p:nvPr/></p:nvSpPr><p:spPr><a:xfrm><a:off x="%d" y="%d"/>'
            '<a:ext cx="%d" cy="%d"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/>'
            '</a:prstGeom><a:noFill/><a:ln><a:noFill/></a:ln></p:spPr><p:txBody>'
            '<a:bodyPr wrap="square" lIns="0" tIns="0" rIns="0" bIns="0" rtlCol="0" '
            'anchor="%s"><a:noAutofit/></a:bodyPr><a:lstStyle/>%s</p:txBody></p:sp>'
            % (nid(), nm, x, y, w, h, anchor, "".join(paras)))

def simple(x, y, w, h, text, sz, b, color, algn="l", anchor="t", lnspc=118, name=None):
    return tb(x, y, w, h, [para([run(text, sz, b, color)], algn, lnspc)],
              anchor, name or text[:40])

def card(x, y, w, h, fill=CARD, stroke=EDGE, lw=12700, radius=4467, shadow=True):
    eff = ('<a:effectLst><a:outerShdw blurRad="114300" dist="25400" dir="5400000" '
           'algn="bl" rotWithShape="0"><a:srgbClr val="%s"><a:alpha val="30000"/>'
           '</a:srgbClr></a:outerShdw></a:effectLst>' % SHDW) if shadow else '<a:effectLst/>'
    ln = ('<a:ln w="%d"><a:solidFill><a:srgbClr val="%s"/></a:solidFill>'
          '<a:prstDash val="solid"/></a:ln>' % (lw, stroke)) if stroke else '<a:ln><a:noFill/></a:ln>'
    return ('<p:sp><p:nvSpPr><p:cNvPr id="%d" name="card"/><p:cNvSpPr/><p:nvPr/>'
            '</p:nvSpPr><p:spPr><a:xfrm><a:off x="%d" y="%d"/><a:ext cx="%d" cy="%d"/>'
            '</a:xfrm><a:prstGeom prst="roundRect"><a:avLst><a:gd name="adj" fmla="val %d"/>'
            '</a:avLst></a:prstGeom><a:solidFill><a:srgbClr val="%s"/></a:solidFill>%s%s'
            '</p:spPr><p:txBody><a:bodyPr/><a:lstStyle/><a:p><a:endParaRPr lang="en-US"/>'
            '</a:p></p:txBody></p:sp>' % (nid(), x, y, w, h, radius, fill, ln, eff))

def rect(x, y, w, h, fill, radius=None):
    geom = ('<a:prstGeom prst="roundRect"><a:avLst><a:gd name="adj" fmla="val %d"/>'
            '</a:avLst></a:prstGeom>' % radius) if radius else '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom>'
    return ('<p:sp><p:nvSpPr><p:cNvPr id="%d" name="bar"/><p:cNvSpPr/><p:nvPr/>'
            '</p:nvSpPr><p:spPr><a:xfrm><a:off x="%d" y="%d"/><a:ext cx="%d" cy="%d"/>'
            '</a:xfrm>%s<a:solidFill><a:srgbClr val="%s"/></a:solidFill>'
            '<a:ln><a:noFill/></a:ln><a:effectLst/></p:spPr><p:txBody><a:bodyPr/>'
            '<a:lstStyle/><a:p><a:endParaRPr lang="en-US"/></a:p></p:txBody></p:sp>'
            % (nid(), x, y, w, h, geom, fill))

def rule(x, y, w, color=EDGE, h=12700):
    return rect(x, y, w, h, color)

def pill(x, y, text, color, sz=1500, padx=150000, h=390000):
    w = int(len(text) * sz / 100.0 * EMU_PT * 0.66) + 2 * padx
    s = rect(x, y, w, h, color, radius=50000)
    s += tb(x, y, w, h, [para([run(text, sz, 1, "FFFFFF")], "ctr", 100)], "ctr", "pill")
    return s, w

def arrow(x, y, w, color=BRASS):
    return ('<p:cxnSp><p:nvCxnSpPr><p:cNvPr id="%d" name="arrow"/><p:cNvCxnSpPr/>'
            '<p:nvPr/></p:nvCxnSpPr><p:spPr><a:xfrm><a:off x="%d" y="%d"/>'
            '<a:ext cx="%d" cy="0"/></a:xfrm><a:prstGeom prst="straightConnector1">'
            '<a:avLst/></a:prstGeom><a:ln w="19050"><a:solidFill><a:srgbClr val="%s"/>'
            '</a:solidFill><a:tailEnd type="triangle" w="med" len="med"/></a:ln>'
            '</p:spPr></p:cxnSp>' % (nid(), x, y, w, color))

def pic(rid, x, y, w, h, name="Logo"):
    return ('<p:pic><p:nvPicPr><p:cNvPr id="%d" name="%s"/><p:cNvPicPr/><p:nvPr/>'
            '</p:nvPicPr><p:blipFill><a:blip r:embed="%s"/><a:stretch><a:fillRect/>'
            '</a:stretch></p:blipFill><p:spPr><a:xfrm><a:off x="%d" y="%d"/>'
            '<a:ext cx="%d" cy="%d"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/>'
            '</a:prstGeom></p:spPr></p:pic>' % (nid(), name, rid, x, y, w, h))

TITLE_Y, TITLE_H = 742950, 1238250
SUB_Y,  SUB_H    = 2028825, 1000125
FOOT_Y, FOOT_H   = 9486900, 476250

def header(title, subtitle):
    fits([(title, 5400, 1)], 16287750, TITLE_H, "title:" + title)
    fits([(subtitle, 2625, 0)], CW, SUB_H, "sub:" + subtitle)
    return (simple(1000125, TITLE_Y, 16287750, TITLE_H, title, 5400, 1, INK, name=title)
            + simple(L, SUB_Y, CW, SUB_H, subtitle, 2625, 0, BODY, name=subtitle[:40]))

def footer(text):
    return simple(L, FOOT_Y, CW, FOOT_H, text, 1875, 0, BODY, name="footnote")

def slide(shapes):
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\r\n'
            '<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
            'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
            '<p:cSld><p:bg><p:bgPr><a:solidFill><a:srgbClr val="%s"/></a:solidFill>'
            '<a:effectLst/></p:bgPr></p:bg><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/>'
            '<p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr><a:xfrm>'
            '<a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/>'
            '<a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>%s</p:spTree></p:cSld>'
            '<p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sld>' % (BG, "".join(shapes)))
