import json
import logging
import unittest

from fastapi.testclient import TestClient

from main import app
from utils.logger import JsonFormatter, get_request_id, reset_request_id, set_request_id


class RequestContextTest(unittest.TestCase):
    def test_request_id_is_included_in_structured_logs(self):
        token = set_request_id("request-123")
        try:
            record = logging.LogRecord("tripcraft", logging.INFO, "", 0, "hello", (), None)
            payload = json.loads(JsonFormatter().format(record))
            self.assertEqual(payload["request_id"], "request-123")
            self.assertEqual(get_request_id(), "request-123")
        finally:
            reset_request_id(token)

    def test_api_echoes_or_creates_request_id_header(self):
        client = TestClient(app)

        supplied = client.get("/", headers={"X-Request-ID": "client-request"})
        generated = client.get("/")

        self.assertEqual(supplied.headers["X-Request-ID"], "client-request")
        self.assertTrue(generated.headers["X-Request-ID"])


if __name__ == "__main__":
    unittest.main()
