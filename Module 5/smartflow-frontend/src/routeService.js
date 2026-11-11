
const OSRM_BASE_URL =
  'https://router.project-osrm.org/route/v1/driving';

/**
 * Validates [longitude, latitude] coordinates.
 */
function isValidCoordinates(coordinates) {
  return (
    Array.isArray(coordinates) &&
    coordinates.length === 2 &&
    Number.isFinite(coordinates[0]) &&
    Number.isFinite(coordinates[1]) &&
    coordinates[0] >= -180 &&
    coordinates[0] <= 180 &&
    coordinates[1] >= -90 &&
    coordinates[1] <= 90
  );
}

/**
 * Calculates driving routes between two coordinates.
 * Routes are sorted by estimated travel time, fastest first.
 * OSRM durations are estimates, not live traffic predictions.
 */
export async function getRoute(start, end) {
  if (!isValidCoordinates(start) || !isValidCoordinates(end)) {
    throw new Error(
      'Please provide valid [longitude, latitude] coordinates.'
    );
  }

  const coordinates =
    `${start[0]},${start[1]};${end[0]},${end[1]}`;

  const url =
    `${OSRM_BASE_URL}/${coordinates}` +
    '?overview=full&geometries=geojson&alternatives=true&steps=true';

  let response;

  try {
    response = await fetch(url);
  } catch {
    throw new Error(
      'Could not connect to OSRM. Check your internet connection and try again.'
    );
  }

  if (!response.ok) {
    throw new Error(
      `OSRM request failed with HTTP ${response.status}. Please try again later.`
    );
  }

  let data;

  try {
    data = await response.json();
  } catch {
    throw new Error(
      'The routing service returned an invalid response. Please try again.'
    );
  }

  if (data.code !== 'Ok' || !Array.isArray(data.routes)) {
    throw new Error(
      data.message || 'No driving route was found.'
    );
  }

  if (data.routes.length === 0) {
    throw new Error(
      'No driving routes are available for this journey.'
    );
  }

  const validRoutes = data.routes.filter((route) => {
    const routeCoordinates = route.geometry?.coordinates;

    return (
      Number.isFinite(route.distance) &&
      route.distance >= 0 &&
      Number.isFinite(route.duration) &&
      route.duration >= 0 &&
      Array.isArray(routeCoordinates) &&
      routeCoordinates.length >= 2 &&
      routeCoordinates.every(
        (point) =>
          Array.isArray(point) &&
          point.length >= 2 &&
          Number.isFinite(point[0]) &&
          Number.isFinite(point[1]) &&
          point[0] >= -180 &&
          point[0] <= 180 &&
          point[1] >= -90 &&
          point[1] <= 90
      )
    );
  });

  if (validRoutes.length === 0) {
    throw new Error(
      'The routing service did not return any valid route geometry.'
    );
  }

  const sortedRoutes = [...validRoutes].sort(
    (a, b) => a.duration - b.duration
  );

  const fastestDurationSeconds = sortedRoutes[0].duration;
  const fastestDurationMinutes = Math.round(
    fastestDurationSeconds / 60
  );

  return sortedRoutes.map((route, index) => {
    const durationMinutes = Math.round(route.duration / 60);

    // Calculate time differences using the original seconds
    // to reduce rounding errors.
    const extraMinutesComparedToFastest = Math.max(
      0,
      Math.round(
        (route.duration - fastestDurationSeconds) / 60
      )
    );

    return {
      id: index + 1,
      distanceKm: Number(
        (route.distance / 1000).toFixed(2)
      ),
      durationMinutes,
      extraMinutesComparedToFastest,
      minutesSavedComparedToRoute:
        extraMinutesComparedToFastest,
      coordinates: route.geometry.coordinates.map(
        ([longitude, latitude]) => [latitude, longitude]
      ),
      isRecommended: index === 0,
      recommendationReason:
        index === 0
          ? 'Fastest available route based on estimated travel time.'
          : `${extraMinutesComparedToFastest} additional estimated minute(s) compared with the fastest route.`,
    };
  });
}
