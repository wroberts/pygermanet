=================
 Packaging Notes
=================

python setup.py sdist
python setup.py bdist_wheel
python3.4 setup.py bdist_wheel
twine upload dist/*
