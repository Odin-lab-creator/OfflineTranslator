import re, subprocess, json, sys
lines=[l.strip() for l in open('script.txt',encoding='utf8') if l.strip()]
out=subprocess.run(['ffmpeg','-i','voice.mp3','-af','silencedetect=noise=-38dB:d=0.2','-f','null','-'],capture_output=True,text=True).stderr
ev=re.findall(r'silence_(start|end): ([0-9.]+)',out)
dur=116.61
sil=[]; cur=None
for k,v in ev:
    v=float(v)
    if k=='start': cur=v
    else: sil.append((cur,v))
chunks=[]; t=0.0
for s,e in sil:
    if s-t>0.05: chunks.append((t,s))
    t=e
if dur-t>0.1: chunks.append((t,dur))
syl=lambda s: len(re.findall('[аеёиоуыэюяАЕЁИОУЫЭЮЯ]',s))+0.0
S=[syl(l) for l in lines]
rate=sum(e-s for s,e in chunks)/sum(S)
N,M=len(lines),len(chunks); INF=1e18; G=4
dp=[[INF]*(M+1) for _ in range(N+1)]; bk={}
dp[0][0]=0
for i in range(N+1):
  for j in range(M+1):
    if dp[i][j]>=INF: continue
    for a in range(1,G+1):
      for b in range(1,G+1):
        if i+a>N or j+b>M: continue
        if a>1 and b>1: continue
        d=chunks[j+b-1][1]-chunks[j][0]; exp=sum(S[i:i+a])*rate
        c=dp[i][j]+(d-exp)**2+0.3*(a-1)+0.3*(b-1)
        if c<dp[i+a][j+b]: dp[i+a][j+b]=c; bk[(i+a,j+b)]=(i,j)
res=[None]*N; i,j=N,M
while (i,j)!=(0,0):
    pi,pj=bk[(i,j)]
    s0,e0=chunks[pj][0],chunks[j-1][1]; tot=sum(S[pi:i]); t=s0
    for k in range(pi,i):
        d=(e0-s0)*S[k]/tot; res[k]=(round(t,2),round(t+d,2)); t+=d
    i,j=pi,pj
json.dump([{'start':a,'end':b,'text':l} for (a,b),l in zip(res,lines)],open('timings.json','w',encoding='utf8'),ensure_ascii=False,indent=1)
for (a,b),l in zip(res,lines): print(f"{a:6.2f}-{b:6.2f} {l}")
