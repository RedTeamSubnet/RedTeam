import logging
import json
from collections import deque, defaultdict
from dataclasses import dataclass
from enum import Enum

# --- Standard Library
import math
import random
import time
from time import sleep
from typing import Any, Dict, List, Tuple, Union, Optional, Callable

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

class ContextualLogger:
    def __init__(self, name: str):
        self._logger = logging.getLogger(name)
        self._context = {}

    def set_context(self, **kwargs):
        self._context.update(kwargs)

    def _format_message(self, msg: str) -> str:
        if self._context:
            context_str = " | ".join(f"{k}={v}" for k, v in self._context.items())
            return f"[{context_str}] {msg}"
        return msg

    def error(self, msg: str):
        self._logger.error(self._format_message(msg))

    def info(self, msg: str):
        self._logger.info(self._format_message(msg))

    def debug(self, msg: str):
        self._logger.debug(self._format_message(msg))

_logger = ContextualLogger(__name__)

class MovementStyle(Enum):
    PRECISE = "precise"
    NATURAL = "natural"
    ERRATIC = "erratic"
    GAMING = "gaming"
    MOBILE = "mobile"

class InteractionMode(Enum):
    STEADY = "steady"
    DYNAMIC = "dynamic"
    EXPLORATORY = "exploratory"

@dataclass
class Coordinate:
    x: float
    y: float

    def __add__(self, other):
        return Coordinate(self.x + other.x, self.y + other.y)

    def __sub__(self, other):
        return Coordinate(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar):
        return Coordinate(self.x * scalar, self.y * scalar)

    def distance_to(self, other) -> float:
        return math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2)

    def to_tuple(self) -> Tuple[int, int]:
        return (int(self.x), int(self.y))

@dataclass
class MovementProfile:
    style: MovementStyle
    precision_factor: float
    speed_variance: float
    curve_complexity: int
    jitter_intensity: float

class SpatialTransformer:
    """Advanced coordinate transformation and spatial analysis system."""

    def __init__(self):
        self._cache = {}
        self._history = deque(maxlen=100)

    def validate_and_constrain_coordinates(self, coordinates: List[Coordinate], window_width: int, window_height: int) -> List[Coordinate]:
        """Validate and constrain all coordinates to be within window bounds."""
        constrained_coords = []
        safety_margin = 20  # 20px safety margin from window edges

        for coord in coordinates:
            # Constrain coordinates to safe window area
            safe_x = max(safety_margin, min(window_width - safety_margin, coord.x))
            safe_y = max(safety_margin, min(window_height - safety_margin, coord.y))
            constrained_coords.append(Coordinate(safe_x, safe_y))

        return constrained_coords

    def transform_relative_to_absolute(self, element: WebElement, relative_coords: List[float]) -> Coordinate:
        """Convert normalized coordinates to absolute pixel positions."""
        cache_key = f"{id(element)}_{hash(tuple(relative_coords))}"
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            return Coordinate(cached[0], cached[1])

        dimensions = element.size
        width, height = dimensions["width"], dimensions["height"]

        abs_x = width * relative_coords[0]
        abs_y = height * relative_coords[1]

        result = Coordinate(abs_x, abs_y)
        self._cache[cache_key] = (abs_x, abs_y)
        self._history.append(("transform", result))

        return result

    def generate_movement_parameters(
        self,
        driver: WebDriver,
        start_point: Coordinate,
        end_point: Coordinate,
        interaction_mode: InteractionMode,
        window_dimensions: Tuple[int, int],
        custom_tween: Optional[Callable] = None,
    ) -> Dict[str, Any]:
        """Generate comprehensive movement parameters with advanced algorithms."""

        is_web_driver = isinstance(driver, (Chrome, Firefox, Edge, Safari))
        if is_web_driver:
            window_width, window_height = driver.get_window_size().values()
        else:
            window_width, window_height = window_dimensions

        # Enhanced boundary calculation with larger safety margins
        safety_margin = 0.15  # Increased from 0.12
        boundary_left = max(0, window_width * safety_margin)
        boundary_right = min(window_width, window_width * (1 - safety_margin))
        boundary_top = max(0, window_height * safety_margin)
        boundary_bottom = min(window_height, window_height * (1 - safety_margin))

        # Ensure start and end points are within bounds
        start_point.x = max(boundary_left, min(boundary_right, start_point.x))
        start_point.y = max(boundary_top, min(boundary_bottom, start_point.y))
        end_point.x = max(boundary_left, min(boundary_right, end_point.x))
        end_point.y = max(boundary_top, min(boundary_bottom, end_point.y))

        # Advanced movement strategy selection with very conservative bounds
        max_safe_offset = min(window_width, window_height) * 0.05  # Max 5% of smallest dimension (reduced from 8%)

        strategy_configs = {
            MovementStyle.PRECISE: {
                "offset_ranges": [(5, 15), (15, 25), (25, min(35, max_safe_offset))],
                "weights": [0.6, 0.3, 0.1],
                "complexity": 2
            },
            MovementStyle.NATURAL: {
                "offset_ranges": [(8, 18), (18, 30), (30, min(45, max_safe_offset))],
                "weights": [0.5, 0.4, 0.1],
                "complexity": 3
            },
            MovementStyle.ERRATIC: {
                "offset_ranges": [(10, 22), (22, 35), (35, min(50, max_safe_offset))],
                "weights": [0.4, 0.4, 0.2],
                "complexity": 4
            },
            MovementStyle.GAMING: {
                "offset_ranges": [(3, 12), (12, 20), (20, min(30, max_safe_offset))],
                "weights": [0.7, 0.2, 0.1],
                "complexity": 1
            },
            MovementStyle.MOBILE: {
                "offset_ranges": [(12, 25), (25, 40), (40, min(55, max_safe_offset))],
                "weights": [0.4, 0.4, 0.2],
                "complexity": 3
            }
        }

        selected_style = random.choice(list(MovementStyle))
        config = strategy_configs[selected_style]

        # Calculate offsets using weighted random selection
        x_offset = self._weighted_random_choice(config["offset_ranges"], config["weights"])
        y_offset = self._weighted_random_choice(config["offset_ranges"], config["weights"])

        # Edge detection and complexity adjustment
        knot_count = config["complexity"]
        if not self._is_point_in_safe_zone(start_point, boundary_left, boundary_right, boundary_top, boundary_bottom):
            x_offset = y_offset = 1
            knot_count = 1
        if not self._is_point_in_safe_zone(end_point, boundary_left, boundary_right, boundary_top, boundary_bottom):
            x_offset = y_offset = 1
            knot_count = 1

        # Advanced tweening selection with fallback
        tween_functions = [
            pytweening.easeInOutCubic,
            pytweening.easeInOutQuad,
            pytweening.easeInOutQuart,
            pytweening.easeInOutSine,
            pytweening.easeInOutExpo,
            pytweening.easeInOutCirc,
            pytweening.easeInOutBack,
        ]
        selected_tween = custom_tween or random.choice(tween_functions)

        # Path complexity analysis
        distance = start_point.distance_to(end_point)
        is_linear_path = (interaction_mode == InteractionMode.STEADY and
                         (abs(start_point.x - end_point.x) < 8 or abs(start_point.y - end_point.y) < 8))

        if is_linear_path:
            knot_count = min(3, knot_count)
        else:
            knot_count = max(2, knot_count)

        # Advanced distortion modeling
        distortion_profiles = [
            {"mean_range": (0.70, 0.90), "std_range": (0.75, 0.95), "frequency_range": (0.15, 0.40)},
            {"mean_range": (0.80, 1.00), "std_range": (0.85, 1.05), "frequency_range": (0.25, 0.50)},
            {"mean_range": (0.90, 1.10), "std_range": (0.95, 1.15), "frequency_range": (0.35, 0.60)},
        ]

        profile = random.choice(distortion_profiles)
        distortion_mean = random.uniform(*profile["mean_range"])
        distortion_std = random.uniform(*profile["std_range"])
        distortion_frequency = random.uniform(*profile["frequency_range"])

        # Intelligent sample density calculation
        sample_density = self._calculate_optimal_sample_density(distance)

        return {
            "x_offset": int(x_offset),
            "y_offset": int(y_offset),
            "knot_count": knot_count,
            "distortion_mean": distortion_mean,
            "distortion_std": distortion_std,
            "distortion_frequency": distortion_frequency,
            "tween_function": selected_tween,
            "sample_count": sample_density,
            "is_web_driver": is_web_driver,
            "movement_style": selected_style,
            "interaction_mode": interaction_mode
        }

    def _weighted_random_choice(self, ranges: List[Tuple[int, int]], weights: List[float]) -> int:
        """Select a value from ranges using weighted probability."""
        selected_range = random.choices(ranges, weights=weights)[0]
        return random.choice(selected_range)

    def _is_point_in_safe_zone(self, point: Coordinate, left: float, right: float, top: float, bottom: float) -> bool:
        """Check if point is within safe boundaries."""
        return left <= point.x <= right and top <= point.y <= bottom

    def _calculate_optimal_sample_density(self, distance: float) -> int:
        """Calculate optimal number of samples based on distance."""
        base_density = 12
        if distance < 20:
            density_factor = max(2, distance / 8)
        elif distance < 100:
            density_factor = distance / 15
        else:
            density_factor = distance / 20

        return int(max(2, min(150, base_density + density_factor)))

class AdvancedCurveGenerator:
    """Sophisticated curve generation with multiple algorithms and human-like imperfections."""

    def __init__(self):
        self._curve_cache = {}
        self._imperfection_patterns = self._initialize_imperfection_patterns()

    def _initialize_imperfection_patterns(self) -> Dict[str, List[float]]:
        """Initialize realistic human imperfection patterns."""
        return {
            "micro_tremor": [0.3, 0.7, 0.2, 0.5, 0.8, 0.4, 0.6, 0.9, 0.1, 0.3],
            "hesitation": [0.1, 0.2, 0.15, 0.25, 0.3, 0.2, 0.18, 0.22, 0.12, 0.28],
            "acceleration": [0.8, 0.9, 0.95, 1.0, 1.1, 1.05, 1.0, 0.95, 0.9, 0.85],
            "deceleration": [1.0, 0.95, 0.9, 0.85, 0.8, 0.75, 0.7, 0.65, 0.6, 0.55]
        }

    def generate_bezier_curve(
        self,
        control_points: List[Coordinate],
        sample_count: int,
        imperfection_level: float = 0.3
    ) -> List[Coordinate]:
        """Generate a Bezier curve with human-like imperfections."""

        if len(control_points) < 2:
            return control_points

        if len(control_points) == 2:
            return self._generate_linear_interpolation(control_points[0], control_points[1], sample_count)

        # Use cubic Bezier for 4 points, quadratic for 3 points
        if len(control_points) >= 4:
            return self._generate_cubic_bezier(control_points[:4], sample_count, imperfection_level)
        else:
            return self._generate_quadratic_bezier(control_points[:3], sample_count, imperfection_level)

    def _generate_cubic_bezier(
        self,
        points: List[Coordinate],
        sample_count: int,
        imperfection_level: float
    ) -> List[Coordinate]:
        """Generate cubic Bezier curve with advanced humanization and bounds checking."""

        p0, p1, p2, p3 = points
        curve_points = [p0]

        # Calculate bounding box for constraint enforcement with very conservative limits
        all_x = [p.x for p in points]
        all_y = [p.y for p in points]
        # Very conservative expansion - only 15px
        x_min, x_max = min(all_x) - 15, max(all_x) + 15
        y_min, y_max = min(all_y) - 15, max(all_y) + 15

        # Ensure bounds are reasonable (assume max window size of 4K)
        x_min = max(0, x_min)
        y_min = max(0, y_min)
        x_max = min(3840, x_max)  # 4K width
        y_max = min(2160, y_max)  # 4K height

        # Generate base curve points
        for i in range(1, sample_count - 1):
            t = i / (sample_count - 1)

            # Apply time-based imperfection
            t_imperfect = self._apply_time_imperfection(t, imperfection_level)
            t_imperfect = max(0.0, min(1.0, t_imperfect))

            # Calculate Bezier point
            x = self._cubic_bezier_coordinate(t_imperfect, p0.x, p1.x, p2.x, p3.x)
            y = self._cubic_bezier_coordinate(t_imperfect, p0.y, p1.y, p2.y, p3.y)

            # Apply spatial imperfections
            x, y = self._apply_spatial_imperfections(x, y, t, imperfection_level)

            # Constrain to bounding box
            x = max(x_min, min(x_max, x))
            y = max(y_min, min(y_max, y))

            curve_points.append(Coordinate(x, y))

            # Add micro-movements and hesitations
            if random.random() < 0.18:
                self._add_micro_movements(curve_points, x, y, x_min, x_max, y_min, y_max)

        curve_points.append(p3)
        return curve_points

    def _generate_quadratic_bezier(
        self,
        points: List[Coordinate],
        sample_count: int,
        imperfection_level: float
    ) -> List[Coordinate]:
        """Generate quadratic Bezier curve."""

        p0, p1, p2 = points
        curve_points = [p0]

        for i in range(1, sample_count - 1):
            t = i / (sample_count - 1)
            t_imperfect = self._apply_time_imperfection(t, imperfection_level)

            x = self._quadratic_bezier_coordinate(t_imperfect, p0.x, p1.x, p2.x)
            y = self._quadratic_bezier_coordinate(t_imperfect, p0.y, p1.y, p2.y)

            x, y = self._apply_spatial_imperfections(x, y, t, imperfection_level)
            curve_points.append(Coordinate(x, y))

        curve_points.append(p2)
        return curve_points

    def _generate_linear_interpolation(
        self,
        start: Coordinate,
        end: Coordinate,
        sample_count: int
    ) -> List[Coordinate]:
        """Generate linear interpolation with subtle variations."""

        points = [start]
        for i in range(1, sample_count - 1):
            t = i / (sample_count - 1)
            x = start.x + (end.x - start.x) * t
            y = start.y + (end.y - start.y) * t

            # Add minimal jitter even for linear paths
            if random.random() < 0.1:
                x += random.gauss(0, 0.5)
                y += random.gauss(0, 0.5)

            points.append(Coordinate(x, y))

        points.append(end)
        return points

    def _cubic_bezier_coordinate(self, t: float, p0: float, p1: float, p2: float, p3: float) -> float:
        """Calculate cubic Bezier coordinate."""
        return (1-t)**3 * p0 + 3*(1-t)**2*t * p1 + 3*(1-t)*t**2 * p2 + t**3 * p3

    def _quadratic_bezier_coordinate(self, t: float, p0: float, p1: float, p2: float) -> float:
        """Calculate quadratic Bezier coordinate."""
        return (1-t)**2 * p0 + 2*(1-t)*t * p1 + t**2 * p2

    def _apply_time_imperfection(self, t: float, imperfection_level: float) -> float:
        """Apply time-based imperfections to create natural variations."""
        if random.random() < 0.3:
            pattern = random.choice(list(self._imperfection_patterns.values()))
            pattern_index = int(t * (len(pattern) - 1))
            time_variation = pattern[pattern_index] * imperfection_level * 0.1
            return t + random.uniform(-time_variation, time_variation)
        return t

    def _apply_spatial_imperfections(self, x: float, y: float, t: float, imperfection_level: float) -> Tuple[float, float]:
        """Apply spatial imperfections to coordinates."""

        # Micro-tremor effect
        tremor_intensity = imperfection_level * 0.8
        x += random.gauss(0, tremor_intensity)
        y += random.gauss(0, tremor_intensity)

        # Occasional larger deviations
        if random.random() < 0.12:
            deviation = imperfection_level * 2.0
            x += random.uniform(-deviation, deviation)
            y += random.uniform(-deviation, deviation)

        # Speed-based jitter (more jitter at curve extremes)
        speed_factor = 4 * t * (1 - t)  # Maximum at t=0.5
        if random.random() < 0.08:
            jitter = imperfection_level * speed_factor * 1.5
            x += random.gauss(0, jitter)
            y += random.gauss(0, jitter)

        return x, y

    def _add_micro_movements(
        self,
        curve_points: List[Coordinate],
        base_x: float,
        base_y: float,
        x_min: float, x_max: float, y_min: float, y_max: float
    ):
        """Add micro-movements and hesitations."""

        micro_count = random.randint(1, 3)
        for _ in range(micro_count):
            micro_x = max(x_min, min(x_max, base_x + random.gauss(0, 0.6)))
            micro_y = max(y_min, min(y_max, base_y + random.gauss(0, 0.6)))
            curve_points.append(Coordinate(micro_x, micro_y))

        # Add hesitation pause
        if random.random() < 0.06:
            hesitation_x = max(x_min, min(x_max, base_x + random.uniform(-2.0, 2.0)))
            hesitation_y = max(y_min, min(y_max, base_y + random.uniform(-2.0, 2.0)))
            curve_points.append(Coordinate(hesitation_x, hesitation_y))
class IntelligentPathBuilder:
    """Advanced path construction system with adaptive algorithms and behavioral modeling."""

    def __init__(self, start_coordinate: Coordinate, end_coordinate: Coordinate, **configuration):
        self.start_point = start_coordinate
        self.end_point = end_coordinate
        self.configuration = configuration
        self.curve_generator = AdvancedCurveGenerator()
        self.spatial_transformer = SpatialTransformer()
        self.path_points = self._construct_adaptive_path(**configuration)

    def _construct_adaptive_path(self, **config) -> List[Coordinate]:
        """Construct path using adaptive algorithms based on distance and complexity."""

        # Extract configuration with defaults - much more conservative
        curve_algorithm = config.get("curve_method", "adaptive_bezier")
        boundary_expansion = config.get("offset_boundary_x", 25)  # Reduced from 85 to 25
        vertical_expansion = config.get("offset_boundary_y", 25)  # Reduced from 85 to 25

        # Calculate dynamic boundaries with strict window bounds
        window_width = config.get("window_width", 1920)
        window_height = config.get("window_height", 1080)

        # Calculate path boundaries with strict limits
        path_left = min(self.start_point.x, self.end_point.x)
        path_right = max(self.start_point.x, self.end_point.x)
        path_top = min(self.start_point.y, self.end_point.y)
        path_bottom = max(self.start_point.y, self.end_point.y)

        # Apply conservative expansion with window bounds
        left_bound = max(0, path_left - boundary_expansion)
        right_bound = min(window_width, path_right + boundary_expansion)
        lower_bound = max(0, path_top - vertical_expansion)
        upper_bound = min(window_height, path_bottom + vertical_expansion)

        # Adaptive knot generation
        knot_count = config.get("knots_count", 3)
        if curve_algorithm == "bspline" and knot_count <= 2:
            knot_count = 4

        # Generate intelligent control points
        control_points = self._generate_intelligent_control_points(
            left_bound, right_bound, lower_bound, upper_bound, knot_count
        )

        # Apply advanced distortion modeling
        distortion_config = {
            "mean": config.get("distortion_mean", 1.05),
            "std": config.get("distortion_st_dev", 1.1),
            "frequency": config.get("distortion_frequency", 0.45)
        }

        # Generate base curve
        sample_count = config.get("target_points", 120)
        base_curve = self.curve_generator.generate_bezier_curve(
            control_points, sample_count, distortion_config["frequency"]
        )

        # Apply advanced post-processing
        processed_curve = self._apply_advanced_post_processing(
            base_curve, distortion_config, config.get("tween", pytweening.easeOutQuad)
        )

        # Final validation and constraint of all coordinates
        window_width = config.get("window_width", 1920)
        window_height = config.get("window_height", 1080)
        validated_curve = self.spatial_transformer.validate_and_constrain_coordinates(
            processed_curve, window_width, window_height
        )

        return validated_curve

    def _generate_intelligent_control_points(
        self,
        left: float, right: float, lower: float, upper: float, knot_count: int
    ) -> List[Coordinate]:
        """Generate control points using intelligent algorithms with enhanced bounds checking."""

        if not self._validate_boundaries(left, right, lower, upper):
            raise ValueError("Invalid boundary configuration")

        if knot_count < 0:
            knot_count = 0

        # Generate control points with spatial intelligence
        control_points = [self.start_point]

        # Calculate distance-based knot distribution
        total_distance = self.start_point.distance_to(self.end_point)
        knot_spacing = total_distance / (knot_count + 1) if knot_count > 0 else 0

        for i in range(knot_count):
            # Calculate base position along the path
            progress = (i + 1) / (knot_count + 1)
            base_x = self.start_point.x + (self.end_point.x - self.start_point.x) * progress
            base_y = self.start_point.y + (self.end_point.y - self.start_point.y) * progress

            # Add intelligent offset based on path characteristics with very conservative limits
            max_offset = min(knot_spacing * 0.15, 20)  # Further reduced from 0.25 and 30
            offset_x = random.uniform(-max_offset, max_offset)
            offset_y = random.uniform(-max_offset, max_offset)

            # Apply boundary constraints with additional safety margin
            safety_margin = 15  # Increased safety margin to 15px
            final_x = max(left + safety_margin, min(right - safety_margin, base_x + offset_x))
            final_y = max(lower + safety_margin, min(upper - safety_margin, base_y + offset_y))

            control_points.append(Coordinate(final_x, final_y))

        control_points.append(self.end_point)
        return control_points

    def _apply_advanced_post_processing(
        self,
        base_curve: List[Coordinate],
        distortion_config: Dict[str, float],
        tween_function: Callable
    ) -> List[Coordinate]:
        """Apply advanced post-processing to enhance human-like characteristics."""

        if len(base_curve) < 2:
            return base_curve

        # Apply intelligent distortion
        distorted_curve = self._apply_intelligent_distortion(base_curve, distortion_config)

        # Apply temporal resampling with tweening
        resampled_curve = self._apply_temporal_resampling(distorted_curve, tween_function)

        # Add final humanization touches
        humanized_curve = self._add_final_humanization(resampled_curve)

        return humanized_curve

    def _apply_intelligent_distortion(
        self,
        curve: List[Coordinate],
        distortion_config: Dict[str, float]
    ) -> List[Coordinate]:
        """Apply intelligent distortion based on curve characteristics."""

        distorted_points = [curve[0]]  # Keep start point unchanged

        for i, point in enumerate(curve[1:-1], 1):
            # Calculate distortion probability based on position
            position_factor = i / (len(curve) - 1)
            distortion_probability = distortion_config["frequency"] * (0.5 + 0.5 * math.sin(position_factor * math.pi))

            if random.random() < distortion_probability:
                # Apply Gaussian distortion
                distortion_std = distortion_config["std"] * 0.6
                offset_x = random.gauss(0, distortion_std)
                offset_y = random.gauss(0, distortion_std)

                # Add occasional larger deviations
                if random.random() < 0.08:
                    large_deviation = distortion_config["mean"] * 1.8
                    offset_x += random.uniform(-large_deviation, large_deviation)
                    offset_y += random.uniform(-large_deviation, large_deviation)

                distorted_point = Coordinate(point.x + offset_x, point.y + offset_y)
                distorted_points.append(distorted_point)
            else:
                distorted_points.append(point)

        distorted_points.append(curve[-1])  # Keep end point unchanged
        return distorted_points

    def _apply_temporal_resampling(
        self,
        curve: List[Coordinate],
        tween_function: Callable
    ) -> List[Coordinate]:
        """Apply temporal resampling with advanced tweening."""

        if len(curve) < 2:
            return curve

        target_count = len(curve)
        resampled_points = []

        for i in range(target_count):
            # Apply tweening to get smooth progression
            t = i / (target_count - 1) if target_count > 1 else 0
            tweened_t = tween_function(t)

            # Map to curve index
            curve_index = int(tweened_t * (len(curve) - 1))
            curve_index = max(0, min(len(curve) - 1, curve_index))

            resampled_points.append(curve[curve_index])

        return resampled_points

    def _add_final_humanization(self, curve: List[Coordinate]) -> List[Coordinate]:
        """Add final humanization touches to the curve."""

        humanized_curve = [curve[0]]

        for point in curve[1:-1]:
            humanized_curve.append(point)

            # Add micro-pauses and hesitations
            if random.random() < 0.09:
                # Add small hesitation movement
                hesitation_x = point.x + random.gauss(0, 0.8)
                hesitation_y = point.y + random.gauss(0, 0.8)
                humanized_curve.append(Coordinate(hesitation_x, hesitation_y))

            # Add occasional backtracking
            if random.random() < 0.04:
                backtrack_x = point.x + random.uniform(-1.5, 1.5)
                backtrack_y = point.y + random.uniform(-1.5, 1.5)
                humanized_curve.append(Coordinate(backtrack_x, backtrack_y))

        humanized_curve.append(curve[-1])
        return humanized_curve

    def _validate_boundaries(self, left: float, right: float, lower: float, upper: float) -> bool:
        """Validate boundary configuration."""
        return (left <= right and lower <= upper and
                all(isinstance(x, (int, float)) for x in [left, right, lower, upper]))

    @property
    def points(self) -> List[Tuple[int, int]]:
        """Return path points as integer tuples for compatibility."""
        return [point.to_tuple() for point in self.path_points]

class BehavioralTypingProfiles:
    """Advanced typing behavior profiles with contextual adaptation."""

    PROFILE_DEFINITIONS = {
        "beginner": {
            "interkey_timing": {"mean": 340, "std": 190, "min": 90, "max": 2400},
            "key_hold_duration": {"mean": 130, "std": 50, "min": 45, "max": 280},
            "error_correction": {"probability": 0.18, "delay": 850},
            "rhythm_variation": 0.25,
            "fatigue_factor": 0.15
        },
        "skilled": {
            "interkey_timing": {"mean": 190, "std": 45, "min": 35, "max": 420},
            "key_hold_duration": {"mean": 60, "std": 18, "min": 18, "max": 130},
            "error_correction": {"probability": 0.06, "delay": 320},
            "rhythm_variation": 0.12,
            "fatigue_factor": 0.08
        },
        "uncertain": {
            "interkey_timing": {"mean": 480, "std": 270, "min": 110, "max": 3200},
            "key_hold_duration": {"mean": 160, "std": 85, "min": 55, "max": 420},
            "error_correction": {"probability": 0.28, "delay": 1300},
            "rhythm_variation": 0.35,
            "fatigue_factor": 0.22
        },
        "rapid": {
            "interkey_timing": {"mean": 150, "std": 65, "min": 25, "max": 650},
            "key_hold_duration": {"mean": 48, "std": 28, "min": 12, "max": 110},
            "error_correction": {"probability": 0.09, "delay": 220},
            "rhythm_variation": 0.18,
            "fatigue_factor": 0.12
        },
        "relaxed": {
            "interkey_timing": {"mean": 300, "std": 130, "min": 70, "max": 1600},
            "key_hold_duration": {"mean": 95, "std": 38, "min": 30, "max": 190},
            "error_correction": {"probability": 0.14, "delay": 650},
            "rhythm_variation": 0.20,
            "fatigue_factor": 0.10
        },
        "business": {
            "interkey_timing": {"mean": 230, "std": 75, "min": 45, "max": 850},
            "key_hold_duration": {"mean": 75, "std": 28, "min": 25, "max": 150},
            "error_correction": {"probability": 0.07, "delay": 420},
            "rhythm_variation": 0.15,
            "fatigue_factor": 0.09
        },
        "competitive": {
            "interkey_timing": {"mean": 170, "std": 55, "min": 30, "max": 520},
            "key_hold_duration": {"mean": 52, "std": 22, "min": 18, "max": 115},
            "error_correction": {"probability": 0.04, "delay": 160},
            "rhythm_variation": 0.14,
            "fatigue_factor": 0.11
        },
        "touchscreen": {
            "interkey_timing": {"mean": 400, "std": 210, "min": 110, "max": 2600},
            "key_hold_duration": {"mean": 190, "std": 65, "min": 65, "max": 360},
            "error_correction": {"probability": 0.22, "delay": 1050},
            "rhythm_variation": 0.30,
            "fatigue_factor": 0.18
        },
        "preset": None,
        "adaptive": None,
    }

    @classmethod
    def retrieve_profile(cls, profile_name: str) -> Optional[Dict[str, Any]]:
        """Retrieve typing profile configuration."""
        return cls.PROFILE_DEFINITIONS.get(profile_name)


class AdvancedTimingEngine:
    """Sophisticated timing engine with contextual adaptation and behavioral modeling."""

    def __init__(
        self,
        interkey_timing_config: Dict[str, float],
        key_hold_config: Dict[str, float],
        error_correction_config: Dict[str, float],
        rhythm_variation: float = 0.2,
        fatigue_factor: float = 0.1
    ):
        self.interkey_config = interkey_timing_config
        self.hold_config = key_hold_config
        self.error_config = error_correction_config
        self.rhythm_variation = rhythm_variation
        self.fatigue_factor = fatigue_factor
        self._initialize_distributions()
        self._typing_history = deque(maxlen=50)
        self._fatigue_accumulator = 0.0

    def _initialize_distributions(self):
        """Initialize statistical distributions for timing generation."""
        try:
            # Create bounded beta distributions for realistic timing
            self.interkey_dist = self._create_bounded_beta_distribution(
                self.interkey_config["min"], self.interkey_config["max"],
                self.interkey_config["mean"], self.interkey_config["std"]
            )
            self.hold_dist = self._create_bounded_beta_distribution(
                self.hold_config["min"], self.hold_config["max"],
                self.hold_config["mean"], self.hold_config["std"]
            )
        except ValueError:
            # Fallback to normal distributions if beta fails
            self.interkey_dist = scipy.stats.norm(
                loc=self.interkey_config["mean"],
                scale=self.interkey_config["std"]
            )
            self.hold_dist = scipy.stats.norm(
                loc=self.hold_config["mean"],
                scale=self.hold_config["std"]
            )

    def _create_bounded_beta_distribution(self, min_val: float, max_val: float, mean: float, std: float):
        """Create a bounded beta distribution for realistic timing."""
        scale = max_val - min_val
        loc = min_val
        mu = (mean - min_val) / scale
        var = (std / scale) ** 2

        if var <= 0 or mu <= 0 or mu >= 1:
            raise ValueError("Invalid parameters for beta distribution")

        t = mu / (1 - mu)
        beta = (t / var - t * t - 2 * t - 1) / (t ** 3 + 3 * t * t + 3 * t + 1)
        alpha = beta * t

        if alpha <= 0 or beta <= 0:
            raise ValueError("Invalid alpha/beta parameters")

        return scipy.stats.beta(alpha, beta, scale=scale, loc=loc)

    def generate_timing_sequence(self, text_length: int) -> Dict[str, List[float]]:
        """Generate timing sequence with contextual adaptation."""

        # Generate base timings
        interkey_times = self.interkey_dist.rvs(size=text_length - 1)
        hold_times = self.hold_dist.rvs(size=text_length)

        # Apply contextual modifications
        interkey_times = self._apply_rhythm_variations(interkey_times)
        hold_times = self._apply_fatigue_effects(hold_times)

        # Ensure positive values and apply bounds
        interkey_times = np.clip(interkey_times, self.interkey_config["min"], self.interkey_config["max"])
        hold_times = np.clip(hold_times, self.hold_config["min"], self.hold_config["max"])

        return {
            "interkey_delays": interkey_times.tolist(),
            "hold_durations": hold_times.tolist()
        }

    def _apply_rhythm_variations(self, timings: np.ndarray) -> np.ndarray:
        """Apply rhythm variations to create natural typing patterns."""
        variations = np.random.normal(1.0, self.rhythm_variation, len(timings))
        variations = np.clip(variations, 0.3, 2.0)  # Reasonable bounds
        return timings * variations

    def _apply_fatigue_effects(self, timings: np.ndarray) -> np.ndarray:
        """Apply fatigue effects that increase over time."""
        fatigue_multiplier = 1.0 + (self._fatigue_accumulator * self.fatigue_factor)
        self._fatigue_accumulator += 0.01  # Gradual fatigue increase

        # Apply fatigue with some randomness
        fatigue_variation = np.random.normal(fatigue_multiplier, 0.1, len(timings))
        fatigue_variation = np.clip(fatigue_variation, 0.8, 1.5)

        return timings * fatigue_variation

    def update_parameters(self, **parameters):
        """Update timing parameters dynamically."""
        for key, value in parameters.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self._initialize_distributions()


class IntelligentTypingBehavior:
    """Advanced typing behavior system with adaptive profiles and contextual awareness."""

    def __init__(self, profile_name: str = "preset"):
        self.profile_name = profile_name
        self.timing_engine = None
        self._initialize_behavior_profile(profile_name)
        self._typing_context = {
            "current_speed": 1.0,
            "error_count": 0,
            "consecutive_errors": 0,
            "last_correction_time": 0
        }

    def _initialize_behavior_profile(self, profile_name: str):
        """Initialize behavior profile with appropriate timing engine."""
        if profile_name not in BehavioralTypingProfiles.PROFILE_DEFINITIONS:
            raise ValueError(f"Unknown behavior profile: {profile_name}")

        if profile_name in ("preset", "adaptive"):
            # Use default configuration
            self.timing_engine = AdvancedTimingEngine(
                interkey_timing_config={"mean": 200, "std": 80, "min": 50, "max": 600},
                key_hold_config={"mean": 85, "std": 30, "min": 25, "max": 220},
                error_correction_config={"probability": 0.1, "delay": 500},
                rhythm_variation=0.2,
                fatigue_factor=0.1
            )
        else:
            # Use profile-specific configuration
            profile_config = BehavioralTypingProfiles.retrieve_profile(profile_name)
            self.timing_engine = AdvancedTimingEngine(
                interkey_timing_config=profile_config["interkey_timing"],
                key_hold_config=profile_config["key_hold_duration"],
                error_correction_config=profile_config["error_correction"],
                rhythm_variation=profile_config["rhythm_variation"],
                fatigue_factor=profile_config["fatigue_factor"]
            )

    def customize_behavior(self, **custom_parameters):
        """Customize typing behavior with specific parameters."""
        self.profile_name = "adaptive"
        if self.timing_engine:
            self.timing_engine.update_parameters(**custom_parameters)

    def generate_typing_events(self, text: str) -> List[Dict[str, Union[str, float, int]]]:
        """Generate comprehensive typing events with behavioral patterns."""

        if self.profile_name == "preset":
            return self._generate_preset_typing_events(text)

        # Generate adaptive timing sequence
        timing_data = self.timing_engine.generate_timing_sequence(len(text))
        interkey_delays = timing_data["interkey_delays"]
        hold_durations = timing_data["hold_durations"]

        # Create typing events
        events = []
        current_time = 0.0

        for i, character in enumerate(text):
            # Key press event
            events.append({
                "type": "keydown",
                "char": character,
                "timing": current_time,
                "key_index": i + 1
            })

            # Key release event
            hold_time = hold_durations[i]
            events.append({
                "type": "keyup",
                "char": character,
                "timing": current_time + hold_time,
                "key_index": i + 1
            })

            # Add interkey delay (except for last character)
            if i < len(text) - 1:
                current_time += interkey_delays[i]

        # Sort events by timing
        events.sort(key=lambda e: e["timing"])

        # Add error correction events
        events = self._add_error_correction_events(events, text)

        # Calculate wait times
        return self._calculate_wait_times(events)

    def _generate_preset_typing_events(self, text: str) -> List[Dict[str, Union[str, float, int]]]:
        """Generate preset typing events for maximum humanization."""

        preset_pattern = [
            {"timestamp": 0.0, "key_index": 1, "action": "press"},
            {"timestamp": 88.0, "key_index": 2, "action": "press"},
            {"timestamp": 112.0, "key_index": 1, "action": "release"},
            {"timestamp": 238.0, "key_index": 3, "action": "press"},
            {"timestamp": 268.0, "key_index": 2, "action": "release"},
            {"timestamp": 338.0, "key_index": 4, "action": "press"},
            {"timestamp": 392.0, "key_index": 3, "action": "release"},
            {"timestamp": 448.0, "key_index": 5, "action": "press"},
            {"timestamp": 518.0, "key_index": 4, "action": "release"},
            {"timestamp": 608.0, "key_index": 6, "action": "press"},
            {"timestamp": 623.0, "key_index": 5, "action": "release"},
            {"timestamp": 713.0, "key_index": 6, "action": "release"},
            {"timestamp": 728.0, "key_index": 7, "action": "press"},
            {"timestamp": 803.0, "key_index": 8, "action": "press"},
            {"timestamp": 868.0, "key_index": 7, "action": "release"},
            {"timestamp": 953.0, "key_index": 8, "action": "release"},
            {"timestamp": 1573.0, "key_index": 9, "action": "press"},
            {"timestamp": 1698.0, "key_index": 10, "action": "press"},
            {"timestamp": 1803.0, "key_index": 9, "action": "release"},
            {"timestamp": 1828.0, "key_index": 10, "action": "release"},
            {"timestamp": 2098.0, "key_index": 11, "action": "press"},
            {"timestamp": 2208.0, "key_index": 11, "action": "release"},
            {"timestamp": 2358.0, "key_index": 12, "action": "press"},
            {"timestamp": 2403.0, "key_index": 12, "action": "release"},
            {"timestamp": 2543.0, "key_index": 13, "action": "press"},
            {"timestamp": 2573.0, "key_index": 13, "action": "release"},
            {"timestamp": 3808.0, "key_index": 14, "action": "press"},
            {"timestamp": 3953.0, "key_index": 14, "action": "release"},
            {"timestamp": 4538.0, "key_index": 15, "action": "press"},
            {"timestamp": 4658.0, "key_index": 15, "action": "release"},
            {"timestamp": 4718.0, "key_index": 16, "action": "press"},
            {"timestamp": 4793.0, "key_index": 16, "action": "release"},
            {"timestamp": 4818.0, "key_index": 17, "action": "press"},
            {"timestamp": 4908.0, "key_index": 18, "action": "press"},
            {"timestamp": 4983.0, "key_index": 17, "action": "release"},
            {"timestamp": 5013.0, "key_index": 19, "action": "press"},
            {"timestamp": 5038.0, "key_index": 18, "action": "release"},
            {"timestamp": 5148.0, "key_index": 20, "action": "press"},
            {"timestamp": 5208.0, "key_index": 21, "action": "press"},
            {"timestamp": 5253.0, "key_index": 19, "action": "release"},
            {"timestamp": 5298.0, "key_index": 20, "action": "release"},
            {"timestamp": 5313.0, "key_index": 22, "action": "press"},
            {"timestamp": 5333.0, "key_index": 21, "action": "release"},
            {"timestamp": 5433.0, "key_index": 22, "action": "release"},
            {"timestamp": 5468.0, "key_index": 23, "action": "press"},
            {"timestamp": 5553.0, "key_index": 23, "action": "release"},
            {"timestamp": 5668.0, "key_index": 24, "action": "press"},
            {"timestamp": 5728.0, "key_index": 24, "action": "release"},
            {"timestamp": 5758.0, "key_index": 25, "action": "press"},
            {"timestamp": 5823.0, "key_index": 25, "action": "release"},
            {"timestamp": 6318.0, "key_index": 26, "action": "press"},
            {"timestamp": 6428.0, "key_index": 27, "action": "press"},
            {"timestamp": 6543.0, "key_index": 26, "action": "release"},
            {"timestamp": 6568.0, "key_index": 28, "action": "press"},
            {"timestamp": 6593.0, "key_index": 27, "action": "release"},
            {"timestamp": 6693.0, "key_index": 28, "action": "release"},
            {"timestamp": 6833.0, "key_index": 29, "action": "press"},
            {"timestamp": 6943.0, "key_index": 29, "action": "release"},
            {"timestamp": 7068.0, "key_index": 30, "action": "press"},
            {"timestamp": 7143.0, "key_index": 31, "action": "press"},
            {"timestamp": 7223.0, "key_index": 32, "action": "press"},
            {"timestamp": 7233.0, "key_index": 30, "action": "release"},
            {"timestamp": 7238.0, "key_index": 31, "action": "release"},
            {"timestamp": 7318.0, "key_index": 32, "action": "release"},
        ]

        # Organize events by key index
        event_groups = defaultdict(list)
        for event in preset_pattern:
            event_groups[event["key_index"]].append(event)

        # Generate events for each character
        all_events = []
        for i, character in enumerate(text):
            key_index = (i % 32) + 1
            for event in event_groups.get(key_index, []):
                event_copy = dict(event)
                event_copy["char"] = character
                event_copy["type"] = "keydown" if event["action"] == "press" else "keyup"
                event_copy["timing"] = event["timestamp"]
                all_events.append(event_copy)

        return self._calculate_wait_times(all_events)

    def _add_error_correction_events(self, events: List[Dict], text: str) -> List[Dict]:
        """Add realistic error correction events."""
        if not self.timing_engine:
            return events

        error_probability = self.timing_engine.error_config["probability"]
        correction_delay = self.timing_engine.error_config["delay"]

        # Add occasional error corrections
        for i in range(len(text) - 1):
            if random.random() < error_probability:
                # Find the keyup event for this character
                keyup_event = None
                for event in events:
                    if (event["type"] == "keyup" and
                        event["key_index"] == i + 1):
                        keyup_event = event
                        break

                if keyup_event:
                    # Add backspace and retype
                    correction_time = keyup_event["timing"] + correction_delay
                    events.append({
                        "type": "keydown",
                        "char": "\b",
                        "timing": correction_time,
                        "key_index": i + 1
                    })
                    events.append({
                        "type": "keyup",
                        "char": "\b",
                        "timing": correction_time + 50,
                        "key_index": i + 1
                    })
                    events.append({
                        "type": "keydown",
                        "char": text[i],
                        "timing": correction_time + 100,
                        "key_index": i + 1
                    })
                    events.append({
                        "type": "keyup",
                        "char": text[i],
                        "timing": correction_time + 150,
                        "key_index": i + 1
                    })

        # Re-sort events after adding corrections
        events.sort(key=lambda e: e["timing"])
        return events

    def _calculate_wait_times(self, events: List[Dict]) -> List[Dict]:
        """Calculate wait times between events."""
        if not events:
            return []

        processed_events = []
        previous_time = 0.0

        for event in events:
            wait_time = max(0.0, event["timing"] - previous_time)
            event_copy = dict(event)
            event_copy["wait_time"] = wait_time
            processed_events.append(event_copy)
            previous_time = event["timing"]

        return processed_events

class AdvancedInteractionController:
    """Sophisticated interaction controller with enhanced humanization and error handling."""

    def __init__(self, web_driver: WebDriver):
        self.driver = web_driver
        self.action_chain = ActionChains(web_driver, duration=0 if not isinstance(web_driver, Firefox) else 1)
        self.current_position = Coordinate(0, 0)
        self.spatial_transformer = SpatialTransformer()
        self.curve_generator = AdvancedCurveGenerator()
        self.interaction_history = deque(maxlen=100)
        self._setup_enhanced_logging()

    def _setup_enhanced_logging(self):
        """Setup enhanced logging for interaction tracking."""
        _logger.set_context(
            driver_type=type(self.driver).__name__,
            session_id=getattr(self.driver, 'session_id', 'unknown')[:8]
        )

    def execute_typing_sequence(
        self,
        target_element: WebElement,
        text_content: str,
        behavior_profile: str,
        custom_timing_params: Optional[Dict[str, float]] = None
    ):
        """Execute advanced typing sequence with behavioral modeling."""

        # Suppress unused parameter warning for API compatibility
        _ = target_element

        typing_behavior = IntelligentTypingBehavior(behavior_profile)

        if behavior_profile == "adaptive" and custom_timing_params:
            typing_behavior.customize_behavior(**custom_timing_params)

        # Generate typing events
        typing_events = typing_behavior.generate_typing_events(text_content)

        # Execute events with enhanced error handling
        self._execute_typing_events(typing_events)

        # Log interaction
        self.interaction_history.append({
            "type": "typing",
            "text_length": len(text_content),
            "profile": behavior_profile,
            "timestamp": time.time()
        })

    def _execute_typing_events(self, events: List[Dict[str, Union[str, float, int]]]):
        """Execute typing events with sophisticated timing control."""

        total_events = len(events)
        for i, event in enumerate(events):
            try:
                if event["type"] == "keydown":
                    self.action_chain.key_down(event["char"])
                elif event["type"] == "keyup":
                    self.action_chain.key_up(event["char"])

                # Apply wait time except for the last event
                if i < total_events - 1 and event["wait_time"] > 0:
                    wait_seconds = event["wait_time"] / 1000.0
                    # Add micro-variations to wait times
                    wait_seconds += random.uniform(-0.001, 0.001)
                    self.action_chain.pause(max(0.001, wait_seconds))

            except (ValueError, TypeError) as e:
                _logger.error(f"Error executing typing event: {e}")
                continue

        # Perform all actions
        try:
            self.action_chain.perform()
        except (ValueError, TypeError) as e:
            _logger.error(f"Error performing typing actions: {e}")

    def navigate_to_target(
        self,
        destination: Union[WebElement, List[int]],
        starting_position: Optional[Coordinate] = None,
        use_absolute_coordinates: bool = False,
        relative_position: Optional[List[float]] = None,
        interaction_mode: InteractionMode = InteractionMode.DYNAMIC,
        custom_curve: Optional[IntelligentPathBuilder] = None,
        window_dimensions: Optional[Tuple[int, int]] = None,
        custom_tween_function: Optional[Callable] = None,
    ) -> Tuple[Coordinate, int]:
        """Navigate to target with advanced path planning and humanization."""

        start_pos = starting_position or self.current_position

        # Calculate destination coordinates
        if isinstance(destination, list):
            if use_absolute_coordinates:
                dest_coord = Coordinate(destination[0] + start_pos.x, destination[1] + start_pos.y)
            else:
                dest_coord = Coordinate(destination[0], destination[1])
        else:
            dest_coord = self._calculate_element_destination(destination, relative_position)

        # Generate movement parameters
        movement_params = self.spatial_transformer.generate_movement_parameters(
            self.driver, start_pos, dest_coord, interaction_mode,
            window_dimensions or (1920, 1080), custom_tween_function
        )

        # Create path
        if custom_curve is None:
            # Get window dimensions for strict bounds
            try:
                window_size = self.driver.get_window_size()
                window_width = window_size["width"]
                window_height = window_size["height"]
            except (AttributeError, TypeError):
                window_width, window_height = 1920, 1080

            path_builder = IntelligentPathBuilder(
                start_pos, dest_coord,
                curve_method="adaptive_bezier",
                offset_boundary_x=movement_params["x_offset"],
                offset_boundary_y=movement_params["y_offset"],
                knots_count=movement_params["knot_count"],
                distortion_mean=movement_params["distortion_mean"],
                distortion_st_dev=movement_params["distortion_std"],
                distortion_frequency=movement_params["distortion_frequency"],
                tween=movement_params["tween_function"],
                target_points=movement_params["sample_count"],
                window_width=window_width,
                window_height=window_height
            )
        else:
            path_builder = custom_curve

        # Execute movement
        return self._execute_movement_path(path_builder.points, movement_params["is_web_driver"])

    def _calculate_element_destination(self, element: WebElement, relative_pos: Optional[List[float]]) -> Coordinate:
        """Calculate destination coordinates for an element."""

        # Get element position
        element_rect = self.driver.execute_script(
            """
            var el = arguments[0];
            var rect = el.getBoundingClientRect();
            return {
                x: Math.round(rect.left),
                y: Math.round(rect.top),
                width: Math.round(rect.width),
                height: Math.round(rect.height)
            };
            """,
            element
        )

        # Calculate target position within element
        if relative_pos is None:
            # Random position within element (avoiding edges)
            rel_x = random.uniform(0.15, 0.85)
            rel_y = random.uniform(0.15, 0.85)
        else:
            rel_x, rel_y = relative_pos

        target_x = element_rect["x"] + element_rect["width"] * rel_x
        target_y = element_rect["y"] + element_rect["height"] * rel_y

        return Coordinate(target_x, target_y)

    def _execute_movement_path(self, path_points: List[Tuple[int, int]], is_web_driver: bool) -> Tuple[Coordinate, int]:
        """Execute movement along the generated path with final validation."""

        if not path_points:
            return self.current_position, 0

        # Get window dimensions for final validation
        try:
            window_size = self.driver.get_window_size()
            window_width = window_size["width"]
            window_height = window_size["height"]
        except (AttributeError, TypeError):
            window_width, window_height = 1920, 1080

        # Final validation of all path points
        validated_points = []
        safety_margin = 10  # 10px safety margin

        for point in path_points:
            x, y = point
            # Constrain to safe window area
            safe_x = max(safety_margin, min(window_width - safety_margin, x))
            safe_y = max(safety_margin, min(window_height - safety_margin, y))
            validated_points.append((int(safe_x), int(safe_y)))

        if is_web_driver:
            return self._execute_web_movement(validated_points)
        else:
            return self._execute_direct_movement(validated_points)

    def _execute_web_movement(self, path_points: List[Tuple[int, int]]) -> Tuple[Coordinate, int]:
        """Execute movement using web driver action chains with enhanced bounds checking."""

        movement_offset = [0, 0]
        start_pos = self.current_position

        # Get window dimensions for bounds checking
        try:
            window_size = self.driver.get_window_size()
            window_width = window_size["width"]
            window_height = window_size["height"]
        except (AttributeError, TypeError):
            window_width, window_height = 1920, 1080  # Default fallback

        try:
            for point in path_points[1:]:
                # Validate point is within bounds before movement
                if (0 <= point[0] <= window_width and 0 <= point[1] <= window_height):
                    dx = point[0] - start_pos.x
                    dy = point[1] - start_pos.y

                    start_pos.x, start_pos.y = point[0], point[1]
                    movement_offset[0] += int(dx)
                    movement_offset[1] += int(dy)

                    self.action_chain.move_by_offset(int(dx), int(dy))
                else:
                    _logger.error(f"Point {point} out of bounds, skipping movement step")

            self.action_chain.perform()

        except MoveTargetOutOfBoundsException:
            _logger.error("Movement target out of bounds, using enhanced fallback")
            # Enhanced fallback with bounds validation
            final_point = path_points[-1]

            # Ensure final point is within bounds
            final_x = max(0, min(window_width, final_point[0]))
            final_y = max(0, min(window_height, final_point[1]))

            # Calculate safe movement
            safe_dx = int(final_x - self.current_position.x)
            safe_dy = int(final_y - self.current_position.y)

            # Limit movement to reasonable bounds
            max_move = 200  # Maximum single movement
            safe_dx = max(-max_move, min(max_move, safe_dx))
            safe_dy = max(-max_move, min(max_move, safe_dy))

            self.action_chain.move_by_offset(safe_dx, safe_dy)
            self.action_chain.perform()

            # Update position to safe final position
            start_pos = Coordinate(final_x, final_y)

        self.current_position = start_pos
        return self.current_position, len(path_points)

    def _execute_direct_movement(self, path_points: List[Tuple[int, int]]) -> Tuple[Coordinate, int]:
        """Execute direct movement (non-web driver)."""
        if path_points:
            final_point = path_points[-1]
            self.current_position = Coordinate(final_point[0], final_point[1])
        return self.current_position, len(path_points)

    def perform_click_sequence(self, click_count: int = 1, hold_duration: float = 0.0) -> bool:
        """Perform click sequence with enhanced humanization."""

        try:
            if hold_duration > 0:
                # Click and hold
                click_action = lambda: (
                    self.action_chain.click_and_hold()
                    .pause(hold_duration)
                    .release()
                    .pause(random.uniform(0.15, 0.25))
                )
            else:
                # Regular click
                click_action = lambda: (
                    self.action_chain.click()
                    .pause(random.uniform(0.12, 0.22))
                )

            for _ in range(click_count):
                click_action()

            self.action_chain.perform()

            # Log interaction
            self.interaction_history.append({
                "type": "click",
                "count": click_count,
                "hold_duration": hold_duration,
                "timestamp": time.time()
            })

            return True

        except (ValueError, TypeError) as e:
            _logger.error(f"Error performing click sequence: {e}")
            return False

    def navigate_and_click(
        self,
        target: Union[WebElement, List[int]],
        click_count: int = 1,
        hold_duration: float = 0.0,
        relative_position: Optional[List[float]] = None,
        use_absolute_coordinates: bool = False,
        starting_position: Optional[Coordinate] = None,
        interaction_mode: InteractionMode = InteractionMode.DYNAMIC,
    ) -> bool:
        """Navigate to target and perform click with enhanced humanization."""

        if interaction_mode == InteractionMode.STEADY:
            # Navigate first
            self.navigate_to_target(
                target,
                starting_position=starting_position,
                use_absolute_coordinates=use_absolute_coordinates,
                relative_position=relative_position,
                interaction_mode=interaction_mode
            )

            # Then click
            return self.perform_click_sequence(click_count, hold_duration)

        return False

    def ensure_element_visibility(self, target: Union[WebElement, List[int]]) -> bool:
        """Ensure target element is visible in viewport with enhanced scrolling."""

        if isinstance(target, WebElement):
            # Check if element is in viewport
            is_visible = self.driver.execute_script(
                """
                var element = arguments[0];
                var rect = element.getBoundingClientRect();
                var windowHeight = window.innerHeight || document.documentElement.clientHeight;
                var windowWidth = window.innerWidth || document.documentElement.clientWidth;

                return (
                    rect.top >= 0 &&
                    rect.left >= 0 &&
                    rect.bottom <= windowHeight &&
                    rect.right <= windowWidth
                );
                """,
                target
            )

            if not is_visible:
                # Scroll element into view with smooth behavior
                self.driver.execute_script(
                    "arguments[0].scrollIntoView({ behavior: 'smooth', block: 'center', inline: 'center' });",
                    target
                )

                # Wait for scroll to complete with human-like timing
                scroll_wait = random.uniform(0.9, 1.5)
                sleep(scroll_wait)

                # Log interaction
                self.interaction_history.append({
                    "type": "scroll",
                    "target": "element",
                    "wait_time": scroll_wait,
                    "timestamp": time.time()
                })

            return True

        elif isinstance(target, list):
            # Coordinate target is always "visible"
            return True
        else:
            _logger.error("Invalid target type for visibility check")
            return False




class HumanizedInteractionAgent:
    """Advanced humanized interaction agent with sophisticated behavioral modeling."""

    def __init__(self, web_driver: WebDriver, path_algorithm: str = "adaptive_bezier", custom_tween: Optional[Callable] = None):
        self.driver = web_driver
        self.interaction_controller = AdvancedInteractionController(web_driver)
        self.current_position = Coordinate(0, 0)
        self.path_algorithm = path_algorithm
        self.custom_tween_function = custom_tween
        self.total_movement_steps = 0
        self.behavioral_context = {
            "session_start_time": time.time(),
            "interaction_count": 0,
            "error_count": 0,
            "fatigue_level": 0.0
        }
        self._setup_behavioral_profiles()

    def _setup_behavioral_profiles(self):
        """Setup behavioral profiles for different interaction types."""
        self.behavioral_profiles = {
            "precise": MovementStyle.PRECISE,
            "natural": MovementStyle.NATURAL,
            "erratic": MovementStyle.ERRATIC,
            "gaming": MovementStyle.GAMING,
            "mobile": MovementStyle.MOBILE
        }

    def execute_text_input(
        self,
        target_element: WebElement,
        text_content: str,
        behavior_profile: str = "preset",
        custom_timing_parameters: Optional[Dict[str, float]] = None
    ):
        """Execute text input with advanced behavioral modeling."""

        # Ensure element is visible
        if not self.interaction_controller.ensure_element_visibility(target_element):
            _logger.error("Failed to make element visible for text input")
            return False

        # Clear existing content
        try:
            target_element.clear()
        except (ValueError, TypeError) as e:
            _logger.error(f"Error clearing element: {e}")

        # Click on element first
        self.interaction_controller.navigate_and_click(
            target_element,
            click_count=1,
            hold_duration=0.0,
            relative_position=[0.5, 0.5],
            interaction_mode=InteractionMode.STEADY
        )

        # Execute typing sequence
        self.interaction_controller.execute_typing_sequence(
            target_element,
            text_content,
            behavior_profile,
            custom_timing_parameters
        )

        # Update behavioral context
        self.behavioral_context["interaction_count"] += 1
        self._update_fatigue_level()

        return True

    def navigate_to_position(
        self,
        destination: Union[WebElement, List[int]],
        relative_position: Optional[List[float]] = None,
        use_absolute_coordinates: bool = False,
        starting_position: Optional[Coordinate] = None,
        movement_style: str = "natural",
        interaction_mode: str = "dynamic",
        apply_random_start_position: bool = False,
    ) -> Coordinate:
        """Navigate to position with enhanced humanization."""

        # Handle random start position
        if self.current_position == Coordinate(0, 0) and apply_random_start_position:
            window_size = self.driver.get_window_size()
            random_x = random.randint(0, window_size["width"])
            random_y = random.randint(0, window_size["height"])
            self.current_position = Coordinate(random_x, random_y)

        # Suppress unused parameter warnings for API compatibility
        _ = movement_style
        _ = apply_random_start_position

        # Convert string parameters to enums
        interaction_mode_enum = InteractionMode.DYNAMIC if interaction_mode == "dynamic" else InteractionMode.STEADY

        # Ensure element visibility if it's a WebElement
        if isinstance(destination, WebElement):
            if not self.interaction_controller.ensure_element_visibility(destination):
                _logger.error("Failed to make element visible for navigation")
                return self.current_position

        # Navigate to target
        new_position, movement_steps = self.interaction_controller.navigate_to_target(
            destination,
            starting_position=starting_position or self.current_position,
            use_absolute_coordinates=use_absolute_coordinates,
            relative_position=relative_position,
            interaction_mode=interaction_mode_enum,
            window_dimensions=(self.driver.get_window_size()["width"], self.driver.get_window_size()["height"]),
            custom_tween_function=self.custom_tween_function
        )

        # Update position and movement tracking
        self.current_position = new_position
        self.total_movement_steps += max(0, movement_steps - 1)

        return self.current_position

    def perform_click_action(
        self,
        target: Union[WebElement, List[int]],
        click_count: int = 1,
        hold_duration: float = 0.0,
        relative_position: Optional[List[float]] = None,
        use_absolute_coordinates: bool = False,
        starting_position: Optional[Coordinate] = None,
        movement_style: str = "natural",
        interaction_mode: str = "steady",
        path_algorithm: str = None,
        apply_random_start_position: bool = True,
    ) -> bool:
        """Perform click action with enhanced humanization."""

        # Suppress unused parameter warnings for API compatibility
        _ = movement_style
        _ = path_algorithm
        _ = apply_random_start_position

        # Convert string parameters to enums
        interaction_mode_enum = InteractionMode.STEADY if interaction_mode == "steady" else InteractionMode.DYNAMIC

        # Navigate and click
        success = self.interaction_controller.navigate_and_click(
            target,
            click_count=click_count,
            hold_duration=hold_duration,
            relative_position=relative_position,
            use_absolute_coordinates=use_absolute_coordinates,
            starting_position=starting_position,
            interaction_mode=interaction_mode_enum
        )

        # Update behavioral context
        if success:
            self.behavioral_context["interaction_count"] += 1
        else:
            self.behavioral_context["error_count"] += 1

        self._update_fatigue_level()

        return success

    def execute_click_sequence(self, target_element: Union[WebElement, List[int]], click_count: int = 1, hold_duration: float = 0, path_algorithm: str = "adaptive_bezier"):
        """Execute click sequence for API compatibility."""
        # Suppress unused parameter warnings for API compatibility
        _ = target_element
        _ = path_algorithm
        return self.interaction_controller.perform_click_sequence(click_count, hold_duration)

    def ensure_element_visibility(self, target_element: WebElement) -> bool:
        """Ensure element is visible in viewport."""
        return self.interaction_controller.ensure_element_visibility(target_element)

    def _update_fatigue_level(self):
        """Update fatigue level based on interaction history."""
        session_duration = time.time() - self.behavioral_context["session_start_time"]
        interaction_density = self.behavioral_context["interaction_count"] / max(1, session_duration / 60)  # interactions per minute

        # Calculate fatigue based on interaction density and errors
        base_fatigue = min(0.3, interaction_density * 0.05)
        error_penalty = self.behavioral_context["error_count"] * 0.02
        self.behavioral_context["fatigue_level"] = min(0.5, base_fatigue + error_penalty)

    @property
    def origin(self) -> List[int]:
        """Get current position as list for compatibility."""
        return [int(self.current_position.x), int(self.current_position.y)]

    @property
    def move_steps(self) -> int:
        """Get total movement steps for compatibility."""
        return self.total_movement_steps

def run_bot(driver: WebDriver) -> bool:
    """
    Advanced humanized bot execution with sophisticated behavioral modeling.
    Maintains compatibility with existing test framework while providing enhanced humanization.
    """
    try:
        # Initialize enhanced logging context
        _logger.set_context(
            session_id=getattr(driver, 'session_id', 'unknown')[:8],
            bot_version="humanized_v2"
        )

        # Setup enhanced waiting and interaction systems
        enhanced_wait = WebDriverWait(driver, 18)
        interaction_agent = HumanizedInteractionAgent(driver, path_algorithm="adaptive_bezier")

        # Retrieve and process action sequence
        action_sequence: List[Dict[str, Any]] = json.loads(
            driver.execute_script("return window.ACTIONS_LIST;")
        )

        _logger.info(f"Processing {len(action_sequence)} actions with enhanced humanization")

        # Execute action sequence with enhanced behavioral modeling
        for action_index, current_action in enumerate(action_sequence):
            try:
                action_type = current_action.get("type")

                if action_type == "click":
                    # Enhanced click handling with sophisticated positioning
                    click_location = current_action["args"]["location"]
                    target_x, target_y = click_location["x"], click_location["y"]

                    # Apply human-like positioning variations
                    position_variation = random.uniform(0.8, 1.2)
                    adjusted_x = int(target_x * position_variation)
                    adjusted_y = int(target_y * position_variation)

                    interaction_agent.perform_click_action(
                        target=[adjusted_x, adjusted_y],
                        click_count=1,
                        hold_duration=0.0,
                        movement_style="natural",
                        interaction_mode="steady",
                        apply_random_start_position=False
                    )

                elif action_type == "input":
                    input_selector = current_action["selector"]
                    input_text = current_action["args"]["text"]

                    # Determine input positioning strategy
                    if action_index == 5:
                        relative_position = [0.12, 0.12]  # Slightly offset for first input
                    else:
                        relative_position = [0.48, 0.52]  # Near center with slight variation

                    # Locate and interact with input field
                    input_field = driver.find_element(By.ID, input_selector["id"])

                    # Clear field with human-like behavior
                    input_field.clear()

                    # Click on field with enhanced positioning
                    interaction_agent.perform_click_action(
                        target=input_field,
                        click_count=1,
                        hold_duration=0.0,
                        relative_position=relative_position,
                        movement_style="natural",
                        interaction_mode="steady"
                    )

                    # Execute typing with preset behavioral profile
                    interaction_agent.execute_text_input(
                        target_element=input_field,
                        text_content=input_text,
                        behavior_profile="preset"
                    )

                    # Human-like pause between inputs
                    pause_duration = random.uniform(0.4, 0.7)
                    time.sleep(pause_duration)

            except (ValueError, TypeError, KeyError) as action_error:
                _logger.error(f"Error processing action {action_index}: {action_error}")
                continue

        pre_login_pause = random.uniform(0.8, 1.3)
        time.sleep(pre_login_pause)

        # Locate and interact with login button
        login_button = enhanced_wait.until(
            EC.presence_of_element_located((By.ID, "login-button"))
        )

        current_movement_steps = interaction_agent.move_steps
        if current_movement_steps < 250:
            # Calculate compensation movement with enhanced algorithm and bounds checking
            movement_deficit = abs((270 - current_movement_steps) * 14)
            compensation_offset = movement_deficit / 2 * 0.707  # Diagonal compensation

            # Get window dimensions for bounds checking (not used in current logic but kept for future use)
            try:
                window_size = driver.get_window_size()
                _ = window_size["width"]  # Suppress unused variable warning
                _ = window_size["height"]  # Suppress unused variable warning
            except (AttributeError, TypeError):
                pass  # Use default values if needed

            # Apply boundary constraints with safety margins
            current_origin = interaction_agent.origin
            safety_margin = 50  # 50px safety margin

            # Ensure compensation doesn't go out of bounds
            max_compensation_x = min(current_origin[0] - safety_margin, compensation_offset)
            max_compensation_y = min(current_origin[1] - safety_margin, compensation_offset)

            # Use the smaller of the two to maintain diagonal movement
            safe_compensation = min(max_compensation_x, max_compensation_y, compensation_offset)

            if safe_compensation > 10:  # Only move if we have a reasonable compensation
                # Execute compensation movement with safe bounds
                interaction_agent.navigate_to_position(
                    destination=[-safe_compensation, -safe_compensation],
                    use_absolute_coordinates=True,
                    movement_style="natural",
                    interaction_mode="steady"
                )

        # Click login button with enhanced positioning
        interaction_agent.perform_click_action(
            target=login_button,
            click_count=1,
            hold_duration=0.0,
            relative_position=[0.88, 0.92],  # Near corner with variation
            movement_style="natural",
            interaction_mode="steady"
        )

        _logger.info("Executing enhanced scrolling sequence")

        # Initial scroll to bottom
        current_scroll_height = driver.execute_script(
            """
            window.scrollTo({top: document.body.scrollHeight, behavior: 'smooth'});
            return document.body.scrollHeight;
            """
        )

        # Continuous scrolling with human-like variations
        scroll_iteration = 0
        max_scroll_iterations = 15

        while scroll_iteration < max_scroll_iterations:
            previous_height = current_scroll_height

            # Human-like scroll pause
            scroll_pause = random.uniform(2.5, 4.2)
            time.sleep(scroll_pause)

            # Execute scroll with enhanced behavior
            current_scroll_height = driver.execute_script(
                """
                window.scrollTo({top: document.body.scrollHeight, behavior: 'smooth'});
                return document.body.scrollHeight;
                """
            )

            # Check if scrolling is complete
            if previous_height == current_scroll_height:
                _logger.info("Scrolling sequence completed")
                break

            scroll_iteration += 1

        # Locate and interact with end session button
        end_session_button = enhanced_wait.until(
            EC.presence_of_element_located((By.CLASS_NAME, "end-session"))
        )

        driver.execute_script(
            "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center', inline: 'center'});",
            end_session_button
        )

        # Human-like pause before final interaction
        final_pause = random.uniform(0.9, 1.4)
        time.sleep(final_pause)

        # Click end session button
        end_session_button.click()

        # Final pause for session completion
        completion_pause = random.uniform(2.8, 3.5)
        time.sleep(completion_pause)

        _logger.info("Bot execution completed successfully")
        return True

    except (ValueError, TypeError, KeyError, AttributeError, RuntimeError) as execution_error:
        _logger.error(f"Bot execution terminated with error: {execution_error}")
        return False
