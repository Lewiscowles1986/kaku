.PHONY: help clean install install-hook install-uwsgi install-dev info server uwsgi

help:
	@echo "This project assumes that an active Python virtualenv is present."
	@echo "The following make targets are available:"
	@echo "  env         install all production dependencies"
	@echo "  dev         install all dev and production dependencies (pyenv is assumed)"
	@echo "  clean       remove unwanted files"
	@echo "  lint        flake8 lint check"
	@echo "  test        run unit tests"
	@echo "  coverage    run code coverage"
	@echo "  ci          run CI tests"

install-hook:
	git-pre-commit-hook install --force --plugins json --plugins yaml --plugins flake8 \
                              --flake8_ignore E111,E124,E126,E201,E202,E221,E241,E302,E501,N802,N803

install-uwsgi:
	pip install uwsgi

env:
	pyenv install -s 2.7.12
	pyenv install -s 3.5.2
	pyenv local 2.7.12 3.5.2
	pip install -U pip

dev: env
	pip install -Ur requirements.txt
	pip install -Ur requirements-test.txt

info:
	@python --version
	@pyenv --version
	@pip --version

clean:
	python manage.py clean

lint: info
	@rm -f violations.flake8.txt
	flake8 --exclude=env --exclude=archive . > violations.flake8.txt

test: lint
	python manage.py test

tox: clean
	tox

coverage: clean
	@coverage run --source=kaku manage.py test
	@coverage html
	@coverage report

ci: info coverage
	CODECOV_TOKEN=`cat .codecov-token` codecov

server:
	python manage.py server

uwsgi:
	uwsgi --socket 127.0.0.1:5080 --module service --callable application
