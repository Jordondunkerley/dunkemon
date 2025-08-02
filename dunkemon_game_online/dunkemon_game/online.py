"""Utilities for optional online connectivity.

This module provides functions to save and load game state to a remote
endpoint.  The remote service is expected to expose REST endpoints for
reading and writing JSON data.  Environment variables control the
behaviour:

* `ONLINE_MODE` – set to "1" to enable online connectivity.  Any other
  value or missing defaults to offline mode.
* `REMOTE_BASE_URL` – the base URL of your remote storage API.  For
  example, a Supabase REST endpoint like ``https://your-project.supabase.co/rest/v1``.
* `REMOTE_API_KEY` – the API key or token required by the service.

When online mode is enabled and properly configured, the `save_game`
function sends a POST request with a JSON payload to
``{REMOTE_BASE_URL}/dunkemon_saves``.  Similarly, `load_game` retrieves
the latest save via a GET request to the same endpoint.  Adjust these
URLs to match your own backend.

If any network error occurs or the configuration is incomplete, both
functions raise an exception and the caller should fall back to local
storage.
"""

import json
import os
import urllib.request
import urllib.error


def is_online_mode() -> bool:
    return os.environ.get('ONLINE_MODE', '0') == '1'


def get_remote_config():
    base_url = os.environ.get('REMOTE_BASE_URL')
    api_key = os.environ.get('REMOTE_API_KEY')
    if not base_url or not api_key:
        raise RuntimeError('Remote configuration missing (REMOTE_BASE_URL or REMOTE_API_KEY)')
    return base_url.rstrip('/'), api_key


def save_game(data: dict):
    """Send the save data to the remote API.

    Raises an exception on failure.
    """
    base_url, api_key = get_remote_config()
    url = f"{base_url}/dunkemon_saves"
    body = json.dumps(data).encode('utf-8')
    req = urllib.request.Request(url, data=body, method='POST', headers={
        'Content-Type': 'application/json',
        'apikey': api_key
    })
    with urllib.request.urlopen(req) as resp:
        if resp.status not in (200, 201):
            raise RuntimeError(f"Failed to save remotely: HTTP {resp.status}")


def load_game() -> dict:
    """Retrieve the latest save data from the remote API.

    Returns the JSON payload as a dict.  Raises an exception on
    failure.
    """
    base_url, api_key = get_remote_config()
    url = f"{base_url}/dunkemon_saves?limit=1&order=inserted_at.desc"
    req = urllib.request.Request(url, headers={'apikey': api_key})
    with urllib.request.urlopen(req) as resp:
        if resp.status != 200:
            raise RuntimeError(f"Failed to load remotely: HTTP {resp.status}")
        data = json.loads(resp.read().decode('utf-8'))
        if not data:
            raise RuntimeError('No remote saves found')
        return data[0]