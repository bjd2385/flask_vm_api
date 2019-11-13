TODO:
    1. Implement field schema parser to ensure additional fields can't be added
       to a request.
    2. Cache all host-level calls.
    3. Add a restricted user for host-level calls / information gathering. Problem
       is, I don't know how to implement this; thoughts are, maybe a restricted user
       that only has the ability to execute specific commands (e.g., `uptime`).
    4. `uptimeCache`, by default, reads the entire file into memory. It may be
       better to scale the number of cached results by the length of valid
       hosts (you never know how many you may have), then read a new file for
       each from disk as it's requested into memory.
    5. Add schema validation on input (and output?) JSON.
    6. Fix `resources` endpoint return structure. My goal at this time is just to
       get the data, which I've accomplished. Later, I need to come back and
       restructure it so it actually makes _sense_.
    7. At points of file IO, perhaps it would make sense on cache refresh to 
       add async IO and an async cache decorator.
    8. Spin off a worker to go create the ZFS dataset and VM from this API's threads.
       In other words, the API POST request would update a database and create a
       thread, which
    9. Refactor so that Libvirt connections are opened to all available hosts from
       the start, as opposed to opening them and tearing them down for every request.
    10. Refactor with cached async functions?