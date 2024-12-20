import asyncio

from translation_server import TranslationServer
from video_translation_client.models import StatusPollingConfig
from video_translation_client.video_translation_client import VideoTranslationClient


async def status_changed(status_response):
    print(f"Status changed to: {status_response.status.value}")
    print(f"Elapsed time: {status_response.elapsed_time:.6f}s")


async def main():
    PORT = 8000
    server = TranslationServer(completion_time=20.0, error_rate=0.1)
    await server.start(port=PORT)
    print(f"Server started on http://localhost:{PORT}")

    config = StatusPollingConfig(
        initial_delay=1.0, max_delay=8.0, backoff_factor=3.0, timeout=60.0
    )

    client = VideoTranslationClient(
        f"http://localhost:{PORT}", config, on_status_change=status_changed
    )

    try:
        final_status = await client.poll_until_complete()
        print(f"Final status: {final_status.status.value}")
        print(f"Total time: {final_status.elapsed_time:.6f}s")
    except TimeoutError as e:
        print(f"Polling timed out: {e}")
    except Exception as e:
        print(f"Error occurred: {e}")

    await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())
