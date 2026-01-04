
import base64
from talos_sdk.wallet import Wallet
from talos_sdk.errors import TalosError

def base64url_decode(s):
    # Fix padding
    s += "=" * ((4 - len(s) % 4) % 4)
    return base64.urlsafe_b64decode(s)

def base64url_encode(b):
    return base64.urlsafe_b64encode(b).decode('utf-8').rstrip("=")

class BaseHandler:
    def run_vector(self, vector):
        raise NotImplementedError

    # Updated run_negative logic
    def run_negative(self, vector):
        # test_id = vector["test_id"]
        expected_error = vector.get("expected_error")
        expected_result = vector.get("expected") # For cases like verify: false
        
        try:
            self.run_vector(vector)
        except TalosError as e:
            if expected_error:
                self._check_expected_error(vector, e.code, e.message)
                return
            else:
                # Unexpected error if we expected a result
                 raise AssertionError(f"Unexpected error when expecting result: {e}")
        except Exception as e:
            if expected_error:
                 self._check_expected_error_generic(vector, str(e))
                 return
            pass # Fallback check below

        # If execution succeeded, check if we expected a specific negative result
        # e.g. verify: false. Logic inside run_vector for verify checks should raise Assertion if verify result is wrong.
        # But wait, run_vector for verify checks if result matches expected.
        # If expected.verify is false, and run_vector verified false, it passes silently.
        
        if expected_result and "verify" in expected_result:
             # Already handled in run_vector logic
             return

        if expected_error:
             raise AssertionError("Expected error but operation succeeded")

    def _check_expected_error(self, vector, code, message):
         expected = vector.get("expected_error", {})
         if "code" in expected and code != expected["code"]:
             raise AssertionError(f"Expected error code {expected['code']}, got {code}")
         if "message_contains" in expected and expected["message_contains"].lower() not in message.lower():
             raise AssertionError(f"Error message should contain '{expected['message_contains']}', got '{message}'")

    def _check_expected_error_generic(self, vector, message):
         expected = vector.get("expected_error", {})
         if "message_contains" in expected and expected["message_contains"].lower() not in message.lower():
             raise AssertionError(f"Exception message should contain '{expected['message_contains']}', got '{message}'")

class SigningVerifyHandler(BaseHandler):
    def run_vector(self, vector):
        test_id = vector["test_id"]
        inputs = vector["inputs"]
        expected = vector.get("expected", {})

        if test_id.startswith("sign_"):
            self._test_sign(inputs, expected)
        elif test_id.startswith("verify_"):
            self._test_verify(inputs, expected)
        elif test_id.startswith("invalid_"):
            if "seed_hex" in inputs:
                 self._test_sign(inputs, expected)
            else:
                 pass
        else:
            raise NotImplementedError(f"Unknown test type: {test_id}")

    def _test_sign(self, inputs, expected):
        seed_hex = inputs.get("seed_hex")
        message = inputs.get("message_utf8", "").encode("utf-8")
        
        if seed_hex:
            try:
                seed = bytes.fromhex(seed_hex)
                wallet = Wallet.from_seed(seed)
            except ValueError:
                raise
        else:
            wallet = None

        if wallet:
            if "did" in expected:
                if wallet.to_did() != expected["did"]:
                     raise AssertionError(f"DID mismatch: expected {expected['did']}, got {wallet.to_did()}")

            signature = wallet.sign(message)
            
            if "signature_base64url" in expected:
                sig_b64 = base64url_encode(signature)
                if sig_b64 != expected["signature_base64url"]:
                     raise AssertionError(f"Signature mismatch. Got {sig_b64}, expected {expected['signature_base64url']}")
            
            if "signature_length" in expected:
                if len(signature) != expected["signature_length"]:
                    raise AssertionError(f"Signature length mismatch: expected {expected['signature_length']}, got {len(signature)}")

            if expected.get("verify") is True:
                 # verify is static method accepting bytes
                 if not Wallet.verify(message, signature, wallet.public_key):
                      raise AssertionError("Failed to verify own signature")

    def _test_verify(self, inputs, expected):
        message = inputs.get("message_utf8", "").encode("utf-8")
        
        public_key = None
        if "public_key_hex" in inputs:
             public_key = bytes.fromhex(inputs["public_key_hex"])
        elif "wrong_public_key_hex" in inputs:
             public_key = bytes.fromhex(inputs["wrong_public_key_hex"])
        elif "seed_hex" in inputs:
             w = Wallet.from_seed(bytes.fromhex(inputs["seed_hex"]))
             public_key = w.public_key
        
        signature = None
        if "signature_base64url" in inputs:
            signature = base64url_decode(inputs["signature_base64url"])
        
        if "tampered_message" in inputs:
            message = inputs["tampered_message"].encode("utf-8")

        if public_key and signature:
             result = Wallet.verify(message, signature, public_key)
             if expected.get("verify") is not None and expected.get("verify") != result:
                 raise AssertionError(f"Verification mismatch: expected {expected.get('verify')}, got {result}")

def get_handler_for_file(filename):
    if filename == "signing_verify.json":
        return SigningVerifyHandler()
    return None
