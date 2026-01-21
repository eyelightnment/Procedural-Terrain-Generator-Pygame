import numpy as np

def fade(t):
    # 6t^5 - 15t^4 + 10t^3
    return t * t * t * (t * (t * 6 - 15) + 10)

def lerp(a, b, x):
    return a + x * (b - a)

def gradient(h, x, y):
    # Standard Perlin 2D gradients
    vectors = np.array([[1, 1], [-1, 1], [1, -1], [-1, -1],
                        [1, 0], [-1, 0], [0, 1], [0, -1]])
    # Use array indexing to pick the vector for every point in the grid
    g = vectors[h % 8]
    return g[..., 0] * x + g[..., 1] * y

def perlin_2d(x, y, p):
    # Ensure x and y are handled as numpy arrays
    xi = np.floor(x).astype(int) & 255
    yi = np.floor(y).astype(int) & 255
    
    xf = x - np.floor(x)
    yf = y - np.floor(y)
    
    u = fade(xf)
    v = fade(yf)
    
    # Hashing: p must be at least 512 elements to avoid index errors
    n00 = p[p[xi] + yi]
    n01 = p[p[xi] + (yi + 1)]
    n10 = p[p[(xi + 1)] + yi]
    n11 = p[p[(xi + 1)] + (yi + 1)]
    
    # Bilinear interpolation
    x1 = lerp(gradient(n00, xf, yf), gradient(n10, xf - 1, yf), u)
    x2 = lerp(gradient(n01, xf, yf - 1), gradient(n11, xf - 1, yf - 1), u)
    
    return lerp(x1, x2, v)

def get_permutation_table(seed=42):
    rng = np.random.default_rng(seed)
    p = np.arange(256, dtype=int)
    rng.shuffle(p)
    # Double the table to handle the p[p[xi]+yi] indexing without wrapping
    return np.tile(p, 2)

def generate_fractal_noise(x, y, p, octaves=6, persistence=0.5, lacunarity=2.0):
    total = np.zeros_like(x, dtype=float)
    frequency = 1
    amplitude = 1
    max_val = 0
    for _ in range(octaves):
        total += perlin_2d(x * frequency, y * frequency, p) * amplitude
        max_val += amplitude
        amplitude *= persistence
        frequency *= lacunarity
    return total / max_val