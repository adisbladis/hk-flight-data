#!/usr/bin/env python
from prettytable import PrettyTable
from dataclasses import dataclass
from textwrap import dedent
from datetime import date
import pandas as pd
from typing import (
    List,
    Dict,
)
import requests
import tempfile
import os.path
import tabula
import csv
import os


URL = "https://www.chp.gov.hk/files/pdf/flights_trains_en.pdf"


SEATS_DEFAULT = 301  # Smallest capacity of a 777
SEATS = {
    "EK384": 354,
}


@dataclass
class Entry:
    flight_no: str
    departure_city: str
    seat: str
    arrival_date: date
    related_cases: str


if __name__ == "__main__":
    resp = requests.get(URL)
    with tempfile.NamedTemporaryFile(mode="wb") as f:
        for chunk in resp.iter_content(100):
            f.write(chunk)
        f.flush()
        df = tabula.read_pdf(f.name, pages="all", silent=True)

    entries: List[Entry] = []

    for page in df:
        if "Ship" in page.columns[0]:
            continue
        for i, row in page.iterrows():
            if pd.isna(row[0]):
                continue

            entries.append(
                Entry(
                    flight_no=row[0],
                    departure_city=row[1],
                    seat=row[2],
                    arrival_date=date(*[int(i) for i in reversed(row[3].split("/"))]),
                    related_cases=row[4],
                )
            )

    # Entries grouped by flight -> date
    entries_grouped: Dict[str, Dict[date, List[Entry]]] = {}
    for entry in entries:
        entries_grouped.setdefault(entry.flight_no, {}).setdefault(
            entry.arrival_date, []
        ).append(entry)

    field_names = [
        "Flight",
        "City",
        "Date",
        "Number positive",
        "Percent positive",
        "Assumed capacity",
    ]

    table = PrettyTable()
    table.field_names = field_names

    try:
        os.mkdir("dist")
    except FileExistsError:
        pass

    with open(os.path.join("dist", "flights.csv"), "w", newline="") as csvfile:
        csv_writer = csv.writer(csvfile)
        csv_writer.writerow(field_names)

        for flight_no in sorted(entries_grouped.keys()):
            flight = entries_grouped[flight_no]
            for date in sorted(flight.keys()):
                capacity = SEATS.get(flight_no, SEATS_DEFAULT)

                flight = entries_grouped[flight_no]
                flight_entries = flight[date]
                num_positive = len(flight_entries)
                pct = round((100 / capacity) * num_positive, 2)

                line = [
                    flight_no,
                    flight_entries[0].departure_city,
                    date,
                    num_positive,
                    pct,
                    capacity,
                ]
                table.add_row(line)
                csv_writer.writerow(line)

    with open(os.path.join("dist", "index.html"), "w") as htmlfile:
        htmlfile.write(
            dedent(
                """
        <html>
          <head>
            <title>HK positive covid cases flight data</title>
          </head>
          <body>
        """
            )
        )
        htmlfile.write(table.get_html_string())
        htmlfile.write(
            dedent(
                """
          <hr />
          <div>
            <p>This data is also available as <a href="./flight.csv">CSV</a>.</p>
            <p>Generator managed at <a href="https://github.com/adisbladis/hk-flight-data">https://github.com/adisbladis/hk-flight-data</a>.</p>
          </div>
          </body>
        </html>
        """
            )
        )

    print(table)
