

import mss
for index, monitor in enumerate(mss.mss().monitors[1:], 1):
    print(f"Monitor {index}: {monitor}")