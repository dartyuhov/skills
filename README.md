# Personal agent skills

I built these skills for my own workflows and share them here in case they're
useful to you. Each skill lives in [`.agents/skills/`](.agents/skills/) with its
instructions and any supporting files.

## Install a skill

You'll need a compatible agent, Node.js 22.20.0 or newer with `npx`, Git, and
internet access. The installer copies the skill files; check the skill's own
requirements below for any tools it needs at runtime.

1. List the available skills:

   ```sh
   npx --yes skills@1.9.0 add dartyuhov/skills --list
   ```

2. From the project where you want to use the skill, install it by name. This
   example copies `flight-search` into the project for OpenCode:

   ```sh
   npx --yes skills@1.9.0 add dartyuhov/skills --skill flight-search --agent opencode --copy --yes
   ```

3. Use your agent from that project and ask it to use the skill by name. Try one
   of the example prompts below.

Choose your agent with `--agent`. The paths below are relative to the project
where you run the install command.

| Agent | `--agent` value | Project skill directory |
| --- | --- | --- |
| OpenCode | `opencode` | `.agents/skills/` |
| Codex | `codex` | `.agents/skills/` |
| Claude Code | `claude-code` | `.claude/skills/` |

[skills.sh](https://skills.sh/) uses anonymous install counts to surface skills
in its directory. A listing isn't guaranteed or needed: `--list` and `add`
work directly from the GitHub repository.

## Skills and example prompts

Read the skill's source before using it, and check its requirements against your
project and agent.

### Flight search

[`flight-search`](.agents/skills/flight-search/SKILL.md) compares Google Flights
quotes for fixed or flexible dates and rechecks shortlisted fares. It's for
flight research only; you verify the final fare and book it yourself.

**Requirements:** Terminal access, internet access, and the `fli` CLI from the
Python `flights` package (Python 3.10 or newer). See
[how to install and verify Fli](.agents/skills/flight-search/references/install.md).

> Use `flight-search` to compare nonstop economy fares from Barcelona to Warsaw
> for a seven-night trip between December 14 and 28, 2026, for two adults and
> one child aged eight. Show totals in EUR.

### Herdr handoff

[`herdr-handoff`](.agents/skills/herdr-handoff/SKILL.md) sends a redacted task
summary to a fresh OpenCode session in a sibling Herdr pane, in the current
project directory. It checks that the receiver starts acting on the prompt;
this doesn't establish that the receiver finished the task.

**Requirements:** Python 3, the Herdr CLI with shell process inspection, the
OpenCode CLI with `--auto` support, and a Herdr-managed terminal (`HERDR_ENV=1`).
You can install the skill into another supported agent to initiate the handoff,
but the receiving agent is always OpenCode.

> Use `herdr-handoff` to continue this task in a fresh OpenCode pane. Include
> what changed, which checks passed, and the next step.

### Open-source preparation

[`opensource-me`](.agents/skills/opensource-me/SKILL.md) audits, prepares, or
launches an existing Git repository on GitHub. You set the scope for each
project. Audit mode is read-only; the workflow checks your authorization before
making GitHub changes or publishing anything.

**Requirements:** Python 3 and Git. Remote operations also require the GitHub
CLI (`gh`) and access to the target repository. An agent that supports
subagents is recommended.

> Use `opensource-me` in audit mode to review this repository for a public
> launch. Report what's missing and which checks you ran.

## Contributing and license

See [the contribution guide](CONTRIBUTING.md) for how to propose a change and
run the two offline test suites. To report a problem, use
[GitHub Issues](https://github.com/dartyuhov/skills/issues).

This project uses the [MIT License](LICENSE).
Copyright (c) 2026 Dzmitry Artsiukhou.
