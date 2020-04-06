import redis

rs = redis.Redis(host='host1', port=6379, db=0)
rd = redis.Redis(host='host2', port=6379, db=0)

print('Getting data...')
data = rs.lrange('key', 0, 100000000)

print('Migrating...')
total = len(data)
now = 0
for d in data:
    now += 1

    rd.rpush('key', d)

    if not now % 100:
        print('Progress: %d%% (%d/%d)' % ((now / total) * 100, now, total))
