
import { useEffect, useMemo } from 'react';
import {
  MapContainer,
  TileLayer,
  Marker,
  Popup,
  Polyline,
  useMap,
} from 'react-leaflet';
import 'leaflet/dist/leaflet.css';

// ==========================================
// MAP CONFIGURATION
// ==========================================

const DEFAULT_POSITION = [12.9716, 77.5946];

const TRAFFIC_STYLES = {
  low: {
    color: '#16a34a',
    label: 'Low congestion (demo)',
  },
  moderate: {
    color: '#eab308',
    label: 'Moderate congestion (demo)',
  },
  high: {
    color: '#dc2626',
    label: 'High congestion (demo)',
  },
};

// ==========================================
// ROUTE DISPLAY AND MAP BOUNDS
// ==========================================

function RouteDisplay({
  routes,
  selectedRouteId,
  onSelectRoute,
}) {
  const map = useMap();

  useEffect(() => {
    const selectedRoute = routes.find(
      (route) => route.id === selectedRouteId
    );

    const coordinates =
      selectedRoute?.coordinates ??
      routes[0]?.coordinates;

    if (coordinates?.length > 1) {
      map.fitBounds(coordinates, {
        padding: [35, 35],
        maxZoom: 14,
      });
    }
  }, [routes, selectedRouteId, map]);

  return (
    <>
      {routes.map((route, index) => {
        if (
          !Array.isArray(route.coordinates) ||
          route.coordinates.length < 2
        ) {
          return null;
        }

        const isSelected =
          route.id === selectedRouteId;

        return (
          <Polyline
            key={route.id}
            positions={route.coordinates}
            pathOptions={{
              color: isSelected
                ? '#2563eb'
                : '#64748b',
              weight: isSelected ? 7 : 4,
              opacity: isSelected ? 1 : 0.65,
              lineCap: 'round',
              lineJoin: 'round',
            }}
            eventHandlers={{
              click: () =>
                onSelectRoute?.(route.id),
            }}
          >
            <Popup>
              <strong>
                {isSelected
                  ? 'Selected route'
                  : route.isRecommended
                    ? 'Fastest estimated route'
                    : `Alternative route ${index + 1}`}
              </strong>

              <br />

              Distance: {route.distanceKm} km

              <br />

              Estimated time: {route.durationMinutes} minutes

              <br />

              <small>
                Time is estimated by the routing service;
                live traffic is not included.
              </small>

              <br />

              Click the route line to select it.
            </Popup>
          </Polyline>
        );
      })}
    </>
  );
}

// ==========================================
// SIMULATED TRAFFIC VISUALIZATION
// ==========================================

// DEMO ONLY:
// These traffic levels are illustrative.
// They do not represent actual road congestion.

function SimulatedTrafficLayer({ routes }) {
  const trafficSegments = useMemo(() => {
    return routes.flatMap((route) => {
      const coordinates = route.coordinates;

      if (
        !Array.isArray(coordinates) ||
        coordinates.length < 3
      ) {
        return [];
      }

      const middle = Math.floor(
        coordinates.length / 2
      );

      const start = Math.max(0, middle - 2);

      const end = Math.min(
        coordinates.length - 1,
        middle + 2
      );

      const segmentCoordinates =
        coordinates.slice(start, end + 1);

      if (segmentCoordinates.length < 2) {
        return [];
      }

      // Deterministic illustrative demo levels.
      const level =
        route.id % 3 === 0
          ? 'low'
          : route.id % 2 === 0
            ? 'high'
            : 'moderate';

      return [
        {
          id: `demo-traffic-${route.id}`,
          coordinates: segmentCoordinates,
          level,
        },
      ];
    });
  }, [routes]);

  return (
    <>
      {trafficSegments.map((segment) => {
        const style =
          TRAFFIC_STYLES[segment.level];

        return (
          <Polyline
            key={segment.id}
            positions={segment.coordinates}
            pathOptions={{
              color: style.color,
              weight: 10,
              opacity: 0.95,
              lineCap: 'round',
              lineJoin: 'round',
            }}
            interactive={false}
          />
        );
      })}
    </>
  );
}

// ==========================================
// TRAFFIC DEMO LEGEND
// ==========================================

function TrafficLegend() {
  return (
    <div
      className="traffic-demo-legend"
      style={{
        position: 'absolute',
        bottom: 18,
        left: 12,
        zIndex: 1000,
        background: '#ffffff',
        color: '#111827',
        padding: '12px 14px',
        borderRadius: 8,
        boxShadow: '0 2px 10px rgba(0,0,0,0.18)',
        fontSize: 12,
        lineHeight: 1.8,
      }}
    >
      <strong>Traffic visualization (demo)</strong>

      {Object.entries(TRAFFIC_STYLES).map(
        ([level, style]) => (
          <div
            key={level}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 8,
            }}
          >
            <span
              aria-hidden="true"
              style={{
                display: 'inline-block',
                width: 22,
                height: 5,
                borderRadius: 4,
                background: style.color,
              }}
            />

            <span>{style.label}</span>
          </div>
        )
      )}

      <div
        style={{
          marginTop: 5,
          color: '#b91c1c',
          maxWidth: 220,
          lineHeight: 1.4,
        }}
      >
        Illustrative colors only. Not live traffic data.
      </div>
    </div>
  );
}

// ==========================================
// MAIN TRAFFIC MAP
// ==========================================

function TrafficMap({
  routes = [],
  selectedRouteId,
  onSelectRoute,
}) {
  const firstRoute = routes.find(
    (route) =>
      Array.isArray(route.coordinates) &&
      route.coordinates.length > 1
  );

  const startPosition =
    firstRoute?.coordinates?.[0] ??
    DEFAULT_POSITION;

  const endPosition =
    firstRoute?.coordinates?.[
      firstRoute.coordinates.length - 1
    ] ?? DEFAULT_POSITION;

  return (
    <div
      className="traffic-map"
      style={{
        position: 'relative',
        width: '100%',
        height: '100%',
        minHeight: 400,
      }}
    >
      <MapContainer
        center={startPosition}
        zoom={13}
        scrollWheelZoom={true}
        style={{
          height: '100%',
          width: '100%',
          minHeight: 400,
        }}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {firstRoute && (
          <>
            <Marker position={startPosition}>
              <Popup>
                <strong>Starting point</strong>
                <br />
                Journey begins here.
              </Popup>
            </Marker>

            <Marker position={endPosition}>
              <Popup>
                <strong>Destination</strong>
                <br />
                Journey ends here.
              </Popup>
            </Marker>
          </>
        )}

        <RouteDisplay
          routes={routes}
          selectedRouteId={selectedRouteId}
          onSelectRoute={onSelectRoute}
        />

        {/* Traffic layer renders above route lines */}
        {firstRoute && (
          <SimulatedTrafficLayer routes={routes} />
        )}
      </MapContainer>

      {routes.length > 0 && <TrafficLegend />}
    </div>
  );
}

export default TrafficMap;
