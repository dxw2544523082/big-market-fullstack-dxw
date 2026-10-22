#!/usr/bin/env python3
"""Real API -> MySQL smoke test. Creates one demo draw; no Mock and no production credentials."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import urllib.request

from dev import ROOT, RUNTIME, compose, environment

USER = 'fullstack_demo'
ACTIVITY = 100301


def sql(env, statement):
    args = compose(env)+['exec','-T','-e','MYSQL_PWD='+env['MYSQL_PASSWORD'],'mysql','mysql','-uroot','--batch','--raw','--skip-column-names','-e',statement]
    p = subprocess.run(args,cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True)
    return p.stdout.decode('utf-8').strip().splitlines()


def records(env,table,columns):
    selects=[]
    for db in ['big_market_01','big_market_02']:
        tables=[f'{table}_{i:03}' for i in range(4)] if table in ['user_raffle_order','user_award_record'] else [table]
        for name in tables:
            pairs=", ".join(f"'{col}', `{col}`" for col in columns)
            selects.append(f"SELECT JSON_OBJECT('database','{db}','table','{name}',{pairs}) FROM {db}.{name} WHERE user_id='{USER}'")
    return [json.loads(row) for row in sql(env,' UNION ALL '.join(selects)+';')]


def snapshot(env):
    return {'orders':records(env,'user_raffle_order',['order_id','order_state','activity_id']),
            'awards':records(env,'user_award_record',['order_id','award_id','award_state']),
            'tasks':records(env,'task',['message_id','state']),
            'accounts':records(env,'raffle_activity_account',['total_count_surplus'])}


def api(base,path,data=None):
    req=urllib.request.Request(base+path,data=json.dumps(data).encode() if data is not None else None,
                               headers={'Content-Type':'application/json'})
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(req,timeout=20) as response:body=json.load(response)
    assert body.get('code')=='0000',body
    return body


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--draws',type=int,default=1)
    parser.add_argument('--output',default=str(RUNTIME/'smoke.json'))
    args=parser.parse_args()
    assert 1<=args.draws<=10,'Use 1..10 test draws only.'
    env=environment();base='http://127.0.0.1:'+env['BACKEND_PORT']
    before=snapshot(env)
    armory=api(base,'/api/v1/raffle/activity/armory?activityId=100301')
    # Hit the cache again: this detects the old JSONObject/ClassCastException regression.
    armory_again=api(base,'/api/v1/raffle/activity/armory?activityId=100301')
    request={'userId':USER,'activityId':ACTIVITY}
    listing=api(base,'/api/v1/raffle/strategy/query_raffle_award_list',request)
    assert len(listing['data'])==8,listing
    results=[api(base,'/api/v1/raffle/activity/draw',request) for _ in range(args.draws)]
    after=snapshot(env)
    old_orders={row['order_id'] for row in before['orders']}
    old_awards={row['order_id'] for row in before['awards']}
    new_orders=[row for row in after['orders'] if row['order_id'] not in old_orders]
    new_awards=[row for row in after['awards'] if row['order_id'] not in old_awards]
    assert len(new_orders)==args.draws,(new_orders,results)
    assert len(new_awards)==args.draws,(new_awards,results)
    assert all(row['order_state']=='used' for row in new_orders),new_orders
    assert {x['order_id'] for x in new_orders}=={x['order_id'] for x in new_awards}
    assert Counter(row['award_id'] for row in new_awards)==Counter(row['data']['awardId'] for row in results)
    assert len(after['tasks'])-len(before['tasks'])==args.draws
    assert sum(x['total_count_surplus'] for x in before['accounts'])-sum(x['total_count_surplus'] for x in after['accounts'])==args.draws
    old_tasks={x['message_id'] for x in before['tasks']}
    assert all(x['state']=='completed' for x in after['tasks'] if x['message_id'] not in old_tasks),after['tasks']
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open('http://127.0.0.1:'+env['FRONTEND_PORT'],timeout=10) as res:
        assert res.status==200 and '大营销平台'.encode() in res.read()
    report={'timestamp':datetime.now(timezone.utc).isoformat(),'backend':base,'mock':False,
            'armory':armory,'armory_cache_hit':armory_again,'award_count':len(listing['data']),
            'draws':results,'new_orders':new_orders,'new_awards':new_awards,
            'new_tasks':[x for x in after['tasks'] if x['message_id'] not in old_tasks],
            'quota_decrement':args.draws,'frontend_http':200,'passed':True}
    output=Path(args.output);output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=True,indent=2))
    print('PASS; evidence:',output)

if __name__=='__main__':
    try:main()
    except Exception as error:
        print('FAIL:',error,file=sys.stderr);sys.exit(1)
