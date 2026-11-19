# Contributing

Thanks for helping improve these skills. Use
[GitHub Issues](https://github.com/dartyuhov/skills/issues) to report bugs or
discuss larger changes. Include the skill name, your agent and relevant tool
versions, what you expected, and a short prompt or command that reproduces the
problem. Remove credentials and private data from logs and examples.

## Edit a skill

Start with the skill's `SKILL.md` under [`.agents/skills/`](.agents/skills/).
Keep its instructions, scripts, and references together so a selective install
has everything the skill needs. Document new runtime requirements in the
skill's `SKILL.md` and update the [README](README.md) if setup or usage changes.

## Run offline tests

From the repository root, run both commands with Python 3 and Git available.
The suites use local fixtures and mocks; they don't need live fares, a running
Herdr session, or GitHub credentials.

```sh
python3 -B -m unittest discover -s .agents/skills/herdr-handoff/scripts -p 'test_herdr_handoff.py'
python3 -B -m unittest discover -s .agents/skills/opensource-me/tests -p 'test_*.py'
```

If your change depends on live behavior, include any manual checks you ran and
their results. The offline suites cover the Python helpers, so use a relevant
example prompt to check changes to skill instructions when possible.

## Open a pull request

Use a [Conventional Commit](https://www.conventionalcommits.org/en/v1.0.0/)
title, such as `fix(herdr-handoff): handle a slow shell startup` or
`docs(flight-search): clarify Fli setup`. Use the same format for commit
subjects. If you introduce a breaking change, mark it with `!` and explain how
users can migrate in the pull request description.

Before opening a pull request, use this checklist:

- [ ] Keep the change focused and explain what changes for users and why.
- [ ] Name the affected skills and link any related issue.
- [ ] Update affected instructions, requirements, prompts, and links.
- [ ] Run both offline test commands and record the results and any manual checks.
- [ ] Check that the diff, examples, and logs contain no secrets or private data.
