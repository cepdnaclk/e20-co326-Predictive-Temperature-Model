from __future__ import annotations
import numpy as np
import config


# ── ESN hyper-parameters ──────────────────────────────────────────────────────
_RESERVOIR_SIZE:   int   = getattr(config, "ESN_RESERVOIR_SIZE",   200)
_SPARSITY:         float = getattr(config, "ESN_SPARSITY",         0.10)
_SPECTRAL_RADIUS:  float = getattr(config, "ESN_SPECTRAL_RADIUS",  0.90)  # slightly safer
_INPUT_SCALING:    float = getattr(config, "ESN_INPUT_SCALING",    0.3)   # reduced
_RIDGE_LAMBDA:     float = getattr(config, "ESN_RIDGE_LAMBDA",     1e-3)  # stronger regularization
_LEAK_RATE:        float = getattr(config, "ESN_LEAK_RATE",        0.3)


class _ESNForecaster:
    def __init__(self, n, sparsity, spectral_radius,
                 input_scaling, ridge_lambda, leak_rate,
                 horizon_steps):

        rng = np.random.default_rng(42)

        # Reservoir
        W = rng.standard_normal((n, n))
        mask = rng.random((n, n)) > sparsity
        W[mask] = 0.0
        eigvals = np.linalg.eigvals(W)
        sr = np.max(np.abs(eigvals))
        if sr > 1e-9:
            W *= spectral_radius / sr
        self.W_res = W

        self.W_in = rng.standard_normal((n, 1)) * input_scaling

        self.n = n
        self.leak_rate = leak_rate
        self.ridge_lambda = ridge_lambda
        self.horizon_steps = horizon_steps

        self.x = np.zeros(n)

        self.A = np.zeros((n, n))
        self.b = np.zeros(n)
        self.W_out = None

        # Normalisation
        self._norm_count = 0
        self._norm_mean = 0.0
        self._norm_M2 = 0.0

        self._state_buffer = []
        self.steps = 0

        # smoothing
        self._last_pred = None

    # ── Normalisation ─────────────────────────────────────────────────────────

    def _update_stats(self, value: float):
        self._norm_count += 1
        delta = value - self._norm_mean
        self._norm_mean += delta / self._norm_count
        self._norm_M2 += delta * (value - self._norm_mean)

    @property
    def _norm_std(self):
        if self._norm_count < 2:
            return 1.0
        var = self._norm_M2 / (self._norm_count - 1)
        return float(np.sqrt(max(var, 1e-6)))

    def _normalise(self, value: float):
        std = max(self._norm_std, 0.5)  # prevent explosion
        return (value - self._norm_mean) / std

    def _denormalise(self, value: float):
        return value * self._norm_std + self._norm_mean

    # ── Reservoir step ────────────────────────────────────────────────────────

    def _drive(self, x_norm: float):
        pre = self.W_res @ self.x + self.W_in[:, 0] * x_norm
        self.x = ((1.0 - self.leak_rate) * self.x +
                  self.leak_rate * np.tanh(pre))
        return self.x.copy()

    # ── Regression update ─────────────────────────────────────────────────────

    def _update_readout(self, state, target_norm):
        self.A += np.outer(state, state)
        self.b += state * target_norm
        self.W_out = None

    def _solve_readout(self):
        lhs = self.A + self.ridge_lambda * np.eye(self.n)
        return np.linalg.solve(lhs, self.b)

    # ── Main ──────────────────────────────────────────────────────────────────

    def update_and_predict(self, temp: float):

        self._update_stats(temp)

        x_norm = self._normalise(temp)
        state_t = self._drive(x_norm)

        self.steps += 1
        self._state_buffer.append(state_t)

        # Train only when enough history exists
        if len(self._state_buffer) > self.horizon_steps + 1:
            old_state = self._state_buffer[-self.horizon_steps - 1]
            target_norm = self._normalise(temp)
            self._update_readout(old_state, target_norm)

        # # SAFE WARM-UP
        # min_steps = max(config.WINDOW_SIZE, self.horizon_steps * 5)
        # if self.steps < min_steps:
        #     return temp, 0.0

        # Solve readout only after stable
        if self.W_out is None:
            self.W_out = self._solve_readout()

        pred_norm = float(self.W_out @ state_t)
        pred_temp = self._denormalise(pred_norm)

        # Clamp to realistic range
        pred_temp = max(temp - 10.0, min(temp + 10.0, pred_temp))
        pred_temp = max(0.0, min(60.0, pred_temp))

        # Smooth output
        if self._last_pred is None:
            self._last_pred = pred_temp

        alpha = 0.3
        pred_temp = alpha * pred_temp + (1 - alpha) * self._last_pred
        self._last_pred = pred_temp

        # Trend slope
        horizon_sec = config.PREDICTION_HORIZON_SEC
        slope = (pred_temp - temp) / max(horizon_sec, 1.0)

        return round(pred_temp, 2), round(slope, 6)


# ── Singleton ─────────────────────────────────────────────────────────────────

def _make_forecaster():
    sample_interval = getattr(
        config,
        "ESN_SAMPLE_INTERVAL_SEC",
        config.PREDICTION_HORIZON_SEC / 10.0,
    )

    horizon_steps = max(
        1,
        round(config.PREDICTION_HORIZON_SEC / sample_interval)
    )

    return _ESNForecaster(
        n=_RESERVOIR_SIZE,
        sparsity=_SPARSITY,
        spectral_radius=_SPECTRAL_RADIUS,
        input_scaling=_INPUT_SCALING,
        ridge_lambda=_RIDGE_LAMBDA,
        leak_rate=_LEAK_RATE,
        horizon_steps=horizon_steps,
    )


_forecaster = None


def _get_forecaster():
    global _forecaster
    if _forecaster is None:
        _forecaster = _make_forecaster()
    return _forecaster


# ── Public API ────────────────────────────────────────────────────────────────

def predict_temperature(history, horizon_sec):
    if not history:
        return None, None

    forecaster = _get_forecaster()
    _, temp = history[-1]
    return forecaster.update_and_predict(float(temp))


def classify_trend(slope):
    if slope is None:
        return "warming_up"

    threshold = config.TREND_SLOPE_THRESHOLD_C_PER_SEC

    if slope > threshold:
        return "rising"
    if slope < -threshold:
        return "falling"
    return "stable"


def reset_forecaster():
    global _forecaster
    _forecaster = None