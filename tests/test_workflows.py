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


# release.yml, "Create Release": validates, then commits the version to main
# through the deploy key and tags it (job "commit", which holds the key),
# then creates the GitHub release (job "publish", which does not).
_RELEASE = "release.yml"
_DEPLOY_KEY = "${{ secrets.RELEASE_DEPLOY_KEY }}"
# The condition of every step and job a dry run skips, and the spellings of
# the condition of the one step only a dry run runs.
_NOT_A_DRY_RUN = "${{ !inputs.dry_run }}"
_ONLY_A_DRY_RUN = ("inputs.dry_run", "${{ inputs.dry_run }}")
# Stands in for the deploy key's private key, which no script may print.
_A_KEY = "deploy-key-stand-in"
# An `env` value that is one expression, such as ${{ secrets.X }}.
_AN_EXPRESSION = re.compile(r"\$\{\{\s*(.+?)\s*\}\}")


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


def _release_clone(directory: Path) -> tuple[Path, Path]:
    """What the release job holds when it pushes, as (origin, clone):
    origin, a bare repository whose main is the validated commit, and a
    clone of it checked out at that commit, detached -- as actions/checkout
    leaves a SHA -- with the version commit on top, and the identity the
    job's commit step configures, so a script can commit as it could
    there."""
    directory.mkdir(parents=True, exist_ok=True)
    origin, clone = directory / "origin.git", directory / "clone"
    _git(directory, "init", "--quiet", "--bare", "--initial-branch=main", str(origin))
    _git(directory, "clone", "--quiet", str(origin), str(clone))
    _git(clone, "config", "user.name", "github-actions[bot]")
    _git(clone, "config", "user.email", "github-actions[bot]@users.noreply.github.com")
    _commit(clone, "The validated commit")
    _git(clone, "push", "--quiet", "origin", "HEAD:main")
    _git(clone, "switch", "--quiet", "--detach")
    _commit(clone, "The version commit")
    return origin, clone


def _merged_meanwhile(origin: Path) -> str:
    """Moves origin's main on by one commit, as a pull request merged while
    a release runs; the commit main moved to."""
    other = origin.parent / "meanwhile"
    _git(origin.parent, "clone", "--quiet", str(origin), str(other))
    merged = _commit(other, "A pull request merged meanwhile")
    _git(other, "push", "--quiet", "origin", "HEAD:main")
    return merged


def _utc_clock(directory: Path, today: str) -> str:
    """A PATH on which `date -u +%Y.%m.%d` prints `today` and any other
    `date` fails: the release's clock, fixed, and in UTC only."""
    bin_directory = directory / "bin"
    bin_directory.mkdir()
    date = bin_directory / "date"
    date.write_text(
        "#!/bin/sh\n"
        f'if [ "$*" = "-u +%Y.%m.%d" ]; then echo {today}; else exit 64; fi\n',
        encoding="utf-8",
    )
    date.chmod(0o755)
    return f"{bin_directory}{os.pathsep}{os.environ['PATH']}"


def _determine_version(step: dict, clone: Path, path: str) -> dict[str, str]:
    """Run the version step in `clone`, with `path` as PATH; the outputs
    it sets."""
    output = clone.parent / "github_output"
    output.write_text("", encoding="utf-8")
    result = _run_step(step, cwd=clone, env={"PATH": path, "GITHUB_OUTPUT": str(output)})
    assert result.returncode == 0, result.stderr
    return dict(line.split("=", 1) for line in output.read_text(encoding="utf-8").splitlines())


def test_release_runs_only_by_hand_with_draft_and_dry_run():
    """Only the maintainer starts a release. It opens as a draft, for the
    changelog, and a dry run checks the path without pushing anything. One
    release runs at a time and is never cancelled halfway through its
    pushes; the token only reads, unless a job asks for more."""
    release = _workflow(_RELEASE)
    assert list(release["on"]) == ["workflow_dispatch"]
    inputs = release["on"]["workflow_dispatch"]["inputs"]
    assert sorted(inputs) == ["draft", "dry_run"]
    assert inputs["draft"]["type"] == "boolean"
    assert inputs["draft"]["default"] is True
    assert inputs["dry_run"]["type"] == "boolean"
    assert inputs["dry_run"]["default"] is False
    assert release["concurrency"] == {"group": "release", "cancel-in-progress": False}
    assert release["permissions"] == {"contents": "read"}


def test_release_refuses_other_branches_before_anything_else():
    """A release commits to main, tags and publishes, so it runs from main
    only. Started from another branch or a tag, it fails at its first job;
    each job after it waits for the one before, and none has an if: that
    would run it anyway -- the Publish job's only skips a dry run. Nothing
    carries the run past a failure either: continue-on-error on the guard --
    or on the key check or the push -- would let the release go on."""
    jobs = _workflow(_RELEASE)["jobs"]
    assert sorted(jobs) == ["commit", "only-main", "publish", "validate"]
    only_main = jobs["only-main"]
    assert only_main["name"] == "Only on main"
    assert only_main["permissions"] == {}
    assert "needs" not in only_main
    assert "if" not in only_main
    [guard] = only_main["steps"]
    assert "if" not in guard
    assert "GITHUB_REF" in guard["run"]
    assert "refs/heads/main" in guard["run"]
    assert "exit 1" in guard["run"]
    started_from = {
        ref: _run_step(
            guard, env={"GITHUB_REF": ref, "GITHUB_REF_NAME": ref.split("/", 2)[2]}
        ).returncode
        for ref in (
            "refs/heads/main",
            "refs/heads/redesign",
            "refs/heads/main-backup",
            "refs/tags/v2026.09.27",
        )
    }
    assert started_from == {
        "refs/heads/main": 0,
        "refs/heads/redesign": 1,
        "refs/heads/main-backup": 1,
        "refs/tags/v2026.09.27": 1,
    }
    assert "only-main" in _needs(jobs["validate"])
    assert "validate" in _needs(jobs["commit"])
    assert "commit" in _needs(jobs["publish"])
    assert "if" not in jobs["validate"]
    assert "if" not in jobs["commit"]
    assert jobs["publish"]["if"] == _NOT_A_DRY_RUN
    assert [
        (key, part.get("name"))
        for key, job in jobs.items()
        for part in (job, *job.get("steps", []))
        if "continue-on-error" in part
    ] == []


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
    on. The version commit goes on top of exactly that commit, never on
    main as it is by then, which may have moved on, unvalidated: nothing in
    the job pulls, rebases, merges, resets or switches it onto another. The
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
    """Only the deploy key can push the version commit to main. Without it
    a release stops at once, with the reason: otherwise checkout would fall
    back to the job's token, which only reads, and the release would fail at
    the push, after the commit, with a refusal that hides why. GitHub allows
    no secret in an if:, so the script tests the key, and never prints it.
    A dry run pushes nothing and needs no key."""
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
    actions/checkout: the rest is shell. Its token only reads -- it pushes
    with the key, over SSH. The GitHub release is created in a job of its
    own, with a token that may write, without checkout and without the key;
    a dry run skips it. The validation's third-party actions get no secret
    either."""
    jobs = _workflow(_RELEASE)["jobs"]
    assert [key for key, job in jobs.items() if "RELEASE_DEPLOY_KEY" in str(job)] == ["commit"]
    commit, publish = jobs["commit"], jobs["publish"]
    assert [step["uses"] for step in commit["steps"] if "uses" in step] == ["actions/checkout@v7"]
    assert commit["permissions"] == {"contents": "read"}
    assert publish["name"] == "Publish release"
    assert _needs(publish) == ["commit"]
    assert publish["if"] == _NOT_A_DRY_RUN
    assert publish["permissions"] == {"contents": "write"}
    assert [
        step for step in publish["steps"] if step.get("uses", "").startswith("actions/checkout@")
    ] == []
    assert "secrets" not in jobs["validate"]


def test_release_pushes_without_force_and_tags_only_after_the_commit(tmp_path):
    """The push to main is the safety net. It is a plain push of the version
    commit, which sits on the validated commit: if main moved meanwhile -- a
    pull request merged while the release ran -- the push is no fast-forward
    and main refuses it; the script stops there, and nothing unvalidated is
    tagged or released. Forced, it would throw the merged change away: the
    deploy key passes main's ruleset, its block on force pushes included. The
    release is created only after the push, from the tag the pushing job
    hands on. A dry run pushes, tags and publishes nothing."""
    jobs = _workflow(_RELEASE)["jobs"]
    every_step = [step for job in jobs.values() for step in job.get("steps", [])]
    [push] = [step for step in every_step if "git push" in step.get("run", "")]
    assert push in jobs["commit"]["steps"]
    lines = push["run"].splitlines()
    pushes = [line for line in lines if "git push" in line]
    assert "git push origin HEAD:main" in pushes[0]
    # The tag's push, in the same script, after the commit's.
    assert len(pushes) > 1
    tagging = [index for index, line in enumerate(lines) if re.search(r"\bgit tag\b", line)]
    assert tagging
    assert min(tagging) > lines.index(pushes[0])
    assert [line for line in pushes if any(_forces(word) for word in line.split())] == []
    [create] = [
        step
        for step in every_step
        if step.get("uses", "").startswith("softprops/action-gh-release@")
    ]
    assert create in jobs["publish"]["steps"]
    assert create["uses"] == "softprops/action-gh-release@v3"
    assert push["if"] == _NOT_A_DRY_RUN
    assert jobs["publish"]["if"] == _NOT_A_DRY_RUN
    assert "commit" in _needs(jobs["publish"])
    assert jobs["commit"]["outputs"] == {"tag": "${{ steps.version.outputs.tag }}"}
    assert create["with"]["tag_name"] == "${{ needs.commit.outputs.tag }}"
    assert create["with"]["draft"] == "${{ inputs.draft }}"
    assert create["with"]["generate_release_notes"] is True

    tag = {"steps.version.outputs.tag": "v2026.09.27"}
    origin, clone = _release_clone(tmp_path / "main-unchanged")
    version_commit = _git(clone, "rev-parse", "HEAD")
    released = _run_step(push, tag, cwd=clone)
    assert released.returncode == 0, released.stderr
    assert _refs(origin) == {
        "refs/heads/main": version_commit,
        "refs/tags/v2026.09.27": version_commit,
    }

    origin, clone = _release_clone(tmp_path / "main-moved")
    merged = _merged_meanwhile(origin)
    refused = _run_step(push, tag, cwd=clone)
    assert refused.returncode != 0
    assert _refs(origin) == {"refs/heads/main": merged}


def test_release_versions_by_utc_date_and_commits_as_the_actions_bot(tmp_path):
    """The version is the date in UTC, YYYY.MM.DD, tagged v<version>. A
    second release on the same day becomes -1, a third -2: a tag is never
    reused. The Actions bot commits it into the manifest Home Assistant and
    HACS read."""
    release = _workflow(_RELEASE)
    job = release["jobs"]["commit"]
    [version] = [step for step in job["steps"] if step.get("id") == "version"]
    assert 'date -u +"%Y.%m.%d"' in version["run"]
    origin, clone = _release_clone(tmp_path)
    path = _utc_clock(tmp_path, "2026.09.27")
    _git(origin, "tag", "v2026.09.26", "main")
    assert _determine_version(version, clone, path) == {
        "version": "2026.09.27",
        "tag": "v2026.09.27",
    }
    _git(origin, "tag", "v2026.09.27", "main")
    assert _determine_version(version, clone, path) == {
        "version": "2026.09.27-1",
        "tag": "v2026.09.27-1",
    }
    _git(origin, "tag", "v2026.09.27-1", "main")
    assert _determine_version(version, clone, path) == {
        "version": "2026.09.27-2",
        "tag": "v2026.09.27-2",
    }

    manifest = "custom_components/bitpanda/manifest.json"
    assert (Path(__file__).parents[1] / manifest).is_file()
    assert release["env"]["MANIFEST"] == manifest
    script = _script(job)
    assert 'git commit -m "chore: bump version to ' in script
    assert 'git config user.name "github-actions[bot]"' in script
    assert 'git config user.email "github-actions[bot]@users.noreply.github.com"' in script


def _as_jq_writes(manifest: dict) -> str:
    """`manifest` laid out as jq writes a JSON object: indented by two
    spaces, one space after each colon, a newline at the end."""
    return json.dumps(manifest, indent=2) + "\n"


def test_release_writes_the_version_into_the_manifest_and_checks_it(tmp_path):
    """The release's reason for being: the version goes into manifest.json,
    the file Home Assistant and HACS read, in the commit that is pushed and
    tagged. jq sets its "version". Right after, a check fails the release
    unless the manifest carries exactly that version -- a bump that did not
    land would ship a tag whose manifest names the previous one. Then the
    file is added and committed, and nothing else. (jq itself runs only in
    CI, so its command is held as written.)"""
    release = _workflow(_RELEASE)
    manifest = release["env"]["MANIFEST"]
    steps = release["jobs"]["commit"]["steps"]
    [version] = [index for index, step in enumerate(steps) if step.get("id") == "version"]
    [update] = [index for index, step in enumerate(steps) if "jq " in step.get("run", "")]
    [commit] = [index for index, step in enumerate(steps) if "git commit" in step.get("run", "")]
    assert version < update < update + 1 < commit
    assert steps[update]["env"] == {"VERSION": "${{ steps.version.outputs.version }}"}
    written_by_jq = steps[update]["run"]
    assert """jq --arg v "${VERSION}" '.version = $v' "${MANIFEST}" > tmp.json""" in written_by_jq
    assert 'mv tmp.json "${MANIFEST}"' in written_by_jq

    # The check, right after the update, on the manifest as jq leaves it.
    check = steps[update + 1]
    shipped = json.loads((Path(__file__).parents[1] / manifest).read_text(encoding="utf-8"))
    version_value = {"steps.version.outputs.version": "2026.09.27"}
    written = tmp_path / "written"
    (written / manifest).parent.mkdir(parents=True)
    checked = {}
    for case, fields in {
        "bumped": {"version": "2026.09.27"},
        "not bumped": {"version": "2026.06.04"},
        "another key bumped": {"version": "2026.06.04", "Version": "2026.09.27"},
        "a longer version": {"version": "2026.09.27-1"},
    }.items():
        (written / manifest).write_text(_as_jq_writes({**shipped, **fields}), encoding="utf-8")
        result = _run_step(check, version_value, cwd=written, env={"MANIFEST": manifest})
        checked[case] = (result.returncode, "::error::" in result.stdout)
    assert checked == {
        "bumped": (0, False),
        "not bumped": (1, True),
        "another key bumped": (1, True),
        "a longer version": (1, True),
    }

    # The commit, on top of the validated one: the manifest, and only it.
    repository = tmp_path / "repository"
    (repository / manifest).parent.mkdir(parents=True)
    (repository / manifest).write_text(
        _as_jq_writes({**shipped, "version": "2026.06.04"}), encoding="utf-8"
    )
    _git(tmp_path, "init", "--quiet", "--initial-branch=main", str(repository))
    _git(repository, "add", manifest)
    validated = _commit(repository, "The validated commit")
    (repository / manifest).write_text(
        _as_jq_writes({**shipped, "version": "2026.09.27"}), encoding="utf-8"
    )
    committed = _run_step(steps[commit], version_value, cwd=repository, env={"MANIFEST": manifest})
    assert committed.returncode == 0, committed.stderr
    bot = "github-actions[bot] <github-actions[bot]@users.noreply.github.com>"
    assert _git(repository, "log", "-1", "--format=%s|%an <%ae>|%cn <%ce>") == (
        f"chore: bump version to 2026.09.27|{bot}|{bot}"
    )
    assert _git(repository, "rev-parse", "HEAD~1") == validated
    assert _git(repository, "show", "--name-only", "--format=", "HEAD") == manifest
    assert json.loads(_git(repository, "show", f"HEAD:{manifest}"))["version"] == "2026.09.27"


def test_a_dry_run_checks_the_deploy_key_and_publishes_nothing(tmp_path):
    """A dry run goes as far as the version commit, in the runner. Then it
    shows the version, the tag and the commit, checks that the deploy key
    reaches the repository -- when there is one: a dry run may start without
    it -- and ends. The steps after it, and the Publish job, are the ones a
    dry run skips."""
    jobs = _workflow(_RELEASE)["jobs"]
    steps = jobs["commit"]["steps"]
    [dry_run] = [step for step in steps if step.get("if") in _ONLY_A_DRY_RUN]
    [version] = [index for index, step in enumerate(steps) if step.get("id") == "version"]
    [commit] = [index for index, step in enumerate(steps) if "git commit" in step.get("run", "")]
    ends = steps.index(dry_run)
    assert version < commit < ends
    assert {step.get("if") for step in steps[ends + 1 :]} == {_NOT_A_DRY_RUN}
    assert jobs["publish"]["if"] == _NOT_A_DRY_RUN
    assert "git ls-remote" in dry_run["run"]

    values = {
        "steps.version.outputs.version": "2026.09.27-1",
        "steps.version.outputs.tag": "v2026.09.27-1",
        "secrets.RELEASE_DEPLOY_KEY": _A_KEY,
    }
    origin, clone = _release_clone(tmp_path)
    before = _refs(origin)
    shown = _run_step(dry_run, values, cwd=clone)
    assert shown.returncode == 0, shown.stderr
    assert re.search(r"(?<!v)2026\.09\.27-1", shown.stdout)
    assert "v2026.09.27-1" in shown.stdout
    assert "The version commit" in shown.stdout
    assert _A_KEY not in shown.stdout + shown.stderr
    assert _refs(origin) == before
    # With a key, a repository it cannot reach fails the dry run; without
    # one, the dry run does not try.
    _git(clone, "remote", "set-url", "origin", str(tmp_path / "unreachable.git"))
    assert _run_step(dry_run, values, cwd=clone).returncode != 0
    keyless = _run_step(dry_run, {**values, "secrets.RELEASE_DEPLOY_KEY": ""}, cwd=clone)
    assert keyless.returncode == 0, keyless.stderr
