import base64
from unittest.mock import mock_open, patch
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from galadriel.entities import Message, Proof
from galadriel.proof.prover import Prover


@pytest.fixture
def mock_private_key():
    return Ed25519PrivateKey.generate()


@pytest.fixture
def mock_public_key(mock_private_key):
    return mock_private_key.public_key()


@pytest.fixture
def mock_files(mock_private_key, mock_public_key):
    """Mock file operations for key loading"""
    private_bytes = mock_private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_bytes = mock_public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    mock_files = {
        "/private_key.pem": mock_open(read_data=private_bytes).return_value,
        "/public_key.pem": mock_open(read_data=public_bytes).return_value,
    }

    def mock_open_file(filename, *args, **kwargs):
        return mock_files[filename]

    with patch("builtins.open", mock_open_file):
        yield


@pytest.fixture
def prover(mock_files):
    with patch("galadriel.proof.prover.NSMUtil") as mock_nsm:
        mock_nsm.return_value.get_attestation_doc.return_value = b"mock_attestation_doc"
        yield Prover()


@pytest.mark.asyncio
async def test_generate_proof_success(prover):
    """Test successful proof generation"""
    # Setup
    request = Message(content="hello")
    response = Message(content="world")

    # Execute
    proof = await prover.generate_proof(request, response)

    # Assert
    assert isinstance(proof, Proof)
    assert proof.hash  # Should contain a hex string
    assert proof.signature  # Should contain a hex string
    assert proof.public_key  # Should contain a hex string
    assert proof.attestation == base64.b64encode(b"mock_attestation_doc").decode()


@pytest.mark.asyncio
async def test_generate_proof_with_empty_messages(prover):
    """Test proof generation with empty messages"""
    # Setup
    request = Message(content="")
    response = Message(content="")

    # Execute
    proof = await prover.generate_proof(request, response)

    # Assert
    assert isinstance(proof, Proof)
    assert all(isinstance(field, str) for field in [proof.hash, proof.signature, proof.public_key, proof.attestation])


@pytest.mark.asyncio
async def test_generate_proof_error_handling(prover):
    """Test error handling during proof generation"""
    # Setup
    prover.nsm_util.get_attestation_doc.side_effect = Exception("NSM error")

    # Execute and Assert
    with pytest.raises(Exception, match="NSM error"):
        await prover.generate_proof(Message(content="test"), Message(content="test"))


def test_hash_data_consistency(prover):
    """Test that _hash_data produces consistent results"""
    # Setup
    request = Message(content="test request")
    response = Message(content="test response")

    # Execute
    hash1 = prover._hash_data(request, response)
    hash2 = prover._hash_data(request, response)

    # Assert
    assert hash1 == hash2
    assert isinstance(hash1, bytes)
    assert len(hash1) == 32  # SHA-256 produces 32 bytes


@pytest.mark.asyncio
async def test_publish_proof_success(prover):
    """Test successful proof publication"""
    # Setup
    with patch("requests.post") as mock_post:
        mock_post.return_value.status_code = 200
        request = Message(content="test request")
        response = Message(content="test response")
        proof = await prover.generate_proof(request, response)

        # Execute
        with patch.dict("os.environ", {"GALADRIEL_API_KEY": "test_key"}):
            result = await prover.publish_proof(request, response, proof)

        # Assert
        assert result is True
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == "https://api.galadriel.com/v1/verified/chat/log"
        assert call_args[1]["headers"]["Authorization"] == "Bearer test_key"


@pytest.mark.asyncio
async def test_publish_proof_failure(prover):
    """Test failed proof publication"""
    # Setup
    with patch("requests.post") as mock_post:
        mock_post.return_value.status_code = 500
        request = Message(content="test request")
        response = Message(content="test response")
        proof = await prover.generate_proof(request, response)

        # Execute
        result = await prover.publish_proof(request, response, proof)

        # Assert
        assert result is False


def test_get_authorization_with_key(prover):
    """Test authorization header generation with API key"""
    # Setup
    with patch.dict("os.environ", {"GALADRIEL_API_KEY": "test_key"}):
        # Execute
        auth = prover._get_authorization()

        # Assert
        assert auth == "Bearer test_key"


def test_get_authorization_without_key(prover):
    """Test authorization header generation without API key"""
    # Setup
    with patch.dict("os.environ", {}, clear=True):
        # Execute
        auth = prover._get_authorization()

        # Assert
        assert auth is None
