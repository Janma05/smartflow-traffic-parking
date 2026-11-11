
const API_BASE_URL = 'http://127.0.0.1:8000';

export async function getTrafficFlow(latitude, longitude) {
  if (
    !Number.isFinite(latitude) ||
    latitude < -90 ||
    latitude > 90 ||
    !Number.isFinite(longitude) ||
    longitude < -180 ||
    longitude > 180
  ) {
    throw new Error('Please provide valid latitude and longitude.');
  }

  const params = new URLSearchParams({
    lat: String(latitude),
    lon: String(longitude),
  });

  let response;

  try {
    response = await fetch(
      `${API_BASE_URL}/api/traffic/flow?${params.toString()}`
    );
  } catch {
    throw new Error(
      'Cannot connect to the SmartFlow backend. Check that FastAPI is running.'
    );
  }

  let data;

  try {
    data = await response.json();
  } catch {
    throw new Error('The backend returned an invalid response.');
  }

  if (!response.ok) {
    const detail =
      typeof data.detail === 'string'
        ? data.detail
        : `HTTP ${response.status}`;

    throw new Error(detail);
  }

  return data;
}
