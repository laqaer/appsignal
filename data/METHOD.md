# METHOD (rank+velocity v1)
Inputs: Apple RSS rank per chart + lookup rating/price.
Downloads: dl_day=20000*(50/rank)^0.7, x30 for month. Velocity: rating-count delta/day when 2+ snapshots exist.
Revenue: paid=price*dl*0.7; free=grossing?0.12:0.04 USD per dl. Caps: none beyond curve.
Limits: US charts only, estimates not exact, first run has no velocity. All UI values prefixed est.
