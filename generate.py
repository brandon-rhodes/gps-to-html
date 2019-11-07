#!/usr/bin/env python3

import argparse
import datetime as dt
import json
import pytz
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from bottle import SimpleTemplate

ISO = '%Y-%m-%dT%H:%M:%SZ'
MILES_PER_METER = 0.000621371

def main(argv):
    template_path = argv[0]
    cache_dir = Path('./cache')
    output_dir = Path('./output')
    fit_paths = argv[1:]

    with open(template_path) as f:
        template_html = f.read()

    if not output_dir.is_dir():
        output_dir.mkdir()

    summaries = []

    for path_string in fit_paths:
        input_path = Path(path_string)
        xml_path = cache_dir / (input_path.stem + '.xml')
        html_path = output_dir / (input_path.stem + '.html')
        if not xml_path.exists():
            convert_to_xml(input_path, xml_path)
        summary = process(xml_path, template_html, html_path)
        summaries.append(summary)

    write_index(summaries, output_dir / 'index.html')

def convert_to_xml(input_path, output_path):
    print('Converting', input_path, '->', output_path)
    cmd = '/home/brandon/usr/lib/garmin/fit2tcx'
    with open(output_path, 'w') as f:
        xml = subprocess.run([cmd, input_path], stdout=f)

def process(xml_path, template_html, output_path):
    xml = open(xml_path).read()
    xml = xml.replace(
        'xmlns="http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2"',
        '',
    )
    import xml.etree.ElementTree as etree
    x = etree.fromstring(xml)

    c = []

    icons = []
    next_mile = 0
    splits = []

    trackpoints = list(parse_trackpoints(x))

    from timezonefinder import TimezoneFinder
    tf = TimezoneFinder()
    name = tf.timezone_at(lng=trackpoints[0].longitude_degrees,
                          lat=trackpoints[0].latitude_degrees)
    tz = pytz.timezone(name)
    utc = pytz.utc
    print(tz)
    for p in trackpoints:
        p.time = utc.localize(p.time).astimezone(tz)

    route = [[p.latitude_degrees, p.longitude_degrees] for p in trackpoints]
    mileposts = list(compute_mileposts(trackpoints))

    icons = [
        {
            'lat': p.latitude_degrees,
            'lon': p.longitude_degrees,
            'label': '{} mi<br>{:%-I:%M} {}'.format(
                p.distance_meters * MILES_PER_METER,
                p.time,
                p.time.strftime('%p').lower(),
            ),
        }
        for p in mileposts
    ]

    def compute_splits(trackpoints, mileposts):
        previous = trackpoints[0]
        for milepost in mileposts + [trackpoints[-1]]:
            meters = milepost.distance_meters - previous.distance_meters
            duration = milepost.time - previous.time
            yield Split(
                start = previous.time,
                end = milepost.time,
                duration = duration,
                meters = meters,
                mph = mph(meters, duration),
            )
            previous = milepost

    splits = list(compute_splits(trackpoints, mileposts))

    meters = trackpoints[-1].distance_meters
    miles = meters * MILES_PER_METER
    duration = trackpoints[-1].time - trackpoints[0].time
    #mph = miles / duration.total_seconds() * 60 * 60

    template = SimpleTemplate(template_html)
    content = template.render(
        duration=duration,
        icons=json.dumps(icons),
        route=json.dumps(route),
        miles=miles,
        mph=mph(meters, duration),
        splits=splits,
        start=trackpoints[0].time,
    )

    print(splits)

    with open(output_path, 'w') as f:
        f.write(content)

    return Summary(start=trackpoints[0].time, miles=miles, url=output_path.name)

def write_index(summaries, output_path):
    with open('index.template.html') as f:
        template_html = f.read()

    template = SimpleTemplate(template_html)
    content = template.render(
        summaries=summaries,
    )

    with open(output_path, 'w') as f:
        f.write(content)

@dataclass
class Summary(object):
    start: dt.datetime
    miles: float
    url: str

@dataclass
class Trackpoint(object):
    time: dt.datetime
    altitude_meters: float = 0.0
    distance_meters: float = 0.0
    latitude_degrees: float = 0.0
    longitude_degrees: float = 0.0

@dataclass
class Split(object):
    start: dt.datetime
    end: dt.datetime
    duration: dt.timedelta
    meters: float = 0.0
    mph: float = 0.0

def mph(meters, duration):
    return meters * MILES_PER_METER / duration.total_seconds() * 60 * 60

def parse_trackpoints(document):
    elements = document.findall('.//Trackpoint')
    for t in elements:
        p = t.find('Position')
        a = t.find('AltitudeMeters')
        if a is None:
            continue
        yield Trackpoint(
            time = dt.datetime.strptime(t.find('Time').text, ISO),
            altitude_meters = float(t.find('AltitudeMeters').text),
            distance_meters = float(t.find('DistanceMeters').text),
            latitude_degrees = float(p.find('LatitudeDegrees').text),
            longitude_degrees = float(p.find('LongitudeDegrees').text),
        )

def compute_mileposts(datapoints):
    datapoints = list(datapoints)
    next_mile = 1
    previous_time = 0
    previous_miles = 0
    for point in datapoints:
        d = point
        miles = d.distance_meters * MILES_PER_METER
        while miles > next_mile:
            fraction = (next_mile - previous_miles) / (miles - previous_miles)
            delta = d.time - previous_time
            yield Trackpoint(
                time = previous_time + delta * fraction,
                distance_meters = next_mile / MILES_PER_METER,
                altitude_meters = interpolate(
                    previous_point.altitude_meters,
                    point.altitude_meters,
                    fraction,
                ),
                latitude_degrees = interpolate(
                    previous_point.latitude_degrees,
                    point.latitude_degrees,
                    fraction,
                ),
                longitude_degrees = interpolate(
                    previous_point.longitude_degrees,
                    point.longitude_degrees,
                    fraction,
                ),
            )
            print(fraction)
            next_mile += 1
        previous_time = d.time
        previous_miles = miles
        previous_point = point

def interpolate(a, b, fraction):
    return a + (b - a) * fraction

# def compute_splits(mileposts):
#

if __name__ == '__main__':
    main(sys.argv[1:])
