run:
	python src/main.py $(ID)

clean:
	rm -rf src/models/__pycache__
	rm -rf src/utils/__pycache__