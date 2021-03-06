#!/usr/bin/env python3
# We should use a database to store the data
# But right now we don't have time :(

import flask
import redis
import os
import signal
import subprocess as sp
import psutil
import util

from flask_cors import CORS

PID_KEY = 'SCRAPER_PID'

db  = redis.Redis('localhost')
app = flask.Flask(__name__)
CORS(app)

def find_pid():
    pid = db.get(PID_KEY)
    pid = parse_key(pid, int)
    if pid and psutil.pid_exists(pid):
        return pid
    db.delete(PID_KEY)
    return None

def parse_key(pid, cast):
    return cast(pid) if pid else pid

@app.route('/start')
def run():
    pid = find_pid()
    if pid is None:
        try:
            # Check if value can be converted to float
            # Prevent security flaw
            rate = flask.request.args.get('priceRate', 20)
            rate = str(float(rate))
        except ValueError:
            return flask.jsonify({ 'pid': None, 'msg': 'Nein!' })
        
        cmd = [ 'scraper.py', '--price-rate', rate ]
        p = sp.Popen(cmd, stdin=sp.DEVNULL)
        pid = p.pid
        db.set(PID_KEY, pid)

    return flask.jsonify({ 'pid': pid })

@app.route('/status')
def status():
    pid = find_pid()
    st  = { 'pid': pid }
    if pid is None:
        st['status'] = 'stopped'
    st = util.read_status(st)
    return flask.jsonify(st)

@app.route('/stop')
def stop():
    pid = find_pid()
    if pid: os.kill(pid, signal.SIGINT)
    # Ugly fix :(
    sp.run(['pkill', 'chromium'])
    db.delete(PID_KEY)
    return flask.jsonify({ 'pid': pid })

def main():
    return app

if __name__ == '__main__':
    main()

