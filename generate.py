#!/usr/bin/env python3

import argparse
import datetime as dt
import json
import os
import pytz
import subprocess
import sys
from dataclasses import dataclass
from glob import glob
from pathlib import Path

import xml.etree.ElementTree as etree
from bottle import SimpleTemplate
from geopy.distance import distance as geopy_distance

import reverse_geocoder

ISO = '%Y-%m-%dT%H:%M:%SZ'
FEET_PER_METER = 3.2808399
MILES_PER_METER = 0.000621371
cache_dir = Path('./cache')
nan = float('nan')

def main(argv):
    # build_red_mountain()
    # build_rest()
    build_walhalla()

def build_red_mountain():
    scene = Scene()
    scene.append('~/Downloads/red_mountain_1.gpx')
    scene.add_icon('Camp 1')
    scene.append('~/Downloads/red_mountain_2.gpx')
    scene.add_icon('Camp 2')
    scene.append('~/Downloads/red_mountain_3.gpx')
    print(len(scene.trackpoints))
    geocoder = CachingGeocoder(cache_dir / 'geocodings.json')
    scene.write(geocoder, 'output/2019-red-mountain.html',
                dt.date(2019, 10, 26))

def build_walhalla():
    # cache_dir = Path('./cache')
    # geocoder = CachingGeocoder(cache_dir / 'geocodings.json')
    # for path in glob('cache/*.xml'):
    #     # if not 'A3BD4526' in path:
    #     #     continue
    #     name = path.split('/')[1].split('.')[0]
    cache_dir = Path('./cache')
    geocoder = CachingGeocoder(cache_dir / 'geocodings.json')

    scene = Scene()
    for path in sorted(glob('cache/*.xml')):
        filename = path.split('/')[-1]
        if 'A9R' < filename < 'AA3':
            scene.append(path)
    scene.write(geocoder, 'output/walhalla.html', None)

def build_rest():
    cache_dir = Path('./cache')
    geocoder = CachingGeocoder(cache_dir / 'geocodings.json')
    for path in glob('cache/*.xml'):
        # if not 'A3BD4526' in path:
        #     continue
        name = path.split('/')[1].split('.')[0]
        scene = Scene()
        scene.append(path)
        scene.write(geocoder, 'output/%s.html' % name, None)

def build_one(path):
    cache_dir = Path('./cache')
    geocoder = CachingGeocoder(cache_dir / 'geocodings.json')
    #name = path.split('/')[1].split('.')[0]
    scene = Scene()
    scene.append(path)
    output_path = 'output/show.html'
    scene.write(geocoder, output_path, None)
    print(output_path)

class Scene:
    def __init__(self):
        self.icons = []
        self.trackpoints = []

    def append(self, path):
        path = Path(path).expanduser()
        # cache_dir = Path('./cache')
        # xml_path = cache_dir / (path.stem + '.xml')
        # if not xml_path.exists():
        #     convert_to_xml(path, xml_path)
        # with xml_path.open() as f:
        #     xml = f.read()
        # xml = xml.replace('xmlns="http://www.garmin.com/xmlschemas'
        #                   '/TrainingCenterDatabase/v2"', '')
        # import xml.etree.ElementTree as etree
        # x = etree.fromstring(xml)
        # self.trackpoints.extend(parse_trackpoints(x))
        print(path)
        with open(path, 'rb') as f:
            x = f.read()
        previous = self.trackpoints[-1] if self.trackpoints else None
        trackpoints = list(parse_trackpoints(x))
        trackpoints = synthesize_distance(previous, trackpoints)
        self.trackpoints.extend(trackpoints)

    def add_icon(self, label):
        p = self.trackpoints[-1]
        self.icons.append({
            'lat': p.latitude_degrees,
            'lon': p.longitude_degrees,
            'label': label,
        })

    def write(self, geocoder, path, start=None):
        html = render_html(self, geocoder, start, self.icons)
        path = Path(path).expanduser()
        with path.open('w') as f:
            f.write(html)

def foof():
    exit
    template_path = argv[0]
    cache_dir = Path('./cache')
    output_dir = Path('./output')
    fit_paths = argv[1:]

    with open(template_path) as f:
        template_html = f.read()

    if not output_dir.is_dir():
        output_dir.mkdir()

    geocoder = CachingGeocoder(cache_dir / 'geocodings.json')

    summaries = []

    for path_string in fit_paths:
        input_path = Path(path_string)
        xml_path = cache_dir / (input_path.stem + '.xml')
        html_path = output_dir / (input_path.stem + '.html')
        if not xml_path.exists():
            convert_to_xml(input_path, xml_path)
        summary = process(xml_path, geocoder, template_html, html_path)
        summaries.append(summary)

    write_index(summaries, output_dir / 'index.html')
    geocoder.save()

class CachingGeocoder(object):
    def __init__(self, path):
        self.path = path
        try:
            self.data = json.load(path.open())
        except FileNotFoundError:
            self.data = {}

    def search(self, lat, lon):
        key = '%.6f %.6f' % (lat, lon)
        result = self.data.get(key)
        if result is not None:
            return result
        result = reverse_geocoder.search([(lat, lon)])
        self.data[key] = result
        return result

    def save(self):
        j = json.dumps(self.data)  # to catch all errors before opening file
        with self.path.open('w') as f:
            f.write(j)
            f.write('\n')

def convert_to_xml(input_path, output_path):
    print('Converting', input_path, '->', output_path)
    cmd = '/home/brandon/usr/lib/garmin/fit2tcx'
    with open(output_path, 'w') as f:
        subprocess.run([cmd, input_path], stdout=f)

def process(xml_path, geocoder, template_html, output_path):
    xml = open(xml_path).read()
    xml = xml.replace(
        'xmlns="http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2"',
        '',
    )
    x = etree.fromstring(xml)

    c = []

    icons = []
    next_mile = 0
    splits = []

    trackpoints = list(parse_trackpoints(x))

def render_html(scene, geocoder, start, icons):
    trackpoints = scene.trackpoints

    if not trackpoints:
        print('EMPTY')
        return 'NOTHING'

    lat0 = trackpoints[0].latitude_degrees
    lon0 = trackpoints[0].longitude_degrees

    geocodes = geocoder.search(lat0, lon0)
    geocode = geocodes[0]

    from timezonefinder import TimezoneFinder
    tf = TimezoneFinder()
    name = tf.timezone_at(lng=lon0, lat=lat0)
    tz = pytz.timezone(name)
    utc = pytz.utc
    print(tz)
    for p in trackpoints:
        if p.time is not None:
            p.time = utc.localize(p.time).astimezone(tz)

    route = [[p.latitude_degrees, p.longitude_degrees] for p in trackpoints]
    mileposts = list(insert_mileposts(trackpoints))

    icons.extend(
        {
            'lat': p.latitude_degrees,
            'lon': p.longitude_degrees,
            'label': '{:.0f} mi<br>{:%-I:%M} {}'.format(
                p.distance_meters * MILES_PER_METER,
                p.time,
                p.time.strftime('%p').lower(),
            ) if p.time else '{:.0f}'.format(
                p.distance_meters * MILES_PER_METER,
            ),
        }
        for p in mileposts
    )

    def compute_splits(trackpoints, mileposts):
        previous = trackpoints[0]
        for m in mileposts + [trackpoints[-1]]:
            meters = m.distance_meters - previous.distance_meters
            duration = m.time - previous.time if m.time else None
            yield Split(
                start = previous.time,
                end = m.time,
                duration = duration,
                meters = meters,
                mph = mph(meters, duration),
                elevation_meters = m.elevation_meters,
                elevation_gain_meters = (
                    m.elevation_gain_meters - previous.elevation_gain_meters
                    if previous else nan
                ),
                elevation_loss_meters = (
                    m.elevation_loss_meters - previous.elevation_loss_meters
                    if previous else nan
                ),
            )
            previous = m

    splits = list(compute_splits(trackpoints, mileposts))
    if trackpoints[0].time is None:
        duration = None
    else:
        duration = trackpoints[-1].time - trackpoints[0].time

    meters = trackpoints[-1].distance_meters
    miles = meters * MILES_PER_METER
    #mph = miles / duration.total_seconds() * 60 * 60

    # TODO: read only once instead of N times
    template_path = 'test.template.html'
    with open(template_path) as f:
        template_html = f.read()

    template = SimpleTemplate(template_html)
    content = template.render(
        duration=duration,
        escale=FEET_PER_METER,
        icons=json.dumps(icons),
        route=json.dumps(route),
        miles=miles,
        mph=mph(meters, duration),
        nan=nan,
        splits=splits,
        start=start or trackpoints[0].time,
    )

    #print(splits)

    return content

    with open(output_path, 'w') as f:
        f.write(content)

    print(geocode)

    return Summary(
        geocode=geocode,
        start=trackpoints[0].time,
        miles=miles,
        url=output_path.name,
    )

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
    geocode: dict
    start: dt.datetime
    miles: float
    url: str

@dataclass
class Trackpoint(object):
    time: dt.datetime = None
    latitude_degrees: float = 0.0
    longitude_degrees: float = 0.0
    distance_meters: float = 0.0
    elevation_meters: float = 0.0
    elevation_gain_meters: float = 0.0
    elevation_loss_meters: float = 0.0

@dataclass
class Split(object):
    start: dt.datetime
    end: dt.datetime
    duration: dt.timedelta
    meters: float = 0.0
    mph: float = 0.0
    elevation_meters: float = 0.0
    elevation_gain_meters: float = 0.0
    elevation_loss_meters: float = 0.0

def mph(meters, duration):
    if duration is None:
        return nan
    try:
        return meters * MILES_PER_METER / duration.total_seconds() * 60 * 60
    except ZeroDivisionError:
        return 0.0

def parse_trackpoints(text):
    if b'<gpx ' in text:
        return parse_gpx(text)
    if b'<TrainingCenterDatabase ' in text:
        return parse_tcx(text)
    raise ValueError('not sure how to parse')

#usr/lib/garmin/fit2tcx

import re
XMLNS = re.compile(rb' xmlns="[^"]+"')

def parse_gpx(text):
    text = XMLNS.sub('', text)
    x = etree.fromstring(text)
    for p in x.findall('.//trkpt'):
        e = p.find('ele')
        yield Trackpoint(
            elevation_meters = float(e.text),
            latitude_degrees = float(p.attrib['lat']),
            longitude_degrees = float(p.attrib['lon']),
        )

def parse_tcx(text):
    text = XMLNS.sub(b'', text)
    x = etree.fromstring(text)
    elements = x.findall('.//Trackpoint')
    for t in elements:
        alt = t.find('AltitudeMeters')
        p = t.find('Position')
        if alt is None or p is None:
            continue
        lat = p.find('LatitudeDegrees')
        lon = p.find('LongitudeDegrees')
        # if alt is None or lat is None or lon is None:
        #     continue
        yield Trackpoint(
            time = date_of(t, 'Time'),
            elevation_meters = float(alt.text),
            distance_meters = float_of(t, 'DistanceMeters'),
            latitude_degrees = float(lat.text),
            longitude_degrees = float(lon.text),
        )

def date_of(parent, name):
    e = parent.find(name)
    if e is None:
        s = '2019-11-11T01:02:03Z'
    else:
        s = e.text
    return dt.datetime.strptime(s, ISO)

def float_of(parent, name):
    element = parent.find(name)
    if element is None:
        return nan
    return float(element.text)

def synthesize_distance(previous, trackpoints):
    p = previous
    for t in trackpoints:
        if not t.distance_meters and p:
            t.distance_meters = p.distance_meters + geopy_distance(
                (p.latitude_degrees, p.longitude_degrees),
                (t.latitude_degrees, t.longitude_degrees),
            ).m
        if p:
            t.elevation_gain_meters = p.elevation_gain_meters
            t.elevation_loss_meters = p.elevation_loss_meters
            difference = t.elevation_meters - p.elevation_meters
            if difference > 0:
                t.elevation_gain_meters += difference
            else:
                t.elevation_loss_meters += difference
        yield t
        p = t

def insert_mileposts(datapoints):
    datapoints = list(datapoints)
    next_mile = 1.0
    previous_time = 0
    previous_miles = 0
    for point in datapoints:
        d = point
        miles = d.distance_meters * MILES_PER_METER
        while miles > next_mile:
            fraction = (next_mile - previous_miles) / (miles - previous_miles)
            delta = None if d.time is None else d.time - previous_time
            yield Trackpoint(
                time = None if delta is None else previous_time + delta * fraction,
                distance_meters = next_mile / MILES_PER_METER,
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
                elevation_meters = interpolate(
                    previous_point.elevation_meters,
                    point.elevation_meters,
                    fraction,
                ),
                elevation_gain_meters = interpolate(
                    previous_point.elevation_gain_meters,
                    point.elevation_gain_meters,
                    fraction,
                ),
                elevation_loss_meters = interpolate(
                    previous_point.elevation_loss_meters,
                    point.elevation_loss_meters,
                    fraction,
                ),
            )
            print(fraction)
            next_mile += 1.0
        previous_time = d.time
        previous_miles = miles
        previous_point = point

def interpolate(a, b, fraction):
    return a + (b - a) * fraction

# def compute_splits(mileposts):
#

if __name__ == '__main__':
    main(sys.argv[1:])
