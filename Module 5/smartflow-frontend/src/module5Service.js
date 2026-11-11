
const API_BASE_URL = "http://127.0.0.1:8000";

export async function getSampleRoutes() {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/routes/sample`
  );

  if (!response.ok) {
    throw new Error(`Sample routes API failed: ${response.status}`);
  }

  return await response.json();
}

export async function recommendRoutes(origin, destination) {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/routes/recommend`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        origin,
        destination,
        traffic_aware: true,
      }),
    }
  );

  const data = await response.json();

  if (!response.ok) {
    throw new Error(
      data.detail || `Route recommendation failed: ${response.status}`
    );
  }

  return data;
}

export async function getRoadStatus() {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/traffic/road-status`
  );

  if (!response.ok) {
    throw new Error(`Road status API failed: ${response.status}`);
  }

  return await response.json();
}
