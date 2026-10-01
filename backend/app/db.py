from pathlib import Path
import duckdb

class DB:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.con = duckdb.connect(str(self.path), read_only=self.path.exists()) if self.path.exists() else None

    def exists(self):
        return self.path.exists()

    def _c(self):
        if self.con is None:
            self.con = duckdb.connect(str(self.path), read_only=True)
        return self.con

    def stats(self):
        c=self._c()
        r=c.execute("SELECT (SELECT COUNT(*) FROM transactions), (SELECT COUNT(*) FROM accounts)").fetchone()
        return {"transactions":r[0],"accounts":r[1]}

    def account_exists(self, a):
        return self._c().execute("SELECT 1 FROM accounts WHERE account_id=? LIMIT 1",[a]).fetchone() is not None

    def search_accounts(self,q,limit):
        rows=self._c().execute("SELECT account_id, risk_score, layer, total_in, total_out, in_degree, out_degree FROM accounts WHERE account_id ILIKE ? ORDER BY risk_score DESC LIMIT ?",[f"%{q}%",limit]).fetchall()
        return [dict(zip(["account_id","risk_score","layer","total_in","total_out","in_degree","out_degree"],r)) for r in rows]

    def account_summary(self,a):
        row=self._c().execute("SELECT account_id, first_seen, last_seen, total_in, total_out, in_degree, out_degree, risk_score, layer, velocity_ratio, terminal_score FROM accounts WHERE account_id=?",[a]).fetchone()
        if not row:return None
        keys=["account_id","first_seen","last_seen","total_in","total_out","in_degree","out_degree","risk_score","layer","velocity_ratio","terminal_score"]
        return dict(zip(keys,row))

    def account_transactions(self,a,limit):
        q='''SELECT transaction_id,sender_account,receiver_account,amount,timestamp,payment_mode,narration,ip_address,device_type,sender_ifsc,receiver_ifsc FROM transactions WHERE sender_account=? OR receiver_account=? ORDER BY timestamp LIMIT ?'''
        rows=self._c().execute(q,[a,a,limit]).fetchall()
        cols=["transaction_id","sender_account","receiver_account","amount","timestamp","payment_mode","narration","ip_address","device_type","sender_ifsc","receiver_ifsc"]
        return [dict(zip(cols,r)) for r in rows]

    def outgoing(self,a,limit=5000):
        q='''SELECT transaction_id,sender_account,receiver_account,amount,timestamp,payment_mode,narration,ip_address,device_type,sender_ifsc,receiver_ifsc FROM transactions WHERE sender_account=? ORDER BY timestamp LIMIT ?'''
        rows=self._c().execute(q,[a,limit]).fetchall()
        cols=["transaction_id","sender_account","receiver_account","amount","timestamp","payment_mode","narration","ip_address","device_type","sender_ifsc","receiver_ifsc"]
        return [dict(zip(cols,r)) for r in rows]

    def incoming(self,a,limit=5000):
        q='''SELECT transaction_id,sender_account,receiver_account,amount,timestamp,payment_mode,narration,ip_address,device_type,sender_ifsc,receiver_ifsc FROM transactions WHERE receiver_account=? ORDER BY timestamp LIMIT ?'''
        rows=self._c().execute(q,[a,limit]).fetchall()
        cols=["transaction_id","sender_account","receiver_account","amount","timestamp","payment_mode","narration","ip_address","device_type","sender_ifsc","receiver_ifsc"]
        return [dict(zip(cols,r)) for r in rows]
