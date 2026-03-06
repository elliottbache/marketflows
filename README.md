<!-- docs:start -->
# MarketFlows

## PRE-RELEASE

[![CI](https://github.com/elliottbache/marketflows/actions/workflows/ci.yaml/badge.svg)](https://github.com/elliottbache/marketflows/actions/workflows/ci.yaml)
[![codecov](https://codecov.io/github/elliottbache/marketflows/graph/badge.svg?token=kNwbaexX4N)](https://codecov.io/github/elliottbache/marketflows) 
[![Docs](https://img.shields.io/badge/docs-Read%20the%20Docs-brightgreen)](https://marketflows.readthedocs.io/en/latest/?badge=latest)
[![Release](https://img.shields.io/github/v/release/elliottbache/marketflows)](https://github.com/elliottbache/marketflows/releases)
[![License: GPL-3.0](https://img.shields.io/badge/license-%20%20GNU%20GPLv3%20-green?style=plastic)](https://github.com/elliottbache/marketflows/blob/main/LICENSE)

Track capital flows and narrative rotation across markets.

## Tutorial
The outputs from running in tutorial mode
```bash
marketflows --tutorial
```
should closely resemble the following plots.

![Tutorial – Narratives](docs/images/tutorial_Narratives_MC_by_us-dollar.png)
![Tutorial – Narratives_EMA](docs/images/tutorial_Narratives_MC_by_us-dollar_ema20.png)
![Tutorial – Narratives_Table](docs/images/tutorial_Narratives_MC_by_us-dollar_percent_gains_table.png)

## How it works
This program makes multiple queries when run and may be slow due to rate limits.

### Which coins are used in market cap ranges?
At the time of running MarketFlows, all the coins with a market cap above the lower limit of the smallest 
range are queried.  At each time step, the bucket of coins within each range is redefined.
This means that coins that were below the smallest market cap will not be included in the study
even if they were above the lower limit at some point in the past.  This means that there will be a certain
amount of inherent bias.  In order to mitigate this as much as possible, the smallest range (e.g. 
micro caps) will contain all the coins up to the lower limit of the next largest range.  

Example: we have micro, small, mid, and large cap ranges.  The respective lower limits are 
\$100M, \$1B, \$10B and \$100B.  Any coin that had a market cap of \$110M at the time of launching
the program will be included in the micro cap bucket as long as its market cap does not exceed
\$1B.  If it has a market cap of \$10M 2 days before the program is launched, it will be included
in the micro cap range.  

If we leave the same coins in the same buckets, then coins that are no longer micro cap and have done a 100X
could be mislabeled, thus skewing results.  In the same way, large caps that have fallen could
no longer be large caps, but would count as such in calculations.  

What we need to do is different depending on the derivative we are considering ($0^{th}$
corresponds to market caps, $1^{st}$ corresponds to market cap growth, and $2^{nd}$ corresponds
to market cap inflection).
0. 
   1. Group assets by market cap at $1^{st}$ time step.
   2. Repeat for time step $n$.
1. 
   1. Group assets by market cap at $2^{nd}$ time step for $1^{st}$ and $2^{nd}$ time steps.
   2. Calculate diff at $2^{nd}$ time step.
   3. Repeat for time step $n$.
2. 
   1. Group assets by market cap at $3^{rd}$ time step for $1^{st}$, $2^{nd}$, and $3^{rd}$ time steps.
   2. Calculate diff at $3^{rd}$ time step.
   3. Repeat for time step $n$.

As of now, smoothing is only used on narratives and asset groups, and is not used on ranges.
This is because for narratives and asset groups the EMAs are taken on the original data
(before differentiation), then differentiation occurs.  Afterwards, the smoothing EMAs are
applied.  For ranges however, differentiation occurs *before* taking the EMAs, causing a 
second smoothing to be redundant.  

The smoothing periods are shown in the file name, but not the plot title since this could 
become confusing for the user consulting the plots.  On the other hand, the use of these periods
must be recorded somewhere so that we do not have different charts for the same file name. 

CHECK IF WE SHOULD BE DOING ONLY SMOOTHING EMA FOR RANGES OR IF DIFFERENT EMA VALUES LIKE FOR NARRATIVES AND GROUPS


### Store locally or query once?
Free plan has 30 calls per minute limit, and we typically would need to make around 150 calls 
for narratives, 10 calls for individual assets, and 430 calls for small-large cap ranges.

### Which coins are chosen in each narrative and market cap range?
By default, the top 10 coins at the time of running the program in each narrative are chosen.  
The exact coins that are in the top 10 at each point in time will change, but mapping the evolution
of the top 10 coins at the time of running will allow for visualizing the flows between narratives,
and the exact tokens used should not be important.  This is especially true since the plots are
all normalized to better compare market cap increments/decrements (and thus price changes).

The same can be said of the market cap ranges.  The exact coins would normally change at each 
point in time, but we are more interested in whether the changes from one point in time to the 
next is positive for a cap range and which range is growing fastest.


## Future stuff
- Add caching so that provider doesn't need to be requeried every time.
- Remove gold and stables from ranges and narratives

<!-- docs:end -->

