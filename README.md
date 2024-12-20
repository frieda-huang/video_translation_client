# Video Translation Status Client Library

This project simulates a video translation backend by providing a **Status API server** and a **client library** for interacting with it. The server API delivers job status updates (e.g., `pending`, `completed`, or `error`), while the client library simplifies and optimizes fetching these updates.

---

## Features

### Server

-   **Endpoint:** `GET /status`
    -   **pending:** Returned until a configurable elapsed time has passed.
    -   **completed:** Indicates the job is finished.
    -   **error:** Simulates an error condition.
-   Configurable completion time for the `pending` status.

### Client Library

-   **Status Polling**:
    -   Exponential backoff to optimize API usage and reduce server load.
    -   Retry mechanism for handling transient errors.
    -   Configurable timeouts for responsiveness.
    -   Callback functionality for handling dynamic status updates.

---

## Setup

1. Clone the Repository

```shell
git clone https://github.com/your-username/video_translation_client.git
cd video_translation_client
```

2. Install Dependencies

```shell
uv sync
```

## Usage

### Quick Start

```python
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
        base_url=f"http://localhost:{PORT}",
        config=config,
        on_status_change=status_changed
    )

    try:
        final_status = await client.poll_until_complete()
        print(f"Final status: {final_status.status.value}")
        print(f"Total time: {final_status.elapsed_time:.6f}s")
    except TimeoutError as e:
        print(f"Polling timed out: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(main())
```

### Step-by-Step Instructions

1. Import and Initialize the Client

```python
from video_translation_client import VideoTranslationClient, StatusPollingConfig

config = StatusPollingConfig(
    initial_delay=1.0,      # Delay before the first retry (seconds)
    max_delay=8.0,          # Maximum delay between retries (seconds)
    backoff_factor=2.0,     # Exponential backoff factor
    timeout=30.0            # Timeout for the entire polling session
)

client = VideoTranslationClient(
    base_url="http://localhost:8000",
    config=config,
    on_status_change=lambda status: print(f"Status changed: {status}")
)
```

2. Poll the Server for Job Status

```python
try:
    result = await client.poll_until_complete()
    print(f"Final result: {result.status}")
except TimeoutError:
    print("Job did not complete within the configured timeout.")
```

### Testing

Run tests using `pytest`

### Tech Stack

-   Python
-   [uv](https://docs.astral.sh/uv/)
-   pytest
