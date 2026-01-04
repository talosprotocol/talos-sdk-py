#!/usr/bin/env python3
"""
Talos SDK Quickstart Example.

This example demonstrates the basic usage of the Talos SDK:
1. Generate an identity wallet
2. Sign a message
3. Verify the signature
4. Create a TalosClient
"""

import asyncio

from talos_sdk import Wallet, TalosClient


async def main():
    # 1. Generate a new identity wallet
    print("=== Talos SDK Quickstart ===\n")

    wallet = Wallet.generate(name="my-agent")
    print(f"Generated wallet: {wallet.name}")
    print(f"  DID: {wallet.to_did()}")
    print(f"  Address: {wallet.address[:16]}...")

    # 2. Sign a message
    message = b"Hello, Talos!"
    signature = wallet.sign(message)
    print(f"\nSigned message: {message.decode()}")
    print(f"  Signature: {signature.hex()[:32]}...")

    # 3. Verify the signature
    is_valid = Wallet.verify(message, signature, wallet.public_key)
    print(f"  Verification: {'✓ Valid' if is_valid else '✗ Invalid'}")

    # 4. Create a TalosClient
    client = TalosClient("wss://gateway.example.com", wallet)
    print("\nCreated TalosClient")
    print(f"  Protocol version: {client.protocol_version()}")
    print(f"  Supported range: {client.supported_protocol_range()}")

    # 5. Connect and sign an MCP request
    await client.connect()
    print("\nConnected to gateway")

    frame = client.sign_mcp_request(
        request={"method": "read", "params": {"path": "/data"}},
        tool="filesystem",
        action="read",
    )
    print("Signed MCP request:")
    print(f"  Correlation ID: {frame.correlation_id}")
    print(f"  Signer DID: {frame.signer_did}")

    await client.close()
    print("\nDisconnected. Quickstart complete!")


if __name__ == "__main__":
    asyncio.run(main())
