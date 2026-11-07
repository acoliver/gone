"""NumPy point serialization used by the native P3-SAM Sonata encoder."""

from __future__ import annotations

import numpy as np

SERIALIZATION_ORDERS = ("z", "z-trans", "hilbert", "hilbert-trans")


def z_order_encode(grid_coord: np.ndarray, depth: int) -> np.ndarray:
    coord = np.asarray(grid_coord, dtype=np.int64)
    code = np.zeros(coord.shape[0], dtype=np.int64)
    for bit in range(depth):
        code |= ((coord[:, 0] >> bit) & 1) << (3 * bit + 2)
        code |= ((coord[:, 1] >> bit) & 1) << (3 * bit + 1)
        code |= ((coord[:, 2] >> bit) & 1) << (3 * bit)
    return code


def _gray_to_binary(gray: np.ndarray) -> np.ndarray:
    binary = gray.copy()
    shift = 1
    while shift < binary.shape[1]:
        shift *= 2
    shift //= 2
    while shift:
        shifted = np.zeros_like(binary)
        shifted[:, shift:] = binary[:, :-shift]
        binary ^= shifted
        shift //= 2
    return binary


def hilbert_encode(grid_coord: np.ndarray, depth: int) -> np.ndarray:
    coord = np.asarray(grid_coord, dtype=np.int64)
    if coord.ndim != 2 or coord.shape[1] != 3:
        raise ValueError(f"Hilbert coordinates must be [N,3], got {coord.shape}")
    if depth * 3 > 63:
        raise ValueError("Hilbert code exceeds signed int64")

    bit_positions = np.arange(depth - 1, -1, -1, dtype=np.int64)
    gray = ((coord[:, :, None] >> bit_positions[None, None, :]) & 1).astype(np.bool_)
    for bit in range(depth):
        for dim in range(3):
            mask = gray[:, dim, bit]
            gray[:, 0, bit + 1 :] ^= mask[:, None]
            to_flip = (~mask[:, None]) & (
                gray[:, 0, bit + 1 :] ^ gray[:, dim, bit + 1 :]
            )
            gray[:, dim, bit + 1 :] ^= to_flip
            gray[:, 0, bit + 1 :] ^= to_flip

    packed_gray = gray.swapaxes(1, 2).reshape(coord.shape[0], depth * 3)
    binary = _gray_to_binary(packed_gray)
    code = np.zeros(coord.shape[0], dtype=np.int64)
    for column in range(binary.shape[1]):
        code = (code << 1) | binary[:, column].astype(np.int64)
    return code


def encode(
    grid_coord: np.ndarray,
    batch: np.ndarray,
    depth: int,
    order: str,
) -> np.ndarray:
    if order not in SERIALIZATION_ORDERS:
        raise ValueError(f"unsupported serialization order {order!r}")
    coord = np.asarray(grid_coord, dtype=np.int64)
    if order.endswith("-trans"):
        coord = coord[:, [1, 0, 2]]
    if order.startswith("z"):
        code = z_order_encode(coord, depth)
    else:
        code = hilbert_encode(coord, depth)
    return (np.asarray(batch, dtype=np.int64) << (depth * 3)) | code


def serialize(
    grid_coord: np.ndarray,
    batch: np.ndarray | None = None,
    orders: tuple[str, ...] = SERIALIZATION_ORDERS,
    order_permutation: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, int]:
    coord = np.asarray(grid_coord, dtype=np.int64)
    if coord.ndim != 2 or coord.shape[1] != 3 or coord.shape[0] == 0:
        raise ValueError(f"grid coordinates must be nonempty [N,3], got {coord.shape}")
    if np.any(coord < 0):
        raise ValueError("serialized grid coordinates must be nonnegative")
    if batch is None:
        batch = np.zeros(coord.shape[0], dtype=np.int64)
    depth = int(int(coord.max()) + 1).bit_length()
    if depth > 16:
        raise ValueError(f"serialized coordinate depth {depth} exceeds Sonata limit 16")
    codes = np.stack([encode(coord, batch, depth, order) for order in orders])
    order = np.argsort(codes, axis=1, kind="stable")
    inverse = np.empty_like(order)
    values = np.broadcast_to(np.arange(coord.shape[0], dtype=np.int64), order.shape)
    np.put_along_axis(inverse, order, values, axis=1)
    if order_permutation is not None:
        permutation = np.asarray(order_permutation, dtype=np.int64)
        codes = codes[permutation]
        order = order[permutation]
        inverse = inverse[permutation]
    return codes, order, inverse, depth
