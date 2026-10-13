import { useState, useEffect, useRef, useCallback } from 'react';
import { MapPin, Check, Loader2 } from 'lucide-react';
import { geocodeAddress } from '../services/api';

/**
 * Autocomplete location input with geocoding via Open-Meteo Geocoding API.
 * Features debounce, keyboard navigation, and clear status indicators.
 */
export default function LocationInput({ label, value, onChange, placeholder, id }) {
  const [query, setQuery] = useState(value?.name || '');
  const [suggestions, setSuggestions] = useState([]);
  const [isOpen, setIsOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);
  const [loading, setLoading] = useState(false);
  const containerRef = useRef(null);
  const debounceRef = useRef(null);

  // Close on outside click
  useEffect(() => {
    function handleClick(e) {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  // Sync external value changes
  useEffect(() => {
    if (value?.name && value.name !== query) {
      setQuery(value.name);
    }
  }, [value?.name]);

  const search = useCallback(async (q) => {
    if (!q || q.trim().length < 3) {
      setSuggestions([]);
      setIsOpen(false);
      return [];
    }

    setLoading(true);
    try {
      const results = await geocodeAddress(q.trim());
      const filtered = results.slice(0, 5);
      setSuggestions(filtered);
      setIsOpen(filtered.length > 0);
      setActiveIndex(-1);
      return filtered;
    } catch (err) {
      console.error('Geocoding error:', err);
      setSuggestions([]);
      return [];
    } finally {
      setLoading(false);
    }
  }, []);

  const handleInputChange = (e) => {
    const val = e.target.value;
    setQuery(val);

    // Clear selection if user modifies text
    if (value?.lat) {
      onChange(null);
    }

    // Debounce geocoding
    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => search(val), 350);
  };

  const handleSelect = (suggestion) => {
    if (!suggestion) return;
    setQuery(suggestion.display_name);
    setIsOpen(false);
    setSuggestions([]);
    onChange({
      lat: parseFloat(suggestion.lat),
      lon: parseFloat(suggestion.lon),
      name: suggestion.display_name,
    });
  };

  const handleKeyDown = async (e) => {
    if (e.key === 'ArrowDown') {
      if (!isOpen) return;
      e.preventDefault();
      setActiveIndex((prev) => Math.min(prev + 1, suggestions.length - 1));
    } else if (e.key === 'ArrowUp') {
      if (!isOpen) return;
      e.preventDefault();
      setActiveIndex((prev) => Math.max(prev - 1, 0));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (isOpen && activeIndex >= 0 && suggestions[activeIndex]) {
        handleSelect(suggestions[activeIndex]);
      } else if (isOpen && suggestions.length > 0) {
        handleSelect(suggestions[0]);
      } else if (query && query.trim().length >= 3) {
        clearTimeout(debounceRef.current);
        const results = await search(query);
        if (results && results.length > 0) {
          handleSelect(results[0]);
        }
      }
    } else if (e.key === 'Escape') {
      setIsOpen(false);
    }
  };

  return (
    <div className="relative" ref={containerRef}>
      <label htmlFor={id} className="block text-xs font-medium mb-1.5" style={{ color: 'var(--color-text-secondary)' }}>
        {label}
      </label>
      <div className="relative">
        <div className="absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none z-10" style={{ color: 'var(--color-text-muted)' }}>
          <MapPin size={15} strokeWidth={2} />
        </div>
        <input
          id={id}
          type="text"
          className="input-field"
          style={{ paddingLeft: '2.4rem', paddingRight: '2.25rem' }}
          placeholder={placeholder}
          value={query}
          onChange={handleInputChange}
          onKeyDown={handleKeyDown}
          onFocus={() => suggestions.length > 0 && setIsOpen(true)}
          autoComplete="off"
        />
        {loading && (
          <div className="absolute right-3 top-1/2 -translate-y-1/2 z-10">
            <Loader2 size={15} className="animate-spin" style={{ color: 'var(--color-accent)' }} />
          </div>
        )}
        {value?.lat && !loading && (
          <div className="absolute right-3 top-1/2 -translate-y-1/2 z-10" style={{ color: 'var(--color-risk-low)' }} title="Coordinates resolved">
            <Check size={16} strokeWidth={2.5} />
          </div>
        )}
      </div>

      {isOpen && suggestions.length > 0 && (
        <div className="autocomplete-dropdown">
          {suggestions.map((s, i) => (
            <div
              key={`${s.lat}-${s.lon}-${i}`}
              className={`autocomplete-item flex items-center gap-2 ${i === activeIndex ? 'autocomplete-item--active' : ''}`}
              onClick={() => handleSelect(s)}
              onMouseEnter={() => setActiveIndex(i)}
            >
              <MapPin size={13} className="shrink-0 opacity-40" />
              <span className="truncate">{s.display_name}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
