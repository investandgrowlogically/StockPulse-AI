import streamlit as st, pandas as pd, numpy as np, yfinance as yf, requests
from urllib.parse import quote
st.set_page_config(page_title="StockPulse Lite V5.3",page_icon="📈",layout="wide")
st.markdown("""<style>
html,body,[data-testid="stAppViewContainer"],section.main{overflow-y:auto!important;min-height:100vh!important}
[data-testid="stMetric"]{border:1px solid #e5e7eb;border-radius:14px;padding:12px}
.sp{font-size:2.4rem;font-weight:800;color:#111827}.sub{color:#667085}.note{background:#fff8e6;border:1px solid #f2d27c;padding:10px;border-radius:10px}
</style>""",unsafe_allow_html=True)
UNIVERSE="""AAPL MSFT NVDA AMZN GOOGL META AVGO AMD MU AMAT LRCX KLAC ASML TSM ARM INTC TXN QCOM MRVL TSLA NFLX PLTR APP NOW CRWD PANW FTNT DDOG NET SNOW ORCL CRM ADBE INTU IBM ACN JPM GS MS BAC C WFC BLK SCHW COF AXP V MA PYPL FI SOFI HOOD COIN XOM CVX COP SLB EOG OXY MPC PSX VLO LNG CAT DE URI PH HON RTX LMT NOC GD UNP UPS VRT ETN CEG GEV GE FSLR COST WMT HD LOW TJX TGT LULU NKE SBUX MCD CMG KO PEP PM MO UBER ABNB BKNG DASH SHOP MELI EBAY ETSY JNJ LLY MRK PFE ABBV BMY AMGN GILD REGN TMO DHR EL ELV UNH CI CVS HUM NEE DUK SO""".split()
@st.cache_data(ttl=1800)
def px(t,start=None,end=None,period="2y"):
    try:
        x=yf.download(t,start=start,end=end,period=period,auto_adjust=True,progress=False,threads=False)
        if isinstance(x.columns,pd.MultiIndex):x.columns=x.columns.get_level_values(0)
        return x.dropna()
    except:return pd.DataFrame()
def score(t,x):
    if len(x)<220:return None
    c,v=x.Close,x.Volume;m20=c.rolling(20).mean();m50=c.rolling(50).mean();m200=c.rolling(200).mean()
    d=c.diff();g=d.clip(lower=0).rolling(14).mean();l=(-d.clip(upper=0)).rolling(14).mean()
    rsi=float(100-100/(1+g.iloc[-1]/l.iloc[-1])) if l.iloc[-1] else 50
    p=float(c.iloc[-1]);atr=float((x.High-x.Low).rolling(14).mean().iloc[-1]);vr=float(v.iloc[-1]/v.rolling(20).mean().iloc[-1])
    hi=float(x.High.shift(1).rolling(20).max().iloc[-1]);r20=p/float(c.iloc[-21])-1;r60=p/float(c.iloc[-61])-1
    s=(15 if p>m20.iloc[-1] else 0)+(15 if m20.iloc[-1]>m50.iloc[-1] else 0)+(15 if m50.iloc[-1]>m200.iloc[-1] else 0)+(10 if r20>.05 else 5 if r20>0 else 0)+(10 if r60>.10 else 5 if r60>0 else 0)+(15 if p>=hi else 8 if p>=hi*.985 else 0)+(10 if vr>=1.5 else 6 if vr>=1.1 else 2)+(5 if 50<=rsi<=72 else 2 if rsi>72 else 0)
    return [t,round(min(100,s),1),("BUY" if s>=75 else "WATCH" if s>=60 else "SKIP"),round(p,2),round(p-1.5*atr,2),round(p+2*atr,2),round(rsi,1),round(vr,1)]
def wfscore(x):
    if len(x)<220:return None
    return score("x",x)[1]
@st.cache_data(ttl=21600)
def backtest(tickers,years,step,topn):
    end=pd.Timestamp.today().normalize()+pd.Timedelta(days=1);start=end-pd.DateOffset(years=years);warm=start-pd.Timedelta(days=450)
    cache={t:px(t,start=warm.strftime("%Y-%m-%d"),end=end.strftime("%Y-%m-%d")) for t in tickers}
    spy=px("SPY",start=start.strftime("%Y-%m-%d"),end=end.strftime("%Y-%m-%d"));qqq=px("QQQ",start=start.strftime("%Y-%m-%d"),end=end.strftime("%Y-%m-%d"))
    if spy.empty or qqq.empty:return pd.DataFrame(),pd.DataFrame()
    dates=spy.index;periods=[];picks=[]
    for dt in dates[::step]:
        fut=dates[dates>dt]
        if len(fut)==0:continue
        nxt=fut[min(step-1,len(fut)-1)];sc=[]
        for t,x in cache.items():
            xx=x.loc[:dt]
            z=wfscore(xx)
            if z is not None:sc.append((t,z))
        sc=sorted(sc,key=lambda z:z[1],reverse=True)[:topn];rets=[]
        for rank,(t,z) in enumerate(sc,1):
            x=cache[t]
            if dt not in x.index or nxt not in x.index:continue
            e=float(x.loc[dt,"Close"]);q=float(x.loc[nxt,"Close"]);r=q/e-1;rets.append(r)
            picks.append({"Date":dt.date(),"Rank":rank,"Ticker":t,"Score":z,"Entry":round(e,2),"Exit":round(q,2),"Return %":round(r*100,2)})
        if rets:periods.append({"Date":dt.date(),"StockPulse %":np.mean(rets)*100,"SPY %":(float(spy.loc[nxt,"Close"])/float(spy.loc[dt,"Close"])-1)*100,"QQQ %":(float(qqq.loc[nxt,"Close"])/float(qqq.loc[dt,"Close"])-1)*100,"Top N":len(rets)})
    return pd.DataFrame(periods),pd.DataFrame(picks)
def stats(s):
    r=pd.to_numeric(s,errors="coerce").dropna()/100
    if r.empty:return [0,0,0,0]
    e=(1+r).cumprod();yrs=max(len(r)*20/252,1/252);dd=e/e.cummax()-1
    return [(e.iloc[-1]**(1/yrs)-1)*100,(e.iloc[-1]-1)*100,dd.min()*100,(r>0).mean()*100]
st.markdown('<div class="sp">📈 StockPulse <span style="color:#2563eb">Lite V5.3</span></div><div class="sub">Daily stock discovery + walk-forward validation • free data</div>',unsafe_allow_html=True)
st.markdown('<div class="note"><b>Important:</b> research signals only. Backtests are not guarantees of future profits.</div>',unsafe_allow_html=True)
with st.sidebar:
    raw=st.text_area("Universe"," ".join(UNIVERSE),height=220);tickers=sorted(set(raw.replace(","," ").split()))
    if st.button("Refresh data"):st.cache_data.clear();st.rerun()
m1,m2,m3=st.columns(3);m1.metric("Universe",len(tickers));m2.metric("Mode","Free data");m3.metric("Validation","Walk-forward")
tab1,tab2=st.tabs(["🔥 Daily Top 10","🧪 Walk-Forward Backtest"])
with tab1:
    rows=[];bar=st.progress(0)
    for i,t in enumerate(tickers):
        x=px(t,period="1y")
        if len(x)>=180 and float((x.Close*x.Volume).rolling(20).mean().iloc[-1])>=20_000_000 and float(x.Close.iloc[-1])>=5:
            z=score(t,x)
            if z:rows.append(z)
        bar.progress((i+1)/len(tickers))
    bar.empty();df=pd.DataFrame(rows,columns=["Ticker","Score","Action","Price","Stop","Target","RSI","Vol x"]).sort_values("Score",ascending=False)
    st.dataframe(df.head(10),use_container_width=True,hide_index=True)
    st.caption("Stop/target are model reference levels, not guaranteed execution prices.")
with tab2:
    a,b,c=st.columns(3);years=a.selectbox("History",[1,2,3,5],2);step=b.selectbox("Rebalance",[5,10,20],2);topn=c.selectbox("Portfolio",[5,10],1)
    if st.button("▶ Run walk-forward backtest",type="primary"):
        with st.spinner("Replaying history without using future data…"):bt,picks=backtest(tuple(tickers),years,step,topn)
        st.session_state.bt=bt;st.session_state.picks=picks
    if "bt" in st.session_state and not st.session_state.bt.empty:
        bt=st.session_state.bt;picks=st.session_state.picks;ps,ss,qs=stats(bt["StockPulse %"]),stats(bt["SPY %"]),stats(bt["QQQ %"])
        x,y,z,w=st.columns(4);x.metric("StockPulse CAGR",f"{ps[0]:.1f}%");y.metric("SPY CAGR",f"{ss[0]:.1f}%");z.metric("QQQ CAGR",f"{qs[0]:.1f}%");w.metric("Win rate",f"{ps[3]:.0f}%")
        st.dataframe(pd.DataFrame([["StockPulse",*ps],["SPY",*ss],["QQQ",*qs]],columns=["Strategy","CAGR %","Total %","Max DD %","Win %"]),use_container_width=True,hide_index=True)
        st.subheader("Historical periods");st.dataframe(bt,use_container_width=True,hide_index=True)
        st.subheader("Every historical recommendation");st.dataframe(picks,use_container_width=True,hide_index=True)
        st.download_button("⬇️ Download recommendation history",picks.to_csv(index=False),"stockpulse_v5_3_history.csv","text/csv")
    else:st.info("Choose settings and run the backtest.")
st.caption("V5.3 • free-data mode • historical performance is not a promise of future returns")
