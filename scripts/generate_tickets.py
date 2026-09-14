import json,random
from datetime import datetime,timedelta
from pathlib import Path
random.seed(42)
profiles=[("Assessment","Assessment Support",.31),("Login","General Support",.18),("Password","General Support",.14),("Billing","Billing Support",.10),("Account","Account Support",.09),("Technical","Technical Support",.08),("Plagiarism","Trust & Safety",.04),("Security","Security Support",.03),("Other","General Support",.03)]
templates={"Assessment":[("Assessment submitted after browser crash","My browser crashed during my assessment and when I reopened it the assessment was already submitted. My interview is tomorrow."),("Cannot access assessment","I received the assessment link but it says the test is no longer available."),("Assessment terminated unexpectedly","My assessment suddenly ended while I was solving a problem. I need someone to check what happened."),("Wrong assessment result","I believe my assessment score is incorrect and I want the result reviewed.")],"Login":[("Cannot log in","I keep getting an error when trying to sign in to my account."),("Login failure before interview","I cannot access my account and my interview is later today.")],"Password":[("Forgot password","I forgot my password. How can I reset it?"),("Password reset link expired","The password reset link I received has expired. Please help.")],"Billing":[("Duplicate charge","I was charged twice for the same service and would like this investigated."),("Refund request","I want a refund for a payment I made."),("Invoice question","I need help understanding a charge on my invoice.")],"Account":[("Account access issue","I cannot access part of my account and need help."),("Profile information change","I need to change information on my account.")],"Technical":[("Editor not loading","The coding editor is stuck loading and I cannot start the challenge."),("Compilation problem","The platform is showing an unexpected compilation error.")],"Plagiarism":[("Plagiarism flag dispute","My submission was flagged and I believe the decision is incorrect. Please review it.")],"Security":[("Suspicious login alert","I received a login alert from a location I do not recognize. I think someone accessed my account.")],"Other":[("General support question","I need help with an issue on the platform.")]}
sevs={"Assessment":["LOW","MEDIUM","HIGH","CRITICAL"],"Login":["LOW","LOW","MEDIUM","HIGH"],"Password":["LOW","LOW","LOW","MEDIUM"],"Billing":["LOW","MEDIUM","MEDIUM","HIGH"],"Account":["LOW","MEDIUM","HIGH"],"Technical":["LOW","MEDIUM","HIGH"],"Plagiarism":["MEDIUM","HIGH","CRITICAL"],"Security":["HIGH","CRITICAL"],"Other":["LOW","MEDIUM"]}
names=["Aarav Sharma","Ananya Iyer","Rohan Mehta","Meera Nair","Kabir Singh","Diya Rao","Arjun Patel","Ishita Gupta"]
start=datetime.utcnow()-timedelta(days=30); out=[]
for i in range(10000):
    x=random.random(); cum=0
    for cat,team,w in profiles:
        cum+=w
        if x<=cum: break
    subject,msg=random.choice(templates[cat]); created=start+timedelta(minutes=random.randint(0,30*24*60))
    out.append({"ticket_id":f"HR-{100001+i}","customer_name":random.choice(names),"subject":subject,"message":msg,"category":cat,"severity":random.choice(sevs[cat]),"team":team,"created_at":created.isoformat()})
Path("data/tickets.json").write_text(json.dumps(out),encoding="utf-8"); print("Generated",len(out),"tickets")
