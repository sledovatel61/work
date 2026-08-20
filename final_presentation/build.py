#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Генератор финальной презентации UNIT GROUP.
Рендерит каждый слайд в PNG 1280x720 через Pillow,
затем собирает из них PDF (через img2pdf) и PPTX (с PNG-фоном).
"""

from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

BASE_DIR = Path(__file__).parent
IMG_DIR = BASE_DIR / "img"

# ============== ПАЛИТРА ==============
BG_DEEP = (10, 14, 20)
BG_DEEP_2 = (14, 27, 46)
SURFACE = (22, 38, 60)
LINE = (31, 49, 71)
ORANGE = (255, 107, 0)
CYAN = (34, 211, 238)
GOLD = (212, 175, 55)
TEXT_PRIMARY = (232, 237, 242)
TEXT_SECONDARY = (138, 151, 168)
TEXT_MUTED = (90, 104, 120)

# ============== ШРИФТЫ (DejaVu — поддержка кириллицы) ==============
F_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
F_REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
F_MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
F_MONO_B = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"

FOOTER_Y = 678
SLIDE_H = 720


def make_font(size, bold=False, mono=False):
    if mono and bold:
        return ImageFont.truetype(F_MONO_B, size)
    if mono:
        return ImageFont.truetype(F_MONO, size)
    if bold:
        return ImageFont.truetype(F_BOLD, size)
    return ImageFont.truetype(F_REG, size)


def wrap_to_width(text, fnt, max_w, draw):
    """Перенос строки с заданным шрифтом под max_w в пикселях"""
    words = text.split()
    lines = []
    cur = ""
    for w in words:
        test = (cur + " " + w).strip()
        bbox = draw.textbbox((0, 0), test, font=fnt)
        if bbox[2] - bbox[0] <= max_w:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def fit_wrapped(text, fnt, max_w, max_h_px, draw, lh=1.3):
    """Возвращает текст и max_lines обрезанный под max_h_px (если не влезает, режет с троеточием)"""
    lines = wrap_to_width(text, fnt, max_w, draw)
    bbox = draw.textbbox((0, 0), "Tg", font=fnt)
    line_h = (bbox[3] - bbox[1]) * lh
    max_lines = max(1, int(max_h_px // line_h))
    if len(lines) <= max_lines:
        return lines, max_lines, False
    # Иначе обрезаем
    full = lines[:max_lines]
    # Если последняя строка без троеточия — добавляем «…»
    if max_lines > 0:
        last = full[-1]
        # Отрезаем последние 2 символа и ставим троеточие, чтобы не вылезало за max_w
        while last and draw.textbbox((0, 0), last + "…", font=fnt)[2] - draw.textbbox((0, 0), last, font=fnt)[0] > max_w - 30:
            last = last[:-1]
        full[-1] = last.rstrip() + "…"
    return full, max_lines, True


def draw_wrapped(draw, x, y, text, fnt, color, max_w, lh=1.3):
    """Рисует многострочный текст"""
    lines = wrap_to_width(text, fnt, max_w, draw)
    bbox = draw.textbbox((0, 0), "Tg", font=fnt)
    line_h = (bbox[3] - bbox[1]) * lh
    for i, ln in enumerate(lines):
        draw.text((x, y + i * line_h), ln, font=fnt, fill=color)
    return y + len(lines) * line_h


def slide_chrome(draw, w, num, footer_left, footer_right):
    """Номер слайда и футер"""
    f_num = make_font(28, bold=True, mono=True)
    f_total = make_font(18, mono=True)
    draw.text((w - 100, 40), f"{num:02d}", font=f_num, fill=ORANGE)
    nb = draw.textbbox((0, 0), f"{num:02d}", font=f_num)
    draw.text((w - 100 + (nb[2] - nb[0]) + 8, 50), f"/ 05", font=f_total, fill=TEXT_MUTED)

    draw.line([(60, FOOTER_Y - 8), (w - 60, FOOTER_Y - 8)], fill=LINE, width=1)
    f_f = make_font(13, mono=True)
    draw.text((60, FOOTER_Y + 6), footer_left, font=f_f, fill=TEXT_MUTED)
    nb_r = draw.textbbox((0, 0), footer_right, font=f_f)
    draw.text((w - 60 - (nb_r[2] - nb_r[0]), FOOTER_Y + 6), footer_right, font=f_f, fill=TEXT_MUTED)


def make_gradient_vertical(c1, c2, h):
    """Вертикальный RGBA-градиент"""
    img = Image.new('RGBA', (1, h), (0, 0, 0, 0))
    d = img.load()
    for i in range(h):
        r = i / (h - 1) if h > 1 else 0
        c = tuple(int(c1[j] * (1 - r) + c2[j] * r) for j in range(3)) + (255,)
        d[0, i] = c
    return img.resize((1280, h))


# ============== СЛАЙД 1 — ТИТУЛ ==============

def render_slide_1():
    W, H = 1280, 720
    img = Image.new('RGBA', (W, H), (*BG_DEEP, 255))

    # Загружаем фоновое изображение и применяем затемнения как в CSS
    bg_path = IMG_DIR / "slide1_cover_bg.png"
    if bg_path.exists():
        bg = Image.open(bg_path).convert('RGBA')
        bg = bg.resize((W, H), Image.LANCZOS)
        # Затемнение градиентом сверху
        grad = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        gd = grad.load()
        # Используем BLACK с alpha 215-180 (0.85-0.7)
        for y in range(H):
            ratio = y / H
            alpha = int(217 - 38 * ratio)  # ~85% сверху, ~70% снизу
            for x in range(W):
                gd[x, y] = (10, 14, 20, alpha)
        bg = Image.alpha_composite(bg, grad)
        # Радиальный overlay по правому краю
        rad = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        rd = rad.load()
        cx, cy = int(W * 0.7), int(H * 0.5)
        max_d = max(W, H) * 0.8
        for y in range(H):
            for x in range(W):
                d = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5
                a = min(180, int((d / max_d) ** 1.5 * 180))
                rd[x, y] = (10, 14, 20, a)
        bg = Image.alpha_composite(bg, rad)
        img = bg

    draw = ImageDraw.Draw(img)

    # Тег сверху
    f_tag = make_font(13, bold=True, mono=True)
    draw.line([(60, 95), (110, 95)], fill=CYAN, width=2)
    draw.text((125, 85), "ИНЖЕНЕРНО-СТРОИТЕЛЬНАЯ ГРУППА ПОЛНОГО ЦИКЛА", font=f_tag, fill=CYAN)

    # Логотип
    f_logo = make_font(112, bold=True)
    draw.text((60, 125), "UNIT", font=f_logo, fill=TEXT_PRIMARY)
    nb = draw.textbbox((0, 0), "UNIT", font=f_logo)
    draw.text((60 + (nb[2] - nb[0]) + 10, 125), "GROUP", font=f_logo, fill=ORANGE)

    # Подзаголовок
    f_sub = make_font(17)
    draw.text((60, 260), "Москва · Инжиниринг · Строительство · Мосты и тоннели", font=f_sub, fill=TEXT_SECONDARY)

    # Headline
    f_big = make_font(54, bold=True)
    draw.text((60, 305), "Полный цикл.", font=f_big, fill=TEXT_PRIMARY)
    draw.text((60, 370), "Одна ответственность.", font=f_big, fill=ORANGE)
    f_subtle = make_font(36)
    draw.text((60, 430), "От фундамента до космоса.", font=f_subtle, fill=TEXT_SECONDARY)

    # Описание
    f_desc = make_font(15)
    desc_strong = "Группа из трёх специализированных компаний"
    desc_rest = ", объединённых общим EPC-контуром. Проектируем, строим, монтируем инженерные системы и доводим объекты до финишной отделки — под одну юридическую и финансовую ответственность."
    part1 = desc_strong + ","
    full = part1 + " " + desc_rest
    draw_wrapped(draw, 60, 495, full, f_desc, TEXT_PRIMARY, max_w=900, lh=1.4)

    # Метрики (4 колонки)
    metric_y = 600
    draw.line([(60, metric_y - 15), (W - 60, metric_y - 15)], fill=LINE, width=1)
    draw.line([(60, metric_y + 65), (W - 60, metric_y + 65)], fill=LINE, width=1)

    metrics = [
        ("3", "юрлица", "единый EPC-контур"),
        ("288", "м", "НКЦ Роскосмос · флагман"),
        ("20 000", "м³", "монолит в водонасыщенных грунтах"),
        ("24", "/7", "любая геология и климат"),
    ]
    col_w = (W - 120) / 4
    f_num = make_font(34, bold=True)
    f_unit = make_font(18, bold=True, mono=True)
    f_lbl = make_font(12, bold=True)
    for i, (num, unit, label) in enumerate(metrics):
        cx = 60 + i * col_w
        if i > 0:
            draw.line([(cx, metric_y - 5), (cx, metric_y + 55)], fill=LINE, width=1)
        draw.text((cx + 20, metric_y), num, font=f_num, fill=ORANGE)
        nb = draw.textbbox((0, 0), num, font=f_num)
        draw.text((cx + 20 + (nb[2] - nb[0]) + 6, metric_y + 8), unit, font=f_unit, fill=CYAN)
        draw.text((cx + 20, metric_y + 42), label, font=f_lbl, fill=TEXT_SECONDARY)

    slide_chrome(draw, W, 1, "UNIT GROUP · Москва · 2026", "Единая ответственность EPC-уровня")
    return img


# ============== СЛАЙД 2 — СТРУКТУРА ==============

def render_slide_2():
    W, H = 1280, 720
    img = Image.new('RGBA', (W, H), (*BG_DEEP, 255))
    img = Image.alpha_composite(img, make_gradient_vertical(BG_DEEP, BG_DEEP_2, H))
    draw = ImageDraw.Draw(img)

    f_eb = make_font(13, bold=True, mono=True)
    draw.text((60, 50), "СТРУКТУРА ГРУППЫ", font=f_eb, fill=CYAN)

    f_t1 = make_font(44, bold=True)
    f_t2 = make_font(44, bold=True)
    draw.text((60, 85), "Единый контур.", font=f_t1, fill=TEXT_PRIMARY)
    draw.text((60, 138), "Три уровня экспертизы.", font=f_t2, fill=ORANGE)

    f_sub = make_font(15)
    draw_wrapped(draw, 60, 198,
                 "Каждая компания закрывает свой сегмент. Один договор — и вся цепочка от инженерного проекта до финишной отделки под одной ответственностью.",
                 f_sub, TEXT_SECONDARY, max_w=1100, lh=1.3)

    # 3 строки таблицы
    ROW_X = 60
    ROW_W = W - 120
    ROW_TOP = 280
    ROW_BOTTOM = 615
    ROW_H = (ROW_BOTTOM - ROW_TOP) // 3

    rows_data = [
        {"num": "01", "role": "EPC · УПРАВЛЕНИЕ", "color": ORANGE,
         "name1": "ЮНИТ", "name2": "ИНЖИНИРИНГ",
         "extra": "Головная компания группы · с 2025",
         "caps": [
             "Проектирование, BIM, сметы, авторский надзор",
             "Генподряд, техзаказчик, управление строительством",
             "Комплекс работ на объекте НКЦ — башня 288 м, 47 этажей, 257 000 м²",
             "Проектирование/строительство «Стрелковый клуб Румянцево»",
             "Капремонт тоннеля «Новокутузовский ТТК»",
         ],
         "meta": [
             ("Ген. директор", "Махадов Ильян Абдурагимович"),
             ("ИНН", "9701308826"),
             ("ОГРН", "1257700109072"),
             ("", "105082, Москва, ул. Б. Почтовая, 26В, стр. 1"),
             ("Тел.", "+7 915 186-66-11"),
             ("Тел.", "+7 916 839-40-20"),
             ("E-mail", "ooo-unit@list.ru"),
         ]},
        {"num": "02", "role": "ОПЕРАЦИОННЫЙ КОНТУР", "color": CYAN,
         "name1": "АММ", "name2": "СТРОЙ",
         "extra": "Создана 04.05.2026 · команда и портфель AIVA",
         "caps": [
             "Демонтаж и алмазная резка ж/б любой сложности",
             "Черновые: стяжка, штукатурка, кладка",
             "Отделка под ключ: шпатлёвка, краска, керамогранит, паркет/ламинат",
             "Столярные: двери, МДФ-плинтусы, доборы",
             "Сантехника, электрика, ОВиК — полный цикл",
         ],
         "meta": [
             ("Ген. директор", "Михеев Михаил Вахитович"),
             ("ИНН", "9729419389"),
             ("ОГРН", "1267700156052"),
             ("", "117393, Москва, ул. Архитектора Власова, 55"),
             ("E-mail", "mikheev.mikhail13@mail.ru"),
         ]},
        {"num": "03", "role": "СПЕЦКОНТУР · 10+ ЛЕТ", "color": GOLD,
         "name1": "МОСТЫ", "name2": "И ТОННЕЛИ",
         "extra": "Собственный парк Casagrande · Hilti",
         "caps": [
             "Мосты, тоннели, метрополитен, ИССО — полный цикл",
             "Буровые: БНС, БСС, БКС, «стена в грунте», Ø620–1200 мм, до 10 гр.",
             "Монолит: армирование, опалубка, бетонирование, маркшейдерия",
             "Гидроизоляция полного цикла (2–4 слоя, металлоизоляция, инъектирование)",
             "Работа 24/7, любой климат, высокая мобильность",
         ],
         "meta": [
             ("Ген. директор", "Хидешели Леван Иванович"),
             ("ИНН", "5001107429"),
             ("ОГРН", "1165001050785"),
             ("", "140014, МО, Люберцы, Электрификации 3, стр. 3"),
             ("Тел.", "+7 499 148-63-83"),
             ("E-mail", "info@ooomit.com"),
             ("Сайт", "ooomit.com"),
         ]},
    ]

    # Фон контейнера
    draw.rectangle([(ROW_X, ROW_TOP), (ROW_X + ROW_W, ROW_BOTTOM)],
                   fill=SURFACE)
    draw.rectangle([(ROW_X, ROW_TOP), (ROW_X + ROW_W, ROW_BOTTOM)],
                   outline=LINE, width=1)

    f_num = make_font(16, bold=True)
    f_role = make_font(10, bold=True, mono=True)
    f_name = make_font(22, bold=True)
    f_extra = make_font(11)
    f_cap = make_font(11)
    f_met_l = make_font(9, bold=True, mono=True)
    f_met_v = make_font(10, mono=True)

    for idx, row in enumerate(rows_data):
        ry_top = ROW_TOP + idx * ROW_H
        ry_bot = ry_top + ROW_H

        if idx > 0:
            draw.line([(ROW_X, ry_top), (ROW_X + ROW_W, ry_top)], fill=LINE, width=1)

        # Цветная полоса
        draw.rectangle([(ROW_X + 8, ry_top + 6), (ROW_X + 12, ry_bot - 6)],
                       fill=row["color"])

        # Левая колонка
        col_lx = ROW_X + 30
        draw.text((col_lx, ry_top + 12), row["num"], font=f_num, fill=TEXT_MUTED)
        draw.text((col_lx, ry_top + 32), row["role"], font=f_role, fill=row["color"])
        draw.text((col_lx, ry_top + 50), row["name1"], font=f_name, fill=TEXT_PRIMARY)
        draw.text((col_lx, ry_top + 76), row["name2"], font=f_name, fill=TEXT_PRIMARY)
        # Доп. инфо внизу строки
        draw.text((col_lx, ry_bot - 18), row["extra"], font=f_extra, fill=TEXT_SECONDARY)

        # Средняя колонка
        col_mx = ROW_X + 290
        col_mw = 540
        cap_y = ry_top + 12
        f_plus = make_font(11, bold=True, mono=True)
        for cap in row["caps"]:
            draw.ellipse([(col_mx, cap_y + 3), (col_mx + 13, cap_y + 16)],
                         outline=row["color"], width=1)
            draw.text((col_mx + 4, cap_y + 3), "+", font=f_plus, fill=row["color"])
            cap_lines = wrap_to_width(cap, f_cap, col_mw - 25, draw)
            line_h_local = 14
            for j, line in enumerate(cap_lines):
                draw.text((col_mx + 22, cap_y + j * line_h_local), line, font=f_cap, fill=TEXT_PRIMARY)
            cap_y += line_h_local * len(cap_lines) + 2

        # Правая колонка
        col_rx = ROW_X + 860
        my = ry_top + 12
        for label, val in row["meta"]:
            if label and val:
                draw.text((col_rx, my), label, font=f_met_l, fill=TEXT_MUTED)
                nb = draw.textbbox((0, 0), label, font=f_met_l)
                draw.text((col_rx + nb[2] - nb[0] + 8, my), val, font=f_met_v, fill=TEXT_SECONDARY)
                my += 12
            elif val and not label:
                draw.text((col_rx, my), val, font=f_met_v, fill=TEXT_SECONDARY)
                my += 12

    # Flow внизу
    flow_y = 618
    flow_h = 40
    draw.rectangle([(ROW_X, flow_y), (ROW_X + ROW_W, flow_y + flow_h)],
                   fill=BG_DEEP, outline=ORANGE, width=2)
    f_step = make_font(13, bold=True, mono=True)
    f_arrow = make_font(24, bold=True)
    steps = ["ОДИН ТЕНДЕР", "ОДИН ДОГОВОР", "ОДНА ОТВЕТСТВЕННОСТЬ"]
    step_w = ROW_W / 3
    for i, step in enumerate(steps):
        sx = ROW_X + i * step_w + step_w / 2
        nb = draw.textbbox((0, 0), step, font=f_step)
        draw.text((sx - (nb[2] - nb[0]) / 2, flow_y + 13), step, font=f_step, fill=TEXT_PRIMARY)
        if i < 2:
            ax = ROW_X + (i + 1) * step_w
            draw.text((ax - 10, flow_y + 8), "→", font=f_arrow, fill=ORANGE)

    slide_chrome(draw, W, 2, "UNIT GROUP · Структура", "3 юрлица · 1 EPC-контур")
    return img


# ============== СЛАЙД 3 — КОМПЕТЕНЦИИ ==============

def render_slide_3():
    W, H = 1280, 720
    img = Image.new('RGBA', (W, H), (*BG_DEEP, 255))

    # Изометрия (opacity 0.08 справа)
    iso_path = IMG_DIR / "infrastructure_isometric.png"
    if iso_path.exists():
        iso = Image.open(iso_path).convert('RGBA')
        iso = iso.resize((W, H), Image.LANCZOS)
        layer = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        ld = layer.load()
        for x in range(W):
            if x >= int(W * 0.4):
                for y in range(H):
                    p = iso.getpixel((x, y))
                    if p[3] > 0:
                        ld[x, y] = (p[0], p[1], p[2], 25)
        img = Image.alpha_composite(img, layer)

    draw = ImageDraw.Draw(img)

    f_eb = make_font(13, bold=True, mono=True)
    draw.text((60, 50), "ПОЛНЫЙ ЦИКЛ · ОТ КОТЛОВАНА ДО ФИНИША", font=f_eb, fill=CYAN)

    f_t = make_font(40, bold=True)
    draw.text((60, 85), "Что закрываем.", font=f_t, fill=TEXT_PRIMARY)
    draw.text((60, 135), "Без стыков. Без субподрядчиков.", font=f_t, fill=ORANGE)

    f_sub = make_font(15)
    draw_wrapped(draw, 60, 190,
                 "Шесть направлений, которые в обычной связке раздают 3-5 подрядчикам. У нас — одна команда, одна ответственность, одна смета.",
                 f_sub, TEXT_SECONDARY, max_w=1100, lh=1.3)

    # Bento 3x2
    grid_x = 60
    grid_y = 260
    grid_w = W - 120
    grid_h = 360
    gap = 12
    cell_w = (grid_w - gap * 2) / 3
    cell_h = (grid_h - gap) / 2

    cards = [
        {"icon": "▶", "color": ORANGE, "featured": True,
         "title": "Проектирование и\nEPC-управление",
         "desc": "Проектная и рабочая документация, BIM, сметы, авторский надзор, генподряд.",
         "metric": "257 000 м² · НКЦ"},
        {"icon": "◇", "color": CYAN, "featured": False,
         "title": "Монолит и подземные\nконструкции",
         "desc": "Армирование, опалубка, бетонирование, геодезия. Водонасыщенные грунты.",
         "metric": "20 000 м³ · ст. «Кленовый бульвар»"},
        {"icon": "▶", "color": ORANGE, "featured": False,
         "title": "Мосты · тоннели · метро",
         "desc": "Станции «Говорово», «Кленовый», «Столбово», «Академическая». Тоннели.",
         "metric": "4 станции · 2 тоннеля"},
        {"icon": "◆", "color": GOLD, "featured": False,
         "title": "Буровые работы\nи спецоснования",
         "desc": "БНС Ø1000–1200 мм, БСС, БКС, стена в грунте. Casagrande, Hilti.",
         "metric": "291 БКС · 1000 тн"},
        {"icon": "◇", "color": CYAN, "featured": False,
         "title": "Инженерные системы",
         "desc": "Кондиц., вентиляция, отопление, ВК, газ, электрика. Свои бригады.",
         "metric": "7 направлений · 24/7"},
        {"icon": "▶", "color": ORANGE, "featured": False,
         "title": "Отделка и финиш\n«под ключ»",
         "desc": "Демонтаж → стяжка/штукатурка → паркет/плитка → двери и свет.",
         "metric": "AIVA → АММ-СТРОЙ"},
    ]

    f_icon = make_font(20, bold=True)
    f_title = make_font(14, bold=True)
    f_desc = make_font(11)
    f_num = make_font(10, mono=True)
    f_metric = make_font(11, bold=True, mono=True)

    for i, card in enumerate(cards):
        col = i % 3
        row_idx = i // 3
        cx = grid_x + col * (cell_w + gap)
        cy = grid_y + row_idx * (cell_h + gap)

        # Фон
        if card["featured"]:
            for y_local in range(int(cell_h)):
                ratio = y_local / cell_h
                r = int(SURFACE[0] * (1 - ratio) + BG_DEEP_2[0] * ratio)
                g = int(SURFACE[1] * (1 - ratio) + BG_DEEP_2[1] * ratio)
                b = int(SURFACE[2] * (1 - ratio) + BG_DEEP_2[2] * ratio)
                draw.line([(cx, cy + y_local), (cx + cell_w, cy + y_local)], fill=(r, g, b))
            draw.rectangle([(cx, cy), (cx + cell_w, cy + cell_h)], outline=ORANGE, width=2)
        else:
            draw.rectangle([(cx, cy), (cx + cell_w, cy + cell_h)], fill=SURFACE, outline=LINE, width=1)

        # Номер
        num_str = f"{i+1:02d} / 06"
        nb = draw.textbbox((0, 0), num_str, font=f_num)
        draw.text((cx + cell_w - (nb[2] - nb[0]) - 14, cy + 12), num_str, font=f_num, fill=TEXT_MUTED)

        # Иконка
        icon_box = 32
        icon_x = cx + 16
        icon_y = cy + 48
        draw.rectangle([(icon_x, icon_y), (icon_x + icon_box, icon_y + icon_box)],
                       outline=card["color"], width=2)
        nb_icon = draw.textbbox((0, 0), card["icon"], font=f_icon)
        ix = icon_x + (icon_box - (nb_icon[2] - nb_icon[0])) / 2
        iy = icon_y + (icon_box - (nb_icon[3] - nb_icon[1])) / 2 - 2
        draw.text((ix, iy), card["icon"], font=f_icon, fill=card["color"])

        # Title
        title_x = cx + 16
        title_y = cy + 96
        for line in card["title"].split("\n"):
            draw.text((title_x, title_y), line, font=f_title, fill=TEXT_PRIMARY)
            title_y += 18

        # Desc — вписываем в оставшееся место до метрики
        desc_top = title_y + 4
        # metric находится на cy + cell_h - 20
        metric_h = 20
        max_desc_h = (cy + cell_h - 20) - desc_top - 4  # отступ 4px от метрики
        lines, _max_lines, truncated = fit_wrapped(
            card["desc"], f_desc, cell_w - 32, max_desc_h, draw, lh=1.3)
        line_h_calc = (draw.textbbox((0, 0), "Tg", font=f_desc)[3] -
                       draw.textbbox((0, 0), "Tg", font=f_desc)[1]) * 1.3
        for j, ln in enumerate(lines):
            draw.text((title_x, desc_top + j * line_h_calc), ln, font=f_desc, fill=TEXT_SECONDARY)

        # Metric — фиксированно внизу карточки
        metric_y = cy + cell_h - 22
        draw.text((title_x, metric_y), card["metric"], font=f_metric, fill=card["color"])

    slide_chrome(draw, W, 3, "UNIT GROUP · Компетенции", "6 направлений · 1 ответственный")
    return img


# ============== СЛАЙД 4 — ПРОЕКТЫ ==============

def render_slide_4():
    W, H = 1280, 720
    img = Image.new('RGBA', (W, H), (*BG_DEEP, 255))
    img = Image.alpha_composite(img, make_gradient_vertical(BG_DEEP, BG_DEEP_2, H))
    draw = ImageDraw.Draw(img)

    f_eb = make_font(13, bold=True, mono=True)
    draw.text((60, 50), "ПРОЕКТЫ-ДОКАЗАТЕЛЬСТВА", font=f_eb, fill=CYAN)

    f_t = make_font(44, bold=True)
    draw.text((60, 85), "Там, где нас уже", font=f_t, fill=TEXT_PRIMARY)
    draw.text((60, 138), "проверили.", font=f_t, fill=ORANGE)

    f_sub = make_font(15)
    draw_wrapped(draw, 60, 198,
                 "Не стоковые фотографии — реальные объекты Роскосмоса, Московского метрополитена, ЦАО и крупнейших девелоперов столицы.",
                 f_sub, TEXT_SECONDARY, max_w=1100, lh=1.3)

    grid_y = 280
    grid_h = 340
    total_w = W - 120
    gap = 12
    hero_w = total_w * 0.42
    small_w = (total_w - hero_w - gap) / 2
    small_h = (grid_h - gap) / 2

    # HERO
    hero_x = 60
    hero_y = grid_y
    for y_local in range(grid_h):
        ratio = y_local / grid_h
        r = int(SURFACE[0] * (1 - ratio) + BG_DEEP_2[0] * ratio)
        g = int(SURFACE[1] * (1 - ratio) + BG_DEEP_2[1] * ratio)
        b = int(SURFACE[2] * (1 - ratio) + BG_DEEP_2[2] * ratio)
        draw.line([(hero_x, hero_y + y_local), (hero_x + hero_w, hero_y + y_local)], fill=(r, g, b))
    draw.rectangle([(hero_x, hero_y), (hero_x + hero_w, hero_y + grid_h)], outline=ORANGE, width=2)

    # Простой glow — одиночный софт-оранжевый круг
    radial_x = hero_x + hero_w - 80
    radial_y = hero_y + 60
    for r in range(60, 0, -2):
        draw.ellipse([(radial_x - r, radial_y - r),
                      (radial_x + r, radial_y + r)],
                     outline=(255, 107, 0))

    f_hero_type = make_font(10, bold=True, mono=True)
    f_hero_name = make_font(24, bold=True)
    f_hero_desc = make_font(12)
    f_hero_val = make_font(32, bold=True)
    f_hero_lbl = make_font(9, bold=True, mono=True)

    draw.text((hero_x + 24, hero_y + 20), "◤ ФЛАГМАН · КОСМОС", font=f_hero_type, fill=ORANGE)
    draw.text((hero_x + 24, hero_y + 42), "Национальный космический", font=f_hero_name, fill=TEXT_PRIMARY)
    draw.text((hero_x + 24, hero_y + 70), "центр", font=f_hero_name, fill=TEXT_PRIMARY)

    desc = "Комплекс работ на объекте совместного проекта Правительства Москвы и Роскосмоса. Башня-«ракета» — главный архитектурный объект столицы. Открыт 13.09.2025."
    draw_wrapped(draw, hero_x + 24, hero_y + 108, desc, f_hero_desc, TEXT_SECONDARY,
                 max_w=hero_w - 48, lh=1.4)

    metrics = [("288", "м / 47 эт."), ("257к", "м² площадь"), ("20к", "рабочих мест")]
    mw = (hero_w - 48) / 3
    base_y = hero_y + grid_h - 75
    for i, (val, lbl) in enumerate(metrics):
        mx = hero_x + 24 + i * mw
        draw.text((mx, base_y), val, font=f_hero_val, fill=ORANGE)
        draw.text((mx, base_y + 42), lbl, font=f_hero_lbl, fill=TEXT_MUTED)

    # 4 small cards
    small_cards = [
        {"tag": "◤ МЕТРО · БКЛ",
         "name": "Станция «Кленовый бульвар»",
         "desc": "Сооружение основных конструкций в условиях водонасыщенных грунтов, река в 50 м.",
         "metrics": [("20к", "м³ монолита")]},
        {"tag": "◤ МЕТРО · ТРОИЦКАЯ",
         "name": "Вестибюль №1 ст. «Академическая»",
         "desc": "Возведение основных и внутренних конструкций. Открытие — 13.09.2025.",
         "metrics": [("17", "станций Троицкой линии")]},
        {"tag": "◤ ТРАНСПОРТ · ГЧП",
         "name": "Тоннель в г. Видное",
         "desc": "Секция 7 в составе трассы «ЮЛА» — концессия 86,7 млрд ₽.",
         "metrics": [("300", "м тоннель")]},
        {"tag": "◤ ДЕВЕЛОПМЕНТ · ТПУ",
         "name": "МФЖК «Мичуринский проспект»",
         "desc": "Свайное основание Башни А. Статические испытания 1000 тн.",
         "metrics": [("1000т", "испытания свай")]},
    ]

    f_sm_type = make_font(10, bold=True, mono=True)
    f_sm_name = make_font(15, bold=True)
    f_sm_desc = make_font(10)
    f_sm_val = make_font(20, bold=True)
    f_sm_lbl = make_font(9, bold=True, mono=True)

    for i, card in enumerate(small_cards):
        col = i % 2
        row_idx = i // 2
        cx = 60 + hero_w + gap + col * (small_w + gap)
        cy = grid_y + row_idx * (small_h + gap)
        draw.rectangle([(cx, cy), (cx + small_w, cy + small_h)], fill=SURFACE, outline=LINE, width=1)

        draw.text((cx + 16, cy + 16), card["tag"], font=f_sm_type, fill=CYAN)
        name_y = cy + 36
        name_lines = wrap_to_width(card["name"], f_sm_name, small_w - 32, draw)
        for line in name_lines[:2]:
            draw.text((cx + 16, name_y), line, font=f_sm_name, fill=TEXT_PRIMARY)
            name_y += 18
        desc_lines = wrap_to_width(card["desc"], f_sm_desc, small_w - 32, draw)
        for j, line in enumerate(desc_lines[:3]):
            draw.text((cx + 16, name_y + 4 + j * 13), line, font=f_sm_desc, fill=TEXT_SECONDARY)
        for j, (val, lbl) in enumerate(card["metrics"]):
            my = cy + small_h - 38
            draw.text((cx + 16, my), val, font=f_sm_val, fill=ORANGE)
            draw.text((cx + 16, my + 22), lbl, font=f_sm_lbl, fill=TEXT_MUTED)

    # Footer line items
    foot_items = [("12+", "знаковых объектов"), ("2", "линии метро"),
                  ("3", "тоннеля"), ("1", "объект Роскосмоса"),
                  ("10+", "лет практики")]
    foot_y = grid_y + grid_h + 22
    f_foot_v = make_font(13, bold=True)
    f_foot_l = make_font(11)
    fx = 60
    for val, lbl in foot_items:
        draw.ellipse([(fx + 3, foot_y + 8), (fx + 11, foot_y + 16)], fill=ORANGE)
        draw.text((fx + 18, foot_y + 4), val, font=f_foot_v, fill=ORANGE)
        nb_v = draw.textbbox((0, 0), val, font=f_foot_v)
        draw.text((fx + 18 + nb_v[2] - nb_v[0] + 8, foot_y + 6), lbl, font=f_foot_l, fill=TEXT_SECONDARY)
        nb_l = draw.textbbox((0, 0), lbl, font=f_foot_l)
        fx += 18 + nb_v[2] - nb_v[0] + nb_l[2] - nb_l[0] + 30

    slide_chrome(draw, W, 4, "UNIT GROUP · Проекты", "Москва · МО · 2018–2026")
    return img


# ============== СЛАЙД 5 — КОНТАКТЫ ==============

def render_slide_5():
    W, H = 1280, 720
    img = Image.new('RGBA', (W, H), (*BG_DEEP, 255))

    bg_path = IMG_DIR / "contacts_bg.png"
    if bg_path.exists():
        bg = Image.open(bg_path).convert('RGBA')
        bg = bg.resize((W, H), Image.LANCZOS)
        overlay = Image.new('RGBA', (W, H), (*BG_DEEP, 220))
        bg = Image.alpha_composite(bg, overlay)
        img = bg

    # Градиент снизу
    grad = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    gd = grad.load()
    for y in range(H):
        for x in range(W):
            ratio = (y / H) ** 2
            a = int(80 * ratio)
            gd[x, y] = (10, 14, 20, a)
    img = Image.alpha_composite(img, grad)

    # Оранжевый горизонт
    horizon = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    hd = horizon.load()
    horizon_y = int(H * 0.55)
    for y in range(horizon_y - 1, horizon_y + 2):
        for x in range(W):
            hd[x, y] = (255, 107, 0, 180)
    img = Image.alpha_composite(img, horizon)

    # Wireframe
    wire = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    wp = wire.load()
    for t in range(20):
        for s in range(80):
            x_start = 50 + t * 8
            x_end = x_start + s * 5
            y_end = s * 8
            if y_end >= horizon_y:
                break
            if 0 <= x_end < W:
                wp[x_end, y_end] = (34, 211, 238, 50)
    img = Image.alpha_composite(img, wire)

    draw = ImageDraw.Draw(img)

    f_h1 = make_font(54, bold=True)
    f_h2 = make_font(54, bold=True)
    draw.text((60, 50), "Снимите риски.", font=f_h1, fill=TEXT_PRIMARY)
    draw.text((60, 115), "Дайте площадку.", font=f_h2, fill=ORANGE)

    f_tag = make_font(16)
    draw_wrapped(draw, 60, 195,
                 "Один тендер → один договор → одна юридическая и финансовая ответственность. Собственная техника, мобильность, выход на объект от 3 дней.",
                 f_tag, TEXT_SECONDARY, max_w=1100, lh=1.3)

    # CTA
    cta_y = 285
    draw.rectangle([(60, cta_y), (60 + 380, cta_y + 56)], fill=ORANGE)
    f_cta = make_font(17, bold=True)
    cta_text = "Готовы к диалогу"
    nb = draw.textbbox((0, 0), cta_text, font=f_cta)
    draw.text((82, cta_y + 20), cta_text, font=f_cta, fill=BG_DEEP)
    draw.text((82 + nb[2] - nb[0] + 36, cta_y + 12), "→", font=make_font(26, bold=True), fill=BG_DEEP)

    # Contacts
    contacts_top = 420
    draw.line([(60, contacts_top - 16), (W - 60, contacts_top - 16)], fill=LINE, width=1)

    contacts = [
        {"tag": "◤ EPC · ГОЛОВНАЯ", "color": ORANGE,
         "name1": "ООО «ЮНИТ", "name2": "ИНЖИНИРИНГ»",
         "role": "Генеральный директор",
         "director": "Махадов Ильян Абдурагимович",
         "address": "105082, Москва, ул. Большая Почтовая, д. 26В, стр. 1, пом. 1/3",
         "phones": ["+7 915 186-66-11", "+7 916 839-40-20"],
         "email": "ooo-unit@list.ru", "site": None,
         "inn": "9701308826", "ogrn": "1257700109072", "extra": None},
        {"tag": "◤ ОПЕРАЦИОННЫЙ КОНТУР", "color": CYAN,
         "name1": "ООО «АММ", "name2": "СТРОЙ»",
         "role": "Генеральный директор",
         "director": "Михеев Михаил Вахитович",
         "address": "117393, Москва, ул. Архитектора Власова, д. 55",
         "phones": [],
         "email": "mikheev.mikhail13@mail.ru", "site": None,
         "inn": "9729419389", "ogrn": "1267700156052", "extra": "Создана 04.05.2026"},
        {"tag": "◤ СПЕЦКОНТУР · 10+ ЛЕТ", "color": GOLD,
         "name1": "ООО «МОСТЫ", "name2": "И ТОННЕЛИ»",
         "role": "Генеральный директор",
         "director": "Хидешели Леван Иванович",
         "address": "140014, МО, г. Люберцы, ул. Электрификации, д. 3, стр. 3, оф. 12",
         "phones": ["+7 499 148-63-83"],
         "email": "info@ooomit.com", "site": "ooomit.com",
         "inn": "5001107429", "ogrn": "1165001050785", "extra": None},
    ]

    contacts_bot = 645
    draw.line([(60, contacts_bot + 8), (W - 60, contacts_bot + 8)], fill=LINE, width=1)

    col_w = (W - 120) / 3
    f_tag_c = make_font(10, bold=True, mono=True)
    f_name_c = make_font(14, bold=True)
    f_role = make_font(9, bold=True, mono=True)
    f_dir = make_font(11, bold=True)
    f_addr = make_font(10)
    f_contact = make_font(10, mono=True)
    f_requi = make_font(9, mono=True)

    for i, contact in enumerate(contacts):
        cx = 60 + i * col_w
        if i < 2:
            draw.line([(cx + col_w, contacts_top - 12),
                       (cx + col_w, contacts_bot + 4)], fill=LINE, width=1)

        cur_y = contacts_top
        draw.text((cx + 24, cur_y), contact["tag"], font=f_tag_c, fill=contact["color"])
        cur_y += 16
        draw.text((cx + 24, cur_y), contact["name1"], font=f_name_c, fill=TEXT_PRIMARY)
        cur_y += 19
        draw.text((cx + 24, cur_y), contact["name2"], font=f_name_c, fill=TEXT_PRIMARY)
        cur_y += 20
        draw.text((cx + 24, cur_y), contact["role"], font=f_role, fill=TEXT_MUTED)
        cur_y += 13
        draw.text((cx + 24, cur_y), contact["director"], font=f_dir, fill=TEXT_PRIMARY)
        cur_y += 15
        addr_lines = wrap_to_width(contact["address"], f_addr, col_w - 48, draw)
        for line in addr_lines[:2]:
            draw.text((cx + 24, cur_y), line, font=f_addr, fill=TEXT_SECONDARY)
            cur_y += 12
        cur_y += 3
        for phone in contact["phones"]:
            draw.text((cx + 24, cur_y), phone, font=f_contact, fill=contact["color"])
            cur_y += 13
        if contact["email"]:
            draw.text((cx + 24, cur_y), contact["email"], font=f_contact, fill=contact["color"])
            cur_y += 13
        if contact["site"]:
            draw.text((cx + 24, cur_y), contact["site"], font=f_contact, fill=contact["color"])
            cur_y += 13
        if contact["extra"]:
            draw.text((cx + 24, cur_y), contact["extra"], font=f_requi, fill=TEXT_MUTED)
            cur_y += 12
        cur_y += 4
        draw.text((cx + 24, cur_y), f"ИНН {contact['inn']}", font=f_requi, fill=TEXT_MUTED)
        cur_y += 11
        draw.text((cx + 24, cur_y), f"ОГРН {contact['ogrn']}", font=f_requi, fill=TEXT_MUTED)

    # Hashtags
    tag_y = contacts_bot + 16
    hashtags = ["#ПолныйЦиклСтроительства", "#МостыТоннелиМетро", "#КосмическийМасштаб",
                "#СобственныйПаркCasagrande", "#МонолитВВоде", "#ОдинДоговорВместоПяти", "#МоскваиМО"]
    f_hash = make_font(10, mono=True)
    hx = 60
    for tag in hashtags:
        nb = draw.textbbox((0, 0), tag, font=f_hash)
        draw.text((hx, tag_y), tag, font=f_hash, fill=CYAN)
        hx += nb[2] - nb[0] + 16

    slide_chrome(draw, W, 5, "UNIT GROUP · Контакты", "3 юрлица · 1 EPC-контур")
    return img


# ============== MAIN ==============

def main():
    print("=" * 60)
    print("Генератор UNIT GROUP — финальный рендер")
    print("=" * 60)

    png_dir = BASE_DIR / "render_png"
    png_dir.mkdir(exist_ok=True)

    slides = [
        ("slide1.png", render_slide_1()),
        ("slide2.png", render_slide_2()),
        ("slide3.png", render_slide_3()),
        ("slide4.png", render_slide_4()),
        ("slide5.png", render_slide_5()),
    ]

    for name, img in slides:
        out = png_dir / name
        final = Image.new('RGB', img.size, BG_DEEP)
        final.paste(img, mask=img.split()[3] if img.mode == 'RGBA' else None)
        final.save(out, "PNG", optimize=True)
        print(f"  ✓ {name} ({out.stat().st_size // 1024} KB)")

    # PDF
    print()
    print("Сборка PDF...")
    import img2pdf
    pdf_path = BASE_DIR / "UNIT_GROUP_Presentation.pdf"
    layout = img2pdf.get_layout_fun(pagesize=(img2pdf.in_to_pt(13.333), img2pdf.in_to_pt(7.5)))
    with open(pdf_path, "wb") as f:
        f.write(img2pdf.convert(
            [str(png_dir / s[0]) for s in slides],
            title="UNIT GROUP — Презентация Группы Компаний",
            author="UNIT GROUP",
            creator="UNIT GROUP",
            layout_fun=layout))
    print(f"  ✓ {pdf_path.name} ({pdf_path.stat().st_size // 1024} KB)")

    # PPTX
    print()
    print("Сборка PPTX...")
    from pptx import Presentation
    from pptx.util import Emu
    prs = Presentation()
    prs.slide_width = Emu(1280 * 9525)
    prs.slide_height = Emu(720 * 9525)
    for name, _ in slides:
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        slide.shapes.add_picture(str(png_dir / name), 0, 0,
                                 width=prs.slide_width, height=prs.slide_height)
    pptx_path = BASE_DIR / "UNIT_GROUP_Presentation.pptx"
    prs.save(str(pptx_path))
    print(f"  ✓ {pptx_path.name} ({pptx_path.stat().st_size // 1024} KB)")

    print()
    print("=" * 60)
    print("✅ Готово!")
    print("=" * 60)


if __name__ == "__main__":
    main()
