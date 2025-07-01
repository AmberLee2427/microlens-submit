import zipfile

from microlens_submit.api import load


def test_full_lifecycle(tmp_path):
    project = tmp_path / "proj"
    sub = load(str(project))
    sub.team_name = "Test Team"
    sub.tier = "test"

    evt = sub.get_event("test-event")
    sol1 = evt.add_solution(model_type="test", parameters={"a": 1})
    sol1.set_compute_info()
    sol2 = evt.add_solution(model_type="test", parameters={"b": 2})
    sub.save()

    new_sub = load(str(project))
    assert new_sub.team_name == "Test Team"
    assert "test-event" in new_sub.events
    new_evt = new_sub.events["test-event"]
    assert sol1.solution_id in new_evt.solutions
    assert sol2.solution_id in new_evt.solutions
    new_sol1 = new_evt.solutions[sol1.solution_id]
    assert "dependencies" in new_sol1.compute_info
    assert isinstance(new_sol1.compute_info["dependencies"], list)
    assert any("pytest" in dep for dep in new_sol1.compute_info["dependencies"])


def test_compute_info_hours(tmp_path):
    """CPU and wall time are persisted."""
    project = tmp_path / "proj"
    sub = load(str(project))
    evt = sub.get_event("evt")
    sol = evt.add_solution(model_type="test", parameters={})
    sol.set_compute_info(cpu_hours=1.5, wall_time_hours=2.0)
    sub.save()

    new_sub = load(str(project))
    new_sol = new_sub.get_event("evt").solutions[sol.solution_id]
    assert new_sol.compute_info["cpu_hours"] == 1.5
    assert new_sol.compute_info["wall_time_hours"] == 2.0


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
    assert solution_files == [
        f"events/test-event/solutions/{sol_active.solution_id}.json"
    ]


def test_get_active_solutions(tmp_path):
    project = tmp_path / "proj"
    sub = load(str(project))
    evt = sub.get_event("evt")
    sol1 = evt.add_solution("test", {"a": 1})
    sol2 = evt.add_solution("test", {"b": 2})
    sol2.deactivate()

    actives = evt.get_active_solutions()

    assert len(actives) == 1
    assert actives[0].solution_id == sol1.solution_id


def test_clear_solutions(tmp_path):
    project = tmp_path / "proj"
    sub = load(str(project))
    evt = sub.get_event("evt")
    sol1 = evt.add_solution("test", {"a": 1})
    sol2 = evt.add_solution("test", {"b": 2})

    evt.clear_solutions()
    sub.save()

    reloaded = load(str(project))
    evt2 = reloaded.get_event("evt")

    assert not evt2.solutions[sol1.solution_id].is_active
    assert not evt2.solutions[sol2.solution_id].is_active
    assert len(evt2.solutions) == 2


def test_posterior_path_persists(tmp_path):
    project = tmp_path / "proj"
    sub = load(str(project))
    evt = sub.get_event("event")
    sol = evt.add_solution("test", {"x": 1})
    sol.posterior_path = "posteriors/post.h5"
    sub.save()

    new_sub = load(str(project))
    new_sol = new_sub.events["event"].solutions[sol.solution_id]
    assert new_sol.posterior_path == "posteriors/post.h5"


def test_validate_warnings(tmp_path):
    project = tmp_path / "proj"
    sub = load(str(project))
    evt1 = sub.get_event("evt1")
    evt1.add_solution("test", {"a": 1})
    evt2 = sub.get_event("evt2")
    sol2 = evt2.add_solution("test", {"b": 2})
    sol2.deactivate()

    warnings = sub.validate()

    assert any("Hardware info" in w for w in warnings)
    assert any("evt2" in w for w in warnings)
    assert any("log_likelihood" in w for w in warnings)
