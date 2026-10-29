"""Where people live, and how far apart they are."""

import numpy as np

# Rough outline of the contiguous US (lon, lat). Used to keep sampled points on land.
US = [(-124.7, 48.4), (-122.8, 49), (-95.2, 49), (-94.8, 49.3), (-89.6, 48), (-84.9, 46.9), (-83.5, 46),
      (-82.5, 45.3), (-82.1, 43), (-79, 42.9), (-76.5, 44.2), (-74.9, 45), (-71.5, 45), (-70, 46.7), (-69.2, 47.4),
      (-67.8, 47.1), (-67, 44.8), (-70.6, 43.1), (-70.2, 41.7), (-73.7, 40.6), (-74, 39.6), (-75.5, 38.5), (-76, 37),
      (-75.5, 35.3), (-77.9, 33.9), (-80.9, 32.1), (-81.4, 30.7), (-80, 26.9), (-80.4, 25.2), (-81.8, 25.9),
      (-82.8, 27.9), (-84.3, 30), (-86.5, 30.4), (-89.6, 30.2), (-90.2, 29.1), (-93.8, 29.7), (-97.2, 27.7),
      (-97.4, 25.9), (-99.1, 26.4), (-101.4, 29.8), (-103.3, 29), (-104.7, 29.9), (-106.5, 31.8), (-108.2, 31.3),
      (-111, 31.3), (-114.8, 32.5), (-117.1, 32.5), (-118.5, 34), (-120.6, 34.6), (-122.5, 37.5), (-123.8, 39.8),
      (-124.2, 41.9), (-124.1, 43.7), (-124, 46.2)]

# (name, lon, lat, relative weight). Rough metro sizes; to be replaced by census figures.
METROS = [("New York, New York", -74, 40.7, 8), ("Los Angeles, California", -118.2, 34, 6),
          ("Chicago, Illinois", -87.6, 41.9, 4), ("Houston, Texas", -95.4, 29.8, 3),
          ("Phoenix, Arizona", -112, 33.4, 2.5), ("Philadelphia, Pennsylvania", -75.2, 40, 2),
          ("San Antonio, Texas", -98.5, 29.4, 2), ("San Diego, California", -117.2, 32.7, 2),
          ("Dallas, Texas", -96.8, 32.8, 3), ("Columbus, Ohio", -83, 40, 1.5), ("Seattle, Washington", -122.3, 47.6, 2),
          ("Atlanta, Georgia", -84.4, 33.7, 3), ("Miami, Florida", -80.2, 25.8, 3),
          ("Boston, Massachusetts", -71.1, 42.4, 2.5), ("San Francisco, California", -122.4, 37.8, 3),
          ("Detroit, Michigan", -83, 42.3, 2), ("Minneapolis, Minnesota", -93.3, 45, 1.5),
          ("Portland, Oregon", -122.7, 45.5, 1.5), ("Las Vegas, Nevada", -115.1, 36.2, 1.2),
          ("Charlotte, North Carolina", -80.8, 35.2, 1.5), ("St. Louis, Missouri", -90.2, 38.6, 1.2),
          ("Kansas City, Missouri", -94.6, 39.1, 1), ("Salt Lake City, Utah", -111.9, 40.8, 1),
          ("Nashville, Tennessee", -86.8, 36.2, 1.5), ("Denver, Colorado", -105, 39.7, 2),
          ("Austin, Texas", -97.7, 30.3, 2)]
SMALL_TOWN = "Small town"
SMALL_TOWN_SHARE = 0.2   # share of nationwide reach outside the listed metros
KM_PER_DEG = 111.0
# How far the real people behind one simulated person are spread around them.
METRO_SPREAD_KM = 25
CITY_SPREAD_KM = 8       # campus-led launches start tight
SMALL_TOWN_SPREAD_KM = 60


def inside_us(lon, lat):
    c = False
    j = len(US) - 1
    for i in range(len(US)):
        xi, yi = US[i]
        xj, yj = US[j]
        if (yi > lat) != (yj > lat) and lon < (xj - xi) * (lat - yi) / (yj - yi) + xi:
            c = not c
        j = i
    return c


def near(rng, lon, lat, spread_km):
    """A point around (lon, lat) that is on US land."""
    spread_deg = spread_km / KM_PER_DEG
    for _ in range(30):
        p = (lon + rng.normal(0, spread_deg), lat + rng.normal(0, spread_deg * 0.8))
        if inside_us(*p):
            return p
    return lon, lat


def nationwide(rng):
    """(place, lon, lat, spread_km) for one person reached by a nationwide channel."""
    if rng.random() < SMALL_TOWN_SHARE:
        while True:
            lon, lat = rng.uniform(-124, -67), rng.uniform(25, 49)
            if inside_us(lon, lat):
                return SMALL_TOWN, lon, lat, SMALL_TOWN_SPREAD_KM
    w = np.array([m[3] for m in METROS], float)
    name, lon, lat, _ = METROS[rng.choice(len(METROS), p=w / w.sum())]
    return (name, *near(rng, lon, lat, METRO_SPREAD_KM), METRO_SPREAD_KM)


def distance_km(lon_a, lat_a, lon_b, lat_b):
    """Pairwise distances (len(a) x len(b)), equirectangular per pair: fine at city scale."""
    lat0 = np.radians((lat_a[:, None] + lat_b[None, :]) / 2)
    dx = (lon_a[:, None] - lon_b[None, :]) * np.cos(lat0) * KM_PER_DEG
    dy = (lat_a[:, None] - lat_b[None, :]) * KM_PER_DEG
    return np.hypot(dx, dy)


US_AREA_KM2 = 8.08e6


def _blob(dist_km, spread_km, lambda_km):
    """E[K] from one person at distance d to a Gaussian crowd of width `spread_km`.

    K(d) = exp(-d/lambda) is taken as a Gaussian of the same mass (width lambda).
    """
    v = lambda_km ** 2 + spread_km ** 2
    return lambda_km ** 2 / v * np.exp(-dist_km ** 2 / (2 * v))


def nationwide_density(lon, lat, lambda_km):
    """E[K] between people at (lon, lat) and one person drawn like nationwide() draws."""
    w = np.array([m[3] for m in METROS], float)
    w /= w.sum()
    mlon = np.array([m[1] for m in METROS], float)
    mlat = np.array([m[2] for m in METROS], float)
    d = distance_km(lon, lat, mlon, mlat)
    metro = (_blob(d, METRO_SPREAD_KM, lambda_km) * w[None, :]).sum(axis=1)
    rural = 2 * np.pi * lambda_km ** 2 / US_AREA_KM2
    return (1 - SMALL_TOWN_SHARE) * metro + SMALL_TOWN_SHARE * rural


def city_density(lon, lat, city_lon, city_lat, spread_km, lambda_km):
    """E[K] between people at (lon, lat) and one person drawn around a city center."""
    d = distance_km(lon, lat, np.array([city_lon]), np.array([city_lat]))[:, 0]
    return _blob(d, spread_km, lambda_km)


def density_kernel(dist_km, spread_i, spread_j, lambda_km):
    """Expected nearness between the real people behind two simulated people.

    K(d) = exp(-d/lambda) is taken as a Gaussian of the same mass (width lambda) and
    blurred by both groups' spreads, so a sparse sample does not read as an empty map:
    K = l^2 / v * exp(-d^2 / 2v), v = l^2 + s_i^2 + s_j^2.
    """
    v = lambda_km ** 2 + spread_i[:, None] ** 2 + spread_j[None, :] ** 2
    return lambda_km ** 2 / v * np.exp(-dist_km ** 2 / (2 * v))
