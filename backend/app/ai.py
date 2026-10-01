import json, os, re
from pathlib import Path
import httpx

FACT_KEYS = ["account_id","transaction_id","amount","timestamp","sender_account","receiver_account","sender_ifsc","receiver_ifsc"]

def _facts(evidence):
    accounts={n['id'] for n in evidence.get('nodes',[])}
    txs=evidence.get('edges',[])
    amounts={f"{float(t['amount']):.2f}" for t in txs}
    txids={t['id'] for t in txs}
    return accounts,amounts,txids

def validate_output(text,evidence):
    accounts,amounts,txids=_facts(evidence)
    # Strong guard: every 12-ish account-looking token in output must exist in evidence.
    tokens=re.findall(r"\b[A-Z]{4,6}\d{8,12}\b",text)
    bad=[t for t in tokens if t not in accounts]
    # Every transaction ID with TXN prefix must be in evidence.
    tx_tokens=re.findall(r"\bTXN[A-Za-z0-9]+\b",text)
    bad += [t for t in tx_tokens if t not in txids]
    # INR numeric values: permit dates and section numbers, but reject obvious fabricated amounts.
    money=re.findall(r"(?:₹|INR\s*)\s*([0-9][0-9,]*(?:\.[0-9]{1,2})?)",text,flags=re.I)
    bad_money=[]
    for m in money:
        n=f"{float(m.replace(',','')):.2f}"
        if n not in amounts: bad_money.append(m)
    return {"valid":not bad and not bad_money,"fabricated_accounts":bad,"fabricated_amounts":bad_money}

def deterministic(e,kind):
    r=e['risk']; victim=e['victim']; edges=e['edges']; nodes=e['nodes']
    lines=[f"OFFLINE FORENSIC DRAFT — {kind.replace('_',' ').title()}","",f"Subject account: {victim}",f"Mule Risk Index: {r['risk_score']}/100",f"Detected layer: {r['layer']}","","Observed transaction trail:"]
    for x in edges[:100]:
        lines.append(f"{x['timestamp']} | {x['source']} -> {x['target']} | INR {x['amount']:.2f} | {x['id']}")
    lines += ["","This is a machine-generated factual draft for officer/legal review. Facts are limited to the supplied transaction evidence."]
    return "\n".join(lines)

def generate_document(evidence,kind):
    payload=json.dumps(evidence,default=str,separators=(',',':'))
    text=None; model_used=False
    try:
        model=os.getenv('OLLAMA_MODEL','llama3.2:3b')
        prompt=("You are an evidence formatter. Use ONLY facts present in the JSON evidence. "
                "Do not invent or infer account numbers, amounts, transaction IDs, IFSCs or timestamps. "
                "Return a factual draft for officer/legal review. If a fact is absent, omit it. "
                "Do not add citations or external facts.\nEVIDENCE JSON:\n"+payload)
        resp=httpx.post('http://127.0.0.1:11434/api/generate',json={'model':model,'prompt':prompt,'stream':False},timeout=20)
        if resp.status_code==200:
            text=resp.json().get('response','').strip(); model_used=True
    except Exception:
        pass
    if not text: text=deterministic(evidence,kind)
    validation=validate_output(text,evidence)
    if not validation['valid']:
        text=deterministic(evidence,kind)
        validation=validate_output(text,evidence)
    return {"kind":kind,"model_used":model_used,"validated":validation['valid'],"validation":validation,"text":text,"evidence":evidence}
