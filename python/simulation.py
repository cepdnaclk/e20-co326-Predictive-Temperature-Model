"""
simulation.py
-------------
Simulates more natural temperature readings with:
- Variable daily cycles (non-perfect sine)
- Correlated noise (more realistic than uniform)
- Slow baseline drift
- Softer anomaly behavior
"""

import random
import numpy as np

# Parameters
BASE_TEMP = 30.0
AMPLITUDE = 5.0
NOISE_LEVEL = 0.3
ANOMALY_PROB = 0.03

# Internal state (for realism)
_phase = 0.0
_baseline_drift = 0.0
_noise_state = 0.0


def simulate_temperature(step: int) -> tuple[float, bool]:
    global _phase, _baseline_drift, _noise_state

    # --- 1. Variable cycle (non-repeating) ---
    # Slightly vary the "day length"
    period = 50 + random.uniform(-5, 5)
    _phase += (2 * np.pi) / period

    # Add a second harmonic to break symmetry
    daily_cycle = (
        AMPLITUDE * np.sin(_phase) +
        0.3 * AMPLITUDE * np.sin(2 * _phase + 1.5)
    )

    # --- 2. Slow baseline drift ---
    _baseline_drift += random.uniform(-0.02, 0.02)

    # --- 3. Correlated noise (random walk) ---
    _noise_state += random.uniform(-NOISE_LEVEL, NOISE_LEVEL)
    _noise_state *= 0.9  # dampen runaway drift

    temp = BASE_TEMP + daily_cycle + _baseline_drift + _noise_state

    # --- 4. More natural anomalies ---
    is_anomaly = False
    if random.random() < ANOMALY_PROB:
        spike = random.uniform(3.0, 8.0)
        # Smooth spike (not instant jump)
        temp += spike * (0.5 + 0.5 * np.sin(_phase))
        is_anomaly = True

    return round(temp, 2), is_anomaly