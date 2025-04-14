import numpy as np

# Create a 2D NumPy array that prints "HI"
arr = np.array([
    [1, 0, 0, 1, 0, 1, 1, 1],
    [1, 0, 0, 1, 0, 0, 1, 0],
    [1, 1, 1, 1, 0, 0, 1, 0],
    [1, 0, 0, 1, 0, 0, 1, 0],
    [1, 0, 0, 1, 0, 1, 1, 1]
])

# Print the array where 1 represents "#" and 0 represents " "
for row in arr:
    print("".join(['#' if pixel else ' ' for pixel in row]))