/* Shared form behavior and charts. Every chart reads server-generated JSON. */
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('form[data-loading]').forEach(form => {
        form.addEventListener('submit', () => {
            if (!form.checkValidity()) return;
            const button = form.querySelector('button[type="submit"]');
            button.disabled = true;
            button.innerHTML = '<span class="spinner-border spinner-border-sm" aria-hidden="true"></span> Processingâ€¦';
        });
    });
    document.querySelectorAll('form[data-confirm]').forEach(form => {
        form.addEventListener('submit', event => {
            if (!window.confirm(form.dataset.confirm)) event.preventDefault();
        });
    });
    const predictionForm = document.getElementById('prediction-form');
    if (predictionForm) {
        const phone = document.getElementById('phone_service');
        const lines = document.getElementById('multiple_lines');
        const internet = document.getElementById('internet_service');
        const addons = ['online_security', 'online_backup', 'device_protection', 'tech_support', 'streaming_tv', 'streaming_movies'];

        function restrict(select, unavailable, noService) {
            [...select.options].forEach(option => {
                option.disabled = unavailable ? option.value !== noService : option.value === noService;
            });
            if (unavailable) select.value = noService;
            else if (select.value === noService) select.value = 'No';
        }
        const syncPhone = () => restrict(lines, phone.value === 'No', 'No phone service');
        const syncInternet = () => addons.forEach(field => restrict(document.getElementById(field), internet.value === 'No', 'No internet service'));
        phone.addEventListener('change', syncPhone);
        internet.addEventListener('change', syncInternet);
        syncPhone();
        syncInternet();
    }
    const element = document.getElementById('chart-data');
    if (!element || !window.Chart) return;
    const charts = JSON.parse(element.textContent);
    const purple = '#8170df',
        teal = '#46bca5',
        muted = '#acb3c2';
    Chart.defaults.font.family = 'Inter, Segoe UI, Arial, sans-serif';
    Chart.defaults.font.size = 10;
    Chart.defaults.color = '#9aa3b7';
    Chart.defaults.plugins.legend.labels.usePointStyle = true;
    Chart.defaults.plugins.legend.labels.boxWidth = 6;
    Chart.defaults.plugins.legend.labels.padding = 18;
    const animation = window.matchMedia('(prefers-reduced-motion: reduce)').matches ? false : {
        duration: 650
    };
    document.querySelectorAll('canvas[data-chart]').forEach(canvas => {
        const name = canvas.dataset.chart,
            data = charts[name];
        if (!data) return;
        let type = 'bar',
            datasets, options = {
                responsive: true,
                maintainAspectRatio: false,
                animation,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        padding: 12,
                        backgroundColor: '#28314b',
                        cornerRadius: 8
                    }
                }
            };
        if (name === 'distribution') {
            type = 'doughnut';
            datasets = [{
                data: data.values,
                backgroundColor: [teal, purple],
                borderWidth: 0,
                hoverOffset: 3,
                spacing: 4,
                borderRadius: 4
            }];
            options.cutout = '77%';
            if (canvas.closest('.admin-content')) options.plugins.legend = {
                display: true,
                position: 'bottom'
            };
        } else if (name === 'timeline') {
            type = 'line';
            const ctx = canvas.getContext('2d');
            const fill = ctx.createLinearGradient(0, 0, 0, 240);
            fill.addColorStop(0, '#8170df27');
            fill.addColorStop(1, '#8170df00');
            datasets = [{
                label: 'Predictions',
                data: data.values,
                borderColor: purple,
                backgroundColor: fill,
                fill: true,
                tension: .35,
                pointRadius: 3,
                pointBackgroundColor: '#fff',
                pointBorderWidth: 2,
                borderWidth: 2
            }];
        } else if (canvas.dataset.kind === 'stacked') {
            datasets = [{
                label: 'Stay',
                data: data.stay,
                backgroundColor: teal,
                borderRadius: 4,
                maxBarThickness: 38
            }, {
                label: 'Churn',
                data: data.churn,
                backgroundColor: purple,
                borderRadius: 4,
                maxBarThickness: 38
            }];
            options.plugins.legend = {
                display: true,
                position: 'bottom'
            };
        } else {
            datasets = [{
                label: name === 'models' ? 'CV F1' : 'Records',
                data: data.values,
                backgroundColor: [purple, '#b4a7ec', teal],
                borderRadius: 5,
                maxBarThickness: 28
            }];
            options.indexAxis = 'y';
        }
        if (type !== 'doughnut') {
            options.scales = {
                x: {
                    grid: {
                        display: type === 'line' ? false : options.indexAxis === 'y',
                        color: '#f1f2f7',
                        drawTicks: false
                    },
                    border: {
                        display: false
                    },
                    ticks: {
                        padding: 9,
                        maxRotation: 0,
                        maxTicksLimit: 7
                    }
                },
                y: {
                    beginAtZero: true,
                    grid: {
                        display: options.indexAxis !== 'y',
                        color: '#f0f2f7',
                        drawTicks: false
                    },
                    border: {
                        display: false
                    },
                    ticks: {
                        padding: 10,
                        precision: 0
                    }
                }
            };
            if (canvas.dataset.kind === 'stacked') {
                options.scales.x.stacked = true;
                options.scales.y.stacked = true;
            }
            if (options.indexAxis === 'y') {
                options.scales.x.beginAtZero = true;
                options.scales.x.ticks.precision = 0;
            }
            if (name === 'models') {
                options.scales.x.max = 1;
                options.scales.x.ticks.callback = value => (value * 100).toFixed(0) + '%';
                options.plugins.tooltip.callbacks = {
                    label: context => ' F1: ' + (context.raw * 100).toFixed(2) + '%'
                };
            }
        }
        new Chart(canvas, {
            type,
            data: {
                labels: data.labels,
                datasets
            },
            options
        });
    });
});
