import base64
import json
from talos_sdk.wallet import Wallet
from talos_sdk.errors import TalosError
from talos_sdk.session import SessionManager, PrekeyBundle
from talos_sdk.crypto import KeyPair
from talos_sdk.canonical import canonical_json_bytes
from talos_sdk.mcp import sign_mcp_request


def base64url_decode(s):
    # Fix padding
    s += "=" * ((4 - len(s) % 4) % 4)
    return base64.urlsafe_b64decode(s)


def base64url_encode(b):
    return base64.urlsafe_b64encode(b).decode("utf-8").rstrip("=")


class BaseHandler:
    def run_vector(self, vector):
        raise NotImplementedError

    def run_negative(self, vector):
        expected_error = vector.get("expected_error")
        expected_result = vector.get("expected")

        try:
            self.run_vector(vector)
        except TalosError as e:
            if expected_error:
                self._check_expected_error(vector, e.code, e.message)
                return
            else:
                raise AssertionError(f"Unexpected error when expecting result: {e}")
        except Exception as e:
            if expected_error:
                self._check_expected_error_generic(vector, str(e))
                return
            raise e

        if expected_result and "verify" in expected_result:
            return

        if expected_error:
            raise AssertionError("Expected error but operation succeeded")

    def _check_expected_error(self, vector, code, message):
        expected = vector.get("expected_error", {})
        if "code" in expected and code != expected["code"]:
            raise AssertionError(f"Expected error code {expected['code']}, got {code}")
        if (
            "message_contains" in expected
            and expected["message_contains"].lower() not in message.lower()
        ):
            raise AssertionError(
                f"Error message should contain '{expected['message_contains']}', got '{message}'"
            )

    def _check_expected_error_generic(self, vector, message):
        expected = vector.get("expected_error", {})
        if (
            "message_contains" in expected
            and expected["message_contains"].lower() not in message.lower()
        ):
            raise AssertionError(
                f"Exception message should contain '{expected['message_contains']}', got '{message}'"
            )


class SigningVerifyHandler(BaseHandler):
    def run_vector(self, vector):
        test_id = vector["test_id"]
        inputs = vector["inputs"]
        expected = vector.get("expected", {})

        if test_id.startswith("sign_"):
            self._test_sign(inputs, expected)
        elif test_id.startswith("verify_"):
            self._test_verify(inputs, expected)
        else:
            raise NotImplementedError(f"Unknown test type: {test_id}")

    def _test_sign(self, inputs, expected):
        seed_hex = inputs.get("seed_hex")
        message = inputs.get("message_utf8", "").encode("utf-8")
        wallet = Wallet.from_seed(bytes.fromhex(seed_hex)) if seed_hex else None

        if wallet:
            if "did" in expected:
                if wallet.to_did() != expected["did"]:
                    raise AssertionError(f"DID mismatch: {wallet.to_did()} != {expected['did']}")

            signature = wallet.sign(message)
            if "signature_base64url" in expected:
                sig_b64 = base64url_encode(signature)
                if sig_b64 != expected["signature_base64url"]:
                    raise AssertionError(
                        f"Signature mismatch. Got {sig_b64}, expected {expected['signature_base64url']}"
                    )

    def _test_verify(self, inputs, expected):
        message = inputs.get("message_utf8", "").encode("utf-8")
        public_key = bytes.fromhex(inputs["public_key_hex"]) if "public_key_hex" in inputs else None
        signature = (
            base64url_decode(inputs["signature_base64url"])
            if "signature_base64url" in inputs
            else None
        )

        if public_key and signature:
            result = Wallet.verify(message, signature, public_key)
            if expected.get("verify") is not None and expected.get("verify") != result:
                raise AssertionError(f"Verification mismatch: {result} != {expected.get('verify')}")


class CanonicalJsonHandler(BaseHandler):
    def run_vector(self, vector):
        inputs = vector["inputs"]
        expected = vector["expected"]

        if "unordered" in inputs:
            res = canonical_json_bytes(inputs["unordered"]).decode("utf-8")
            if res != expected["canonical"]:
                raise AssertionError(f"Canonical mismatch: {res} != {expected['canonical']}")
        elif "value" in inputs:
            res = canonical_json_bytes(inputs["value"]).decode("utf-8")
            if "canonical_number" in expected:
                if res != expected["canonical_number"]:
                    raise AssertionError(
                        f"Number encoding mismatch: {res} != {expected['canonical_number']}"
                    )
            elif "canonical" in expected:
                if res != expected["canonical"]:
                    raise AssertionError(
                        f"Value canonical mismatch: {res} != {expected['canonical']}"
                    )
        elif "pretty_printed" in inputs:
            obj = json.loads(inputs["pretty_printed"])
            res = canonical_json_bytes(obj).decode("utf-8")
            if res != expected["canonical"]:
                raise AssertionError(f"Pretty printed mismatch: {res} != {expected['canonical']}")


class CapabilityHandler(BaseHandler):
    def run_vector(self, vector):
        inputs = vector["inputs"]
        expected = vector.get("expected", {})

        from talos_sdk.security import Capability
        from talos_sdk.wallet import Wallet

        # 1. Create capability
        issuer_wallet = Wallet.from_seed(bytes.fromhex(inputs["issuer_seed_hex"]))
        cap = Capability.create(
            issuer_wallet=issuer_wallet,
            subject_did=inputs["subject_did"],
            scope=inputs["scope"],
            exp=inputs["exp"],
            iat=1704067200,  # Fixed for deterministic test if needed, or use iat from inputs if exists
        )

        # 2. Verify
        if "verify" in expected:
            result = cap.verify(issuer_wallet.public_key)
            if result != expected["verify"]:
                raise AssertionError(f"Capability verification mismatch: {result}")

        # 3. Authorize
        for key, val in expected.items():
            if key.startswith("authorize_fast_"):
                parts = key.split("_")
                tool = parts[2]
                action = "_".join(parts[3:])
                result = cap.authorize(tool, action)
                if result != val:
                    raise AssertionError(
                        f"Authorization mismatch for {tool}:{action}. Got {result}"
                    )

    def run_negative(self, vector):
        # Specific negative tests for expiry/tampering
        # For now, minimal pass if they raise the right error code
        super().run_negative(vector)


class FrameCodecHandler(BaseHandler):
    def run_vector(self, vector):
        inputs = vector["inputs"]
        expected = vector.get("expected", {})

        from talos_sdk.frames import Frame

        if "frame_type" in inputs and "payload_utf8" in inputs:
            # Encoding test
            payload = inputs["payload_utf8"].encode("utf-8")
            frame = Frame(inputs["frame_type"], payload)
            encoded = frame.encode().decode("utf-8")
            if encoded != expected["encoded_base64url"]:
                raise AssertionError("Frame encoding mismatch")

        if "encoded_base64url" in inputs:
            # Decoding test
            frame = Frame.decode(inputs["encoded_base64url"].encode("utf-8"))
            if "frame_type" in expected and frame.type != expected["frame_type"]:
                raise AssertionError("Decoded type mismatch")
            if "version" in expected and frame.version != expected["version"]:
                raise AssertionError("Decoded version mismatch")


class MCPSignHandler(BaseHandler):
    def run_vector(self, vector):
        inputs = vector["inputs"]
        expected = vector.get("expected", {})

        if "signer_seed_hex" in inputs:
            wallet = Wallet.from_seed(bytes.fromhex(inputs["signer_seed_hex"]))
            frame = sign_mcp_request(
                wallet,
                inputs["request"],
                inputs["session_id"],
                inputs["correlation_id"],
                inputs["tool"],
                inputs["action"],
                inputs.get("timestamp"),
            )

            if "payload_canonical" in expected:
                if frame.payload.decode("utf-8") != expected["payload_canonical"]:
                    raise AssertionError("MCP Payload mismatch")
            if "signature_length" in expected:
                if len(frame.signature) != expected["signature_length"]:
                    raise AssertionError("MCP Signature length mismatch")

        if "actual_correlation_id" in inputs:
            # Negative case: verify fail
            # verify_mcp_response needs a frame
            pass


class RatchetHandler(BaseHandler):
    def run_trace(self, trace):
        def mk_pair(priv_b64, pub_b64):
            return KeyPair(
                private_key=base64url_decode(priv_b64),
                public_key=base64url_decode(pub_b64),
                key_type="ed25519",
            )

        alice_id = mk_pair(trace["alice"]["identity_private"], trace["alice"]["identity_public"])
        bob_id = mk_pair(trace["bob"]["identity_private"], trace["bob"]["identity_public"])

        alice_mgr = SessionManager(alice_id)
        bob_mgr = SessionManager(bob_id)

        bob_bundle = trace["bob"]["prekey_bundle"]
        spk_priv = base64url_decode(trace["bob"]["bundle_secrets"]["signed_prekey_private"])
        spk_pub = base64url_decode(bob_bundle["signed_prekey"])

        bob_mgr._signed_prekey = KeyPair(
            private_key=spk_priv, public_key=spk_pub, key_type="x25519"
        )
        bob_mgr._prekey_signature = base64url_decode(bob_bundle["prekey_signature"])

        b_bundle_obj = PrekeyBundle(
            identity_key=base64url_decode(bob_bundle["identity_key"]),
            signed_prekey=base64url_decode(bob_bundle["signed_prekey"]),
            prekey_signature=base64url_decode(bob_bundle["prekey_signature"]),
            one_time_prekey=base64url_decode(bob_bundle["one_time_prekey"])
            if bob_bundle["one_time_prekey"]
            else None,
        )

        import talos_sdk.session

        alice_eph_priv = base64url_decode(trace["alice"]["ephemeral_private"])
        original_gen = talos_sdk.session.generate_encryption_keypair

        def mock_gen_init():
            return KeyPair(
                private_key=alice_eph_priv,
                public_key=base64url_decode(trace["steps"][0]["header"]["dh"]),
                key_type="x25519",
            )

        talos_sdk.session.generate_encryption_keypair = mock_gen_init
        try:
            alice_session = alice_mgr.create_session_as_initiator("did:bob", b_bundle_obj)
        finally:
            talos_sdk.session.generate_encryption_keypair = original_gen

        bob_session = None

        def reconstruct_msg(step_data):
            if "wire_message_b64u" in step_data:
                return base64url_decode(step_data["wire_message_b64u"])
            header_bytes = base64url_decode(step_data["aad"])
            nonce = base64url_decode(step_data["nonce"])
            ct = base64url_decode(step_data["ciphertext"])
            h_len = len(header_bytes).to_bytes(2, "big")
            return h_len + header_bytes + nonce + ct

        for step in trace["steps"]:
            actor = step["actor"]
            action = step["action"]

            original_gen = talos_sdk.session.generate_encryption_keypair
            if "ratchet_priv" in step:
                r_priv = base64url_decode(step["ratchet_priv"])

                def mock_gen_step():
                    from cryptography.hazmat.primitives.asymmetric import x25519
                    from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

                    priv_obj = x25519.X25519PrivateKey.from_private_bytes(r_priv)
                    pub_bytes = priv_obj.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
                    return KeyPair(private_key=r_priv, public_key=pub_bytes, key_type="x25519")

                talos_sdk.session.generate_encryption_keypair = mock_gen_step

            try:
                if action == "encrypt":
                    session = alice_session if actor == "alice" else bob_session
                    pt = base64url_decode(step["plaintext"])
                    session.encrypt(pt)

                elif action == "decrypt":
                    msg_bytes = reconstruct_msg(step)

                    if actor == "bob" and bob_session is None:
                        try:
                            envelope = json.loads(msg_bytes)
                            peer_dh = base64url_decode(envelope["header"]["dh"])
                        except (json.JSONDecodeError, KeyError):
                            h_len = int.from_bytes(msg_bytes[:2], "big")
                            h_bytes = msg_bytes[2 : 2 + h_len]
                            h_json = json.loads(h_bytes)
                            peer_dh = base64url_decode(h_json["dh"])

                        bob_session = bob_mgr.create_session_as_responder("did:alice", peer_dh)

                    session = alice_session if actor == "alice" else bob_session
                    decrypted = session.decrypt(msg_bytes)
                    expected_pt = base64url_decode(
                        step["expected_plaintext"]
                        if "expected_plaintext" in step
                        else step["plaintext"]
                    )

                    if decrypted != expected_pt:
                        raise AssertionError(f"Decryption mismatch at step {step['step']}")

            finally:
                talos_sdk.session.generate_encryption_keypair = original_gen


class MicroVectorHandler(BaseHandler):
    def run_vector(self, vector):
        test_id = vector["test_id"]
        if test_id == "header_canonical_sorting":
            self._test_header_canonical(vector)
        elif test_id == "kdf_rk_root_ratchet":
            self._test_kdf_rk(vector)
        elif test_id == "kdf_ck_symmetric_ratchet":
            self._test_kdf_ck(vector)
        else:
            raise NotImplementedError(f"Unknown micro-vector test: {test_id}")

    def _test_header_canonical(self, vector):
        from talos_sdk.session import MessageHeader

        inputs = vector["input_header"]
        header = MessageHeader(
            dh_public=base64url_decode(inputs["dh"]),
            previous_chain_length=inputs["pn"],
            message_number=inputs["n"],
        )
        canonical = header.to_bytes()
        expected = base64url_decode(vector["expected_canonical_b64u"])
        if canonical != expected:
            raise AssertionError(
                f"Canonical mismatch. Got {base64url_encode(canonical)}, expected {vector['expected_canonical_b64u']}"
            )

    def _test_kdf_rk(self, vector):
        from talos_sdk.session import _kdf_rk

        rk = base64url_decode(vector["inputs"]["rk"])
        dh_out = base64url_decode(vector["inputs"]["dh_out"])
        new_rk, new_ck = _kdf_rk(rk, dh_out)
        expected_rk = base64url_decode(vector["expected"]["new_rk"])
        expected_ck = base64url_decode(vector["expected"]["new_ck"])
        if new_rk != expected_rk:
            raise AssertionError(
                f"New RK mismatch. Got {base64url_encode(new_rk)}, expected {vector['expected']['new_rk']}"
            )
        if new_ck != expected_ck:
            raise AssertionError(
                f"New CK mismatch. Got {base64url_encode(new_ck)}, expected {vector['expected']['new_ck']}"
            )

    def _test_kdf_ck(self, vector):
        from talos_sdk.session import _kdf_ck

        ck = base64url_decode(vector["inputs"]["ck"])
        mk, next_ck = _kdf_ck(ck)
        expected_next_ck = base64url_decode(vector["expected"]["next_ck"])
        expected_mk = base64url_decode(vector["expected"]["mk"])
        if next_ck != expected_next_ck:
            raise AssertionError(
                f"Next CK mismatch. Got {base64url_encode(next_ck)}, expected {vector['expected']['next_ck']}"
            )
        if mk != expected_mk:
            raise AssertionError(
                f"MK mismatch. Got {base64url_encode(mk)}, expected {vector['expected']['mk']}"
            )


def get_handler_for_file(filename):
    if filename == "signing_verify.json":
        return SigningVerifyHandler()
    if filename == "canonical_json.json":
        return CanonicalJsonHandler()
    if filename == "capability_verify.json":
        return CapabilityHandler()
    if filename == "frame_codec.json":
        return FrameCodecHandler()
    if filename == "mcp_sign_verify.json":
        return MCPSignHandler()
    if filename in [
        "roundtrip_basic.json",
        "out_of_order.json",
        "max_skip.json",
        "v1_1_0_roundtrip.json",
    ]:
        return RatchetHandler()
    if filename in ["header_canonical_bytes.json", "kdf_rk_step.json", "kdf_ck_step.json"]:
        return MicroVectorHandler()
    return None
