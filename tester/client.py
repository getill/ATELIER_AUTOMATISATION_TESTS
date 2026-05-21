import time
import requests
from requests.exceptions import RequestException

class ChicagoArtInstituteClient:
    """
    Robust HTTP Client for the Art Institute of Chicago API.
    Handles rate-limiting (429), server errors (5xx), strict timeouts (3s), 
    and captures exact request latency in milliseconds.
    """
    BASE_URL = "https://api.artic.edu/api/v1"

    def __init__(self, timeout=3.0):
        self.timeout = timeout

    def request(self, method, endpoint, params=None, json_data=None):
        """
        Executes an HTTP request with automatic retry logic (max 1 retry) and timeout.
        Measures latency and returns a structured dictionary detailing the outcome.
        """
        url = f"{self.BASE_URL}{endpoint}" if endpoint.startswith("/") else f"{self.BASE_URL}/{endpoint}"
        
        attempts = 2
        last_error = None
        response = None
        latency_ms = 0.0
        
        for attempt in range(attempts):
            start_time = time.perf_counter()
            try:
                response = requests.request(
                    method=method,
                    url=url,
                    params=params,
                    json=json_data,
                    timeout=self.timeout
                )
                latency_ms = (time.perf_counter() - start_time) * 1000.0
                
                # If we hit rate limits (429) or temporary server errors (5xx), retry once after a backoff
                if response.status_code == 429 and attempt == 0:
                    time.sleep(1.0)  # Rate limit cooldown backoff
                    continue
                elif 500 <= response.status_code < 600 and attempt == 0:
                    time.sleep(0.5)  # Server error cooldown
                    continue
                
                # Success or standard client errors (e.g. 404) do not trigger retry
                break
            except RequestException as e:
                latency_ms = (time.perf_counter() - start_time) * 1000.0
                last_error = str(e)
                if attempt == 0:
                    time.sleep(0.5)  # Connection error backoff
                    continue
                break
        
        if response is not None:
            # Check content-type header
            content_type = response.headers.get("Content-Type", "")
            is_json = "application/json" in content_type
            
            parsed_json = None
            if is_json:
                try:
                    parsed_json = response.json()
                except Exception as je:
                    last_error = f"Failed to parse JSON: {str(je)}"
            
            return {
                "status_code": response.status_code,
                "json": parsed_json,
                "headers": dict(response.headers),
                "latency_ms": latency_ms,
                "success": response.status_code < 400 and last_error is None,
                "error": last_error
            }
        else:
            return {
                "status_code": None,
                "json": None,
                "headers": {},
                "latency_ms": latency_ms,
                "success": False,
                "error": last_error or "Network request failed"
            }

    def get(self, endpoint, params=None):
        return self.request("GET", endpoint, params=params)
