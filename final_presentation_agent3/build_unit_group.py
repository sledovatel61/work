# -*- coding: utf-8 -*-
"""
UNIT GROUP — финальная презентация (агент 3).
Рендер 5 слайдов 2400x1350 (16:9) -> PNG -> PDF (13.33"x7.5") + PPTX.
Дизайн-система «Dark Engineering» (агент 2): графит #0A0E14, оранж #FF6B00,
бирюза #22D3EE; шрифты Unbounded / Inter / IBM Plex Mono (кириллица).
Ключевое отличие от версии оркестратора: крупный читаемый текст
(тело >= 26-30 px на 2400px канвасе ~= 11-12 pt на слайде 13,3").
"""
import os, math
from PIL import Image, ImageDraw, ImageFont, ImageFilter

BASE = os.path.dirname(os.path.abspath(__file__))
IMG, FNT = os.path.join(BASE, "img"), os.path.join(BASE, "fonts")
W, H = 2400, 1350

# ---------- палитра ----------
BG      = (10, 14, 20)      # #0A0E14 графит
BG2     = (14, 27, 46)      # #0E1B2E глубокий синий
CARD    = (22, 38, 60)      # #16263C синяя сталь
CARD2   = (17, 30, 48)
LINE    = (30, 52, 80)      # рамки
ORANGE  = (255, 107, 0)     # #FF6B00
ORANGE2 = (255, 140, 50)
CYAN    = (34, 211, 238)    # #22D3EE
GOLD    = (212, 175, 55)
WHITE   = (232, 237, 242)   # #E8EDF2
GREY    = (138, 151, 168)   # #8A97A8
GREY2   = (110, 122, 138)
FAINT   = (86, 98, 114)

# ---------- шрифты ----------
_font_cache = {}
def F(role, size):
    """role: disp800/disp700/disp500 (Unbounded), body400..body700 (Inter),
       mono400/500/600/700 (IBM Plex Mono)."""
    key = (role, size)
    if key in _font_cache: return _font_cache[key]
    if role.startswith("disp"):
        w = {"disp900":900,"disp800":800,"disp700":700,"disp600":600,"disp500":500}[role]
        f = ImageFont.truetype(os.path.join(FNT, "Unbounded[wght].ttf"), size)
        f.set_variation_by_axes([w])
    elif role.startswith("body"):
        w = {"body400":400,"body500":500,"body600":600,"body700":700}[role]
        f = ImageFont.truetype(os.path.join(FNT, "Inter[opsz,wght].ttf"), size)
        f.set_variation_by_axes([28, w])   # opsz 28 для дисплея
    else:
        fn = {"mono300": "IBMPlexMono-Regular.ttf","mono400":"IBMPlexMono-Regular.ttf",
              "mono500":"IBMPlexMono-Medium.ttf","mono600":"IBMPlexMono-SemiBold.ttf",
              "mono700":"IBMPlexMono-Bold.ttf"}[role]
        f = ImageFont.truetype(os.path.join(FNT, fn), size)
    _font_cache[key] = f
    return f

# ---------- примитивы ----------
def canvas():
    im = Image.new("RGB", (W, H), BG)
    return im, ImageDraw.Draw(im)

def vgrad(im, box, c1, c2, alpha=255):
    x0, y0, x1, y1 = box
    ov = Image.new("L", (1, max(1, y1 - y0)))
    for y in range(ov.height):
        ov.putpixel((0, y), int(alpha * (1 - y / max(1, ov.height - 1))))
    ov = ov.resize((x1 - x0, y1 - y0))
    sol = Image.new("RGB", ov.size, c1)
    grad = Image.new("RGB", ov.size, c2)
    m = ov.convert("L")
    band = Image.composite(sol, grad, m)
    im.paste(band, (x0, y0))

def overlay(im, box, color, alpha):
    x0, y0, x1, y1 = box
    ov = Image.new("RGBA", (x1 - x0, y1 - y0), color + (alpha,))
    im.paste(Image.alpha_composite(im.crop(box).convert("RGBA"), ov).convert("RGB"), (x0, y0))

def grid(d, alpha_main=16, alpha_big=30, step=80, big_every=5, color=(120, 160, 200)):
    for x in range(0, W + 1, step):
        a = alpha_big if (x // step) % big_every == 0 else alpha_main
        d.line([(x, 0), (x, H)], fill=color + (a,), width=1)
    for y in range(0, H + 1, step):
        a = alpha_big if (y // step) % big_every == 0 else alpha_main
        d.line([(0, y), (W, y)], fill=color + (a,), width=1)

def corner_marks(d, m=42, l=34, color=CYAN, alpha=130, w=3):
    for cx, cy, dx, dy in [(m, m, 1, 1), (W - m, m, -1, 1), (m, H - m, 1, -1), (W - m, H - m, -1, -1)]:
        d.line([(cx, cy), (cx + dx * l, cy)], fill=color + (alpha,), width=w)
        d.line([(cx, cy), (cx, cy + dy * l)], fill=color + (alpha,), width=w)

def rrect(d, box, r=20, fill=None, outline=None, width=2):
    d.rounded_rectangle(box, radius=r, fill=fill, outline=outline, width=width)

def chip(d, x, y, text, font, fg, bg=None, pad=(18, 9), border=None):
    tw = font.getlength(text)
    asc, desc = font.getmetrics()
    th = asc + desc
    box = (x, y, x + tw + pad[0] * 2, y + th + pad[1] * 2 - 6)
    rrect(d, box, r=(box[3] - box[1]) // 2, fill=bg, outline=border, width=2 if border else 0)
    d.text((x + pad[0], y + pad[1] - 3), text, font=font, fill=fg)
    return box

def wrap(text, font, maxw):
    lines, line = [], ""
    for word in text.split():
        t = (line + " " + word).strip()
        if font.getlength(t) <= maxw: line = t
        else:
            if line: lines.append(line)
            line = word
    if line: lines.append(line)
    return lines

def text_block(d, xy, text, font, fill, maxw=None, lh=None, align="left", max_lines=None):
    """Рисует многострочный текст с переносом; возвращает (высота, линии)."""
    x, y = xy
    asc, desc = font.getmetrics()
    natural = asc + desc
    lh = lh or int(natural * 1.32)
    lines = wrap(text, font, maxw) if maxw else [text]
    if max_lines and len(lines) > max_lines:
        print(f"  [!] overflow: {len(lines)} lines > {max_lines}: {text[:60]}...")
    for ln in lines:
        lx = x
        if align == "center": lx = x + (maxw - font.getlength(ln)) // 2
        d.text((lx, y), ln, font=font, fill=fill)
        y += lh
    return y - xy[1], lines

def glow_text(im, d, xy, text, font, fill, glow=ORANGE, rad=26, alpha=110):
    x, y = xy
    lay = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ld = ImageDraw.Draw(lay)
    ld.text((x, y), text, font=font, fill=glow + (alpha,))
    lay = lay.filter(ImageFilter.GaussianBlur(rad))
    im.paste(Image.alpha_composite(im.convert("RGBA"), lay).convert("RGB"), (0, 0))
    d.text((x, y), text, font=font, fill=fill)

def cover_img(im, path, box, extra_dark=0):
    x0, y0, x1, y1 = box
    bw, bh = x1 - x0, y1 - y0
    pic = Image.open(path).convert("RGB")
    pr, br = pic.width / pic.height, bw / bh
    if pr > br:
        nh = bh; nw = int(bh * pr); off = (nw - bw) // 2; pic = pic.resize((nw, nh)).crop((off, 0, off + bw, bh))
    else:
        nw = bw; nh = int(nw / pr); off = (nh - bh) // 2; pic = pic.resize((nw, nh)).crop((0, off, bw, off + bh))
    im.paste(pic, (x0, y0))
    if extra_dark:
        overlay(im, box, (5, 8, 14), extra_dark)

def stat(d, im, x, y, num, unit, label, numf, labf, numc=ORANGE, labc=GREY, gap=10, unitf=None):
    d.text((x, y), num, font=numf, fill=numc)
    nx = x + numf.getlength(num) + gap
    if unit:
        d.text((nx, y + numf.size - (unitf or numf).size - int(numf.size*0.06)), unit, font=unitf or numf, fill=WHITE)
    asc, desc = labf.getmetrics()
    return y + numf.size + int(numf.size * 1.12)

def header(d, im, kicker, title_lines, sub=None, ky=96, tsize=104, ssize=30):
    """Шапка слайда: кикер-моно + заголовок Unbounded + подзаголовок."""
    d.text((100, ky), kicker, font=F("mono600", 26), fill=ORANGE)
    y = ky + 66
    for ln, col in title_lines:
        text_block(d, (100, y), ln, F("disp800", tsize), col)
        y += int(tsize * 1.28)
    if sub:
        text_block(d, (100, y + 14), sub, F("body500", ssize), GREY, maxw=W - 200, lh=int(ssize*1.4))
        y += int(ssize * 1.4) * len(wrap(sub, F("body500", ssize), W - 200)) + 14
    return y

def footer(d, text_left, page=None):
    d.line([(100, H - 74), (W - 100, H - 74)], fill=LINE + (160,), width=2)
    d.text((100, H - 52), text_left, font=F("mono400", 21), fill=FAINT)
    if page:
        d.text((W - 100 - F("mono400", 21).getlength(page), H - 52), page, font=F("mono400", 21), fill=FAINT)

def arrow_line(d, x0, x1, y, color=ORANGE, w=4):
    d.line([(x0, y), (x1 - 16, y)], fill=color + (230,), width=w)
    d.polygon([(x1, y), (x1 - 20, y - 11), (x1 - 20, y + 11)], fill=color + (230,))

def bg_plain(im, d, glow_spots=True):
    vgrad(im, (0, 0, W, H), BG, BG2)
    grid(d)
    if glow_spots:
        for gx, gy, r, col, a in [(W*0.88, H*0.12, 500, ORANGE, 26), (W*0.10, H*0.95, 560, (20, 80, 140), 40)]:
            lay = Image.new("RGBA", (r*2, r*2), (0,0,0,0))
            ld = ImageDraw.Draw(lay)
            ld.ellipse((r*0.4, r*0.4, r*1.6, r*1.6), fill=col + (a,))
            lay = lay.filter(ImageFilter.GaussianBlur(r*0.5))
            im.paste(Image.alpha_composite(im.crop((int(gx-r), int(gy-r), int(gx+r), int(gy+r))).convert("RGBA"), lay).convert("RGB"), (int(gx-r), int(gy-r)))
    corner_marks(d)

def img_tile(im, d, path, box, caption=None, dark=90, capf=None, tag=None, tagf=None):
    x0, y0, x1, y1 = box
    cover_img(im, path, box, extra_dark=dark)
    d.rounded_rectangle(box, radius=22, outline=LINE + (255,), width=3)
    if tag:
        chip(d, x0 + 22, y0 + 20, tag, tagf or F("mono600", 20), WHITE, bg=(8, 12, 18, 215), border=CYAN + (150,))
    if caption:
        vgrad(im, (x0, y1 - 150, x1, y1), (5, 8, 14), (5, 8, 14), alpha=225)
        text_block(d, (x0 + 24, y1 - 118), caption, capf or F("body600", 26), WHITE, maxw=(x1-x0)-48, max_lines=2)

def bullet_list(d, x, y, items, font, maxw, gap=16, markc=ORANGE, textc=(205, 216, 228), lh_f=1.3):
    for it in items:
        d.text((x, y + int(font.size*0.28)), "▸", font=F("body700", int(font.size*0.86)), fill=markc)
        hgt, _ = text_block(d, (x + int(font.size*1.15), y), it, font, textc, maxw=maxw - int(font.size*1.15), lh=int(font.size*lh_f))
        y += max(hgt, font.size) + gap
    return y

# =====================================================================
# СЛАЙД 1 — ТИТУЛ
# =====================================================================
def slide1():
    im, d = canvas()
    cover_img(im, os.path.join(IMG, "hero_cover.png"), (0, 0, W, H))
    vgrad(im, (0, 0, int(W*0.78), H), BG, (10, 16, 26), alpha=245)
    overlay(im, (0, 0, W, 300), BG, 120)
    overlay(im, (0, H-380, W, H), BG, 200)
    grid(d, alpha_main=10, alpha_big=20)
    corner_marks(d)

    # логотип-строка
    d.rectangle((100, 88, 148, 136), fill=ORANGE)
    d.text((124, 112), "U", font=F("disp900", 34), fill=(10, 14, 20), anchor="mm")
    d.text((170, 96), "UNIT GROUP", font=F("disp700", 40), fill=WHITE)
    d.text((W - 100 - F("mono500", 24).getlength("МОСКВА И МО · 2026"), 104),
           "МОСКВА И МО · 2026", font=F("mono500", 24), fill=GREY)

    # кикер
    chip(d, 100, 300, "ПРОЕКТИРОВАНИЕ · СТРОИТЕЛЬСТВО · ИНЖЕНЕРНЫЕ СИСТЕМЫ · ОТДЕЛКА",
         F("mono500", 24), CYAN, bg=(8, 14, 22, 190), border=CYAN + (90,))

    # слоган
    glow_text(im, d, (96, 396), "ПОЛНЫЙ ЦИКЛ.", F("disp800", 116), WHITE, glow=ORANGE, rad=30, alpha=60)
    glow_text(im, d, (96, 556), "ОДНА ОТВЕТСТВЕННОСТЬ.", F("disp800", 116), ORANGE2, glow=ORANGE, rad=34, alpha=90)
    text_block(d, (100, 752), "От фундамента до космоса: группа из трёх компаний закрывает весь цикл работ — от буронабивной сваи до финишной отделки под ключ.",
               F("body500", 32), (196, 208, 222), maxw=1500, lh=46)

    # нижняя панель статов
    py = H - 320
    overlay(im, (100, py, W - 100, py + 190), CARD, 170)
    d.line([(100, py), (W - 100, py)], fill=ORANGE + (200,), width=5)
    stats = [
        ("3",      "компании",       "единый контрактный контур"),
        ("10+",    "лет",            "спецработы: метро, тоннели"),
        ("288 м",  "",               "НКЦ — флагманский объект"),
        ("24/7",   "",               "работы в любом климате"),
    ]
    cw = (W - 200) / 4
    for i, (num, unit, lab) in enumerate(stats):
        x = 100 + i * cw
        if i: d.line([(x, py + 34), (x, py + 156)], fill=LINE + (220,), width=2)
        d.text((x + 44, py + 30), num, font=F("mono700", 62), fill=ORANGE if i in (0, 2) else WHITE)
        text_block(d, (x + 44, py + 112), lab, F("body500", 24), GREY, maxw=cw - 70, lh=31, max_lines=2)

    footer(d, "ООО «ЮНИТ ИНЖИНИРИНГ»  ·  ООО «АММ-СТРОЙ»  ·  ООО «МОСТЫ И ТОННЕЛИ»", page="01 / 05")
    return im

# =====================================================================
# СЛАЙД 2 — СТРУКТУРА ГРУППЫ
# =====================================================================
def slide2():
    im, d = canvas()
    bg_plain(im, d)
    header(d, im, "01 · СТРУКТУРА ГРУППЫ",
           [("Три компании. Один контур.", WHITE)],
           sub="Каждая компания закрывает свой сегмент, заказчик получает один договор и одну ответственность за весь цикл — от проекта до отделки.")

    cards = [
        dict(role="ГОЛОВНАЯ · ИНЖИНИРИНГ", rolec=ORANGE, name="ЮНИТ\nИНЖИНИРИНГ",
             items=["Проектирование и строительство любой сложности",
                    "Комплекс работ на объекте НКЦ — башня 288 м, 257 000 м²",
                    "Капремонт тоннеля «Новокутузовский» на ТТК",
                    "Стрелковый клуб «Румянцево» — проект и стройка"],
             head="Махадов Ильян Абдурагимович", meta="гендиректор · с 2025 г."),
        dict(role="ОПЕРАЦИОННАЯ · СТРОЙКА", rolec=CYAN, name="АММ-СТРОЙ",
             items=["Отделка «под ключ»: плитка, паркет, ГКЛ, лепнина",
                    "Демонтаж и алмазная резка ж/б любой сложности",
                    "Черновые работы, столярка, двери, плинтусы",
                    "Сантехника, электрика, ОВиК и газоснабжение"],
             head="Михеев Михаил Вахитович", meta="гендиректор · с 05.2026 · команда AIVA"),
        dict(role="СПЕЦПОДРЯД · 10+ ЛЕТ", rolec=GOLD, name="МОСТЫ\nИ ТОННЕЛИ",
             items=["Мосты, тоннели, метрополитен, ИССО",
                    "БНС · БСС · БКС · «стена в грунте» Ø620–1200 мм",
                    "Монолит и гидроизоляция полного цикла",
                    "Собственный парк: Casagrande · Hilti · работа 24/7"],
             head="Хидешели Леван Иванович", meta="гендиректор · оoomit.com"),
    ]
    top, ch_ = 414, 662
    cw = int((W - 200 - 80) // 3)
    for i, c in enumerate(cards):
        x = 100 + i * (cw + 40)
        box = (x, top, x + cw, top + ch_)
        overlay(im, box, CARD2, 210)
        rrect(d, box, r=24, outline=LINE + (255,), width=3)
        d.line([(x + 24, top), (x + 190, top)], fill=c["rolec"] + (240,), width=6)
        chip(d, x + 28, top + 34, c["role"], F("mono600", 21), c["rolec"], bg=(8, 12, 18, 200))
        ny = top + 106
        for ln in c["name"].split("\n"):
            text_block(d, (x + 28, ny), ln, F("disp700", 44), WHITE, max_lines=1)
            ny += 58
        ny += 10
        d.line([(x + 28, ny), (x + cw - 28, ny)], fill=LINE + (200,), width=2)
        ny += 24
        ny = bullet_list(d, x + 28, ny, c["items"], F("body500", 25), cw - 56, gap=15)
        # низ карточки
        by = top + ch_ - 118
        overlay(im, (x + 1, by, x + cw - 1, top + ch_ - 1), (12, 19, 30), 200)
        text_block(d, (x + 28, by + 18), c["head"], F("body600", 25), WHITE, maxw=cw - 56, max_lines=1)
        text_block(d, (x + 28, by + 58), c["meta"], F("mono400", 20), GREY, maxw=cw - 56, max_lines=1)

    # нижняя лента
    ly = top + ch_ + 44
    overlay(im, (100, ly, W - 100, ly + 92), CARD, 190)
    d.line([(100, ly), (W - 100, ly)], fill=ORANGE + (190,), width=4)
    t = "ОДИН ТЕНДЕР  →  ОДИН ДОГОВОР  →  ОДНА ОТВЕТСТВЕННОСТЬ"
    f = F("mono700", 34)
    d.text(((W - f.getlength(t)) / 2, ly + 26), t, font=f, fill=WHITE)

    footer(d, "UNIT GROUP · структура группы", page="02 / 05")
    return im

# =====================================================================
# СЛАЙД 3 — КОМПЕТЕНЦИИ
# =====================================================================
def slide3():
    im, d = canvas()
    bg_plain(im, d)
    header(d, im, "02 · КОМПЕТЕНЦИИ",
           [("Полный цикл. Без стыков.", WHITE)],
           sub="Шесть этапов, которые на рынке обычно делят между 3–5 подрядчиками. У нас их закрывает одна команда, одна смета и одна ответственность.")

    # конвейер 6 этапов
    py = 400
    stages = [
        ("01", "Проектирование", "стадии П и Р, BIM, сметы, надзор"),
        ("02", "Буровые работы", "БНС, БСС, БКС, «стена в грунте»"),
        ("03", "Монолит", "армирование, опалубка, бетонирование"),
        ("04", "Гидроизоляция", "2–4 слоя, металлоизоляция, инъекции"),
        ("05", "Инженерные системы", "ОВиК, вода, газ, электрика"),
        ("06", "Отделка под ключ", "от стяжки до дверей и света"),
    ]
    sw = int((W - 200 - 5 * 26) // 6)
    for i, (n, t, s) in enumerate(stages):
        x = 100 + i * (sw + 26)
        box = (x, py, x + sw, py + 200)
        overlay(im, box, CARD2, 215)
        rrect(d, box, r=18, outline=LINE + (255,), width=2)
        d.line([(x, py), (x + 62, py)], fill=ORANGE + (230,), width=5)
        d.text((x + 22, py + 20), n, font=F("mono700", 34), fill=ORANGE)
        text_block(d, (x + 22, py + 76), t, F("body700", 27), WHITE, maxw=sw - 44, lh=33, max_lines=2)
        text_block(d, (x + 22, py + 146), s, F("body500", 21), GREY, maxw=sw - 44, lh=26, max_lines=2)
        if i < 5:
            d.polygon([(x + sw + 6, py + 100), (x + sw + 20, py + 89), (x + sw + 20, py + 111)], fill=ORANGE + (220,))

    # левый тайл с буровой
    ty, th_ = 660, 480
    lb = (100, ty, 1060, ty + th_)
    assert isinstance(lb[0], int)
    cover_img(im, os.path.join(IMG, "drill_rig.png"), lb, extra_dark=96)
    d.rounded_rectangle(lb, radius=22, outline=LINE + (255,), width=3)
    vgrad(im, (lb[0], lb[3] - 320, lb[2], lb[3]), (5, 8, 14), (5, 8, 14), alpha=235)
    chip(d, lb[0] + 26, lb[1] + 24, "СОБСТВЕННЫЙ ПАРК ТЕХНИКИ", F("mono600", 21), WHITE, bg=(8, 12, 18, 210), border=ORANGE + (160,))
    text_block(d, (lb[0] + 26, lb[3] - 252), "Буровые установки Casagrande и канатная пила Hilti", F("disp700", 40), WHITE, maxw=lb[2]-lb[0]-52, lh=52, max_lines=2)
    text_block(d, (lb[0] + 26, lb[3] - 132), "Свайные работы Ø620–1200 мм в грунтах до 10 группы, в напорных водоносных горизонтах. Мобильные участки работают круглосуточно.",
               F("body500", 24), (190, 202, 216), maxw=lb[2]-lb[0]-52, lh=32, max_lines=3)

    # правые статы 3 шт
    sx, sw2 = 1100, W - 100 - 1100
    sh = int((th_ - 2 * 24) // 3)
    rows = [
        ("291 БКС", "ограждение котлована ЖК — Шмитовский проезд, ЦАО"),
        ("1 000 т", "статические испытания свай — ТПУ «Мичуринский проспект»"),
        ("20 000 м³", "монолит основных конструкций — ст. «Кленовый бульвар», БКЛ"),
    ]
    for i, (num, lab) in enumerate(rows):
        y = ty + i * (sh + 24)
        box = (sx, y, W - 100, y + sh)
        overlay(im, box, CARD2, 215)
        rrect(d, box, r=20, outline=LINE + (255,), width=2)
        d.line([(sx, y), (sx, y + 84)], fill=ORANGE + (220,), width=5)
        d.text((sx + 34, y + 18), num, font=F("mono700", 56), fill=ORANGE)
        text_block(d, (sx + 34, y + 96), lab, F("body500", 24), (198, 210, 224), maxw=sw2 - 68, lh=31, max_lines=2)

    footer(d, "UNIT GROUP · компетенции", page="03 / 05")
    return im

# =====================================================================
# СЛАЙД 4 — ПРОЕКТЫ
# =====================================================================
def slide4():
    im, d = canvas()
    bg_plain(im, d)
    header(d, im, "03 · ПРОЕКТЫ-ДОКАЗАТЕЛЬСТВА",
           [("Там, где нас уже проверили.", WHITE)], tsize=96)

    top = 330
    # левый флагман
    fb = (100, top, 940, top + 760)
    cover_img(im, os.path.join(IMG, "nkz_tower.png"), fb, extra_dark=70)
    d.rounded_rectangle(fb, radius=24, outline=LINE + (255,), width=3)
    chip(d, fb[0] + 26, fb[1] + 24, "ФЛАГМАН · КОСМОС", F("mono600", 22), WHITE, bg=(8, 12, 18, 215), border=ORANGE + (170,))
    vgrad(im, (fb[0], fb[3] - 420, fb[2], fb[3]), (5, 8, 14), (5, 8, 14), alpha=240)
    text_block(d, (fb[0] + 28, fb[3] - 352), "Национальный космический центр", F("disp700", 44), WHITE, maxw=fb[2]-fb[0]-56, lh=56, max_lines=2)
    text_block(d, (fb[0] + 28, fb[3] - 234), "Комплекс работ на объекте совместного проекта Правительства Москвы и «Роскосмоса». Открыт 13.09.2025.",
               F("body500", 24), (196, 208, 222), maxw=fb[2]-fb[0]-56, lh=32, max_lines=3)
    sy = fb[3] - 118
    d.line([(fb[0] + 28, sy - 14), (fb[2] - 28, sy - 14)], fill=LINE + (220,), width=2)
    cols = [("288 м", "47 этажей"), ("257 000", "м² площади"), ("20 000", "раб. мест")]
    cwid = (fb[2] - fb[0] - 56) / 3
    for i, (n, l) in enumerate(cols):
        x = fb[0] + 28 + i * cwid
        d.text((x, sy), n, font=F("mono700", 44), fill=ORANGE)
        text_block(d, (x, sy + 62), l, F("body500", 22), GREY, maxw=cwid - 12, max_lines=1)

    # правая сетка 2x2
    gx0, gx1 = 980, W - 100
    gw, gh = (gx1 - gx0 - 30) / 2, (760 - 30) / 2
    cells = [
        dict(img="metro_build.png", tag="МЕТРО · БКЛ И ТРОИЦКАЯ ЛИНИЯ",
             title="4 станции метро",
             text="Говорово · Столбово · «Кленовый бульвар» (20 000 м³) · вестибюль №1 «Академической», 2025"),
        dict(img="tunnel_road.png", tag="ТОННЕЛИ И ДОРОГИ",
             title="Тоннель в Видном — 300 м",
             text="Секция трассы «ЮЛА» (концессия 86,7 млрд ₽) · капремонт Новокутузовского тоннеля на ТТК"),
        dict(img=None, tag="ГЕОТЕХНИКА · СВАИ",
             title="291 БКС и 238 БНС",
             text="Ограждение котлована на Шмитовском проезде · свайное основание УДС ул. Маршала Шестопалова"),
        dict(img=None, tag="ДЕВЕЛОПМЕНТ · ТПУ",
             title="«Мичуринский проспект», Башня А",
             text="Свайное основание БНС Ø1000–1200 мм и испытания нагрузкой 1 000 т в составе ТПУ"),
    ]
    for i, c in enumerate(cells):
        cx = gx0 + (i % 2) * (gw + 30)
        cy = top + (i // 2) * (gh + 30)
        box = (int(cx), int(cy), int(cx + gw), int(cy + gh))
        overlay(im, box, CARD2, 225)
        if c["img"]:
            cover_img(im, os.path.join(IMG, c["img"]), box, extra_dark=118)
            vgrad(im, (box[0], box[3] - 260, box[2], box[3]), (5, 8, 14), (5, 8, 14), alpha=235)
        rrect(d, box, r=20, outline=LINE + (255,), width=3)
        chip(d, box[0] + 22, box[1] + 20, c["tag"], F("mono600", 19), CYAN, bg=(8, 12, 18, 205))
        text_block(d, (box[0] + 22, box[3] - 168), c["title"], F("body700", 31), WHITE, maxw=gw - 44, lh=39, max_lines=2)
        text_block(d, (box[0] + 22, box[3] - 124), c["text"], F("body500", 21), GREY, maxw=gw - 44, lh=27, max_lines=3)

    footer(d, "Группа выполняла комплекс работ на объектах; генпроектировщик и генподрядчик ряда проектов — иные организации.", page="04 / 05")
    return im

# =====================================================================
# СЛАЙД 5 — КОНТАКТЫ
# =====================================================================
def slide5():
    im, d = canvas()
    cover_img(im, os.path.join(IMG, "hero_cover.png"), (0, 0, W, H))
    overlay(im, (0, 0, W, H), BG, 208)
    grid(d, alpha_main=10, alpha_big=20)
    corner_marks(d)
    header(d, im, "04 · КОНТАКТЫ",
           [("Готовы к диалогу.", WHITE), ("Обсудим ваш объект.", ORANGE2)], tsize=92)
    text_block(d, (100, 418), "Полный цикл. Одна ответственность. От котлована и свай до отделки под ключ — в одном договоре.",
               F("body500", 30), (198, 210, 224), maxw=1560, lh=42)

    top, ch_ = 528, 536
    cw = int((W - 200 - 80) // 3)
    cards = [
        dict(role="ГОЛОВНАЯ · EPC", rolec=ORANGE, name="ООО «ЮНИТ ИНЖИНИРИНГ»",
             rows=[("Гендиректор", "Махадов Ильян Абдурагимович"),
                   ("Телефон", "+7 915 186-66-11 · +7 916 839-40-20"),
                   ("E-mail", "ooo-unit@list.ru"),
                   ("Адрес", "105082, Москва, ул. Б. Почтовая, 26В, стр. 1"),
                   ("ИНН / ОГРН", "9701308826 / 1257700109072")]),
        dict(role="ОПЕРАЦИОННЫЙ КОНТУР", rolec=CYAN, name="ООО «АММ-СТРОЙ»",
             rows=[("Гендиректор", "Михеев Михаил Вахитович"),
                   ("E-mail", "mikheev.mikhail13@mail.ru"),
                   ("Адрес", "117393, Москва, ул. Архитектора Власова, 55"),
                   ("Создана", "04.05.2026 · команда и портфель AIVA"),
                   ("ИНН / ОГРН", "9729419389 / 1267700156052")]),
        dict(role="СПЕЦПОДРЯД · 10+ ЛЕТ", rolec=GOLD, name="ООО «МОСТЫ И ТОННЕЛИ»",
             rows=[("Гендиректор", "Хидешели Леван Иванович"),
                   ("Телефон", "+7 499 148-63-83"),
                   ("Сайт / e-mail", "ooomit.com · info@ooomit.com"),
                   ("Адрес", "140014, МО, Люберцы, ул. Электрификации, 3, стр. 3"),
                   ("ИНН / ОГРН", "5001107429 / 1165001050785")]),
    ]
    for i, c in enumerate(cards):
        x = 100 + i * (cw + 40)
        box = (x, top, x + cw, top + ch_)
        overlay(im, box, CARD2, 215)
        rrect(d, box, r=24, outline=LINE + (255,), width=3)
        d.line([(x + 24, top), (x + 190, top)], fill=c["rolec"] + (240,), width=6)
        chip(d, x + 28, top + 32, c["role"], F("mono600", 20), c["rolec"], bg=(8, 12, 18, 200))
        text_block(d, (x + 28, top + 92), c["name"], F("disp700", 34), WHITE, maxw=cw - 56, lh=44, max_lines=2)
        y = top + 190
        for k, v in c["rows"]:
            d.text((x + 28, y), k.upper(), font=F("mono500", 18), fill=GREY2)
            hgt, _ = text_block(d, (x + 28, y + 26), v, F("body600", 23), (212, 222, 234), maxw=cw - 56, lh=29, max_lines=2)
            y += 26 + 29 * max(1, len(wrap(v, F("body600", 23), cw - 56))) + 8

    footer(d, "«Ваш надёжный партнёр в мире инженерии»  ·  UNIT GROUP, 2026", page="05 / 05")
    return im

# =====================================================================
def main():
    out = os.path.join(BASE, "slides")
    os.makedirs(out, exist_ok=True)
    pages = [slide1(), slide2(), slide3(), slide4(), slide5()]
    paths = []
    for i, p in enumerate(pages, 1):
        fp = os.path.join(out, f"slide{i}.png")
        p.save(fp, optimize=True)
        paths.append(fp)
        print("saved", fp)

    # PDF: страницы 13.33x7.5 inch (960x540 pt) при resolution=180
    pdf_pages = [p.convert("RGB") for p in pages]
    pdf = os.path.join(BASE, "UNIT_GROUP_Презентация.pdf")
    pdf_pages[0].save(pdf, save_all=True, append_images=pdf_pages[1:], resolution=180.0, quality=93)
    print("PDF:", pdf, os.path.getsize(pdf) // 1024, "KB")

    # PPTX 16:9, слайды = полнокадровые изображения
    from pptx import Presentation
    from pptx.util import Emu
    prs = Presentation()
    prs.slide_width, prs.slide_height = Emu(12192000), Emu(6858000)
    blank = prs.slide_layouts[6]
    for fp in paths:
        s = prs.slides.add_slide(blank)
        s.shapes.add_picture(fp, 0, 0, width=Emu(12192000), height=Emu(6858000))
    prs.core_properties.title = "UNIT GROUP — инженерно-строительная группа полного цикла"
    prs.core_properties.author = "UNIT GROUP"
    pptx = os.path.join(BASE, "UNIT_GROUP_Презентация.pptx")
    prs.save(pptx)
    print("PPTX:", pptx, os.path.getsize(pptx) // 1024, "KB")

if __name__ == "__main__":
    main()
