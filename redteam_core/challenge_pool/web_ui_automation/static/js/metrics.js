class UIMetricsCollector {
    constructor() {
        this.data = {
            movements: [],
            clicks: [],
            startTime: Date.now()
        };
    }

    track() {
        document.addEventListener('mousemove', (e) => {
            this.data.movements.push({
                x: e.clientX,
                y: e.clientY,
                t: Date.now() - this.data.startTime
            });
        });
        
        document.addEventListener('click', (e) => {
            this.data.clicks.push({
                x: e.clientX,
                y: e.clientY,
                t: Date.now() - this.data.startTime
            });
        });
    }

    save() {
        localStorage.setItem('ui_metrics', JSON.stringify(this.data));
    }
}