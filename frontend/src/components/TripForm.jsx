import { useState } from 'react';
import { Navigation, Loader2 } from 'lucide-react';
import LocationInput from './LocationInput';
import { getDefaultDepartureTime } from '../utils/helpers';

const SAMPLING_OPTIONS = [
  { value: 10, label: '10 miles', desc: 'High detail' },
  { value: 25, label: '25 miles', desc: 'Balanced' },
  { value: 50, label: '50 miles', desc: 'Quick scan' },
];

const PRESETS = [
  {
    label: 'Chicago → Detroit',
    origin: { lat: 41.8781, lon: -87.6298, name: 'Chicago, IL' },
    destination: { lat: 42.3314, lon: -83.0458, name: 'Detroit, MI' },
  },
  {
    label: 'Denver → Kansas City',
    origin: { lat: 39.7392, lon: -104.9903, name: 'Denver, CO' },
    destination: { lat: 39.0997, lon: -94.5786, name: 'Kansas City, MO' },
  },
  {
    label: 'Dallas → Atlanta',
    origin: { lat: 32.7767, lon: -96.7970, name: 'Dallas, TX' },
    destination: { lat: 33.7490, lon: -84.3880, name: 'Atlanta, GA' },
  },
];

export default function TripForm({ onSubmit, loading }) {
  const [origin, setOrigin] = useState(null);
  const [destination, setDestination] = useState(null);
  const [departureTime, setDepartureTime] = useState(getDefaultDepartureTime());
  const [loadWeight, setLoadWeight] = useState(45000);
  const [samplingInterval, setSamplingInterval] = useState(25);

  const canSubmit = origin?.lat && destination?.lat && departureTime && !loading;

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!canSubmit) return;

    const weightNum = Number(loadWeight);
    const validWeight = isNaN(weightNum) || weightNum <= 0 ? 45000 : Math.min(weightNum, 80000);

    onSubmit({
      origin: { lat: origin.lat, lon: origin.lon, name: origin.name },
      destination: { lat: destination.lat, lon: destination.lon, name: destination.name },
      departure_time: new Date(departureTime).toISOString(),
      load_weight_lb: validWeight,
      sampling_interval_miles: Number(samplingInterval),
    });
  };

  const handleApplyPreset = (preset) => {
    setOrigin(preset.origin);
    setDestination(preset.destination);
  };

  return (
    <form onSubmit={handleSubmit} className="card animate-fade-in" style={{ padding: 18 }}>
      {/* Header */}
      <div style={{
        display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between',
        paddingBottom: 12, borderBottom: '1px solid #E4EAF2', marginBottom: 14,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <div style={{
            width: 32, height: 32, borderRadius: 6, display: 'flex',
            alignItems: 'center', justifyContent: 'center',
            background: '#EAF3FF', color: '#3984E8', flexShrink: 0,
          }}>
            <Navigation size={15} strokeWidth={2.2} />
          </div>
          <div>
            <h2 style={{ fontSize: 15, fontWeight: 600, color: '#202938' }}>Trip Parameters</h2>
            <p style={{ fontSize: 12, color: '#667085', marginTop: 1 }}>
              Corridor, departure time, and vehicle load
            </p>
          </div>
        </div>

        <span style={{
          fontSize: 11, fontWeight: 500, padding: '2px 8px', borderRadius: 4,
          background: '#F4F8FF', color: '#667085', border: '1px solid #E4EAF2',
          flexShrink: 0,
        }}>
          Heavy Truck
        </span>
      </div>

      {/* Quick Route Presets */}
      <div style={{ marginBottom: 14 }}>
        <div style={{ fontSize: 12, fontWeight: 500, color: '#667085', marginBottom: 6 }}>
          Quick Route Presets
        </div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
          {PRESETS.map((p) => (
            <button
              key={p.label}
              type="button"
              onClick={() => handleApplyPreset(p)}
              style={{
                fontSize: 12, padding: '5px 10px', borderRadius: 6,
                background: '#F8FAFD', color: '#202938',
                border: '1px solid #E4EAF2', cursor: 'pointer',
                fontWeight: 500, transition: 'all 0.15s ease',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = '#3984E8';
                e.currentTarget.style.color = '#3984E8';
                e.currentTarget.style.background = '#EAF3FF';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = '#E4EAF2';
                e.currentTarget.style.color = '#202938';
                e.currentTarget.style.background = '#F8FAFD';
              }}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      {/* Origin & Destination */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 12 }}>
        <LocationInput
          id="origin-input"
          label="Origin"
          value={origin}
          onChange={setOrigin}
          placeholder="e.g. Chicago, IL"
        />
        <LocationInput
          id="destination-input"
          label="Destination"
          value={destination}
          onChange={setDestination}
          placeholder="e.g. Detroit, MI"
        />
      </div>

      {/* Departure & Cargo Weight */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 14 }}>
        <div>
          <label htmlFor="departure-time" style={{ display: 'block', fontSize: 12, fontWeight: 500, color: '#202938', marginBottom: 4 }}>
            Departure Date & Time
          </label>
          <input
            id="departure-time"
            type="datetime-local"
            className="input-field"
            value={departureTime}
            onChange={(e) => setDepartureTime(e.target.value)}
          />
        </div>
        <div>
          <label htmlFor="load-weight" style={{ display: 'block', fontSize: 12, fontWeight: 500, color: '#202938', marginBottom: 4 }}>
            Cargo Weight
          </label>
          <div style={{ position: 'relative' }}>
            <input
              id="load-weight"
              type="number"
              className="input-field"
              style={{ paddingRight: 36, fontFamily: 'var(--font-mono)' }}
              value={loadWeight}
              onChange={(e) => setLoadWeight(e.target.value)}
              min="0"
              max="80000"
              step="1000"
              placeholder="45000"
            />
            <div style={{
              position: 'absolute', right: 12, top: '50%', transform: 'translateY(-50%)',
              fontSize: 12, fontWeight: 500, color: '#98A2B3', pointerEvents: 'none',
            }}>
              lb
            </div>
          </div>
          <p style={{ fontSize: 11, color: '#667085', marginTop: 4 }}>
            {loadWeight > 40000
              ? 'Heavy load (>40k lb) — wind limits adjusted'
              : 'Standard load — baseline thresholds'}
          </p>
        </div>
      </div>

      {/* Sampling Interval */}
      <div style={{ marginBottom: 14 }}>
        <label style={{ display: 'block', fontSize: 12, fontWeight: 500, color: '#202938', marginBottom: 6 }}>
          Weather Sampling Interval
        </label>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8 }}>
          {SAMPLING_OPTIONS.map((opt) => {
            const isSelected = samplingInterval === opt.value;
            return (
              <button
                key={opt.value}
                type="button"
                onClick={() => setSamplingInterval(opt.value)}
                style={{
                  padding: '8px 4px', borderRadius: 6, textAlign: 'center',
                  cursor: 'pointer', transition: 'all 0.15s ease',
                  background: isSelected ? '#EAF3FF' : '#F8FAFD',
                  color: isSelected ? '#3984E8' : '#667085',
                  border: isSelected ? '1.5px solid #3984E8' : '1px solid #E4EAF2',
                }}
              >
                <div style={{ fontWeight: 600, fontSize: 13 }}>{opt.label}</div>
                <div style={{ fontSize: 10, opacity: 0.75, marginTop: 2 }}>{opt.desc}</div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Analyze Button */}
      <button
        type="submit"
        disabled={!canSubmit}
        className="btn-primary"
        id="analyze-routes-btn"
        style={{ width: '100%', height: 44 }}
      >
        {loading ? (
          <>
            <Loader2 size={15} className="animate-spin" />
            <span>Analyzing Routes & Weather…</span>
          </>
        ) : (
          <>
            <Navigation size={15} strokeWidth={2} />
            <span>Analyze Routes</span>
          </>
        )}
      </button>
    </form>
  );
}
