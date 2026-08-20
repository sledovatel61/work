# -*- coding: utf-8 -*-
"""
UNIT GROUP — видео v3:
1) плавные кроссфейды между слайдами (в v2 был баг — резкий переключатель);
2) точные тайминги слайдов 2 и 4: озвучка пересобрана из отдельных фраз
   (тот же голос, те же тексты) — ключи = стыки клипов, миллисекундная
   точность вместо оценки по символам;
3) эпичный тёмный эмбиент-подклад (синтез в ffmpeg) с авточувствительностью
   к речи (sidechaincompress): музыка тихо дышит под диктором.
Рендер кадров и слои — как в v2 (numpy 1080p30, стриминг в ffmpeg).
"""
import os, sys, subprocess, math
import numpy as np
from PIL import Image

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)
sys.path.insert(0, BASE)
sys.path.insert(0, ROOT)
import build_unit_group as B
import build_animated_pptx as A
import build_video2 as V2          # SPEC/NARR/extract_slide/slide_frame
import imageio_ffmpeg

FF = imageio_ffmpeg.get_ffmpeg_exe()
FPS, W2, H2 = 30, 1920, 1080
HEAD, TAIL, XF, END_HOLD = 0.5, 0.9, 0.6, 2.8
GAP = 0.35

def dur_of(p):
    out = subprocess.run([FF, "-i", p, "-f", "null", "-"], capture_output=True, text=True).stderr
    t = None
    for line in out.splitlines():
        if "time=" in line:
            t = line.split("time=")[1].split(" ")[0]
    h, m, s = t.split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)

def assemble(clips, out_path):
    """Склеить фразы с паузами GAP; вернуть (итоговая длительность, старты клипов)."""
    args = [FF, "-y"]
    for c in clips:
        args += ["-i", c]
    fc = []
    for i in range(len(clips)):
        fc.append(f"[{i}:a]aresample=48000,apad=pad_dur={GAP}[a{i}]")
    fc.append("".join(f"[a{i}]" for i in range(len(clips))) +
              f"concat=n={len(clips)}:v=0:a=1[out]")
    args += ["-filter_complex", ";".join(fc), "-map", "[out]", "-c:a", "libmp3lame", "-q:a", "2", out_path]
    r = subprocess.run(args, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr[-1500:]); raise SystemExit(1)
    durs = [dur_of(c) for c in clips]
    starts, t = [], 0.0
    for d in durs:
        starts.append(t)
        t += d + GAP
    return t - GAP, starts

# ------------------------------------------------ сборка новых дорожек 2/4
s2_clips = [os.path.join(BASE, f"s2_c{i}.mp3") for i in range(1, 5)]
s4_clips = [os.path.join(BASE, f"s4_c{i}.mp3") for i in range(1, 7)]
voice2_v3 = os.path.join(BASE, "voice_s2_v3.mp3")
voice4_v3 = os.path.join(BASE, "voice_s4_v3.mp3")
dur2, st2 = assemble(s2_clips, voice2_v3)
dur4, st4 = assemble(s4_clips, voice4_v3)
d2c = [dur_of(c) for c in s2_clips]
d4c = [dur_of(c) for c in s4_clips]
print(f"s2_v3: {dur2:.2f}s, старты клипов {[round(x,2) for x in st2]}")
print(f"s4_v3: {dur4:.2f}s, старты клипов {[round(x,2) for x in st4]}")

# ключи слайда 2: card1 внутри c1 (после «В основе группы — три компании.»)
c1_text_len = len("В основе группы — три компании. ") ; c1_full = len("В основе группы — три компании. ЮНИТ ИНЖИНИРИНГ — головная организация: проектирование и строительство объектов любой сложности, комплекс работ на объекте Национального космического центра.")
OVR = {
 2: {"card1": HEAD + st2[0] + c1_text_len / c1_full * d2c[0],
     "card2": HEAD + st2[1], "card3": HEAD + st2[2], "band": HEAD + st2[3]},
 4: {"nkzc": HEAD + st4[1], "metro": HEAD + st4[3], "tun": HEAD + st4[4],
     "piles": HEAD + st4[5], "towers": HEAD + st4[5] + 0.72 * d4c[5]},
}

voices = [os.path.join(BASE, "voice_s1.mp3"), voice2_v3,
          os.path.join(BASE, "voice_s3.mp3"), voice4_v3,
          os.path.join(BASE, "voice_s5.mp3")]
vdur = [dur_of(v) for v in voices]
seg = [round(v + HEAD + TAIL, 2) for v in vdur]
seg[-1] = round(seg[-1] + END_HOLD, 2)
starts = [round(sum(seg[:i]) - XF * i, 3) for i in range(5)]
total = round(sum(seg) - XF * 4, 2)
print("речь:", [round(v, 1) for v in vdur], "\nсегменты:", seg, "| итого:", total)

# ------------------------------------------------ слои и ключи
preps = []
for sn in range(1, 6):
    base, layers, spec = V2.extract_slide(sn)
    if sn in (2, 4):
        cues = []
        name2cue = OVR[sn]
        for d in spec:
            cues.append(name2cue.get(d["n"], HEAD + 0.3))
    else:
        pauses = V2.silences(voices[sn - 1])
        cues = V2.build_cues(sn, vdur[sn - 1], pauses)
    prep = {"base": V2.to_np(base), "layers": []}
    for d, lyr, cue in zip(spec, layers, cues):
        rgba = np.asarray(lyr.resize((W2, H2), Image.LANCZOS), dtype=np.uint8)
        glow, bbox = (V2.glow_for(lyr) if d.get("pulse") else (None, None))
        prep["layers"].append(dict(rgba=rgba, fx=d["fx"], cue=round(cue, 2),
                                   pulse=bool(d.get("pulse")), glow=glow, n=d["n"]))
    preps.append(prep)
    print(f"  slide{sn} ключи:", [(l['n'], l['cue']) for l in prep['layers']])

# ------------------------------------------------ фильтры аудио: речь + музыка с ducking
fc = []
for i in range(5):
    fc.append(f"[{i}:a]aresample=48000,adelay={int(HEAD*1000)}|{int(HEAD*1000)},"
              f"apad=whole_dur={seg[i]}[a{i}]")
fc.append("[a0][a1][a2][a3][a4]concat=n=5:v=0:a=1,volume=1.0[speech]")
# эмбиент: дрон ля-минор с медленным дыханием + розовый шум «воздух»
fc.append(f"[5:a]volume=0.9[drone]")
fc.append(f"[6:a]volume=0.8[air]")
fc.append("[drone][air]amix=inputs=2:duration=longest:normalize=0,"
          f"afade=t=in:st=0:d=2.5,afade=t=out:st={round(total-5,2)}:d=5[mus]")
fc.append("[speech]loudnorm=I=-16:TP=-1.5:LRA=11[vnorm]")
fc.append("[vnorm]asplit=2[v1][v2]")
fc.append("[mus][v2]sidechaincompress=threshold=0.028:ratio=14:attack=90:release=900[mduck]")
fc.append("[v1][mduck]amix=inputs=2:duration=longest:normalize=0,"
          f"afade=t=out:st={round(total-1.2,2)}:d=1.2,aresample=48000[afin]")

DRONE = ("aevalsrc=exprs='(0.55+0.45*sin(2*PI*t/29))*"
         "(0.24*sin(2*PI*55*t)+0.20*sin(2*PI*110*t)+0.15*sin(2*PI*110.7*t)+"
         "0.13*sin(2*PI*164.81*t)+0.09*sin(2*PI*220*t)+0.045*sin(2*PI*261.63*t))':"
         f"s=48000:d={total}")
AIR = (f"anoisesrc=color=pink:r=48000:amplitude=0.05:d={total},"
       "lowpass=f=270,highpass=f=40,volume='0.5+0.5*sin(2*PI*t/17+2)':eval=frame")

args = [FF, "-y"]
for v in voices:
    args += ["-i", v]
args += ["-f", "lavfi", "-i", DRONE, "-f", "lavfi", "-i", AIR]
args += ["-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W2}x{H2}", "-r", str(FPS), "-i", "-",
         "-filter_complex", ";".join(fc),
         "-map", "7:v", "-map", "[afin]",
         "-c:v", "libx264", "-crf", "20", "-preset", "medium", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
         "-movflags", "+faststart", "-t", str(total),
         os.path.join(ROOT, "UNIT_GROUP_Видео.mp4")]

proc = subprocess.Popen(args, stdin=subprocess.PIPE,
                        stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
nframes = int(round(total * FPS))
ease = V2.ease
for fi in range(nframes):
    t = fi / FPS
    si = 0
    for i in range(5):
        if t >= starts[i]:
            si = i
    local = t - starts[si]
    fr = V2.slide_frame(preps[si], local)
    # ПЛАВНЫЙ ПЕРЕХОД: первые XF секунд слайда — бленд с хвостом предыдущего
    if si > 0 and local < XF:
        prev = V2.slide_frame(preps[si - 1], t - starts[si - 1])
        w = ease(local / XF)
        fr = (prev.astype(np.float32) * (1 - w) + fr.astype(np.float32) * w).astype(np.uint8)
    if t < 0.6:
        fr = (fr * (t / 0.6)).astype(np.uint8)
    if t > total - 1.0:
        fr = (fr * max(0.0, (total - t) / 1.0)).astype(np.uint8)
    pw = int(W2 * t / total)
    if pw > 0:
        fr[H2 - 5:H2, 0:pw] = np.array([255, 107, 0], dtype=np.uint8)
    proc.stdin.write(fr.tobytes())
    if fi % 600 == 0:
        print(f"  кадр {fi}/{nframes} (t={t:.1f}s)", flush=True)
proc.stdin.close()
err = proc.stderr.read().decode(errors="ignore") if proc.stderr else ""
if proc.wait() != 0:
    print(err[-2500:]); raise SystemExit(1)
print("Готово:", total, "c,", os.path.getsize(os.path.join(ROOT, "UNIT_GROUP_Видео.mp4")) // 1024 // 1024, "МБ")
