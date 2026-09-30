
RAW_POSTS = "weather.raw.posts"
ENRICHED_POSTS = "weather.enriched.posts"
DEDUPED_POSTS = "weather.deduped.posts"
CLASSIFIED_POSTS = "weather.classified.posts"
VERIFIED_POSTS = "weather.verified.posts"
DLQ = "weather.dlq"

ALL_TOPICS = [RAW_POSTS, ENRICHED_POSTS, DEDUPED_POSTS, CLASSIFIED_POSTS, VERIFIED_POSTS, DLQ]
PARTITIONS = 4
REPLICATION = 1
