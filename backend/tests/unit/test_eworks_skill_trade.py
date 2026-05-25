"""Unit tests for skill → trade resolution in eWorks sessions."""

from __future__ import annotations

from app.schemas.eworks_link import WorkBlockSnapshot
from app.services.calculation_aggregate_service import group_works_by_skill
from app.services.eworks_link_service import collect_work_skills, skills_are_uniform, work_skill_name


def _block(skill: str | None = None) -> WorkBlockSnapshot:
    return WorkBlockSnapshot(scope="Test", skill_required=skill)


def test_work_skill_name_uses_block_or_fallback() -> None:
    assert work_skill_name(_block("Plumber"), "Carpenter") == "Plumber"
    assert work_skill_name(_block(None), "Carpenter") == "Carpenter"


def test_collect_work_skills_unique_in_order() -> None:
    works = [_block("Plumber"), _block("Carpenter"), _block("Plumber")]
    assert collect_work_skills(works, "Electrician") == ["Plumber", "Carpenter"]


def test_skills_are_uniform_true_for_same_skill() -> None:
    works = [_block("Plumber"), _block("Plumber")]
    assert skills_are_uniform(works, "Carpenter") is True


def test_skills_are_uniform_false_for_mixed() -> None:
    works = [_block("Plumber"), _block("Carpenter")]
    assert skills_are_uniform(works, "Carpenter") is False


def test_group_works_by_skill_preserves_first_seen_order() -> None:
    works = [_block("Carpenter"), _block("Plumber"), _block("Carpenter")]
    grouped = group_works_by_skill(works, "Electrician")
    assert [skill for skill, _blocks in grouped] == ["Carpenter", "Plumber"]
    assert len(grouped[0][1]) == 2
    assert len(grouped[1][1]) == 1
