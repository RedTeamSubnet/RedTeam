import json
import logging
import time
import random
import math
from typing import List, Dict
from time import sleep

import numpy as np
import scipy.stats
import pytweening
from selenium.webdriver import Chrome, Firefox, Edge, Safari
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# -----------------------------
# Helpers for Humanization
# -----------------------------
def apply_velocity_profile(points, tween=pytweening.easeInOutQuad):
    n = len(points)
    new_points = []
    for i in range(n):
        t = i / (n - 1)
        t = tween(t)
        idx = int(t * (n - 1))
        new_points.append(points[idx])
    return new_points


def add_human_jitter(points, intensity=2, pause_chance=0.05):
    jittered = []
    for x, y in points:
        x += random.randint(-intensity, intensity)
        y += random.randint(-intensity, intensity)
        jittered.append((x, y))
        if random.random() < pause_chance:
            jittered.append((x, y))  # simulate hesitation
    return jittered


def random_curve_variant(from_point, to_point, knots):
    """
    Always generate a Bezier curve using provided knots.
    Adds randomness to simulate human arcs.
    """
    n_points = random.randint(60, 150)  # number of points along the curve
    # Insert random midpoints if not enough knots
    if len(knots) < 2:
        mid_x = (from_point[0] + to_point[0]) // 2
        mid_y = (from_point[1] + to_point[1]) // 2 + random.randint(-50, 50)
        knots.append((mid_x, mid_y))
    full_points = [from_point] + knots + [to_point]
    return BezierCalculator.calculate_points_in_curve(n_points, full_points)


# -----------------------------
# Bezier Calculator
# -----------------------------
class BezierCalculator:
    @staticmethod
    def binomial(n, k):
        return math.factorial(n) / (math.factorial(k) * math.factorial(n - k))

    @staticmethod
    def bernstein_polynomial_point(x, i, n):
        return BezierCalculator.binomial(n, i) * (x**i) * ((1 - x) ** (n - i))

    @staticmethod
    def bernstein_polynomial(points):
        def bernstein(t):
            n = len(points) - 1
            x = y = 0
            for i, p in enumerate(points):
                bern = BezierCalculator.bernstein_polynomial_point(t, i, n)
                x += p[0] * bern
                y += p[1] * bern
            return x, y

        return bernstein

    @staticmethod
    def calculate_points_in_curve(n, points):
        curve_points = []
        bernstein_poly = BezierCalculator.bernstein_polynomial(points)
        for i in range(n):
            t = i / (n - 1)
            curve_points.append(bernstein_poly(t))
        return curve_points


# -----------------------------
# Calculate and Randomize
# -----------------------------
class CalculateAndRandomize:
    @staticmethod
    def generate_random_curve_parameters(
        driver,
        pre_origin,
        post_destination,
        steady,
        window_width=1920,
        window_height=1080,
        tweening_method=None,
    ):
        isWeb = isinstance(driver, (Chrome, Firefox, Edge, Safari))
        if isWeb:
            window_width, window_height = driver.get_window_size().values()

        offset_boundary_x = random.randint(20, 100)
        offset_boundary_y = random.randint(20, 100)
        knots_count = 2 if not steady else 3
        tween = tweening_method or pytweening.easeInOutCubic
        x1, y1 = pre_origin
        x2, y2 = post_destination
        distance = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
        pxl_2_distance = max(1, distance // 13)
        target_points = int(distance // pxl_2_distance)
        return (offset_boundary_x, offset_boundary_y, knots_count, tween, target_points)


# -----------------------------
# Humanize Mouse Trajectory
# -----------------------------
class HumanizeMouseTrajectory:
    def __init__(self, from_point, to_point, **kwargs):
        self.from_point = from_point
        self.to_point = to_point
        self.points = self.generate_curve(**kwargs)

    def generate_curve(self, **kwargs):
        offset_boundary_x = kwargs.get("offset_boundary_x", 80)
        offset_boundary_y = kwargs.get("offset_boundary_y", 80)
        knots_count = kwargs.get("knots_count", 2)
        tween = kwargs.get("tween", pytweening.easeOutQuad)
        target_points = kwargs.get("target_points", 100)
        knots = [
            (random.randint(0, offset_boundary_x), random.randint(0, offset_boundary_y))
            for _ in range(knots_count)
        ]
        raw_points = random_curve_variant(self.from_point, self.to_point, knots)
        curved = apply_velocity_profile(raw_points, tween)
        distorted = add_human_jitter(curved, intensity=2, pause_chance=0.07)
        return [(int(x), int(y)) for x, y in distorted]


# -----------------------------
# Typing Metrics
# -----------------------------
class TypingMetrics:
    def __init__(
        self,
        interkey_mean=180,
        interkey_std=70,
        interkey_min=50,
        interkey_max=500,
        hold_mean=80,
        hold_std=25,
        hold_min=30,
        hold_max=200,
    ):
        self.interkey_mean, self.interkey_std, self.interkey_min, self.interkey_max = (
            interkey_mean,
            interkey_std,
            interkey_min,
            interkey_max,
        )
        self.hold_mean, self.hold_std, self.hold_min, self.hold_max = (
            hold_mean,
            hold_std,
            hold_min,
            hold_max,
        )
        self._create_distributions()

    def _create_bounded_distribution(self, min_val, max_val, mean, std):
        scale = max_val - min_val
        location = min_val
        unscaled_mean = (mean - min_val) / scale
        unscaled_var = (std / scale) ** 2
        t = unscaled_mean / (1 - unscaled_mean + 1e-9)
        beta = ((t / unscaled_var) - (t**2) - (2 * t) - 1) / (
            (t**3) + (3 * t**2) + (3 * t) + 1
        )
        alpha = beta * t
        alpha = max(alpha, 0.1)
        beta = max(beta, 0.1)
        return scipy.stats.beta(alpha, beta, scale=scale, loc=location)

    def _create_distributions(self):
        self.interkey_dist = self._create_bounded_distribution(
            self.interkey_min, self.interkey_max, self.interkey_mean, self.interkey_std
        )
        self.hold_dist = self._create_bounded_distribution(
            self.hold_min, self.hold_max, self.hold_mean, self.hold_std
        )

    def generate_patterns(self, text_length):
        interkey_latencies = self.interkey_dist.rvs(size=text_length - 1)
        hold_times = self.hold_dist.rvs(size=text_length)
        return [int(x) for x in interkey_latencies], [int(x) for x in hold_times]


class KeyboardProfile:
    DEFAULTS = {
        "default": {
            "interkey_mean": 254,
            "interkey_std": 224,
            "interkey_min": 1,
            "interkey_max": 1700,
            "hold_mean": 77,
            "hold_std": 36,
            "hold_min": 24,
            "hold_max": 175,
        },
        "slow": {
            "interkey_mean": 300,
            "interkey_std": 150,
            "interkey_min": 50,
            "interkey_max": 2000,
            "hold_mean": 100,
            "hold_std": 50,
            "hold_min": 30,
            "hold_max": 200,
        },
    }

    def __init__(self, profile_name="default"):
        params = self.DEFAULTS.get(profile_name, None)
        self.metrics = TypingMetrics(**params) if params else TypingMetrics()

    def generate_events_with_time_intervals(self, text: str) -> List[Dict]:
        interkey, hold = self.metrics.generate_patterns(len(text))
        events, current_time = [], 0
        for idx, char in enumerate(text):
            events.append({"type": "keydown", "char": char, "timing": current_time})
            events.append(
                {"type": "keyup", "char": char, "timing": current_time + hold[idx]}
            )
            if idx < len(text) - 1:
                current_time += interkey[idx]
        prev_time = 0
        for e in events:
            e["wait_time"] = float(max(0, e["timing"] - prev_time))
            prev_time = e["timing"]
        return events


# -----------------------------
# Adjuster and WebCursor
# -----------------------------
class Adjuster:
    def __init__(self, driver):
        self.driver = driver
        self.action = ActionChains(driver)
        self.origin_coordinate = [0, 0]

    def type_text(self, text, profile="default", typo_chance=0.2):
        """
        Type text with optional random typos.
        typo_chance: probability of making a typo per key press (0-1)
        """
        keyboard_profile = KeyboardProfile(profile)
        events = keyboard_profile.generate_events_with_time_intervals(text)

        for e in events:
            if e["type"] == "keydown":
                # Introduce random typo
                if random.random() < typo_chance:
                    wrong_char = random.choice("abcdefghijklmnopqrstuvwxyz")
                    self.action.key_down(wrong_char).key_up(wrong_char).pause(
                        random.uniform(0.05, 0.2)
                    )
                    # Backspace to correct typo
                    self.action.key_down("\\ue003").key_up("\\ue003").pause(
                        random.uniform(0.05, 0.15)
                    )

                self.action.key_down(e["char"])
            else:
                self.action.key_up(e["char"])

            self.action.pause(e["wait_time"] / 1000)

        self.action.perform()

    def move_to(
        self,
        element_or_pos,
        absolute_offset=False,
        relative_position=None,
        steady=False,
    ):
        origin = self.origin_coordinate[:]
        if isinstance(element_or_pos, list):
            x, y = (
                element_or_pos
                if not absolute_offset
                else [element_or_pos[0] + origin[0], element_or_pos[1] + origin[1]]
            )
        else:
            dest = self.driver.execute_script(
                "return arguments[0].getBoundingClientRect();", element_or_pos
            )
            x_off = element_or_pos.size["width"] * (
                relative_position[0] if relative_position else 0.5
            )
            y_off = element_or_pos.size["height"] * (
                relative_position[1] if relative_position else 0.5
            )
            x, y = dest["x"] + x_off, dest["y"] + y_off

        params = CalculateAndRandomize.generate_random_curve_parameters(
            self.driver, origin, [x, y], steady
        )
        human_curve = HumanizeMouseTrajectory(
            origin,
            [x, y],
            offset_boundary_x=params[0],
            offset_boundary_y=params[1],
            knots_count=params[2],
            tween=params[3],
            target_points=params[4],
        )
        total_offset = [0, 0]
        window = self.driver.get_window_size()
        max_x, max_y = window["width"] - 1, window["height"] - 1
        safe_points = [
            (max(0, min(px, max_x)), max(0, min(py, max_y)))
            for px, py in human_curve.points
        ]

        for px, py in safe_points[1:]:
            dx, dy = px - origin[0], py - origin[1]
            try:
                self.action.move_by_offset(dx, dy)
            except:
                continue
            origin = [px, py]
            total_offset[0] += dx
            total_offset[1] += dy
            self.action.pause(random.uniform(0.005, 0.03))

        self.action.perform()
        self.origin_coordinate = [
            self.origin_coordinate[0] + total_offset[0],
            self.origin_coordinate[1] + total_offset[1],
        ]
        return self.origin_coordinate


class WebCursor:
    def __init__(self, driver):
        self.driver = driver
        self.human = Adjuster(driver)

    def move_to(
        self,
        element_or_pos,
        relative_position=None,
        absolute_offset=False,
        steady=False,
    ):
        return self.human.move_to(
            element_or_pos, absolute_offset, relative_position, steady
        )

    def click_on(
        self,
        element_or_pos,
        number_of_clicks=1,
        click_duration=0,
        relative_position=None,
        absolute_offset=False,
        steady=False,
    ):
        self.move_to(element_or_pos, relative_position, absolute_offset, steady)
        for _ in range(number_of_clicks):
            if click_duration:
                self.human.action.click_and_hold().pause(click_duration).release()
            else:
                self.human.action.click()
            self.human.action.pause(random.uniform(0.05, 0.25))
        self.human.action.perform()

    def type(self, text, profile="default"):
        self.human.type_text(text, profile)


# -----------------------------
# Bot Runner
# -----------------------------
def run_bot(driver: WebDriver) -> bool:
    try:
        _wait = WebDriverWait(driver, 15)
        _cursor = WebCursor(driver)
        config = json.loads(driver.execute_script("return window.ACTIONS_LIST;"))
        for i, _action in enumerate(config):
            try:
                if _action["type"] == "click":
                    x, y = (
                        _action["args"]["location"]["x"],
                        _action["args"]["location"]["y"],
                    )
                    _cursor.click_on([x, y], steady=True)
                if _action["type"] == "input":
                    field_id = _action["selector"]["id"]
                    text = _action["args"]["text"]
                    input_field = driver.find_element(By.ID, field_id)
                    input_field.clear()
                    _cursor.click_on(
                        input_field, steady=True, relative_position=[0.5, 0.5]
                    )
                    _cursor.type(text, profile="default")
                    sleep(random.uniform(0.4, 0.9))
            except Exception as e:
                logger.error(f"Failed action {i+1}: {e}")
                continue

        sleep(random.uniform(1.0, 3.0))
        login_button = _wait.until(
            EC.presence_of_element_located((By.ID, "login-button"))
        )
        _cursor.move_to(login_button, steady=True)
        _cursor.click_on(login_button)

        last_count = 0
        while True:
            page_len = driver.execute_script("return document.body.scrollHeight")
            if page_len == last_count:
                break
            driver.execute_script("window.scrollTo(0,document.body.scrollHeight);")
            last_count = page_len
            sleep(1)
        end_session = _wait.until(
            EC.presence_of_element_located((By.CLASS_NAME, "end-session"))
        )
        driver.execute_script(
            "arguments[0].scrollIntoView({behavior:'smooth',block:'center'});",
            end_session,
        )
        sleep(1)
        end_session.click()
        sleep(3)
        return True
    except Exception as err:
        logger.error(f"Bot failed: {err}")
        return False
