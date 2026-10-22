#!/usr/bin/env python3
"""Build/start/stop the isolated local demo. Python 3.9+, Docker Compose v2, JDK 8, Maven, Node 20.9+."""
import argparse
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / '.runtime'


def environment():
    env = dict(os.environ)
    path = ROOT / '.env'
    if path.exists():
        for line in path.read_text(encoding='utf-8-sig').splitlines():
            if line.strip() and not line.lstrip().startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                env.setdefault(key.strip(), value.strip().strip('"').strip("'"))
    defaults = {'MYSQL_PORT':'23306', 'MYSQL_PASSWORD':'bigmarket-dev-only', 'REDIS_PORT':'26379',
                'RABBITMQ_PORT':'25673', 'RABBITMQ_MANAGEMENT_PORT':'35673', 'RABBITMQ_USER':'bigmarket',
                'RABBITMQ_PASSWORD':'bigmarket-dev-only', 'BACKEND_PORT':'18091', 'FRONTEND_PORT':'13000'}
    for key,value in defaults.items(): env.setdefault(key,value)
    env['API_HOST_URL'] = 'http://127.0.0.1:' + env['BACKEND_PORT']
    env['FRONTEND_ORIGIN'] = 'http://127.0.0.1:' + env['FRONTEND_PORT']
    env['NEXT_TELEMETRY_DISABLED'] = '1'
    return env


def compose(env):
    return [shutil.which('docker') or 'docker', 'compose', '-p', env.get('COMPOSE_PROJECT_NAME','big-market-fullstack'), '-f', str(ROOT/'compose.infra.yml')]


def execute(args, env, cwd=ROOT, logfile=None):
    print('+', ' '.join(map(str,args)), flush=True)
    if logfile:
        with logfile.open('w',encoding='utf-8') as stream:
            result = subprocess.run(list(map(str,args)),cwd=cwd,env=env,stdout=stream,stderr=subprocess.STDOUT)
        if result.returncode:
            print(logfile.read_text(encoding='utf-8',errors='replace')[-16000:])
            raise RuntimeError(f'Command failed; see {logfile}')
    else:
        subprocess.run(list(map(str,args)),cwd=cwd,env=env,check=True)


def java8(env):
    home = env.get('JAVA8_HOME') or env.get('JAVA_HOME')
    candidates = [Path(home)] if home else []
    if os.name == 'nt': candidates += sorted((Path(os.environ.get('ProgramFiles','C:/Program Files'))/'Java').glob('jdk1.8*'))
    for candidate in candidates:
        binary = candidate/'bin'/('java.exe' if os.name == 'nt' else 'java')
        if not binary.exists(): continue
        version = subprocess.run([str(binary),'-version'],capture_output=True,text=True)
        if '1.8.' in version.stderr + version.stdout:
            env['JAVA_HOME'] = str(candidate)
            env['PATH'] = str(candidate/'bin') + os.pathsep + env['PATH']
            return str(binary)
    binary = shutil.which('java',path=env.get('PATH'))
    if binary and '1.8.' in subprocess.run([binary,'-version'],capture_output=True,text=True).stderr:
        return binary
    raise RuntimeError('JDK 8 required: set JAVA8_HOME or JAVA_HOME to your JDK 8 directory.')


def build(env):
    java8(env)
    execute([shutil.which('mvn') or 'mvn','-B','clean','package','-DskipTests'],env,ROOT/'backend',RUNTIME/'build-backend.log')
    execute([shutil.which('mvn') or 'mvn','-B','-pl','big-market-dxw-app','-am','-Dtest=RedisCodecTest','-Dsurefire.failIfNoSpecifiedTests=false','-DskipTests=false','test'],env,ROOT/'backend',RUNTIME/'codec-test.log')
    execute([shutil.which('npm') or 'npm','ci','--no-audit','--no-fund'],env,ROOT/'frontend',RUNTIME/'npm-ci.log')
    execute([shutil.which('npm') or 'npm','run','build'],env,ROOT/'frontend',RUNTIME/'build-frontend.log')
    execute([shutil.which('npm') or 'npm','run','lint'],env,ROOT/'frontend',RUNTIME/'lint.log')


def spawn(args, cwd, env, name):
    with (RUNTIME/f'{name}.log').open('w',encoding='utf-8') as stream:
        options = {'creationflags':subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS} if os.name=='nt' else {'start_new_session':True}
        process = subprocess.Popen(list(map(str,args)),cwd=cwd,env=env,stdout=stream,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,**options)
    return process


def wait_http(url,process,logfile,timeout=120):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    end = time.monotonic()+timeout
    while time.monotonic()<end:
        if process.poll() is not None: break
        try:
            with opener.open(url,timeout=2) as response:
                if response.status==200:
                    if '/api/' in url:
                        body=json.load(response)
                        if body.get('code')=='0000' and body.get('data') is True:return
                    else:return
        except Exception: time.sleep(1)
    print(logfile.read_text(encoding='utf-8',errors='replace')[-18000:])
    raise RuntimeError(f'Service not ready: {url}; see {logfile}')


def assert_free(port):
    with socket.socket() as s:
        try:s.bind(('127.0.0.1',int(port)))
        except OSError:raise RuntimeError(f'Port {port} is occupied. Stop the existing demo with scripts/dev.py down or change .env.')


def up(env,skip_build=False):
    assert_free(env['BACKEND_PORT']); assert_free(env['FRONTEND_PORT'])
    execute(compose(env)+['up','-d','--wait','--wait-timeout','180'],env)
    if not skip_build:build(env)
    java=java8(env)
    backend=spawn([java,'-Xms128m','-Xmx512m','-jar',ROOT/'backend/big-market-dxw-app/target/big-market-dxw-app.jar','--spring.profiles.active=local'],ROOT/'backend',env,'backend')
    state={'backend':backend.pid}
    (RUNTIME/'processes.json').write_text(json.dumps(state),encoding='utf-8')
    # A real award-list endpoint is POST-only; the armory is a GET readiness check and warms the local demo.
    wait_http(env['API_HOST_URL']+'/api/v1/raffle/activity/armory?activityId=100301',backend,RUNTIME/'backend.log')
    frontend=spawn([shutil.which('node') or 'node',ROOT/'frontend/node_modules/next/dist/bin/next','start','--hostname','127.0.0.1','--port',env['FRONTEND_PORT']],ROOT/'frontend',env,'frontend')
    state['frontend']=frontend.pid
    (RUNTIME/'processes.json').write_text(json.dumps(state),encoding='utf-8')
    url='http://127.0.0.1:'+env['FRONTEND_PORT']
    wait_http(url,frontend,RUNTIME/'frontend.log')
    print('READY:',url+'/?userId=fullstack_demo&activityId=100301',flush=True)


def down(env,infra=False):
    state=RUNTIME/'processes.json'
    if state.exists():
        for name,pid in json.loads(state.read_text()).items():
            if os.name=='nt':
                info=subprocess.run(['powershell.exe','-NoProfile','-Command',f'(Get-CimInstance Win32_Process -Filter "ProcessId = {int(pid)}").CommandLine'],capture_output=True,text=True)
                # Do not kill a reused PID belonging to an unrelated process.
                if str(ROOT).lower().replace('\\','/') not in info.stdout.lower().replace('\\','/'):
                    print(f'Skipping {name} PID {pid}: no matching project command line.');continue
                subprocess.run(['taskkill','/PID',str(pid),'/T','/F'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            else:
                try:
                    command=Path(f'/proc/{pid}/cmdline').read_bytes().decode().replace('\x00',' ')
                    if str(ROOT) in command:os.killpg(int(pid),signal.SIGTERM)
                except (OSError,ProcessLookupError):pass
        state.unlink()
    if infra:execute(compose(env)+['down'],env) # Named database volume intentionally retained.


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['build','up','down'])
    parser.add_argument('--skip-build',action='store_true',help='Only after a successful build with the same .env values')
    parser.add_argument('--infra',action='store_true',help='For down: also stop this Compose stack, preserving its database volume')
    args=parser.parse_args();RUNTIME.mkdir(exist_ok=True);env=environment()
    if args.action=='build':build(env)
    elif args.action=='up':up(env,args.skip_build)
    else:down(env,args.infra)

if __name__=='__main__':
    try:main()
    except Exception as error:
        print('ERROR:',error,file=sys.stderr)
        sys.exit(1)
