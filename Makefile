
test.html: test.template.html generate.py
	mkdir -p output
	python3 generate.py $<

loop:
	,watch make -- *.html *.py
