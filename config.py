"""
SMC Ground Pressure - Configuration & Constants
"""

# PHYSICS CONSTANTS
G_CONST = 9.81  # Gravity (m/s^2)

# SOLVER SETTINGS
SOIL_KS_DEFAULT = 30000  # Default Soil Modulus (kN/m^3)
SOLVER_TOLERANCE = 1e-6
SOLVER_MAX_ITERS = 100

# UI COLORS
COLOR_BG_APP = '#ffffff'
COLOR_TEXT_MAIN = '#1e293b' # Slate 800
COLOR_TEXT_SEC = '#64748b'  # Slate 500
COLOR_ACCENT = '#0284c7'    # Sky 600
COLOR_SAFE = '#16a34a'      # Green 600
COLOR_DANGER = '#dc2626'    # Red 600
COLOR_STEEL = '#94a3b8'
COLOR_TRACK_OUTLINE = '#334155'
COLOR_MAT = '#f1f5f9'
COLOR_MAT_BORDER = '#94a3b8'
COLOR_DIM_LINE = '#64748b'

# POLAR CHART SETTINGS
POLAR_RESOLUTION_DEG = 5  # Step size for polar chart (degrees)
