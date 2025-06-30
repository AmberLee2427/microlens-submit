import zipfile
from pathlib import Path
import pytest

from microlens_submit.api import load


def test_full_lifecycle(tmp_path):
    project = tmp_path / "proj"
    sub = load(str(project))
    sub.team_name = "Test Team"
    sub.tier = "test"

    evt = sub.get_event("test-event")
    sol1 = evt.add_solution(model_type="test", parameters={"a": 1})
    sol2 = evt.add_solution(model_type="test", parameters={"b": 2})
    sub.save()

    new_sub = load(str(project))
    assert new_sub.team_name == "Test Team"
    assert "test-event" in new_sub.events
    new_evt = new_sub.events["test-event"]
    assert sol1.solution_id in new_evt.solutions
    assert sol2.solution_id in new_evt.solutions


def test_deactivate_and_export(tmp_path):
    project = tmp_path / "proj"
    sub = load(str(project))
    evt = sub.get_event("test-event")
    sol_active = evt.add_solution("test", {"a": 1})
    sol_inactive = evt.add_solution("test", {"b": 2})
    sol_inactive.deactivate()
    sub.save()

    zip_path = project / "submission.zip"
    sub.export(str(zip_path))

    assert zip_path.exists()
    with zipfile.ZipFile(zip_path) as zf:
        solution_files = [
            n for n in zf.namelist() if n.startswith("events/") and "solutions" in n
        ]
    assert solution_files == [f"events/test-event/solutions/{sol_active.solution_id}.json"]
