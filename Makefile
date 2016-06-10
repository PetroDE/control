PYFILES := $(shell find control -name "*.py")
EXE := control.zip

.PHONY: test build clean

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
	py.test -v --junitxml results.xml tests

clean:
	-rm $(EXE)

reallyclean:
	-rm $(EXE)
	-rm -r **/*/__pycache__
	-rm **/*pyc
