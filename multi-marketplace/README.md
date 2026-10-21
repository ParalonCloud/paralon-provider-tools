# One machine, several marketplaces, no double rentals

`dual_list.py` keeps a machine listed on Paralon and on another marketplace in step: rented on Paralon, it unlists it there; busy there, it takes the node off Paralon (`PATCH /nodes/{id}` `{"available": false}`); free on both, it lists it everywhere again. When both rent inside the same poll window, a Paralon spot node is reclaimed with two minutes' notice.

```bash
pip install requests
export PARALON_API_KEY=prlc_your_key PARALON_NODE_ID=<your node id>
export OTHER_UNLIST_CMD="<your marketplace's unlist command>" OTHER_LIST_CMD="<its list command>"
python3 dual_list.py
```

Fill in `busy_elsewhere()` with how you detect the other marketplace's job (its containers, its API, or a file); by default it looks at `/tmp/busy-elsewhere`, so you can try it safely. Full guide: https://paraloncloud.com/resources/list-gpu-on-multiple-marketplaces
