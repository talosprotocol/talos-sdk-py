"""
Tests for the Talos SDK TalosClient.
"""

import pytest
from talos_sdk import Wallet, TalosClient, TalosTransportError


class TestTalosClient:
    """Tests for TalosClient facade."""

    def test_client_creation(self):
        """TalosClient should be creatable with wallet."""
        wallet = Wallet.generate()
        client = TalosClient("wss://example.com", wallet)
        assert client.wallet is wallet

    def test_protocol_version(self):
        """protocol_version should return version string."""
        wallet = Wallet.generate()
        client = TalosClient("wss://example.com", wallet)
        version = client.protocol_version()
        assert version == "1.0"

    def test_supported_protocol_range(self):
        """supported_protocol_range should return min/max tuple."""
        wallet = Wallet.generate()
        client = TalosClient("wss://example.com", wallet)
        min_v, max_v = client.supported_protocol_range()
        assert min_v == "1.0"
        assert max_v == "1.0"

    @pytest.mark.asyncio
    async def test_connect_and_close(self):
        """connect and close should work."""
        wallet = Wallet.generate()
        client = TalosClient("wss://example.com", wallet)

        await client.connect()
        await client.close()

    def test_sign_mcp_request_without_connect_fails(self):
        """sign_mcp_request should fail if not connected."""
        wallet = Wallet.generate()
        client = TalosClient("wss://example.com", wallet)

        with pytest.raises(TalosTransportError):
            client.sign_mcp_request({"method": "test"}, "tool", "action")

    @pytest.mark.asyncio
    async def test_sign_mcp_request_after_connect(self):
        """sign_mcp_request should work after connect."""
        wallet = Wallet.generate()
        client = TalosClient("wss://example.com", wallet)

        await client.connect()
        frame = client.sign_mcp_request({"method": "test"}, "tool", "action")

        assert frame.correlation_id.startswith("corr-")
        assert len(frame.signature) == 64

        await client.close()

    @pytest.mark.asyncio
    async def test_sign_and_send_mcp(self):
        """sign_and_send_mcp should return response."""
        wallet = Wallet.generate()
        client = TalosClient("wss://example.com", wallet)

        await client.connect()
        response = await client.sign_and_send_mcp({"method": "test"}, "tool", "action")

        assert response["status"] == "ok"
        assert "correlation_id" in response

        await client.close()
