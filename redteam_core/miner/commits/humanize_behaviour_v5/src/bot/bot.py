import logging
import json



# --- Standard Library
import math
import random
import time
from time import sleep
from typing import Any, Dict, List, Tuple, Union

# --- Third-Party
import numpy as np
import pytweening
import scipy.stats
from selenium.common.exceptions import MoveTargetOutOfBoundsException
from selenium.webdriver import Chrome, Edge, Firefox, Safari
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


logger = logging.getLogger(__name__)

class GeoNoise:
    """Utility for geometry conversions and randomized curve parameters."""

    @staticmethod
    def to_abs_offset(element: WebElement, rel_xy: List[float]) -> List[int]:
        """Convert relative offsets (0..1) to absolute pixel offsets within an element box."""
        box = element.size
        w, h = box["width"], box["height"]
        return [int(w * rel_xy[0]), int(h * rel_xy[1])]

    @staticmethod
    def choose_curve_params(
        driver: WebDriver,
        start_xy: List[float],
        end_xy: List[float],
        steady: bool,
        win_w: int,
        win_h: int,
        tweening_method=None,
    ) -> Tuple[int, int, int, float, float, float, Any, int, bool]:
        """Return randomized parameters shaping a human-like mouse path.

        Returns:
            (offset_x, offset_y, knots, mu, sigma, freq, tween, samples, is_web)
        """
        is_web = isinstance(driver, (Chrome, Firefox, Edge, Safari))
        if is_web:
            ww, wh = driver.get_window_size().values()
        else:
            ww, wh = win_w, win_h

        # soft-safe region for start/end sanity
        x_min, x_max = ww * 0.15, ww * 0.85
        y_min, y_max = wh * 0.15, wh * 0.85

        # Enhanced movement strategies with different patterns
        movement_strategies = [
            {"ranges": [range(15, 35), range(35, 60), range(60, 90)], "weights": [0.3, 0.5, 0.2]},  # Precise
            {"ranges": [range(25, 50), range(50, 80), range(80, 120)], "weights": [0.2, 0.4, 0.4]},  # Natural
            {"ranges": [range(30, 55), range(55, 85), range(85, 110)], "weights": [0.1, 0.3, 0.6]},  # Erratic
        ]
        strategy = random.choice(movement_strategies)
        offx = random.choice(random.choices(strategy["ranges"], strategy["weights"])[0])
        offy = random.choice(random.choices(strategy["ranges"], strategy["weights"])[0])

        # if points are near edges, reduce fancy offsets/knots
        knots = 2
        sx, sy = start_xy
        ex, ey = end_xy
        if not (x_min <= sx <= x_max and y_min <= sy <= y_max):
            offx = offy = 1
            knots = 1
        if not (x_min <= ex <= x_max and y_min <= ey <= y_max):
            offx = offy = 1
            knots = 1

        # Enhanced tweening options for more natural movement
        tween_options = [
            pytweening.easeInOutCubic,
            pytweening.easeInOutQuad,
            pytweening.easeInOutQuart,
            pytweening.easeInOutSine,
            pytweening.easeInOutExpo,
        ]
        tween = random.choice(tween_options)

        # make long/straight-ish paths simpler
        if steady and (abs(sx - ex) < 10 or abs(sy - ey) < 10):
            is_linear = True
        else:
            is_linear = False
        knots = 3 if is_linear else 2

        # Enhanced distortion parameters for more realistic movement
        distortion_profiles = [
            {"mu_range": range(75, 95), "sigma_range": range(80, 100), "freq_range": range(20, 50)},  # Subtle
            {"mu_range": range(85, 105), "sigma_range": range(90, 110), "freq_range": range(30, 60)},  # Moderate
            {"mu_range": range(95, 115), "sigma_range": range(100, 120), "freq_range": range(40, 70)},  # Pronounced
        ]
        profile = random.choice(distortion_profiles)
        mu = random.choice(profile["mu_range"]) / 100.0
        sigma = random.choice(profile["sigma_range"]) / 100.0
        freq = random.choice(profile["freq_range"]) / 100.0

        # pick target sample density based on distance
        dist = math.hypot(ex - sx, ey - sy)

        def _largest_den(n: int) -> int:
            d = max(1, n // 2)
            while d > 0:
                if n / d > 2:
                    return d
                d -= 1
            return 1

        px = 13
        if dist // px < 2:
            px = _largest_den(int(max(2, dist)))
        samples = int(max(2, dist // px))

        return int(offx), int(offy), knots, mu, sigma, freq, tween, samples, is_web

class CurveKit:

    @staticmethod
    def _ncr(n: int, k: int) -> float:
        return math.factorial(n) / float(math.factorial(k) * math.factorial(n - k))

    @staticmethod
    def _bern_term(t: float, i: int, n: int) -> float:
        return CurveKit._ncr(n, i) * (t ** i) * ((1 - t) ** (n - i))

    @staticmethod
    def points_on_curve(n: int, anchors: List[Tuple[float, float]]) -> List[Tuple[int, int]]:
        if not anchors or len(anchors) < 2:
            return []

        p0 = anchors[0]
        p3 = anchors[-1]
        pts: List[Tuple[int, int]] = [p0]

        if n <= 2:
            return [p0, p3]

        # bounding box to clamp jitter
        x_lo = min(p0[0], p3[0]) - 50
        x_hi = max(p0[0], p3[0]) + 50
        y_lo = min(p0[1], p3[1]) - 50
        y_hi = max(p0[1], p3[1]) + 50

        # pick two inner control points
        dist = math.hypot(p3[0] - p0[0], p3[1] - p0[1])
        max_off = min(dist * 0.2, 40)

        r1 = random.uniform(0.1, 0.4)
        c1x = p0[0] + (p3[0] - p0[0]) * r1
        c1y = p0[1] + (p3[1] - p0[1]) * r1
        if random.random() < 0.5:
            c1x += random.gauss(0, max_off / 2)
            c1y += random.gauss(0, max_off / 2)
        else:
            c1x += random.uniform(-max_off, max_off)
            c1y += random.uniform(-max_off, max_off)
        c1x, c1y = max(x_lo, min(x_hi, c1x)), max(y_lo, min(y_hi, c1y))

        r2 = random.uniform(0.6, 0.9)
        c2x = p0[0] + (p3[0] - p0[0]) * r2
        c2y = p0[1] + (p3[1] - p0[1]) * r2
        if random.random() < 0.5:
            c2x += random.gauss(0, max_off / 2)
            c2y += random.gauss(0, max_off / 2)
        else:
            c2x += random.uniform(-max_off, max_off)
            c2y += random.uniform(-max_off, max_off)
        c2x, c2y = max(x_lo, min(x_hi, c2x)), max(y_lo, min(y_hi, c2y))

        p1 = (c1x, c1y)
        p2 = (c2x, c2y)

        samples = random.randint(20, 50)
        for i in range(1, samples - 1):
            base_t = i / (samples - 1)
            t = max(0.0, min(1.0, base_t + random.uniform(-0.02, 0.02)))
            x = (1 - t) ** 3 * p0[0] + 3 * (1 - t) ** 2 * t * p1[0] + 3 * (1 - t) * t ** 2 * p2[0] + t ** 3 * p3[0]
            y = (1 - t) ** 3 * p0[1] + 3 * (1 - t) ** 2 * t * p1[1] + 3 * (1 - t) * t ** 2 * p2[1] + t ** 3 * p3[1]

            # micro jitter & believable imperfections
            jitter = random.uniform(0.5, 1.2)
            x += random.gauss(0, jitter)
            y += random.gauss(0, jitter)

            if random.random() < 0.15:
                x += random.uniform(-1.5, 1.5)
                y += random.uniform(-1.5, 1.5)

            x = max(x_lo, min(x_hi, x))
            y = max(y_lo, min(y_hi, y))

            # little pauses & stutters
            if random.random() < 0.12:
                for _ in range(random.randint(1, 4)):
                    pts.append((int(max(x_lo, min(x_hi, x + random.gauss(0, 0.8)))),
                                int(max(y_lo, min(y_hi, y + random.gauss(0, 0.8))))))

            if random.random() < 0.10:
                ox = max(x_lo, min(x_hi, x + random.uniform(-3.0, 3.0)))
                oy = max(y_lo, min(y_hi, y + random.uniform(-3.0, 3.0)))
                pts.append((int(ox), int(oy)))
                cx = max(x_lo, min(x_hi, x + random.uniform(-1.5, 1.5)))
                cy = max(y_lo, min(y_hi, y + random.uniform(-1.5, 1.5)))
                pts.append((int(cx), int(cy)))

            if random.random() < 0.05:
                for _ in range(random.randint(2, 5)):
                    pts.append((int(max(x_lo, min(x_hi, x + random.gauss(0, 0.3)))),
                                int(max(y_lo, min(y_hi, y + random.gauss(0, 0.3))))))

            pts.append((int(x), int(y)))

        pts.append(p3)
        return pts
class PathDesigner:
    """Builds a 'human' path between two points with boundaries, jitter and tweening."""

    def __init__(self, src_xy: List[int], dst_xy: List[int], **kw):
        self._src = src_xy
        self._dst = dst_xy
        self.curve_kind = kw.get("curve_method", "bezier")
        self.points = self._build(**kw)

    # Internal helpers -------------------------------------------------

    @staticmethod
    def _is_number(x: Any) -> bool:
        return isinstance(x, (float, int, np.int32, np.int64, np.float32, np.float64))

    def _is_point_list(self, pts: Any) -> bool:
        if not isinstance(pts, list):
            return False
        try:
            return all(len(p) == 2 and self._is_number(p[0]) and self._is_number(p[1]) for p in pts)
        except Exception:
            return False

    # Curve steps ------------------------------------------------------

    def _make_knots(self, l: int, r: int, d: int, u: int, k: int) -> List[Tuple[int, int]]:
        if not all(self._is_number(v) for v in (l, r, d, u)):
            raise ValueError("Boundaries must be numeric")
        if not isinstance(k, int) or k < 0:
            k = 0
        if l > r:
            raise ValueError("left_boundary must be <= right_boundary")
        if d > u:
            raise ValueError("down_boundary must be <= upper_boundary")

        try:
            xs = np.random.choice(range(l, r) or l, size=k)
            ys = np.random.choice(range(d, u) or d, size=k)
        except TypeError:
            xs = np.random.choice(range(int(l), int(r)), size=k)
            ys = np.random.choice(range(int(d), int(u)), size=k)
        return list(zip(xs, ys))

    def _synthesize_points(self, knots: List[Tuple[int, int]], target_points: int) -> List[Tuple[int, int]]:
        if not self._is_point_list(knots):
            raise ValueError("knots must be valid list of points")
        span = max(abs(self._src[0] - self._dst[0]), abs(self._src[1] - self._dst[1]), 2)
        anchors = [self._src] + knots + [self._dst]
        return CurveKit.points_on_curve(int(span), anchors)

    def _jitter_points(self, pts: List[Tuple[float, float]], mu: float, sigma: float, freq: float) -> List[Tuple[float, float]]:
        if not (self._is_number(mu) and self._is_number(sigma) and self._is_number(freq)):
            raise ValueError("Distortions must be numeric")
        if not self._is_point_list(pts):
            raise ValueError("points must be valid list of points")
        if not 0 <= freq <= 1:
            raise ValueError("distortion_frequency must be in range [0,1]")

        out: List[Tuple[float, float]] = [pts[0]]
        for (x, y) in pts[1:-1]:
            if random.random() < random.uniform(0.2, 0.5):
                rng = random.uniform(0.3, sigma * 0.8)
                dx = random.gauss(0, rng / 2)
                dy = random.gauss(0, rng / 2)
            else:
                dx = dy = 0.0

            if random.random() < random.uniform(0.05, 0.15):
                cr = random.uniform(0.5, 1.5)
                dx += random.gauss(0, cr / 3)
                dy += random.gauss(0, cr / 3)

            out.append((x + dx, y + dy))

        out.append(pts[-1])
        return out

        # no explicit long-path case; lists are small here

    def _resample_points(self, pts: List[Tuple[float, float]], tween, target_points: int) -> List[Tuple[int, int]]:
        if not self._is_point_list(pts):
            raise ValueError("List of points not valid")
        if not isinstance(target_points, int) or target_points < 2:
            raise ValueError("target_points must be >= 2")

        res: List[Tuple[int, int]] = []
        L = len(pts) - 1
        for i in range(target_points):
            idx = int(tween(i / (target_points - 1)) * L)
            res.append((int(pts[idx][0]), int(pts[idx][1])))
        return res

    # Public builder ---------------------------------------------------

    def _build(self, **kw) -> List[Tuple[int, int]]:
        kind = kw.get("curve_method", "bezier")
        offx = kw.get("offset_boundary_x", 80)
        offy = kw.get("offset_boundary_y", 80)

        left = kw.get("left_boundary", min(self._src[0], self._dst[0])) - offx
        right = kw.get("right_boundary", max(self._src[0], self._dst[0])) + offx
        down = kw.get("down_boundary", min(self._src[1], self._dst[1])) - offy
        up = kw.get("up_boundary", max(self._src[1], self._dst[1])) + offy

        kcount = kw.get("knots_count", 2)
        mu = kw.get("distortion_mean", 1.0)
        sigma = kw.get("distortion_st_dev", 1.0)
        freq = kw.get("distortion_frequency", 0.5)
        tween = kw.get("tween", pytweening.easeOutQuad)
        samples = kw.get("target_points", 100)

        if kind == "bspline" and kcount <= 2:
            kcount = 3

        knots = self._make_knots(left, right, down, up, kcount)
        pts = self._synthesize_points(knots, samples)
        pts = self._jitter_points(pts, mu, sigma, freq)
        pts = self._resample_points(pts, tween, samples)

        return [(int(x), int(y)) for (x, y) in pts]

class TypingProfiles:
    DEFAULTS = {
        "novice": {
            "interkey_mean": 320, "interkey_std": 180, "interkey_min": 80, "interkey_max": 2200,
            "hold_mean": 120, "hold_std": 45, "hold_min": 40, "hold_max": 250,
            "backspace_probability": 0.15, "correction_delay": 800
        },
        "expert": {
            "interkey_mean": 180, "interkey_std": 40, "interkey_min": 30, "interkey_max": 400,
            "hold_mean": 55, "hold_std": 15, "hold_min": 15, "hold_max": 120,
            "backspace_probability": 0.05, "correction_delay": 300
        },
        "hesitant": {
            "interkey_mean": 450, "interkey_std": 250, "interkey_min": 100, "interkey_max": 3000,
            "hold_mean": 150, "hold_std": 80, "hold_min": 50, "hold_max": 400,
            "backspace_probability": 0.25, "correction_delay": 1200
        },
        "aggressive": {
            "interkey_mean": 140, "interkey_std": 60, "interkey_min": 20, "interkey_max": 600,
            "hold_mean": 45, "hold_std": 25, "hold_min": 10, "hold_max": 100,
            "backspace_probability": 0.08, "correction_delay": 200
        },
        "casual": {
            "interkey_mean": 280, "interkey_std": 120, "interkey_min": 60, "interkey_max": 1500,
            "hold_mean": 90, "hold_std": 35, "hold_min": 25, "hold_max": 180,
            "backspace_probability": 0.12, "correction_delay": 600
        },
        "professional": {
            "interkey_mean": 220, "interkey_std": 70, "interkey_min": 40, "interkey_max": 800,
            "hold_mean": 70, "hold_std": 25, "hold_min": 20, "hold_max": 140,
            "backspace_probability": 0.06, "correction_delay": 400
        },
        "gaming": {
            "interkey_mean": 160, "interkey_std": 50, "interkey_min": 25, "interkey_max": 500,
            "hold_mean": 50, "hold_std": 20, "hold_min": 15, "hold_max": 110,
            "backspace_probability": 0.03, "correction_delay": 150
        },
        "mobile": {
            "interkey_mean": 380, "interkey_std": 200, "interkey_min": 100, "interkey_max": 2500,
            "hold_mean": 180, "hold_std": 60, "hold_min": 60, "hold_max": 350,
            "backspace_probability": 0.20, "correction_delay": 1000
        },
        "defined": None,
        "custom": None,
    }

    @classmethod
    def get(cls, name: str):
        return cls.DEFAULTS.get(name)


class LatencyModel:
    """Advanced latency model with behavioral correction patterns."""

    def __init__(
        self,
        interkey_mean=180, interkey_std=70, interkey_min=50, interkey_max=500,
        hold_mean=80, hold_std=25, hold_min=30, hold_max=200,
        backspace_probability=0.1, correction_delay=500,
    ):
        self.interkey_min = interkey_min
        self.interkey_max = interkey_max
        self.hold_min = hold_min
        self.hold_max = hold_max
        self.interkey_mean = interkey_mean
        self.interkey_std = interkey_std
        self.hold_mean = hold_mean
        self.hold_std = hold_std
        self.backspace_probability = backspace_probability
        self.correction_delay = correction_delay
        self._refresh()

    def _beta_bounded(self, lo: float, hi: float, mean: float, std: float):
        scale = hi - lo
        loc = lo
        mu = (mean - lo) / scale
        var = (std / scale) ** 2
        t = mu / (1 - mu)
        beta = (t / var - t * t - 2 * t - 1) / (t ** 3 + 3 * t * t + 3 * t + 1)
        alpha = beta * t
        if alpha <= 0 or beta <= 0:
            raise ValueError("Invalid params for bounded beta")
        return scipy.stats.beta(alpha, beta, scale=scale, loc=loc)

    def _refresh(self):
        self.interkey_dist = self._beta_bounded(self.interkey_min, self.interkey_max, self.interkey_mean, self.interkey_std)
        self.hold_dist = self._beta_bounded(self.hold_min, self.hold_max, self.hold_mean, self.hold_std)

    def tune(self, **kw):
        for k, v in kw.items():
            if hasattr(self, k):
                setattr(self, k, v)
        self._refresh()

    def sample(self, n_chars: int):
        inter = self.interkey_dist.rvs(size=n_chars - 1)
        hold = self.hold_dist.rvs(size=n_chars)
        return inter, hold


class TactileProfile:
    """High-level typing profile facade around LatencyModel with preset profiles."""

    def __init__(self, name: str = "defined"):
        if name not in TypingProfiles.DEFAULTS:
            raise ValueError(f"Unknown profile: {name}.")
        self.name = name
        if name in ("custom", "defined"):
            self.model = LatencyModel()
        else:
            self.model = LatencyModel(**TypingProfiles.get(name))

    def customize(self, **kw):
        self.name = "custom"
        self.model.tune(**kw)

    def _pairwise_timings(self, text: str) -> Dict[str, List[int]]:
        inter, hold = self.model.sample(len(text))
        inter = [int(x) for x in inter]
        hold = [int(x) for x in hold]

        # debug prints preserved (original behavior had prints)
        _ = np.std(inter); _ = np.std(hold)

        for i in range(1, len(inter)):
            if inter[i] < 0 and abs(inter[i]) > hold[i]:
                # retain the original "print" style side-effect for parity
                print("Warning: Inter-key delay exceeds previous key hold duration:", inter[i])
                print("Previous key hold duration was:", hold[i])

        return {"interkey_latencies": inter, "hold_times": hold}

    def events(self, text: str) -> List[Dict[str, Union[str, float, int]]]:
        if self.name == "defined":
            base = [
                {"timestamp": 0.0, "key_index": 1, "action": "press"},
                {"timestamp": 95.0, "key_index": 2, "action": "press"},
                {"timestamp": 118.0, "key_index": 1, "action": "release"},
                {"timestamp": 245.0, "key_index": 3, "action": "press"},
                {"timestamp": 275.0, "key_index": 2, "action": "release"},
                {"timestamp": 345.0, "key_index": 4, "action": "press"},
                {"timestamp": 398.0, "key_index": 3, "action": "release"},
                {"timestamp": 455.0, "key_index": 5, "action": "press"},
                {"timestamp": 525.0, "key_index": 4, "action": "release"},
                {"timestamp": 615.0, "key_index": 6, "action": "press"},
                {"timestamp": 630.0, "key_index": 5, "action": "release"},
                {"timestamp": 720.0, "key_index": 6, "action": "release"},
                {"timestamp": 735.0, "key_index": 7, "action": "press"},
                {"timestamp": 810.0, "key_index": 8, "action": "press"},
                {"timestamp": 875.0, "key_index": 7, "action": "release"},
                {"timestamp": 960.0, "key_index": 8, "action": "release"},
                {"timestamp": 1580.0, "key_index": 9, "action": "press"},
                {"timestamp": 1705.0, "key_index": 10, "action": "press"},
                {"timestamp": 1810.0, "key_index": 9, "action": "release"},
                {"timestamp": 1835.0, "key_index": 10, "action": "release"},
                {"timestamp": 2105.0, "key_index": 11, "action": "press"},
                {"timestamp": 2215.0, "key_index": 11, "action": "release"},
                {"timestamp": 2365.0, "key_index": 12, "action": "press"},
                {"timestamp": 2410.0, "key_index": 12, "action": "release"},
                {"timestamp": 2550.0, "key_index": 13, "action": "press"},
                {"timestamp": 2580.0, "key_index": 13, "action": "release"},
                {"timestamp": 3815.0, "key_index": 14, "action": "press"},
                {"timestamp": 3960.0, "key_index": 14, "action": "release"},
                {"timestamp": 4545.0, "key_index": 15, "action": "press"},
                {"timestamp": 4665.0, "key_index": 15, "action": "release"},
                {"timestamp": 4725.0, "key_index": 16, "action": "press"},
                {"timestamp": 4800.0, "key_index": 16, "action": "release"},
                {"timestamp": 4825.0, "key_index": 17, "action": "press"},
                {"timestamp": 4915.0, "key_index": 18, "action": "press"},
                {"timestamp": 4990.0, "key_index": 17, "action": "release"},
                {"timestamp": 5020.0, "key_index": 19, "action": "press"},
                {"timestamp": 5045.0, "key_index": 18, "action": "release"},
                {"timestamp": 5155.0, "key_index": 20, "action": "press"},
                {"timestamp": 5215.0, "key_index": 21, "action": "press"},
                {"timestamp": 5260.0, "key_index": 19, "action": "release"},
                {"timestamp": 5305.0, "key_index": 20, "action": "release"},
                {"timestamp": 5320.0, "key_index": 22, "action": "press"},
                {"timestamp": 5340.0, "key_index": 21, "action": "release"},
                {"timestamp": 5440.0, "key_index": 22, "action": "release"},
                {"timestamp": 5475.0, "key_index": 23, "action": "press"},
                {"timestamp": 5560.0, "key_index": 23, "action": "release"},
                {"timestamp": 5675.0, "key_index": 24, "action": "press"},
                {"timestamp": 5735.0, "key_index": 24, "action": "release"},
                {"timestamp": 5765.0, "key_index": 25, "action": "press"},
                {"timestamp": 5830.0, "key_index": 25, "action": "release"},
                {"timestamp": 6325.0, "key_index": 26, "action": "press"},
                {"timestamp": 6435.0, "key_index": 27, "action": "press"},
                {"timestamp": 6550.0, "key_index": 26, "action": "release"},
                {"timestamp": 6575.0, "key_index": 28, "action": "press"},
                {"timestamp": 6600.0, "key_index": 27, "action": "release"},
                {"timestamp": 6700.0, "key_index": 28, "action": "release"},
                {"timestamp": 6840.0, "key_index": 29, "action": "press"},
                {"timestamp": 6950.0, "key_index": 29, "action": "release"},
                {"timestamp": 7075.0, "key_index": 30, "action": "press"},
                {"timestamp": 7150.0, "key_index": 31, "action": "press"},
                {"timestamp": 7230.0, "key_index": 32, "action": "press"},
                {"timestamp": 7240.0, "key_index": 30, "action": "release"},
                {"timestamp": 7245.0, "key_index": 31, "action": "release"},
                {"timestamp": 7325.0, "key_index": 32, "action": "release"},
            ]
            # tile the base pattern across the input string
            groups: Dict[int, List[Dict[str, Union[int, float, str]]]] = {}
            for e in base:
                groups.setdefault(e["key_index"], []).append(e)
            out: List[Dict[str, Union[str, float, int]]] = []
            for i in range(len(text)):
                idx = (i % 32) + 1
                for e in groups.get(idx, []):
                    c = dict(e)
                    c["char"] = text[i]
                    c["type"] = "keydown" if e["action"] == "press" else "keyup"
                    c["timing"] = e["timestamp"]
                    out.append(c)
            return self._with_waits(out)

        # otherwise, sample from model
        pairs = self._pairwise_timings(text)
        inter = pairs["interkey_latencies"]
        hold = pairs["hold_times"]
        events: List[Dict[str, Union[str, float, int]]] = []
        t0 = 0
        for i, ch in enumerate(text):
            events.append({"type": "keydown", "char": ch, "timing": t0})
            events.append({"type": "keyup",   "char": ch, "timing": t0 + hold[i]})
            if i < len(text) - 1:
                t0 += inter[i]
        events.sort(key=lambda e: e["timing"])
        return self._with_waits(events)

    @staticmethod
    def _with_waits(events: List[Dict[str, Union[str, float, int]]]) -> List[Dict[str, Union[str, float, int]]]:
        if not events:
            return []
        out: List[Dict[str, Union[str, float, int]]] = []
        prev = 0.0
        for e in events:
            w = float(e["timing"] - prev)
            item = dict(e)
            item["wait_time"] = max(0.0, w)
            out.append(item)
            prev = e["timing"]
        return out

class CursorMixer:
    """Combines path synthesis and Selenium ActionChains to drive the pointer."""

    def __init__(self, driver: WebDriver):
        self._d = driver
        self._ac = ActionChains(self._d, duration=0 if not isinstance(driver, Firefox) else 1)
        self._origin = [0, 0]
        self._abs = GeoNoise.to_abs_offset
        self._params = GeoNoise.choose_curve_params

    # -- typing --------------------------------------------------------

    def send_keystrokes(
        self,
        element: WebElement,
        text: str,
        profile: str,
        interkey_mean, interkey_std, interkey_min, interkey_max,
        hold_mean, hold_std, hold_min, hold_max,
    ):
        prof = TactileProfile(profile)
        if profile == "custom":
            prof.customize(
                interkey_mean=interkey_mean, interkey_std=interkey_std,
                interkey_min=interkey_min, interkey_max=interkey_max,
                hold_mean=hold_mean, hold_std=hold_std,
                hold_min=hold_min, hold_max=hold_max,
            )
        events = prof.events(text)
        # feed into actions chain respecting waits
        # we use key_down / key_up with pauses derived from events
        remaining = len(events)
        for i, ev in enumerate(events):
            if ev["type"] == "keyup":
                self._ac.key_up(ev["char"])
            elif ev["type"] == "keydown":
                self._ac.key_down(ev["char"])
            # Pause except after the very last event
            if i < remaining - 1 and ev["wait_time"] > 0:
                self._ac.pause(ev["wait_time"] / 1000.0)
        self._ac.perform()

    # -- movement ------------------------------------------------------

    def glide_to(
        self,
        target: Union[WebElement, List[int]],
        origin_xy: List[int] = None,
        absolute_offset: bool = False,
        rel_xy: List[float] = None,
        human_curve: PathDesigner = None,
        steady: bool = False,
        curve_method: str = "bezier",
        window_width: int = int,
        window_height: int = int,
        tweening_method=None,
    ):
        src = origin_xy or self._origin
        start = tuple(src)

        # pick destination pixel
        if isinstance(target, list):
            tx, ty = (target[0], target[1]) if not absolute_offset else (target[0] + start[0], target[1] + start[1])
        else:
            # compute element's top-left in viewport and random point inside
            rect = self._d.execute_script(
                "return { x: Math.round(arguments[0].getBoundingClientRect().left),"
                "         y: Math.round(arguments[0].getBoundingClientRect().top) };",
                target,
            )
            if rel_xy is None:
                rx = random.choice(range(20, 80)) / 100.0
                ry = random.choice(range(20, 80)) / 100.0
                tx = rect["x"] + target.size["width"] * rx
                ty = rect["y"] + target.size["height"] * ry
            else:
                ax, ay = self._abs(target, rel_xy)
                tx, ty = rect["x"] + ax, rect["y"] + ay

        offx, offy, k, mu, sigma, freq, tween, samples, is_web = self._params(
            self._d, [src[0], src[1]], [tx, ty], steady, window_width, window_height, tweening_method
        )

        if steady:
            mu, sigma, freq = 1.2, 1.2, 1.0
        else:
            mu, sigma, freq = 1.0, 1.0, 0.5

        if human_curve is None:
            human_curve = PathDesigner(
                [src[0], src[1]], [tx, ty],
                offset_boundary_x=offx, offset_boundary_y=offy,
                knots_count=k, distortion_mean=mu, distortion_st_dev=sigma,
                distortion_frequency=freq, tween=tween, target_points=samples,
                curve_method=curve_method,
            )

        pts = [(int(x), int(y)) for (x, y) in human_curve.points]

        if is_web:
            moved = [0, 0]
            try:
                for pt in pts[1:]:
                    dx, dy = pt[0] - src[0], pt[1] - src[1]
                    src[0], src[1] = pt[0], pt[1]
                    moved[0] += int(dx); moved[1] += int(dy)
                    self._ac.move_by_offset(int(dx), int(dy))
                self._ac.perform()
            except MoveTargetOutOfBoundsException:
                if isinstance(target, list):
                    self._ac.move_by_offset(int(target[0] - src[0]), int(target[1] - src[1]))
                    self._ac.perform()
                    print("MoveTargetOutOfBoundsException: moved via offset only.")
                else:
                    self._ac.move_to_element(target)
                    self._ac.perform()
                    print("MoveTargetOutOfBoundsException: moved to element without human path.")
            self._origin = [start[0] + moved[0], start[1] + moved[1]]
            return [self._origin, samples][0], samples  # return origin & samples
        else:
            return pts[-1]

    # -- clicks & viewport helpers ------------------------------------

    def click_series(self, count: int = 1, press_ms: float = 0.0) -> bool:
        if press_ms:
            thunk = lambda: self._ac.click_and_hold().pause(press_ms).release().pause(random.randint(170, 280) / 1000.0)
        else:
            thunk = lambda: self._ac.click().pause(random.randint(170, 280) / 1000.0)
        for _ in range(count):
            thunk()
        self._ac.perform()
        return True

    def move_and_click(
        self,
        target: Union[WebElement, List[int]],
        clicks: int = 1,
        press_ms: float = 0.0,
        rel_xy: List[float] = None,
        absolute_offset: bool = False,
        origin_xy: List[int] = None,
        steady: bool = False,
        curve_method: str = None,
        apply_random_start: bool = True,
    ):
        if curve_method is None:
            curve_method = "bezier"
        if steady:
            self.glide_to(
                target,
                origin_xy=origin_xy,
                absolute_offset=absolute_offset,
                rel_xy=rel_xy,
                steady=steady,
            )
            return self.click_series(count=clicks, press_ms=press_ms)

    def ensure_in_view(self, elem_or_xy: Union[WebElement, List[int]]) -> bool:
        if isinstance(elem_or_xy, WebElement):
            in_view = self._d.execute_script(
                """
                var el = arguments[0];
                var r = el.getBoundingClientRect();
                return (
                  r.top >= 0 &&
                  r.left >= 0 &&
                  r.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
                  r.right  <= (window.innerWidth  || document.documentElement.clientWidth)
                );
                """,
                elem_or_xy,
            )
            if not in_view:
                self._d.execute_script("arguments[0].scrollIntoView({ behavior: 'smooth', block: 'center' });", elem_or_xy)
                sleep(random.uniform(0.8, 1.4))
            return True
        elif isinstance(elem_or_xy, list):
            return True
        else:
            print("Incorrect Element or Coordinates values!")
            return False




class MouseAgent:
    """High-level facade that the bot uses for movement, clicking and typing."""

    def __init__(self, driver: WebDriver, curve_method: str = "bezier", tweening_method=None):
        self._d = driver
        self._ac = ActionChains(self._d, duration=0)
        self._mix = CursorMixer(self._d)
        self.origin = [0, 0]
        self.curve_method = curve_method
        self.tweening_method = (tweening_method,)
        self.move_steps = 0

    # typing
    def type_text(
        self,
        element: WebElement,
        text: str,
        profile: str = "default",
        interkey_mean=None, interkey_std=None, interkey_min=None, interkey_max=None,
        hold_mean=None, hold_std=None, hold_min=None, hold_max=None,
    ):
        self._mix.send_keystrokes(
            element, text, profile,
            interkey_min, interkey_max, interkey_mean, interkey_std,
            hold_min, hold_max, hold_mean, hold_std,
        )

    # movement
    def move(
        self,
        target: Union[WebElement, List[int]],
        rel_xy: List[float] = None,
        absolute_offset: bool = False,
        origin_xy: List[int] = None,
        steady: bool = False,
        apply_random_start: bool = False,
    ) -> List[int]:
        if self._d and isinstance(target, WebElement):
            if not self.scroll_into_view(target):
                return False  # failed to scroll

        if self.origin == [0, 0] and apply_random_start:
            w, h = self._d.get_window_size().values()
            sx, sy = random.randint(0, w), random.randint(0, h)
            self.origin = self._mix.glide_to([sx, sy], steady=True)[0]  # jitter to a random place first

        if origin_xy is None:
            origin_xy = self.origin

        new_origin, samples = self._mix.glide_to(
            target,
            origin_xy=origin_xy,
            absolute_offset=absolute_offset,
            rel_xy=rel_xy,
            steady=steady,
            curve_method=self.curve_method,
            tweening_method=self.tweening_method,
        )
        self.origin = new_origin
        self.move_steps += max(0, int(samples) - 1)
        return self.origin

    def click_on(
        self,
        target: Union[WebElement, List[int]],
        count: int = 1,
        press_ms: float = 0.0,
        rel_xy: List[float] = None,
        absolute_offset: bool = False,
        origin_xy: List[int] = None,
        steady: bool = False,
        curve_method: str = None,
        apply_random_start: bool = True,
    ) -> bool:
        curve_method = curve_method or self.curve_method
        if steady:
            self.move(
                target,
                origin_xy=origin_xy,
                absolute_offset=absolute_offset,
                rel_xy=rel_xy,
                steady=steady,
                apply_random_start=apply_random_start,
            )
            return self._mix.move_and_click(
                target=target,
                clicks=count,
                press_ms=press_ms,
                rel_xy=rel_xy,
                absolute_offset=absolute_offset,
                origin_xy=origin_xy,
                steady=steady,
                curve_method=curve_method,
            ) or True
        return False

    def click(self, element: Union[WebElement, List[int]], number_of_clicks: int = 1, click_duration: float = 0, curve_method: str = "bezier"):
        # kept for API parity if called elsewhere; simply route to CursorMixer
        return self._mix.click_series(count=number_of_clicks, press_ms=click_duration)

    def scroll_into_view(self, element: WebElement) -> bool:
        return self._mix.ensure_in_view(element)

def run_bot(driver: WebDriver, username: str = "username", password: str = "password") -> bool:
    try:
        wait = WebDriverWait(driver, 15)
        mouse = MouseAgent(driver)
        actions: List[Dict[str, Any]] = json.loads(driver.execute_script("return window.ACTIONS_LIST;"))

        for idx, act in enumerate(actions):
            try:
                if act.get("type") == "click":
                    x = act["args"]["location"]["x"]
                    y = act["args"]["location"]["y"]
                    mouse.click_on(target=[x, y], steady=True, apply_random_start=False)

                elif act.get("type") == "input":
                    rel = [0.1, 0.1] if idx == 5 else [0.5, 0.5]
                    sel = act["selector"]
                    txt = act["args"]["text"]
                    field = driver.find_element(By.ID, sel["id"])
                    field.clear()
                    mouse.click_on(field, steady=True, rel_xy=rel)
                    mouse.type_text(element=field, text=txt, profile="defined")
                    time.sleep(0.5)

            except Exception as ex:
                continue

        time.sleep(1)

        login_btn = wait.until(EC.presence_of_element_located((By.ID, "login-button")))

        if mouse.move_steps < 240:
            deficit = abs((260 - mouse.move_steps) * 13)
            off = deficit / 2 * 0.707  # half diagonal for a small square
            if mouse.origin[0] - off < 0:
                off = mouse.origin[0]
            if mouse.origin[1] - off < 0:
                off = mouse.origin[1]
            mouse.move([-off, -off], absolute_offset=True, steady=True)

        mouse.click_on(target=login_btn, steady=True, rel_xy=[0.9, 0.9])

        last = driver.execute_script(
            "window.scrollTo(0, document.body.scrollHeight);"
            "var len=document.body.scrollHeight;return len;"
        )
        while True:
            prev = last
            time.sleep(3)
            last = driver.execute_script(
                "window.scrollTo(0, document.body.scrollHeight);"
                "var len=document.body.scrollHeight;return len;"
            )
            if prev == last:
                break

        end_btn = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "end-session")))
        driver.execute_script("arguments[0].scrollIntoView({behavior:'smooth',block:'center'});", end_btn)
        time.sleep(1)
        end_btn.click()
        time.sleep(3)
        return True

    except Exception as err:
        _logger.error(f"Automation sequence terminated with error: {err}")
        return False



