"""The contract of the GitHub workflows.

GitHub alone runs these files, and a mistake in one shows only there --
often only when it matters: a required check that stays green although the
tests failed, a workflow GitHub has quietly disabled, a release that pushes
past a main that moved. These tests read the YAML and hold the decisions
CONTRIBUTING.md ("Continuous integration", "Releases") describes. Where a
script decides, they run it: with bash, as GitHub does, and with git on
repositories of their own.
"""
import itertools
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

import yaml

_WORKFLOWS = Path(__file__).parents[1] / ".github" / "workflows"


def _workflow(name: str) -> dict:
    """The workflow file `name` in .github/workflows (e.g. "validate.yml"),
    parsed, with its trigger block under the key "on".

    PyYAML reads YAML 1.1, where the bare key `on` is the boolean True;
    GitHub reads it as the string "on". The block is moved to "on", so a
    test reads `_workflow(name)["on"]` as the file spells it.
    """
    workflow = yaml.safe_load((_WORKFLOWS / name).read_text(encoding="utf-8"))
    if True in workflow:
        workflow["on"] = workflow.pop(True)
    return workflow


def _every_workflow() -> list[tuple[str, dict]]:
    """Every workflow file GitHub runs, by name, parsed like `_workflow`."""
    names = sorted(
        path.name for path in _WORKFLOWS.iterdir() if path.suffix in {".yml", ".yaml"}
    )
    assert names, f"no workflow in {_WORKFLOWS}"
    return [(name, _workflow(name)) for name in names]


def _jobs_by_name(workflow: dict) -> dict[str, dict]:
    """The workflow's jobs by the name GitHub shows for them."""
    return {job["name"]: job for job in workflow["jobs"].values()}


def _python(job: dict) -> str:
    """The Python version the job sets up."""
    [version] = [
        step["with"]["python-version"]
        for step in job["steps"]
        if step.get("uses", "").startswith("actions/setup-python@")
    ]
    return version


def _script(job: dict) -> str:
    """Everything the job's steps run, as one text."""
    return "\n".join(step["run"] for step in job["steps"] if "run" in step)


def test_no_workflow_has_a_schedule():
    """GitHub disables a workflow that has a schedule after 60 days without
    repository activity -- and then it runs on no push either."""
    assert [name for name, workflow in _every_workflow() if "schedule" in workflow["on"]] == []


def test_no_workflow_uses_pull_request_target():
    """pull_request_target hands a fork's pull request the repository's
    secrets and a token that can write; pull_request runs it with neither."""
    assert [
        name for name, workflow in _every_workflow() if "pull_request_target" in workflow["on"]
    ] == []


def test_every_job_runs_on_the_pinned_runner_with_a_timeout():
    """ubuntu-latest can move to a new image under an unchanged workflow;
    a job without a timeout that hangs holds its runner for six hours.
    A job that calls a reusable workflow has neither: its jobs do."""
    assert [
        (name, key)
        for name, workflow in _every_workflow()
        for key, job in workflow["jobs"].items()
        if "runs-on" in job
        and (job["runs-on"] != "ubuntu-24.04" or type(job.get("timeout-minutes")) is not int)
    ] == []


_CURRENT_MAJORS = {
    "actions/checkout": "v7",
    "actions/setup-python": "v7",
    "softprops/action-gh-release": "v3",
}


def test_actions_use_their_current_major():
    """All workflows move to a new major together, so none is left behind
    on one GitHub stops supporting."""
    outdated = []
    for name, workflow in _every_workflow():
        for job in workflow["jobs"].values():
            for step in job.get("steps", []):
                action, _, ref = step.get("uses", "").partition("@")
                if action in _CURRENT_MAJORS and ref != _CURRENT_MAJORS[action]:
                    outdated.append((name, step["uses"]))
    assert outdated == []


def test_no_script_has_an_expression_in_its_text():
    """GitHub writes an expression's value into a run: script before bash
    reads it, so a branch name, a pull request's title or an input could
    turn into shell code there. Every value reaches a script through env."""
    assert [
        (name, key, step.get("name"))
        for name, workflow in _every_workflow()
        for key, job in workflow["jobs"].items()
        for step in job.get("steps", [])
        if "${{" in step.get("run", "")
    ] == []


def test_no_job_or_step_goes_on_after_a_failure():
    """continue-on-error turns a failure into success: on a check, the
    Validation result goes green while the check failed; on the release's
    guard, key check or push, the release goes on."""
    assert [
        (name, key, part.get("name"))
        for name, workflow in _every_workflow()
        for key, job in workflow["jobs"].items()
        for part in (job, *job.get("steps", []))
        if "continue-on-error" in part
    ] == []


def test_internal_validation_offers_a_tests_switch():
    """Only other workflows call it; a caller that sets nothing runs
    everything."""
    on = _workflow("_validate.yml")["on"]
    tests = on["workflow_call"]["inputs"]["tests"]
    assert on == {"workflow_call": {"inputs": {"tests": tests}}}
    assert tests["type"] == "boolean"
    assert tests["default"] is True


def test_internal_validation_always_runs_hassfest_hacs_and_the_floor_checks():
    """hassfest and HACS check what ships, the floor checks what Home
    Assistant 2025.5's Python needs; each is quick, and no caller can skip
    one. Only the tests and mypy, minutes each, can be switched off -- and
    only as whole jobs: no step is skipped on a condition of its own, and no
    job waits for another, which a switched-off one would skip with it."""
    workflow = _workflow("_validate.yml")
    assert sorted(job["name"] for job in workflow["jobs"].values()) == [
        "HACS validation",
        "Hassfest validation",
        "Python 3.13 syntax",
        "Strict typing",
        "Tests with coverage",
    ]
    jobs = _jobs_by_name(workflow)
    for name in ("Hassfest validation", "HACS validation", "Python 3.13 syntax"):
        assert "if" not in jobs[name], name
    for name in ("Tests with coverage", "Strict typing"):
        assert jobs[name]["if"] in ("inputs.tests", "${{ inputs.tests }}"), name
    assert [name for name, job in jobs.items() if "needs" in job] == []
    assert [
        (name, step.get("name", step.get("uses")))
        for name, job in jobs.items()
        for step in job["steps"]
        if "if" in step
    ] == []


def test_internal_validation_checks_the_commit_its_caller_runs_for():
    """Without a ref, actions/checkout checks out github.sha: the commit a
    push brought, a pull request's merge commit, the commit a release was
    started on -- and puts its version on top of. Any other ref would
    validate something else than what merges or ships."""
    checkouts = [
        (key, step.get("with", {}))
        for key, job in _workflow("_validate.yml")["jobs"].items()
        for step in job["steps"]
        if step.get("uses", "").startswith("actions/checkout@")
    ]
    assert sorted(key for key, _ in checkouts) == sorted(
        _workflow("_validate.yml")["jobs"]
    )
    assert [key for key, with_ in checkouts if "ref" in with_] == []


def test_the_checks_run_what_ci_promises():
    """The gates and commands CONTRIBUTING.md names. The tests and mypy run
    on 3.14, which the pinned Home Assistant needs, and install from
    tests/requirements.txt -- another mypy release can find errors in
    unchanged code. The floor job runs on 3.13, Home Assistant 2025.5's."""
    jobs = _jobs_by_name(_workflow("_validate.yml"))
    tests, typing, floor = (
        jobs["Tests with coverage"],
        jobs["Strict typing"],
        jobs["Python 3.13 syntax"],
    )
    for job in (tests, typing):
        assert _python(job) == "3.14", job["name"]
        assert "pip install -r tests/requirements.txt" in _script(job), job["name"]
    assert "python -m pytest tests/" in _script(tests)
    assert "--cov=custom_components.bitpanda" in _script(tests)
    assert "--cov-fail-under=95" in _script(tests)
    assert "python -m mypy --strict" in _script(typing)
    assert _python(floor) == "3.13"
    assert "python -m compileall" in _script(floor)
    assert "from __future__ import annotations" in _script(floor)


def test_validate_runs_on_every_push_but_main_on_pull_requests_to_main_and_by_hand():
    """main needs no run of its own: changes reach it only through a
    validated pull request, or as the release's version commit, validated
    just before. A newer push or pull request update cancels the run it
    makes obsolete."""
    validate = _workflow("validate.yml")
    on = validate["on"]
    assert sorted(on) == ["pull_request", "push", "workflow_dispatch"]
    assert on["push"] == {"branches-ignore": ["main"]}
    assert on["pull_request"] == {"branches": ["main"]}
    tests = on["workflow_dispatch"]["inputs"]["tests"]
    assert tests["type"] == "boolean"
    assert tests["default"] is True
    assert validate["concurrency"] == {
        "group": "validate-${{ github.ref }}",
        "cancel-in-progress": True,
    }
    assert validate["permissions"] == {"contents": "read"}


def test_validate_runs_the_tests_unless_switched_off_by_hand():
    """A push or pull request always runs them; only a manual run can
    leave them out."""
    checks = _workflow("validate.yml")["jobs"]["checks"]
    assert checks["uses"] == "./.github/workflows/_validate.yml"
    assert checks["with"]["tests"] == (
        "${{ github.event_name != 'workflow_dispatch' || inputs.tests }}"
    )


# The results GitHub reports for a job a later job needs, and the one
# expression that hands the result job all of them: every job it needs,
# whichever jobs that is.
_JOB_RESULTS = ("success", "failure", "cancelled", "skipped")
_EVERY_RESULT = "${{ join(needs.*.result, ' ') }}"


def _exit_status(step: dict, results: tuple[str, ...]) -> int:
    """The exit status of the step's script, run as GitHub runs it
    (`bash -e`), when the jobs it needs ended in `results`, one per job:
    its `env` gets them as join(needs.*.result, ' ') hands them over."""
    env = {
        variable: " ".join(results)
        for variable, value in step.get("env", {}).items()
        if value == _EVERY_RESULT
    }
    return subprocess.run(
        ["bash", "-e", "-c", step["run"]],
        env={**os.environ, **env},
        capture_output=True,
        check=False,
    ).returncode


def test_validation_result_is_the_one_required_check():
    """main's ruleset requires this one check by its name, which stays valid
    when the jobs behind it change.

    always(), not the default success() or !cancelled(): a skipped job
    counts as passed for a required check, so a failed or cancelled
    validation must still run this job, and fail it. It waits for every
    other job and reads the result of each, whichever jobs that is -- one it
    did not wait for, or did not read, could fail and leave it green. No
    result at all is no pass either.
    """
    jobs = _workflow("validate.yml")["jobs"]
    result = jobs["result"]
    assert result["name"] == "Validation result"
    assert "checks" in result["needs"]
    assert sorted(result["needs"]) == sorted(key for key in jobs if key != "result")
    assert result["if"] == "always()"
    assert result["runs-on"] == "ubuntu-24.04"
    assert type(result["timeout-minutes"]) is int
    [step] = result["steps"]
    assert "if" not in step
    assert step["env"] == {"RESULTS": _EVERY_RESULT}
    assert [value for value in _JOB_RESULTS if value in step["run"]] == ["success"]
    assert "exit 1" in step["run"]
    # One job, as today, in each result -- and any number of jobs, each of
    # which fails the check unless it succeeded.
    assert {value: _exit_status(step, (value,)) for value in _JOB_RESULTS} == {
        "success": 0,
        "failure": 1,
        "cancelled": 1,
        "skipped": 1,
    }
    for count in range(4):
        for results in itertools.product(_JOB_RESULTS, repeat=count):
            passed = bool(results) and set(results) == {"success"}
            assert _exit_status(step, results) == (0 if passed else 1), results


# release.yml, "Create Release": checks the branch, validates, then plans
# the version, commits it and pushes it with the deploy key -- to main and
# the tag for a stable release, only the tag for a pre-release (job
# "commit", which holds the key) -- and creates the GitHub release (job
# "publish", which does not).
_RELEASE = "release.yml"
_RELEASE_SCRIPT = Path(__file__).parents[1] / ".github" / "scripts" / "release.py"
_MANIFEST = "custom_components/bitpanda/manifest.json"
_DEPLOY_KEY = "${{ secrets.RELEASE_DEPLOY_KEY }}"
# The condition of every step and job a dry run skips, and the spellings of
# the condition of the one step only a dry run runs.
_NOT_A_DRY_RUN = "${{ !inputs.dry_run }}"
_ONLY_A_DRY_RUN = ("inputs.dry_run", "${{ inputs.dry_run }}")
# Stands in for the deploy key's private key, which no script may print.
_A_KEY = "deploy-key-stand-in"
# An `env` value that is one expression, such as ${{ secrets.X }}.
_AN_EXPRESSION = re.compile(r"\$\{\{\s*(.+?)\s*\}\}")
# An expression that reads the secrets context: one secret, or all of them,
# as toJSON(secrets) would.
_READS_SECRETS = re.compile(r"\$\{\{[^}]*\bsecrets\b")
# The notes the release script writes for the one change the repositories
# below carry after the previous release.
_NOTES = "### ✨ New Features\n\n- Add the validated change"


def _environment(variables: dict[str, str] | None = None) -> dict[str, str]:
    """The environment for git and the scripts: the test process's, less
    git's own variables -- a hook's GIT_DIR would send git to this
    repository -- and without the user's or the system's git configuration,
    plus `variables`."""
    inherited = {name: value for name, value in os.environ.items() if not name.startswith("GIT_")}
    unconfigured = {"GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}
    return {**inherited, **unconfigured, **(variables or {})}


def _run_step(
    step: dict,
    values: dict[str, str] | None = None,
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run the step's script as GitHub runs it (`bash -e`), in `cwd`.

    A variable of the step's `env` that holds an expression, such as
    `DEPLOY_KEY: ${{ secrets.RELEASE_DEPLOY_KEY }}`, gets that expression's
    value from `values` ("secrets.RELEASE_DEPLOY_KEY"), or stays empty.
    `env` adds what the runner sets itself, such as GITHUB_REF.
    GITHUB_OUTPUT leads nowhere unless `env` names a file, so no script
    writes into the outputs of the CI step running these tests.
    """
    step_env = {}
    for variable, value in step.get("env", {}).items():
        expression = _AN_EXPRESSION.fullmatch(str(value))
        step_env[variable] = (values or {}).get(expression[1], "") if expression else str(value)
    return subprocess.run(
        ["bash", "-e", "-c", step["run"]],
        cwd=cwd,
        env=_environment({"GITHUB_OUTPUT": os.devnull, **(env or {}), **step_env}),
        capture_output=True,
        text=True,
        check=False,
    )


def _github_outputs(path: Path) -> dict[str, str]:
    """The outputs a step wrote into the file GITHUB_OUTPUT names, read as
    the runner reads them: `name=value`, or `name<<DELIMITER` and the
    value's lines up to the first line that is exactly DELIMITER."""
    outputs = {}
    lines = iter(path.read_text(encoding="utf-8").splitlines())
    for line in lines:
        equals, heredoc = line.find("="), line.find("<<")
        if heredoc < 0 or 0 <= equals < heredoc:
            assert equals > 0, f"not an output: {line!r}"
            outputs[line[:equals]] = line[equals + 1 :]
            continue
        name, delimiter, value = line[:heredoc], line[heredoc + 2 :], []
        for value_line in lines:
            if value_line == delimiter:
                break
            value.append(value_line)
        else:
            raise AssertionError(f"the value of {name} never ends: no line {delimiter!r}")
        outputs[name] = "\n".join(value)
    return outputs


def _outputs_of(step: dict, values: dict[str, str], cwd: Path, output: Path) -> dict[str, str]:
    """Run the step in `cwd`, with GITHUB_OUTPUT the file `output`; the
    outputs it sets."""
    output.write_text("", encoding="utf-8")
    result = _run_step(step, values, cwd=cwd, env={"GITHUB_OUTPUT": str(output)})
    assert result.returncode == 0, result.stderr
    return _github_outputs(output)


def _needs(job: dict) -> list[str]:
    """The jobs `job` waits for; `needs` names one job or a list."""
    needs = job.get("needs", [])
    return [needs] if isinstance(needs, str) else needs


def _forces(word: str) -> bool:
    """Whether a word of a git push command makes it overwrite what it
    pushes to: --force (with-lease too), -f alone or among other short
    options, or a +refspec."""
    word = word.strip("\"'")
    return word.startswith(("--force", "+")) or bool(re.fullmatch(r"-[a-zA-Z]*f[a-zA-Z]*", word))


def _git(directory: Path, *args: str) -> str:
    """Run git in `directory`; what it prints."""
    return subprocess.run(
        ["git", *args],
        cwd=directory,
        env=_environment(),
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def _commit(repository: Path, message: str) -> str:
    """An empty commit in `repository`, by a test author; its SHA."""
    _git(
        repository,
        *("-c", "user.name=Test", "-c", "user.email=test@example.invalid"),
        *("commit", "--quiet", "--allow-empty", "--message", message),
    )
    return _git(repository, "rev-parse", "HEAD")


def _refs(repository: Path) -> dict[str, str]:
    """Every branch and tag of `repository`, with the commit it points at."""
    listing = _git(repository, "for-each-ref", "--format=%(refname) %(objectname)")
    return dict(line.split(" ") for line in listing.splitlines())


def _release_clone(
    directory: Path,
    started_on: str = "main",
    *,
    earlier: str = "An earlier commit",
    validated: str = "The validated commit",
    version_commit: bool = True,
) -> tuple[Path, Path]:
    """What the key job holds, as (origin, clone).

    origin is a bare repository with main and dev. The release was started
    on `started_on`, which points at the validated commit; the other branch
    points at the commit before it, so a push of the validated commit there
    would be a fast-forward -- only the script can keep it from happening.
    clone is checked out at the validated commit, detached -- as
    actions/checkout leaves a SHA -- with the identity the key job's commit
    step configures, and, unless `version_commit` is False, the version
    commit on top."""
    directory.mkdir(parents=True, exist_ok=True)
    origin, clone = directory / "origin.git", directory / "clone"
    _git(directory, "init", "--quiet", "--bare", "--initial-branch=main", str(origin))
    _git(directory, "clone", "--quiet", str(origin), str(clone))
    _git(clone, "config", "user.name", "github-actions[bot]")
    _git(clone, "config", "user.email", "github-actions[bot]@users.noreply.github.com")
    _commit(clone, earlier)
    _git(clone, "push", "--quiet", "origin", "HEAD:main", "HEAD:dev")
    _commit(clone, validated)
    _git(clone, "push", "--quiet", "origin", f"HEAD:{started_on}")
    _git(clone, "switch", "--quiet", "--detach")
    if version_commit:
        _commit(clone, "The version commit")
    return origin, clone


def _merged_meanwhile(origin: Path, branch: str = "main") -> str:
    """Moves origin's `branch` on by one commit, as a pull request merged
    while a release runs; the commit the branch moved to."""
    other = origin.parent / f"meanwhile-{branch}"
    _git(origin.parent, "clone", "--quiet", "--branch", branch, str(origin), str(other))
    merged = _commit(other, "A pull request merged meanwhile")
    _git(other, "push", "--quiet", "origin", f"HEAD:{branch}")
    return merged


def _with_the_release_script(clone: Path) -> None:
    """Puts .github/scripts/release.py into `clone`, where the key job's
    checkout has it."""
    script = clone / ".github" / "scripts" / "release.py"
    script.parent.mkdir(parents=True)
    shutil.copyfile(_RELEASE_SCRIPT, script)


def test_release_runs_only_by_hand_as_a_stable_or_a_prerelease():
    """Only the maintainer starts a release: a stable one, or a pre-release
    -- a beta, for testing. The commits since the last stable release choose
    the version's bump unless he forces one; a stable one can open as a
    draft, for notes written by hand; a dry run checks the path and pushes
    nothing. One release runs at a time and is never cancelled halfway
    through its pushes; the token only reads, unless a job asks for more."""
    release = _workflow(_RELEASE)
    assert list(release["on"]) == ["workflow_dispatch"]
    inputs = release["on"]["workflow_dispatch"]["inputs"]
    assert sorted(inputs) == ["bump", "draft", "dry_run", "release_type"]
    choices = {
        name: (inputs[name]["type"], inputs[name]["options"], inputs[name]["default"])
        for name in ("release_type", "bump")
    }
    assert choices == {
        "release_type": ("choice", ["stable", "prerelease"], "stable"),
        "bump": ("choice", ["auto", "major", "minor", "patch"], "auto"),
    }
    for name in ("draft", "dry_run"):
        assert inputs[name]["type"] == "boolean", name
        assert inputs[name]["default"] is False, name
    assert release["concurrency"] == {"group": "release", "cancel-in-progress": False}
    assert release["permissions"] == {"contents": "read"}


def test_a_release_on_the_wrong_branch_stops_before_anything_else():
    """A stable release runs from main, which it pushes to; a pre-release
    from dev, which it leaves as it is -- and never as a draft: HACS does
    not see drafts, so a draft beta would reach nobody. Any other start --
    another branch, a tag named like one of the two, a draft beta -- fails
    at the first job, before anything is validated, committed, tagged or
    published: each job after it waits for the one before, and none has an
    if: that would run it anyway; the Publish job's only skips a dry run."""
    jobs = _workflow(_RELEASE)["jobs"]
    assert sorted(jobs) == ["check-branch", "commit", "publish", "validate"]
    check = jobs["check-branch"]
    assert check["name"] == "Check branch"
    assert check["permissions"] == {}
    assert "needs" not in check
    assert "if" not in check
    [guard] = check["steps"]
    assert "if" not in guard
    assert guard["env"] == {
        "RELEASE_TYPE": "${{ inputs.release_type }}",
        "DRAFT": "${{ inputs.draft }}",
    }
    assert "exit 1" in guard["run"]

    def started(release_type: str, ref: str, draft: bool) -> tuple[int, bool]:
        result = _run_step(
            guard,
            {"inputs.release_type": release_type, "inputs.draft": str(draft).lower()},
            env={"GITHUB_REF": ref, "GITHUB_REF_NAME": ref.split("/", 2)[2]},
        )
        return result.returncode, "::error::" in result.stdout

    allowed = {
        ("stable", "refs/heads/main", False),
        ("stable", "refs/heads/main", True),
        ("prerelease", "refs/heads/dev", False),
    }
    for release_type in ("stable", "prerelease", "beta"):
        for ref in (
            "refs/heads/main",
            "refs/heads/dev",
            "refs/heads/redesign",
            "refs/heads/main-backup",
            "refs/heads/dev-backup",
            "refs/tags/main",
            "refs/tags/dev",
            "refs/tags/v2.0.0",
        ):
            for draft in (False, True):
                case = (release_type, ref, draft)
                expected = (0, False) if case in allowed else (1, True)
                assert started(*case) == expected, case
    assert _needs(jobs["validate"]) == ["check-branch"]
    assert _needs(jobs["commit"]) == ["validate"]
    assert _needs(jobs["publish"]) == ["commit"]
    assert "if" not in jobs["validate"]
    assert "if" not in jobs["commit"]
    assert jobs["publish"]["if"] == _NOT_A_DRY_RUN


def test_release_always_validates_with_the_tests():
    """No release without the complete validation: _validate.yml with the
    tests, and no switch to leave them out. Its checks only read."""
    release = _workflow(_RELEASE)
    validate = release["jobs"]["validate"]
    assert validate["name"] == "Validate"
    assert validate["uses"] == "./.github/workflows/_validate.yml"
    assert validate["with"] == {"tests": True}
    assert validate["with"]["tests"] is True
    assert validate.get("permissions", release["permissions"]) == {"contents": "read"}


def test_release_commits_exactly_the_validated_commit():
    """The validation checked github.sha, the commit this run was started
    on (test_internal_validation_checks_the_commit_its_caller_runs_for). The
    version commit goes on top of exactly that commit, never on the branch
    as it is by then, which may have moved on, unvalidated: nothing in the
    job pulls, rebases, merges, resets or switches it onto another. The
    deploy key sets origin up for the pushes."""
    commit = _workflow(_RELEASE)["jobs"]["commit"]
    assert commit["name"] == "Commit version and tag"
    [checkout] = [
        step for step in commit["steps"] if step.get("uses", "").startswith("actions/checkout@")
    ]
    assert checkout["with"]["ref"] == "${{ github.sha }}"
    assert checkout["with"]["fetch-depth"] == 0
    assert checkout["with"]["ssh-key"] == _DEPLOY_KEY
    moves = r"\bgit\s+(?:pull|rebase|merge|reset|checkout|switch|cherry-pick)\b"
    assert re.findall(moves, _script(commit)) == []


def test_release_without_the_deploy_key_stops_before_pushing():
    """Only the deploy key can push the version commit and the tag -- the
    job's token only reads. Without it a release stops at once, with the
    reason: otherwise checkout would fall back to the token, and the
    release would fail at the push, after the commit, with a refusal that
    hides why. GitHub allows no secret in an if:, so the script tests the
    key, and never prints it. A dry run pushes nothing and needs no key."""
    steps = _workflow(_RELEASE)["jobs"]["commit"]["steps"]
    [checkout] = [
        index
        for index, step in enumerate(steps)
        if step.get("uses", "").startswith("actions/checkout@")
    ]
    [check] = [step for step in steps[:checkout] if _DEPLOY_KEY in step.get("env", {}).values()]
    assert check["if"] == _NOT_A_DRY_RUN
    missing = _run_step(check, {"secrets.RELEASE_DEPLOY_KEY": ""})
    assert missing.returncode == 1
    assert "::error::" in missing.stdout
    assert "RELEASE_DEPLOY_KEY" in missing.stdout
    present = _run_step(check, {"secrets.RELEASE_DEPLOY_KEY": _A_KEY})
    assert present.returncode == 0, present.stdout
    assert _A_KEY not in present.stdout + present.stderr


def test_release_keeps_the_deploy_key_from_third_party_actions():
    """The deploy key passes main's ruleset, its block on force pushes
    included, and a tampered third-party action could read it from the job
    it runs in. So one job holds the key, and it runs no action but
    actions/checkout: the rest is shell and the repository's own release
    script. Its token only reads -- it pushes with the key, over SSH. No
    other job of any workflow reads a secret or passes secrets on, and
    release.yml has no workflow-level env, which would reach the steps of
    every job, the Publish job's third-party action included. The GitHub
    release is created in a job of its own, with a token that may write,
    without checkout and without the key; a dry run skips it."""
    workflows = _every_workflow()
    release = _workflow(_RELEASE)
    assert "env" not in release
    # Above the jobs -- a workflow-level env reaches every one of them --
    # no workflow names the key or reads a secret.
    outside_the_jobs = {
        name: str({key: part for key, part in workflow.items() if key != "jobs"})
        for name, workflow in workflows
    }
    assert [
        name
        for name, text in outside_the_jobs.items()
        if "RELEASE_DEPLOY_KEY" in text or _READS_SECRETS.search(text)
    ] == []
    assert [
        (name, key)
        for name, workflow in workflows
        for key, job in workflow["jobs"].items()
        if "RELEASE_DEPLOY_KEY" in str(job) or _READS_SECRETS.search(str(job))
    ] == [(_RELEASE, "commit")]
    assert [
        (name, key)
        for name, workflow in workflows
        for key, job in workflow["jobs"].items()
        if "secrets" in job
    ] == []
    commit, publish = release["jobs"]["commit"], release["jobs"]["publish"]
    assert [step["uses"] for step in commit["steps"] if "uses" in step] == ["actions/checkout@v7"]
    assert set(re.findall(r"\bpython3?\s+(\S+)", _script(commit))) == {
        ".github/scripts/release.py"
    }
    assert commit["env"] == {"MANIFEST": _MANIFEST}
    assert commit["permissions"] == {"contents": "read"}
    assert publish["name"] == "Publish release"
    assert _needs(publish) == ["commit"]
    assert publish["if"] == _NOT_A_DRY_RUN
    assert publish["permissions"] == {"contents": "write"}
    assert [
        step for step in publish["steps"] if step.get("uses", "").startswith("actions/checkout@")
    ] == []


def test_a_stable_release_pushes_main_without_force_then_its_tag(tmp_path):
    """A stable release's version commit goes to main, and main is the
    safety net. The push is a plain one of the version commit, which sits
    on the validated commit: if main moved meanwhile -- a pull request
    merged while the release ran -- it is no fast-forward and main refuses
    it; the script stops there, and nothing unvalidated is tagged or
    released. Forced, it would throw the merged change away: the deploy key
    passes main's ruleset, its block on force pushes included. Only once
    main took the commit is it tagged, and the tag pushed; dev stays as it
    is. A dry run pushes nothing."""
    jobs = _workflow(_RELEASE)["jobs"]
    every_step = [step for job in jobs.values() for step in job.get("steps", [])]
    [push] = [step for step in every_step if "git push" in step.get("run", "")]
    assert push in jobs["commit"]["steps"]
    assert push["if"] == _NOT_A_DRY_RUN
    assert push["env"] == {
        "RELEASE_TYPE": "${{ inputs.release_type }}",
        "TAG": "${{ steps.plan.outputs.tag }}",
    }
    lines = push["run"].splitlines()
    pushes = [line for line in lines if "git push" in line]
    assert "git push origin HEAD:main" in pushes[0]
    # The tag's push, in the same script, after the commit's: the tag, and
    # nothing else.
    assert len(pushes) > 1
    assert all("refs/tags/" in line for line in pushes[1:])
    tagging = [index for index, line in enumerate(lines) if re.search(r"\bgit tag\b", line)]
    assert tagging
    assert min(tagging) > lines.index(pushes[0])
    assert [line for line in pushes if any(_forces(word) for word in line.split())] == []

    stable = {"inputs.release_type": "stable", "steps.plan.outputs.tag": "v2.0.0_redesign"}
    origin, clone = _release_clone(tmp_path / "main-unchanged")
    version_commit = _git(clone, "rev-parse", "HEAD")
    before = _refs(origin)
    released = _run_step(push, stable, cwd=clone)
    assert released.returncode == 0, released.stderr
    assert _refs(origin) == {
        **before,
        "refs/heads/main": version_commit,
        "refs/tags/v2.0.0_redesign": version_commit,
    }

    origin, clone = _release_clone(tmp_path / "main-moved")
    _merged_meanwhile(origin)
    before = _refs(origin)
    refused = _run_step(push, stable, cwd=clone)
    assert refused.returncode != 0
    assert "::error::" in refused.stdout
    assert _refs(origin) == before


def test_a_prerelease_pushes_its_tag_and_never_a_branch(tmp_path):
    """A beta's version commit lives only in its tag: the tag is pushed and
    takes the commit along, while no branch is pushed or moved -- dev stays
    at the commit the release was started on, main where it was, although a
    push to either would be a fast-forward here. dev may even move
    meanwhile: the beta carries the commit that was validated, and nothing
    of what came after."""
    [push] = [
        step
        for step in _workflow(_RELEASE)["jobs"]["commit"]["steps"]
        if "git push" in step.get("run", "")
    ]
    prerelease = {"inputs.release_type": "prerelease", "steps.plan.outputs.tag": "v2.1.0-beta.1"}
    for dev_moved in (False, True):
        origin, clone = _release_clone(tmp_path / f"dev-moved-{dev_moved}", "dev")
        validated, version_commit = _git(clone, "rev-parse", "HEAD~1", "HEAD").splitlines()
        if dev_moved:
            _merged_meanwhile(origin, "dev")
        before = _refs(origin)
        released = _run_step(push, prerelease, cwd=clone)
        assert released.returncode == 0, released.stderr
        assert _refs(origin) == {**before, "refs/tags/v2.1.0-beta.1": version_commit}
        assert _git(origin, "rev-parse", "v2.1.0-beta.1~1") == validated


def test_publish_releases_the_tag_with_the_generated_notes():
    """The Publish job has no checkout: what it needs comes from the key
    job's outputs -- the tag, the version, the notes, and whether this is a
    pre-release, which the key job takes from the release type. Job outputs
    are strings, so the job asks whether that one is 'true'. A stable
    release is published at once and marked latest, or opens as a draft for
    notes written by hand; a pre-release is published at once, marked as
    one and never latest, so HACS offers it only where betas are switched
    on. The title is v<version>, without the transition tag's suffix; the
    body is the generated notes alone -- GitHub's own would come on top."""
    jobs = _workflow(_RELEASE)["jobs"]
    assert jobs["commit"]["outputs"] == {
        "version": "${{ steps.plan.outputs.version }}",
        "tag": "${{ steps.plan.outputs.tag }}",
        "notes": "${{ steps.notes.outputs.notes }}",
        "prerelease": "${{ inputs.release_type == 'prerelease' }}",
    }
    [create] = jobs["publish"]["steps"]
    assert create["uses"] == "softprops/action-gh-release@v3"
    assert create["with"] == {
        "tag_name": "${{ needs.commit.outputs.tag }}",
        "name": "v${{ needs.commit.outputs.version }}",
        "body": "${{ needs.commit.outputs.notes }}",
        "prerelease": "${{ needs.commit.outputs.prerelease == 'true' }}",
        "make_latest": "${{ needs.commit.outputs.prerelease == 'true' && 'false' || 'true' }}",
        "draft": "${{ inputs.draft && needs.commit.outputs.prerelease != 'true' }}",
    }


def test_release_plans_its_version_with_the_release_script(tmp_path):
    """The version, its tag and the previous release come from the
    repository's own .github/scripts/release.py, run by the runner's
    python3, from the tags -- fetched first -- and the commits since; the
    release type and the bump reach it through env. After the 1.x line's
    date tags, the first stable is 2.0.0, its bump forced to major, tagged
    v2.0.0_redesign; after that, a feat makes the next stable 2.1.0 and a
    beta of it 2.1.0-beta.1, whose notes start after v2.0.0_redesign."""
    [plan] = [
        step
        for step in _workflow(_RELEASE)["jobs"]["commit"]["steps"]
        if step.get("id") == "plan"
    ]
    assert plan["env"] == {
        "RELEASE_TYPE": "${{ inputs.release_type }}",
        "BUMP": "${{ inputs.bump }}",
    }
    assert "python3 .github/scripts/release.py plan" in plan["run"]
    feat = "feat: add the validated change"

    origin, clone = _release_clone(tmp_path / "stable", validated=feat, version_commit=False)
    _with_the_release_script(clone)
    # On origin only, like a tag pushed after the checkout: the step fetches it.
    _git(origin, "tag", "v2026.06.04", "main~1")
    stable = {"inputs.release_type": "stable", "inputs.bump": "major"}
    assert _outputs_of(plan, stable, clone, tmp_path / "stable.out") == {
        "version": "2.0.0",
        "tag": "v2.0.0_redesign",
        "previous": "v2026.06.04",
    }

    origin, clone = _release_clone(
        tmp_path / "prerelease", "dev", validated=feat, version_commit=False
    )
    _with_the_release_script(clone)
    for tag in ("v2026.06.04", "v2.0.0_redesign"):
        _git(origin, "tag", tag, "main")
    prerelease = {"inputs.release_type": "prerelease", "inputs.bump": "auto"}
    assert _outputs_of(plan, prerelease, clone, tmp_path / "prerelease.out") == {
        "version": "2.1.0-beta.1",
        "tag": "v2.1.0-beta.1",
        "previous": "v2.0.0_redesign",
    }


def test_release_notes_reach_the_publish_job_between_random_delimiters(tmp_path):
    """The notes come from the same script, over the commits after the
    previous release, and leave the key job as an output of several lines.
    Such a value stands between two lines that name its delimiter -- a
    random one: a line of the notes equal to a fixed delimiter would end
    them early, and the lines after it would set outputs of their own."""
    [notes] = [
        step
        for step in _workflow(_RELEASE)["jobs"]["commit"]["steps"]
        if step.get("id") == "notes"
    ]
    assert notes["env"] == {"PREVIOUS": "${{ steps.plan.outputs.previous }}"}
    assert "python3 .github/scripts/release.py notes" in notes["run"]
    origin, clone = _release_clone(
        tmp_path,
        earlier="feat: add a change the previous release shipped",
        validated="feat: add the validated change",
        version_commit=False,
    )
    _with_the_release_script(clone)
    _git(origin, "tag", "v2026.06.04", "main~1")
    _git(clone, "fetch", "--quiet", "--tags")  # as the plan step before it
    previous = {"steps.plan.outputs.previous": "v2026.06.04"}
    delimiters = []
    for run in ("first", "second"):
        output = tmp_path / f"{run}.out"
        assert _outputs_of(notes, previous, clone, output) == {"notes": _NOTES}
        [opening] = [
            line
            for line in output.read_text(encoding="utf-8").splitlines()
            if line.startswith("notes<<")
        ]
        delimiters.append(opening.removeprefix("notes<<"))
    assert delimiters[0] != delimiters[1]


def _as_jq_writes(manifest: dict) -> str:
    """`manifest` laid out as jq writes a JSON object: indented by two
    spaces, one space after each colon, a newline at the end."""
    return json.dumps(manifest, indent=2) + "\n"


def test_release_writes_the_version_into_the_manifest_and_checks_it(tmp_path):
    """The release's reason for being: the version -- without the tag's v
    and without the transition tag's suffix -- goes into manifest.json, the
    file Home Assistant and HACS read, in the commit that is pushed and
    tagged. jq sets its "version". Right after, a check fails the release
    unless the manifest carries exactly that version, and a version at all:
    a bump that did not land would ship a tag whose manifest names the
    previous one. Then the Actions bot adds and commits the file, and
    nothing else. (jq itself runs only in CI, so its command is held as
    written.)"""
    job = _workflow(_RELEASE)["jobs"]["commit"]
    assert job["env"]["MANIFEST"] == _MANIFEST
    assert (Path(__file__).parents[1] / _MANIFEST).is_file()
    steps = job["steps"]
    [plan] = [index for index, step in enumerate(steps) if step.get("id") == "plan"]
    [update] = [index for index, step in enumerate(steps) if "jq " in step.get("run", "")]
    [commit] = [index for index, step in enumerate(steps) if "git commit" in step.get("run", "")]
    assert plan < update < update + 1 < commit
    the_version = {"VERSION": "${{ steps.plan.outputs.version }}"}
    assert steps[update]["env"] == the_version
    written_by_jq = steps[update]["run"]
    assert """jq --arg v "${VERSION}" '.version = $v' "${MANIFEST}" > tmp.json""" in written_by_jq
    assert 'mv tmp.json "${MANIFEST}"' in written_by_jq

    # The check, right after the update, on the manifest as jq leaves it.
    check = steps[update + 1]
    assert check["env"] == the_version
    shipped = json.loads((Path(__file__).parents[1] / _MANIFEST).read_text(encoding="utf-8"))
    written = tmp_path / "written"
    (written / _MANIFEST).parent.mkdir(parents=True)
    checked = {}
    for case, (version, fields) in {
        "bumped": ("2.0.0", {"version": "2.0.0"}),
        "a beta bumped": ("2.1.0-beta.1", {"version": "2.1.0-beta.1"}),
        "not bumped": ("2.0.0", {"version": "2026.06.04"}),
        "another key bumped": ("2.0.0", {"version": "2026.06.04", "Version": "2.0.0"}),
        "a longer version": ("2.1.0", {"version": "2.1.0-beta.1"}),
        "no version": ("", {"version": ""}),
    }.items():
        (written / _MANIFEST).write_text(_as_jq_writes({**shipped, **fields}), encoding="utf-8")
        result = _run_step(
            check,
            {"steps.plan.outputs.version": version},
            cwd=written,
            env={"MANIFEST": _MANIFEST},
        )
        checked[case] = (result.returncode, "::error::" in result.stdout)
    assert checked == {
        "bumped": (0, False),
        "a beta bumped": (0, False),
        "not bumped": (1, True),
        "another key bumped": (1, True),
        "a longer version": (1, True),
        "no version": (1, True),
    }

    # The commit, on top of the validated one: the manifest, and only it.
    repository = tmp_path / "repository"
    (repository / _MANIFEST).parent.mkdir(parents=True)
    (repository / _MANIFEST).write_text(
        _as_jq_writes({**shipped, "version": "2026.06.04"}), encoding="utf-8"
    )
    _git(tmp_path, "init", "--quiet", "--initial-branch=main", str(repository))
    _git(repository, "add", _MANIFEST)
    validated = _commit(repository, "The validated commit")
    (repository / _MANIFEST).write_text(
        _as_jq_writes({**shipped, "version": "2.0.0"}), encoding="utf-8"
    )
    committed = _run_step(
        steps[commit],
        {"steps.plan.outputs.version": "2.0.0"},
        cwd=repository,
        env={"MANIFEST": _MANIFEST},
    )
    assert committed.returncode == 0, committed.stderr
    bot = "github-actions[bot] <github-actions[bot]@users.noreply.github.com>"
    assert _git(repository, "log", "-1", "--format=%s|%an <%ae>|%cn <%ce>") == (
        f"chore: bump version to 2.0.0|{bot}|{bot}"
    )
    assert _git(repository, "rev-parse", "HEAD~1") == validated
    assert _git(repository, "show", "--name-only", "--format=", "HEAD") == _MANIFEST
    assert json.loads(_git(repository, "show", f"HEAD:{_MANIFEST}"))["version"] == "2.0.0"


def test_a_dry_run_shows_the_release_and_pushes_nothing(tmp_path):
    """A dry run goes as far as the version commit, in the runner. Then it
    shows the release type, the version, the tag, the previous release, the
    commit and the notes, checks that the deploy key reaches the repository
    -- when there is one: a dry run may start without it -- and ends. The
    steps after it, and the Publish job, are the ones a dry run skips, and
    the key check before the checkout is the one a real release adds.
    Every other step runs in both: a condition on one of them -- the plan,
    the notes, the manifest, its check, the commit -- could skip what a
    real release must not go without."""
    jobs = _workflow(_RELEASE)["jobs"]
    steps = jobs["commit"]["steps"]
    assert [step["name"] for step in steps if "if" in step] == [
        "Require the deploy key",
        "Dry run - show the release and check the deploy key",
        "Push the version commit and the tag",
    ]
    [dry_run] = [step for step in steps if step.get("if") in _ONLY_A_DRY_RUN]
    [plan] = [index for index, step in enumerate(steps) if step.get("id") == "plan"]
    [notes] = [index for index, step in enumerate(steps) if step.get("id") == "notes"]
    [commit] = [index for index, step in enumerate(steps) if "git commit" in step.get("run", "")]
    ends = steps.index(dry_run)
    assert plan < notes < commit < ends
    assert {step.get("if") for step in steps[ends + 1 :]} == {_NOT_A_DRY_RUN}
    assert jobs["publish"]["if"] == _NOT_A_DRY_RUN
    assert "git ls-remote" in dry_run["run"]

    values = {
        "inputs.release_type": "prerelease",
        "steps.plan.outputs.version": "2.1.0-beta.1",
        "steps.plan.outputs.tag": "v2.1.0-beta.1",
        "steps.plan.outputs.previous": "v2.0.0_redesign",
        "steps.notes.outputs.notes": _NOTES,
        "secrets.RELEASE_DEPLOY_KEY": _A_KEY,
    }
    origin, clone = _release_clone(tmp_path, "dev")
    before = _refs(origin)
    shown = _run_step(dry_run, values, cwd=clone)
    assert shown.returncode == 0, shown.stderr
    assert re.search(r"(?<!v)2\.1\.0-beta\.1", shown.stdout)
    for value in ("prerelease", "v2.1.0-beta.1", "v2.0.0_redesign", "The version commit", _NOTES):
        assert value in shown.stdout, value
    assert _A_KEY not in shown.stdout + shown.stderr
    assert _refs(origin) == before
    # With a key, a repository it cannot reach fails the dry run; without
    # one, the dry run does not try.
    _git(clone, "remote", "set-url", "origin", str(tmp_path / "unreachable.git"))
    assert _run_step(dry_run, values, cwd=clone).returncode != 0
    keyless = _run_step(dry_run, {**values, "secrets.RELEASE_DEPLOY_KEY": ""}, cwd=clone)
    assert keyless.returncode == 0, keyless.stderr
