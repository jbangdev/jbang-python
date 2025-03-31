default:
    echo 'Hello, world!'

test:
    source venv/bin/activate
    #pip3 install -e .
    pip install -e ".[test]"
    python -m pytest  -o log_cli_level=DEBUG  -o log_cli=true

release:
    source venv/bin/activate
    pip3 install setuptools
    gh release create `python3 setup.py --version` --generate-notes
