/**
 * DWOS Admin Panel JavaScript
 * Handles all frontend interactions for the admin dashboard
 */

// Global variables
let refreshInterval;
let adminToken = null;
let charts = {}; // Store chart instances

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeDashboard();
    setupEventListeners();
    
    // Check for admin token in localStorage
    adminToken = localStorage.getItem('dwos_admin_token');
    if (!adminToken) {
        promptForToken();
    } else {
        loadInitialData();
    }
});

/**
 * Initialize dashboard components
 */
function initializeDashboard() {
    // Initialize charts
    initializeCharts();
    
    // Set up auto-refresh (every 30 seconds)
    refreshInterval = setInterval(refreshData, 30000);
    
    console.log('DWOS Admin Dashboard initialized');
}

/**
 * Setup event listeners
 */
function setupEventListeners() {
    // Navigation links
    document.querySelectorAll('[data-section]').forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            showSection(this.dataset.section);
            setActiveNavLink(this);
        });
    });
    
    // Service filters
    document.getElementById('log-service-filter')?.addEventListener('change', refreshLogs);
    document.getElementById('log-level-filter')?.addEventListener('change', refreshLogs);
    
    // Collection selector
    document.getElementById('collection-select')?.addEventListener('change', function() {
        if (this.value) {
            loadCollectionData(this.value);
        }
    });
}

/**
 * Prompt user for admin token
 */
function promptForToken() {
    const token = prompt('Please enter your admin token:');
    if (token) {
        adminToken = token;
        localStorage.setItem('dwos_admin_token', token);
        loadInitialData();
    } else {
        document.body.innerHTML = '<div class="alert alert-danger m-4">Admin token required to access this panel.</div>';
    }
}

/**
 * Load initial data
 */
async function loadInitialData() {
    try {
        await Promise.all([
            loadOverviewData(),
            loadServicesData(),
            loadDatabaseCollections().catch(e => console.warn('Database not available:', e)),
            loadConfiguration().catch(e => console.warn('Configuration not loaded:', e))
        ]);
    } catch (error) {
        console.error('Error loading initial data:', error);
        if (error.message.includes('403')) {
            localStorage.removeItem('dwos_admin_token');
            promptForToken();
        }
    }
}

/**
 * Show specific section and hide others
 */
function showSection(sectionName) {
    // Hide all sections
    document.querySelectorAll('.content-section').forEach(section => {
        section.classList.add('d-none');
    });
    
    // Show selected section
    const targetSection = document.getElementById(`${sectionName}-section`);
    if (targetSection) {
        targetSection.classList.remove('d-none');
        
        // Clean up charts when switching sections (except for dashboard)
        if (sectionName !== 'dashboard') {
            cleanupCharts();
        }
        
        // Load section-specific data
        switch(sectionName) {
            case 'dashboard':
                loadOverviewData();
                break;
            case 'services':
                loadServicesManagement();
                break;
            case 'database':
                loadDatabaseCollections();
                break;
            case 'logs':
                refreshLogs();
                break;
            case 'monitoring':
                loadMonitoringData();
                break;
            case 'configuration':
                loadConfiguration();
                break;
        }
    }
}

/**
 * Clean up all chart instances
 */
function cleanupCharts() {
    Object.keys(charts).forEach(chartKey => {
        if (charts[chartKey]) {
            charts[chartKey].destroy();
            delete charts[chartKey];
        }
    });
}

/**
 * Set active navigation link
 */
function setActiveNavLink(activeLink) {
    document.querySelectorAll('.nav-link').forEach(link => {
        link.classList.remove('active');
    });
    activeLink.classList.add('active');
}

/**
 * Make authenticated API request
 */
async function apiRequest(endpoint, options = {}) {
    const headers = {
        'Authorization': `Bearer ${adminToken}`,
        'Content-Type': 'application/json',
        ...options.headers
    };
    
    const response = await fetch(`/admin/api${endpoint}`, {
        ...options,
        headers
    });
    
    if (!response.ok) {
        if (response.status === 403) {
            throw new Error('403: Invalid admin token');
        }
        throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    return response.json();
}

/**
 * Load overview data
 */
async function loadOverviewData() {
    try {
        const data = await apiRequest('/overview');
        
        // Update metric cards
        document.getElementById('services-count').textContent = data.services || 0;
        document.getElementById('users-count').textContent = data.database_stats?.total_users || 0;
        document.getElementById('alliances-count').textContent = data.database_stats?.total_alliances || 0;
        document.getElementById('events-count').textContent = data.database_stats?.active_events || 0;
        
        // Update services list (the services are directly in the services count)
        // We'll load the detailed service list separately
        loadServicesData();
        
        // Update resources chart
        updateResourcesChart(data.system_metrics);
        
    } catch (error) {
        console.error('Error loading overview:', error);
        showError('Failed to load overview data');
    }
}

/**
 * Load services data
 */
async function loadServicesData() {
    try {
        const data = await apiRequest('/services');
        updateServicesList(data.services || []);
        
        // Also update recent logs
        // loadRecentLogs(); // Removed as logs need to be implemented
    } catch (error) {
        console.error('Error loading services:', error);
        // Show empty state if services not available
        updateServicesList([]);
    }
}

/**
 * Update services list with horizontal layout
 */
function updateServicesList(services) {
    const container = document.getElementById('services-list');
    
    // Remove loading class
    container.classList.remove('loading');
    
    if (services.length === 0) {
        container.innerHTML = '<p class="text-muted text-center py-4">No services found</p>';
        return;
    }
    
    container.innerHTML = `
        <div class="services-horizontal">
            ${services.map(service => `
                <div class="service-card">
                    <div class="service-card-header">
                        <div>
                            <h6 class="service-card-name">${service.name}</h6>
                            <div class="service-card-info mt-1">
                                <i class="fas fa-network-wired"></i>
                                <span>${service.address}:${service.port}</span>
                            </div>
                        </div>
                        <span class="service-card-status status-${service.status}">
                            <i class="fas fa-circle" style="font-size: 0.5rem;"></i>
                            ${service.status}
                        </span>
                    </div>
                    <div class="service-card-health">
                        <span class="status-indicator status-${service.health === 'healthy' ? 'healthy' : service.health === 'warning' ? 'warning' : 'error'}"></span>
                        <span class="text-${service.health === 'healthy' ? 'success' : service.health === 'warning' ? 'warning' : 'danger'}" style="font-size: 0.9rem; font-weight: 500;">
                            ${service.health === 'healthy' ? 'Healthy' : service.health === 'warning' ? 'Warning' : 'Unhealthy'}
                        </span>
                    </div>
                </div>
            `).join('')}
        </div>
    `;
}

/**
 * Load services management
 */
async function loadServicesManagement() {
    try {
        const data = await apiRequest('/services');
        const container = document.getElementById('services-management');
        
        if (data.services.length === 0) {
            container.innerHTML = '<p class="text-muted">No services found</p>';
            return;
        }
        
        container.innerHTML = `
            <div class="table-responsive">
                <table class="table table-hover align-middle">
                    <thead>
                        <tr>
                            <th>Service</th>
                            <th>Status</th>
                            <th>Health</th>
                            <th>Address</th>
                            <th class="text-center">Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${data.services.map(service => `
                            <tr>
                                <td>
                                    <div class="d-flex flex-column">
                                        <strong class="mb-1">${service.name}</strong>
                                        <small class="text-muted">${service.service_id || 'N/A'}</small>
                                    </div>
                                </td>
                                <td>
                                    <span class="badge rounded-pill bg-${service.status === 'running' ? 'success' : 'danger'} px-3 py-2">
                                        <i class="fas fa-circle me-1" style="font-size: 0.6rem;"></i>
                                        ${service.status}
                                    </span>
                                </td>
                                <td>
                                    <div class="d-flex align-items-center">
                                        <span class="status-indicator status-${service.health === 'healthy' ? 'healthy' : service.health === 'warning' ? 'warning' : 'error'} me-2"></span>
                                        <span class="text-${service.health === 'healthy' ? 'success' : service.health === 'warning' ? 'warning' : 'danger'}">
                                            ${service.health}
                                        </span>
                                    </div>
                                </td>
                                <td>
                                    <code class="text-muted">${service.address}:${service.port}</code>
                                </td>
                                <td class="text-center">
                                    <div class="btn-group" role="group">
                                        <button class="btn btn-sm btn-outline-success" onclick="serviceAction('${service.name}', 'restart')" title="Restart">
                                            <i class="fas fa-redo"></i>
                                        </button>
                                        <button class="btn btn-sm btn-outline-warning" onclick="serviceAction('${service.name}', 'reload')" title="Reload">
                                            <i class="fas fa-sync"></i>
                                        </button>
                                        <button class="btn btn-sm btn-outline-danger" onclick="serviceAction('${service.name}', 'stop')" title="Stop">
                                            <i class="fas fa-stop"></i>
                                        </button>
                                    </div>
                                </td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        `;
        
    } catch (error) {
        console.error('Error loading services management:', error);
        showError('Failed to load services management');
    }
}

/**
 * Perform service action
 */
async function serviceAction(serviceName, action) {
    if (!confirm(`Are you sure you want to ${action} the ${serviceName} service?`)) {
        return;
    }
    
    try {
        const result = await apiRequest('/services/action', {
            method: 'POST',
            body: JSON.stringify({
                service_name: serviceName,
                action: action
            })
        });
        
        showSuccess(`${action} action sent to ${serviceName}`);
        
        // Refresh services data after action
        setTimeout(() => {
            loadServicesManagement();
        }, 2000);
        
    } catch (error) {
        console.error('Error performing service action:', error);
        showError(`Failed to ${action} ${serviceName}`);
    }
}

/**
 * Load database collections
 */
async function loadDatabaseCollections() {
    try {
        const data = await apiRequest('/database/collections');
        const select = document.getElementById('collection-select');
        
        select.innerHTML = '<option value="">Select Collection...</option>' +
            data.collections.map(collection => 
                `<option value="${collection.name}">${collection.name} (${collection.count})</option>`
            ).join('');
            
    } catch (error) {
        console.error('Error loading collections:', error);
    }
}

/**
 * Load collection data
 */
function loadCollectionData(collectionName) {
    queryDatabase(collectionName, {});
}

/**
 * Query database
 */
async function queryDatabase(collection = null, query = null) {
    const collectionName = collection || document.getElementById('collection-select').value;
    const queryInput = document.getElementById('query-input').value;
    
    if (!collectionName) {
        showError('Please select a collection');
        return;
    }
    
    let queryObj = query;
    if (query === null) {
        try {
            queryObj = queryInput ? JSON.parse(queryInput) : {};
        } catch (error) {
            showError('Invalid JSON query format');
            return;
        }
    }
    
    try {
        const data = await apiRequest('/database/query', {
            method: 'POST',
            body: JSON.stringify({
                collection: collectionName,
                query: queryObj,
                limit: 50,
                skip: 0
            })
        });
        
        displayDatabaseResults(data);
        
    } catch (error) {
        console.error('Error querying database:', error);
        showError('Failed to query database');
    }
}

/**
 * Display database results
 */
function displayDatabaseResults(data) {
    const container = document.getElementById('database-results');
    
    // Remove any loading state
    container.classList.remove('loading');
    
    if (data.documents.length === 0) {
        container.innerHTML = '<p class="text-muted">No documents found</p>';
        return;
    }
    
    container.innerHTML = `
        <div class="mb-3">
            <small class="text-muted">
                Showing ${data.documents.length} of ${data.total_count} documents
                (Page ${data.current_page} of ${data.total_pages})
            </small>
        </div>
        <div class="table-responsive">
            <table class="table table-sm table-striped">
                <thead>
                    <tr>
                        ${Object.keys(data.documents[0]).map(key => `<th>${key}</th>`).join('')}
                    </tr>
                </thead>
                <tbody>
                    ${data.documents.map(doc => `
                        <tr>
                            ${Object.values(doc).map(value => 
                                `<td>${typeof value === 'object' ? JSON.stringify(value) : value}</td>`
                            ).join('')}
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        </div>
    `;
}

/**
 * Refresh logs
 */
async function refreshLogs() {
    try {
        const serviceFilter = document.getElementById('log-service-filter')?.value || '';
        const levelFilter = document.getElementById('log-level-filter')?.value || '';
        
        const params = new URLSearchParams();
        if (serviceFilter) params.append('service', serviceFilter);
        if (levelFilter) params.append('level', levelFilter);
        params.append('limit', '100');
        
        const data = await apiRequest(`/logs?${params.toString()}`);
        
        const container = document.getElementById('logs-container');
        
        // Remove loading state
        container.classList.remove('loading');
        
        if (data.logs.length === 0) {
            container.innerHTML = '<p class="text-muted">No logs found</p>';
            return;
        }
        
        container.innerHTML = data.logs.map(log => {
            const timestamp = new Date(log.timestamp);
            const timeAgo = getTimeAgo(timestamp);
            
            return `
                <div class="log-entry level-${log.level.toLowerCase()}">
                    <div class="d-flex justify-content-between align-items-start">
                        <div class="flex-grow-1">
                            <div class="d-flex align-items-center gap-2 mb-1">
                                <strong class="log-level">[${log.level}]</strong> 
                                <span class="badge bg-secondary">${log.service}</span>
                                <small class="text-muted">${timeAgo}</small>
                            </div>
                            <div class="log-message">${escapeHtml(log.message)}</div>
                            ${log.metadata && Object.keys(log.metadata).length > 0 ? `
                                <div class="log-metadata mt-1">
                                    <small class="text-muted">
                                        ${Object.entries(log.metadata).map(([key, value]) => 
                                            `<span class="me-2">${key}: ${escapeHtml(value)}</span>`
                                        ).join('')}
                                    </small>
                                </div>
                            ` : ''}
                        </div>
                        <small class="text-muted text-nowrap">${timestamp.toLocaleTimeString()}</small>
                    </div>
                </div>
            `;
        }).join('');
        
        // Update service filter with available services
        if (data.available_services && data.available_services.length > 0) {
            const serviceSelect = document.getElementById('log-service-filter');
            const currentValue = serviceSelect.value;
            serviceSelect.innerHTML = '<option value="">All Services</option>' +
                data.available_services.map(service => 
                    `<option value="${service}" ${service === currentValue ? 'selected' : ''}>${service}</option>`
                ).join('');
        }
        
        // Update level filter with available levels
        if (data.available_levels && data.available_levels.length > 0) {
            const levelSelect = document.getElementById('log-level-filter');
            const currentValue = levelSelect.value;
            levelSelect.innerHTML = '<option value="">All Levels</option>' +
                data.available_levels.map(level => 
                    `<option value="${level}" ${level === currentValue ? 'selected' : ''} 
                     class="text-${level === 'ERROR' ? 'danger' : level === 'WARNING' ? 'warning' : 'secondary'}">
                        ${level}
                    </option>`
                ).join('');
        }
        
    } catch (error) {
        console.error('Error loading logs:', error);
        showError('Failed to load logs');
    }
}

/**
 * Load monitoring data
 */
async function loadMonitoringData() {
    try {
        const data = await apiRequest('/metrics');
        
        // Update metric cards with real-time data
        updateMonitoringMetrics(data);
        
        // Update CPU chart
        updateCPUChart(data.cpu);
        
        // Update memory chart
        updateMemoryChart(data.memory);
        
        // Update additional charts
        updateNetworkChart(data.network);
        updateDiskChart(data.disk);
        
    } catch (error) {
        console.error('Error loading monitoring data:', error);
        showError('Failed to load monitoring data');
    }
}

/**
 * Update monitoring metrics cards
 */
function updateMonitoringMetrics(data) {
    // Update CPU metric cards
    const cpuPercent = data.cpu?.usage_percent || 0;
    const cpuUsageCard = document.getElementById('cpu-usage');
    if (cpuUsageCard) {
        cpuUsageCard.textContent = `${cpuPercent.toFixed(1)}%`;
        // Update color based on usage
        const cpuMetric = cpuUsageCard.closest('.metric-card');
        if (cpuMetric) {
            cpuMetric.classList.remove('metric-warning', 'metric-danger');
            if (cpuPercent > 80) cpuMetric.classList.add('metric-danger');
            else if (cpuPercent > 60) cpuMetric.classList.add('metric-warning');
        }
    }
    // Update CPU cores
    const cpuCores = document.getElementById('cpu-cores');
    if (cpuCores && data.cpu?.cores) {
        cpuCores.textContent = `${data.cpu.cores} Cores`;
    }
    // Update CPU load average
    const cpuLoadAvg = document.getElementById('cpu-load-avg');
    if (cpuLoadAvg && data.cpu?.load_average) {
        cpuLoadAvg.textContent = `Load: ${data.cpu.load_average.map(l => l.toFixed(2)).join(', ')}`;
    }
    
    // Update Memory metric cards
    const memoryPercent = data.memory?.usage_percent || 0;
    const memoryUsageCard = document.getElementById('memory-usage');
    if (memoryUsageCard) {
        memoryUsageCard.textContent = `${memoryPercent.toFixed(1)}%`;
        // Update color based on usage
        const memoryMetric = memoryUsageCard.closest('.metric-card');
        if (memoryMetric) {
            memoryMetric.classList.remove('metric-warning', 'metric-danger');
            if (memoryPercent > 80) memoryMetric.classList.add('metric-danger');
            else if (memoryPercent > 60) memoryMetric.classList.add('metric-warning');
        }
    }
    // Update Memory total
    const memoryTotal = document.getElementById('memory-total');
    if (memoryTotal && data.memory?.total_gb) {
        memoryTotal.textContent = `${data.memory.total_gb.toFixed(1)} GB Total`;
    }
    
    // Update Disk metric cards
    const diskPercent = data.disk?.usage_percent || 0;
    const diskUsageCard = document.getElementById('disk-usage');
    if (diskUsageCard) {
        diskUsageCard.textContent = `${diskPercent.toFixed(1)}%`;
        // Update color based on usage
        const diskMetric = diskUsageCard.closest('.metric-card');
        if (diskMetric) {
            diskMetric.classList.remove('metric-warning', 'metric-danger');
            if (diskPercent > 90) diskMetric.classList.add('metric-danger');
            else if (diskPercent > 75) diskMetric.classList.add('metric-warning');
        }
    }
    // Update Disk total
    const diskTotal = document.getElementById('disk-total');
    if (diskTotal && data.disk?.total_gb) {
        diskTotal.textContent = `${data.disk.total_gb.toFixed(1)} GB Total`;
    }
    
    // Update Network metric cards
    const networkMB = ((data.network?.bytes_sent || 0) + (data.network?.bytes_received || 0)) / 1024 / 1024;
    const networkIO = document.getElementById('network-io');
    if (networkIO) {
        networkIO.textContent = `${networkMB.toFixed(1)} MB`;
    }
    // Update Network packets
    const networkPackets = document.getElementById('network-packets');
    if (networkPackets && data.network) {
        const totalPackets = (data.network.packets_sent || 0) + (data.network.packets_received || 0);
        networkPackets.textContent = `${totalPackets.toLocaleString()} Packets`;
    }
    
    // Update Network Activity details
    if (data.network) {
        const networkSent = document.getElementById('network-sent');
        if (networkSent) {
            networkSent.textContent = formatBytes(data.network.bytes_sent || 0);
        }
        
        const networkReceived = document.getElementById('network-received');
        if (networkReceived) {
            networkReceived.textContent = formatBytes(data.network.bytes_received || 0);
        }
        
        const packetsSent = document.getElementById('packets-sent');
        if (packetsSent) {
            packetsSent.textContent = (data.network.packets_sent || 0).toLocaleString();
        }
        
        const packetsReceived = document.getElementById('packets-received');
        if (packetsReceived) {
            packetsReceived.textContent = (data.network.packets_received || 0).toLocaleString();
        }
    }
    
    // Update Service Health
    if (data.services) {
        const servicesTotal = document.getElementById('services-total');
        if (servicesTotal) {
            servicesTotal.textContent = data.services.total || 0;
        }
        
        const servicesHealthy = document.getElementById('services-healthy');
        if (servicesHealthy) {
            servicesHealthy.textContent = data.services.healthy || 0;
        }
        
        const servicesUnhealthy = document.getElementById('services-unhealthy');
        if (servicesUnhealthy) {
            servicesUnhealthy.textContent = data.services.unhealthy || 0;
        }
        
        // Update health progress bar
        const healthBar = document.getElementById('services-health-bar');
        if (healthBar && data.services.total > 0) {
            const healthPercent = (data.services.healthy / data.services.total) * 100;
            healthBar.style.width = `${healthPercent}%`;
        }
    }
}

/**
 * Format bytes to human readable format
 */
function formatBytes(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

/**
 * Load configuration
 */
async function loadConfiguration() {
    try {
        const data = await apiRequest('/config');
        
        const container = document.getElementById('config-container');
        
        // Remove loading state
        container.classList.remove('loading');
        
        container.innerHTML = `
            <div class="table-responsive">
                <table class="table">
                    <thead>
                        <tr>
                            <th>Setting</th>
                            <th>Value</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${Object.entries(data.configuration).map(([key, value]) => `
                            <tr>
                                <td><strong>${key}</strong></td>
                                <td>${Array.isArray(value) ? value.join(', ') : value}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        `;
        
    } catch (error) {
        console.error('Error loading configuration:', error);
        showError('Failed to load configuration');
    }
}

/**
 * Initialize charts
 */
function initializeCharts() {
    // Resources chart will be initialized when data is loaded
}

/**
 * Update resources chart
 */
function updateResourcesChart(metrics) {
    if (!metrics) return;
    
    const ctx = document.getElementById('resourcesChart');
    if (!ctx) return;
    
    // Destroy existing chart if it exists
    if (charts.resourcesChart) {
        charts.resourcesChart.destroy();
    }
    
    // Update resource metric cards
    const cpuValue = document.getElementById('resource-cpu');
    if (cpuValue) cpuValue.textContent = `${(metrics.cpu_usage || 0).toFixed(1)}%`;
    
    const memoryValue = document.getElementById('resource-memory');
    if (memoryValue) memoryValue.textContent = `${(metrics.memory_usage || 0).toFixed(1)}%`;
    
    const diskValue = document.getElementById('resource-disk');
    if (diskValue) diskValue.textContent = `${(metrics.disk_usage || 0).toFixed(1)}%`;
    
    const networkValue = document.getElementById('resource-network');
    if (networkValue && metrics.network_throughput !== undefined) {
        networkValue.textContent = `${(metrics.network_throughput || 0).toFixed(1)} MB/s`;
    }
    
    charts.resourcesChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['CPU', 'Memory', 'Disk'],
            datasets: [{
                data: [
                    metrics.cpu_usage || 0,
                    metrics.memory_usage || 0,
                    metrics.disk_usage || 0
                ],
                backgroundColor: [
                    'rgba(102, 126, 234, 0.8)',
                    'rgba(78, 205, 196, 0.8)',
                    'rgba(255, 230, 109, 0.8)'
                ],
                borderColor: [
                    'rgba(102, 126, 234, 1)',
                    'rgba(78, 205, 196, 1)',
                    'rgba(255, 230, 109, 1)'
                ],
                borderWidth: 3,
                hoverBorderWidth: 5,
                hoverBackgroundColor: [
                    'rgba(102, 126, 234, 0.9)',
                    'rgba(78, 205, 196, 0.9)',
                    'rgba(255, 230, 109, 0.9)'
                ]
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            cutout: '70%',
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    titleColor: 'white',
                    bodyColor: 'white',
                    borderColor: 'rgba(255, 255, 255, 0.1)',
                    borderWidth: 1,
                    cornerRadius: 8,
                    callbacks: {
                        label: function(context) {
                            return context.label + ': ' + context.parsed + '%';
                        }
                    }
                }
            },
            animation: {
                animateRotate: true,
                animateScale: true,
                duration: 2000,
                easing: 'easeOutCubic'
            }
        }
    });
}

/**
 * Update CPU chart
 */
function updateCPUChart(cpuData) {
    const ctx = document.getElementById('cpuChart');
    if (!ctx) return;
    
    // Destroy existing chart if it exists
    if (charts.cpuChart) {
        charts.cpuChart.destroy();
    }
    
    charts.cpuChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: ['1m', '5m', '15m'],
            datasets: [{
                label: 'CPU Usage %',
                data: [cpuData.usage_percent, cpuData.usage_percent * 0.9, cpuData.usage_percent * 0.8],
                borderColor: 'rgba(102, 126, 234, 1)',
                backgroundColor: 'rgba(102, 126, 234, 0.1)',
                borderWidth: 3,
                pointBackgroundColor: 'rgba(102, 126, 234, 1)',
                pointBorderColor: '#fff',
                pointBorderWidth: 2,
                pointRadius: 6,
                pointHoverRadius: 8,
                tension: 0.4,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    titleColor: 'white',
                    bodyColor: 'white',
                    borderColor: 'rgba(255, 255, 255, 0.1)',
                    borderWidth: 1,
                    cornerRadius: 8
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100,
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)'
                    },
                    ticks: {
                        font: {
                            family: 'Inter'
                        }
                    }
                },
                x: {
                    grid: {
                        display: false
                    },
                    ticks: {
                        font: {
                            family: 'Inter'
                        }
                    }
                }
            },
            animation: {
                duration: 2000,
                easing: 'easeOutCubic'
            }
        }
    });
}

/**
 * Update memory chart
 */
function updateMemoryChart(memoryData) {
    const ctx = document.getElementById('memoryChart');
    if (!ctx) return;
    
    // Destroy existing chart if it exists
    if (charts.memoryChart) {
        charts.memoryChart.destroy();
    }
    
    charts.memoryChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ['Used', 'Available'],
            datasets: [{
                label: 'Memory (GB)',
                data: [memoryData.used_gb, memoryData.available_gb],
                backgroundColor: [
                    'rgba(255, 107, 107, 0.8)',
                    'rgba(78, 205, 196, 0.8)'
                ],
                borderColor: [
                    'rgba(255, 107, 107, 1)',
                    'rgba(78, 205, 196, 1)'
                ],
                borderWidth: 2,
                borderRadius: 8,
                borderSkipped: false,
                hoverBackgroundColor: [
                    'rgba(255, 107, 107, 0.9)',
                    'rgba(78, 205, 196, 0.9)'
                ]
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    titleColor: 'white',
                    bodyColor: 'white',
                    borderColor: 'rgba(255, 255, 255, 0.1)',
                    borderWidth: 1,
                    cornerRadius: 8,
                    callbacks: {
                        label: function(context) {
                            return context.dataset.label + ': ' + context.parsed.y.toFixed(1) + ' GB';
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)'
                    },
                    ticks: {
                        font: {
                            family: 'Inter'
                        },
                        callback: function(value) {
                            return value + ' GB';
                        }
                    }
                },
                x: {
                    grid: {
                        display: false
                    },
                    ticks: {
                        font: {
                            family: 'Inter'
                        }
                    }
                }
            },
            animation: {
                duration: 2000,
                easing: 'easeOutCubic'
            }
        }
    });
}

/**
 * Refresh all data
 */
async function refreshData() {
    const currentSection = document.querySelector('.nav-link.active')?.dataset.section || 'dashboard';
    
    switch(currentSection) {
        case 'dashboard':
            await loadOverviewData();
            break;
        case 'services':
            await loadServicesManagement();
            break;
        case 'database':
            await loadDatabaseCollections();
            break;
        case 'logs':
            await refreshLogs();
            break;
        case 'monitoring':
            await loadMonitoringData();
            break;
        case 'configuration':
            await loadConfiguration();
            break;
    }
}

/**
 * Show success message
 */
function showSuccess(message) {
    showAlert(message, 'success');
}

/**
 * Show error message
 */
function showError(message) {
    showAlert(message, 'danger');
}

/**
 * Show alert message with enhanced styling
 */
function showAlert(message, type) {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    alertDiv.style.cssText = `
        top: 20px; 
        right: 20px; 
        z-index: 9999; 
        max-width: 400px;
        border-radius: 1rem;
        box-shadow: 0 8px 30px rgba(0,0,0,0.15);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.2);
        font-family: 'Inter', sans-serif;
        font-weight: 500;
    `;
    alertDiv.innerHTML = `
        <div class="d-flex align-items-center">
            <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'danger' ? 'exclamation-triangle' : 'info-circle'} me-2"></i>
            <div>${message}</div>
        </div>
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(alertDiv);
    
    // Add entrance animation
    setTimeout(() => {
        alertDiv.style.transform = 'translateX(0)';
        alertDiv.style.opacity = '1';
    }, 100);
    
    // Auto remove after 5 seconds with exit animation
    setTimeout(() => {
        if (alertDiv.parentNode) {
            alertDiv.style.transform = 'translateX(100%)';
            alertDiv.style.opacity = '0';
            setTimeout(() => {
                if (alertDiv.parentNode) {
                    alertDiv.remove();
                }
            }, 300);
        }
    }, 5000);
}

/**
 * Refresh services
 */
function refreshServices() {
    loadServicesManagement();
}

/**
 * Get time ago string
 */
function getTimeAgo(date) {
    const seconds = Math.floor((new Date() - date) / 1000);
    
    if (seconds < 60) return `${seconds}s ago`;
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `${minutes}m ago`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours}h ago`;
    const days = Math.floor(hours / 24);
    return `${days}d ago`;
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.replace(/[&<>"']/g, m => map[m]);
}

/**
 * Update network chart
 */
function updateNetworkChart(networkData) {
    const ctx = document.getElementById('networkChart');
    if (!ctx || !networkData) return;
    
    // Destroy existing chart if it exists
    if (charts.networkChart) {
        charts.networkChart.destroy();
    }
    
    // Convert bytes to MB
    const sentMB = (networkData.bytes_sent || 0) / 1024 / 1024;
    const recvMB = (networkData.bytes_received || 0) / 1024 / 1024;
    
    charts.networkChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: ['5s', '10s', '15s', '20s', '25s', '30s'],
            datasets: [{
                label: 'Sent (MB/s)',
                data: [sentMB * 0.7, sentMB * 0.8, sentMB * 0.9, sentMB * 0.95, sentMB * 0.98, sentMB],
                borderColor: 'rgba(102, 126, 234, 1)',
                backgroundColor: 'rgba(102, 126, 234, 0.1)',
                borderWidth: 3,
                pointRadius: 4,
                tension: 0.4,
                fill: true
            }, {
                label: 'Received (MB/s)',
                data: [recvMB * 0.7, recvMB * 0.8, recvMB * 0.9, recvMB * 0.95, recvMB * 0.98, recvMB],
                borderColor: 'rgba(78, 205, 196, 1)',
                backgroundColor: 'rgba(78, 205, 196, 0.1)',
                borderWidth: 3,
                pointRadius: 4,
                tension: 0.4,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false
            },
            plugins: {
                legend: {
                    position: 'top',
                    labels: {
                        usePointStyle: true,
                        font: {
                            family: 'Inter',
                            size: 12
                        }
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    titleColor: 'white',
                    bodyColor: 'white',
                    borderColor: 'rgba(255, 255, 255, 0.1)',
                    borderWidth: 1,
                    cornerRadius: 8,
                    callbacks: {
                        label: function(context) {
                            return context.dataset.label + ': ' + context.parsed.y.toFixed(2) + ' MB/s';
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)'
                    },
                    ticks: {
                        font: {
                            family: 'Inter'
                        },
                        callback: function(value) {
                            return value + ' MB/s';
                        }
                    }
                },
                x: {
                    grid: {
                        display: false
                    },
                    ticks: {
                        font: {
                            family: 'Inter'
                        }
                    }
                }
            },
            animation: {
                duration: 2000,
                easing: 'easeOutCubic'
            }
        }
    });
}

/**
 * Update disk chart
 */
function updateDiskChart(diskData) {
    const ctx = document.getElementById('diskChart');
    if (!ctx || !diskData) return;
    
    // Destroy existing chart if it exists
    if (charts.diskChart) {
        charts.diskChart.destroy();
    }
    
    const usedGB = diskData.used_gb || 0;
    const freeGB = diskData.available_gb || 0;
    
    charts.diskChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Used', 'Free'],
            datasets: [{
                data: [usedGB, freeGB],
                backgroundColor: [
                    'rgba(255, 107, 107, 0.8)',
                    'rgba(78, 205, 196, 0.8)'
                ],
                borderColor: [
                    'rgba(255, 107, 107, 1)',
                    'rgba(78, 205, 196, 1)'
                ],
                borderWidth: 3,
                hoverBorderWidth: 5,
                hoverBackgroundColor: [
                    'rgba(255, 107, 107, 0.9)',
                    'rgba(78, 205, 196, 0.9)'
                ]
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '70%',
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        usePointStyle: true,
                        padding: 20,
                        font: {
                            size: 12,
                            family: 'Inter'
                        }
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    titleColor: 'white',
                    bodyColor: 'white',
                    borderColor: 'rgba(255, 255, 255, 0.1)',
                    borderWidth: 1,
                    cornerRadius: 8,
                    callbacks: {
                        label: function(context) {
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = ((context.parsed / total) * 100).toFixed(1);
                            return context.label + ': ' + context.parsed.toFixed(1) + ' GB (' + percentage + '%)';
                        }
                    }
                }
            },
            animation: {
                animateRotate: true,
                animateScale: true,
                duration: 2000,
                easing: 'easeOutCubic'
            }
        }
    });
}