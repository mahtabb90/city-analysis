flowchart LR
    A[Mock Traffic API<br/>city=Stockholm<br/>congestion=0.7<br/>speed=30 km/h<br/>incidents=2]
    B[TrafficClient<br/>GET /traffic?city=Stockholm]
    C[TrafficData Model<br/>city: Stockholm<br/>congestion: 0.7<br/>speed: 30<br/>incidents: 2]
    D[City Vibe Analysis<br/>Traffic level: Stressful]

    A --> B
    B --> C
    C --> D
