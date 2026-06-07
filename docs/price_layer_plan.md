# Price layer plan

The price layer starts with source discovery.

Current aim:

- identify a usable SMARD price endpoint
- validate that the endpoint returns hourly numeric values
- keep price ingestion separate from the existing risk model
- only merge prices after the price table has its own quality checks

No trading or P&L claim should be made from source discovery alone.
