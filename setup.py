import setuptools



VERSION="0.1.0"



with open("README.md","r") as rf:
	description=rf.read()
setuptools.setup(
	name="ledsign",
	version=VERSION,
	description="LED Sign controller",
	url="https://github.com/krzem5/ledsign",
	project_urls={
		"Source Code": "https://github.com/krzem5/ledsign",
	},
	author="Krzesimir Hyżyk",
	license="BSD-3-Clause license",
	classifiers=[],
	python_requires=">=3.9",
	install_requires=[],
	packages=["ledsign"],
	long_description=description,
	long_description_content_type="text/markdown"
)
