# -*- coding: utf-8 -*-

"""

 RZD API

"""

import requests
import json
import time

import avia
import myutils
import urllib

places_cache = { }

def find_places(namepart):
    """Find places.
    returns an array of 
    { 
        'name' : 'МОСКВА',  (upper case only)
        'code' : 123        (int)
    }
    """
    namepart = namepart.upper()
    r = requests.get('http://rzd.ru/suggester?lang=ru&stationNamePart='+namepart)
    if r.text == '':
        return []
    res = sorted(r.json(), key=lambda k: -(k['S'] + k['L'])) 
    res = [{'name':item['n'], 'code':item['c']} for item in res if namepart in item['n']]


    return res

def get_tickets(origin, destination, date):
    """Get tickets.

    :param origin: Москва
    :param destination: Омск
    :param date: 2016-12-29
    """
    return format_tickets_data(get_tickets_rawdata(origin, destination, date))

def get_tickets_rawdata(origin, destination, date):
    """get_tickets_rawdata(find_places('москва')[0], find_places('омск')[0], '2016-12-29')
    """

    o = myutils.find_cities(origin)
    d = myutils.find_cities(destination)

    check = myutils.check_zero_len(o, d, origin, destination, 'no such city')
    if not check == 'ok':
        return check
    o = o[0]
    d = d[0]

    o = find_places(o['name'])
    d = find_places(d['name'])

    check = myutils.check_zero_len(o, d, origin, destination, 'no such train station')
    if not check == 'ok':
        return check
    o = o[0]
    d = d[0]

    rzd_date = date_to_retarded_rzd_date(date)

    requesturi = 'http://pass.rzd.ru/timetable/public/ru'
    _params = {
        'STRUCTURE_ID':'735',
        'layer_id':'5371',
        'dir':'0',
        'tfl':'3',
        'checkSeats':'1',

        #'st0':origin.name,
        'code0':o['code'],
        #'st1':destination.name,
        'code1':d['code'],
        'dt0':rzd_date
        }

    r = requests.get(requesturi, params = _params)

    if r.text == '':
        return {'error':'empty response'}

    rj = r.json()

    if not 'result' in rj or not rj['result'] == 'RID':
        return rj

    _params['rid'] = str(rj['rid'])

    return myutils.poll_request(requesturi, 
                                params = _params, 
                                cookies = r.request._cookies, 
                                headers = r.request.headers, 
                                result_return_condition = (lambda r: r['result'] == 'OK'))

def format_tickets_data(data):
    if not 'result' in data or not data['result'] == 'OK':
        return data

    paths = []
    
    list = data['tp'][0]['list']
    for route in list:
        if 'brand' in route and route['brand']=='': del route['brand']
        segment = {
            'type' : 'Train',
            'origin' : myutils.find_make_place(route['station0']),
            'destination' : myutils.find_make_place(route['station1']),
            'departure' : retarded_date_time_to_good(route['date0'], route['time0']), 
            'arrival' : retarded_date_time_to_good(route['date1'], route['time1']),
            'duration' : int(retarded_duration_to_minutes(route['timeInWay'])),
            'pricing' : get_pricing(route, data['tp'][0]),
            'carrier' : {
                'name' : route['carrier'],
                'image' : 'http://pass.rzd.ru/images/logo/logo_rzd.gif',
                'flightNumber' : route['number'] + ('' if not 'brand' in route else ' «'+route['brand']+'»'),
                'code' : route['carrier']
                }
            }

        paths.append({
            'segments' : [segment]
            })
        
    return {
        'route': {
            'origin' : myutils.find_make_place(data['tp'][0]['from']),
            'destination' : myutils.find_make_place(data['tp'][0]['where']),
            'departure' : retarded_date_time_to_good(data['tp'][0]['date']),
            'paths' : paths
            }
        }

def retarded_duration_to_minutes(rzd_duration):
    """Convert hours into minutes.
    :param rzd_duration: '47:14'
    :return: '2834'
    """
    s = rzd_duration.split(':')
    return str(int(s[0])*60 + int(s[1]))

def retarded_date_time_to_good(rzd_date, rzd_time = ''):
    """Convert rzd_date and rzd_time to normal dateTtime.

    :param rzd_date: '29.12.2016'
    :param rzd_time: '16:40'

    :return: '2016-12-29T16:40:00'
    """

    s = rzd_date.split('.')
    date = s[2] + '-' + s[1] + '-' + s[0]

    _time = rzd_time
    if not _time == '':
        _time = 'T' + _time + ':00'

    return date + _time

def date_to_retarded_rzd_date(date):
    """Convert normal date to rzd_date.

    :param date: '2016-12-29'

    :return: '29.12.2016'
    """
    s = date.split('-')
    return s[2]+'.'+s[1]+'.'+s[0]

def get_pricing(route, tp):
    res = []

    link = ('https://pass.rzd.ru/timetable/public/ru?STRUCTURE_ID=735&refererPageId=704#dir=0|tfl=3|checkSeats=1|st0=№%20'+
    urllib.parse.quote(route['number'])+
    '|code0='+
    urllib.parse.quote(str(tp['fromCode']))+
    '|dt0='+
    urllib.parse.quote(tp['date'])+
    '|st1=|code1='+
    urllib.parse.quote(str(tp['whereCode'])))

    for car in route['cars']:
        res.append({
            'price' : float(car["tariff"]),
            'currency' : 'RUB',
            'link' : link,
            'agent' : {
                'name' : car["typeLoc"],
                'image' : ''
                }
            })

    return res