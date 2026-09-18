# URL-shortener domain notes

Aliases are lowercase URL-safe slugs. Generated aliases are collision-safe. Expiration
is enforced synchronously even when DynamoDB TTL is enabled. Redirects return before
analytics aggregation completes; click events are sanitized and processed asynchronously.
