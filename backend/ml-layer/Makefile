# Invoked by `sam build` (see MLLayer's Metadata.BuildMethod: makefile in
# infrastructure/template.yaml) — NOT run directly.
#
# Pulls prebuilt manylinux wheels for the Lambda's exact runtime instead of
# compiling from source, which matters here: pandas/numpy/scikit-learn/xgboost
# don't build cleanly from source against newer CPython header changes, and
# plain `pip install` (no platform flags) resolves wheels for whatever OS
# you're running `sam build` on, not for Lambda's Linux runtime.
build-MLLayer:
	pip3 install \
		--platform manylinux2014_x86_64 \
		--python-version 3.13 \
		--implementation cp \
		--only-binary=:all: \
		--target "$(ARTIFACTS_DIR)/python" \
		-r requirements.txt
