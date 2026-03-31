import numpy as np

vals = np.array([89, 87, 85])
mid = 0.5 * (vals[1:] + vals[:-1])
first = vals[0] - 0.5 * (vals[1] - vals[0])
last = vals[-1] + 0.5 * (vals[-1] - vals[-2])
bounds = np.concatenate([[first], mid, [last]])
bounds = np.clip(bounds, -90.0, 90.0)
print(bounds)
