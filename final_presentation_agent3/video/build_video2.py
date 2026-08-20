# -*- coding: utf-8 -*-
"""
UNIT GROUP — видео v2: анимации, синхронизированные с диктором.

Вместо зума с обрезкой (Ken Burns) каждый слайд разобран на слои
(диф-рендер вёрстки). Объекты ВСПЛЫВАЮТ и НЕОНОВО ПОДСВЕЧИВАЮТСЯ ровно
в тот момент, когда диктор о них говорит. Тайминги реплик вычисляются
по паузам в готовой озвучке (ffmpeg silencedetect + позиция по символам).
Кадры рендерятся в numpy (1080p) и стримятся в ffmpeg без диска.
"""
import os, sys, subprocess, math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageChops

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)
sys.path.insert(0, BASE)
sys.path.insert(0, ROOT)
import build_unit_group as B
import build_animated_pptx as A          # диф-рендер-машина (патчит B.canvas)
import imageio_ffmpeg

FF = imageio_ffmpeg.get_ffmpeg_exe()
FPS, W2, H2 = 30, 1920, 1080
HEAD, TAIL, XF, END_HOLD = 0.5, 0.9, 0.6, 2.8
SCALE = W2 / B.W                          # 0.8

# ---------------------------------------------------------------- сценарии
NARR = {
1: "UNIT GROUP — инженерно-строительная группа полного цикла. Полный цикл и одна ответственность: от фундамента до космоса. Три компании, которые закрывают весь цикл работ — от буронабивной сваи до финишной отделки под ключ. Более десяти лет специальных работ на объектах метро, тоннелей и мостов. Работаем круглосуточно, в любом климате. Москва и Московская область.",
2: "В основе группы — три компании. ЮНИТ ИНЖИНИРИНГ — головная организация: проектирование и строительство объектов любой сложности, комплекс работ на объекте Национального космического центра. АММ-СТРОЙ — операционный контур группы: демонтаж и алмазная резка, отделка под ключ, сантехника, электрика и инженерные системы. МОСТЫ И ТОННЕЛИ — специализированный подрядчик с опытом более десяти лет: мосты, тоннели и метрополитен, собственный парк буровых установок Casagrande. Один тендер, один договор, одна ответственность.",
3: "Что мы закрываем? Весь цикл — без стыков между подрядчиками. Проектирование. Буровые работы: буронабивные, буросекущие и бурокасательные сваи, стена в грунте. Монолитное строительство и гидроизоляция полного цикла. Инженерные системы. И отделка под ключ. Собственный парк техники: буровые установки Casagrande и канатная пила Hilti. Сваи диаметром до тысячи двухсот миллиметров в грунтах до десятой группы. Двести девяносто одна бурокасательная свая в ограждении одного котлована. Статические испытания свай — нагрузкой в тысячу тонн. Двадцать тысяч кубометров монолита на одной станции метро.",
4: "Наши проекты — там, где нас уже проверили. Национальный космический центр, совместный проект Правительства Москвы и Роскосмоса: башня высотой двести восемьдесят восемь метров и двести пятьдесят семь тысяч квадратных метров площади. Четыре станции метро, включая «Кленовый бульвар» на Большой кольцевой линии и вестибюль станции «Академическая» на новой Троицкой линии. Тоннель в Видном на трассе «ЮЛА» и капитальный ремонт Новокутузовского тоннеля на Третьем транспортном кольце. Свайное основание и испытания в составе транспортно-пересадочного узла «Мичуринский проспект».",
5: "Готовы к диалогу. Обсудим ваш объект — от котлована и свай до отделки под ключ, в одном договоре. ЮНИТ ИНЖИНИРИНГ. АММ-СТРОЙ. МОСТЫ И ТОННЕЛИ. Все контакты — на экране. UNIT GROUP: полный цикл. Одна ответственность. От фундамента до космоса.",
}

# ---------------------------------------------------------------- слои/ключи
# marker: ("text",needle) | ("pb",needle[,back]) — paste непосредственно перед text
SPEC = {
1: [
  dict(n="slogan",  mk=("pb", "ПОЛНЫЙ ЦИКЛ.", 1), fx="float", cue="UNIT GROUP", pulse=True),
  dict(n="subtext", mk=("text", "От фундамента"), fx="fade",  cue="от фундамента до космоса"),
  dict(n="stats",   mk=("pb", "3"),             fx="float", cue="Три компании"),
  dict(n="num1",    mk=("text", "3"),           fx="float", cue=None, add=1.3, pulse=True),
  dict(n="num2",    mk=("text", "10+"),         fx="float", cue="Более десяти лет", pulse=True),
  dict(n="num3",    mk=("text", "288 м"),       fx="float", cue="метро, тоннелей и мостов", pulse=True),
  dict(n="num4",    mk=("text", "24/7"),        fx="float", cue="круглосуточно", pulse=True),
  dict(n="tail",    mk=("text", "ООО «ЮНИТ"),   fx="fade",  cue="Москва и Московская область"),
],
2: [
  dict(n="card1", mk=("pb", "ГОЛОВНАЯ"),   fx="float", cue="ЮНИТ ИНЖИНИРИНГ", pulse=True),
  dict(n="card2", mk=("pb", "ОПЕРАЦИОННАЯ"), fx="float", cue="АММ-СТРОЙ", pulse=True),
  dict(n="card3", mk=("pb", "СПЕЦПОДРЯД"), fx="float", cue="МОСТЫ И ТОННЕЛИ", pulse=True),
  dict(n="band",  mk=("pb", "ОДИН ТЕНДЕР"), fx="fade",  cue="Один тендер"),
],
3: [
  dict(n="st1", mk=("pb", "01"), fx="float", cue="Проектирование."),
  dict(n="st2", mk=("pb", "02"), fx="float", cue="Буровые работы"),
  dict(n="st3", mk=("pb", "03"), fx="float", cue="Монолитное строительство"),
  dict(n="st4", mk=("pb", "04"), fx="float", cue="гидроизоляция полного цикла"),
  dict(n="st5", mk=("pb", "05"), fx="float", cue="Инженерные системы"),
  dict(n="st6", mk=("pb", "06"), fx="float", cue="отделка под ключ"),
  dict(n="drill", mk=("pb", "СОБСТВЕННЫЙ ПАРК"), fx="float", cue="Собственный парк техники", pulse=True),
  dict(n="s1x", mk=("text", "291 БКС"),   fx="float", cue="Двести девяносто одна", pulse=True),
  dict(n="s2x", mk=("text", "1 000 т"),   fx="float", cue="тысячу тонн", pulse=True),
  dict(n="s3x", mk=("text", "20 000 м³"), fx="float", cue="Двадцать тысяч кубометров", pulse=True),
],
4: [
  dict(n="nkzc",  mk=("pb", "ФЛАГМАН"),         fx="float", cue="Национальный космический центр", pulse=True),
  dict(n="metro", mk=("pb", "МЕТРО"),           fx="float", cue="Четыре станции метро", pulse=True),
  dict(n="tun",   mk=("pb", "ТОННЕЛИ И ДОРОГИ"),fx="float", cue="Тоннель в Видном", pulse=True),
  dict(n="piles", mk=("pb", "ГЕОТЕХНИКА"),      fx="float", cue="Свайное основание", pulse=True),
  dict(n="towers",mk=("pb", "ДЕВЕЛОПМЕНТ"),     fx="float", cue="Мичуринский проспект", pulse=True),
],
5: [
  dict(n="card1", mk=("pb", "ГОЛОВНАЯ"),        fx="float", cue="ЮНИТ ИНЖИНИРИНГ", pulse=True),
  dict(n="card2", mk=("pb", "ОПЕРАЦИОННЫЙ"),    fx="float", cue="АММ-СТРОЙ", pulse=True),
  dict(n="card3", mk=("pb", "СПЕЦПОДРЯД"),      fx="float", cue="МОСТЫ И ТОННЕЛИ", pulse=True),
  dict(n="flash", mk=("text", "«Ваш надёжный"), fx="fade",  cue="полный цикл. Одна ответственность", flash=True),
],
}
SLIDE_FNS = {1: B.slide1, 2: B.slide2, 3: B.slide3, 4: B.slide4, 5: B.slide5}

# ---------------------------------------------------------------- утилиты
def dur_of(path):
    out = subprocess.run([FF, "-i", path, "-f", "null", "-"], capture_output=True, text=True).stderr
    t = None
    for line in out.splitlines():
        if "time=" in line:
            t = line.split("time=")[1].split(" ")[0]
    h, m, s = t.split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)

def silences(path):
    """Середины пауз в mp3 (по silencedetect)."""
    out = subprocess.run([FF, "-i", path, "-af", "silencedetect=noise=-35dB:d=0.25",
                          "-f", "null", "-"], capture_output=True, text=True).stderr
    starts, ends = [], []
    for line in out.splitlines():
        if "silence_start" in line:
            starts.append(float(line.split("silence_start:")[1].split()[0]))
        elif "silence_end" in line:
            ends.append(float(line.split("silence_end:")[1].split()[0]))
    return [(s + e) / 2 for s, e in zip(starts, ends) if e > s]

def marker_idx(log, mk, start=0):
    kind, needle = mk[0], mk[1]
    back = mk[2] if len(mk) > 2 else 0
    if kind == "text":
        for idx, k, info in log:
            if idx > start and k == "text" and needle in info:
                return idx
    else:  # paste перед первым text с needle (возможно на |back| паст назад)
        t_idx = marker_idx(log, ("text", needle), start)
        pastes = [i for i, k, _ in log if k == "paste" and i < t_idx]
        return pastes[-1 - back] if len(pastes) > back else pastes[0]
    raise RuntimeError(f"marker {mk} not found (from {start})")

def extract_slide(sn):
    fn = SLIDE_FNS[sn]
    full, log = A.render_with_limit(fn, 10 ** 12, want_log=True)
    spec = SPEC[sn]
    starts, cursor = [], 0
    for d in spec:
        i = marker_idx(log, d["mk"], cursor)
        starts.append(i); cursor = i
    cuts = [1] + starts + [10 ** 12]
    base = A.render_with_limit(fn, cuts[1] - 1)
    layers = []
    for li, d in enumerate(spec):
        before = A.render_with_limit(fn, cuts[li + 1] - 1)
        after = A.render_with_limit(fn, cuts[li + 2] - 1)
        layers.append(A.diff_layer(before, after))
    comp = A.composite(base, layers)
    diff = ImageChops.difference(comp, full).convert("L")
    arr = np.asarray(diff, dtype=np.uint8)
    print(f"slide{sn}: {len(layers)} слоёв, средн.расхождение {arr.mean():.2f}, пикселов>12: {(arr>12).sum()}")
    return base, layers, spec

def to_np(im):
    return np.asarray(im.resize((W2, H2), Image.LANCZOS), dtype=np.uint8)

def glow_for(layer):
    """Неоновая рамка-подсветка по bbox слоя (в координатах 1080p)."""
    a = np.asarray(layer.resize((W2, H2), Image.LANCZOS))[:, :, 3]
    ys, xs = np.where(a > 24)
    if len(xs) == 0:
        return None, None
    x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
    pad = 10
    box = (max(0, x0 - pad), max(0, y0 - pad), min(W2, x1 + pad), min(H2, y1 + pad))
    img = Image.new("L", (W2, H2), 0)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle(box, radius=20, outline=255, width=8)
    img = img.filter(ImageFilter.GaussianBlur(14))
    g = np.asarray(img, dtype=np.float32) / 255.0
    orange = np.zeros((H2, W2, 3), dtype=np.float32)
    orange[:, :, 0], orange[:, :, 1], orange[:, :, 2] = 255, 120, 10
    return orange * g[:, :, None], (x0, y0, x1, y1)

# ---------------------------------------------------------------- тайминги
def build_cues(sn, voice_dur, pauses):
    text = NARR[sn].lower()
    total_chars = len(text)
    cues = []
    for d in SPEC[sn]:
        if d.get("cue"):
            pos = text.find(d["cue"].lower())
            if pos < 0:
                raise RuntimeError(f"slide{sn}: фраза не найдена: {d['cue']}")
            pred = HEAD + (pos / total_chars) * voice_dur
            best, bd = None, 1.0
            for p in pauses:
                if abs(p - (pred - HEAD)) < bd:
                    best, bd = p, abs(p - (pred - HEAD))
            t = HEAD + (best if best is not None else pred - HEAD)
            cues.append(max(t, HEAD + 0.25))
        else:
            cues.append(None)
    # производные (add) и монотонность
    prev = HEAD + 0.2
    for i, (d, t) in enumerate(zip(SPEC[sn], cues)):
        if t is None:
            t = prev + (d.get("add") or 0.8)
            cues[i] = t
        cues[i] = max(cues[i], prev + 0.45)
        prev = cues[i]
    return cues

# ---------------------------------------------------------------- рендер
def ease(t):
    return t * t * (3 - 2 * t)

def slide_frame(prep, local_t):
    """Кадр слайда в момент local_t (или None если ещё не начался)."""
    if local_t < 0:
        return prep["base"].copy()
    fr = prep["base"].copy()
    for lyr in prep["layers"]:
        cue = lyr["cue"]
        if local_t < cue:
            continue
        e = min(1.0, (local_t - cue) / 0.7)
        k = ease(e)
        rgba = lyr["rgba"]
        alpha = rgba[:, :, 3].astype(np.float32) * (k / 255.0)
        dy = int(round((1 - k) * 22)) if lyr["fx"] == "float" else 0
        h = H2 - dy
        reg = fr[dy:H2]
        la = alpha[0:h]
        lc = rgba[0:h, :, :3].astype(np.float32)
        m = la[:, :, None]
        fr[dy:H2] = (lc * m + reg.astype(np.float32) * (1 - m)).astype(np.uint8)
        if lyr.get("pulse"):
            pt = local_t - (cue + 0.75)
            if 0 < pt < 1.6 and lyr["glow"] is not None:
                g = math.sin(math.pi * pt / 1.6) * 0.9
                fr = np.clip(fr.astype(np.float32) + lyr["glow"] * g, 0, 255).astype(np.uint8)
    return fr

def main():
    voices = [os.path.join(BASE, f"voice_s{i}.mp3") for i in range(1, 6)]
    vdur = [dur_of(v) for v in voices]
    seg = [round(v + HEAD + TAIL, 2) for v in vdur]
    seg[-1] = round(seg[-1] + END_HOLD, 2)
    starts = [round(sum(seg[:i]) - XF * i, 3) for i in range(5)]
    total = round(sum(seg) - XF * 4, 2)
    print("сегменты:", seg, "| итого:", total, "c")

    preps = []
    for sn in range(1, 6):
        base, layers, spec = extract_slide(sn)
        pauses = silences(voices[sn - 1])
        cues = build_cues(sn, vdur[sn - 1], pauses)
        prep = {"base": to_np(base), "layers": []}
        for d, lyr, cue in zip(spec, layers, cues):
            rgba = np.asarray(lyr.resize((W2, H2), Image.LANCZOS), dtype=np.uint8)
            glow, bbox = (glow_for(lyr) if d.get("pulse") else (None, None))
            prep["layers"].append(dict(rgba=rgba, fx=d["fx"], cue=round(cue, 2),
                                       pulse=bool(d.get("pulse")), glow=glow, n=d["n"]))
        preps.append(prep)
        print(f"  slide{sn} ключи:", [(l['n'], l['cue']) for l in prep['layers']])

    # ---- аудио-граф (как в v1)
    fc = []
    for i in range(5):
        fc.append(f"[{i+5}:a]aresample=48000,adelay={int(HEAD*1000)}|{int(HEAD*1000)},"
                  f"apad=whole_dur={seg[i]}[a{i}]")
    fc.append("[a0][a1][a2][a3][a4]concat=n=5:v=0:a=1,"
              f"loudnorm=I=-16:TP=-1.5:LRA=11,afade=t=out:st={round(total-1.2,2)}:d=1.2[aout]")

    args = [FF, "-y"]
    for i in range(5):
        args += ["-i", os.path.join(ROOT, "slides", f"slide{i+1}.png")]
    for v in voices:
        args += ["-i", v]
    args += ["-filter_complex", ";".join(fc),
             "-map", "[aout]", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
             "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W2}x{H2}", "-r", str(FPS),
             "-i", "-",
             "-map", "0:v"] # placeholder (заменяем ниже)
    # корректный порядок: video pipe должен идти последним входом
    args = [FF, "-y"]
    for i in range(5):
        args += ["-i", os.path.join(ROOT, "slides", f"slide{i+1}.png")]
    for v in voices:
        args += ["-i", v]
    args += ["-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W2}x{H2}", "-r", str(FPS), "-i", "-",
             "-filter_complex", ";".join(fc),
             "-map", "10:v", "-map", "[aout]",
             "-c:v", "libx264", "-crf", "20", "-preset", "medium", "-pix_fmt", "yuv420p",
             "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
             "-movflags", "+faststart", "-t", str(total),
             os.path.join(ROOT, "UNIT_GROUP_Видео.mp4")]

    proc = subprocess.Popen(args, stdin=subprocess.PIPE,
                            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    nframes = int(round(total * FPS))
    orange = np.array([255, 107, 0], dtype=np.float32)
    for fi in range(nframes):
        t = fi / FPS
        # активный слайд
        si = 0
        for i in range(5):
            if t >= starts[i]:
                si = i
        fr = slide_frame(preps[si], t - starts[si])
        # кроссфейд в начало следующего слайда
        if si < 4:
            nt = t - starts[si + 1]
            if 0 <= nt < XF:
                nxt = slide_frame(preps[si + 1], nt if nt >= 0 else -1)
                w = ease(nt / XF)
                fr = (fr.astype(np.float32) * (1 - w) + nxt.astype(np.float32) * w).astype(np.uint8)
        # фейды начала/конца
        if t < 0.6:
            fr = (fr * (t / 0.6)).astype(np.uint8)
        if t > total - 1.0:
            fr = (fr * max(0.0, (total - t) / 1.0)).astype(np.uint8)
        # прогресс-бар
        pw = int(W2 * t / total)
        if pw > 0:
            fr[H2 - 5:H2, 0:pw] = orange.astype(np.uint8)
        proc.stdin.write(fr.tobytes())
        if fi % 450 == 0:
            print(f"  кадр {fi}/{nframes} (t={t:.1f}s)", flush=True)
    proc.stdin.close()
    err = proc.stderr.read().decode(errors="ignore") if proc.stderr else ""
    rc = proc.wait()
    if rc != 0:
        print(err[-2500:]); raise SystemExit(1)
    sz = os.path.getsize(os.path.join(ROOT, "UNIT_GROUP_Видео.mp4")) // 1024 // 1024
    print(f"Готово: {total} c, {sz} МБ")

if __name__ == "__main__":
    main()
