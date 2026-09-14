from pathlib import Path
import re,math
from collections import Counter
from app.config import settings
from app.models import RAGResult
def tok(x): return re.findall(r"[a-zA-Z0-9_]+",x.lower())
def docs():
    return [(p.stem.replace("_"," ").title(),p.read_text()) for p in Path(settings.knowledge_base_dir).glob("*.md")]
def score(q,d):
    a,b=Counter(tok(q)),Counter(tok(d)); common=set(a)&set(b)
    den=math.sqrt(sum(v*v for v in a.values())*sum(v*v for v in b.values()))
    return sum(a[x]*b[x] for x in common)/den if den else 0
def retrieve(q,k=None):
    r=sorted([(t,c,score(q,c)) for t,c in docs()],key=lambda x:x[2],reverse=True)
    return [RAGResult(title=t,content=c,score=round(s,4)) for t,c,s in r[:k or settings.top_k]]
