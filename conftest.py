"""Root conftest so `import server` resolves under a bare `pytest`.

Not decoration: with no conftest here, pytest puts only tests/ on sys.path and
every test that imports the server errors out. It passed locally because
`python -m pytest` adds the working directory and the console script does not
— a difference that made the local run weaker than CI's.
"""
