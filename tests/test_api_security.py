import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from superturiya.api import build_server


class ApiSecurityTest(unittest.TestCase):
    def _start(self, **kwargs):
        tmp = tempfile.TemporaryDirectory()
        server = build_server(
            host="127.0.0.1",
            port=0,
            db_path=str(Path(tmp.name) / "api.db"),
            seed=False,
            **kwargs,
        )
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = "http://127.0.0.1:%d" % server.server_address[1]
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        return tmp, server, thread, base, opener

    def _stop(self, tmp, server, thread):
        server.shutdown()
        thread.join(timeout=2)
        server.RequestHandlerClass.engine.store.close()
        server.server_close()
        tmp.cleanup()

    def test_security_headers_and_no_wildcard_cors(self):
        args = self._start()
        tmp, server, thread, base, opener = args
        try:
            with opener.open(base + "/health", timeout=2) as response:
                self.assertEqual(response.headers["x-content-type-options"], "nosniff")
                self.assertIn("frame-ancestors 'none'", response.headers["content-security-policy"])
                self.assertIsNone(response.headers["access-control-allow-origin"])
        finally:
            self._stop(tmp, server, thread)

    def test_token_auth_scope_override_and_body_limit(self):
        args = self._start(
            api_token="secret",
            principal_id="principal-1",
            tenant_id="bound-tenant",
            max_body_bytes=256,
        )
        tmp, server, thread, base, opener = args
        try:
            unauthorized = urllib.request.Request(
                base + "/memories/search",
                data=b"{}",
                headers={"content-type": "application/json"},
                method="POST",
            )
            with self.assertRaises(urllib.error.HTTPError) as denied:
                opener.open(unauthorized, timeout=2)
            self.assertEqual(denied.exception.code, 401)

            oversized = urllib.request.Request(
                base + "/memories/search",
                data=json.dumps({"padding": "x" * 500}).encode(),
                headers={
                    "content-type": "application/json",
                    "authorization": "Bearer secret",
                },
                method="POST",
            )
            with self.assertRaises(urllib.error.HTTPError) as too_large:
                opener.open(oversized, timeout=2)
            self.assertEqual(too_large.exception.code, 413)

            server.RequestHandlerClass.engine.ingest_evidence(
                {
                    "tenant_id": "other-tenant",
                    "subject_id": "s1",
                    "record_id": "other-record",
                    "record": {"content": "tenant-private"},
                }
            )
            cross_tenant = urllib.request.Request(
                base + "/evidence/records/other-record",
                headers={"authorization": "Bearer secret"},
            )
            with self.assertRaises(urllib.error.HTTPError) as forbidden:
                opener.open(cross_tenant, timeout=2)
            self.assertEqual(forbidden.exception.code, 403)
        finally:
            self._stop(tmp, server, thread)

    def test_dual_record_api_keeps_raw_on_separate_attachment_path(self):
        args = self._start()
        tmp, server, thread, base, opener = args
        try:
            request = urllib.request.Request(
                base + "/evidence/records",
                data=json.dumps(
                    {
                        "tenant_id": "t1",
                        "subject_id": "s1",
                        "record_id": "record-api",
                        "record": {"content": "<script>alert(1)</script>"},
                    }
                ).encode(),
                headers={"content-type": "application/json"},
                method="POST",
            )
            with opener.open(request, timeout=2) as response:
                created = json.load(response)
            self.assertTrue(created["integrity"]["verified"])
            self.assertNotIn("raw_payload", created)

            with opener.open(base + "/evidence/records/record-api", timeout=2) as response:
                projection = json.load(response)
            self.assertNotIn("raw_payload", projection)

            with opener.open(
                base + "/evidence/records/record-api/raw", timeout=2
            ) as response:
                raw = json.load(response)
                self.assertIn("attachment", response.headers["content-disposition"])
            self.assertEqual(raw["raw_payload"]["content"], "<script>alert(1)</script>")
        finally:
            self._stop(tmp, server, thread)


if __name__ == "__main__":
    unittest.main()
