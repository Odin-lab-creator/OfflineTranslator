"""Сетка: фаза доли и сильная доля (по бочке/808 и снэйру) для заданного BPM.  python3 -I grid.py минус.wav BPM"""
import subprocess, sys
import numpy as np
SR = 22050
x = np.frombuffer(subprocess.run(["ffmpeg","-v","error","-i",sys.argv[1],"-ac","1","-ar",str(SR),"-f","f32le","-"],capture_output=True).stdout,np.float32).astype(float)
bpm = float(sys.argv[2]); beat = 60/bpm
hop = 64; fps = SR/hop
def onset(lo, hi):
    S = np.abs(np.array([np.fft.rfft(x[i:i+1024]*np.hanning(1024)) for i in range(0, len(x)-1024, hop)]))
    f = np.fft.rfftfreq(1024, 1/SR); m = (f>=lo)&(f<hi)
    o = np.maximum(0, np.diff(np.log1p(S[:, m]*10), axis=0)).sum(1); return np.concatenate([[0], o])
full, low, mid = onset(30, 8000), onset(30, 150), onset(150, 4000)
per = beat*fps; n = int((len(full)-2)/per)
phs = np.linspace(0, beat, 400, endpoint=False)
sc = [full[np.round((p + beat*np.arange(n))*fps).astype(int)].mean() for p in phs]
p0 = phs[int(np.argmax(sc))]
# уточнение с подвыборкой
idx = np.round((p0 + beat*np.arange(n))*fps).astype(int)
print(f"фаза доли: {p0*1000:.1f} мс")
kick = [low[idx[k::4]].mean() for k in range(4)]; sn = [mid[idx[k::4]].mean() for k in range(4)]
print("бочка по долям 1–4 (сдвиг 0..3):", np.round(kick, 2), " снэйр:", np.round(sn, 2))
# сильная доля: где бочка сильнее; при полутемпе снэйр на 3-й
k0 = int(np.argmax(kick))
t0 = p0 + k0*beat
print(f"сильная доля: {t0*1000:.1f} мс (такт {4*beat:.4f} с)")
print("T0", t0)
