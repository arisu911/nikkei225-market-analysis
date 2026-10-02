/**
 * Nikkei 225 Market Behavior Research - Client Application Controller
 * Handles SPA navigation, asynchronous KPI hydration, and reactive Plotly rendering.
 */

// Application State Store
const state = {
  activeModule: 'overview',
  period: '5Y',
  weekday: 'All',
  resolution: '15m',
  instrument: '1321.T',
  isLoading: false,
};

// Module Information Mapping
const MODULE_INFO = {
  overview: {
    title: 'Market Overview',
    description: 'Descriptive statistical summary of the Nikkei 225 index and TSE market behavior. All timestamps displayed in MYT (UTC+8).'
  },
  weekday: {
    title: 'Day-of-Week Behavior Analysis (Monday – Friday)',
    description: 'Descriptive statistical breakdown of Nikkei 225 behavior across individual trading weekdays. All calculations represent historical descriptive statistics across the selected period.'
  },
  intraday: {
    title: 'Intraday Market Behavior & Time-of-Day Profile',
    description: 'Detailed statistical profile of how the Nikkei 225 moves throughout the Tokyo Stock Exchange session. All timestamps displayed in MYT (UTC+8) with the 10:30–11:30 MYT lunch break filtered out.'
  },
  gaps: {
    title: 'Opening Behavior & Gap Analysis (08:00 MYT)',
    description: 'Descriptive statistical examination of the Tokyo Stock Exchange cash equity opening session at 08:00 MYT (09:00 JST). Examines opening gaps, gap-fill tendencies, and 5m, 15m, 30m, and 60m opening range expansions.'
  },
  volatility: {
    title: 'Volatility, Session Comparison & Excursion Path Analysis',
    description: 'Descriptive metrics of Nikkei 225 price dispersion, rolling multi-session volatility regimes, Morning vs Afternoon session dynamics, and Maximum Favorable/Adverse Excursion (MFE/MAE) paths.'
  },
  distributions: {
    title: 'Statistical Distributions & Movement Frequencies',
    description: 'Examines the full probability-style historical empirical distributions for Nikkei 225 returns, ranges, and absolute excursions. All figures reflect historical empirical frequencies, strictly non-predictive.'
  }
};

// Unified Plotly Configuration
const PLOTLY_CONFIG = {
  responsive: true,
  displayModeBar: true,
  displaylogo: false,
  modeBarButtonsToRemove: ['lasso2d', 'select2d', 'toggleSpikelines']
};

/**
 * Enforce Dark Theme layout overrides onto Plotly figures
 */
function applyDarkThemeToLayout(layout) {
  layout = layout || {};
  layout.paper_bgcolor = 'rgba(0,0,0,0)';
  layout.plot_bgcolor = 'rgba(0,0,0,0)';
  layout.autosize = true;
  layout.font = {
    family: 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    color: '#e6edf3',
    size: 11
  };
  if (layout.xaxis) {
    layout.xaxis.gridcolor = '#21262d';
    layout.xaxis.zerolinecolor = '#21262d';
    layout.xaxis.tickfont = { color: '#8b949e', size: 10 };
    layout.xaxis.title = layout.xaxis.title || {};
    layout.xaxis.title.font = { color: '#e6edf3', size: 11 };
  }
  if (layout.yaxis) {
    layout.yaxis.gridcolor = '#21262d';
    layout.yaxis.zerolinecolor = '#21262d';
    layout.yaxis.tickfont = { color: '#8b949e', size: 10 };
    layout.yaxis.title = layout.yaxis.title || {};
    layout.yaxis.title.font = { color: '#e6edf3', size: 11 };
  }
  return layout;
}

/**
 * Render or Reactively Update a Plotly Chart
 */
function renderPlotlyChart(containerId, figureJson) {
  const container = document.getElementById(containerId);
  if (!container) return;

  if (!figureJson || !figureJson.data || figureJson.data.length === 0) {
    container.innerHTML = '<div style="display:flex;align-items:center;justify-content:center;height:100%;color:#8b949e;font-style:italic;">No data available for chart</div>';
    return;
  }

  const data = figureJson.data || [];
  const layout = applyDarkThemeToLayout(figureJson.layout || {});

  Plotly.react(containerId, data, layout, PLOTLY_CONFIG).catch(err => {
    console.error(`Error rendering chart ${containerId}:`, err);
  });
}

/**
 * Construct Query String from Current Application State
 */
function getQueryParams(extraParams = {}) {
  const params = new URLSearchParams({
    period: state.period,
    weekday: state.weekday,
    resolution: state.resolution,
    instrument: state.instrument,
    ...extraParams
  });
  return params.toString();
}

/**
 * Format numbers with signs and decimals
 */
function formatNumber(val, decimals = 2, withSign = false) {
  if (val === null || val === undefined || isNaN(val)) return '--';
  const num = Number(val);
  const formatted = num.toFixed(decimals);
  if (withSign && num > 0) return `+${formatted}`;
  return formatted;
}

function formatPercentage(val, decimals = 2, withSign = false) {
  if (val === null || val === undefined || isNaN(val)) return '--';
  return `${formatNumber(val, decimals, withSign)}%`;
}

/**
 * Fetch and Hydrate Global Metadata and Top 6 KPI Cards
 */
async function fetchMetadataAndKPIs() {
  try {
    const qs = getQueryParams();
    
    // Fetch in parallel
    const [metaRes, kpiRes] = await Promise.all([
      fetch(`/api/metadata?${qs}`),
      fetch(`/api/overview/metrics?${qs}`)
    ]);

    const meta = await metaRes.json();
    const kpis = await kpiRes.json();

    // 1. Update Top Status Badges
    document.getElementById('badge-coverage').textContent = meta.coverage_display || 'N/A';
    document.getElementById('badge-timezone').textContent = meta.active_timezone || 'MYT (UTC+8)';
    document.getElementById('badge-sessions').textContent = meta.total_sessions ? `${meta.total_sessions.toLocaleString()} sessions` : '0';
    document.getElementById('badge-resolution').textContent = meta.resolution || state.resolution;
    document.getElementById('badge-volume').textContent = meta.volume_symbol ? `${meta.volume_symbol} ETF` : 'Index Only';

    // 2. Update KPI Cards
    const elAvgRet = document.getElementById('kpi-avg-return');
    elAvgRet.textContent = kpis.avg_daily_return_str || '--';
    elAvgRet.className = 'kpi-value ' + (kpis.avg_daily_return >= 0 ? 'text-green' : 'text-red');

    const elMedRet = document.getElementById('kpi-median-return');
    elMedRet.textContent = kpis.median_return_str || '--';
    elMedRet.className = 'kpi-value ' + (kpis.median_return >= 0 ? 'text-green' : 'text-red');

    document.getElementById('kpi-volatility').textContent = kpis.daily_volatility_str || '--';
    document.getElementById('kpi-ann-vol').textContent = kpis.annualized_volatility_str || 'Ann: --';
    document.getElementById('kpi-daily-range').textContent = kpis.avg_daily_range_str || '--';

    document.getElementById('kpi-positive-days').textContent = kpis.positive_days_pct_str || '--';
    document.getElementById('kpi-negative-days').textContent = kpis.negative_days_pct_str || 'Neg: --';

    document.getElementById('kpi-total-sessions').textContent = kpis.total_sessions_str || '--';
    document.getElementById('kpi-active-period').textContent = kpis.active_period || `Period: ${state.period}`;

  } catch (err) {
    console.error('Failed to fetch metadata and KPIs:', err);
  }
}

/**
 * Load Active Research Module Data and Render Views
 */
async function loadActiveModule() {
  const module = state.activeModule;
  const qs = getQueryParams();

  try {
    switch (module) {
      case 'overview':
        await loadOverviewModule(qs);
        break;
      case 'weekday':
        await loadWeekdayModule(qs);
        break;
      case 'intraday':
        await loadIntradayModule(qs);
        break;
      case 'gaps':
        await loadGapsModule(qs);
        break;
      case 'volatility':
        await loadVolatilityModule(qs);
        break;
      case 'distributions':
        await loadDistributionsModule(qs);
        break;
      default:
        console.warn(`Unknown module: ${module}`);
    }
  } catch (err) {
    console.error(`Failed to load module ${module}:`, err);
  }
}

/**
 * Module 1: Market Overview
 */
async function loadOverviewModule(qs) {
  const [chartRes, seasonRes] = await Promise.all([
    fetch(`/api/overview/cumulative-chart?${qs}`),
    fetch(`/api/overview/seasonality?${qs}`)
  ]);

  const chartJson = await chartRes.json();
  const seasonData = await seasonRes.json();

  renderPlotlyChart('chart-cumulative', chartJson);

  // Render Yearly Performance Table
  const tbodyYearly = document.querySelector('#table-yearly tbody');
  if (seasonData.yearly && seasonData.yearly.length > 0) {
    tbodyYearly.innerHTML = seasonData.yearly.map(row => {
      const rowLabel = row.label || row['Year'] || row.year || row.index || Object.values(row)[0];
      return `
      <tr>
        <td><strong>${rowLabel}</strong></td>
        <td class="${(row['Annual Return (%)'] || 0) >= 0 ? 'text-green' : 'text-red'}">${formatPercentage(row['Annual Return (%)'], 2, true)}</td>
        <td class="${(row['Avg Daily Return (%)'] || 0) >= 0 ? 'text-green' : 'text-red'}">${formatPercentage(row['Avg Daily Return (%)'], 2, true)}</td>
        <td>${formatPercentage(row['Daily Volatility (%)'], 2)}</td>
        <td>${formatPercentage(row['Annualized Vol (%)'], 1)}</td>
        <td class="text-red">${formatPercentage(row['Max Drawdown (%)'], 2)}</td>
        <td>${row['Sessions (n)'] ? row['Sessions (n)'].toLocaleString() : '--'}</td>
      </tr>
    `;
    }).join('');
  } else {
    tbodyYearly.innerHTML = '<tr><td colspan="7" class="loading-td">No annual data available</td></tr>';
  }

  // Render Monthly Seasonality Table
  const tbodyMonthly = document.querySelector('#table-monthly tbody');
  if (seasonData.monthly && seasonData.monthly.length > 0) {
    tbodyMonthly.innerHTML = seasonData.monthly.map(row => {
      const rowLabel = row.label || row['Month'] || row.month || row.index || Object.values(row)[0];
      return `
      <tr>
        <td><strong>${rowLabel}</strong></td>
        <td class="${(row['Avg Return (%)'] || 0) >= 0 ? 'text-green' : 'text-red'}">${formatPercentage(row['Avg Return (%)'], 2, true)}</td>
        <td class="${(row['Median Return (%)'] || 0) >= 0 ? 'text-green' : 'text-red'}">${formatPercentage(row['Median Return (%)'], 2, true)}</td>
        <td>${formatPercentage(row['Volatility (Std %)'], 2)}</td>
        <td>${formatPercentage(row['Avg Range (%)'], 2)}</td>
        <td class="text-green">${formatPercentage(row['Positive Days (%)'], 1)}</td>
        <td>${row['Sessions (n)'] ? row['Sessions (n)'].toLocaleString() : '--'}</td>
      </tr>
    `;
    }).join('');
  } else {
    tbodyMonthly.innerHTML = '<tr><td colspan="7" class="loading-td">No monthly data available</td></tr>';
  }
}

/**
 * Module 2: Day of Week Analysis
 */
async function loadWeekdayModule(qs) {
  const [analysisRes, tableRes] = await Promise.all([
    fetch(`/api/weekday/analysis?${qs}`),
    fetch(`/api/weekday/table?${qs}`)
  ]);

  const analysis = await analysisRes.json();
  const tableData = await tableRes.json();

  renderPlotlyChart('chart-weekday-comp', analysis.comparisons_chart);
  renderPlotlyChart('chart-weekday-box', analysis.boxplots_chart);
  renderPlotlyChart('chart-weekday-heatmap', analysis.heatmap_chart);

  // Render Weekday Table
  const tbodyWeekday = document.querySelector('#table-weekday tbody');
  if (tableData.data && tableData.data.length > 0) {
    tbodyWeekday.innerHTML = tableData.data.map(row => {
      const rowLabel = row.label || row['Day of Week'] || row.day || row.index || Object.values(row)[0];
      return `
      <tr>
        <td><strong>${rowLabel}</strong></td>
        <td>${row['Sample Size (n)'] ? row['Sample Size (n)'].toLocaleString() : '--'}</td>
        <td class="${(row['Avg Return (%)'] || 0) >= 0 ? 'text-green' : 'text-red'}">${formatPercentage(row['Avg Return (%)'], 2, true)}</td>
        <td class="${(row['Median Return (%)'] || 0) >= 0 ? 'text-green' : 'text-red'}">${formatPercentage(row['Median Return (%)'], 2, true)}</td>
        <td>${formatPercentage(row['Avg Abs Move (%)'], 2)}</td>
        <td>${formatPercentage(row['Avg Range (%)'], 2)}</td>
        <td class="text-green">${formatPercentage(row['Max Return (%)'], 2, true)}</td>
        <td class="text-red">${formatPercentage(row['Min Return (%)'], 2, true)}</td>
        <td class="text-green">${formatPercentage(row['Positive Days (%)'], 1)}</td>
        <td>${formatPercentage(row['Std Dev (%)'], 2)}</td>
        <td>${formatPercentage(row['25th Pct (%)'], 2, true)}</td>
        <td>${formatPercentage(row['75th Pct (%)'], 2, true)}</td>
        <td>${formatPercentage(row['90th Pct (%)'], 2, true)}</td>
      </tr>
    `;
    }).join('');
  } else {
    tbodyWeekday.innerHTML = '<tr><td colspan="13" class="loading-td">No weekday data available</td></tr>';
  }
}

/**
 * Module 3: Intraday & Time Profile
 */
async function loadIntradayModule(qs) {
  const res = await fetch(`/api/intraday/profile?${qs}`);
  const data = await res.json();

  renderPlotlyChart('chart-intraday-profile', data.profile_chart);

  const tbody = document.querySelector('#table-time-windows tbody');
  if (data.time_windows && data.time_windows.length > 0) {
    tbody.innerHTML = data.time_windows.map(row => {
      const rowLabel = row.label || row['Time Window (MYT)'] || row.time_window || row.series || row.metric_label || row.index || Object.values(row)[0];
      return `
      <tr>
        <td><strong>${rowLabel}</strong></td>
        <td>${row['Segment Description']}</td>
        <td>${row['Sample Size (n)'] ? row['Sample Size (n)'].toLocaleString() : '--'}</td>
        <td class="${(row['Avg Return (%)'] || 0) >= 0 ? 'text-green' : 'text-red'}">${formatPercentage(row['Avg Return (%)'], 2, true)}</td>
        <td class="${(row['Median Return (%)'] || 0) >= 0 ? 'text-green' : 'text-red'}">${formatPercentage(row['Median Return (%)'], 2, true)}</td>
        <td>${formatPercentage(row['Avg Abs Move (%)'], 2)}</td>
        <td>${formatPercentage(row['Volatility (Std %)'], 2)}</td>
        <td>${formatPercentage(row['Avg Range (%)'], 2)}</td>
        <td class="text-green">${formatPercentage(row['Positive Sessions (%)'], 1)}</td>
      </tr>
    `;
    }).join('');
  } else {
    tbody.innerHTML = '<tr><td colspan="9" class="loading-td">No time windows data available</td></tr>';
  }
}

/**
 * Module 4: Opening & Gap Analysis
 */
async function loadGapsModule(qs) {
  const res = await fetch(`/api/gaps/analysis?${qs}`);
  const data = await res.json();

  // Metrics
  const m = data.metrics || {};
  document.getElementById('gap-kpi-avg').textContent = m.avg_gap || '--';
  document.getElementById('gap-kpi-med').textContent = m.median_gap || '--';
  document.getElementById('gap-kpi-abs').textContent = m.avg_abs_gap || '--';
  document.getElementById('gap-kpi-up').textContent = m.gap_up_pct || '--';
  document.getElementById('gap-kpi-fill').textContent = m.fill_rate_pct || '--';
  document.getElementById('gap-kpi-total').textContent = m.total_gaps || '--';

  renderPlotlyChart('chart-gap-dist', data.gap_distribution_chart);
  renderPlotlyChart('chart-gap-fill', data.gap_fill_chart);

  const timeToFillCard = document.getElementById('card-time-to-fill');
  if (data.time_to_fill_chart) {
    timeToFillCard.style.display = 'block';
    renderPlotlyChart('chart-time-to-fill', data.time_to_fill_chart);
  } else {
    timeToFillCard.style.display = 'none';
  }

  // Opening Ranges Table
  const tbodyOR = document.querySelector('#table-opening-ranges tbody');
  if (data.opening_ranges_table && data.opening_ranges_table.length > 0) {
    tbodyOR.innerHTML = data.opening_ranges_table.map(row => {
      const rowLabel = row.label || row['Opening Window'] || row.opening_window || row.series || row.metric_label || row.index || Object.values(row)[0];
      return `
      <tr>
        <td><strong>${rowLabel}</strong></td>
        <td>${row['Sample Size (n)'] ? row['Sample Size (n)'].toLocaleString() : '--'}</td>
        <td class="${(row['Avg Return (%)'] || 0) >= 0 ? 'text-green' : 'text-red'}">${formatPercentage(row['Avg Return (%)'], 2, true)}</td>
        <td class="${(row['Median Return (%)'] || 0) >= 0 ? 'text-green' : 'text-red'}">${formatPercentage(row['Median Return (%)'], 2, true)}</td>
        <td>${formatPercentage(row['Volatility (Std %)'], 2)}</td>
        <td>${formatPercentage(row['Avg Range (%)'], 2)}</td>
        <td>${formatPercentage(row['Avg % of Full-Day Range'], 1)}</td>
        <td class="text-green">${formatPercentage(row['Positive Window (%)'], 1)}</td>
      </tr>
    `;
    }).join('');
  } else {
    tbodyOR.innerHTML = '<tr><td colspan="8" class="loading-td">No opening range data available</td></tr>';
  }

  const orRatioCard = document.getElementById('card-opening-range-ratio');
  if (data.opening_range_chart) {
    orRatioCard.style.display = 'block';
    renderPlotlyChart('chart-opening-range-ratio', data.opening_range_chart);
  } else {
    orRatioCard.style.display = 'none';
  }
}

/**
 * Module 5: Volatility & MFE/MAE
 */
async function loadVolatilityModule(qs) {
  const res = await fetch(`/api/volatility/excursions?${qs}`);
  const data = await res.json();

  renderPlotlyChart('chart-rolling-vol', data.rolling_chart);

  // Volatility Quantiles Table
  const tbodyVol = document.querySelector('#table-volatility-quantiles tbody');
  if (data.volatility_quantiles && data.volatility_quantiles.length > 0) {
    tbodyVol.innerHTML = data.volatility_quantiles.map(row => {
      const rowLabel = row.label || row.series || row.metric_label || row['Metric Label'] || row.Metric || row.category || row.index || Object.values(row)[0];
      return `
      <tr>
        <td><strong>${rowLabel}</strong></td>
        <td>${row['Count (n)'] !== undefined && row['Count (n)'] !== null ? row['Count (n)'].toLocaleString() : (row['Count'] ? row['Count'].toLocaleString() : '--')}</td>
        <td>${formatPercentage(row['Mean'], 2, true)}</td>
        <td>${formatPercentage(row['Median'], 2, true)}</td>
        <td>${formatPercentage(row['Std Dev'], 2)}</td>
        <td>${formatPercentage(row['Min'], 2, true)}</td>
        <td>${formatPercentage(row['Max'], 2, true)}</td>
        <td>${formatNumber(row['Skewness'], 2)}</td>
        <td>${formatNumber(row['Kurtosis'], 2)}</td>
        <td>${formatPercentage(row['P10'], 2, true)}</td>
        <td>${formatPercentage(row['P25'], 2, true)}</td>
        <td>${formatPercentage(row['P50'], 2, true)}</td>
        <td>${formatPercentage(row['P75'], 2, true)}</td>
        <td>${formatPercentage(row['P90'], 2, true)}</td>
      </tr>
    `;
    }).join('');
  }

  // Morning vs Afternoon Table & Chart
  const tbodyMA = document.querySelector('#table-morning-afternoon tbody');
  if (data.morning_vs_afternoon_table && data.morning_vs_afternoon_table.length > 0) {
    tbodyMA.innerHTML = data.morning_vs_afternoon_table.map(row => {
      const rowLabel = row.label || row['Session Segment'] || row.series || row.metric_label || row.category || row.index || Object.values(row)[0];
      return `
      <tr>
        <td><strong>${rowLabel}</strong></td>
        <td>${row['Duration'] || '--'}</td>
        <td>${row['Sessions (n)'] ? row['Sessions (n)'].toLocaleString() : '--'}</td>
        <td class="${(row['Avg Return (%)'] || 0) >= 0 ? 'text-green' : 'text-red'}">${formatPercentage(row['Avg Return (%)'], 2, true)}</td>
        <td class="${(row['Median Return (%)'] || 0) >= 0 ? 'text-green' : 'text-red'}">${formatPercentage(row['Median Return (%)'], 2, true)}</td>
        <td>${formatPercentage(row['Volatility (Std %)'], 2)}</td>
        <td>${formatPercentage(row['Avg Range (%)'], 2)}</td>
        <td class="text-green">${formatPercentage(row['Positive Frequency (%)'], 1)}</td>
      </tr>
    `;
    }).join('');
  } else {
    tbodyMA.innerHTML = '<tr><td colspan="8" class="loading-td">Intraday data required for morning vs afternoon</td></tr>';
  }

  if (data.morning_vs_afternoon_chart) {
    renderPlotlyChart('chart-morning-afternoon', data.morning_vs_afternoon_chart);
  }

  // MFE vs MAE Scatter & Histograms
  renderPlotlyChart('chart-mfe-mae', data.mfe_mae_chart);
  if (data.mfe_hist) renderPlotlyChart('chart-mfe-hist', data.mfe_hist);
  if (data.mae_hist) renderPlotlyChart('chart-mae-hist', data.mae_hist);
}

/**
 * Module 6: Statistical Distributions
 */
async function loadDistributionsModule(qs) {
  const res = await fetch(`/api/distributions/quantiles?${qs}`);
  const data = await res.json();

  // Quantiles Table
  const tbodyQuant = document.querySelector('#table-distributions-quantiles tbody');
  if (data.quantiles_table && data.quantiles_table.length > 0) {
    tbodyQuant.innerHTML = data.quantiles_table.map(row => {
      const rowLabel = row.label || row.series || row.metric_label || row['Metric Label'] || row.Metric || row.category || row.index || Object.values(row)[0];
      return `
      <tr>
        <td><strong>${rowLabel}</strong></td>
        <td>${row['Count (n)'] !== undefined && row['Count (n)'] !== null ? row['Count (n)'].toLocaleString() : (row['Count'] ? row['Count'].toLocaleString() : '--')}</td>
        <td>${formatPercentage(row['Mean'], 2, true)}</td>
        <td>${formatPercentage(row['Median'], 2, true)}</td>
        <td>${formatPercentage(row['Std Dev'], 2)}</td>
        <td>${formatPercentage(row['Min'], 2, true)}</td>
        <td>${formatPercentage(row['Max'], 2, true)}</td>
        <td>${formatNumber(row['Skewness'], 2)}</td>
        <td>${formatNumber(row['Kurtosis'], 2)}</td>
        <td>${formatPercentage(row['P10'], 2, true)}</td>
        <td>${formatPercentage(row['P25'], 2, true)}</td>
        <td>${formatPercentage(row['P50'], 2, true)}</td>
        <td>${formatPercentage(row['P75'], 2, true)}</td>
        <td>${formatPercentage(row['P90'], 2, true)}</td>
      </tr>
    `;
    }).join('');
  }

  // Frequency Table
  const tbodyFreq = document.querySelector('#table-movement-frequencies tbody');
  if (data.frequency_table && data.frequency_table.length > 0) {
    tbodyFreq.innerHTML = data.frequency_table.map(row => {
      const rowLabel = row.label || row['Condition / Event'] || row['Move Category'] || row.series || row.metric_label || row.category || row.index || Object.values(row)[0];
      return `
      <tr>
        <td><strong>${rowLabel}</strong></td>
        <td class="text-blue">${formatPercentage(row['Historical Frequency (%)'], 1)}</td>
        <td>${row['Occurrences (Count)'] !== undefined && row['Occurrences (Count)'] !== null ? row['Occurrences (Count)'].toLocaleString() : (row['Occurrences'] ? row['Occurrences'].toLocaleString() : '--')}</td>
        <td>${row['Sample Size (n)'] !== undefined && row['Sample Size (n)'] !== null ? row['Sample Size (n)'].toLocaleString() : (row['Sample Size'] ? row['Sample Size'].toLocaleString() : '--')}</td>
      </tr>
    `;
    }).join('');
  }

  // Histograms
  renderPlotlyChart('chart-return-hist', data.return_histogram);
  renderPlotlyChart('chart-range-hist', data.range_histogram);
}

/**
 * Switch Active Research Module
 */
function switchModule(moduleKey) {
  if (state.activeModule === moduleKey) return;
  state.activeModule = moduleKey;

  // 1. Update Navigation Buttons
  document.querySelectorAll('.nav-item').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.module === moduleKey);
  });

  // 2. Update Header
  const info = MODULE_INFO[moduleKey] || { title: 'Research Dashboard', description: '' };
  document.getElementById('module-title').textContent = info.title;
  document.getElementById('module-description').textContent = info.description;

  // 3. Toggle View Panels
  document.querySelectorAll('.view-panel').forEach(panel => {
    panel.classList.remove('active');
  });
  const targetPanel = document.getElementById(`view-${moduleKey}`);
  if (targetPanel) {
    targetPanel.classList.add('active');
  }

  // 4. Load Data for View
  loadActiveModule();
}

/**
 * Initialize Event Bindings
 */
function initEventBindings() {
  // Navigation Buttons
  document.querySelectorAll('.nav-item').forEach(btn => {
    btn.addEventListener('click', () => {
      const moduleKey = btn.dataset.module;
      if (moduleKey) switchModule(moduleKey);
    });
  });

  // Period Selector
  const filterPeriod = document.getElementById('filter-period');
  if (filterPeriod) {
    filterPeriod.addEventListener('change', (e) => {
      state.period = e.target.value;
      fetchMetadataAndKPIs();
      loadActiveModule();
    });
  }

  // Weekday Selector
  const filterWeekday = document.getElementById('filter-weekday');
  if (filterWeekday) {
    filterWeekday.addEventListener('change', (e) => {
      state.weekday = e.target.value;
      fetchMetadataAndKPIs();
      loadActiveModule();
    });
  }

  // Resolution Selector
  const filterRes = document.getElementById('filter-resolution');
  if (filterRes) {
    filterRes.addEventListener('change', (e) => {
      state.resolution = e.target.value;
      fetchMetadataAndKPIs();
      loadActiveModule();
    });
  }

  // Refresh Button
  const btnRefresh = document.getElementById('btn-refresh');
  if (btnRefresh) {
    btnRefresh.addEventListener('click', async () => {
      const icon = btnRefresh.querySelector('.refresh-icon');
      if (icon) icon.classList.add('spin');
      btnRefresh.disabled = true;

      try {
        await fetch('/api/refresh', { method: 'POST' });
        await fetchMetadataAndKPIs();
        await loadActiveModule();
      } catch (err) {
        console.error('Refresh failed:', err);
      } finally {
        if (icon) icon.classList.remove('spin');
        btnRefresh.disabled = false;
      }
    });
  }

  // Responsive Chart Resizing on Window Resize
  let resizeTimeout;
  window.addEventListener('resize', () => {
    clearTimeout(resizeTimeout);
    resizeTimeout = setTimeout(() => {
      const activePanel = document.querySelector('.view-panel.active');
      if (!activePanel) return;
      activePanel.querySelectorAll('.chart-container, .chart-container-large').forEach(container => {
        if (container.id && container.data) {
          Plotly.Plots.resize(container);
        }
      });
    }, 150);
  });
}

// Initial Boot
document.addEventListener('DOMContentLoaded', () => {
  initEventBindings();
  fetchMetadataAndKPIs();
  loadActiveModule();
});
