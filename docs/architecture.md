# architecture.md
[Start] --> [FieldSentinel] -- Yield/Pasture Scores --> [PricePredictor]
                                                             |
                                                             v
[WeatherOracle] -- Weather Forecast --> [LogisticsMaster] <-- [ConflictGuard] -- Risk Assessment
       |                                       |
       v                                       |
[FarmerCompanion] <----------------------- [LogisticsMaster] -- Optimized Routes
       ^                                       |
       |                                       v
       +-------------------------------- [TraceabilityAgent] -- QR Codes/Docs
                                               |
                                               v
                                         [CarbonTracker] -- ESG Metrics
