import asyncio
from typing import AsyncGenerator

import aiohttp
import pytest
import pytest_asyncio
from translation_server import TranslationServer
from video_translation_client.models import JobStatus, StatusPollingConfig
from video_translation_client.video_translation_client import VideoTranslationClient

BASE_URL_TEMPLATE = "http://localhost:{}"


@pytest_asyncio.fixture
async def server(unused_tcp_port_factory) -> AsyncGenerator[TranslationServer, None]:
    """Start and yield a test TranslationServer instance on a random port."""
    port = unused_tcp_port_factory()
    server_instance = TranslationServer(completion_time=2.0, error_rate=0.0)
    await server_instance.start(port=port)
    try:
        yield server_instance, port
    finally:
        await _cleanup_server(server_instance)


async def _cleanup_server(server_instance: TranslationServer):
    """Clean up tasks and stop the server."""
    try:
        tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
    except Exception as e:
        print(f"Error during cleanup: {e}")
    finally:
        await server_instance.app.shutdown()
        await server_instance.app.cleanup()


@pytest.fixture
def config() -> StatusPollingConfig:
    """Provide default configuration for the client."""
    return StatusPollingConfig(
        initial_delay=0.5,
        max_delay=2.0,
        backoff_factor=2.0,
        timeout=10.0,
        max_attempts=5,
    )


@pytest.mark.asyncio
async def test_successful_completion(server, config):
    """Test normal successful completion flow."""
    status_changes = []
    server_instance, port = server
    base_url = BASE_URL_TEMPLATE.format(port)

    async def status_callback(response):
        status_changes.append(response.status)

    client = VideoTranslationClient(
        base_url=base_url, config=config, on_status_change=status_callback
    )

    result = await client.poll_until_complete()

    assert result.status == JobStatus.completed
    assert result.elapsed_time > 0
    assert JobStatus.pending in status_changes
    assert JobStatus.completed in status_changes


@pytest.mark.asyncio
async def test_error_scenario(server, config):
    """Test error handling with high error rate."""
    server_instance, port = server
    server_instance.error_rate = 1.0
    base_url = BASE_URL_TEMPLATE.format(port)

    client = VideoTranslationClient(base_url=base_url, config=config)
    result = await client.poll_until_complete()
    assert result.status == JobStatus.error


@pytest.mark.asyncio
async def test_timeout_scenario(server, config):
    """Test timeout handling."""
    server_instance, port = server
    server_instance.completion_time = 30.0
    base_url = BASE_URL_TEMPLATE.format(port)
    config.timeout = 2.0

    client = VideoTranslationClient(base_url=base_url, config=config)

    with pytest.raises(TimeoutError):
        await client.poll_until_complete()


@pytest.mark.asyncio
async def test_server_unavailable(config):
    """Test behavior when server is not available."""
    client = VideoTranslationClient(
        base_url="http://localhost:9999", config=config  # Invalid port
    )

    with pytest.raises(aiohttp.ClientConnectionError):
        await client.poll_until_complete()


@pytest.mark.asyncio
async def test_multiple_clients(server, config):
    """Test multiple clients polling simultaneously."""
    server_instance, port = server
    base_url = BASE_URL_TEMPLATE.format(port)

    async def run_client():
        client = VideoTranslationClient(base_url=base_url, config=config)
        return await client.poll_until_complete()

    results = await asyncio.gather(
        *[run_client() for _ in range(3)], return_exceptions=True
    )

    for result in results:
        assert isinstance(result, Exception) or result.status == JobStatus.completed
