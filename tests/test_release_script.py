"""Unit tests for `.github/scripts/release.py` -- the version and release
notes computation the release workflow's key job calls (spec section 12,
CONTRIBUTING.md "Releases"). Imported by path: `.github/scripts` is not a
package (there is no `scripts/__init__.py`), so a normal `import` cannot
reach it.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from types import ModuleType

_SCRIPT = Path(__file__).parents[1] / ".github" / "scripts" / "release.py"


def _load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("release_script", _SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # dataclasses (3.14) looks its own module up in sys.modules while
    # processing a decorated class -- without this, exec_module raises.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


release = _load_script()

Version = release.Version
RawCommit = release.RawCommit
Commit = release.Commit
parse_commit = release.parse_commit
compute_bump = release.compute_bump
next_stable_version = release.next_stable_version
next_prerelease_version = release.next_prerelease_version
stable_tag = release.stable_tag
prerelease_tag = release.prerelease_tag
previous_ref = release.previous_ref
build_notes = release.build_notes
parse_legacy_tag = release.parse_legacy_tag
parse_stable_tag = release.parse_stable_tag
parse_prerelease_tag = release.parse_prerelease_tag

# A stand-in tag list once the redesign's own transition tag exists, used by
# several scenarios below (spec 12.4's worked example).
_AFTER_REDESIGN = ["v2026.05.17", "v2026.06.04", "v2.0.0_redesign"]


# --------------------------------------------------------------------------
# parse_commit -- Conventional Commits header + BREAKING CHANGE footer
# --------------------------------------------------------------------------

def test_parse_commit_reads_type_and_description():
    commit = parse_commit(RawCommit(subject="feat: add multi-currency support", body=""))
    assert commit == Commit(
        type="feat", scope=None, breaking=False, description="add multi-currency support"
    )


def test_parse_commit_reads_the_scope():
    commit = parse_commit(RawCommit(subject="fix(sensors): correct balance rounding", body=""))
    assert commit == Commit(
        type="fix", scope="sensors", breaking=False, description="correct balance rounding"
    )


def test_parse_commit_reads_breaking_from_the_bang():
    commit = parse_commit(RawCommit(subject="feat!: drop the legacy sensor", body=""))
    assert commit is not None and commit.breaking is True

    scoped = parse_commit(RawCommit(subject="feat(api)!: drop v1 endpoints", body=""))
    assert scoped == Commit(
        type="feat", scope="api", breaking=True, description="drop v1 endpoints"
    )


def test_parse_commit_reads_breaking_from_the_footer():
    commit = parse_commit(
        RawCommit(
            subject="fix: adjust rounding",
            body="Fixes drift in totals.\n\nBREAKING CHANGE: changes the stored units.",
        )
    )
    assert commit is not None and commit.breaking is True


def test_parse_commit_type_is_case_insensitive():
    commit = parse_commit(RawCommit(subject="Feat: add x", body=""))
    assert commit is not None and commit.type == "feat"


def test_parse_commit_rejects_a_merge_commit_subject():
    """A merge's subject has no "type: description" shape at all, which is
    what keeps merges out of the release notes without a special case."""
    assert parse_commit(RawCommit(subject="Merge pull request #42 from foo/bar", body="")) is None
    assert parse_commit(RawCommit(subject="Merge branch 'dev' into redesign", body="")) is None


def test_parse_commit_rejects_prose_without_a_conventional_header():
    assert parse_commit(RawCommit(subject="oops forgot a file", body="")) is None


# --------------------------------------------------------------------------
# compute_bump
# --------------------------------------------------------------------------

def _commit(type_: str, breaking: bool = False, description: str = "x") -> Commit:
    return Commit(type=type_, scope=None, breaking=breaking, description=description)


def test_compute_bump_override_wins_over_the_commits():
    commits = [_commit("feat")]
    assert compute_bump(commits, "patch") == "patch"
    assert compute_bump(commits, "major") == "major"
    assert compute_bump([], "minor") == "minor"


def test_compute_bump_auto_is_major_when_any_commit_is_breaking():
    commits = [_commit("fix"), _commit("feat", breaking=True)]
    assert compute_bump(commits, "auto") == "major"


def test_compute_bump_auto_is_minor_for_a_feat_without_breaking():
    commits = [_commit("fix"), _commit("feat")]
    assert compute_bump(commits, "auto") == "minor"


def test_compute_bump_auto_is_patch_otherwise():
    assert compute_bump([_commit("fix"), _commit("docs")], "auto") == "patch"
    assert compute_bump([], "auto") == "patch"


# --------------------------------------------------------------------------
# Tag parsing -- legacy date tags are never a SemVer base
# --------------------------------------------------------------------------

def test_parse_legacy_tag_reads_date_and_sequence():
    assert parse_legacy_tag("v2026.06.04") == (2026, 6, 4, 0)
    assert parse_legacy_tag("v2026.09.28-1") == (2026, 9, 28, 1)
    # One tag from before the "v" convention: still legacy.
    assert parse_legacy_tag("2025.10.06") == (2025, 10, 6, 0)
    # Two real tags in this repository's history with a single-digit day --
    # must still classify as legacy, never leak into parse_stable_tag as a
    # syntactically-valid but wrong SemVer (2026.5.1).
    assert parse_legacy_tag("v2026.05.1") == (2026, 5, 1, 0)
    assert parse_legacy_tag("v2.0.0") is None


def test_parse_stable_tag_never_reads_a_legacy_date_as_semver():
    """spec 12.4: v2026.06.04 must never become a SemVer base (it would
    otherwise compute a minor bump as 2026.7.0)."""
    assert parse_stable_tag("v2026.06.04") is None
    assert parse_stable_tag("v2026.09.28-1") is None
    assert parse_stable_tag("v2026.05.1") is None


def test_parse_stable_tag_reads_plain_and_suffixed_tags():
    assert parse_stable_tag("v2.0.0") == Version(2, 0, 0)
    assert parse_stable_tag("v2.0.0_redesign") == Version(2, 0, 0)
    assert parse_stable_tag("v2.1.0-beta.1") is None


def test_parse_prerelease_tag_reads_target_and_beta_number():
    assert parse_prerelease_tag("v2.1.0-beta.2") == (Version(2, 1, 0), 2)
    assert parse_prerelease_tag("v2.0.0_redesign") is None
    assert parse_prerelease_tag("v2026.06.04") is None


# --------------------------------------------------------------------------
# next_stable_version -- spec 12.4's worked examples
# --------------------------------------------------------------------------

def test_next_stable_version_bases_on_1_0_0_with_legacy_tags_only():
    legacy = ["v2026.05.17", "v2026.06.04"]
    assert next_stable_version(legacy, "minor") == Version(1, 1, 0)
    assert next_stable_version(legacy, "major") == Version(2, 0, 0)


def test_next_stable_version_never_bases_on_a_legacy_date():
    """A single legacy tag whose numbers look like a plausible SemVer
    (v2026.09.28-1) must still bump from 1.0.0, not from 2026.9.28."""
    assert next_stable_version(["v2026.09.28-1"], "patch") == Version(1, 0, 1)


def test_next_stable_version_bumps_the_latest_stable_tag():
    assert next_stable_version(_AFTER_REDESIGN, "patch") == Version(2, 0, 1)
    assert next_stable_version(_AFTER_REDESIGN, "minor") == Version(2, 1, 0)
    assert next_stable_version(_AFTER_REDESIGN, "major") == Version(3, 0, 0)


def test_next_stable_version_picks_the_highest_stable_tag():
    tags = [*_AFTER_REDESIGN, "v2.1.0"]
    assert next_stable_version(tags, "patch") == Version(2, 1, 1)


# --------------------------------------------------------------------------
# stable_tag -- the one-time "_redesign" suffix
# --------------------------------------------------------------------------

def test_stable_tag_suffixes_the_first_semver_stable_only():
    legacy = ["v2026.05.17", "v2026.06.04"]
    assert stable_tag(Version(2, 0, 0), legacy) == "v2.0.0_redesign"


def test_stable_tag_is_plain_once_a_stable_tag_exists():
    assert stable_tag(Version(2, 0, 1), _AFTER_REDESIGN) == "v2.0.1"
    assert stable_tag(Version(2, 1, 0), _AFTER_REDESIGN) == "v2.1.0"


# --------------------------------------------------------------------------
# next_prerelease_version / prerelease_tag -- betas target the next stable
# --------------------------------------------------------------------------

def test_prerelease_targets_1_x_successor_with_legacy_tags_only():
    legacy = ["v2026.05.17", "v2026.06.04"]
    assert next_prerelease_version(legacy, "major") == (Version(2, 0, 0), 1)
    assert prerelease_tag(Version(2, 0, 0), 1) == "v2.0.0-beta.1"


def test_prerelease_numbering_counts_existing_betas_of_the_same_target():
    tags = [*_AFTER_REDESIGN, "v2.1.0-beta.1", "v2.1.0-beta.2"]
    assert next_prerelease_version(tags, "minor") == (Version(2, 1, 0), 3)
    assert prerelease_tag(Version(2, 1, 0), 3) == "v2.1.0-beta.3"


def test_prerelease_after_a_stable_targets_the_next_stable():
    tags = [*_AFTER_REDESIGN, "v2.1.0"]
    assert next_prerelease_version(tags, "patch") == (Version(2, 1, 1), 1)
    assert prerelease_tag(Version(2, 1, 1), 1) == "v2.1.1-beta.1"


# --------------------------------------------------------------------------
# previous_ref -- the tag notes (and a stable bump) start after
# --------------------------------------------------------------------------

def test_previous_ref_stable_falls_back_to_the_newest_legacy_tag():
    legacy = ["v2026.05.17", "v2026.06.04", "v2026.05.1"]
    assert previous_ref(legacy, "stable") == "v2026.06.04"


def test_previous_ref_stable_counts_a_suffixed_tag():
    tags = ["v2026.05.17", "v2026.06.04", "v2.0.0_redesign"]
    assert previous_ref(tags, "stable") == "v2.0.0_redesign"


def test_previous_ref_stable_picks_the_highest_stable_tag():
    tags = [*_AFTER_REDESIGN, "v2.1.0"]
    assert previous_ref(tags, "stable") == "v2.1.0"


def test_previous_ref_stable_with_no_tags_at_all_is_none():
    assert previous_ref([], "stable") is None


def test_previous_ref_prerelease_is_the_newest_of_either_semver_kind():
    # A pre-release of the next stable outranks the current stable (spec
    # 12.4's verified ordering: 2.1.0-beta.1 > 2.0.0).
    assert previous_ref(["v2.0.0_redesign", "v2.1.0-beta.1"], "prerelease") == "v2.1.0-beta.1"
    # A published stable outranks a pre-release of that same version.
    assert previous_ref(["v2.1.0-beta.1", "v2.1.0"], "prerelease") == "v2.1.0"
    # The higher beta number wins among pre-releases of the same target.
    assert (
        previous_ref(["v2.1.0-beta.1", "v2.1.0-beta.2"], "prerelease") == "v2.1.0-beta.2"
    )


def test_previous_ref_prerelease_ignores_legacy_tags():
    """A pre-release cut before any SemVer stable exists has no previous
    tag of "either type" -- its notes cover the whole history."""
    assert previous_ref(["v2026.05.17", "v2026.06.04"], "prerelease") is None


# --------------------------------------------------------------------------
# build_notes -- sections, item order, and what never gets listed
# --------------------------------------------------------------------------

def test_build_notes_with_nothing_to_list():
    assert build_notes([]) == "No user-facing changes."


def test_build_notes_excludes_internal_types_merges_and_the_version_commit():
    """Review focus: test/ci/chore/build, merge commits and the release's
    own "chore: bump version to ..." commit are never listed."""
    commits = [
        RawCommit(subject="test: add a regression test", body=""),
        RawCommit(subject="ci: cache pip downloads", body=""),
        RawCommit(subject="build: bump the pinned image", body=""),
        RawCommit(subject="chore: bump version to 2.0.1", body=""),
        RawCommit(subject="Merge pull request #7 from foo/bar", body=""),
    ]
    assert build_notes(commits) == "No user-facing changes."


def test_build_notes_renders_a_scoped_and_an_unscoped_item():
    commits = [
        RawCommit(subject="feat: add multi-currency support", body=""),
        RawCommit(subject="fix(sensors): correct balance rounding", body=""),
    ]
    notes = build_notes(commits)
    assert "### ✨ New Features\n\n- Add multi-currency support" in notes
    assert "### \U0001F41B Bug Fixes\n\n- **sensors:** Correct balance rounding" in notes


def test_build_notes_maps_every_type_and_scope_to_its_section():
    commits = [
        RawCommit(subject="perf: speed up the wallet coordinator", body=""),
        RawCommit(subject="fix(security): patch a token leak", body=""),
        RawCommit(subject="refactor: split the api client", body=""),
        RawCommit(subject="style: reformat the sensor module", body=""),
        RawCommit(subject="docs: describe the new sensors", body=""),
    ]
    notes = build_notes(commits)
    assert "### ⚡ Improvements\n\n- Speed up the wallet coordinator" in notes
    # scope=security wins over the fix type -- listed only under Security.
    assert "### \U0001F512 Security\n\n- **security:** Patch a token leak" in notes
    assert "### \U0001F41B Bug Fixes" not in notes
    assert "Refactor & Code Quality\n\n- Split the api client\n- Reformat the sensor module" in notes
    assert "### \U0001F4DD Documentation\n\n- Describe the new sensors" in notes


def test_build_notes_files_a_breaking_commit_only_under_breaking_changes():
    commits = [RawCommit(subject="feat!: drop the legacy sensor", body="")]
    notes = build_notes(commits)
    assert notes == "### \U0001F4A5 Breaking Changes\n\n- Drop the legacy sensor"
    assert "New Features" not in notes


def test_build_notes_footer_breaking_change_also_files_under_breaking_only():
    commits = [
        RawCommit(
            subject="fix: adjust rounding",
            body="BREAKING CHANGE: changes the stored units.",
        )
    ]
    notes = build_notes(commits)
    assert notes == "### \U0001F4A5 Breaking Changes\n\n- Adjust rounding"
    assert "Bug Fixes" not in notes


def test_build_notes_orders_sections_in_the_global_order_and_omits_empty_ones():
    commits = [
        RawCommit(subject="docs: update the readme", body=""),
        RawCommit(subject="feat: add a new sensor", body=""),
        RawCommit(subject="fix: correct a typo", body=""),
    ]
    notes = build_notes(commits)
    # New Features, then Bug Fixes, then Documentation -- Breaking Changes,
    # Improvements, Security and Refactor & Code Quality are all empty and
    # must not appear at all.
    assert notes == (
        "### ✨ New Features\n\n- Add a new sensor"
        "\n\n### \U0001F41B Bug Fixes\n\n- Correct a typo"
        "\n\n### \U0001F4DD Documentation\n\n- Update the readme"
    )


def test_build_notes_item_order_is_added_changed_fixed_removed():
    commits = [
        RawCommit(subject="feat: fix the onboarding hint wording", body=""),
        RawCommit(subject="feat: add a portfolio sensor", body=""),
        RawCommit(subject="feat: streamline the config flow", body=""),
        RawCommit(subject="feat: remove the deprecated icon option", body=""),
        RawCommit(subject="feat: add a second sensor", body=""),
    ]
    notes = build_notes(commits)
    assert notes == (
        "### ✨ New Features\n\n"
        "- Add a portfolio sensor\n"
        "- Add a second sensor\n"
        "- Streamline the config flow\n"
        "- Fix the onboarding hint wording\n"
        "- Remove the deprecated icon option"
    )


# --------------------------------------------------------------------------
# plan() / notes_command() -- the CLI's orchestration, git calls stubbed out
# --------------------------------------------------------------------------

def test_plan_stable_from_legacy_tags_only(monkeypatch):
    monkeypatch.setattr(release, "git_tags", lambda: ["v2026.05.17", "v2026.06.04"])
    monkeypatch.setattr(release, "list_commits", lambda from_ref, to_ref: [])
    assert release.plan("stable", "major") == {
        "version": "2.0.0",
        "tag": "v2.0.0_redesign",
        "previous": "v2026.06.04",
    }


def test_plan_prerelease_targets_the_next_stable(monkeypatch):
    monkeypatch.setattr(
        release, "git_tags", lambda: ["v2.0.0_redesign", "v2.1.0-beta.1"]
    )
    monkeypatch.setattr(
        release,
        "list_commits",
        lambda from_ref, to_ref: [RawCommit(subject="feat: add y", body="")],
    )
    assert release.plan("prerelease", "auto") == {
        "version": "2.1.0-beta.2",
        "tag": "v2.1.0-beta.2",
        "previous": "v2.1.0-beta.1",
    }


def test_plan_bump_auto_reads_commits_since_the_latest_stable_tag(monkeypatch):
    """The bump always looks at commits since the latest *stable* tag, even
    for a pre-release -- so a beta's version target stays put across
    several betas regardless of what the previous *pre-release* tag was."""
    seen_ranges = []

    def fake_list_commits(from_ref: str, to_ref: str):
        seen_ranges.append((from_ref, to_ref))
        return [RawCommit(subject="feat: add y", body="")]

    monkeypatch.setattr(
        release, "git_tags", lambda: ["v2.0.0_redesign", "v2.1.0-beta.1"]
    )
    monkeypatch.setattr(release, "list_commits", fake_list_commits)
    release.plan("prerelease", "auto")
    assert seen_ranges == [("v2.0.0_redesign", "HEAD")]


def test_notes_command_delegates_to_build_notes(monkeypatch):
    commits = [RawCommit(subject="feat: add z", body="")]
    monkeypatch.setattr(release, "list_commits", lambda from_ref, to_ref: commits)
    assert release.notes_command("v1.0.0", "HEAD") == build_notes(commits)


# --------------------------------------------------------------------------
# main() -- the exact $GITHUB_OUTPUT and Markdown text printed
# --------------------------------------------------------------------------

def test_main_plan_prints_key_value_lines(monkeypatch, capsys):
    monkeypatch.setattr(release, "git_tags", lambda: ["v2026.06.04"])
    monkeypatch.setattr(release, "list_commits", lambda from_ref, to_ref: [])
    exit_code = release.main(["plan", "--type", "stable", "--bump", "major"])
    assert exit_code == 0
    assert capsys.readouterr().out == "version=2.0.0\ntag=v2.0.0_redesign\nprevious=v2026.06.04\n"


def test_main_notes_prints_markdown(monkeypatch, capsys):
    monkeypatch.setattr(
        release,
        "list_commits",
        lambda from_ref, to_ref: [RawCommit(subject="feat: add a", body="")],
    )
    exit_code = release.main(["notes", "--from", "", "--to", "HEAD"])
    assert exit_code == 0
    assert capsys.readouterr().out == "### ✨ New Features\n\n- Add a\n"
