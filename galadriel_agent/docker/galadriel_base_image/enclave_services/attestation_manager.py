import os
import base64
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
from nsm_util import NSMUtil


class AttestationManager:
    KEYPAIR_DIR = os.getcwd()
    PRIVATE_KEY_FILE = os.path.join(KEYPAIR_DIR, "private_key.pem")
    PUBLIC_KEY_FILE = os.path.join(KEYPAIR_DIR, "public_key.pem")
    GET_ATTESTATION_DOC = "GET_ATTESTATION_DOC"

    def __init__(self):
        self.nsm_util = NSMUtil()
        self._initialize_keypair()

    def _initialize_keypair(self):
        """Generate and store the Ed25519 keypair if it doesn't exist."""
        if not os.path.exists(self.PRIVATE_KEY_FILE) or not os.path.exists(self.PUBLIC_KEY_FILE):
            private_key = Ed25519PrivateKey.generate()
            public_key = private_key.public_key()

            # Serialize and store the private key
            with open(self.PRIVATE_KEY_FILE, "wb") as priv_file:
                priv_file.write(
                    private_key.private_bytes(
                        encoding=serialization.Encoding.PEM,
                        format=serialization.PrivateFormat.PKCS8,
                        encryption_algorithm=serialization.NoEncryption(),
                    )
                )

            # Serialize and store the public key
            with open(self.PUBLIC_KEY_FILE, "wb") as pub_file:
                pub_file.write(
                    public_key.public_bytes(
                        encoding=serialization.Encoding.PEM,
                        format=serialization.PublicFormat.SubjectPublicKeyInfo,
                    )
                )

            print("Ed25519 keypair generated and stored.")

    def _get_public_key(self) -> bytes:
        """Retrieve the public key from the stored file."""
        with open(self.PUBLIC_KEY_FILE, "rb") as pub_file:
            return pub_file.read()

    def handle_request(self, data: str) -> str:
        """Process the request."""
        try:
            if data.startswith(self.GET_ATTESTATION_DOC):
                # Extract public key from the request
                public_key = self._get_public_key()
                attestation_doc = self.nsm_util.get_attestation_doc(public_key)
                # Encode the attestation document in base64
                return base64.b64encode(attestation_doc).decode("utf-8")
            else:
                return "Invalid command"
        except Exception as e:
            return f"Error: {str(e)}"
