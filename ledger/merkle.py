"""The build-plan Merkle algorithm. Input order is significant."""
import hashlib


def merkle_root(hashes: list[str]) -> str | None:
    layer = [bytes.fromhex(h) for h in hashes]
    if not layer:
        return None
    while len(layer) > 1:
        if len(layer) % 2:
            layer.append(layer[-1])
        layer = [
            hashlib.sha256(layer[i] + layer[i + 1]).digest()
            for i in range(0, len(layer), 2)
        ]
    return layer[0].hex()
