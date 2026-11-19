# Install and verify Fli

Fli requires Python 3.10 or newer. The Python package is `flights`; the terminal
command is `fli`. The skill uses only the CLI, so no MCP setup is needed.

## Install with pipx

If you don't have `pipx`, follow the [official pipx installation steps](https://github.com/pypa/pipx#install-pipx).
On macOS with Homebrew, run `brew install pipx`. Then run:

```bash
pipx ensurepath
pipx install flights
```

Open a new terminal after a PATH change. Verify the executable and its search
commands:

```bash
command -v fli
fli flights --help
fli dates --help
```

## Use the revision verified with this skill

The published build may lag behind the upstream repository. If it lacks a
needed flag or can't fetch quotes after an upgrade, the following pinned
upstream revision is the one used to verify this skill. It requires Git and
replaces an existing pipx installation of `flights`.

```bash
pipx install --force 'git+https://github.com/punitarani/fli.git@881aee5ff4321e81ea2157cb44be94ce6a21dc1b'
```

Rerun the help checks after installing. If a search still fails, report the CLI
error and consult upstream troubleshooting rather than report zero flights.

- [Fli upstream quick start](https://github.com/punitarani/fli#quick-start)
- [Fli CLI usage](https://github.com/punitarani/fli#cli-usage)
- [Fli search troubleshooting](https://github.com/punitarani/fli#search-transport)
- [`flights` package on PyPI](https://pypi.org/project/flights/)
