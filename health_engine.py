"""
Core analysis logic: health score + fault classification.
Same rules as the dashboard, kept here in Python so reports/alerts
use identical logic to what's shown on the webpage.

voltage and oil can be None when the active data source doesn't
provide them (e.g. the real ETT dataset has no voltage/oil columns).
In that case those parameters are simply left out of the calculation
instead of being guessed - the health score becomes a partial
estimate based on whatever real data is actually available.
"""

import config

TH = config.THRESHOLDS


def compute_health(temp, current, voltage=None, oil=None):
    temp_pen = max(0, (temp - TH["max_temp"]) * 1.5)
    curr_pen = max(0, (current - TH["max_current"]) * 3)
    volt_pen = abs(voltage - TH["nominal_voltage"]) * 0.6 if voltage is not None else 0
    oil_pen = max(0, (TH["min_oil"] + 10 - oil) * 1.2) if oil is not None else 0
    score = 100 - temp_pen - curr_pen - volt_pen - oil_pen
    return max(0, min(100, round(score)))


def classify_fault(temp, current, voltage, oil, health):
    if health >= 80:
        return "good", "Normal", "All parameters within safe range."
    if temp > TH["max_temp"] and current <= TH["max_current"]:
        return "warn", "Cooling Issue", (
            f"Temperature crossed {TH['max_temp']}C while current is normal "
            "- check cooling system / fan."
        )
    if current > TH["max_current"]:
        return "bad", "Overload", (
            f"Current draw ({current}A) exceeds limit ({TH['max_current']}A) "
            "- reduce load or check wiring."
        )
    if voltage is not None and abs(voltage - TH["nominal_voltage"]) > TH["max_voltage_dev"]:
        return "warn", "Voltage Fluctuation", (
            f"Supply voltage deviates {abs(voltage - TH['nominal_voltage']):.0f}V "
            "from nominal - check grid supply."
        )
    if oil is not None and oil < TH["min_oil"]:
        return "bad", "Low Oil", (
            f"Oil level ({oil}%) below minimum threshold - inspect/refill."
        )
    return "warn", "Minor Deviation", "One or more parameters slightly off normal."
