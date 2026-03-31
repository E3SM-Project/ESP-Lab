import numpy as np
from global_land_mask import globe
print("testing -10:", globe.is_land(50, -10))
print("testing 350:", globe.is_land(50, 350))
