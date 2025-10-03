import json
import subprocess



subprocess.run(["python3","-m","coverage","run","--branch","--data-file","build/coverage","--include=ledsign/*","--omit=ledsign/backend.py","test","--run"],env={"PYTHONPATH":"."})
subprocess.run(["python3","-m","coverage","json","--data-file","build/coverage","-o","build/coverage.json","-q"])
subprocess.run(["python3","-m","coverage","html","--data-file","build/coverage","-d","build/coverage_html","-q"])
with open("build/coverage.json","r") as rf:
	stats=json.loads(rf.read())["totals"]
print(f"Coverage: {stats["percent_covered"]:.2f}%")
