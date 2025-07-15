# stream_writer_multi

Simulates a streamed download with:

- 4 HTTP source inputs
- 2 ndjson outputs
- 2 queues dedicated to each output
- each source is routed to a dedicated queue via config file
