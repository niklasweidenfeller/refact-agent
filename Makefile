java-tennis:
	python src/main.py samples/java_tennis .
java-gilded-rose:
	python src/main.py samples/java_gilded_rose .
java: java-tennis java-gilded-rose

python-tennis:
	python src/main.py samples/python_tennis .
python-yahtzee:
	python src/main.py samples/python_yahtzee .
python: python-tennis python-yahtzee

javascript-gilded-rose:
	python src/main.py samples/js_gilded_rose src
javascript-json-parser:
	python src/main.py samples/js_json_object src
javascript: javascript-gilded-rose javascript-json-parser


all: java python javascript
