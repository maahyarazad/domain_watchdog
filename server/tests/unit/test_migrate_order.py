from pathlib import Path

from app.migrate import pending_migrations


def test_sorted_and_applied_skipped():
    files = [Path("002_b.sql"), Path("001_a.sql"), Path("003_c.sql")]
    assert [f.stem for f in pending_migrations(files, {"001_a"})] == ["002_b", "003_c"]
