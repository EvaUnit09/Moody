"""
Unit tests for per-stage pipeline timing.
"""

import pytest

from app.services.timing import StageTimer


class TestStageTimer:
    def test_records_each_stage_in_order(self):
        timer = StageTimer()

        with timer.stage("expand"):
            pass
        with timer.stage("rerank"):
            pass

        assert list(timer.durations) == ["expand", "rerank"]
        assert all(ms >= 0 for ms in timer.durations.values())

    def test_records_stage_even_when_block_raises(self):
        timer = StageTimer()

        with pytest.raises(RuntimeError):
            with timer.stage("embed"):
                raise RuntimeError("provider down")

        assert "embed" in timer.durations

    def test_durations_returns_copy(self):
        timer = StageTimer()
        with timer.stage("search"):
            pass

        snapshot = timer.durations
        snapshot["search"] = -1

        assert timer.durations["search"] >= 0

    def test_server_timing_header_format(self):
        timer = StageTimer()
        with timer.stage("expand"):
            pass

        header = timer.server_timing_header()

        assert header.startswith("expand;dur=")
        assert header.split(", ")[-1].startswith("total;dur=")

    def test_log_line_includes_stages_and_total(self):
        timer = StageTimer()
        with timer.stage("providers"):
            pass

        line = timer.log_line()

        assert "providers=" in line
        assert "total=" in line
