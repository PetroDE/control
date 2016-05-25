PYFILES := $(shell find control -name "*.py")
EXE := control.zip

.PHONY: test build clean

build: $(EXE)

$(EXE): $(PYFILES)
	@-rm $(EXE) controli.zip
	cd control && zip -R ../controli.zip **.py
	echo "#!/usr/bin/env python3" > $(EXE)
	cat controli.zip >> $(EXE)
	-rm controli.zip
	chmod +x $(EXE)

test:
	py.test -v --junitxml results.xml tests

clean:
	-rm $(EXE)
