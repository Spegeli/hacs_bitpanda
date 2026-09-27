"""The contract of the GitHub workflows.

GitHub alone runs these files, and a mistake in one shows only there --
often only when it matters: a required check that stays green although the
tests failed, a workflow GitHub has quietly disabled. These tests read the
YAML and hold the decisions CONTRIBUTING.md ("Continuous integration")
describes.
"""
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


_CURRENT_MAJORS = {"actions/checkout": "v7", "actions/setup-python": "v7"}


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
    one. Only the tests and mypy, minutes each, can be switched off."""
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
        assert "inputs.tests" in jobs[name]["if"], name


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


# The results GitHub reports for a job a later job needs.
_JOB_RESULTS = ("success", "failure", "cancelled", "skipped")
_A_JOB_RESULT = re.compile(r"\$\{\{\s*needs\.[\w-]+\.result\s*\}\}")


def _exit_status(step: dict, result: str) -> int:
    """The exit status of the step's script, run as GitHub runs it
    (`bash -e`), with every job result its `env` reads set to `result`."""
    env = {
        variable: result
        for variable, value in step.get("env", {}).items()
        if _A_JOB_RESULT.fullmatch(str(value))
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
    other job -- one it did not wait for could fail and leave it green.
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
    assert [value for value in _JOB_RESULTS if value in step["run"]] == ["success"]
    assert "exit 1" in step["run"]
    assert {value: _exit_status(step, value) for value in _JOB_RESULTS} == {
        "success": 0,
        "failure": 1,
        "cancelled": 1,
        "skipped": 1,
    }
