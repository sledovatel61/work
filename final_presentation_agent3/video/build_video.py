# -*- coding: utf-8 -*-
"""UNIT GROUP — видео-версия презентации (MP4, 1920x1080, ~3 мин).
Слайды = движение камеры Ken Burns (зум/панорама, свой характер на каждый
слайд), кроссфейды 0.7 c, дикторская озвучка (voice-00) с паузами,
нормализация громкости -16 LUFS. Длительности сегментов = речь + запас."""
import os, subprocess, json
from fractions import Fraction
import imageio_ffmpeg

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)
FF = imageio_ffmpeg.get_ffmpeg_exe()
FPS = 30
HEAD, TAIL, XF = 0.5, 0.9, 0.7      # пауза до/после речи, кроссфейд
END_HOLD = 2.8                       # удержание финального слайда (компенсация кроссфейдов)

def dur_of(path):
    out = subprocess.run([FF, "-i", path, "-f", "null", "-"], capture_output=True, text=True).stderr
    for line in out.splitlines():
        if "time=" in line:
            t = line.split("time=")[1].split(" ")[0]
    h, m, s = t.split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)

voices = [os.path.join(BASE, f"voice_s{i}.mp3") for i in range(1, 6)]
vdur = [dur_of(v) for v in voices]
seg = [round(v + HEAD + TAIL, 2) for v in vdur]
seg[-1] = round(seg[-1] + END_HOLD, 2)
D = [int(s * FPS) for s in seg]
total = sum(seg) - XF * 4
print("речь:", [round(v, 1) for v in vdur])
print("сегменты:", seg, "итого:", round(total, 1), "c")

# движение камеры на каждый слайд: (зум-выражение, x-выражение)
motions = [
    (f"1+0.10*on/{D[0]}", "(iw-iw/zoom)/2"),
    (f"1+0.09*on/{D[1]}", f"(iw-iw/zoom)/2+150*on/{D[1]}"),
    (f"1.10-0.10*on/{D[2]}", "(iw-iw/zoom)/2"),
    (f"1+0.09*on/{D[3]}", f"(iw-iw/zoom)/2-150*on/{D[3]}"),
    (f"1+0.08*on/{D[4]}", "(iw-iw/zoom)/2"),
]

fc = []
# видео-ветки: картинка -> upscale -> zoompan
for i in range(5):
    fc.append(
        f"[{i}:v]scale=4800:2700:flags=lanczos,"
        f"zoompan=z='{motions[i][0]}':x='{motions[i][1]}':y='ih/2-(ih/zoom/2)'"
        f":d={D[i]}:s=1920x1080:fps={FPS},format=yuv420p[v{i}]")
# кроссфейды
offsets, acc = [], seg[0]
for i in range(4):
    offsets.append(round(acc - XF, 2))
    acc += seg[i + 1] - XF
prev = "v0"
for i in range(4):
    out = f"x{i+1}"
    fc.append(f"[{prev}][v{i+1}]xfade=transition=fade:duration={XF}:offset={offsets[i]}[{out}]")
    prev = out
fc.append(f"[{prev}]fade=t=in:st=0:d=0.6,fade=t=out:st={round(total-1.0,2)}:d=1.0[vout]")
# аудио-ветки: речь с задержкой и паддингом до длины сегмента
for i in range(5):
    fc.append(f"[{i+5}:a]aresample=48000,adelay={int(HEAD*1000)}|{int(HEAD*1000)},"
              f"apad=whole_dur={seg[i]}[a{i}]")
fc.append("[a0][a1][a2][a3][a4]concat=n=5:v=0:a=1,"
          f"loudnorm=I=-16:TP=-1.5:LRA=11,"
          f"afade=t=out:st={round(total-1.2,2)}:d=1.2[aout]")

args = [FF, "-y"]
for i in range(5):
    args += ["-i", os.path.join(ROOT, "slides", f"slide{i+1}.png")]
for v in voices:
    args += ["-i", v]
args += ["-filter_complex", ";".join(fc),
         "-map", "[vout]", "-map", "[aout]",
         "-c:v", "libx264", "-crf", "22", "-preset", "medium", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
         "-movflags", "+faststart",
         "-t", str(round(total, 2)),
         os.path.join(ROOT, "UNIT_GROUP_Видео.mp4")]
print("Запуск ffmpeg…")
r = subprocess.run(args, capture_output=True, text=True)
if r.returncode != 0:
    print(r.stderr[-3000:])
    raise SystemExit(1)
size = os.path.getsize(os.path.join(ROOT, "UNIT_GROUP_Видео.mp4")) // 1024 // 1024
print(f"Готово: UNIT_GROUP_Видео.mp4 — {round(total,1)} c, {size} МБ")
