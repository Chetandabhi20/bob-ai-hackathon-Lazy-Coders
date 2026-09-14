import { useState, useEffect } from 'react';
import { getRankedAssets, getAssetHealth } from '../api';

export default function AssetList({ selectedAssetId, onSelectAsset }) {
  const [assets, setAssets] = useState([]);
  const [detail, setDetail] = useState(null);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    getRankedAssets(25)
      .then((data) => {
        setAssets(data.ranked_assets || []);
        setLoading(false);
      })
      .catch((e) => {
        setError(e.message);
        setLoading(false);
      });
  }, []);

  useEffect(() => {
    if (!selectedAssetId) {
      setDetail(null);
      return;
    }
    setDetailLoading(true);
    getAssetHealth(selectedAssetId)
      .then((d) => {
        setDetail(d);
        setDetailLoading(false);
      })
      .catch((e) => {
        setDetail(null);
        setDetailLoading(false);
        setError(e.message);
      });
  }, [selectedAssetId]);

  if (loading) return <div className="panel loading">Loading assets...</div>;
  if (error) return <div className="panel error">Error: {error}</div>;

  return (
    <div className="panel asset-panel">
      <h2>At-Risk Assets</h2>
      <div className="asset-table-wrap">
        <table className="asset-table">
          <thead>
            <tr>
              <th>Asset</th>
              <th>Type</th>
              <th>Score</th>
              <th>Prob</th>
              <th>Blast</th>
              <th>Customers</th>
            </tr>
          </thead>
          <tbody>
            {assets.map((a) => (
              <tr
                key={a.asset_id}
                className={a.asset_id === selectedAssetId ? 'selected' : ''}
                onClick={() => onSelectAsset?.(a.asset_id)}
              >
                <td className="asset-id">{a.asset_id}</td>
                <td>{a.asset_id.split('-')[0]}</td>
                <td className="score">{a.combined_priority_score.toFixed(1)}</td>
                <td>{(a.failure_probability_14d * 100).toFixed(0)}%</td>
                <td>{a.blast_radius_score.toFixed(1)}</td>
                <td>{a.customers_at_risk.toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Detail panel */}
      {selectedAssetId && (
        <div className="asset-detail">
          {detailLoading ? (
            <p>Loading details...</p>
          ) : detail ? (
            <>
              <h3>
                {detail.asset_name} ({detail.asset_id})
              </h3>
              <div className="detail-grid">
                <div className="detail-card">
                  <span className="label">Failure Prob (14d)</span>
                  <span className="value danger">
                    {(detail.failure_probability_14d * 100).toFixed(1)}%
                  </span>
                </div>
                <div className="detail-card">
                  <span className="label">Blast Radius</span>
                  <span className="value">{detail.blast_radius_score.toFixed(1)}</span>
                </div>
                <div className="detail-card">
                  <span className="label">Customers at Risk</span>
                  <span className="value">
                    {detail.customers_at_risk.toLocaleString()}
                  </span>
                </div>
                <div className="detail-card">
                  <span className="label">Backup Path</span>
                  <span className={`value ${detail.has_backup_path ? 'ok' : 'danger'}`}>
                    {detail.has_backup_path ? 'Yes' : 'No'}
                  </span>
                </div>
              </div>

              {/* Latest sensor readings */}
              {detail.latest_readings && (
                <div className="sensor-readings">
                  <h4>Latest Sensor Readings</h4>
                  <div className="sensor-bars">
                    {[
                      { key: 'temperature_c', label: 'Temp (°C)', max: 120, warn: 75 },
                      { key: 'vibration_mm_s', label: 'Vibration', max: 10, warn: 5 },
                      { key: 'partial_discharge_pc', label: 'Discharge', max: 80, warn: 40 },
                      { key: 'oil_quality_index', label: 'Oil Quality', max: 100, warn: 60, invert: true },
                    ].map(({ key, label, max, warn, invert }) => {
                      const val = detail.latest_readings[key];
                      const pct = Math.min((val / max) * 100, 100);
                      const bad = invert ? val < warn : val > warn;
                      return (
                        <div className="sensor-bar-row" key={key}>
                          <span className="sensor-label">{label}</span>
                          <div className="sensor-bar-bg">
                            <div
                              className={`sensor-bar-fill ${bad ? 'warn' : 'ok'}`}
                              style={{ width: `${pct}%` }}
                            />
                          </div>
                          <span className="sensor-val">{val}</span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Top signals */}
              <div className="signals">
                <h4>Risk Signals</h4>
                <div className="signal-tags">
                  {detail.top_contributing_signals.map((s) => (
                    <span className="signal-tag" key={s}>
                      {s.replace(/_/g, ' ')}
                    </span>
                  ))}
                </div>
              </div>
            </>
          ) : (
            <p>Select an asset to view details</p>
          )}
        </div>
      )}
    </div>
  );
}
