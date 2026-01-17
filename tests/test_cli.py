import json
import os
import unittest
from contextlib import redirect_stdout
from io import StringIO
from unittest.mock import MagicMock, patch

import client.cli as cli


class TestCLI(unittest.TestCase):
    def test_login_test_command(self) -> None:
        fake_client = MagicMock()
        fake_client.login.return_value = MagicMock(expires_in=3600)
        fake_client.get_user_sub.return_value = "sub-123"

        with patch.object(cli, "JSEClient", return_value=fake_client):
            with patch.dict(os.environ, {"JSE_EMAIL": "a", "JSE_PASSWORD": "b"}):
                buf = StringIO()
                with redirect_stdout(buf):
                    code = cli.main(["login-test"])
        self.assertEqual(code, 0)
        payload = json.loads(buf.getvalue())
        self.assertEqual(payload["ok"], True)
        self.assertEqual(payload["sub"], "sub-123")

    def test_customers_command(self) -> None:
        fake_client = MagicMock()
        fake_client.get_user_sub.return_value = "sub-123"
        fake_client.get_customer_ids.return_value = ["jes_1"]
        fake_client.get_metering_point_ids.return_value = ["FI_JSE000_1"]

        with patch.object(cli, "JSEClient", return_value=fake_client):
            with patch.dict(os.environ, {"JSE_EMAIL": "a", "JSE_PASSWORD": "b"}):
                buf = StringIO()
                with redirect_stdout(buf):
                    code = cli.main(["customers"])
        self.assertEqual(code, 0)
        payload = json.loads(buf.getvalue())
        self.assertEqual(payload["customers"][0]["customer_id"], "jes_1")


if __name__ == "__main__":
    unittest.main()
