#!/usr/bin/env python3
"""Fenrir weekly update: append completed Fridays, recompute, bake console + dispatch."""
import json, datetime as dt
import numpy as np, pandas as pd, yfinance as yf

TICKERS = {"omx": "^OMX", "spx": "^GSPC", "world": "^990100-USD-STRD"}
NAMES = ["BULL", "BULL-TR", "CASH", "BEAR"]

def machine(C):
    m=len(C); chg=np.zeros(m); chg[1:]=(C[1:]/C[:-1]-1)*100
    g=np.clip(chg,0,None); l=np.clip(-chg,0,None)
    ag=np.full(m,np.nan); al=np.full(m,np.nan)
    ag[14]=g[1:15].mean(); al[14]=l[1:15].mean()
    for i in range(15,m):
        ag[i]=(ag[i-1]*13+g[i])/14; al[i]=(al[i-1]*13+l[i])/14
    R=100-100/(1+ag/al)
    mom4=np.full(m,np.nan); mom4[4:]=(C[4:]/C[:-4]-1)*100
    e12=np.zeros(m); e20=np.zeros(m); e12[0]=e20[0]=C[0]
    for i in range(1,m):
        e12[i]=C[i]*2/13+e12[i-1]*11/13; e20[i]=C[i]*2/21+e20[i-1]*19/21
    MP=100*(e12-e20)/C
    cs=np.cumsum(C); M40=np.full(m,np.nan); M40[39:]=(cs[39:]-np.concatenate([[0],cs[:-40]]))/40
    M52=np.full(m,np.nan); M52[51:]=(cs[51:]-np.concatenate([[0],cs[:-52]]))/52
    st=0; out=[0]
    for i in range(1,m):
        r=R[i]; m4=mom4[i]; mm=M40[i]; c=C[i]; mp=MP[i]
        new=st
        if not (np.isnan(mm) or np.isnan(r)):
            if st==0:
                if r>=69: new=2
            elif st==1:
                if r>=69 or c<mm: new=2
            elif st==2:
                if r<=35 and mp>-2: new=0
                elif m4<-4 and c<mm: new=3
                elif c>mm and 40<=r<=60: new=1
            else:
                if r<=35 and mp>-2: new=0
                elif c>mm: new=2
        st=new; out.append(st)
    return np.array(out), dict(R=R, MP=MP, mom4=mom4, M52=M52)

def fenrir_positions(O, S):
    so, io_ = machine(O); ss, is_ = machine(S)
    pos=[]
    for i in range(len(O)):
        bear = so[i]==3 and ss[i]==3
        above = True if np.isnan(io_["M52"][i]) else O[i] > io_["M52"][i]
        pos.append(-2 if bear else (2 if above else 1))
    return np.array(pos), so, ss, io_, is_

def fetch_new(last_date):
    frames={}
    for k,t in TICKERS.items():
        d=yf.download(t, start="2024-01-01", auto_adjust=False, progress=False)["Close"]
        s=(d[t] if hasattr(d,"columns") else d).dropna()
        frames[k]=s[s>0]
    # completed weeks only: week ends Friday; include a week once today > its Friday
    today=dt.date.today()
    wk={k: v.resample("W-FRI").last().dropna() for k,v in frames.items()}
    idx=wk["omx"].index
    new=[]
    for ts in idx:
        d=ts.date()
        if d.isoformat() <= last_date: continue
        if d >= today: continue          # week not completed
        row=[d.isoformat()]
        ok=True
        for k in ["omx","spx","world"]:
            if ts in wk[k].index: row.append(round(float(wk[k][ts]),2))
            elif k=="world": row.append(None)  # fill later
            else: ok=False
        if ok: new.append(row)
    return new

def main():
    data=json.load(open("data.json"))
    last=data[-1][0]
    new=fetch_new(last)
    log=[]
    for row in new:
        prev=data[-1]
        if row[3] is None: row[3]=prev[3]
        checks=[(1,0.25),(2,0.25),(3,0.25)]
        if all(abs(row[c]/prev[c]-1)<tol for c,tol in checks):
            data.append(row); log.append(f"appended {row[0]}: OMX {row[1]} SPX {row[2]} WLD {row[3]}")
        else:
            log.append(f"REJECTED {row}: failed sanity vs {prev}")
    json.dump(data, open("data.json","w"))

    O=np.array([r[1] for r in data]); S=np.array([r[2] for r in data])
    pos, so, ss, io_, is_ = fenrir_positions(O,S)
    i=len(data)-1
    posname={2:"BULL \u00d72 \u2014 XACT Bull 2 (SE0003051010)",1:"BULL \u00d71 \u2014 plain OMXS30 ETF",
             -2:"BEAR \u00d72 \u2014 XACT Bear 2 (SE0005466505)"}
    wret=O[i]/O[i-1]-1; sret=S[i]/S[i-1]-1
    stratret=pos[i-1]*wret
    switch = pos[i]!=pos[i-1]
    dist=100*(O[i]/io_["M52"][i]-1)

    lines=[]
    lines.append(f"FENRIR WEEKLY DISPATCH \u00b7 week ending {data[i][0]}")
    lines.append(f"OMXS30 {O[i]:,.2f} ({wret*100:+.1f}%) \u00b7 S&P 500 {S[i]:,.2f} ({sret*100:+.1f}%)")
    lines.append(f"Position held: \u00d7{abs(pos[i-1])}{' short' if pos[i-1]<0 else ''} \u2192 Fenrir week: {stratret*100:+.1f}%")
    if switch:
        lines.append(f"REGIME CHANGE \u2192 {posname[pos[i]]} \u2014 execute at Monday close.")
    else:
        lines.append(f"No regime change. Hold: {posname[pos[i]]}.")
    lines.append(f"Ladder: {dist:+.1f}% vs MA52w \u00b7 OMX machine {NAMES[so[i]]} (RSI {io_['R'][i]:.1f}, MACD% {io_['MP'][i]:.2f}) \u00b7 "
                 f"S&P machine {NAMES[ss[i]]} (RSI {is_['R'][i]:.1f}, MACD% {is_['MP'][i]:.2f})")
    warn=[]
    if io_["R"][i]>=64: warn.append("OMX RSI approaching 69 exit")
    if io_["R"][i]<=40 and pos[i]!=-2: warn.append("OMX RSI approaching 35 entry zone")
    if abs(dist)<3: warn.append("price within 3% of MA52 \u2014 ladder rung may flip")
    if io_["MP"][i]<=-1.2: warn.append("OMX MACD% nearing \u22122 gate")
    if warn: lines.append("Watch: " + "; ".join(warn))
    if log: lines.append("Data: " + " | ".join(log))
    dispatch="\n".join(lines)
    open("dispatch.txt","w").write(dispatch)

    disp_html=('<section><div class="panel" style="border-color:#3A4658;">'
               '<div class="t disp" style="font-size:10px;letter-spacing:.22em;color:#93A7BC;">WEEKLY DISPATCH</div>'
               '<pre style="font-family:inherit;font-size:12px;line-height:1.8;white-space:pre-wrap;margin-top:8px;">'
               + dispatch.replace("&","&amp;").replace("<","&lt;") + "</pre></div></section>")
    tpl=open("template.html").read()
    out=tpl.replace("__DATA__", json.dumps(data)).replace("__DISPATCH__", disp_html)
    open("index.html","w").write(out)
    print(dispatch)

if __name__=="__main__":
    main()
