import numpy as np
import os
from scipy.spatial import ConvexHull

def calculate_max_noise(points):
    """
    Calculates the maximum noise value based on the convex hull of the input points (optimized).

    Args:
        points (numpy.ndarray): A 2D numpy array of points (shape: (n, 2)).

    Returns:
        float: The maximum noise value for the set of points.
    """
    if len(points) < 3:
        return 0.0  # Not enough points to form a hull; return zero noise

    hull = ConvexHull(points)
    hull_points = points[hull.vertices]
    hullX = hull_points[:, 0]
    hullY = hull_points[:, 1]
    num_vertices = len(hull_points)

    # The minimum vertical distance between two parallel lines enclosing all
    # points is attained when the lines' slope equals a convex hull edge slope.
    # For each edge slope m, that vertical distance is
    # max(y - m*x) - min(y - m*x), evaluated over the hull vertices
    # (the extremes always lie on the hull).
    best_noise = np.inf
    for i in range(num_vertices):
        j = (i + 1) % num_vertices  # include closing edge (last -> first)
        dx = hullX[j] - hullX[i]
        dy = hullY[j] - hullY[i]

        if abs(dx) < 1e-13:
            continue  # vertical edge: enclosing lines of infinite slope, skip

        slope = dy / dx
        residuals = hullY - slope * hullX
        vertical_spread = np.max(residuals) - np.min(residuals)
        if vertical_spread < best_noise:
            best_noise = vertical_spread

    return float(best_noise)