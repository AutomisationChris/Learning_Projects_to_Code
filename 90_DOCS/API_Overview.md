# 🌐 API Overview

This document provides an overview of the APIs used in the project, including requirements, documentation links, and integration status.

| API Name | Description | API Key Required? | Documentation | Status |
|----------|-------------|------------------|---------------|---------|
| Open-Meteo | Weather data (current, forecast, historical) | ❌ No | [Open-Meteo Docs](https://open-meteo.com/en/docs) | ✅ Integrated |
| Paris Data API | Open data from Paris (events, transport, etc.) | ❌ No | [Paris Data](https://opendata.paris.fr/) | ✅ Integrated |
| Eventbrite API | Global event discovery and ticketing | ✅ Yes | [Eventbrite Docs](https://www.eventbrite.com/platform/api) | 🟡 In progress |
| Ticketmaster API | Concerts, shows, entertainment data | ✅ Yes | [Ticketmaster Docs](https://developer.ticketmaster.com/) | 🟡 In progress |
| SNCF API | French national railway data | ✅ Yes | [SNCF API](https://www.digital.sncf.com/startup/api) | 🟡 Planned |
| GeoPortail API | French geographic data (IGN) | ✅ Yes | [GeoPortail Docs](https://geoservices.ign.fr/documentation) | 🟡 Planned |
| Overpass API | OpenStreetMap data queries | ❌ No | [Overpass Turbo](https://overpass-turbo.eu/) | ✅ Integrated |
| data.gouv.fr | French government open data | ❌ No | [data.gouv.fr](https://www.data.gouv.fr/en/) | ✅ Integrated |
| FlightRadar / AirDBS | Real-time flight tracking | ✅ Yes | [FlightRadar24](https://www.flightradar24.com/how-it-works) | 🟡 Planned |
| MarineTraffic / AIS | Ship tracking and maritime data | ✅ Yes | [MarineTraffic Docs](https://www.marinetraffic.com/en/ais-api-services) | 🟡 Planned |
| AirParif | Air quality in Paris region | ✅ Yes | [AirParif Docs](https://www.airparif.asso.fr/) | 🟡 Planned |
| Datenadler Brandenburg | Open data from Brandenburg, Germany | ✅ Yes | [Datenadler](https://datenadler.de) | 🟡 Planned |

## Legend
- ✅ Integrated
- 🟡 Planned / In Progress
- ❌ Not yet started
- 🔑 API key required

## Notes
- API keys are not stored in this repository. Use local environment variables or a `.env` file.
- Please refer to each API's official documentation for usage limits and terms of service.

---
