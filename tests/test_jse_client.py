import unittest

from client import jse_client


class TestJSEClientHelpers(unittest.TestCase):
    def test_normalize_datetime_date(self) -> None:
        value = jse_client._normalize_datetime("2026-01-17")
        self.assertTrue(value.startswith("2026-01-17T00:00:00"))
        self.assertIn("+02:00", value)

    def test_normalize_consumption_response_timezone(self) -> None:
        response = {
            "data": {
                "productSeries": [
                    {
                        "typeId": "KWH Usage",
                        "data": [
                            {
                                "startTime": "2026-01-16T22:00:00.000Z",
                                "endTime": "2026-01-16T23:00:00.000Z",
                                "value": 1.23,
                                "type": "kWh",
                                "status": 150,
                            }
                        ],
                    }
                ]
            }
        }
        normalized = jse_client.normalize_consumption_response(response, "hour")
        self.assertEqual(normalized["granularity"], "hour")
        self.assertEqual(normalized["unit"], "kWh")
        self.assertEqual(len(normalized["series"]), 1)
        ts = normalized["series"][0]["ts"]
        self.assertTrue(ts.startswith("2026-01-17T00:00:00"))
        self.assertTrue(ts.endswith("+02:00"))


class TestJSEClientMeteringPoints(unittest.TestCase):
    def test_get_metering_point_ids(self) -> None:
        client = jse_client.JSEClient(email="a", password="b")
        client.get_customer_profile = lambda _: {
            "contracts": [
                {"meteringPoint": {"meteringPointId": "FI_JSE000_111"}},
                {"meteringPoint": {"meteringPointId": "FI_JSE000_222"}},
            ]
        }
        metering_points = client.get_metering_point_ids("jes_123")
        self.assertEqual(metering_points, ["FI_JSE000_111", "FI_JSE000_222"])


if __name__ == "__main__":
    unittest.main()
