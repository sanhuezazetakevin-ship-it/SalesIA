
import pytest

from app.core.security import (
    TokenInvalidoError,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


def test_password_hash():
    password = "ClaveDePrueba-Segura-2026!"

    hashed = hash_password(password)

    assert hashed != password
    assert verify_password(password, hashed)
    assert not verify_password("ClaveIncorrecta", hashed)


def test_access_token():
    token = create_access_token(
        usuario_id=1,
        empresa_id=1,
        sesion_id=1,
    )

    payload = decode_token(token, expected_type="access")

    assert payload["sub"] == "1"
    assert payload["empresa_id"] == 1
    assert payload["sid"] == 1
    assert payload["type"] == "access"


def test_refresh_token():
    token = create_refresh_token(
        usuario_id=1,
        empresa_id=1,
        sesion_id=1,
    )

    payload = decode_token(token, expected_type="refresh")

    assert payload["type"] == "refresh"


def test_refresh_no_puede_usarse_como_access():
    token = create_refresh_token(
        usuario_id=1,
        empresa_id=1,
        sesion_id=1,
    )

    with pytest.raises(TokenInvalidoError):
        decode_token(token, expected_type="access")


def test_token_alterado():
    token = create_access_token(
        usuario_id=1,
        empresa_id=1,
        sesion_id=1,
    )

    partes = token.split(".")
    firma = partes[2]

    # Modificar la firma sin conocer la clave secreta.
    partes[2] = (
        ("A" if firma[0] != "A" else "B")
        + firma[1:]
    )

    token_alterado = ".".join(partes)

    with pytest.raises(TokenInvalidoError):
        decode_token(token_alterado, expected_type="access")


def test_identificadores_invalidos():
    with pytest.raises(ValueError):
        create_access_token(
            usuario_id=0,
            empresa_id=1,
            sesion_id=1,
        )
