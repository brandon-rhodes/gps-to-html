
test.html: test.template.html generate.py
	mkdir -p output
	python3 generate.py $<

loop:
	,watch make -- *.html *.py

push:
	cp output/*.html ~/rhodesmill.org/brandon/tracks
	,push
