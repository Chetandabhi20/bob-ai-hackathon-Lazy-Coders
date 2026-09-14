import { useState, useEffect } from 'react';
import { getCrewPlan } from '../api';

export default function CrewPlan() {
  const [plan, setPlan] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    getCrewPlan()
      .then((data) => {
        setPlan(data);
        setLoading(false);
      })
      .catch((e) => {
        setError(e.message);
        setLoading(false);
      });
  }, []);

  if (loading) return <div className="panel loading">Loading crew plan...</div>;
  if (error) return <div className="panel error">Error: {error}</div>;

  return (
    <div className="panel crew-panel">
      <h2>Crew Deployment Plan</h2>
      <p className="generated-at">Generated: {plan.generated_at}</p>

      <table className="crew-table">
        <thead>
          <tr>
            <th>Crew</th>
            <th>Asset</th>
            <th>Rank</th>
            <th>ETA</th>
            <th>Reason</th>
          </tr>
        </thead>
        <tbody>
          {plan.assignments.map((a) => (
            <tr key={a.crew_id}>
              <td className="crew-id">{a.crew_id}</td>
              <td className="asset-id">{a.assigned_asset_id}</td>
              <td>#{a.priority_rank}</td>
              <td className="eta">{a.eta_minutes} min</td>
              <td className="reason">{a.reason}</td>
            </tr>
          ))}
        </tbody>
      </table>

      {plan.unassigned_high_risk_assets.length > 0 && (
        <div className="unassigned-warning">
          <strong>⚠ Unassigned High-Risk Assets:</strong>{' '}
          {plan.unassigned_high_risk_assets.join(', ')}
          <p>Additional crew resources needed for these assets.</p>
        </div>
      )}
    </div>
  );
}
