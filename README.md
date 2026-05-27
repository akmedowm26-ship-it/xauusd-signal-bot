# xauusd-signal-bot
import requests,time,math
from datetime import datetime
BOT_TOKEN='8986336022:AAEAlUuwqSddsp7n5XBqhe3moofun6aPecc'
CHAT_ID='7431522485'
FAST,MID,SLOW,VLB=9,16,25,4
last_signal=None
def tg(msg):
 try:requests.post(f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage',data={'chat_id':CHAT_ID,'text':msg,'parse_mode':'HTML'},timeout=10)
 except:pass
def wma(d,p):
 if len(d)<p:return None
 w=list(range(1,p+1));return sum(x*y for x,y in zip(d[-p:],w))/sum(w)
def hma(d,l):
 h=round(l/2);s=round(math.sqrt(l))
 if len(d)<l+s+5:return None
 rb=[]
 for i in range(s+2):
  sl=d[:len(d)-i];w1=wma(sl,h);w2=wma(sl,l)
  rb.insert(0,2*w1-w2 if w1 and w2 else 0)
 w=list(range(1,s+1));seg=rb[-s:]
 return sum(seg[j]*w[j] for j in range(s))/sum(w)
def vel(d,l,lb):
 h1=hma(d,l);h2=hma(d[:-lb],l) if len(d)>lb else None
 return h1-h2 if h1 and h2 else None
def candles():
 try:
  r=requests.get('https://query1.finance.yahoo.com/v8/finance/chart/GC=F',params={'interval':'1m','range':'1d'},headers={'User-Agent':'Mozilla/5.0'},timeout=15)
  c=r.json()['chart']['result'][0]['indicators']['quote'][0]['close']
  return [x for x in c if x]
 except:return []
tg('🤖 <b>AMVR Bot bashlandy!</b>\nXAUUSD 1M barlanyyar...')
print('Bot isleyar...')
while True:
 try:
  c=candles();now=datetime.now().strftime('%H:%M:%S')
  if len(c)<60:print(f'[{now}] Garasylyyar...');time.sleep(30);continue
  v1=vel(c,FAST,VLB);v1p=vel(c[:-1],FAST,VLB);p=c[-1]
  print(f'[{now}] Baha:{p:.2f}')
  if v1 and v1p:
   if v1p<=0 and v1>0 and last_signal!='BUY':
    last_signal='BUY'
    tg(f'🟢 <b>BUY SIGNAL!</b>\n💵 Baha: {p:.2f}\n🕐 {now}\n⚡ BUY ac!')
   elif v1p>=0 and v1<0 and last_signal!='SELL':
    last_signal='SELL'
    tg(f'🔴 <b>SELL SIGNAL!</b>\n💵 Baha: {p:.2f}\n🕐 {now}\n⚡ SELL ac!')
  time.sleep(30)
 except Exception as e:print(f'Hata:{e}');time.sleep(30)
 
