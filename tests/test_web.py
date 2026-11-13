"""Pruebas del servidor local: CSP, validación de origen y extracción multipart."""

from __future__ import annotations

import http.client
import json
import re
import sys
import threading
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from extractor.config import MAX_REQUEST_SIZE
from extractor.web import LocalServer, RequestHandler


def multipart_body(filename: str, content: bytes, boundary: str = "----prueba") -> tuple[bytes, str]:
    """Construye un cuerpo multipart mínimo con un único archivo."""
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        "Content-Type: text/plain\r\n\r\n"
    ).encode() + content + f"\r\n--{boundary}--\r\n".encode()
    return body, f"multipart/form-data; boundary={boundary}"


class WebTest(unittest.TestCase):
    """Verifica las defensas del servidor y el flujo de extracción."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.server = LocalServer(("127.0.0.1", 0), RequestHandler)
        cls.port = cls.server.server_address[1]
        cls.host = f"127.0.0.1:{cls.port}"
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)

    def request(self, method: str, path: str, headers: dict[str, str] | None = None,
                body: bytes | None = None) -> tuple[int, dict[str, str], bytes]:
        """Ejecuta una petición contra el servidor de pruebas."""
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        conn.request(method, path, body=body, headers=headers or {"Host": self.host})
        response = conn.getresponse()
        data = response.read()
        result = (response.status, dict(response.getheaders()), data)
        conn.close()
        return result

    def test_pagina_con_nonce_y_cabeceras(self) -> None:
        status, headers, body = self.request("GET", "/")
        html = body.decode("utf-8")
        csp = headers["Content-Security-Policy"]
        nonce = re.search(r"script-src 'nonce-([^']+)'", csp)
        self.assertEqual(status, 200)
        self.assertIsNotNone(nonce)
        self.assertIn(f'nonce="{nonce.group(1)}"', html)
        self.assertNotIn("unsafe-inline", csp)
        self.assertEqual(headers["X-Frame-Options"], "DENY")
        self.assertNotIn("onclick=", html)
        self.assertNotIn('style="', html)

    def test_host_ajeno_rechazado(self) -> None:
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        conn.putrequest("GET", "/", skip_host=True)
        conn.putheader("Host", "evil.example")
        conn.endheaders()
        response = conn.getresponse()
        response.read()
        conn.close()
        self.assertEqual(response.status, 403)

    def test_origen_ajeno_rechazado(self) -> None:
        body, ctype = multipart_body("nota.txt", b"uno\n")
        status, _, _ = self.request(
            "POST",
            "/api/extract",
            {"Host": self.host, "Content-Type": ctype, "Origin": "http://evil.example"},
            body,
        )
        self.assertEqual(status, 403)

    def test_extraccion_multipart(self) -> None:
        body, ctype = multipart_body("nota.txt", b"Linea uno\nLinea dos\n")
        status, _, raw = self.request(
            "POST",
            "/api/extract",
            {"Host": self.host, "Content-Type": ctype, "Origin": f"http://{self.host}"},
            body,
        )
        data = json.loads(raw)
        self.assertEqual(status, 200)
        self.assertEqual(data["filesystem"]["name"], "nota.txt")
        self.assertEqual(data["document"]["words"], 4)

    def test_content_type_invalido(self) -> None:
        status, _, _ = self.request(
            "POST",
            "/api/extract",
            {"Host": self.host, "Content-Type": "application/json"},
            b"{}",
        )
        self.assertEqual(status, 415)

    def test_cuerpo_demasiado_grande(self) -> None:
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        conn.putrequest("POST", "/api/extract")
        conn.putheader("Host", self.host)
        conn.putheader("Content-Type", "multipart/form-data; boundary=x")
        conn.putheader("Content-Length", str(MAX_REQUEST_SIZE + 1))
        conn.endheaders()
        response = conn.getresponse()
        response.read()
        conn.close()
        self.assertEqual(response.status, 413)


if __name__ == "__main__":
    unittest.main()
