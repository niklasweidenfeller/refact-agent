java-tennis:
	python src/main.py samples/java_tennis .
java-gilded-rose:
	python src/main.py samples/java_gilded_rose .
java-yahtzee:
	python src/main.py samples/java_yahtzee .
java-tabula:
	python src/main.py samples/java_tabula src/main/java
java: java-tennis java-gilded-rose java-yahtzee java-tabula

python-tennis:
	python src/main.py samples/py_tennis .
python-yahtzee:
	python src/main.py samples/py_yahtzee .
python: python-tennis python-yahtzee

javascript-gilded-rose:
	python src/main.py samples/js_gilded_rose src
javascript-json-parser:
	python src/main.py samples/js_json_object src
javascript-trivia:
	python src/main.py samples/js_trivia .
javascript: javascript-gilded-rose javascript-json-parser javascript-trivia


all: java python javascript
