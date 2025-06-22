"""
MIT License

Copyright (c) 2025 Christian P. Bonnell

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""


def xxhash32(data, seed=0):
    """
    Optimized xxHash implementation for MicroPython.

    See reference implementation on GitHub:
    https://github.com/Cyan4973/xxHash
    """

    PRIME1 = 2654435761
    PRIME2 = 2246822519
    PRIME3 = 3266489917
    PRIME4 = 668265263
    PRIME5 = 374761393

    def rotl32(x, r):
        """Rotate left (circular shift) for 32-bit values."""
        return ((x << r) & 0xFFFFFFFF) | (x >> (32 - r))

    length = len(data)
    h32 = (seed + PRIME5 + length) & 0xFFFFFFFF  # Base hash initialization

    # Process 4-byte chunks
    i = 0
    while i + 4 <= length:
        k1 = (
            data[i] | (data[i + 1] << 8) | (data[i + 2] << 16) | (data[i + 3] << 24)
        ) & 0xFFFFFFFF
        k1 = (k1 * PRIME3) & 0xFFFFFFFF
        k1 = rotl32(k1, 17)
        k1 = (k1 * PRIME4) & 0xFFFFFFFF
        h32 ^= k1
        h32 = rotl32(h32, 19)
        h32 = (h32 * PRIME1 + PRIME4) & 0xFFFFFFFF
        i += 4

    # Process remaining 1-3 bytes
    if i < length:
        if length - i == 3:
            h32 ^= data[i + 2] << 16
        if length - i >= 2:
            h32 ^= data[i + 1] << 8
        if length - i >= 1:
            h32 ^= data[i]
            h32 = (h32 * PRIME5) & 0xFFFFFFFF
            h32 = rotl32(h32, 11)
            h32 = (h32 * PRIME1) & 0xFFFFFFFF

    # Final mix
    h32 ^= h32 >> 15
    h32 = (h32 * PRIME2) & 0xFFFFFFFF
    h32 ^= h32 >> 13
    h32 = (h32 * PRIME3) & 0xFFFFFFFF
    h32 ^= h32 >> 16

    return h32
