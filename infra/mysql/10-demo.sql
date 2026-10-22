-- Dedicated local test account. Never execute this initializer against a production database.
-- Seed in both shard account tables so the demonstration does not assume a router hash implementation.
INSERT IGNORE INTO big_market_01.raffle_activity_account
(user_id,activity_id,total_count,total_count_surplus,day_count,day_count_surplus,month_count,month_count_surplus)
VALUES ('fullstack_demo',100301,1000,1000,100,100,1000,1000);
INSERT IGNORE INTO big_market_02.raffle_activity_account
(user_id,activity_id,total_count,total_count_surplus,day_count,day_count_surplus,month_count,month_count_surplus)
VALUES ('fullstack_demo',100301,1000,1000,100,100,1000,1000);
