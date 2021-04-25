
test.html: test.template.html generate.py
	mkdir -p output
	python3 generate.py $<

INPUTS = $(wildcard ../Archive/Garmin/*.FIT)
OUTPUTS = $(patsubst ../Archive/Garmin/%.FIT, cache/%.xml, $(INPUTS))

outputs: $(OUTPUTS)

$(OUTPUTS): cache/%.xml: ../Archive/Garmin/%.FIT
	$(HOME)/local/lib/garmin/fit2tcx $< > /tmp/OUT
	mkdir -p cache
	mv /tmp/OUT $@

loop:
	,watch make -- *.html *.py

push:
	cp output/*.html ~/rhodesmill.org/brandon/tracks
	,push
