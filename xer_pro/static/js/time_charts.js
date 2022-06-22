function timeChart(element, datasets) {
    return new Chart(element, {
        type: 'bar',
        data: { datasets: datasets },
        options: {
            responsive: true,
            interaction: {
                mode: 'nearest',
                axis: 'x',
                intersect: false
            },
            scales: {
                x: {
                    type: 'time',
                    time: {
                        unit: 'month',
                        displayFormats: {
                            month: 'MMM-yyyy'
                        }
                    },
                },
            },
            maintainAspectRatio: false
        }
    })
}

function horizontalStackedChart(element, data) {
    return new Chart(element, {
        type: 'bar',
        data: data,
        options: {
            indexAxis: 'y',
            scales: {
                x: {
                    stacked: true,
                    ticks: {
                        callback: function(value, index, ticks) {
                            return value + '%';
                        }
                    }
                },
                y: {stacked: true,},
            },
            maintainAspectRatio: false
        }
    });
}
