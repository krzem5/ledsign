import setuptools



VERSION="0.8.0"



with open("README.md","r") as rf:
	description=rf.read()
setuptools.setup(
	name="ledsign",
	version=VERSION,
	description="LED Sign Python API",
	long_description=description,
	long_description_content_type="text/markdown",
	author="Krzesimir Hyżyk",
	url="https://github.com/krzem5/ledsign",
	packages=["ledsign"],
    python_requires=">=3.9",
	classifiers=[
		"Development Status :: 4 - Beta",
		"Intended Audience :: End Users/Desktop",
		"Natural Language :: English",
		"Operating System :: Microsoft :: Windows",
		"Operating System :: POSIX :: Linux",
		"Programming Language :: Python",
		"Programming Language :: Python :: 3.9",
		"Programming Language :: Python :: 3.10",
		"Programming Language :: Python :: 3.11",
		"Programming Language :: Python :: 3.12",
		"Programming Language :: Python :: 3.13"
	],
	license="BSD-3-Clause",
	install_requires=[],
	project_urls={
		"Source Code": "https://github.com/krzem5/ledsign",
		"Documentation": "https://ledsign.readthedocs.io/en/latest/",
	}
)
