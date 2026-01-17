import os
import unittest

from client.jse_client import JSEClient, normalize_consumption_response


class TestLiveIntegration(unittest.TestCase):
    @unittest.skipUnless(
        os.getenv("JSE_EMAIL") and os.getenv("JSE_PASSWORD"),
        "Set JSE_EMAIL and JSE_PASSWORD to run live tests",
    )
    def test_login_and_consumption(self) -> None:
        client = JSEClient(
            email=os.environ["JSE_EMAIL"],
            password=os.environ["JSE_PASSWORD"],
        )
        sub = client.get_user_sub()
        self.assertTrue(sub)

        customer_ids = client.get_customer_ids(sub)
        self.assertTrue(customer_ids)

        customer_id = customer_ids[0]
        metering_points = client.get_metering_point_ids(customer_id)
        self.assertTrue(metering_points)

        end = "2026-01-17"
        start = "2026-01-16"
        raw = client.get_consumption(
            customer_id=customer_id,
            metering_point_id=metering_points[0],
            start=start,
            end=end,
            resolution="hour",
        )
        normalized = normalize_consumption_response(raw, "hour")
        self.assertEqual(normalized["granularity"], "hour")
        self.assertTrue(normalized["series"])


if __name__ == "__main__":
    unittest.main()
