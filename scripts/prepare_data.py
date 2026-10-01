import argparse, time, os, shutil
from pathlib import Path
import duckdb

SCHEMA = {
'Transaction_ID':'VARCHAR','Sender_Account':'VARCHAR','Receiver_Account':'VARCHAR','Sender_IFSC':'VARCHAR','Receiver_IFSC':'VARCHAR','Amount':'DOUBLE','Timestamp':'TIMESTAMP','Payment_Mode':'VARCHAR','Narration':'VARCHAR','IP_Address':'VARCHAR','Device_Type':'VARCHAR'}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--csv',required=True); ap.add_argument('--db',default='data/duckdb/abhedya.duckdb'); args=ap.parse_args()
    csv=Path(args.csv); db=Path(args.db); db.parent.mkdir(parents=True,exist_ok=True)
    if db.exists(): db.unlink()
    con=duckdb.connect(str(db))
    con.execute("PRAGMA threads=4")
    con.execute("PRAGMA memory_limit='10GB'")
    cols=','.join([f"'{k}':'{v}'" for k,v in SCHEMA.items()])
    start=time.perf_counter()
    con.execute(f'''CREATE TABLE transactions AS SELECT * FROM read_csv(?, header=true, columns={{{cols}}}, sample_size=-1, ignore_errors=false)''',[str(csv)])
    ingest=time.perf_counter()-start
    # Derived columns used by terminal heuristics.
    con.execute('''ALTER TABLE transactions ADD COLUMN ip_anomaly BOOLEAN''')
    con.execute('''ALTER TABLE transactions ADD COLUMN headless_device BOOLEAN''')
    con.execute('''ALTER TABLE transactions ADD COLUMN terminal_narration BOOLEAN''')
    con.execute('''UPDATE transactions SET ip_anomaly=regexp_matches(IP_Address,'^(185\\.|194\\.)'), headless_device=lower(Device_Type) IN ('web_emulator','linux_script'), terminal_narration=regexp_matches(lower(coalesce(Narration,'')),'wallet|crypto|p2p|cash|atm|usdt|binance')''')
    con.execute("CREATE INDEX idx_tx_sender ON transactions(Sender_Account)")
    con.execute("CREATE INDEX idx_tx_receiver ON transactions(Receiver_Account)")
    con.execute("CREATE INDEX idx_tx_id ON transactions(Transaction_ID)")
    con.execute('''CREATE TABLE accounts AS 
      WITH a AS (SELECT Sender_Account account_id, min(Timestamp) first_seen, max(Timestamp) last_seen, 0.0 total_in, sum(Amount) total_out, 0 in_degree, count(*) out_degree FROM transactions GROUP BY 1),
      b AS (SELECT Receiver_Account account_id, min(Timestamp) first_seen, max(Timestamp) last_seen, sum(Amount) total_in, 0.0 total_out, count(*) in_degree, 0 out_degree FROM transactions GROUP BY 1),
      u AS (SELECT account_id, min(first_seen) first_seen, max(last_seen) last_seen, sum(total_in) total_in, sum(total_out) total_out, sum(in_degree) in_degree, sum(out_degree) out_degree FROM (SELECT * FROM a UNION ALL SELECT * FROM b) GROUP BY 1)
      
    SELECT *,
       CAST(0.0 AS DOUBLE) AS risk_score,
       'Observed' AS layer,
       CAST(0.0 AS DOUBLE) AS velocity_ratio,
       CAST(0.0 AS DOUBLE) AS terminal_score
FROM u
  ''')

    # Cheap deterministic terminal aggregates.
  
    con.execute('''UPDATE accounts SET terminal_score = LEAST(25.0, 25.0 * (SELECT LEAST(1.0, SUM(CASE WHEN ip_anomaly OR headless_device OR terminal_narration
            THEN 1
            ELSE 0
        END
    ) / 3.0)
    FROM transactions t
    WHERE t.Sender_Account = accounts.account_id
       OR t.Receiver_Account = accounts.account_id
))''')
    # Initial structural score; request-time detector adds precise velocity features.
    con.execute('''UPDATE accounts SET risk_score = LEAST(100.0,
      LEAST(15.0,in_degree*3.0)+
      CASE WHEN out_degree BETWEEN 3 AND 7 THEN 15.0 ELSE LEAST(15.0,out_degree*2.0) END+
      terminal_score
    ),
    layer=CASE WHEN in_degree>=5 AND in_degree>out_degree THEN 'L1 Collector' WHEN out_degree BETWEEN 3 AND 7 THEN 'L2 Distributor' WHEN terminal_score>0 THEN 'L3 Terminal' ELSE 'Observed' END''')
    con.execute("CREATE INDEX idx_accounts_id ON accounts(account_id)")
    con.execute("CHECKPOINT")
    total=con.execute('SELECT count(*) FROM transactions').fetchone()[0]
    accts=con.execute('SELECT count(*) FROM accounts').fetchone()[0]
    print(f'INGESTED_ROWS={total}')
    print(f'ACCOUNTS={accts}')
    print(f'INGEST_SECONDS={ingest:.3f}')
    print(f'DB_SIZE_MB={db.stat().st_size/1024/1024:.1f}')
    con.close()

if __name__=='__main__': main()
