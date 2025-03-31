
test:
    source .venv/bin/activate
    #pip3 install -e .
    uv pip install -e ".[test]"

    echo Running tests with no jbang in PATH
    PATH=$(echo $PATH | tr ':' '\n' | grep -v "\.jbang/bin" | tr '\n' ':' | sed 's/:$//') python -m pytest  -o log_cli_level=DEBUG  -o log_cli=true

release:
    source venv/bin/activate
    uv pip install setuptools
    gh release create `python3 setup.py --version` --generate-notes
