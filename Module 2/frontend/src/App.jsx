import React, { useEffect, useMemo, useState } from "react";
import {
  ParkingSquare, Car, Upload, Activity, Camera, ScanLine,
  CheckCircle2, AlertCircle, RefreshCw, Database
} from "lucide-react";

const API = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

export default function App() {
  const [file, setFile] = useState(null);
  const [data, setData] = useState(null);
  const [spaces, setSpaces] = useState([]);
  const [summary, setSummary] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [connected, setConnected] = useState(false);

  async function refreshDashboard() {
    try {
      const [healthResponse, spacesResponse, summaryResponse] = await Promise.all([
        fetch(`${API}/health`),
        fetch(`${API}/api/parking/spaces`),
        fetch(`${API}/api/parking/summary`)
      ]);
      setConnected(healthResponse.ok);
      if (spacesResponse.ok) setSpaces(await spacesResponse.json());
      if (summaryResponse.ok) setSummary(await summaryResponse.json());
    } catch {
      setConnected(false);
    }
  }

  useEffect(() => { refreshDashboard(); }, []);

  const displayedSummary = data?.summary || summary;
  const displayedSpaces = data?.results
    ? data.results.map((item) => ({
        id: item.space_id,
        name: item.name,
        status: item.status
      }))
    : spaces;

  async function runDetection() {
    if (!file) return;
    setBusy(true);
    setError("");
    try {
      const form = new FormData();
      form.append("file", file);
      const isVideo = file.type.startsWith("video/");
      const endpoint = isVideo
        ? `${API}/api/parking/detect/video`
        : `${API}/api/parking/detect/image`;
      const response = await fetch(endpoint, { method: "POST", body: form });
      const result = await response.json();
      if (!response.ok) {
        throw new Error(result.detail || "Detection failed");
      }
      setData(result);
      await refreshDashboard();
    } catch (err) {
      setError(`${err.message}. Check that the backend is running and parking spaces are configured.`);
    } finally {
      setBusy(false);
    }
  }

  const annotatedImage = data?.processed_image_url
    ? `${API}${data.processed_image_url}`
    : null;

  return (
    <div className="layout">
      <aside>
        <div className="logo"><ParkingSquare /><b>ParkVision</b></div>
        <p className="muted">SMART PARKING PLATFORM</p>
        <div className="nav"><Activity /> Parking Detection</div>
        <div className="connection"><i className={connected ? "on" : ""} />
          {connected ? "Backend connected" : "Backend offline"}
        </div>
      </aside>

      <main>
        <header>
          <div>
            <small>BACKEND + AI / COMPUTER VISION</small>
            <h1>Smart Parking Detection</h1>
            <p>Manage parking spaces and detect occupied bays using YOLO AI.</p>
          </div>
          <span className="pill">● YOLO AI</span>
        </header>

        <section className="stats">
          {[
            ["Total spaces", displayedSummary?.total_spaces ?? "—", ParkingSquare],
            ["Occupied", displayedSummary?.occupied_spaces ?? "—", Car],
            ["Available", displayedSummary?.available_spaces ?? "—", CheckCircle2],
            ["Occupancy", displayedSummary ? `${displayedSummary.occupancy_percentage}%` : "—", Activity]
          ].map(([label, value, Icon]) => (
            <article key={label}><Icon /><label>{label}</label><strong>{value}</strong></article>
          ))}
        </section>

        <section className="grid">
          <article className="panel">
            <h2>Analyze parking camera</h2>
            <p className="muted">Upload a parking-lot image or recorded video for AI analysis.</p>
            <label className="drop">
              <input type="file" accept="image/*,video/*"
                onChange={(event) => { setFile(event.target.files?.[0] || null); setData(null); setError(""); }} />
              <Upload size={28} />
              <b>{file ? file.name : "Choose image or video"}</b>
              <small>JPG, PNG, MP4, AVI, MOV, MKV</small>
              <em>Browse files</em>
            </label>
            {file && (
              <div className="preview">
                {file.type.startsWith("image/")
                  ? <img src={URL.createObjectURL(file)} alt="Selected parking lot" />
                  : <video controls src={URL.createObjectURL(file)} />}
              </div>
            )}
            <button disabled={!file || busy || !connected} onClick={runDetection}>
              {busy ? <><RefreshCw className="spin" /> Analyzing...</> : <><ScanLine /> Analyze occupancy</>}
            </button>
            {error && <div className="error"><AlertCircle />{error}</div>}
            <p className="tip"><Database /> Parking-space rectangles are stored in the backend database and configured through the API.</p>
          </article>

          <article className="panel">
            <h2>AI detection result</h2>
            <p className="muted">Annotated image returned by the backend</p>
            {annotatedImage ? (
              <>
                <img className="result" src={annotatedImage} alt="AI annotated parking detection" />
                <p className="resultText"><Car /> {data.spaces_processed} parking spaces analyzed · {data.detector}</p>
                <div className="legend"><span>🟥 Occupied</span><span>🟩 Vacant</span></div>
              </>
            ) : (
              <div className="empty"><Camera /><b>Waiting for camera analysis</b>
                <small>Upload a file and run AI detection to see annotated parking spaces.</small>
              </div>
            )}
          </article>
        </section>

        <article className="panel bays">
          <h2>Parking-space status</h2>
          <p className="muted">Latest status saved in the backend database</p>
          {displayedSpaces.length ? (
            <div className="baygrid">
              {displayedSpaces.map((space) => (
                <div className={`bay ${space.status === "occupied" ? "busy" : "free"}`} key={space.id}>
                  <ParkingSquare /><b>{space.name}</b>
                  <span>{space.status === "occupied" ? "Occupied" : "Vacant"}</span>
                </div>
              ))}
            </div>
          ) : (
            <p className="muted">No parking spaces found. Add spaces using the backend API or run the sample seed script.</p>
          )}
        </article>
        <footer>ParkVision · FastAPI · SQLAlchemy · OpenCV · YOLOv8 · React</footer>
      </main>
    </div>
  );
}
