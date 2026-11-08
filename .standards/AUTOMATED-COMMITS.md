# Automated Commit Inventory

Reviewed: 2026-10-05, AirBook. Canonical owner:
`biggie-configs/shared/global-reference/coding/AUTOMATED-COMMITS.md`.
The agent canons carry attributed copies of this single policy list. Update the
owner and affected copies together; GitHub Workflow contains no separate list.

## Exact named production forms

Only these script-generated forms qualify. Custom `--message-file` content is
authored content and must follow R2. Naming a script does not exempt every commit
it can make. Arbitrary subjects beginning "Record", "Sync" or "auto" do not qualify.

| Named automation | Generated subject and body form | Source evidence |
|---|---|---|
| `biggie-configs/scripts/biggie-configs.sh` | `config: <reason>`; `Why`, `Changed`, `Verified`, `Origin / authority`, `Recovery` body | Default message writer and `git commit -F`; already meets R2. |
| `biggie-playground/biggie-playground.py` | `library: register <name>` with `Why`, `Changed`, `Verified`, `Follow-up`; `library: promote <name> to canonical` with `Why`, `Changed`, `Verified`; `library: publish reviewed canonical updates` with `Why`, `Changed`, `Verified` | add/promote/push default message writers and `git_commit_and_maybe_push`; already meets R2. |
| `yuki-canon/scripts/sync-canon.sh` | `Sync Yuki canon: <reason>` with `Why`, `Changed`, `Verified`, `Origin`, `Recovery`; `Record Yuki canon sync status` with `Payload: <payload_commit>`, `Origin: <origin_label>`, `Verification: repository scans passed; live adoption is reported separately.` | Payload writer and separate `.canon/status.json` metadata commit. |
| `rufus-canon/scripts/sync-canon.sh` | `Sync Rufus canon: <reason>` with `Why`, `Changed`, `Verified`, `Origin`, `Recovery`; `Record Rufus canon sync status` with `Payload: <payload_commit>`, `Origin: <origin_label>`, `Verification: repository scans passed; live adoption is reported separately.` | Payload writer and separate `.canon/status.json` metadata commit. |
| Yuki `~/.hermes/scripts/biggie-hq-idle-push.sh` | `asia daily brief (auto)`; no body | Source mirror: `yuki-canon/runtime/scripts/biggie-hq-idle-push.sh`; commits only its configured daily-brief path. Runtime location/job documented in `yuki-canon/scheduled-jobs.md`. |

An exception still retains existing hooks, freshness checks, credential scans,
path scope and authority. This list does not authorize running canon sync scripts
or connecting to hosts. Human authors cannot claim an exception by copying a subject.

## Inventory coverage and limits

Reviewed 2026-10-05: four source repos and approved Yuki/Rufus runtime script roots.
Credential/config files, dependencies and tool symlinks are excluded; fixtures confer no exception.
Unlisted or changed automation needs source review before an exception is granted.
Counts, hashes and fixture names: [scan evidence](https://github.com/gueysito/biggie-configs/blob/main/shared/global-reference/coding/AUTOMATED-COMMITS-EVIDENCE.json).
