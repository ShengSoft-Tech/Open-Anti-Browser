import unittest
from unittest.mock import patch

from backend.services.network import resolve_geo_profile


class FakeResponse:
    def __init__(self, payload=None, text=""):
        self.payload = payload
        self.text = text
        self.status_code = 200

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.urls = []
        self.closed = False

    def get(self, url, **kwargs):
        self.urls.append(url)
        if not self.responses:
            raise AssertionError(f"unexpected GET {url}")
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    def close(self):
        self.closed = True


class GeoResolutionTests(unittest.TestCase):
    def test_resolve_geo_profile_uses_ip_api_when_browserscan_fails(self):
        session = FakeSession(
            RuntimeError("browserscan timeout"),
            FakeResponse(text="47.159.212.24\n"),
            FakeResponse(
                {
                    "status": "success",
                    "query": "47.159.212.24",
                    "countryCode": "US",
                    "timezone": "America/Los_Angeles",
                    "lat": 34.05,
                    "lon": -118.24,
                    "regionName": "California",
                    "city": "Los Angeles",
                    "isp": "Proxy ISP",
                    "zip": "90001",
                }
            ),
        )

        with patch("backend.services.network.create_http_session", return_value=session):
            profile = resolve_geo_profile({"request_proxy": "http://proxy.local:3000"}, True, strict=False)

        self.assertEqual(profile["ip"], "47.159.212.24")
        self.assertEqual(profile["timezone"], "America/Los_Angeles")
        self.assertEqual(profile["country_code"], "US")
        self.assertEqual(profile["source"], "ip-api")
        self.assertIn("ipv4.icanhazip.com", session.urls[1])
        self.assertIn("ip-api.com/json/", session.urls[-1])
        self.assertTrue(session.closed)

    def test_resolve_geo_profile_replaces_generic_utc_timezone_with_ip_api_timezone(self):
        session = FakeSession(
            FakeResponse(
                {
                    "code": 0,
                    "data": {
                        "ip": "47.159.212.24",
                        "ip_data": {
                            "country": "US",
                            "timezone": "utc",
                            "region": "California",
                            "city": "Los Angeles",
                            "latitude": 34.05,
                            "longitude": -118.24,
                            "isp": "Proxy ISP",
                            "ip_scan_channel": "ip2location",
                        },
                    },
                }
            ),
            FakeResponse(
                {
                    "status": "success",
                    "query": "47.159.212.24",
                    "countryCode": "US",
                    "timezone": "America/Los_Angeles",
                    "lat": 34.05,
                    "lon": -118.24,
                    "regionName": "California",
                    "city": "Los Angeles",
                    "isp": "Proxy ISP",
                    "zip": "90001",
                }
            ),
        )

        with patch("backend.services.network.create_http_session", return_value=session):
            profile = resolve_geo_profile({"request_proxy": "http://proxy.local:3000"}, True, strict=False)

        self.assertEqual(profile["timezone"], "America/Los_Angeles")
        self.assertNotEqual(profile["timezone"].lower(), "utc")
        self.assertEqual(profile["source"], "ip-api")


if __name__ == "__main__":
    unittest.main()
