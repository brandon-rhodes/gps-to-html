
test.html: test.template.html generate.py
	mkdir -p output
	python3 generate.py $<

INPUTS = $(wildcard ../garmin/*.FIT)
OUTPUTS = $(patsubst ../garmin/%.FIT, cache/%.xml, $(INPUTS))

outputs: $(OUTPUTS)

$(OUTPUTS): cache/%.xml: ../garmin/%.FIT
	$(HOME)/usr/lib/garmin/fit2tcx $< > /tmp/OUT
	mv /tmp/OUT $@

loop:
	,watch make -- *.html *.py

push:
	cp output/*.html ~/rhodesmill.org/brandon/tracks
	,push
