(() => {
  'use strict';

  const routes = Object.freeze({
    cities: 'cities',
    series: 'series',
    trends: 'trends',
    forecasts: 'forecasts',
    oppositeTrends: 'opposite-trends',
    clusters: 'clusters'
  });
  const isLiveServer = ['localhost', '127.0.0.1'].includes(window.location.hostname)
    && window.location.port === '5500';
  const apiBase = new URL(
    window.EARTH_TREND_API_BASE
      || (isLiveServer ? 'http://127.0.0.1:8000/api/' : '/api/'),
    window.location.href
  );
  const dataBase = new URL(
    withTrailingSlash(window.EARTH_TREND_DATA_ROOT || '../data/'),
    window.location.href
  );
  const outputBase = new URL(
    withTrailingSlash(window.EARTH_TREND_OUTPUT_ROOT || '../outputs/'),
    window.location.href
  );
  const sourceByResource = {};
  const failures = [];
  let dashboardPromise;

  function withTrailingSlash(path) {
    return path.endsWith('/') ? path : `${path}/`;
  }

  apiBase.pathname = withTrailingSlash(apiBase.pathname);

  const fragileTrends = new Set([
    'Islamabad:precipitation',
    'Islamabad:soil_moisture',
    'Delhi:soil_moisture',
    'Beijing:precipitation',
    'Beijing:soil_moisture',
    'Bangkok:precipitation',
    'Bangkok:soil_moisture',
    'Jakarta:precipitation',
    'Lagos:precipitation',
    'Cape_Town:precipitation',
    'Cape_Town:soil_moisture',
    'Accra:precipitation',
    'New_York:soil_moisture',
    'Buenos_Aires:precipitation',
    'Buenos_Aires:soil_moisture',
    'Santiago:soil_moisture'
  ]);

  function cityKey(value) {
    return String(value || '').replace(/[ _-]/g, '').toLowerCase();
  }

  function numeric(value) {
    if (value === undefined || value === null || value === '') return null;
    const result = Number(value);
    return Number.isFinite(result) ? result : null;
  }

  function variableKey(value) {
    const normalized = String(value || '').toLowerCase();
    if (normalized === 'p' || normalized.includes('precip')) return 'p';
    if (normalized === 's' || normalized.includes('soil') || normalized === 'gwetroot') return 's';
    return null;
  }

  function csvRows(text) {
    const records = [];
    let record = [];
    let field = '';
    let quoted = false;

    for (let index = 0; index < text.length; index += 1) {
      const character = text[index];
      if (quoted) {
        if (character === '"' && text[index + 1] === '"') {
          field += '"';
          index += 1;
        } else if (character === '"') {
          quoted = false;
        } else {
          field += character;
        }
      } else if (character === '"' && field.length === 0) {
        quoted = true;
      } else if (character === ',') {
        record.push(field);
        field = '';
      } else if (character === '\n' || character === '\r') {
        if (character === '\r' && text[index + 1] === '\n') index += 1;
        record.push(field);
        if (record.some((value) => value !== '')) records.push(record);
        record = [];
        field = '';
      } else {
        field += character;
      }
    }

    if (field !== '' || record.length) {
      record.push(field);
      if (record.some((value) => value !== '')) records.push(record);
    }

    if (records.length < 2) throw new Error('CSV file has no data rows.');
    const headers = records.shift().map((header) => header.replace(/^\uFEFF/, '').trim());
    return records.map((values) => Object.fromEntries(
      headers.map((header, index) => [header, values[index] === undefined ? '' : values[index]])
    ));
  }

  async function fetchRows(url, label) {
    const response = await fetch(url);
    if (!response.ok) throw new Error(`${label} request failed (${response.status}).`);
    return csvRows(await response.text());
  }

  async function fetchJson(resource) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 3500);
    try {
      const response = await fetch(new URL(routes[resource], apiBase), {
        headers: { Accept: 'application/json' },
        signal: controller.signal
      });
      if (!response.ok) throw new Error(`${resource} endpoint returned ${response.status}.`);
      return await response.json();
    } finally {
      clearTimeout(timeout);
    }
  }

  function responseRows(payload, resource) {
    if (Array.isArray(payload)) return payload;
    if (payload && Array.isArray(payload.data)) return payload.data;
    if (payload && Array.isArray(payload.results)) return payload.results;
    if (payload && Array.isArray(payload[resource])) return payload[resource];
    throw new TypeError(`${resource} endpoint must return an array of records.`);
  }

  async function resourceRows(resource, fallback, validate = () => {}) {
    try {
      const rows = responseRows(await fetchJson(resource), resource);
      validate(rows);
      sourceByResource[resource] = 'live';
      return rows;
    } catch (error) {
      sourceByResource[resource] = 'demo';
      failures.push({ resource, message: error.message });
      const rows = await fallback();
      validate(rows);
      return rows;
    }
  }

  function normalizeCities(payload, fallbackCities) {
    const rows = responseRows(payload, 'cities');
    if (!rows.length) throw new Error('Cities endpoint returned no records.');
    const fallbackByKey = new Map(fallbackCities.map((city) => [cityKey(city.n), city]));
    const liveByKey = new Map();

    rows.forEach((row) => {
      const name = row.n || row.city || row.name;
      const fallback = fallbackByKey.get(cityKey(name));
      if (!fallback) return;
      liveByKey.set(cityKey(name), {
        ...fallback,
        c: row.c || row.continent || fallback.c,
        lat: numeric(row.lat ?? row.latitude) ?? fallback.lat,
        lon: numeric(row.lon ?? row.longitude) ?? fallback.lon,
        k: row.k || row.country || fallback.k,
        w: row.w || row.wettest_month || row.wettestMonth || fallback.w
      });
    });

    const result = fallbackCities.map((city) => liveByKey.get(cityKey(city.n)) || city);
    if (!result.length) throw new Error('No supported cities were returned.');
    return result;
  }

  function validateCities(rows, cities) {
    const supported = new Set(rows.map((row) => cityKey(row.n || row.city || row.name)));
    if (cities.some((city) => !supported.has(cityKey(city.n)))) {
      throw new Error('Cities endpoint must include all supported cities.');
    }
    normalizeCities(rows, cities);
  }

  function cityLookup(cities) {
    return new Map(cities.map((city) => [cityKey(city.n), city.n]));
  }

  function validateSeriesRows(rows, cities) {
    const lookup = cityLookup(cities);
    const available = new Map(cities.map((city) => [city.n, new Set()]));
    rows.forEach((row) => {
      const city = lookup.get(cityKey(row.city || row.n || row.name));
      if (!city) return;
      if (['precipitation', 'p', 'PRECTOTCORR']
        .some((key) => numeric(row[key]) !== null)) available.get(city).add('p');
      if (['soil_moisture', 's', 'GWETROOT']
        .some((key) => numeric(row[key]) !== null)) available.get(city).add('s');
    });
    if (Array.from(available.values()).some((metrics) => metrics.size !== 2)) {
      throw new Error('Series endpoint is missing city precipitation or soil-moisture data.');
    }
  }

  function buildSeries(rows, cities) {
    const lookup = cityLookup(cities);
    const totals = new Map();

    rows.forEach((row) => {
      const city = lookup.get(cityKey(row.city || row.n || row.name));
      const date = String(row.date || '');
      const year = numeric(row.year || date.slice(0, 4));
      if (!city || year === null || year < 1981 || year > 2025) return;
      const cityTotals = totals.get(city) || new Map();
      const yearTotals = cityTotals.get(year) || {
        p: { sum: 0, count: 0 },
        s: { sum: 0, count: 0 }
      };

      for (const [key, names] of [
        ['p', ['precipitation', 'p', 'PRECTOTCORR']],
        ['s', ['soil_moisture', 's', 'GWETROOT']]
      ]) {
        const value = numeric(names.map((name) => row[name]).find((item) => item !== undefined));
        if (value !== null) {
          yearTotals[key].sum += value;
          yearTotals[key].count += 1;
        }
      }

      cityTotals.set(year, yearTotals);
      totals.set(city, cityTotals);
    });

    return Object.fromEntries(cities.map((city) => {
      const cityTotals = totals.get(city.n) || new Map();
      const values = (key) => Array.from({ length: 45 }, (_, index) => {
        const total = cityTotals.get(1981 + index)?.[key];
        return total && total.count ? total.sum / total.count : null;
      });
      return [city.n, { p: values('p'), s: values('s') }];
    }));
  }

  function buildTrends(rows, cities) {
    const lookup = cityLookup(cities);
    const parsed = rows.map((row) => ({
      city: lookup.get(cityKey(row.city || row.name)),
      variable: variableKey(row.variable),
      row,
      p: numeric(row.mk_p_value ?? row.p_value)
    })).filter((item) => item.city && item.variable);
    const ordered = parsed.filter((item) => item.p !== null).sort((a, b) => a.p - b.p);
    const qValues = new Map();
    let adjusted = 1;
    for (let index = ordered.length - 1; index >= 0; index -= 1) {
      adjusted = Math.min(adjusted, ordered[index].p * ordered.length / (index + 1));
      qValues.set(
        `${ordered[index].city}:${ordered[index].variable}`,
        Math.min(1, adjusted)
      );
    }

    const result = Object.fromEntries(cities.map((city) => [city.n, {}]));
    parsed.forEach(({ city, variable, row, p }) => {
      const existingQ = numeric(row.q_value ?? row.fdr_q_value);
      result[city][variable] = {
        pct: numeric(row.pct_per_decade) ?? 0,
        lo: numeric(row.pct_per_decade_lower_95 ?? row.lower_95) ?? 0,
        hi: numeric(row.pct_per_decade_upper_95 ?? row.upper_95) ?? 0,
        p: p ?? 1,
        q: existingQ ?? qValues.get(`${city}:${variable}`) ?? 1,
        n: numeric(row.valid_years) ?? 0,
        sl: numeric(row.sen_slope) ?? 0,
        ic: numeric(row.sen_intercept) ?? 0,
        sig: String(row.significant).toLowerCase() === 'true',
        rob: row.robust === undefined
          ? !fragileTrends.has(`${city}:${variable === 'p' ? 'precipitation' : 'soil_moisture'}`)
          : String(row.robust).toLowerCase() === 'true'
      };
    });
    return result;
  }

  function validateTrendRows(rows, cities) {
    const found = new Set();
    const lookup = cityLookup(cities);
    rows.forEach((row) => {
      const city = lookup.get(cityKey(row.city || row.name));
      const variable = variableKey(row.variable);
      const required = [
        row.valid_years,
        row.pct_per_decade,
        row.pct_per_decade_lower_95,
        row.pct_per_decade_upper_95,
        row.mk_p_value,
        row.sen_slope,
        row.sen_intercept
      ];
      if (city && variable && required.every((value) => numeric(value) !== null)) {
        found.add(`${city}:${variable}`);
      }
    });
    if (found.size !== cities.length * 2) {
      throw new Error('Trends endpoint must include both variables for every supported city.');
    }
  }

  function forecastRowsToBuckets(rows, cities) {
    const lookup = cityLookup(cities);
    const buckets = new Map();
    const add = (city, variable, year, value, lower, upper) => {
      if (!city || !variable || year < 2026 || year > 2035 || value === null) return;
      const key = `${city}:${variable}:${year}`;
      const bucket = buckets.get(key) || { values: [], lower: [], upper: [] };
      bucket.values.push(value);
      if (lower !== null) bucket.lower.push(lower);
      if (upper !== null) bucket.upper.push(upper);
      buckets.set(key, bucket);
    };

    rows.forEach((row) => {
      const city = lookup.get(cityKey(row.city || row.name));
      const year = numeric(row.year || String(row.date || '').slice(0, 4));
      const variable = variableKey(row.variable);
      const lower = numeric(row.lower_bound ?? row.lower);
      const upper = numeric(row.upper_bound ?? row.upper);
      if (variable) {
        add(city, variable, year, numeric(row.predicted ?? row.value), lower, upper);
        return;
      }
      add(city, 'p', year, numeric(row.precipitation), lower, upper);
      add(city, 's', year, numeric(row.soil_moisture), lower, upper);
    });
    return buckets;
  }

  function validateForecastRows(rows, cities) {
    const buckets = forecastRowsToBuckets(rows, cities);
    const missing = cities.some((city) => ['p', 's'].some((variable) => (
      Array.from({ length: 10 }, (_, index) => 2026 + index).some((year) => {
        const bucket = buckets.get(`${city.n}:${variable}:${year}`);
        return !bucket || !bucket.values.length;
      })
    )));
    if (missing) throw new Error('Forecast endpoint must include 2026–2035 for every city and variable.');
  }

  function residualWidth(series, trend, variable) {
    const observed = series[variable]
      .map((value, index) => ({ value, year: 1981 + index }))
      .filter(({ value }) => value !== null);
    if (observed.length < 2) return 0;
    const trendLine = trend[variable];
    const residuals = observed.map(({ value, year }) => (
      value - (trendLine.ic + trendLine.sl * year)
    ));
    const mean = residuals.reduce((sum, value) => sum + value, 0) / residuals.length;
    const variance = residuals.reduce((sum, value) => sum + (value - mean) ** 2, 0)
      / (residuals.length - 1);
    return 1.28 * Math.sqrt(variance);
  }

  function buildForecasts(rows, cities, series, trends) {
    const buckets = forecastRowsToBuckets(rows, cities);
    return Object.fromEntries(cities.map((city) => {
      const forecast = {};
      for (const variable of ['p', 's']) {
        const width = residualWidth(series[city.n], trends[city.n], variable);
        const means = [];
        const band = [];
        for (let year = 2026; year <= 2035; year += 1) {
          const bucket = buckets.get(`${city.n}:${variable}:${year}`);
          const mean = bucket && bucket.values.length
            ? bucket.values.reduce((sum, value) => sum + value, 0) / bucket.values.length
            : null;
          means.push(mean);
          if (bucket && bucket.lower.length && bucket.upper.length) {
            band.push(
              bucket.lower.reduce((sum, value) => sum + value, 0) / bucket.lower.length,
              bucket.upper.reduce((sum, value) => sum + value, 0) / bucket.upper.length
            );
          } else if (mean !== null) {
            band.push(Math.max(0, mean - width), Math.min(variable === 's' ? 1 : Infinity, mean + width));
          } else {
            band.push(null, null);
          }
        }
        forecast[variable] = { m: means, b: band };
      }
      return [city.n, forecast];
    }));
  }

  function buildOppositeTrends(rows) {
    const result = { p: [], s: [] };
    rows.forEach((row) => {
      const variable = variableKey(row.variable);
      if (!variable) return;
      result[variable].push([
        row.city_increasing,
        row.city_decreasing,
        numeric(row.increasing_pct_per_decade) ?? 0,
        numeric(row.decreasing_pct_per_decade) ?? 0,
        numeric(row.trend_gap_pct_points) ?? 0
      ]);
    });
    return result;
  }

  function buildClusters(rows, cities) {
    const lookup = cityLookup(cities);
    const grouped = new Map();
    rows.forEach((row) => {
      const city = lookup.get(cityKey(row.city || row.name));
      if (!city) return;
      const cluster = String(row.cluster ?? row.cluster_id ?? '');
      const members = grouped.get(cluster) || [];
      members.push({
        city,
        direction: (numeric(row.precipitation_pct_per_decade) ?? 0)
          + (numeric(row.soil_moisture_pct_per_decade) ?? 0)
      });
      grouped.set(cluster, members);
    });

    const result = {};
    grouped.forEach((members) => {
      const average = members.reduce((sum, member) => sum + member.direction, 0) / members.length;
      const label = average >= 0 ? 'Wetting trends' : 'Drying or flat trends';
      members.forEach((member) => {
        result[member.city] = label;
      });
    });
    return result;
  }

  function validateClusterRows(rows, cities) {
    const lookup = cityLookup(cities);
    const found = new Set(rows
      .filter((row) => row.cluster !== undefined || row.cluster_id !== undefined)
      .map((row) => lookup.get(cityKey(row.city || row.name)))
      .filter(Boolean));
    if (found.size !== cities.length) {
      throw new Error('Clusters endpoint must include every supported city.');
    }
  }

  async function cachedSeries(cities) {
    let next = 0;
    const results = new Array(cities.length);
    const workers = Array.from({ length: Math.min(6, cities.length) }, async () => {
      while (next < cities.length) {
        const index = next;
        next += 1;
        const city = cities[index];
        const file = `${city.n.toLowerCase()}_monthly.csv`;
        results[index] = await fetchRows(new URL(`cache/${file}`, dataBase), file);
      }
    });
    await Promise.all(workers);
    return results.flat();
  }

  async function initialize(fallbackCities) {
    if (!Array.isArray(fallbackCities) || !fallbackCities.length) {
      throw new TypeError('City metadata is required to initialize the demo cache.');
    }

    const demoCities = fallbackCities;
    const cityPayload = await resourceRows(
      'cities',
      () => demoCities,
      (rows) => validateCities(rows, demoCities)
    );
    const cities = normalizeCities(cityPayload, demoCities);

    const [seriesRows, trendRows, forecastRows, oppositeRows, clusterRows] = await Promise.all([
      resourceRows('series', () => cachedSeries(cities), (rows) => validateSeriesRows(rows, cities)),
      resourceRows(
        'trends',
        () => fetchRows(new URL('all_cities_trend_results.csv', outputBase), 'trends'),
        (rows) => validateTrendRows(rows, cities)
      ),
      resourceRows(
        'forecasts',
        () => fetchRows(new URL('monthly_10_year_forecasts.csv', outputBase), 'forecasts'),
        (rows) => validateForecastRows(rows, cities)
      ),
      resourceRows('oppositeTrends', () => fetchRows(new URL('opposite_trends.csv', outputBase), 'opposite trends')),
      resourceRows(
        'clusters',
        () => fetchRows(new URL('city_clusters.csv', outputBase), 'clusters'),
        (rows) => validateClusterRows(rows, cities)
      )
    ]);

    const ser = buildSeries(seriesRows, cities);
    const tr = buildTrends(trendRows, cities);
    return {
      cities,
      ser,
      tr,
      fc: buildForecasts(forecastRows, cities, ser, tr),
      opp: buildOppositeTrends(oppositeRows),
      cl: buildClusters(clusterRows, cities)
    };
  }

  function loadDashboard(cities) {
    if (!dashboardPromise) dashboardPromise = initialize(cities);
    return dashboardPromise;
  }

  function status() {
    const values = Object.values(sourceByResource);
    const liveCount = values.filter((source) => source === 'live').length;
    const mode = liveCount === 0 ? 'demo' : liveCount === values.length ? 'live' : 'mixed';
    return {
      mode,
      label: mode === 'live' ? 'Live backend' : mode === 'mixed' ? 'Mixed live/demo data' : 'Demo CSV cache',
      resources: { ...sourceByResource },
      failures: failures.map((failure) => ({ ...failure }))
    };
  }

  async function getResource(resource, city) {
    const dashboard = await loadDashboard(window.EARTH_TREND_CITY_METADATA);
    if (!city) return dashboard[resource];
    const key = cityLookup(dashboard.cities).get(cityKey(city));
    if (!key || !dashboard[resource] || !dashboard[resource][key]) {
      throw new Error(`No ${resource} data is available for ${city}.`);
    }
    return dashboard[resource][key];
  }

  window.EarthTrendApi = Object.freeze({
    endpoints: Object.freeze(Object.fromEntries(
      Object.entries(routes).map(([name, route]) => [name, new URL(route, apiBase).href])
    )),
    loadDashboard,
    status,
    getCities: () => getResource('cities'),
    getSeries: (city) => getResource('ser', city),
    getTrends: (city) => getResource('tr', city),
    getForecasts: (city) => getResource('fc', city),
    getOppositeTrends: () => getResource('opp'),
    getClusters: () => getResource('cl')
  });
})();