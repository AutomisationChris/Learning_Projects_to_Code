import csv

U_ROUTE_IDS = {
    "17512_400","17514_400","17515_400","17516_400","17518_400",
    "17521_400","17523_400","17525_400","17526_400"
}

def filter_trips(trips_in="trips.txt", trips_out="trips_ubahn.txt"):
    trip_ids, shape_ids, service_ids = set(), set(), set()
    with open(trips_in, newline="", encoding="utf-8") as f_in, open(trips_out, "w", newline="", encoding="utf-8") as f_out:
        r = csv.DictReader(f_in)
        w = csv.DictWriter(f_out, fieldnames=r.fieldnames)
        w.writeheader()
        for row in r:
            if row.get("route_id") in U_ROUTE_IDS:
                w.writerow(row)
                trip_ids.add(row["trip_id"])
                if "shape_id" in row and row["shape_id"]:
                    shape_ids.add(row["shape_id"])
                if "service_id" in row and row["service_id"]:
                    service_ids.add(row["service_id"])
    return trip_ids, shape_ids, service_ids

def filter_by_ids(infile, outfile, id_field, keep_ids):
    with open(infile, newline="", encoding="utf-8") as f_in, open(outfile, "w", newline="", encoding="utf-8") as f_out:
        r = csv.DictReader(f_in)
        w = csv.DictWriter(f_out, fieldnames=r.fieldnames)
        w.writeheader()
        for row in r:
            if row.get(id_field) in keep_ids:
                w.writerow(row)

trip_ids, shape_ids, service_ids = filter_trips("trips.txt", "trips_ubahn.txt")
filter_by_ids("stop_times.txt", "stop_times_ubahn.txt", "trip_id", trip_ids)
if shape_ids:
    filter_by_ids("shapes.txt", "shapes_ubahn.txt", "shape_id", shape_ids)

# Kalender (falls vorhanden)
try:
    filter_by_ids("calendar.txt", "calendar_ubahn.txt", "service_id", service_ids)
except FileNotFoundError:
    pass

try:
    filter_by_ids("calendar_dates.txt", "calendar_dates_ubahn.txt", "service_id", service_ids)
except FileNotFoundError:
    pass
