PYFILES := $(shell find control -name "*.py")
EXE := control.zip

.PHONY: test build clean reallyclean

build: $(EXE)

$(EXE): $(PYFILES)
	@-rm $(EXE) controli.zip
	cp control/__main__.py .
	zip -r controli.zip __main__.py control -x "control/tests*"
	rm __main__.py
	echo "#!/usr/bin/env python3" > $(EXE)
	cat controli.zip >> $(EXE)
	-rm controli.zip
	chmod +x $(EXE)

test:
	py.test -v --cov-config .coveragerc --cov-report term-missing:skip-covered --cov=control --junitxml results.xml control/tests

jenkins-test:
	-py.test -v --cov-config .coveragerc --cov-report xml --cov=control --junitxml results.xml control/tests

clean:
	-rm $(EXE)

reallyclean: clean
	-rm -r **/__pycache__ __pycache__
	-rm **/*pyc *pyc
	-rm **/results*.xml results*.xml **/.coverage .coverage **/coverage.xml coverage.xml
	-rm **/*,cover *,cover
