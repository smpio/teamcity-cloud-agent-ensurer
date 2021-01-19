import os
import time
import logging
import argparse

import requests

log = logging.getLogger(__name__)

# TODO: add schedule


def main():
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('--base-url', required=True)
    arg_parser.add_argument('--auth-token', required=True)
    arg_parser.add_argument('--cloud-profile-id', required=True)
    arg_parser.add_argument('--min-idle-agents', type=int, default=1)
    arg_parser.add_argument('--watch-interval-sec', type=int, default=60)
    arg_parser.add_argument('--log-level', default='INFO')
    args = arg_parser.parse_args()

    logging.basicConfig(format='%(message)s', level=args.log_level.upper())

    log.info('Base URL: %s', args.base_url)

    if args.auth_token.startswith('$'):
        args.auth_token = os.environ[args.auth_token[1:]]

    s = requests.Session()
    s.headers['Accept'] = 'application/json'
    s.headers['Authorization'] = f'Bearer {args.auth_token}'

    # Test connection
    resp = s.get(f'{args.base_url}app/rest/server')
    resp.raise_for_status()

    while True:
        resp = s.get(f'{args.base_url}app/rest/agents?fields=agent(id,name,connected,enabled,idleSinceTime)')
        resp.raise_for_status()
        agents = resp.json()
        idle_agents = [a for a in agents['agent'] if a['enabled'] and a.get('idleSinceTime')]
        connected_idle_agents = [a for a in idle_agents if a['connected']]

        resp = s.get(f'{args.base_url}app/rest/cloud/instances')
        resp.raise_for_status()
        cloud_instances = resp.json()
        scheduled_agents_count = sum(1 for i in cloud_instances['cloudInstance'] if i['state'] == 'scheduled_to_start')

        log.info('Agents: %d idle (%d connected), %d pending. Target: %d',
                 len(idle_agents),
                 len(connected_idle_agents),
                 scheduled_agents_count,
                 args.min_idle_agents)

        agents_to_start = args.min_idle_agents - len(idle_agents) - scheduled_agents_count
        if agents_to_start > 0:
            log.info('Starting %d agents', agents_to_start)
            for _ in range(agents_to_start):
                s.cookies.clear()  # clear session cookies to fix CSRF error
                log.debug('Starting cloud instance with profile ID "%s"', args.cloud_profile_id)
                resp = s.post(f'{args.base_url}app/rest/cloud/instances', json={
                    'image': {
                        'id': f'profileId:{args.cloud_profile_id}',
                    },
                })
                resp.raise_for_status()

        log.debug('Sleeping %d seconds', args.watch_interval_sec)
        time.sleep(args.watch_interval_sec)


if __name__ == '__main__':
    main()
