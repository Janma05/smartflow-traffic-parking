
import { useState } from 'react';
import TrafficMap from './TrafficMap';
import { getRoute } from './routeService';

const GEOCODING_URL =
  'https://nominatim.openstreetmap.org/search';

// ==========================================
// DEMO TRAFFIC CONFIGURATION
// ==========================================

const CONGESTION_CONFIG = {
  low: {
    label: 'Low congestion',
    score: 1,
    color: '#16a34a',
  },
  moderate: {
    label: 'Moderate congestion',
    score: 2,
    color: '#eab308',
  },
  high: {
    label: 'High congestion',
    score: 3,
    color: '#dc2626',
  },
};

// Same deterministic demo-level logic used by TrafficMap.jsx.
function getDemoCongestion(routeId) {
  if (routeId % 3 === 0) return 'low';
  if (routeId % 2 === 0) return 'high';
  return 'moderate';
}

// ==========================================
// LOCATION SEARCH
// ==========================================

async function findLocation(location) {
  const url =
    `${GEOCODING_URL}?format=jsonv2&limit=5&addressdetails=1&accept-language=en&q=${encodeURIComponent(location)}`;

  let response;

  try {
    response = await fetch(url);
  } catch {
    throw new Error(
      'Could not connect to location search. Check your internet connection.'
    );
  }

  if (!response.ok) {
    throw new Error(
      `Location search failed (HTTP ${response.status}).`
    );
  }

  let results;

  try {
    results = await response.json();
  } catch {
    throw new Error(
      'Location search returned an invalid response. Please try again.'
    );
  }

  if (!Array.isArray(results) || results.length === 0) {
    throw new Error(`Location not found: ${location}`);
  }

  const locations = results
    .map((result) => {
      const latitude = Number(result.lat);
      const longitude = Number(result.lon);

      if (
        !Number.isFinite(latitude) ||
        !Number.isFinite(longitude) ||
        latitude < -90 ||
        latitude > 90 ||
        longitude < -180 ||
        longitude > 180
      ) {
        return null;
      }

      return {
        name: result.display_name || location,
        coordinates: [longitude, latitude],
      };
    })
    .filter(Boolean);

  if (locations.length === 0) {
    throw new Error(
      `No valid location coordinates found for: ${location}`
    );
  }

  return locations;
}

// ==========================================
// ROUTE RECOMMENDATION
// ==========================================

function recommendRoutes(osrmRoutes) {
  const routesWithTraffic = osrmRoutes.map(
    (route, index) => {
      const id = route.id ?? index + 1;
      const congestionLevel = getDemoCongestion(id);
      const congestion =
        CONGESTION_CONFIG[congestionLevel];

      return {
        ...route,
        id,
        congestionLevel,
        congestionScore: congestion.score,
        congestionLabel: congestion.label,
        trafficDelayMinutes: 0,
        isRecommended: false,
        recommendationReason: '',
      };
    }
  );

  // Prefer lower demo congestion.
  // If congestion is equal, prefer shorter estimated travel time.
  const sortedRoutes = [...routesWithTraffic].sort(
    (a, b) =>
      a.congestionScore - b.congestionScore ||
      a.durationMinutes - b.durationMinutes
  );

  const recommendedRouteId = sortedRoutes[0]?.id;

  return routesWithTraffic.map((route) => {
    const isRecommended =
      route.id === recommendedRouteId;

    let recommendationReason;

    if (isRecommended && route.congestionLevel === 'low') {
      recommendationReason =
        'Recommended: lowest demo congestion level among the available routes.';
    } else if (
      isRecommended &&
      route.congestionLevel === 'moderate'
    ) {
      recommendationReason =
        'Recommended: best available demo congestion level, with travel time considered.';
    } else if (
      isRecommended &&
      route.congestionLevel === 'high'
    ) {
      recommendationReason =
        'Recommended: no lower-congestion alternative was available in the returned routes.';
    } else {
      recommendationReason =
        'Alternative route. Compare its congestion level and estimated travel time with the recommended route.';
    }

    return {
      ...route,
      isRecommended,
      recommendationReason,
    };
  });
}

// ==========================================
// MAIN ROUTE DASHBOARD
// ==========================================

function RouteDashboard() {
  const [source, setSource] = useState('');
  const [destination, setDestination] = useState('');

  const [selectedSource, setSelectedSource] = useState(null);
  const [selectedDestination, setSelectedDestination] =
    useState(null);

  const [sourceSuggestions, setSourceSuggestions] = useState([]);
  const [destinationSuggestions, setDestinationSuggestions] =
    useState([]);

  const [resolvedLocations, setResolvedLocations] = useState(null);
  const [routes, setRoutes] = useState([]);
  const [selectedRouteId, setSelectedRouteId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [searchingField, setSearchingField] = useState('');
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  const selectedRoute = routes.find(
    (route) => route.id === selectedRouteId
  );

  const recommendedRoute = routes.find(
    (route) => route.isRecommended
  );

  const clearRouteResults = () => {
    setRoutes([]);
    setSelectedRouteId(null);
    setResolvedLocations(null);
  };

  // ==========================================
  // INPUT HANDLERS
  // ==========================================

  const handleSourceChange = (event) => {
    setSource(event.target.value);
    setSelectedSource(null);
    setSourceSuggestions([]);
    setError('');
    setNotice('');
    clearRouteResults();
  };

  const handleDestinationChange = (event) => {
    setDestination(event.target.value);
    setSelectedDestination(null);
    setDestinationSuggestions([]);
    setError('');
    setNotice('');
    clearRouteResults();
  };

  const handleSelectSource = (location) => {
    setSelectedSource(location);
    setSource(location.name);
    setSourceSuggestions([]);
    setError('');
    setNotice('Starting location selected.');
    clearRouteResults();
  };

  const handleSelectDestination = (location) => {
    setSelectedDestination(location);
    setDestination(location.name);
    setDestinationSuggestions([]);
    setError('');
    setNotice('Destination selected.');
    clearRouteResults();
  };

  const handleClearRoute = () => {
    if (loading) return;

    setSource('');
    setDestination('');
    setSelectedSource(null);
    setSelectedDestination(null);
    setSourceSuggestions([]);
    setDestinationSuggestions([]);
    setResolvedLocations(null);
    setRoutes([]);
    setSelectedRouteId(null);
    setError('');
    setNotice('');
    setSearchingField('');
  };

  const handleSwapLocations = () => {
    if (loading) return;

    setSource(destination);
    setDestination(source);

    setSelectedSource(selectedDestination);
    setSelectedDestination(selectedSource);

    setSourceSuggestions([]);
    setDestinationSuggestions([]);
    setResolvedLocations(null);
    setRoutes([]);
    setSelectedRouteId(null);
    setError('');
    setNotice('');
  };

  // ==========================================
  // LOCATION SEARCH HANDLER
  // ==========================================

  const handleSearchLocation = async (field) => {
    if (loading) return;

    const isSource = field === 'source';
    const query = (isSource ? source : destination).trim();

    if (!query) {
      setError(
        `Please enter a ${
          isSource ? 'starting location' : 'destination'
        }.`
      );
      setNotice('');
      return;
    }

    setLoading(true);
    setSearchingField(field);
    setError('');
    setNotice('');
    clearRouteResults();

    if (isSource) {
      setSelectedSource(null);
      setSourceSuggestions([]);
    } else {
      setSelectedDestination(null);
      setDestinationSuggestions([]);
    }

    try {
      const results = await findLocation(query);

      if (isSource) {
        setSourceSuggestions(results);
        setNotice(
          'Choose the correct starting location from the results.'
        );
      } else {
        setDestinationSuggestions(results);
        setNotice(
          'Choose the correct destination from the results.'
        );
      }
    } catch (err) {
      setError(
        err.message || 'Location search failed. Please try again.'
      );
    } finally {
      setLoading(false);
      setSearchingField('');
    }
  };

  // ==========================================
  // OSRM ROUTE CALCULATION
  // ==========================================

  const handleExploreRoutes = async () => {
    if (loading) return;

    if (!source.trim() || !destination.trim()) {
      setError(
        'Please enter both a starting location and a destination.'
      );
      setNotice('');
      return;
    }

    if (!selectedSource || !selectedDestination) {
      setError(
        'Please search for and select both locations before calculating routes.'
      );
      setNotice('');
      return;
    }

    setLoading(true);
    setError('');
    setNotice('');
    clearRouteResults();

    try {
      const osrmRoutes = await getRoute(
        selectedSource.coordinates,
        selectedDestination.coordinates
      );

      if (
        !Array.isArray(osrmRoutes) ||
        osrmRoutes.length === 0
      ) {
        throw new Error('No routes were returned by OSRM.');
      }

      const calculatedRoutes = recommendRoutes(osrmRoutes);

      setResolvedLocations({
        source: selectedSource.name,
        destination: selectedDestination.name,
      });

      setRoutes(calculatedRoutes);

      // Automatically select the recommended route.
      const bestRoute = calculatedRoutes.find(
        (route) => route.isRecommended
      );

      setSelectedRouteId(bestRoute?.id ?? calculatedRoutes[0].id);

      setNotice(
        'Routes calculated using OSRM and ranked using illustrative demo congestion levels. Traffic is not live.'
      );
    } catch (err) {
      setError(
        err.message ||
          'Unable to calculate routes. Please try again.'
      );
    } finally {
      setLoading(false);
    }
  };

  // ==========================================
  // LOCATION SUGGESTION STYLE
  // ==========================================

  const suggestionStyle = {
    display: 'block',
    width: '100%',
    padding: '10px 12px',
    marginTop: '6px',
    textAlign: 'left',
    border: '1px solid #475569',
    borderRadius: '8px',
    background: 'transparent',
    color: 'inherit',
    fontSize: '13px',
    lineHeight: 1.5,
    cursor: 'pointer',
    overflowWrap: 'anywhere',
  };

  // =====================================
  // UI
  // =====================================

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <h2 className="brand">
          TraffiQ<span>.</span>
        </h2>

        <p className="sidebar-label">
          TRAFFIC MANAGEMENT
        </p>

        <nav className="navigation">
          <a href="#overview">Overview</a>
          <a href="#traffic">Traffic Map</a>
          <a href="#routes" className="active">
            Route Recommendation
          </a>
          <a href="#parking">Smart Parking</a>
        </nav>

        <div className="sidebar-footer">
          <span className="status-dot" />
          Route planning workspace
        </div>
      </aside>

      <main className="main-content" id="routes">
        <header className="topbar">
          <div>
            <p className="eyebrow">
              SMART MOBILITY PLATFORM
            </p>

            <h1>Route Recommendation</h1>

            <p className="subtitle">
              Search locations, compare driving routes,
              and view demo congestion levels.
            </p>
          </div>

          <div className="live-badge">
            <span className="status-dot" />
            Route planning
          </div>
        </header>

        <section className="route-layout">
          <div className="route-panel">
            <div className="section-heading">
              <div>
                <p className="eyebrow">
                  PLAN YOUR JOURNEY
                </p>

                <h2>Find the best route</h2>
              </div>

              <span className="route-icon">↗</span>
            </div>

            <label htmlFor="source">
              Starting location
            </label>

            <input
              id="source"
              type="text"
              value={source}
              onChange={handleSourceChange}
              placeholder="e.g. Bengaluru City Railway Station"
              disabled={loading}
              autoComplete="off"
            />

            <button
              type="button"
              className="clear-button"
              onClick={() => handleSearchLocation('source')}
              disabled={loading}
            >
              {loading && searchingField === 'source'
                ? 'Searching...'
                : 'Search starting location'}
            </button>

            {sourceSuggestions.length > 0 && (
              <div
                className="location-suggestions"
                aria-label="Starting location search results"
              >
                <p>
                  <strong>
                    Choose the starting location
                  </strong>
                </p>

                {sourceSuggestions.map((location, index) => (
                  <button
                    key={`${location.coordinates.join(',')}-${index}`}
                    type="button"
                    style={suggestionStyle}
                    onClick={() => handleSelectSource(location)}
                    disabled={loading}
                  >
                    {location.name}
                  </button>
                ))}
              </div>
            )}

            {selectedSource && (
              <p className="selection-status">
                <span aria-hidden="true">✓ </span>
                Starting location selected
              </p>
            )}

            <button
              type="button"
              className="swap-button"
              onClick={handleSwapLocations}
              disabled={
                loading ||
                (!source.trim() && !destination.trim())
              }
              aria-label="Swap starting location and destination"
            >
              ⇅ Swap locations
            </button>

            <label htmlFor="destination">
              Destination
            </label>

            <input
              id="destination"
              type="text"
              value={destination}
              onChange={handleDestinationChange}
              placeholder="e.g. Vidhana Soudha, Bengaluru"
              disabled={loading}
              autoComplete="off"
            />

            <button
              type="button"
              className="clear-button"
              onClick={() => handleSearchLocation('destination')}
              disabled={loading}
            >
              {loading && searchingField === 'destination'
                ? 'Searching...'
                : 'Search destination'}
            </button>

            {destinationSuggestions.length > 0 && (
              <div
                className="location-suggestions"
                aria-label="Destination search results"
              >
                <p>
                  <strong>Choose the destination</strong>
                </p>

                {destinationSuggestions.map((location, index) => (
                  <button
                    key={`${location.coordinates.join(',')}-${index}`}
                    type="button"
                    style={suggestionStyle}
                    onClick={() =>
                      handleSelectDestination(location)
                    }
                    disabled={loading}
                  >
                    {location.name}
                  </button>
                ))}
              </div>
            )}

            {selectedDestination && (
              <p className="selection-status">
                <span aria-hidden="true">✓ </span>
                Destination selected
              </p>
            )}

            <div className="route-actions">
              <button
                type="button"
                className="primary-button"
                onClick={handleExploreRoutes}
                disabled={loading}
              >
                {loading
                  ? 'Processing...'
                  : 'Explore routes'}

                {!loading && <span> →</span>}
              </button>

              <button
                type="button"
                className="clear-button"
                onClick={handleClearRoute}
                disabled={loading}
              >
                Clear route
              </button>
            </div>

            {error && (
              <p role="alert" className="route-error">
                {error}
              </p>
            )}

            {notice && (
              <p className="route-notice" role="status">
                {notice}
              </p>
            )}

            {routes.length > 0 && (
              <div
                className="route-results"
                aria-live="polite"
              >
                <h3>Available routes</h3>

                {routes.map((route, index) => {
                  const isSelected =
                    route.id === selectedRouteId;

                  const congestion =
                    CONGESTION_CONFIG[route.congestionLevel];

                  const extraMinutes =
                    Number(route.extraMinutesComparedToFastest) || 0;

                  return (
                    <button
                      type="button"
                      key={route.id}
                      className={`route-result ${
                        isSelected ? 'selected' : ''
                      }`}
                      onClick={() =>
                        setSelectedRouteId(route.id)
                      }
                      aria-pressed={isSelected}
                    >
                      <strong>
                        {route.isRecommended
                          ? 'Recommended route'
                          : `Alternative route ${index + 1}`}
                      </strong>

                      {isSelected && (
                        <span> — Selected</span>
                      )}

                      <p>
                        Distance: {route.distanceKm} km
                      </p>

                      <p>
                        Estimated time: {route.durationMinutes} min
                      </p>

                      <p>
                        Demo congestion:{' '}
                        <span
                          style={{
                            color: congestion.color,
                            fontWeight: 700,
                          }}
                        >
                          {congestion.label}
                        </span>
                      </p>

                      {extraMinutes > 0 && (
                        <p className="route-time-difference">
                          +{extraMinutes} min compared with the fastest route
                        </p>
                      )}

                      {route.isRecommended && (
                        <p className="route-time-difference recommended">
                          ✓ Recommended based on demo congestion
                        </p>
                      )}

                      <p className="recommendation-reason">
                        {route.recommendationReason}
                      </p>
                    </button>
                  );
                })}

                {selectedRoute && (
                  <div className="selected-route-summary">
                    <h3>Selected route summary</h3>

                    <p>
                      <strong>From:</strong>{' '}
                      {resolvedLocations?.source}
                    </p>

                    <p>
                      <strong>To:</strong>{' '}
                      {resolvedLocations?.destination}
                    </p>

                    <p>
                      <strong>Route:</strong>{' '}
                      {selectedRoute.isRecommended
                        ? 'Recommended route'
                        : 'Alternative route'}
                    </p>

                    <p>
                      <strong>Distance:</strong>{' '}
                      {selectedRoute.distanceKm} km
                    </p>

                    <p>
                      <strong>Estimated time:</strong>{' '}
                      {selectedRoute.durationMinutes} min
                    </p>

                    <p>
                      <strong>Demo congestion:</strong>{' '}
                      {selectedRoute.congestionLabel}
                    </p>

                    <p className="recommendation-reason">
                      <strong>Why this route?</strong>{' '}
                      {selectedRoute.recommendationReason}
                    </p>
                  </div>
                )}

                {recommendedRoute && (
                  <div className="selected-route-summary">
                    <h3>System recommendation</h3>

                    <p>
                      {recommendedRoute.name}
                    </p>

                    <p>
                      The system prioritizes the lowest
                      demo congestion level and then compares
                      estimated travel time.
                    </p>
                  </div>
                )}
              </div>
            )}

            <div className="traffic-legend">
              <h3>Traffic conditions (demo)</h3>

              <p>
                <span className="legend-dot green" />
                Low congestion
              </p>

              <p>
                <span className="legend-dot yellow" />
                Moderate congestion
              </p>

              <p>
                <span className="legend-dot red" />
                High congestion
              </p>

              <p className="legend-note">
                Illustrative congestion levels only.
                They are not based on live traffic measurements.
              </p>
            </div>
          </div>

          <div className="map-placeholder" id="traffic">
            <TrafficMap
              routes={routes}
              selectedRouteId={selectedRouteId}
              onSelectRoute={setSelectedRouteId}
            />
          </div>
        </section>

        <section className="info-grid" id="overview">
          <article className="info-card">
            <span className="card-icon">⌖</span>
            <p>ROUTE VISIBILITY</p>
            <h3>Map-based routing</h3>
            <span>
              View calculated driving routes on the map.
            </span>
          </article>

          <article className="info-card">
            <span className="card-icon">⇄</span>
            <p>ROUTE OPTIONS</p>
            <h3>Congestion comparison</h3>
            <span>
              Compare illustrative congestion levels
              across available routes.
            </span>
          </article>

          <article className="info-card">
            <span className="card-icon">◷</span>
            <p>TRAVEL PLANNING</p>
            <h3>Estimated travel time</h3>
            <span>
              Compare route distances and estimated
              travel times.
            </span>
          </article>
        </section>

        <footer className="page-footer">
          SmartFlow · Traffic and Smart Parking Management
        </footer>
      </main>
    </div>
  );
}

export default RouteDashboard;

