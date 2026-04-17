"""Tests for git-ref resolution in `exploder diff`. Spins up a fresh repo per
test with two commits of a known YAML so assertions don't depend on the host
repo's history."""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from exploder import DiffInputError, _resolve_diff_inputs, main


# Two versions of a loadable ontology. v1 and v2 differ by a single role body
# field, so the diff should surface a typed ElementChange for that role.

V1_YAML = """\
id: https://test.example/gitref
name: gitref_test
prefixes:
  linkml: https://w3id.org/linkml/
  scont:  https://e2e-ontology.dev/
default_prefix: scont
imports:
  - linkml:types

classes:
  Payload:
    description: "payload"
    annotations:
      scont:domain: dom
    attributes:
      id:
        range: string
        required: true

  role_a:
    instantiates: [scont:Role]
    annotations:
      scont:domain: dom
      scont:role: >-
        {"description": "A", "llm_prompt_hint": "h"}
  role_b:
    instantiates: [scont:Role]
    annotations:
      scont:domain: dom
      scont:role: >-
        {"description": "B", "llm_prompt_hint": "h"}

  flow_one:
    instantiates: [scont:InformationFlow]
    annotations:
      scont:domain: dom
      scont:flow: >-
        {"source_role": "role_a", "target_role": "role_b", "quantum": "Payload"}
      scont:llm_prompt_hint: "hint"
"""

V2_YAML = V1_YAML.replace(
    '{"description": "A", "llm_prompt_hint": "h"}',
    '{"description": "A-v2", "llm_prompt_hint": "h"}',
)


@pytest.fixture
def git_repo(tmp_path, monkeypatch):
    """Create a throwaway git repo with two commits of ont.yaml, cwd'd into it."""
    repo = tmp_path / "repo"
    repo.mkdir()
    # Isolate from user/system git config (commits still need an identity).
    env_overrides = {
        "GIT_AUTHOR_NAME": "test",
        "GIT_AUTHOR_EMAIL": "test@test.invalid",
        "GIT_COMMITTER_NAME": "test",
        "GIT_COMMITTER_EMAIL": "test@test.invalid",
    }
    for k, v in env_overrides.items():
        monkeypatch.setenv(k, v)

    def run(*args):
        subprocess.run(args, cwd=repo, check=True, capture_output=True)

    run("git", "init", "-q", "-b", "main")
    (repo / "ont.yaml").write_text(V1_YAML)
    run("git", "add", "ont.yaml")
    run("git", "commit", "-q", "-m", "v1")
    (repo / "ont.yaml").write_text(V2_YAML)
    run("git", "add", "ont.yaml")
    run("git", "commit", "-q", "-m", "v2")

    monkeypatch.chdir(repo)
    return repo


class TestBareRefDiff:
    def test_head_minus_one_head_with_file_flag(self, git_repo, capsys):
        rc = main(["diff", "HEAD~1", "HEAD", "--file", "ont.yaml", "--json"])
        assert rc == 0
        payload = json.loads(capsys.readouterr().out)
        roles_entry = next(p for p in payload if p["kind"] == "roles")
        change = next(c for c in roles_entry["changed"] if c["name"] == "role_a")
        paths = [c[0] for c in change["changes"]]
        assert "body.description" in paths

    def test_bare_ref_without_file_fails_clearly(self, git_repo, capsys):
        rc = main(["diff", "HEAD~1", "HEAD"])
        err = capsys.readouterr().err
        assert rc == 2
        assert "bare git ref" in err


class TestRefColonPathSyntax:
    def test_ref_colon_path_form(self, git_repo, capsys):
        rc = main(["diff", "HEAD~1:ont.yaml", "HEAD:ont.yaml", "--json"])
        assert rc == 0
        payload = json.loads(capsys.readouterr().out)
        assert any(p["kind"] == "roles" for p in payload)

    def test_ref_colon_path_with_missing_file_fails_clearly(self, git_repo, capsys):
        rc = main(["diff", "HEAD~1:missing.yaml", "HEAD:ont.yaml"])
        err = capsys.readouterr().err
        assert rc == 2
        assert "missing.yaml" in err


class TestMixedRefAndPath:
    def test_ref_vs_working_tree_infers_file(self, git_repo, capsys):
        # Working tree == HEAD (v2). Ref == HEAD~1 (v1). Basename of the disk
        # arg supplies the file for the ref arg.
        rc = main(["diff", "HEAD~1", "ont.yaml", "--json"])
        assert rc == 0
        payload = json.loads(capsys.readouterr().out)
        roles_entry = next(p for p in payload if p["kind"] == "roles")
        assert any(c["name"] == "role_a" for c in roles_entry["changed"])

    def test_path_vs_ref_infers_file(self, git_repo, capsys):
        # Reversed order. path1=disk (v2), path2=ref (v1). Delta is symmetric.
        rc = main(["diff", "ont.yaml", "HEAD~1", "--json"])
        assert rc == 0
        payload = json.loads(capsys.readouterr().out)
        assert any(p["kind"] == "roles" for p in payload)


class TestErrorPaths:
    def test_bad_ref_reports_cleanly(self, git_repo, capsys):
        rc = main(["diff", "nonexistent-ref", "HEAD", "--file", "ont.yaml"])
        err = capsys.readouterr().err
        assert rc == 2
        assert "nonexistent-ref" in err

    def test_resolver_returns_same_content_at_matching_refs(self, git_repo):
        # Same ref twice → both resolved paths should have identical contents.
        with _resolve_diff_inputs("HEAD", "HEAD", "ont.yaml") as (p1, p2):
            assert p1.read_text() == p2.read_text()

    def test_direct_resolver_surfaces_bad_ref(self):
        with pytest.raises(DiffInputError):
            # Even outside a repo (or in the top repo without that ref)
            with _resolve_diff_inputs("definitely-not-a-ref-xyz", "definitely-not-a-ref-xyz", "x.yaml"):
                pass


class TestFilesStillWork:
    def test_two_disk_paths_unchanged_behavior(self, git_repo, capsys, tmp_path):
        # After git-ref support was added, the original two-disk-paths mode
        # must still work. Write v1 and v2 to tmp files and diff them.
        p1 = tmp_path / "a.yaml"
        p2 = tmp_path / "b.yaml"
        p1.write_text(V1_YAML)
        p2.write_text(V2_YAML)
        rc = main(["diff", str(p1), str(p2), "--json"])
        assert rc == 0
        payload = json.loads(capsys.readouterr().out)
        assert any(p["kind"] == "roles" for p in payload)
