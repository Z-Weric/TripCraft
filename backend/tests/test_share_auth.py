import unittest
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import Mock, patch

from fastapi import HTTPException

from services.share_service import can_read_trip, hash_share_token, is_share_token_active, is_trip_owner


class ShareAccessPolicyTest(unittest.TestCase):
    def setUp(self):
        self.trip = SimpleNamespace(id=10, user_id=1, is_public=0)
        self.owner = {"user_id": 1}
        self.other_user = {"user_id": 2}
        self.active_token = SimpleNamespace(
            trip_id=10,
            revoked_at=None,
            expires_at=datetime.utcnow() + timedelta(hours=1),
        )

    def test_guest_cannot_read_private_trip_without_token(self):
        self.assertFalse(can_read_trip(self.trip))

    def test_non_owner_cannot_read_private_trip(self):
        self.assertFalse(can_read_trip(self.trip, user=self.other_user))

    def test_owner_can_read_private_trip(self):
        self.assertTrue(is_trip_owner(self.trip, self.owner))
        self.assertTrue(can_read_trip(self.trip, user=self.owner))

    def test_public_trip_is_readable_by_guest(self):
        self.trip.is_public = 1
        self.assertTrue(can_read_trip(self.trip))

    def test_active_token_can_read_matching_private_trip(self):
        self.assertTrue(can_read_trip(self.trip, share_token=self.active_token))

    def test_expired_or_revoked_token_cannot_read_trip(self):
        self.active_token.expires_at = datetime.utcnow() - timedelta(seconds=1)
        self.assertFalse(is_share_token_active(self.active_token))
        self.assertFalse(can_read_trip(self.trip, share_token=self.active_token))

        self.active_token.expires_at = datetime.utcnow() + timedelta(hours=1)
        self.active_token.revoked_at = datetime.utcnow()
        self.assertFalse(is_share_token_active(self.active_token))

    def test_token_hash_is_deterministic_and_does_not_expose_token(self):
        raw_token = "secret-share-token"
        token_hash = hash_share_token(raw_token)
        self.assertEqual(token_hash, hash_share_token(raw_token))
        self.assertEqual(len(token_hash), 64)
        self.assertNotIn(raw_token, token_hash)


class ShareApiPermissionTest(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        import sys

        class FakeShareToken:
            token_hash = None

            def __init__(self, **kwargs):
                for key, value in kwargs.items():
                    setattr(self, key, value)

        class FakeSavedTrip:
            id = None

        database_models = SimpleNamespace(
            ShareToken=FakeShareToken,
            SavedTrip=FakeSavedTrip,
            get_db=lambda: None,
        )
        async def fake_get_current_user(_authorization=None):
            return None

        def fake_require_user():
            return {"user_id": 1}

        auth_module = SimpleNamespace(
            get_current_user=fake_get_current_user,
            require_user=fake_require_user,
        )
        cls.module_patches = [
            patch.dict(sys.modules, {
                "database.models": database_models,
                "utils.auth": auth_module,
            }),
        ]
        for module_patch in cls.module_patches:
            module_patch.start()

        from api import share

        cls.share = share

    @classmethod
    def tearDownClass(cls):
        for module_patch in reversed(cls.module_patches):
            module_patch.stop()

    async def test_non_owner_cannot_create_share_link(self):
        trip = SimpleNamespace(id=10, user_id=1, is_public=0)
        with patch.object(self.share, "_get_trip_or_404", return_value=trip):
            with self.assertRaises(HTTPException) as raised:
                await self.share.create_share_link(10, Mock(), {"user_id": 2})
        self.assertEqual(raised.exception.status_code, 403)

    async def test_owner_can_create_persistent_share_link(self):
        trip = SimpleNamespace(id=10, user_id=1, is_public=0)
        db = Mock()
        with patch.object(self.share, "_get_trip_or_404", return_value=trip):
            response = await self.share.create_share_link(10, db, {"user_id": 1})

        self.assertTrue(response.url.startswith("/detail/"))
        self.assertEqual(len(response.token), 43)
        db.add.assert_called_once()
        db.commit.assert_called_once()

    async def test_invalid_share_token_returns_not_found(self):
        with patch.object(self.share, "_get_token_record", return_value=None):
            with self.assertRaises(HTTPException) as raised:
                await self.share.get_shared_trip("missing", Mock())
        self.assertEqual(raised.exception.status_code, 404)

    async def test_expired_share_token_returns_gone(self):
        token = SimpleNamespace(
            trip_id=10,
            revoked_at=None,
            expires_at=datetime.utcnow() - timedelta(seconds=1),
        )
        with patch.object(self.share, "_get_token_record", return_value=token):
            with self.assertRaises(HTTPException) as raised:
                await self.share.get_shared_trip("expired", Mock())
        self.assertEqual(raised.exception.status_code, 410)

    async def test_non_owner_cannot_export_private_trip(self):
        trip = SimpleNamespace(
            id=10,
            user_id=1,
            is_public=0,
            itinerary_json='{"itinerary": []}',
        )
        with (
            patch.object(self.share, "_get_trip_or_404", return_value=trip),
            patch.object(self.share, "get_current_user", return_value={"user_id": 2}),
        ):
            with self.assertRaises(HTTPException) as raised:
                await self.share.export_trip(10, "json", None, "Bearer token", Mock())
        self.assertEqual(raised.exception.status_code, 403)

    async def test_owner_can_export_private_trip(self):
        trip = SimpleNamespace(
            id=10,
            user_id=1,
            is_public=0,
            itinerary_json='{"destination": "杭州", "itinerary": []}',
        )
        with (
            patch.object(self.share, "_get_trip_or_404", return_value=trip),
            patch.object(self.share, "get_current_user", return_value={"user_id": 1}),
        ):
            result = await self.share.export_trip(10, "json", None, "Bearer token", Mock())
        self.assertEqual(result["format"], "json")
        self.assertIn("杭州", result["content"])

    async def test_guest_can_export_public_trip(self):
        trip = SimpleNamespace(
            id=10,
            user_id=1,
            is_public=1,
            itinerary_json='{"destination": "杭州", "itinerary": []}',
        )
        with (
            patch.object(self.share, "_get_trip_or_404", return_value=trip),
            patch.object(self.share, "get_current_user", return_value=None),
        ):
            result = await self.share.export_trip(10, "json", None, None, Mock())
        self.assertEqual(result["format"], "json")


if __name__ == "__main__":
    unittest.main()
