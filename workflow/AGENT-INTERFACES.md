# Shared research skills across interfaces

Verified against official documentation on 17 November 2026. `AGENTS.md` remains the canonical project policy. This file records compatibility evidence and verification limits.

## Canonical layout

```text
AGENTS.md
CLAUDE.md -> AGENTS.md
.agents/
  skills/
    research-author/SKILL.md
    proof-verifier/SKILL.md
    counterexample/SKILL.md
    source-auditor/SKILL.md
    style-referee/SKILL.md
    research-review/
      SKILL.md
      references/task.md
      references/review.md
    tex-to-semantex/SKILL.md
.claude/
  skills -> ../.agents/skills
```

Each skill has portable `name` and `description` YAML fields and Markdown instructions. Claude resolves the same physical files as Codex and Antigravity. Edit canonical files under `.agents/skills`; the symlink exposes subsequent changes without copying or synchronizing content. `.agents/roles` and the root `agents` compatibility alias have been removed.

## Documented discovery and invocation

| Interface | Project instructions | Project skills | Explicit use |
| --- | --- | --- | --- |
| Codex | Root `AGENTS.md` | `.agents/skills/<name>/SKILL.md`, searched from the working directory through the repository root | `$proof-verifier` in CLI/IDE, or select the skill in the interface |
| Claude Code | `CLAUDE.md` symlink to `AGENTS.md` | `.claude/skills/<name>/SKILL.md` through the shared directory symlink | `/proof-verifier` |
| Antigravity App, CLI, IDE | Root `AGENTS.md` directly | `.agents/skills/<name>/SKILL.md` | `/proof-verifier` in App/CLI; IDE Customizations lists skills |

Codex documents repository skill discovery, symlinked skill folders, name/description metadata, implicit selection, and explicit invocation in its [skills guide](https://learn.chatgpt.com/docs/build-skills). Its [instruction guide](https://learn.chatgpt.com/docs/agent-configuration/agents-md) documents root and nested `AGENTS.md` files.

Claude documents project skills under `.claude/skills`, symlinked skill directories, progressive disclosure, and slash commands in its [skills guide](https://code.claude.com/docs/en/skills). The directory-level link here supplies those same ordinary filesystem paths. Its [memory guide](https://code.claude.com/docs/en/memory#remove-an-earlier-agentsmd-workaround) explicitly permits `CLAUDE.md -> AGENTS.md`. Current versions can also read `AGENTS.md` directly, subject to settings and version restrictions; the symlink supports older clients too.

Antigravity documents `.agents/skills` for App, CLI, and IDE, plus name/description frontmatter and on-demand activation, in its [skills guide](https://antigravity.google/docs/skills). Its [rules guide](https://antigravity.google/docs/rules) documents direct root `AGENTS.md` discovery on those surfaces. No `GEMINI.md` copy or symlink is needed for those documented versions.

## Skills and worker identities

The five former research prompts are now independently discoverable skills. A skill supplies an approach and workflow; loading several skills in one context does not create several independent reviewers. The review coordinator still assigns separate actual workers, candidate fingerprints, evidence, and exclusive report outputs. Registry `role` values remain unchanged: they describe review responsibilities and are not discovery directories.

The products also support native custom subagents, but their configuration formats differ:

| Product | Native custom subagent configuration |
| --- | --- |
| Codex | `.codex/agents/<name>.toml` with `name`, `description`, and `developer_instructions` |
| Claude Code | `.claude/agents/<name>.md` with YAML metadata and a Markdown prompt |
| Antigravity | `.agents/agents/<name>.md` or `.agents/agents/<name>/agent.md` |

These are documented in the [Codex subagent guide](https://learn.chatgpt.com/docs/agent-configuration/subagents), [Claude subagent guide](https://code.claude.com/docs/en/sub-agents), and [Antigravity subagent guide](https://antigravity.google/docs/subagents/). A skill-directory symlink does not register native custom subagents or standardize model selection, permissions, tools, context isolation, or orchestration. The portable implementation here deliberately shares the research capabilities as skills; request a fresh reviewer context and give it the relevant canonical skill when independence is required.

## Migration and provenance

| Previous maintained path | Current location |
| --- | --- |
| `agents/roles/author.md` | `research-author` |
| `agents/roles/proof-verifier.md` | `proof-verifier` |
| `agents/roles/counterexample.md` | `counterexample` |
| `agents/roles/auditor.md` | `source-auditor` |
| `agents/roles/style-referee.md` | `style-referee` |
| `agents/PROTOCOL.md` | `research-review` |
| `agents/SEMANTEX.md` | [AGENTS.md](../AGENTS.md) and the [SemanTeX reference](SEMANTEX.md) |
| `agents/templates/{task,review}.md` | `research-review/references/{task,review}.md` |

The existing paper-conversion skill remains `tex-to-semantex`. Shared SemanTeX conventions live in the root instructions. The review skills refer to the same writing guide as manuscript authors. Maintained callers and the README generator use the new paths. Historical migration captures and signed/hash-bearing review reports retain their original locators and bytes; their old instruction paths are historical evidence, not active entrypoints. Original tracked guides remain recoverable from Git history.

Review fingerprints now include canonical skill Markdown and YAML resources. Changing a review skill or report template invalidates existing acceptance instead of silently dropping moved instructions from the evidence set. This intentionally changes fingerprints; no acceptance or review report was renewed.

## Verification on 17 November 2026

- Checked the matching eight-skill catalogs, names, descriptions, identical physical files through Claude's symlink, and local Markdown links. The two root symlinks resolve inside this repository.
- The full unit-test suite passed all 64 tests, including a new case showing that changing either a canonical skill or a review template makes an accepted claim stale.
- `git diff --check` passed. Full `make check` was attempted before and after the reorganization; both stalled during corpus reads at `scripts/check.py`, so no full-project pass is claimed.
- The bundled skill validator requires PyYAML, which the default Python does not provide. Required metadata and names were checked separately; Ruby's YAML safe loader successfully parsed every skill's frontmatter.
- Local Codex CLI reports version `0.144.1`. The Claude launcher points to `2.1.185`; its version command stalled. No `agy` or `antigravity` executable is on PATH. A read-only Codex app-server skill-list attempt exited without a result. Live discovery in all three interfaces has therefore not been demonstrated.
- In a fresh client session, confirm the current skill list using Codex's skill selector, Claude's `/` menu and `/context all`, and Antigravity's Customizations panel. Client settings, managed policy, version differences, and cloud-only surfaces can affect loading. Claude's docs specifically distinguish local project skills from account-managed skills in Cowork and project cloud threads; this repository layout does not install skills into those account-level surfaces.
