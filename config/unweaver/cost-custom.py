"""Defines cost function generators for optimal path finding."""
from datetime import datetime
import math
import humanized_opening_hours as hoh
import pytz

# Default base moving speeds for different modes. All in m/s.
# Slightly lower than average walking speed
WALK_BASE = 1.3  # Rough estimate
WHEELCHAIR_BASE = 0.6
# Roughly 5 mph
POWERED_BASE = 2

# 1 / DIVISOR = speed where cutoff starts to apply, dictates exponential"s k.
DIVISOR = 5

# "fastest" incline. -0.0087 is straight from Tobler"s hiking function
INCLINE_IDEAL = -0.0087

STREET_TYPES = [
    "secondary",
    "tertiary",
    "residential",
    "service",
]


def find_k(g, m, n):
    return math.log(n) / abs(g - m)


def tobler(grade, k=3.5, m=INCLINE_IDEAL, base=WALK_BASE):
    # Modified to be in meters / second rather than km / h
    return base * math.exp(-k * abs(grade - m))


def street_avoidance_function(streetAvoidance, k=1):
    if streetAvoidance >= 1:
        return None

    return math.exp(k * streetAvoidance)


def cost_fun_generator(
    G,
    base_speed=WALK_BASE,
    downhill=0.1,
    uphill=0.085,
    avoidCurbs=False,
    timestamp=None,
    streetAvoidance=1,
):
    """Calculates a cost-to-travel that balances distance vs. steepness vs.
    needing to cross the street.

    :param downhill: Maximum downhill incline indicated by the user, e.g.
                     0.1 for 10% downhill.
    :type downhill: float
    :param uphill: Positive incline (uphill) maximum, as grade.
    :type uphill: float
    :param avoidCurbs: Whether curb ramps should be avoided.
    :type avoidCurbs: bool

    """
    k_down = find_k(-downhill, INCLINE_IDEAL, DIVISOR)
    k_up = find_k(uphill, INCLINE_IDEAL, DIVISOR)

    if timestamp is None:
        date = datetime.now(pytz.timezone("US/Pacific"))
    else:
        # Unix epoch time is sent in integer format, but is in milliseconds.
        # Divide by 1000 to get seconds.
        date = datetime.fromtimestamp(timestamp / 1000, pytz.timezone("US/Pacific"))

    def cost_fun(u, v, d):
        """Cost function that evaluates every edge, returning either a
        nonnegative cost or None. Returning a value of None implies an infinite
        cost, i.e. that edge will be excluded from any paths.

        :param u: incoming node ID
        :type u: int
        :param v: ougoing node ID
        :type v: int
        :param d: The edge to evaluate.
        :type d: dict
        :returns: Cost of traversing the edge
        :rtype: float or None

        """
        time = 0
        speed = base_speed
        street_cost_factor = 1

        length = d["length"]
        highway = d["highway"]

        if highway == "footway":
            if d.get("footway") == "crossing":
                # Is a crossing
                if avoidCurbs:
                    if "curbramps" in d:
                        if not d["curbramps"]:
                            return None
                    else:
                        return None
                time += 30
            else:
                if d.get("elevator", False):
                    # Path includes an elevator
                    opening_hours = d["opening_hours"]
                    # Add delay for using the elevator
                    time += 45
                    # See if the elevator has limited hours
                    try:
                        oh = hoh.OHParser(opening_hours)
                        if not oh.is_open(date):
                            return None
                    except KeyError:
                        # 'opening_hours' isn't on this elevator path
                        pass
                    except ValueError:
                        # 'opening_hours' is None (better option for checking?)
                        pass
                    except Exception:
                        # Something else went wrong. TODO: give a useful
                        # message back?
                        return None
                else:
                    pass
        elif highway in STREET_TYPES:
            """
            A street avoidance function should have these properties:
                - When 0, it should not change the cost at all
                - When 1, it should apply an infinite cost to all streets
                - When intermediate (say 0.5), it should apply a modest cost
                increase.
                - The cost should increase monotonically from 0 to 1 and
                probably be exponential-ish.

            As a factor, the output of this function will be multiplied against
            the final cost. Therefore:
                - When the input is 0, the function should be 1
                - When the input is 1, the function should be Inf/None (it is
                okay for the function to be piecewise).
                - When the input is between 0 and 1, the output should be a
                number larger than 1 and monotonically increasing.

                A function that satisfies these conditions is a simple
                exponential/cubic/quartic (etc) function offset in the y axis
                by y=1 and with a piecewise component that returns infinity
                at x=1.
            """
            if highway == "pedestrian":
                # Pedestrian streets are good, use them with no extra cost
                # (Using 'abs' to ensure non-negative)
                street_cost_factor = 1
            elif highway == "service":
                # Slight extra cost for using a service road (includes alleys
                # and driveways and parking lots)
                street_cost_factor = street_avoidance_function(streetAvoidance, 2)
            elif highway == "residential":
                # It's a residential street and hopefully somewhat accessible.
                # Apply a slightly higher cost.
                street_cost_factor = street_avoidance_function(streetAvoidance, 3)
            else:
                # Apply a much higher cost to the other roads
                street_cost_factor = street_avoidance_function(streetAvoidance, 4)
        else:
            # Unknown path type: do not use
            return None

        if street_cost_factor is None:
            return None

        # Handle all other ways as incline-having features
        if "incline" in d and d["incline"] is not None:
            incline = float(d["incline"])

            # Decrease speed based on incline
            if length > 3:
                # If the path is very short, ignore incline due to
                # likelihood that it is incorrectly estimated.
                if (incline > uphill) or (incline < -downhill):
                    return None
            if incline > INCLINE_IDEAL:
                speed = tobler(
                    incline,
                    k=k_up,
                    m=INCLINE_IDEAL,
                    base=base_speed,
                )
            else:
                speed = tobler(
                    incline,
                    k=k_down,
                    m=INCLINE_IDEAL,
                    base=base_speed,
                )

        # TODO: investigate why this value could happen. Tobler shouldn't
        # return 0 speed, but it did once!
        if speed == 0:
            return None
        # Initial time estimate (in seconds) - based on speed
        time += length / speed

        cost = street_cost_factor * time

        return cost

    return cost_fun
