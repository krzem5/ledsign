import json
import os
import subprocess
import sys



if (not os.path.exists("build")):
	os.mkdir("build")
with open("build/.coveragerc","w") as wf:
	wf.write("[report]\nexclude_also=\n    def __repr__\n")
subprocess.run(["python3","-m","coverage","run","--branch","--data-file","build/coverage","--include=ledsign/*","--omit=ledsign/backend.py","test"],env={"PYTHONPATH":"."})
subprocess.run(["python3","-m","coverage","json","--data-file","build/coverage","-o","build/coverage.json","-q","--rcfile=build/.coveragerc"])
subprocess.run(["python3","-m","coverage","html","--data-file","build/coverage","-d","build/coverage_html","-q","--rcfile=build/.coveragerc"])
with open("build/coverage.json","r") as rf:
	stats=json.loads(rf.read())["totals"]
with open("build/test_result.txt","r") as rf:
	passed_tests,failed_tests=map(int,rf.read().strip().split(","))
print(f"Passed tests: {passed_tests}, failed tests: {failed_tests}, coverage: {stats["percent_covered"]:.2f}%")
sys.exit((1 if failed_tests else 0))
