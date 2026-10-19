PYTHON ?= .venv/bin/python

.PHONY: instalar infografia verificar pruebas intervalos todo limpiar

instalar:
	python3 -m venv .venv
	$(PYTHON) -m pip install -r requirements.txt

infografia:
	$(PYTHON) scripts/crear_infografia.py

verificar:
	$(PYTHON) scripts/verificar_entrega.py

pruebas:
	$(PYTHON) -m pytest -q

# Solo si se necesita repetir el ajuste de Prophet.
intervalos:
	$(PYTHON) scripts/recuperar_intervalos.py

todo: pruebas infografia verificar

limpiar:
	rm -rf tmp .pytest_cache scripts/__pycache__ tests/__pycache__
