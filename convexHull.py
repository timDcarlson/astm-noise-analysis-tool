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
    hull_indices_original = hull.vertices  
    hull_points = points[hull_indices_original]

    K = np.arange(len(hull_points))  

    hullX = hull_points[K, 0]
    hullY = hull_points[K, 1]

    cos_angle = np.zeros(len(K) - 1)
    sin_angle = np.zeros(len(K) - 1)
    noiseList = []

    for i in range(len(K) - 1):
        dx = hullX[i + 1] - hullX[i]
        dy = hullY[i + 1] - hullY[i]
        vector = np.array([dx, dy])
        norm_vector = np.linalg.norm(vector)

        if norm_vector < 1e-13:  # Avoid division by zero
            cos_angle[i] = dx*1e13
            sin_angle[i] = dy*1e13
        else:
            cos_angle[i] = dx / norm_vector
            sin_angle[i] = dy / norm_vector

        rotated_hull_points = []
        rotationMatrix = np.array([
            [cos_angle[i], -sin_angle[i]],
            [sin_angle[i], cos_angle[i]]
        ])
        
        # Rotate all hull points
        rotated_points = np.column_stack((hullX, hullY)) @ rotationMatrix.T

        # Take max-min of the y-column (vertical spread after rotation)
        max_y = np.max(rotated_points[:, 1])
        min_y = np.min(rotated_points[:, 1])
        if abs(cos_angle[i]) > 1e-13:
            noise_range = (max_y - min_y) / cos_angle[i]
        else:
            noise_range = 1e13  # or np.nan, or another value that makes sense for your use case
        noiseList.append(abs(noise_range))


    return np.min(noiseList)