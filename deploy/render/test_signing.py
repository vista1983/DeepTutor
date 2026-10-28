import hashlib
import time
import unittest

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

from deploy.render.mcp_bridge import valid_plugin_signature


class PluginSignatureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        cls.public = cls.key.public_key().public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
        cls.body = b'{"method":"tools/list"}'

    def token(self, **changes):
        now = int(time.time())
        claims = dict(iss="deeptutor-private-plugin", aud="deeptutor-shanghai",
                      sub="owner", iat=now, exp=now+60,
                      request_sha256=hashlib.sha256(self.body).hexdigest())
        claims.update(changes)
        return jwt.encode(claims, self.key, algorithm="RS256")

    def test_valid_request(self):
        self.assertTrue(valid_plugin_signature(self.token(), self.body, self.public))

    def test_modified_body(self):
        self.assertFalse(valid_plugin_signature(self.token(), b'{}', self.public))

    def test_invalid_claims(self):
        now = int(time.time())
        for change in [dict(iss="other"), dict(aud="other"), dict(sub=""),
                       dict(exp=now-60, iat=now-120), dict(exp=now+600)]:
            with self.subTest(change=change):
                self.assertFalse(valid_plugin_signature(self.token(**change), self.body, self.public))

    def test_wrong_signing_key_and_algorithm(self):
        other = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        public = other.public_key().public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
        self.assertFalse(valid_plugin_signature(self.token(), self.body, public))
        self.assertFalse(valid_plugin_signature(jwt.encode({"sub":"owner"}, "dummy-test-secret-only-32-characters", algorithm="HS256"), self.body, self.public))


if __name__ == "__main__":
    unittest.main()
