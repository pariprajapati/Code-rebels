from collections import defaultdict, deque
from datetime import timedelta
import re

WALLET = re.compile(r"wallet|crypto|p2p|cash|atm|usdt|binance|paytm|upi/wallet", re.I)
HEADLESS = {"web_emulator","linux_script"}

class Detector:
    def __init__(self,db): self.db=db

    def _features(self,a):
        inc=self.db.incoming(a); out=self.db.outgoing(a)
        senders={x['sender_account'] for x in inc}; receivers={x['receiver_account'] for x in out}
        fanin=len(senders); fanout=len(receivers)
        anomalous_ip=sum(1 for x in inc+out if str(x['ip_address']).startswith(('185.','194.')))
        headless=sum(1 for x in inc+out if str(x['device_type']).lower() in HEADLESS)
        terminal_narr=sum(1 for x in inc+out if WALLET.search(str(x['narration'] or '')))
        velocity_ratios=[]
        # For each incoming transfer, calculate the fraction of its amount matched by
        # subsequent outgoing transfers within the requested 3–15 minute window.
        for i in inc[:2000]:
            t=i['timestamp']; amt=float(i['amount'] or 0)
            if not t or amt<=0: continue
            s=0.0
            for o in out:
                dt=(o['timestamp']-t).total_seconds() if o['timestamp'] else 999999
                if 180 <= dt <= 900:
                    s += float(o['amount'] or 0)
            velocity_ratios.append(min(1.0,s/amt))
        velocity=max(velocity_ratios) if velocity_ratios else 0.0
        velocity_hits=sum(1 for x in velocity_ratios if x>=0.90)
        return dict(fanin=fanin,fanout=fanout,velocity_ratio=velocity,velocity_hits=velocity_hits,anomalous_ip=anomalous_ip,headless=headless,terminal_narr=terminal_narr,total_in=sum(float(x['amount'] or 0) for x in inc),total_out=sum(float(x['amount'] or 0) for x in out))

    def risk(self,a):
        f=self._features(a)
        velocity_pts=30.0*min(1.0,f['velocity_ratio']/0.90) if f['velocity_ratio'] else 0
        fanin_pts=15.0*min(1.0,f['fanin']/5.0)
        fanout_pts=15.0*(1.0 if 3<=f['fanout']<=7 else min(1.0,f['fanout']/7.0))
        terminal_raw=f['anomalous_ip']+f['headless']+f['terminal_narr']
        terminal_pts=25.0*min(1.0,terminal_raw/3.0)
        behavior_pts=15.0*min(1.0,(f['velocity_hits']+max(0,f['fanin']-1))/10.0)
        score=round(min(100,velocity_pts+fanin_pts+fanout_pts+terminal_pts+behavior_pts),2)
        layer='L1 Collector' if f['fanin']>=5 and f['fanin']>f['fanout'] else ('L2 Distributor' if 3<=f['fanout']<=7 else ('L3 Terminal' if terminal_raw else 'Observed'))
        return {"account_id":a,"risk_score":score,"layer":layer,"features":f,"points":{"velocity":round(velocity_pts,2),"fan_in":round(fanin_pts,2),"fan_out":round(fanout_pts,2),"terminal":round(terminal_pts,2),"behavior":round(behavior_pts,2)}}

    def investigate(self,root,hops=4):
        # BFS using DuckDB account lookups. Only the selected subgraph is returned.
        nodes={root:{"id":root,"label":root,"depth":0,"layer":"Victim"}}
        edges=[]; seen={root}; q=deque([(root,0)])
        while q:
            a,d=q.popleft()
            if d>=hops: continue
            outs=self.db.outgoing(a,3000)
            for tx in outs:
                b=tx['receiver_account']
                if b not in nodes:
                    rr=self.risk(b)
                    nodes[b]={"id":b,"label":b,"depth":d+1,"layer":rr['layer'],"risk_score":rr['risk_score']}
                edges.append({"id":tx['transaction_id'],"source":a,"target":b,"amount":float(tx['amount']),"timestamp":tx['timestamp'].isoformat() if tx['timestamp'] else None,"payment_mode":tx['payment_mode'],"narration":tx['narration'],"ip_address":tx['ip_address'],"device_type":tx['device_type']})
                if b not in seen:
                    seen.add(b); q.append((b,d+1))
        root_risk=self.risk(root)
        return {"victim":root,"hops":hops,"risk":root_risk,"nodes":list(nodes.values()),"edges":edges}
