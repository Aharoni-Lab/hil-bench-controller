"""Tests for SupabasePublisher client."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from hilbench.config import BenchConfig
from hilbench.publisher._client import SupabasePublisher
from hilbench.publisher._config import PublisherConfig
from tests.conftest import SAMPLE_CONFIG


@pytest.fixture()
def pub_config() -> PublisherConfig:
    return PublisherConfig(
        supabase_url="https://test.supabase.co",
        supabase_key="test-key",
        bench_email="bench@test.com",
        bench_password="pass123",
    )


@pytest.fixture()
def bench_config() -> BenchConfig:
    return BenchConfig.model_validate(SAMPLE_CONFIG)


@pytest.fixture()
def mock_supabase() -> Any:
    with patch("supabase.create_client") as mock_create:
        mock_client = MagicMock()
        mock_create.return_value = mock_client
        # Auth sign-in returns a session
        mock_client.auth.sign_in_with_password.return_value = MagicMock()
        # Table upsert/insert chain
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table
        mock_table.upsert.return_value = mock_table
        mock_table.insert.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data=[{"id": "test-uuid-1234"}])
        yield mock_client


class TestSupabasePublisher:
    def test_publish_status_success(
        self, pub_config: PublisherConfig, bench_config: BenchConfig, mock_supabase: Any
    ) -> None:
        publisher = SupabasePublisher(pub_config, bench_config)
        publisher.publish_status(state="idle", healthy=True)
        # Should have called table for benches (registration) and bench_status_current
        assert mock_supabase.table.call_count >= 2

    def test_supabase_unavailable_no_exception(
        self, pub_config: PublisherConfig, bench_config: BenchConfig
    ) -> None:
        """Publisher should not raise if Supabase is unreachable."""
        with patch(
            "supabase.create_client",
            side_effect=Exception("connection refused"),
        ):
            publisher = SupabasePublisher(pub_config, bench_config)
            # Should not raise
            publisher.publish_status(state="idle", healthy=True)

    def test_event_gating(
        self, pub_config: PublisherConfig, bench_config: BenchConfig, mock_supabase: Any
    ) -> None:
        """Events should not be published when publish_events is False."""
        assert pub_config.publish_events is False
        publisher = SupabasePublisher(pub_config, bench_config)
        publisher.publish_event("test_event", {"key": "value"})
        # table should not be called for events (only possibly for registration)
        for call in mock_supabase.table.call_args_list:
            assert call[0][0] != "bench_events"

    def test_events_published_when_enabled(
        self, pub_config: PublisherConfig, bench_config: BenchConfig, mock_supabase: Any
    ) -> None:
        """Events should be published when publish_events is True."""
        pub_config.publish_events = True
        publisher = SupabasePublisher(pub_config, bench_config)
        publisher.publish_event("test_event", {"key": "value"})
        table_names = [call[0][0] for call in mock_supabase.table.call_args_list]
        assert "bench_events" in table_names

    def test_bench_registration_upsert(
        self, pub_config: PublisherConfig, bench_config: BenchConfig, mock_supabase: Any
    ) -> None:
        publisher = SupabasePublisher(pub_config, bench_config)
        publisher.publish_status(state="idle", healthy=True)
        # First table call should be benches upsert
        first_table_call = mock_supabase.table.call_args_list[0]
        assert first_table_call[0][0] == "benches"

    def test_close_signs_out(
        self, pub_config: PublisherConfig, bench_config: BenchConfig, mock_supabase: Any
    ) -> None:
        publisher = SupabasePublisher(pub_config, bench_config)
        # Force client creation
        publisher.publish_status(state="idle", healthy=True)
        publisher.close()
        mock_supabase.auth.sign_out.assert_called_once()
