#!/usr/bin/env python3
"""
Debug script to investigate why reference channel noise > 1200 isn't being flagged
"""

import numpy as np
import os
import sys
sys.path.append(r'C:\Users\tim.carlson\OneDrive\Desktop\Work\D2\Lamp analysis\python noise analysis code')

from convexHull import calculate_max_noise

def analyze_single_file(filename):
    """Analyze a single file to debug noise detection"""
    print(f"Analyzing file: {filename}")
    
    # Load the data
    data = np.loadtxt(filename, delimiter='\t', skiprows=1)
    times = data[:, 0]
    
    # Extract main and reference channels (same as in ASTMnoise.py)
    pointsMain = np.column_stack((times, data[:, 2]))  # CHNL0_End
    pointsRef = np.column_stack((times, data[:, 4]))   # CHNL1_End
    
    print(f"Data shape: {data.shape}")
    print(f"Time range: {times[0]:.2f} to {times[-1]:.2f} seconds")
    print(f"Main channel range: {data[:, 2].min():.0f} to {data[:, 2].max():.0f}")
    print(f"Reference channel range: {data[:, 4].min():.0f} to {data[:, 4].max():.0f}")
    
    # Calculate subset size (same logic as ASTMnoise.py)
    num_rows = len(data)
    if num_rows < 2:
        subset_size = 100
    else:
        delta_val = abs(data[1, 0] - data[0, 0])
        subset_size = max(3, int(30 / (delta_val if delta_val > 1e-9 else 0.15)))
    
    print(f"Subset size: {subset_size}")
    
    def process_channel(points, channel_name):
        noise_values = []
        max_noise = 0
        max_noise_time = 0
        
        points_len = len(points)
        for i in range(0, points_len, subset_size):
            if i + subset_size > points_len:
                break
                
            subset = points[i:i + subset_size]
            subset = np.round(subset, decimals=2)
            
            if len(subset) > 2:
                noise_val = calculate_max_noise(subset)
                noise_values.append(noise_val)
                
                if noise_val > max_noise:
                    max_noise = noise_val
                    max_noise_time = subset[0, 0]
                    
                if noise_val > 1200:
                    print(f"  {channel_name} HIGH NOISE: {noise_val:.2f} at time {subset[0, 0]:.2f}s")
        
        return noise_values, max_noise, max_noise_time
    
    # Process both channels
    main_noise, main_max, main_max_time = process_channel(pointsMain, "Main")
    ref_noise, ref_max, ref_max_time = process_channel(pointsRef, "Reference")
    
    print(f"\nResults:")
    print(f"Main channel: {len(main_noise)} intervals, max noise = {main_max:.2f} at {main_max_time:.2f}s")
    print(f"Reference channel: {len(ref_noise)} intervals, max noise = {ref_max:.2f} at {ref_max_time:.2f}s")
    
    # Check for intervals > 1200
    main_high = [n for n in main_noise if n > 1200]
    ref_high = [n for n in ref_noise if n > 1200]
    
    print(f"\nHigh noise intervals (> 1200):")
    print(f"Main channel: {len(main_high)} intervals")
    print(f"Reference channel: {len(ref_high)} intervals")
    
    if ref_high:
        print(f"Reference high noise values: {ref_high}")
    
    return main_max, ref_max

if __name__ == "__main__":
    # Test with the file that should have high reference noise
    test_file = "2025-07-02_17-31-49_DataCollection.txt"
    if os.path.exists(test_file):
        analyze_single_file(test_file)
    else:
        print(f"File not found: {test_file}")
        print("Available files:")
        for f in os.listdir("."):
            if f.endswith("_DataCollection.txt"):
                print(f"  {f}")
