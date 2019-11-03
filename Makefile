
test.html: test.template.html generate.py
	#python3 generate.py $< > $@
	python3 generate.py $<
